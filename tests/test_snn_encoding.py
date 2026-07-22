from pathlib import Path

import pytest

pytest.importorskip("torch")
import torch

from dc_eeg.snn_encoders import (
    AmplitudeCountEncoder,
    Channel8EncodedSNN,
    DeltaEncoder,
    DirectCurrentEncoder,
)
from dc_eeg.snn_encoding import ENCODERS, EncodingConfig


def test_direct_current_is_identity_and_stateless():
    current = torch.tensor([[[0.2, -0.7, 1.1]]])
    encoded, event_rate = DirectCurrentEncoder()(current)

    assert torch.equal(encoded, current)
    assert torch.isnan(event_rate)
    assert DirectCurrentEncoder.state_bytes == 0


def test_amplitude_count_is_deterministic_signed_and_stateless():
    current = torch.tensor([[[0.6, -0.6, 0.1]]])
    encoder = AmplitudeCountEncoder(threshold=0.5)
    encoded, event_rate = encoder(current)

    assert torch.equal(encoded, torch.tensor([[[1.0, -1.0, 0.0]]]))
    assert event_rate.item() == pytest.approx(2 / 3)
    assert encoder.state_bytes == 0


def test_delta_encoder_is_causal_signed_and_resets_each_forward():
    current = torch.tensor([[[0.6, -0.6, 0.4, -0.6]]])
    encoder = DeltaEncoder(threshold=0.5)
    first, first_rate = encoder(current)
    second, second_rate = encoder(current)

    expected = torch.tensor([[[1.0, -1.0, 0.0, -1.0]]])
    assert torch.equal(first, expected)
    assert torch.equal(second, expected)
    assert first_rate.item() == pytest.approx(3 / 4)
    assert second_rate.item() == pytest.approx(3 / 4)
    assert encoder.state_bytes == 4


def test_encoded_channel8_snn_preserves_matched_output_contract():
    x = torch.randn(2, 1, 8, 32)
    for name in ENCODERS:
        model = Channel8EncodedSNN(
            encoder=name,
            encoder_threshold=0.5,
            beta=0.9,
            threshold=0.5,
            channels=8,
            sample_length=32,
            n1=4,
            depth_multiplier=2,
            kernel_length=8,
            temporal_steps=4,
        )
        output = model(x)

        assert output.logits.shape == (2, 2)
        assert output.spike_counts.shape == (2, 8)
        assert output.timesteps == 4
        assert torch.isfinite(output.mean_spike_rate)
        assert output.encoder_ops_proxy_per_sample > 0


def encoding_mapping() -> dict[str, object]:
    return {
        "base_config": "pilot.yaml",
        "results_root": "results/encoding",
        "beta": 0.9,
        "threshold": 0.5,
        "encoder_threshold": 0.5,
        "seed": 20260717,
        "smoke_epochs": 3,
        "full_epochs": 11,
        "train_batch_size": 50,
        "eval_batch_size": 256,
        "target_spike_rate": 0.15,
        "spike_rate_regularization": 0.01,
        "encoders": list(ENCODERS),
    }


def test_encoding_config_freezes_exact_three_encoder_matrix(tmp_path: Path):
    config = EncodingConfig.from_mapping(encoding_mapping(), tmp_path)

    assert config.encoders == ENCODERS
    assert config.beta == pytest.approx(0.9)


def test_encoding_config_rejects_encoder_matrix_growth(tmp_path: Path):
    raw = encoding_mapping()
    raw["encoders"] = [*ENCODERS, "poisson"]

    with pytest.raises(ValueError, match="exactly"):
        EncodingConfig.from_mapping(raw, tmp_path)
