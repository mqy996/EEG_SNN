from pathlib import Path

import pytest

pytest.importorskip("torch")

from dc_eeg.snn_stability import (
    EXPECTED_CONFIG_IDS,
    StabilityConfig,
    StabilityJob,
    build_jobs,
)


def stability_mapping() -> dict[str, object]:
    return {
        "base_config": "pilot.yaml",
        "results_root": "results/stability",
        "screen_seed": 20260717,
        "stability_seeds": [20260717, 20260718, 20260719],
        "smoke_fold": 2,
        "smoke_epochs": 3,
        "full_epochs": 11,
        "max_selected_configs": 2,
        "configs": {
            "S1": {"beta": 0.9, "threshold": 1.0},
            "S2": {"beta": 0.9, "threshold": 0.5},
            "S3": {"beta": 0.9, "threshold": 1.5},
            "S4": {"beta": 0.95, "threshold": 1.0},
        },
    }


def test_stability_config_freezes_exact_matrix(tmp_path: Path):
    config = StabilityConfig.from_mapping(stability_mapping(), tmp_path)

    assert tuple(config.configs) == EXPECTED_CONFIG_IDS
    assert config.max_selected_configs == 2
    assert config.stability_seeds == (20260717, 20260718, 20260719)


def test_stability_config_rejects_matrix_growth(tmp_path: Path):
    raw = stability_mapping()
    raw["configs"] = dict(raw["configs"])
    raw["configs"]["S5"] = {"beta": 0.9, "threshold": 0.8}

    with pytest.raises(ValueError, match="exactly"):
        StabilityConfig.from_mapping(raw, tmp_path)


def test_stability_job_ids_are_unique_and_stage_counts_are_frozen(tmp_path: Path):
    config = StabilityConfig.from_mapping(stability_mapping(), tmp_path)

    smoke = build_jobs("smoke", config, tmp_path / "missing")
    screen = build_jobs("screen-loso", config, tmp_path / "missing")

    assert len(smoke) == 4
    assert len(screen) == 44
    assert len({job.job_id for job in smoke + screen}) == 48
    assert StabilityJob("smoke", "S1", 20260717, 2, "snn").job_id.endswith("-snn")
