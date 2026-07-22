from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("torch")

from dc_eeg.data import EEGDataset, EEGDatasetMetadata
from dc_eeg.metrics import BinaryMetrics
from dc_eeg.snn_pilot import (
    PilotFoldResult,
    SNNPilotConfig,
    _validate_result_matrix,
    validate_pilot_dataset,
)
from dc_eeg.splits import LosoSplit


EXPECTED_HASH = "a" * 64


def config_mapping() -> dict[str, object]:
    return {
        "dataset_path": "data.mat",
        "expected_dataset_sha256": EXPECTED_HASH,
        "results_root": "results/snn_pilot",
        "seed": 1,
        "epochs": 2,
        "smoke_epochs": 1,
        "learning_rate": 0.001,
        "train_batch_size": 4,
        "eval_batch_size": 8,
        "dtype": "float32",
        "model": {
            "sample_length": 384,
            "n1": 4,
            "depth_multiplier": 2,
            "kernel_length": 32,
            "temporal_steps": 8,
        },
        "snn": {
            "beta": 0.9,
            "threshold": 1.0,
            "surrogate_slope": 25.0,
            "current_scale": 1.0,
        },
        "spike_rate_regularization": 0.01,
        "target_spike_rate": 0.15,
    }


def test_snn_pilot_config_resolves_paths(tmp_path: Path):
    config = SNNPilotConfig.from_mapping(config_mapping(), tmp_path)

    assert config.dataset_path == (tmp_path / "data.mat").resolve()
    assert config.expected_dataset_sha256 == EXPECTED_HASH
    assert config.results_root == (tmp_path / "results/snn_pilot").resolve()
    assert config.model["temporal_steps"] == 8


def test_snn_pilot_config_rejects_invalid_target_rate(tmp_path: Path):
    raw = config_mapping()
    raw["target_spike_rate"] = 1.0

    with pytest.raises(ValueError, match="target_spike_rate"):
        SNNPilotConfig.from_mapping(raw, tmp_path)


def test_snn_pilot_config_rejects_missing_nested_keys(tmp_path: Path):
    raw = config_mapping()
    raw["snn"] = {"beta": 0.9}

    with pytest.raises(ValueError, match="nested config keys missing"):
        SNNPilotConfig.from_mapping(raw, tmp_path)


def test_pilot_dataset_validation_pins_hash_and_shape(tmp_path: Path):
    config = SNNPilotConfig.from_mapping(config_mapping(), tmp_path)
    metadata = EEGDatasetMetadata(
        source_path="fixture.mat",
        sha256=EXPECTED_HASH,
        samples=2022,
        channels=30,
        timepoints=384,
        labels={"alert": 1011, "drowsy": 1011},
        subjects=tuple(range(1, 12)),
        order_kind="class_blocked_compatibility",
    )
    dataset = EEGDataset(
        samples=np.empty((0, 30, 384)),
        labels=np.empty(0, dtype=np.int64),
        subject_ids=np.empty(0, dtype=np.int64),
        metadata=metadata,
    )

    validate_pilot_dataset(dataset, config)
    wrong = EEGDataset(
        samples=dataset.samples,
        labels=dataset.labels,
        subject_ids=dataset.subject_ids,
        metadata=EEGDatasetMetadata(**{**metadata.__dict__, "sha256": "b" * 64}),
    )
    with pytest.raises(ValueError, match="SHA-256"):
        validate_pilot_dataset(wrong, config)


def _fold_result(subject: int, model_kind: str) -> PilotFoldResult:
    metrics = BinaryMetrics(0.5, 0.5, 0.5, 0.5, 0.5, 2)
    return PilotFoldResult(
        held_out_subject=subject,
        model_kind=model_kind,
        metrics=metrics,
        checkpoint_identity="a" * 64,
        parameter_count=10,
        epochs=1,
        final_train_loss=1.0,
        mean_spike_rate=0.1 if model_kind == "snn" else None,
        silent_feature_ratio=0.2 if model_kind == "snn" else None,
        saturated_feature_ratio=0.0 if model_kind == "snn" else None,
        head_synops_proxy_per_sample=2.0 if model_kind == "snn" else None,
    )


def test_result_matrix_requires_one_ann_and_snn_per_fold():
    split = LosoSplit(1, np.array([1]), np.array([0]))
    complete = [_fold_result(1, "ann"), _fold_result(1, "snn")]

    _validate_result_matrix([split], complete)
    with pytest.raises(ValueError, match="matrix mismatch"):
        _validate_result_matrix([split], complete[:1])
