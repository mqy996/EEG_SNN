import pytest

pytest.importorskip("torch")
import torch

from dc_eeg.snn_models import Channel8HybridSNN, Channel8PilotANN


def test_hybrid_snn_shape_stats_and_reset_determinism():
    torch.manual_seed(7)
    model = Channel8HybridSNN(temporal_steps=12).double().eval()
    inputs = torch.randn(3, 1, 8, 384, dtype=torch.float64)

    first = model(inputs)
    second = model(inputs)

    assert first.logits.shape == (3, 2)
    assert first.spike_counts.shape == (3, 32)
    assert first.timesteps == 12
    assert 0.0 <= float(first.mean_spike_rate.detach()) <= 1.0
    assert torch.equal(first.spike_counts, second.spike_counts)
    assert torch.equal(first.logits, second.logits)


def test_matched_frontends_start_from_identical_weights():
    torch.manual_seed(11)
    ann = Channel8PilotANN(temporal_steps=8)
    torch.manual_seed(11)
    snn = Channel8HybridSNN(temporal_steps=8)

    assert torch.equal(ann.features.pointwise.weight, snn.features.pointwise.weight)
    assert torch.equal(ann.features.depthwise.weight, snn.features.depthwise.weight)


def test_hybrid_snn_backward_is_finite():
    model = Channel8HybridSNN(temporal_steps=8)
    output = model(torch.randn(2, 1, 8, 384))
    loss = output.logits.square().mean() + output.mean_spike_rate
    loss.backward()

    gradients = [parameter.grad for parameter in model.parameters() if parameter.grad is not None]
    assert gradients
    assert all(torch.isfinite(gradient).all() for gradient in gradients)


def test_hybrid_snn_rejects_invalid_parameters_and_shape():
    with pytest.raises(ValueError, match="beta"):
        Channel8HybridSNN(beta=1.0)
    model = Channel8HybridSNN(temporal_steps=8)
    with pytest.raises(ValueError, match="expected input shape"):
        model(torch.randn(1, 1, 30, 384))
