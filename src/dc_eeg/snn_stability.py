"""Resumable beta/threshold stability sweep for the Channel8 Hybrid-SNN pilot."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
import yaml

from .artifacts import write_json
from .data import EEGDataset, load_legacy_sadt_mat
from .experiment import repository_state, resolve_device
from .snn_pilot import (
    SNNPilotConfig,
    load_config as load_pilot_config,
    train_and_evaluate_pilot_fold,
    validate_pilot_dataset,
)
from .splits import iter_loso_splits


EXPECTED_CONFIG_IDS = ("S1", "S2", "S3", "S4")
STAGES = ("smoke", "screen-loso", "stability")


@dataclass(frozen=True)
class StabilityConfig:
    base_config_path: Path
    results_root: Path
    screen_seed: int
    stability_seeds: tuple[int, ...]
    smoke_fold: int
    smoke_epochs: int
    full_epochs: int
    configs: dict[str, dict[str, float]]
    max_selected_configs: int

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], repository_root: Path) -> "StabilityConfig":
        required = {
            "base_config",
            "results_root",
            "screen_seed",
            "stability_seeds",
            "smoke_fold",
            "smoke_epochs",
            "full_epochs",
            "configs",
            "max_selected_configs",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"stability config is missing keys: {missing}")
        configs_raw = raw["configs"]
        if not isinstance(configs_raw, dict):
            raise ValueError("configs must be a mapping")
        configs: dict[str, dict[str, float]] = {}
        for config_id, values in configs_raw.items():
            if not isinstance(values, dict) or set(values) != {"beta", "threshold"}:
                raise ValueError(f"config {config_id} must contain only beta and threshold")
            configs[str(config_id)] = {
                "beta": float(values["beta"]),
                "threshold": float(values["threshold"]),
            }
        if tuple(configs) != EXPECTED_CONFIG_IDS:
            raise ValueError(f"configs must be exactly {EXPECTED_CONFIG_IDS}")
        stability_seeds = tuple(int(seed) for seed in raw["stability_seeds"])
        config = cls(
            base_config_path=_resolve_path(str(raw["base_config"]), repository_root),
            results_root=_resolve_path(str(raw["results_root"]), repository_root),
            screen_seed=int(raw["screen_seed"]),
            stability_seeds=stability_seeds,
            smoke_fold=int(raw["smoke_fold"]),
            smoke_epochs=int(raw["smoke_epochs"]),
            full_epochs=int(raw["full_epochs"]),
            configs=configs,
            max_selected_configs=int(raw["max_selected_configs"]),
        )
        if len(config.stability_seeds) != 3 or len(set(config.stability_seeds)) != 3:
            raise ValueError("stability_seeds must contain exactly three unique seeds")
        if config.smoke_fold <= 0 or min(config.smoke_epochs, config.full_epochs) <= 0:
            raise ValueError("smoke_fold, smoke_epochs, and full_epochs must be positive")
        if config.max_selected_configs != 2:
            raise ValueError("max_selected_configs is frozen at 2")
        for config_id, values in config.configs.items():
            if not 0.0 <= values["beta"] < 1.0 or values["threshold"] <= 0:
                raise ValueError(f"invalid beta/threshold for {config_id}: {values}")
        return config

    def resolved(self) -> dict[str, Any]:
        return {
            "base_config": str(self.base_config_path),
            "results_root": str(self.results_root),
            "screen_seed": self.screen_seed,
            "stability_seeds": list(self.stability_seeds),
            "smoke_fold": self.smoke_fold,
            "smoke_epochs": self.smoke_epochs,
            "full_epochs": self.full_epochs,
            "configs": self.configs,
            "max_selected_configs": self.max_selected_configs,
        }


@dataclass(frozen=True)
class StabilityJob:
    stage: str
    config_id: str
    seed: int
    fold: int
    model_kind: str

    @property
    def job_id(self) -> str:
        return f"{self.stage}-{self.config_id}-seed{self.seed}-fold{self.fold}-{self.model_kind}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "stage": self.stage,
            "config_id": self.config_id,
            "seed": self.seed,
            "fold": self.fold,
            "model_kind": self.model_kind,
        }


def _resolve_path(value: str, repository_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (repository_root / path).resolve()


def load_stability_config(path: Path, repository_root: Path) -> StabilityConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"configuration must be a mapping: {path}")
    return StabilityConfig.from_mapping(raw, repository_root)


def _config_hash(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def make_run_id() -> str:
    return f"snn-stability-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _job_dir(run_dir: Path, job: StabilityJob) -> Path:
    return run_dir / "jobs" / job.job_id


def _write_manifest(run_dir: Path, payload: dict[str, Any]) -> None:
    write_json(run_dir / "job_manifest.json", payload)


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    return _read_json(run_dir / "job_manifest.json")


def prepare_run(
    run_dir: Path,
    stability: StabilityConfig,
    pilot: SNNPilotConfig,
    dataset: EEGDataset,
    device: torch.device,
    run_id: str,
) -> None:
    if run_dir.exists():
        raise FileExistsError(f"stability run already exists: {run_dir}; use --resume")
    run_dir.mkdir(parents=True)
    (run_dir / "jobs").mkdir()
    (run_dir / "resolved_sweep.yaml").write_text(
        yaml.safe_dump(stability.resolved(), sort_keys=False), encoding="utf-8"
    )
    write_json(
        run_dir / "dataset_manifest.json",
        {
            "source_path": dataset.metadata.source_path,
            "sha256": dataset.metadata.sha256,
            "samples": dataset.metadata.samples,
            "channels": dataset.metadata.channels,
            "timepoints": dataset.metadata.timepoints,
            "order_kind": dataset.metadata.order_kind,
            "selected_channels": [
                "C3",
                "Cz",
                "C4",
                "CP3",
                "CPz",
                "CP4",
                "Oz",
                "O2",
            ],
        },
    )
    base_resolved = pilot.resolved(pilot.epochs)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "base_config_hash": _config_hash(base_resolved),
        "dataset_sha256": dataset.metadata.sha256,
        "device": str(device),
        "jobs": {},
    }
    _write_manifest(run_dir, manifest)
    write_json(
        run_dir / "completion.json",
        {"run_id": run_id, "stages": {}, "complete": False, "failure": None},
    )


def _set_job_state(run_dir: Path, job: StabilityJob, **updates: Any) -> None:
    manifest = _load_manifest(run_dir)
    record = dict(manifest["jobs"].get(job.job_id, job.to_dict()))
    record.update(updates)
    manifest["jobs"][job.job_id] = record
    _write_manifest(run_dir, manifest)


def _job_is_complete(run_dir: Path, job: StabilityJob) -> bool:
    manifest = _load_manifest(run_dir)
    record = manifest["jobs"].get(job.job_id, {})
    return bool(record.get("state") == "complete" and (_job_dir(run_dir, job) / "metrics.json").is_file())


def _write_job_result(run_dir: Path, job: StabilityJob, result: dict[str, Any]) -> None:
    directory = _job_dir(run_dir, job)
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "metrics.json", result)
    _set_job_state(
        run_dir,
        job,
        state="complete",
        result_path=str(directory / "metrics.json"),
        failure=None,
    )


def _write_job_failure(run_dir: Path, job: StabilityJob, error: BaseException) -> None:
    directory = _job_dir(run_dir, job)
    directory.mkdir(parents=True, exist_ok=True)
    write_json(
        directory / "metrics.json",
        {"state": "failed", "failure": {"type": type(error).__name__, "message": str(error)}},
    )
    _set_job_state(
        run_dir,
        job,
        state="failed",
        result_path=str(directory / "metrics.json"),
        failure={"type": type(error).__name__, "message": str(error)},
    )


def _smoke_job_passes(run_dir: Path, job: StabilityJob) -> bool:
    if not _job_is_complete(run_dir, job):
        return False
    payload = _read_json(_job_dir(run_dir, job) / "metrics.json")
    result = payload["result"]
    rate = float(result["mean_spike_rate"])
    silent = float(result["silent_feature_ratio"])
    saturated = float(result["saturated_feature_ratio"])
    metrics = result["metrics"]
    return (
        all(np.isfinite(float(value)) for value in (rate, silent, saturated, metrics["accuracy"]))
        and 0.01 < rate < 0.50
        and silent < 0.80
        and saturated < 0.50
    )


def _load_complete_jobs(run_dir: Path, stage: str) -> list[dict[str, Any]]:
    manifest = _load_manifest(run_dir)
    payloads = []
    for job_id, record in manifest["jobs"].items():
        if record.get("stage") != stage or record.get("state") != "complete":
            continue
        path = Path(record["result_path"])
        if not path.is_file():
            continue
        payloads.append(_read_json(path))
    return payloads


def smoke_survivors(run_dir: Path, stability: StabilityConfig) -> list[str]:
    survivors = []
    for config_id in stability.configs:
        job = StabilityJob("smoke", config_id, stability.screen_seed, stability.smoke_fold, "snn")
        if _smoke_job_passes(run_dir, job):
            survivors.append(config_id)
    return survivors


def _mean_metric(results: Iterable[dict[str, Any]], metric: str) -> float:
    values = [float(item["result"]["metrics"][metric]) for item in results]
    if not values:
        raise ValueError("cannot aggregate an empty result set")
    return float(np.mean(values))


def rank_screen_configs(run_dir: Path, stability: StabilityConfig, survivors: list[str]) -> dict[str, Any]:
    jobs = _load_complete_jobs(run_dir, "screen-loso")
    ranked = []
    for config_id in survivors:
        selected = [item for item in jobs if item["config_id"] == config_id]
        if len(selected) != 11:
            continue
        mean_f1 = _mean_metric(selected, "macro_f1")
        rates = [float(item["result"]["mean_spike_rate"]) for item in selected]
        silent = [float(item["result"]["silent_feature_ratio"]) for item in selected]
        saturated = [float(item["result"]["saturated_feature_ratio"]) for item in selected]
        rate_ok = 0.05 <= float(np.mean(rates)) <= 0.30
        ranked.append(
            {
                "config_id": config_id,
                "complete_folds": len(selected),
                "mean_macro_f1": mean_f1,
                "subject_std_macro_f1": float(np.std([float(item["result"]["metrics"]["macro_f1"]) for item in selected])),
                "mean_spike_rate": float(np.mean(rates)),
                "mean_silent_feature_ratio": float(np.mean(silent)),
                "mean_saturated_feature_ratio": float(np.mean(saturated)),
                "rate_ok": rate_ok,
            }
        )
    ranked.sort(
        key=lambda item: (
            -int(item["rate_ok"]),
            -item["mean_macro_f1"],
            item["subject_std_macro_f1"],
            item["mean_spike_rate"],
            item["config_id"],
        )
    )
    selected = [item["config_id"] for item in ranked if item["rate_ok"]][: stability.max_selected_configs]
    payload = {
        "survivors": survivors,
        "ranked": ranked,
        "selected": selected,
        "selection_gate_passed": bool(selected),
    }
    write_json(run_dir / "selection.json", payload)
    return payload


def build_jobs(
    stage: str,
    stability: StabilityConfig,
    run_dir: Path,
    config_ids: list[str] | None = None,
) -> list[StabilityJob]:
    if stage not in STAGES:
        raise ValueError(f"unsupported stage: {stage}")
    ids = config_ids or list(stability.configs)
    if stage == "smoke":
        return [
            StabilityJob(stage, config_id, stability.screen_seed, stability.smoke_fold, "snn")
            for config_id in ids
        ]
    if stage == "screen-loso":
        return [
            StabilityJob(stage, config_id, stability.screen_seed, fold, "snn")
            for config_id in ids
            for fold in range(1, 12)
        ]
    selection = _read_json(run_dir / "selection.json")
    selected = list(selection.get("selected", []))
    return [
        StabilityJob(stage, config_id, seed, fold, model_kind)
        for config_id in selected
        for seed in stability.stability_seeds
        for fold in range(1, 12)
        for model_kind in ("ann", "snn")
    ]


def _job_pilot_config(
    pilot: SNNPilotConfig,
    stability: StabilityConfig,
    job: StabilityJob,
) -> SNNPilotConfig:
    values = stability.configs[job.config_id]
    snn = dict(pilot.snn)
    snn.update(values)
    return replace(
        pilot,
        seed=job.seed,
        epochs=stability.smoke_epochs if job.stage == "smoke" else stability.full_epochs,
        snn=snn,
    )


def execute_stage(
    run_dir: Path,
    stability: StabilityConfig,
    pilot: SNNPilotConfig,
    dataset: EEGDataset,
    device: torch.device,
    stage: str,
    config_ids: list[str] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    jobs = build_jobs(stage, stability, run_dir, config_ids)
    if not jobs:
        raise ValueError(f"no jobs planned for stage {stage}")
    for job in jobs:
        if resume and _job_is_complete(run_dir, job):
            continue
        _set_job_state(run_dir, job, state="running", started_at=datetime.now(UTC).isoformat())
        try:
            split = iter_loso_splits(dataset.subject_ids, fold=job.fold)[0]
            job_config = _job_pilot_config(pilot, stability, job)
            result = train_and_evaluate_pilot_fold(
                dataset,
                split,
                job_config,
                device,
                job.model_kind,
                job_config.epochs,
            )
            _write_job_result(
                run_dir,
                job,
                {
                    **job.to_dict(),
                    "config": stability.configs[job.config_id],
                    "result": result.to_dict(),
                    "dataset_sha256": dataset.metadata.sha256,
                    "git": repository_state(),
                },
            )
        except BaseException as error:
            _write_job_failure(run_dir, job, error)
            raise
    summary = {"stage": stage, "planned_jobs": len(jobs), "complete_jobs": len([job for job in jobs if _job_is_complete(run_dir, job)])}
    completion = _read_json(run_dir / "completion.json")
    completion["stages"][stage] = summary
    write_json(run_dir / "completion.json", completion)
    return summary


def stability_summary(run_dir: Path, stability: StabilityConfig) -> dict[str, Any]:
    selection = _read_json(run_dir / "selection.json")
    selected = list(selection.get("selected", []))
    jobs = _load_complete_jobs(run_dir, "stability")
    by_pair: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for job in jobs:
        key = (str(job["config_id"]), int(job["seed"]), str(job["model_kind"]))
        by_pair.setdefault(key, []).append(job)
    pair_summary = []
    for config_id in selected:
        for seed in stability.stability_seeds:
            ann = by_pair.get((config_id, seed, "ann"), [])
            snn = by_pair.get((config_id, seed, "snn"), [])
            if len(ann) != 11 or len(snn) != 11:
                continue
            ann_acc = _mean_metric(ann, "accuracy")
            snn_acc = _mean_metric(snn, "accuracy")
            ann_f1 = _mean_metric(ann, "macro_f1")
            snn_f1 = _mean_metric(snn, "macro_f1")
            pair_summary.append(
                {
                    "config_id": config_id,
                    "seed": seed,
                    "ann_accuracy": ann_acc,
                    "snn_accuracy": snn_acc,
                    "accuracy_delta": snn_acc - ann_acc,
                    "ann_macro_f1": ann_f1,
                    "snn_macro_f1": snn_f1,
                    "macro_f1_delta": snn_f1 - ann_f1,
                    "mean_spike_rate": float(np.mean([item["result"]["mean_spike_rate"] for item in snn])),
                }
            )
    configs = {}
    for config_id in selected:
        rows = [row for row in pair_summary if row["config_id"] == config_id]
        if len(rows) != 3:
            continue
        configs[config_id] = {
            "seeds": rows,
            "mean_accuracy_delta": float(np.mean([row["accuracy_delta"] for row in rows])),
            "std_accuracy_delta": float(np.std([row["accuracy_delta"] for row in rows])),
            "mean_macro_f1_delta": float(np.mean([row["macro_f1_delta"] for row in rows])),
            "std_macro_f1_delta": float(np.std([row["macro_f1_delta"] for row in rows])),
            "mean_spike_rate": float(np.mean([row["mean_spike_rate"] for row in rows])),
            "all_rates_ok": all(0.05 <= row["mean_spike_rate"] <= 0.30 for row in rows),
        }
    passed = any(
        row["all_rates_ok"]
        and row["mean_accuracy_delta"] >= -0.05
        and row["mean_macro_f1_delta"] >= -0.05
        for row in configs.values()
    )
    payload = {
        "selected": selected,
        "pair_summary": pair_summary,
        "configs": configs,
        "snn1_gate_passed": passed,
        "next_task": "snn-encoding-comparison" if passed else None,
    }
    write_json(run_dir / "aggregate.json", payload)
    completion = _read_json(run_dir / "completion.json")
    completion["complete"] = bool(configs) and len(pair_summary) == len(selected) * 3
    completion["snn1_gate_passed"] = passed
    write_json(run_dir / "completion.json", completion)
    return payload


def load_dataset_and_pilot(
    stability: StabilityConfig, repository_root: Path
) -> tuple[SNNPilotConfig, EEGDataset]:
    pilot = load_pilot_config(stability.base_config_path, repository_root)
    dataset = load_legacy_sadt_mat(pilot.dataset_path)
    validate_pilot_dataset(dataset, pilot)
    return pilot, dataset


def resolve_run_directory(stability: StabilityConfig, run_id: str) -> Path:
    return stability.results_root / run_id


def resolve_device_for_cli(requested: str) -> torch.device:
    return resolve_device(requested)
