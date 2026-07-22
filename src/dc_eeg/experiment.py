"""Artifact contracts and deterministic training helpers for Channel8 LOSO runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import random
from typing import Any

import numpy as np
import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset

from .artifacts import state_dict_sha256, validate_run_artifacts, write_json
from .data import CHANNEL8_INDICES, CHANNEL8_NAMES, EEGDataset, select_channels
from .metrics import BinaryMetrics, aggregate_subject_metrics, binary_metrics
from .models import Channel8CompactCNN
from .splits import LosoSplit, split_manifest


@dataclass(frozen=True)
class Channel8RunConfig:
    dataset_path: Path
    results_root: Path
    seed: int
    epochs: int
    learning_rate: float
    train_batch_size: int
    eval_batch_size: int | None
    normalization_mode: str
    dtype: str
    replay_information_boundary: str
    model: dict[str, int | str]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], repo_root: Path) -> "Channel8RunConfig":
        required = {
            "dataset_path",
            "results_root",
            "seed",
            "epochs",
            "learning_rate",
            "train_batch_size",
            "normalization_mode",
            "dtype",
            "replay_information_boundary",
            "model",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"Channel8 config is missing keys: {missing}")
        model = raw["model"]
        if not isinstance(model, dict):
            raise ValueError("model must be a mapping")
        dataset_path = _resolve_path(str(raw["dataset_path"]), repo_root)
        results_root = _resolve_path(str(raw["results_root"]), repo_root)
        eval_raw = raw.get("eval_batch_size", "full")
        eval_batch_size = None if eval_raw == "full" else int(eval_raw)
        config = cls(
            dataset_path=dataset_path,
            results_root=results_root,
            seed=int(raw["seed"]),
            epochs=int(raw["epochs"]),
            learning_rate=float(raw["learning_rate"]),
            train_batch_size=int(raw["train_batch_size"]),
            eval_batch_size=eval_batch_size,
            normalization_mode=str(raw["normalization_mode"]),
            dtype=str(raw["dtype"]),
            replay_information_boundary=str(raw["replay_information_boundary"]),
            model={str(key): value for key, value in model.items()},
        )
        if config.epochs <= 0 or config.train_batch_size <= 0 or config.learning_rate <= 0:
            raise ValueError("epochs, train_batch_size, and learning_rate must be positive")
        if config.eval_batch_size is not None and config.eval_batch_size <= 0:
            raise ValueError("eval_batch_size must be a positive integer or 'full'")
        if config.dtype != "float64":
            raise ValueError("the initial compatibility reference must use dtype=float64")
        if config.normalization_mode != config.model.get("norm_mode"):
            raise ValueError("normalization_mode must match model.norm_mode")
        return config

    def as_resolved_mapping(self) -> dict[str, Any]:
        return {
            "dataset_path": str(self.dataset_path),
            "results_root": str(self.results_root),
            "seed": self.seed,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "train_batch_size": self.train_batch_size,
            "eval_batch_size": "full" if self.eval_batch_size is None else self.eval_batch_size,
            "normalization_mode": self.normalization_mode,
            "dtype": self.dtype,
            "replay_information_boundary": self.replay_information_boundary,
            "model": self.model,
        }


@dataclass(frozen=True)
class FoldResult:
    held_out_subject: int
    metrics: BinaryMetrics
    checkpoint_identity: str
    epochs: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "held_out_subject": self.held_out_subject,
            "metrics": self.metrics.to_dict(),
            "checkpoint_identity": self.checkpoint_identity,
            "epochs": self.epochs,
        }


def _resolve_path(value: str, repo_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def set_deterministic_seed(seed: int) -> None:
    """Set all local random sources used by the initial sequential LOSO runner."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def torch_dtype(name: str) -> torch.dtype:
    if name == "float64":
        return torch.float64
    if name == "float32":
        return torch.float32
    raise ValueError(f"unsupported numerical dtype: {name}")


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        requested = "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable in this environment")
    if requested not in {"cpu", "cuda"}:
        raise ValueError("device must be one of: auto, cpu, cuda")
    return torch.device(requested)


def build_channel8_model(config: Channel8RunConfig, dtype: torch.dtype, device: torch.device) -> Channel8CompactCNN:
    model = Channel8CompactCNN(
        channels=len(CHANNEL8_NAMES),
        classes=int(config.model.get("classes", 2)),
        sample_length=int(config.model.get("sample_length", 384)),
        n1=int(config.model.get("n1", 16)),
        depth_multiplier=int(config.model.get("depth_multiplier", 2)),
        kernel_length=int(config.model.get("kernel_length", 32)),
        norm_mode=str(config.model["norm_mode"]),
    )
    return model.to(device=device, dtype=dtype)


def _loader(
    samples: np.ndarray,
    labels: np.ndarray,
    batch_size: int,
    shuffle: bool,
    dtype: torch.dtype,
    seed: int,
) -> DataLoader[tuple[Tensor, Tensor]]:
    inputs = torch.from_numpy(np.ascontiguousarray(samples[:, None, :, :])).to(dtype=dtype)
    targets = torch.from_numpy(np.ascontiguousarray(labels.astype(np.int64, copy=False)))
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        TensorDataset(inputs, targets),
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
    )


def train_and_evaluate_fold(
    dataset: EEGDataset,
    split: LosoSplit,
    config: Channel8RunConfig,
    device: torch.device,
) -> FoldResult:
    """Train one subject-independent fold and evaluate the explicit compatibility protocol."""

    dtype = torch_dtype(config.dtype)
    set_deterministic_seed(config.seed + split.held_out_subject)
    samples = select_channels(dataset.samples, CHANNEL8_INDICES)
    model = build_channel8_model(config, dtype, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_function = nn.CrossEntropyLoss()
    train_loader = _loader(
        samples[split.train_indices],
        dataset.labels[split.train_indices],
        config.train_batch_size,
        True,
        dtype,
        config.seed + split.held_out_subject,
    )
    model.train()
    for _ in range(config.epochs):
        for inputs, targets in train_loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs.to(device=device, non_blocking=True))
            loss = loss_function(logits, targets.to(device=device, non_blocking=True))
            loss.backward()
            optimizer.step()

    test_samples = samples[split.test_indices]
    test_labels = dataset.labels[split.test_indices]
    # Dynamic BN must receive the complete held-out subject here. This is an
    # explicit full-batch compatibility evaluation, not an online replay claim.
    eval_batch_size = config.eval_batch_size or len(test_samples)
    test_loader = _loader(
        test_samples,
        test_labels,
        eval_batch_size,
        False,
        dtype,
        config.seed + split.held_out_subject,
    )
    predictions: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for inputs, _ in test_loader:
            logits = model(inputs.to(device=device, non_blocking=True))
            predictions.append(logits.argmax(dim=1).cpu().numpy())
    prediction_array = np.concatenate(predictions)
    return FoldResult(
        held_out_subject=split.held_out_subject,
        metrics=binary_metrics(test_labels, prediction_array),
        checkpoint_identity=state_dict_sha256(model),
        epochs=config.epochs,
    )


def repository_state() -> dict[str, object]:
    """Capture the q1 repository revision without making Git a runtime dependency."""

    repository_root = Path(__file__).resolve().parents[2]
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=repository_root, text=True, stderr=subprocess.DEVNULL
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return {"git_revision": "unavailable", "git_dirty": None}
    return {"git_revision": revision, "git_dirty": dirty}

def make_run_id(seed: int) -> str:
    return f"channel8-compat-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-seed{seed}"


def dataset_manifest(dataset: EEGDataset) -> dict[str, Any]:
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


def create_run_directory(config: Channel8RunConfig, run_id: str) -> Path:
    run_dir = config.results_root / run_id
    if run_dir.exists():
        raise FileExistsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    return run_dir


def write_run_artifacts(
    run_dir: Path,
    config: Channel8RunConfig,
    dataset: EEGDataset,
    splits: list[LosoSplit],
    device: torch.device,
    results: list[FoldResult],
) -> dict[str, Any]:
    """Persist the schema-checked audit trail for an executed compatibility run."""

    import yaml

    resolved = config.as_resolved_mapping()
    (run_dir / "resolved_config.yaml").write_text(
        yaml.safe_dump(resolved, sort_keys=False), encoding="utf-8"
    )
    manifest = dataset_manifest(dataset)
    write_json(run_dir / "dataset_manifest.json", manifest)
    split_payload = split_manifest(splits, dataset.subject_ids)
    write_json(run_dir / "split_manifest.json", split_payload)
    subject_metrics = [item.metrics for item in results]
    metrics_payload: dict[str, Any] = {
        "schema_version": 1,
        **repository_state(),
        "run_kind": "channel8_full_batch_compatibility",
        "seed": config.seed,
        "split_protocol": "leave_one_subject_out",
        "replay_information_boundary": config.replay_information_boundary,
        "device": str(device),
        "numerical_dtype": config.dtype,
        "normalization_mode": config.normalization_mode,
        "dataset_sha256": dataset.metadata.sha256,
        "fold_results": [item.to_dict() for item in results],
        "aggregate": aggregate_subject_metrics(subject_metrics),
    }
    validate_run_artifacts(resolved, manifest, split_payload, metrics_payload)
    write_json(run_dir / "metrics.json", metrics_payload)
    return metrics_payload
