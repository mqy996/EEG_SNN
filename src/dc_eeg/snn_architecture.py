"""Matched Channel8 architecture ablations for the exploratory SNN study."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import torch
from torch import Tensor, nn
import yaml

from .artifacts import state_dict_sha256, write_json
from .data import EEGDataset, select_channels
from .experiment import set_deterministic_seed, torch_dtype
from .metrics import binary_metrics
from .snn_models import Channel8FeatureExtractor, Channel8HybridSNN, Channel8PilotANN, surrogate_spike
from .snn_pilot import SNNPilotConfig, _loader
from .splits import iter_loso_splits

ARCHITECTURES = ("hybrid_lif_head", "spiking_temporal_block", "ann_control")


class ArchitectureOutput(NamedTuple):
    logits: Tensor
    spike_counts: Tensor | None
    timesteps: int
    mean_spike_rate: Tensor | None
    saturated_feature_ratio: Tensor | None
    ops_proxy_per_sample: float


class SpikingTemporalBlock(nn.Module):
    """Depthwise temporal current mixing followed by a subtract-reset LIF head."""

    def __init__(
        self,
        classes: int = 2,
        beta: float = 0.9,
        threshold: float = 0.5,
        surrogate_slope: float = 25.0,
        current_scale: float = 1.0,
        temporal_kernel: int = 3,
        **feature_kwargs: int,
    ) -> None:
        super().__init__()
        if temporal_kernel <= 0 or temporal_kernel % 2 == 0:
            raise ValueError("temporal_kernel must be a positive odd number")
        if not 0.0 <= beta < 1.0 or threshold <= 0 or surrogate_slope <= 0 or current_scale <= 0:
            raise ValueError("invalid SNN parameters")
        self.features = Channel8FeatureExtractor(**feature_kwargs)
        channels = self.features.feature_channels
        self.temporal = nn.Conv1d(
            channels,
            channels,
            kernel_size=temporal_kernel,
            padding=temporal_kernel // 2,
            groups=channels,
            bias=False,
        )
        nn.init.dirac_(self.temporal.weight)
        self.classifier = nn.Linear(channels, classes)
        self.beta = float(beta)
        self.threshold = float(threshold)
        self.surrogate_slope = float(surrogate_slope)
        self.current_scale = float(current_scale)
        self.temporal_kernel = temporal_kernel

    def forward(self, x: Tensor) -> ArchitectureOutput:
        currents = self.temporal(self.features(x) * self.current_scale)
        membrane = torch.zeros_like(currents[:, :, 0])
        spike_counts = torch.zeros_like(membrane)
        for step in range(currents.shape[-1]):
            membrane = self.beta * membrane + currents[:, :, step]
            spikes = surrogate_spike(membrane - self.threshold, self.surrogate_slope)
            membrane = membrane - spikes.detach() * self.threshold
            spike_counts = spike_counts + spikes
        rates = spike_counts / currents.shape[-1]
        return ArchitectureOutput(
            logits=self.classifier(rates),
            spike_counts=spike_counts,
            timesteps=int(currents.shape[-1]),
            mean_spike_rate=rates.mean(),
            saturated_feature_ratio=(rates >= 0.5).to(rates.dtype).mean(),
            ops_proxy_per_sample=float(
                self.features.feature_channels
                * currents.shape[-1]
                * (1 + self.temporal_kernel)
            ),
        )


@dataclass(frozen=True)
class ArchitectureConfig:
    base_config_path: Path
    results_root: Path
    beta: float
    threshold: float
    seed: int
    smoke_epochs: int
    full_epochs: int
    train_batch_size: int
    eval_batch_size: int
    target_spike_rate: float
    spike_rate_regularization: float
    temporal_kernel: int
    architectures: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], repository_root: Path) -> "ArchitectureConfig":
        required = {
            "base_config",
            "results_root",
            "beta",
            "threshold",
            "seed",
            "smoke_epochs",
            "full_epochs",
            "train_batch_size",
            "eval_batch_size",
            "target_spike_rate",
            "spike_rate_regularization",
            "temporal_kernel",
            "architectures",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"architecture config is missing keys: {missing}")
        config = cls(
            base_config_path=_resolve_path(str(raw["base_config"]), repository_root),
            results_root=_resolve_path(str(raw["results_root"]), repository_root),
            beta=float(raw["beta"]),
            threshold=float(raw["threshold"]),
            seed=int(raw["seed"]),
            smoke_epochs=int(raw["smoke_epochs"]),
            full_epochs=int(raw["full_epochs"]),
            train_batch_size=int(raw["train_batch_size"]),
            eval_batch_size=int(raw["eval_batch_size"]),
            target_spike_rate=float(raw["target_spike_rate"]),
            spike_rate_regularization=float(raw["spike_rate_regularization"]),
            temporal_kernel=int(raw["temporal_kernel"]),
            architectures=tuple(str(name) for name in raw["architectures"]),
        )
        if config.architectures != ARCHITECTURES:
            raise ValueError(f"architectures must be exactly {ARCHITECTURES}")
        if not 0.0 <= config.beta < 1.0 or config.threshold <= 0:
            raise ValueError("beta/threshold values are invalid")
        if config.temporal_kernel <= 0 or config.temporal_kernel % 2 == 0:
            raise ValueError("temporal_kernel must be a positive odd number")
        if min(config.smoke_epochs, config.full_epochs, config.train_batch_size, config.eval_batch_size) <= 0:
            raise ValueError("epochs and batch sizes must be positive")
        return config


def _resolve_path(value: str, repository_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (repository_root / path).resolve()


def load_architecture_config(path: Path, repository_root: Path) -> ArchitectureConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"configuration must be a mapping: {path}")
    return ArchitectureConfig.from_mapping(raw, repository_root)


def _hash_mapping(mapping: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_architecture(name: str, pilot: SNNPilotConfig, config: ArchitectureConfig) -> nn.Module:
    kwargs = {
        "channels": 8,
        "sample_length": pilot.model["sample_length"],
        "n1": pilot.model["n1"],
        "depth_multiplier": pilot.model["depth_multiplier"],
        "kernel_length": pilot.model["kernel_length"],
        "temporal_steps": pilot.model["temporal_steps"],
    }
    if name == "hybrid_lif_head":
        return Channel8HybridSNN(
            classes=2,
            beta=config.beta,
            threshold=config.threshold,
            surrogate_slope=pilot.snn["surrogate_slope"],
            current_scale=pilot.snn["current_scale"],
            **kwargs,
        )
    if name == "spiking_temporal_block":
        return SpikingTemporalBlock(
            classes=2,
            beta=config.beta,
            threshold=config.threshold,
            surrogate_slope=pilot.snn["surrogate_slope"],
            current_scale=pilot.snn["current_scale"],
            temporal_kernel=config.temporal_kernel,
            **kwargs,
        )
    if name == "ann_control":
        return Channel8PilotANN(classes=2, **kwargs)
    raise ValueError(f"unsupported architecture: {name}")


def forward_architecture(model: nn.Module, name: str, inputs: Tensor) -> ArchitectureOutput:
    if name == "ann_control":
        logits = model(inputs)
        return ArchitectureOutput(logits, None, 1, None, None, 0.0)
    output = model(inputs)
    if isinstance(output, ArchitectureOutput):
        return output
    timesteps = int(output.timesteps)
    rates = output.spike_counts / timesteps
    return ArchitectureOutput(
        logits=output.logits,
        spike_counts=output.spike_counts,
        timesteps=timesteps,
        mean_spike_rate=output.mean_spike_rate,
        saturated_feature_ratio=(rates >= 0.5).to(rates.dtype).mean(),
        ops_proxy_per_sample=float(output.spike_counts.shape[1] * timesteps),
    )


def train_and_evaluate_architecture_fold(
    dataset: EEGDataset,
    held_out_fold: int,
    architecture: str,
    pilot: SNNPilotConfig,
    config: ArchitectureConfig,
    device: torch.device,
    epochs: int,
) -> dict[str, Any]:
    if architecture not in ARCHITECTURES:
        raise ValueError(f"unsupported architecture: {architecture}")
    set_deterministic_seed(config.seed + held_out_fold)
    dtype = torch_dtype(pilot.dtype)
    selected = select_channels(dataset.samples)
    split = iter_loso_splits(dataset.subject_ids, fold=held_out_fold)[0]
    model = build_architecture(architecture, pilot, config).to(device=device, dtype=dtype)
    optimizer = torch.optim.Adam(model.parameters(), lr=pilot.learning_rate)
    loss_function = nn.CrossEntropyLoss()
    train_loader = _loader(
        selected[split.train_indices],
        dataset.labels[split.train_indices],
        config.train_batch_size,
        True,
        dtype,
        config.seed + held_out_fold,
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
            output = forward_architecture(model, architecture, inputs)
            loss = loss_function(output.logits, targets)
            if output.mean_spike_rate is not None:
                rate_error = output.mean_spike_rate - config.target_spike_rate
                loss = loss + config.spike_rate_regularization * rate_error.square()
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss: architecture={architecture}, fold={held_out_fold}")
            loss.backward()
            optimizer.step()
            n = int(targets.numel())
            total_loss += float(loss.detach().cpu()) * n
            count += n
        final_loss = total_loss / count

    test_loader = _loader(
        selected[split.test_indices],
        dataset.labels[split.test_indices],
        config.eval_batch_size,
        False,
        dtype,
        config.seed + held_out_fold,
    )
    predictions: list[np.ndarray] = []
    total_spikes = 0.0
    total_slots = 0
    silent = 0
    saturated = 0
    units = 0
    ops_proxy = 0.0
    model.eval()
    with torch.no_grad():
        for inputs, _ in test_loader:
            inputs = inputs.to(device=device, non_blocking=True)
            output = forward_architecture(model, architecture, inputs)
            predictions.append(output.logits.argmax(dim=1).cpu().numpy())
            if output.spike_counts is not None:
                counts = output.spike_counts
                total_spikes += float(counts.sum().cpu())
                total_slots += int(counts.numel() * output.timesteps)
                silent += int((counts == 0).sum().cpu())
                saturated += int((counts / output.timesteps >= 0.5).sum().cpu())
                units += int(counts.numel())
                ops_proxy = output.ops_proxy_per_sample

    pred = np.concatenate(predictions)
    metrics = binary_metrics(dataset.labels[split.test_indices], pred).to_dict()
    mean_spike_rate = total_spikes / total_slots if total_slots else None
    result = {
        "architecture": architecture,
        "held_out_subject": held_out_fold,
        "seed": config.seed,
        "metrics": metrics,
        "checkpoint_identity": state_dict_sha256(model),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "epochs": epochs,
        "final_train_loss": final_loss,
        "mean_spike_rate": mean_spike_rate,
        "silent_feature_ratio": silent / units if units else None,
        "saturated_feature_ratio": saturated / units if units else None,
        "architecture_ops_proxy_per_sample": ops_proxy,
        "temporal_kernel": config.temporal_kernel if architecture == "spiking_temporal_block" else None,
    }
    values = [final_loss]
    values.extend(value for value in (mean_spike_rate, result["silent_feature_ratio"], result["saturated_feature_ratio"]) if value is not None)
    if not all(np.isfinite(float(value)) for value in values):
        raise RuntimeError(f"non-finite architecture evidence: architecture={architecture}, fold={held_out_fold}")
    return result


def prepare_run(run_dir: Path, config: ArchitectureConfig, dataset: EEGDataset, run_id: str) -> None:
    if run_dir.exists():
        raise FileExistsError(f"architecture run exists: {run_dir}; use --resume")
    run_dir.mkdir(parents=True)
    (run_dir / "jobs").mkdir()
    resolved = {key: str(value) if isinstance(value, Path) else value for key, value in {
        "base_config": config.base_config_path,
        "results_root": config.results_root,
        "beta": config.beta,
        "threshold": config.threshold,
        "seed": config.seed,
        "smoke_epochs": config.smoke_epochs,
        "full_epochs": config.full_epochs,
        "train_batch_size": config.train_batch_size,
        "eval_batch_size": config.eval_batch_size,
        "target_spike_rate": config.target_spike_rate,
        "spike_rate_regularization": config.spike_rate_regularization,
        "temporal_kernel": config.temporal_kernel,
        "architectures": list(config.architectures),
    }.items()}
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(resolved, sort_keys=False), encoding="utf-8")
    write_json(run_dir / "dataset_manifest.json", {"sha256": dataset.metadata.sha256, "order_kind": dataset.metadata.order_kind, "samples": dataset.metadata.samples, "channels": dataset.metadata.channels})
    write_json(run_dir / "job_manifest.json", {"schema_version": 1, "run_id": run_id, "config_hash": _hash_mapping(resolved), "jobs": {}})
    write_json(run_dir / "completion.json", {"run_id": run_id, "complete": False, "failure": None, "jobs_expected": 0, "jobs_complete": 0})


def run_architecture_stage(
    run_dir: Path,
    architectures: list[str],
    folds: list[int],
    pilot: SNNPilotConfig,
    config: ArchitectureConfig,
    dataset: EEGDataset,
    device: torch.device,
    epochs: int,
    resume: bool,
) -> dict[str, int]:
    jobs = [(name, fold) for name in architectures for fold in folds]
    manifest = json.loads((run_dir / "job_manifest.json").read_text(encoding="utf-8"))
    manifest["jobs_expected"] = len(jobs)
    for name, fold in jobs:
        job_id = f"{name}-seed{config.seed}-fold{fold}"
        path = run_dir / "jobs" / job_id / "metrics.json"
        if resume and path.is_file():
            continue
        job_dir = path.parent
        job_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = train_and_evaluate_architecture_fold(dataset, fold, name, pilot, config, device, epochs)
            write_json(job_dir / "metrics.json", result)
            manifest["jobs"][job_id] = {"state": "complete", "architecture": name, "fold": fold, "result_path": str(path)}
        except BaseException as error:
            write_json(job_dir / "metrics.json", {"state": "failed", "error": {"type": type(error).__name__, "message": str(error)}})
            manifest["jobs"][job_id] = {"state": "failed", "architecture": name, "fold": fold, "result_path": str(path)}
            (run_dir / "job_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            raise
        (run_dir / "job_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    complete = sum(record.get("state") == "complete" for record in manifest["jobs"].values())
    write_json(run_dir / "completion.json", {"run_id": manifest["run_id"], "complete": complete == len(jobs), "jobs_expected": len(jobs), "jobs_complete": complete, "failure": None})
    return {"planned_jobs": len(jobs), "complete_jobs": complete}


def aggregate_architecture_results(run_dir: Path, architectures: list[str]) -> dict[str, Any]:
    all_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in architectures}
    manifest = json.loads((run_dir / "job_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["jobs"].values():
        if record.get("state") != "complete":
            continue
        all_rows[record["architecture"]].append(json.loads(Path(record["result_path"]).read_text(encoding="utf-8")))
    baseline = all_rows["hybrid_lif_head"]
    if len(baseline) != 11:
        raise ValueError("full architecture aggregation requires 11 hybrid_lif_head results")
    base_acc = float(np.mean([row["metrics"]["accuracy"] for row in baseline]))
    base_balanced = float(np.mean([row["metrics"]["balanced_accuracy"] for row in baseline]))
    base_f1 = float(np.mean([row["metrics"]["macro_f1"] for row in baseline]))
    base_params = float(np.mean([row["parameter_count"] for row in baseline]))
    summary: dict[str, Any] = {}
    for name, rows in all_rows.items():
        if len(rows) != 11:
            continue
        mean_acc = float(np.mean([row["metrics"]["accuracy"] for row in rows]))
        mean_f1 = float(np.mean([row["metrics"]["macro_f1"] for row in rows]))
        mean_balanced = float(np.mean([row["metrics"]["balanced_accuracy"] for row in rows]))
        spike_values = [row["mean_spike_rate"] for row in rows if row["mean_spike_rate"] is not None]
        summary[name] = {
            "folds": 11,
            "mean_accuracy": mean_acc,
            "mean_balanced_accuracy": mean_balanced,
            "mean_macro_f1": mean_f1,
            "accuracy_delta_vs_hybrid": mean_acc - base_acc,
            "balanced_accuracy_delta_vs_hybrid": mean_balanced - base_balanced,
            "macro_f1_delta_vs_hybrid": mean_f1 - base_f1,
            "mean_spike_rate": float(np.mean(spike_values)) if spike_values else None,
            "parameter_count": int(round(np.mean([row["parameter_count"] for row in rows]))),
            "parameter_delta_vs_hybrid": float(np.mean([row["parameter_count"] for row in rows]) / base_params - 1.0),
            "architecture_ops_proxy_per_sample": float(np.mean([row["architecture_ops_proxy_per_sample"] for row in rows])),
            "mean_silent_feature_ratio": float(np.mean([row["silent_feature_ratio"] for row in rows if row["silent_feature_ratio"] is not None])) if spike_values else None,
            "mean_saturated_feature_ratio": float(np.mean([row["saturated_feature_ratio"] for row in rows if row["saturated_feature_ratio"] is not None])) if spike_values else None,
        }
    selected = []
    for name, row in summary.items():
        if name == "ann_control":
            continue
        if row["macro_f1_delta_vs_hybrid"] >= 0.0 and row["mean_spike_rate"] is not None and 0.05 <= row["mean_spike_rate"] <= 0.30 and row["mean_saturated_feature_ratio"] < 0.50:
            selected.append(name)
    result = {"architectures": summary, "selected": selected, "go": bool(selected), "conversion_status": "blocked_not_implemented", "next_task": "snn-hardware-feasibility" if selected else None}
    write_json(run_dir / "aggregate.json", result)
    return result
