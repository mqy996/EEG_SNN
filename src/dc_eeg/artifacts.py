"""Structured, JSON-safe run artifacts for reproducible experiments."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def state_dict_sha256(model: Any) -> str:
    """Hash model parameters without serializing a framework-specific checkpoint."""

    digest = sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def validate_run_artifacts(
    resolved_config: dict[str, Any],
    dataset_manifest: dict[str, Any],
    split_manifest: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    """Reject incomplete artifacts before any claimed result is written."""

    required_config = {
        "dataset_path", "seed", "normalization_mode", "dtype", "replay_information_boundary", "model"
    }
    required_dataset = {"sha256", "samples", "channels", "timepoints", "order_kind"}
    required_split = {"protocol", "folds"}
    required_metrics = {
        "schema_version", "git_revision", "git_dirty", "run_kind", "seed", "split_protocol", "replay_information_boundary", "device", "numerical_dtype",
        "normalization_mode", "dataset_sha256", "fold_results", "aggregate"
    }
    for name, payload, required in (
        ("resolved_config", resolved_config, required_config),
        ("dataset_manifest", dataset_manifest, required_dataset),
        ("split_manifest", split_manifest, required_split),
        ("metrics", metrics, required_metrics),
    ):
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"{name} is missing required keys: {missing}")
    if dataset_manifest["order_kind"] == "class_blocked_compatibility":
        boundary = str(metrics["replay_information_boundary"])
        if "chronological" in boundary:
            raise ValueError("class-blocked legacy data cannot be labeled chronological replay")
    if metrics["dataset_sha256"] != dataset_manifest["sha256"]:
        raise ValueError("metrics dataset hash does not match dataset manifest")
    if len(metrics["fold_results"]) != len(split_manifest["folds"]):
        raise ValueError("metrics fold count does not match split manifest")
