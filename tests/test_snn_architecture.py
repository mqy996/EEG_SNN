from pathlib import Path

import pytest

pytest.importorskip("torch")
import torch

from dc_eeg.snn_architecture import ARCHITECTURES, ArchitectureConfig, SpikingTemporalBlock, build_architecture
from dc_eeg.snn_pilot import SNNPilotConfig


def architecture_mapping() -> dict[str, object]:
    return {
        "base_config": "pilot.yaml",
        "results_root": "results/architecture",
        "beta": 0.9,
        "threshold": 0.5,
        "seed": 20260717,
        "smoke_epochs": 3,
        "full_epochs": 11,
        "train_batch_size": 50,
        "eval_batch_size": 256,
        "target_spike_rate": 0.15,
        "spike_rate_regularization": 0.01,
        "temporal_kernel": 3,
        "architectures": list(ARCHITECTURES),
    }


def test_architecture_config_freezes_exact_variants(tmp_path: Path):
    config = ArchitectureConfig.from_mapping(architecture_mapping(), tmp_path)
    assert config.architectures == ARCHITECTURES
    assert config.temporal_kernel == 3


def test_architecture_config_rejects_extra_variant(tmp_path: Path):
    raw = architecture_mapping()
    raw["architectures"] = [*ARCHITECTURES, "attention"]
    with pytest.raises(ValueError, match="exactly"):
        ArchitectureConfig.from_mapping(raw, tmp_path)


def test_spiking_temporal_block_preserves_output_contract():
    model = SpikingTemporalBlock(
        channels=8,
        sample_length=32,
        n1=4,
        depth_multiplier=2,
        kernel_length=8,
        temporal_steps=4,
        temporal_kernel=3,
    )
    output = model(torch.randn(2, 1, 8, 32))
    assert output.logits.shape == (2, 2)
    assert output.spike_counts.shape == (2, 8)
    assert output.timesteps == 4
    assert torch.isfinite(output.mean_spike_rate)
    assert output.ops_proxy_per_sample == pytest.approx(8 * 4 * 4)


def test_all_architectures_build_from_pilot_config(tmp_path: Path):
    raw = {
        "dataset_path": "dataset.mat",
        "expected_dataset_sha256": "0" * 64,
        "results_root": "results",
        "seed": 1,
        "epochs": 1,
        "smoke_epochs": 1,
        "learning_rate": 0.001,
        "train_batch_size": 2,
        "eval_batch_size": 2,
        "dtype": "float32",
        "model": {"sample_length": 32, "n1": 4, "depth_multiplier": 2, "kernel_length": 8, "temporal_steps": 4},
        "snn": {"beta": 0.9, "threshold": 0.5, "surrogate_slope": 25.0, "current_scale": 1.0},
        "spike_rate_regularization": 0.01,
        "target_spike_rate": 0.15,
    }
    pilot = SNNPilotConfig.from_mapping(raw, tmp_path)
    config = ArchitectureConfig.from_mapping(architecture_mapping(), tmp_path)
    for name in ARCHITECTURES:
        model = build_architecture(name, pilot, config)
        assert sum(parameter.numel() for parameter in model.parameters()) > 0
