"""Training and artifact helpers for the matched Channel8 Hybrid-SNN pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import yaml

from .artifacts import state_dict_sha256, write_json
from .data import CHANNEL8_INDICES, CHANNEL8_NAMES, EEGDataset, select_channels
from .experiment import repository_state, set_deterministic_seed, torch_dtype
from .metrics import BinaryMetrics, aggregate_subject_metrics, binary_metrics
from .snn_models import Channel8HybridSNN, Channel8PilotANN, SNNForwardResult
from .splits import LosoSplit, split_manifest


@dataclass(frozen=True)
class SNNPilotConfig:
    dataset_path: Path
    expected_dataset_sha256: str
    results_root: Path
    seed: int
    epochs: int
    smoke_epochs: int
    learning_rate: float
    train_batch_size: int
    eval_batch_size: int
    dtype: str
    model: dict[str, int]
    snn: dict[str, float]
    spike_rate_regularization: float
    target_spike_rate: float

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], repository_root: Path) -> "SNNPilotConfig":
        required = {
            "dataset_path",
            "expected_dataset_sha256",
            "results_root",
            "seed",
            "epochs",
            "smoke_epochs",
            "learning_rate",
            "train_batch_size",
            "eval_batch_size",
            "dtype",
            "model",
            "snn",
            "spike_rate_regularization",
            "target_spike_rate",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"SNN pilot config is missing keys: {missing}")
        if not isinstance(raw["model"], dict) or not isinstance(raw["snn"], dict):
            raise ValueError("model and snn must be mappings")
        config = cls(
            dataset_path=_resolve_path(str(raw["dataset_path"]), repository_root),
            expected_dataset_sha256=str(raw["expected_dataset_sha256"]).lower(),
            results_root=_resolve_path(str(raw["results_root"]), repository_root),
            seed=int(raw["seed"]),
            epochs=int(raw["epochs"]),
            smoke_epochs=int(raw["smoke_epochs"]),
            learning_rate=float(raw["learning_rate"]),
            train_batch_size=int(raw["train_batch_size"]),
            eval_batch_size=int(raw["eval_batch_size"]),
            dtype=str(raw["dtype"]),
            model={str(key): int(value) for key, value in raw["model"].items()},
            snn={str(key): float(value) for key, value in raw["snn"].items()},
            spike_rate_regularization=float(raw["spike_rate_regularization"]),
            target_spike_rate=float(raw["target_spike_rate"]),
        )
        model_required = {"sample_length", "n1", "depth_multiplier", "kernel_length", "temporal_steps"}
        snn_required = {"beta", "threshold", "surrogate_slope", "current_scale"}
        missing_model = sorted(model_required - config.model.keys())
        missing_snn = sorted(snn_required - config.snn.keys())
        if missing_model or missing_snn:
            raise ValueError(
                f"nested config keys missing: model={missing_model}, snn={missing_snn}"
            )
        if len(config.expected_dataset_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in config.expected_dataset_sha256
        ):
            raise ValueError("expected_dataset_sha256 must be a lowercase 64-character hex digest")
        if min(config.epochs, config.smoke_epochs, config.train_batch_size, config.eval_batch_size) <= 0:
            raise ValueError("epochs and batch sizes must be positive")
        if config.learning_rate <= 0 or config.spike_rate_regularization < 0:
            raise ValueError("learning_rate must be positive and regularization non-negative")
        if not 0.0 < config.target_spike_rate < 1.0:
            raise ValueError("target_spike_rate must be in (0, 1)")
        torch_dtype(config.dtype)
        return config

    def resolved(self, epochs: int) -> dict[str, Any]:
        return {
            "dataset_path": str(self.dataset_path),
            "expected_dataset_sha256": self.expected_dataset_sha256,
            "results_root": str(self.results_root),
            "seed": self.seed,
            "epochs": epochs,
            "smoke_epochs": self.smoke_epochs,
            "learning_rate": self.learning_rate,
            "train_batch_size": self.train_batch_size,
            "eval_batch_size": self.eval_batch_size,
            "dtype": self.dtype,
            "normalization_mode": "groupnorm",
            "replay_order": "class_blocked_compatibility_no_chronology_claim",
            "model": self.model,
            "snn": self.snn,
            "spike_rate_regularization": self.spike_rate_regularization,
            "target_spike_rate": self.target_spike_rate,
        }


@dataclass(frozen=True)
class PilotFoldResult:
    held_out_subject: int
    model_kind: str
    metrics: BinaryMetrics
    checkpoint_identity: str
    parameter_count: int
    epochs: int
    final_train_loss: float
    mean_spike_rate: float | None
    silent_feature_ratio: float | None
    saturated_feature_ratio: float | None
    head_synops_proxy_per_sample: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metrics"] = self.metrics.to_dict()
        return payload


def _resolve_path(value: str, repository_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (repository_root / path).resolve()


def load_config(path: Path, repository_root: Path) -> SNNPilotConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"configuration must be a mapping: {path}")
    return SNNPilotConfig.from_mapping(raw, repository_root)


def validate_pilot_dataset(dataset: EEGDataset, config: SNNPilotConfig) -> None:
    """Pin the exploratory run to the audited official balanced artifact."""

    if dataset.metadata.sha256 != config.expected_dataset_sha256:
        raise ValueError(
            "dataset SHA-256 does not match the pilot configuration: "
            f"expected={config.expected_dataset_sha256}, actual={dataset.metadata.sha256}"
        )
    if dataset.metadata.samples != 2022 or dataset.metadata.channels != 30:
        raise ValueError(
            "Channel8 SNN pilot expects the official balanced 2022x30 artifact; "
            f"got samples={dataset.metadata.samples}, channels={dataset.metadata.channels}"
        )
    if dataset.metadata.order_kind != "class_blocked_compatibility":
        raise ValueError(
            "pilot expects the audited class-blocked compatibility artifact; "
            f"got order_kind={dataset.metadata.order_kind}"
        )


def _loader(
    samples: np.ndarray,
    labels: np.ndarray,
    batch_size: int,
    shuffle: bool,
    dtype: torch.dtype,
    seed: int,
) -> DataLoader:
    tensor_samples = torch.as_tensor(samples, dtype=dtype).unsqueeze(1)
    tensor_labels = torch.as_tensor(labels, dtype=torch.long)
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        TensorDataset(tensor_samples, tensor_labels),
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
    )


def _build_model(
    model_kind: str,
    config: SNNPilotConfig,
    dtype: torch.dtype,
    device: torch.device,
) -> nn.Module:
    common = {
        "classes": 2,
        "channels": len(CHANNEL8_NAMES),
        "sample_length": int(config.model["sample_length"]),
        "n1": int(config.model["n1"]),
        "depth_multiplier": int(config.model["depth_multiplier"]),
        "kernel_length": int(config.model["kernel_length"]),
        "temporal_steps": int(config.model["temporal_steps"]),
    }
    if model_kind == "ann":
        model: nn.Module = Channel8PilotANN(**common)
    elif model_kind == "snn":
        model = Channel8HybridSNN(**common, **config.snn)
    else:
        raise ValueError(f"unsupported model_kind: {model_kind}")
    return model.to(device=device, dtype=dtype)


def _forward_logits(model: nn.Module, inputs: torch.Tensor) -> tuple[torch.Tensor, SNNForwardResult | None]:
    output = model(inputs)
    if isinstance(output, SNNForwardResult):
        return output.logits, output
    return output, None


def train_and_evaluate_pilot_fold(
    dataset: EEGDataset,
    split: LosoSplit,
    config: SNNPilotConfig,
    device: torch.device,
    model_kind: str,
    epochs: int,
) -> PilotFoldResult:
    fold_seed = config.seed + split.held_out_subject
    set_deterministic_seed(fold_seed)
    dtype = torch_dtype(config.dtype)
    selected = select_channels(dataset.samples)
    model = _build_model(model_kind, config, dtype, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_function = nn.CrossEntropyLoss()
    train_loader = _loader(
        selected[split.train_indices],
        dataset.labels[split.train_indices],
        config.train_batch_size,
        True,
        dtype,
        fold_seed,
    )

    final_loss = math.nan
    model.train()
    for _ in range(epochs):
        epoch_loss = 0.0
        seen = 0
        for inputs, targets in train_loader:
            inputs = inputs.to(device=device, non_blocking=True)
            targets = targets.to(device=device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits, snn_output = _forward_logits(model, inputs)
            loss = loss_function(logits, targets)
            if snn_output is not None:
                rate_error = snn_output.mean_spike_rate - config.target_spike_rate
                loss = loss + config.spike_rate_regularization * rate_error.square()
            if not torch.isfinite(loss):
                raise RuntimeError(
                    f"non-finite training loss for fold={split.held_out_subject}, model={model_kind}"
                )
            loss.backward()
            optimizer.step()
            batch_samples = int(targets.numel())
            epoch_loss += float(loss.detach().cpu()) * batch_samples
            seen += batch_samples
        final_loss = epoch_loss / seen

    test_samples = selected[split.test_indices]
    test_labels = dataset.labels[split.test_indices]
    test_loader = _loader(
        test_samples,
        test_labels,
        config.eval_batch_size,
        False,
        dtype,
        fold_seed,
    )
    predictions: list[np.ndarray] = []
    total_spikes = 0.0
    total_slots = 0
    silent_features = 0
    saturated_features = 0
    feature_units = 0
    timesteps = 0
    model.eval()
    with torch.no_grad():
        for inputs, _ in test_loader:
            inputs = inputs.to(device=device, non_blocking=True)
            logits, snn_output = _forward_logits(model, inputs)
            predictions.append(logits.argmax(dim=1).cpu().numpy())
            if snn_output is not None:
                counts = snn_output.spike_counts
                timesteps = snn_output.timesteps
                total_spikes += float(counts.sum().cpu())
                total_slots += int(counts.numel() * timesteps)
                silent_features += int((counts == 0).sum().cpu())
                saturated_features += int((counts / timesteps >= 0.5).sum().cpu())
                feature_units += int(counts.numel())

    prediction_array = np.concatenate(predictions)
    spike_rate = total_spikes / total_slots if total_slots else None
    silent_ratio = silent_features / feature_units if feature_units else None
    saturated_ratio = saturated_features / feature_units if feature_units else None
    synops = total_spikes * 2.0 / len(test_samples) if total_slots else None
    values = [final_loss]
    values.extend(value for value in (spike_rate, silent_ratio, saturated_ratio, synops) if value is not None)
    if not all(math.isfinite(value) for value in values):
        raise RuntimeError(f"non-finite pilot evidence for fold={split.held_out_subject}, model={model_kind}")
    return PilotFoldResult(
        held_out_subject=split.held_out_subject,
        model_kind=model_kind,
        metrics=binary_metrics(test_labels, prediction_array),
        checkpoint_identity=state_dict_sha256(model),
        parameter_count=sum(parameter.numel() for parameter in model.parameters()),
        epochs=epochs,
        final_train_loss=final_loss,
        mean_spike_rate=spike_rate,
        silent_feature_ratio=silent_ratio,
        saturated_feature_ratio=saturated_ratio,
        head_synops_proxy_per_sample=synops,
    )


def make_run_id(seed: int, smoke: bool) -> str:
    mode = "smoke" if smoke else "loso"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"channel8-hybrid-snn-{mode}-{stamp}-seed{seed}"



def _dataset_payload(dataset: EEGDataset) -> dict[str, Any]:
    return {
        "source_path": dataset.metadata.source_path,
        "sha256": dataset.metadata.sha256,
        "samples": dataset.metadata.samples,
        "channels": dataset.metadata.channels,
        "timepoints": dataset.metadata.timepoints,
        "labels": dataset.metadata.labels,
        "subjects": list(dataset.metadata.subjects),
        "order_kind": dataset.metadata.order_kind,
        "selected_channels": list(CHANNEL8_NAMES),
        "selected_channel_indices": list(CHANNEL8_INDICES),
    }


def prepare_pilot_run(
    run_dir: Path,
    config: SNNPilotConfig,
    dataset: EEGDataset,
    splits: list[LosoSplit],
    device: torch.device,
    epochs: int,
    smoke: bool,
) -> None:
    """Create an auditable partial run before expensive training starts."""

    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "resolved_config.yaml").write_text(
        yaml.safe_dump(config.resolved(epochs), sort_keys=False), encoding="utf-8"
    )
    write_json(run_dir / "dataset_manifest.json", _dataset_payload(dataset))
    write_json(run_dir / "split_manifest.json", split_manifest(splits, dataset.subject_ids))
    write_json(
        run_dir / "completion.json",
        {
            "complete": False,
            "smoke": smoke,
            "device": str(device),
            "folds_expected": len(splits),
            "fold_model_results_expected": len(splits) * 2,
            "fold_model_results_written": 0,
            "failure": None,
        },
    )


def mark_pilot_failed(run_dir: Path, error: BaseException) -> None:
    write_json(
        run_dir / "completion.json",
        {
            "complete": False,
            "fold_model_results_written": 0,
            "failure": {"type": type(error).__name__, "message": str(error)},
        },
    )


def _validate_result_matrix(
    splits: list[LosoSplit], results: list[PilotFoldResult]
) -> None:
    expected = {
        (split.held_out_subject, model_kind)
        for split in splits
        for model_kind in ("ann", "snn")
    }
    actual = [(result.held_out_subject, result.model_kind) for result in results]
    if len(actual) != len(set(actual)):
        raise ValueError("pilot results contain duplicate fold/model pairs")
    missing = sorted(expected - set(actual))
    unexpected = sorted(set(actual) - expected)
    if missing or unexpected:
        raise ValueError(
            f"pilot result matrix mismatch: missing={missing}, unexpected={unexpected}"
        )

def write_pilot_artifacts(
    run_dir: Path,
    config: SNNPilotConfig,
    dataset: EEGDataset,
    splits: list[LosoSplit],
    device: torch.device,
    results: list[PilotFoldResult],
    epochs: int,
    smoke: bool,
) -> dict[str, Any]:
    if not run_dir.is_dir():
        raise FileNotFoundError(f"pilot run was not prepared: {run_dir}")
    _validate_result_matrix(splits, results)

    by_model: dict[str, list[PilotFoldResult]] = {"ann": [], "snn": []}
    for result in results:
        by_model[result.model_kind].append(result)
    aggregate: dict[str, Any] = {}
    for model_kind, model_results in by_model.items():
        if not model_results:
            continue
        aggregate[model_kind] = {
            **aggregate_subject_metrics([item.metrics for item in model_results]),
            "parameter_count": model_results[0].parameter_count,
        }
        if model_kind == "snn":
            aggregate[model_kind]["mean_spike_rate"] = float(
                np.mean([item.mean_spike_rate for item in model_results])
            )
            aggregate[model_kind]["mean_silent_feature_ratio"] = float(
                np.mean([item.silent_feature_ratio for item in model_results])
            )
            aggregate[model_kind]["mean_saturated_feature_ratio"] = float(
                np.mean([item.saturated_feature_ratio for item in model_results])
            )
            aggregate[model_kind]["mean_head_synops_proxy_per_sample"] = float(
                np.mean([item.head_synops_proxy_per_sample for item in model_results])
            )
    if "ann" in aggregate and "snn" in aggregate:
        aggregate["snn_minus_ann"] = {
            key: aggregate["snn"]["subject_mean"][key]
            - aggregate["ann"]["subject_mean"][key]
            for key in ("accuracy", "macro_f1", "balanced_accuracy", "sensitivity", "specificity")
        }

    snn_rates = [item.mean_spike_rate for item in by_model["snn"]]
    smoke_gate = bool(snn_rates) and all(0.01 < float(rate) < 0.50 for rate in snn_rates)
    worth_continuing = None
    if not smoke and len(splits) == 11 and "snn_minus_ann" in aggregate:
        delta = aggregate["snn_minus_ann"]
        mean_rate = aggregate["snn"]["mean_spike_rate"]
        worth_continuing = bool(
            delta["accuracy"] >= -0.05
            and delta["macro_f1"] >= -0.05
            and 0.05 <= mean_rate <= 0.30
        )
    payload: dict[str, Any] = {
        "schema_version": 1,
        **repository_state(),
        "run_kind": "channel8_hybrid_snn_compatibility_pilot",
        "smoke": smoke,
        "seed": config.seed,
        "device": str(device),
        "numerical_dtype": config.dtype,
        "dataset_sha256": dataset.metadata.sha256,
        "order_kind": dataset.metadata.order_kind,
        "claim_boundary": "compatibility pilot; not chronological, causal, fixed-point, or hardware energy evidence",
        "fold_results": [item.to_dict() for item in results],
        "aggregate": aggregate,
    }
    write_json(run_dir / "metrics.json", payload)
    completion = {
        "complete": True,
        "folds_expected": len(splits),
        "fold_model_results_expected": len(splits) * 2,
        "fold_model_results_written": len(results),
        "finite": True,
        "smoke_gate_passed": smoke_gate,
        "worth_continuing": worth_continuing,
    }
    write_json(run_dir / "completion.json", completion)
    return {"metrics": payload, "completion": completion}
