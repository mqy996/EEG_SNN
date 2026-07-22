"""Training and staged artifacts for SNN input-encoding comparisons."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
import yaml

from .artifacts import state_dict_sha256, write_json
from .data import EEGDataset, select_channels
from .experiment import set_deterministic_seed, torch_dtype
from .metrics import binary_metrics
from .snn_encoders import Channel8EncodedSNN
from .snn_pilot import SNNPilotConfig, _loader
from .splits import iter_loso_splits

ENCODERS = ("direct_current", "amplitude_count", "delta")


@dataclass(frozen=True)
class EncodingConfig:
    base_config_path: Path
    results_root: Path
    beta: float
    threshold: float
    encoder_threshold: float
    seed: int
    smoke_epochs: int
    full_epochs: int
    train_batch_size: int
    eval_batch_size: int
    target_spike_rate: float
    spike_rate_regularization: float
    encoders: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], repository_root: Path) -> "EncodingConfig":
        required = {
            "base_config",
            "results_root",
            "beta",
            "threshold",
            "encoder_threshold",
            "seed",
            "smoke_epochs",
            "full_epochs",
            "train_batch_size",
            "eval_batch_size",
            "target_spike_rate",
            "spike_rate_regularization",
            "encoders",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"encoding config is missing keys: {missing}")
        config = cls(
            base_config_path=_resolve_path(str(raw["base_config"]), repository_root),
            results_root=_resolve_path(str(raw["results_root"]), repository_root),
            beta=float(raw["beta"]),
            threshold=float(raw["threshold"]),
            encoder_threshold=float(raw["encoder_threshold"]),
            seed=int(raw["seed"]),
            smoke_epochs=int(raw["smoke_epochs"]),
            full_epochs=int(raw["full_epochs"]),
            train_batch_size=int(raw["train_batch_size"]),
            eval_batch_size=int(raw["eval_batch_size"]),
            target_spike_rate=float(raw["target_spike_rate"]),
            spike_rate_regularization=float(raw["spike_rate_regularization"]),
            encoders=tuple(str(name) for name in raw["encoders"]),
        )
        if config.encoders != ENCODERS:
            raise ValueError(f"encoders must be exactly {ENCODERS}")
        if not 0.0 <= config.beta < 1.0 or config.threshold <= 0 or config.encoder_threshold <= 0:
            raise ValueError("beta/threshold values are invalid")
        if min(config.smoke_epochs, config.full_epochs, config.train_batch_size, config.eval_batch_size) <= 0:
            raise ValueError("epochs and batch sizes must be positive")
        return config


def _resolve_path(value: str, repository_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (repository_root / path).resolve()


def load_encoding_config(path: Path, repository_root: Path) -> EncodingConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"configuration must be a mapping: {path}")
    return EncodingConfig.from_mapping(raw, repository_root)


def _hash_mapping(mapping: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _build_model(encoding: str, config: SNNPilotConfig, override: EncodingConfig) -> Channel8EncodedSNN:
    return Channel8EncodedSNN(
        encoder=encoding,
        encoder_threshold=override.encoder_threshold,
        classes=2,
        beta=override.beta,
        threshold=override.threshold,
        surrogate_slope=config.snn["surrogate_slope"],
        current_scale=config.snn["current_scale"],
        channels=8,
        sample_length=config.model["sample_length"],
        n1=config.model["n1"],
        depth_multiplier=config.model["depth_multiplier"],
        kernel_length=config.model["kernel_length"],
        temporal_steps=config.model["temporal_steps"],
    )


def train_and_evaluate_encoding_fold(
    dataset: EEGDataset,
    held_out_fold: int,
    encoding: str,
    pilot: SNNPilotConfig,
    override: EncodingConfig,
    device: torch.device,
    epochs: int,
) -> dict[str, Any]:
    if encoding not in ENCODERS:
        raise ValueError(f"unsupported encoding: {encoding}")
    set_deterministic_seed(override.seed + held_out_fold)
    dtype = torch_dtype(pilot.dtype)
    selected = select_channels(dataset.samples)
    split = iter_loso_splits(dataset.subject_ids, fold=held_out_fold)[0]
    model = _build_model(encoding, pilot, override).to(device=device, dtype=dtype)
    optimizer = torch.optim.Adam(model.parameters(), lr=pilot.learning_rate)
    loss_function = nn.CrossEntropyLoss()
    train_loader = _loader(
        selected[split.train_indices],
        dataset.labels[split.train_indices],
        override.train_batch_size,
        True,
        dtype,
        override.seed + held_out_fold,
    )
    final_loss = float("nan")
    model.train()
    for _ in range(epochs):
        total_loss = 0.0
        count = 0
        for inputs, targets in train_loader:
            inputs = inputs.to(device=device, non_blocking=True)
            targets = targets.to(device=device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            output = model(inputs)
            loss = loss_function(output.logits, targets)
            rate_error = output.mean_spike_rate - override.target_spike_rate
            loss = loss + override.spike_rate_regularization * rate_error.square()
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss: encoding={encoding}, fold={held_out_fold}")
            loss.backward()
            optimizer.step()
            n = int(targets.numel())
            total_loss += float(loss.detach().cpu()) * n
            count += n
        final_loss = total_loss / count

    test_loader = _loader(
        selected[split.test_indices],
        dataset.labels[split.test_indices],
        override.eval_batch_size,
        False,
        dtype,
        override.seed + held_out_fold,
    )
    predictions: list[np.ndarray] = []
    total_spikes = 0.0
    total_slots = 0
    total_input_rate = 0.0
    input_batches = 0
    silent = 0
    saturated = 0
    units = 0
    input_ops = 0.0
    state_bytes = 0
    model.eval()
    with torch.no_grad():
        for inputs, _ in test_loader:
            inputs = inputs.to(device=device, non_blocking=True)
            output = model(inputs)
            predictions.append(output.logits.argmax(dim=1).cpu().numpy())
            counts = output.spike_counts
            total_spikes += float(counts.sum().cpu())
            total_slots += int(counts.numel() * output.timesteps)
            silent += int((counts == 0).sum().cpu())
            saturated += int((counts / output.timesteps >= 0.5).sum().cpu())
            units += int(counts.numel())
            if torch.isfinite(output.input_event_rate):
                total_input_rate += float(output.input_event_rate.cpu()) * inputs.shape[0]
                input_batches += int(inputs.shape[0])
            input_ops = output.encoder_ops_proxy_per_sample
            state_bytes = output.encoder_state_bytes
    pred = np.concatenate(predictions)
    metrics = binary_metrics(dataset.labels[split.test_indices], pred).to_dict()
    mean_spike_rate = total_spikes / total_slots
    result = {
        "encoding": encoding,
        "held_out_subject": held_out_fold,
        "seed": override.seed,
        "metrics": metrics,
        "checkpoint_identity": state_dict_sha256(model),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "epochs": epochs,
        "final_train_loss": final_loss,
        "mean_spike_rate": mean_spike_rate,
        "input_event_rate": total_input_rate / input_batches if input_batches else None,
        "silent_feature_ratio": silent / units,
        "saturated_feature_ratio": saturated / units,
        "encoder_state_bytes": state_bytes,
        "encoder_ops_proxy_per_sample": input_ops,
    }
    values = [final_loss, mean_spike_rate, result["silent_feature_ratio"], result["saturated_feature_ratio"]]
    if not all(np.isfinite(float(value)) for value in values):
        raise RuntimeError(f"non-finite encoding evidence: encoding={encoding}, fold={held_out_fold}")
    return result


def prepare_run(run_dir: Path, encoding: EncodingConfig, pilot: SNNPilotConfig, dataset: EEGDataset, run_id: str) -> None:
    if run_dir.exists():
        raise FileExistsError(f"encoding run exists: {run_dir}; use --resume")
    run_dir.mkdir(parents=True)
    (run_dir / "jobs").mkdir()
    resolved = {
        "base_config": str(encoding.base_config_path),
        "results_root": str(encoding.results_root),
        "beta": encoding.beta,
        "threshold": encoding.threshold,
        "encoder_threshold": encoding.encoder_threshold,
        "seed": encoding.seed,
        "smoke_epochs": encoding.smoke_epochs,
        "full_epochs": encoding.full_epochs,
        "train_batch_size": encoding.train_batch_size,
        "eval_batch_size": encoding.eval_batch_size,
        "target_spike_rate": encoding.target_spike_rate,
        "spike_rate_regularization": encoding.spike_rate_regularization,
        "encoders": list(encoding.encoders),
    }
    (run_dir / "resolved_config.yaml").write_text(
        yaml.safe_dump(resolved, sort_keys=False), encoding="utf-8"
    )
    write_json(run_dir / "dataset_manifest.json", {"sha256": dataset.metadata.sha256, "order_kind": dataset.metadata.order_kind, "samples": dataset.metadata.samples, "channels": dataset.metadata.channels})
    write_json(run_dir / "job_manifest.json", {"schema_version": 1, "run_id": run_id, "config_hash": _hash_mapping({"beta": encoding.beta, "threshold": encoding.threshold, "encoder_threshold": encoding.encoder_threshold}), "jobs": {}})
    write_json(run_dir / "completion.json", {"run_id": run_id, "complete": False, "failure": None, "jobs_expected": 0, "jobs_complete": 0})


def run_encoding_stage(run_dir: Path, encodings: list[str], folds: list[int], pilot: SNNPilotConfig, encoding_config: EncodingConfig, dataset: EEGDataset, device: torch.device, epochs: int, resume: bool) -> dict[str, Any]:
    jobs = [(name, fold) for name in encodings for fold in folds]
    manifest = json.loads((run_dir / "job_manifest.json").read_text(encoding="utf-8"))
    manifest["jobs_expected"] = len(jobs)
    for name, fold in jobs:
        job_id = f"{name}-seed{encoding_config.seed}-fold{fold}"
        path = run_dir / "jobs" / job_id / "metrics.json"
        if resume and path.is_file():
            continue
        job_dir = path.parent
        job_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = train_and_evaluate_encoding_fold(dataset, fold, name, pilot, encoding_config, device, epochs)
            write_json(job_dir / "metrics.json", result)
            manifest["jobs"][job_id] = {"state": "complete", "encoding": name, "fold": fold, "result_path": str(path)}
        except BaseException as error:
            write_json(job_dir / "metrics.json", {"state": "failed", "error": {"type": type(error).__name__, "message": str(error)}})
            manifest["jobs"][job_id] = {"state": "failed", "encoding": name, "fold": fold, "result_path": str(path)}
            (run_dir / "job_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            raise
        (run_dir / "job_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    complete = sum(record.get("state") == "complete" for record in manifest["jobs"].values())
    write_json(run_dir / "completion.json", {"run_id": manifest["run_id"], "complete": complete == len(jobs), "jobs_expected": len(jobs), "jobs_complete": complete, "failure": None})
    return {"planned_jobs": len(jobs), "complete_jobs": complete}


def aggregate_encoding_results(run_dir: Path, encodings: list[str]) -> dict[str, Any]:
    all_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in encodings}
    manifest = json.loads((run_dir / "job_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["jobs"].values():
        if record.get("state") != "complete":
            continue
        all_rows[record["encoding"]].append(json.loads(Path(record["result_path"]).read_text(encoding="utf-8")))
    summary: dict[str, Any] = {}
    direct = all_rows["direct_current"]
    if len(direct) != 11:
        raise ValueError("full encoding aggregation requires 11 direct_current fold results")
    direct_acc = float(np.mean([row["metrics"]["accuracy"] for row in direct]))
    direct_f1 = float(np.mean([row["metrics"]["macro_f1"] for row in direct]))
    direct_balanced = float(np.mean([row["metrics"]["balanced_accuracy"] for row in direct]))
    for name, rows in all_rows.items():
        if len(rows) != 11:
            continue
        mean_f1 = float(np.mean([row["metrics"]["macro_f1"] for row in rows]))
        mean_acc = float(np.mean([row["metrics"]["accuracy"] for row in rows]))
        mean_balanced = float(np.mean([row["metrics"]["balanced_accuracy"] for row in rows]))
        summary[name] = {
            "folds": 11,
            "mean_accuracy": mean_acc,
            "mean_balanced_accuracy": mean_balanced,
            "mean_macro_f1": mean_f1,
            "accuracy_delta_vs_direct": mean_acc - direct_acc,
            "balanced_accuracy_delta_vs_direct": mean_balanced - direct_balanced,
            "macro_f1_delta_vs_direct": mean_f1 - direct_f1,
            "mean_spike_rate": float(np.mean([row["mean_spike_rate"] for row in rows])),
            "mean_input_event_rate": None if all(row["input_event_rate"] is None for row in rows) else float(np.mean([row["input_event_rate"] for row in rows if row["input_event_rate"] is not None])),
            "encoder_state_bytes": int(max(row["encoder_state_bytes"] for row in rows)),
            "encoder_ops_proxy_per_sample": float(np.mean([row["encoder_ops_proxy_per_sample"] for row in rows])),
            "mean_silent_feature_ratio": float(np.mean([row["silent_feature_ratio"] for row in rows])),
            "mean_saturated_feature_ratio": float(np.mean([row["saturated_feature_ratio"] for row in rows])),
        }
    selected = []
    for name, row in summary.items():
        if row["macro_f1_delta_vs_direct"] >= -0.05 and 0.05 <= row["mean_spike_rate"] <= 0.30 and row["mean_saturated_feature_ratio"] < 0.50:
            selected.append(name)
    result = {"encodings": summary, "selected": selected, "go": bool(selected), "next_task": "snn-architecture-ablation" if selected else None}
    write_json(run_dir / "aggregate.json", result)
    return result
