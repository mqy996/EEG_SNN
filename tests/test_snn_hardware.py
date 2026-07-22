from pathlib import Path

import pytest

pytest.importorskip("torch")
import torch

from dc_eeg.snn_hardware import FixedPointConfig, HardwareConfig, fixed_lif_head, quantize


def test_fixed_point_config_and_saturation():
    config = FixedPointConfig(total_bits=8, frac_bits=4)
    values, saturation = quantize(torch.tensor([-20.0, 0.25, 20.0]), config)

    assert values.tolist() == [-128, 4, 127]
    assert saturation.item() == pytest.approx(2 / 3)


def test_fixed_lif_head_is_finite_and_preserves_shapes():
    config = FixedPointConfig(total_bits=16, frac_bits=8)
    currents = torch.tensor([[[0.6, 0.0, 0.6], [-0.6, 0.0, -0.6]]], dtype=torch.float64)
    weight = torch.tensor([[1.0, -1.0], [-1.0, 1.0]], dtype=torch.float64)
    bias = torch.zeros(2, dtype=torch.float64)
    logits, counts, saturation = fixed_lif_head(currents, weight, bias, 0.9, 0.5, config)

    assert logits.shape == (1, 2)
    assert counts.shape == (1, 2)
    assert torch.isfinite(logits).all()
    assert set(saturation) == {"current", "weight", "bias", "beta", "threshold"}


def test_hardware_config_rejects_unfrozen_target_or_input_contract(tmp_path: Path):
    raw = {
        "base_config": "pilot.yaml",
        "results_root": "results",
        "seed": 1,
        "fold": 2,
        "epochs": 1,
        "train_batch_size": 2,
        "eval_batch_size": 2,
        "target_part": "xc7z020clg400-1",
        "clock_mhz": 100,
        "input_format": "float_current",
        "fixed_points": [{"total_bits": 8, "frac_bits": 4}],
    }
    with pytest.raises(ValueError, match="input_format"):
        HardwareConfig.from_mapping(raw, tmp_path)

    raw["input_format"] = "feature_current_q"
    raw["target_part"] = "xc7z010clg400-1"
    with pytest.raises(ValueError, match="target_part"):
        HardwareConfig.from_mapping(raw, tmp_path)
