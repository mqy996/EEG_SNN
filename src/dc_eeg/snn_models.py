"""Pure-PyTorch spiking models for the Channel8 exploratory pilot."""

from __future__ import annotations

from typing import NamedTuple

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from .data import CHANNEL8_NAMES


class SNNForwardResult(NamedTuple):
    logits: Tensor
    spike_counts: Tensor
    timesteps: int
    mean_spike_rate: Tensor


class _FastSigmoidSpike(torch.autograd.Function):
    @staticmethod
    def forward(ctx: object, membrane_minus_threshold: Tensor, slope: float) -> Tensor:
        ctx.save_for_backward(membrane_minus_threshold)  # type: ignore[attr-defined]
        ctx.slope = slope  # type: ignore[attr-defined]
        return (membrane_minus_threshold >= 0).to(membrane_minus_threshold.dtype)

    @staticmethod
    def backward(ctx: object, grad_output: Tensor) -> tuple[Tensor, None]:
        (delta,) = ctx.saved_tensors  # type: ignore[attr-defined]
        slope = ctx.slope  # type: ignore[attr-defined]
        surrogate = 1.0 / (1.0 + slope * delta.abs()).pow(2)
        return grad_output * surrogate, None


def surrogate_spike(value: Tensor, slope: float) -> Tensor:
    return _FastSigmoidSpike.apply(value, slope)


def _group_count(channels: int) -> int:
    return max(group for group in range(1, min(16, channels) + 1) if channels % group == 0)


class Channel8FeatureExtractor(nn.Module):
    """Matched convolutional front end shared by the ANN and SNN pilot."""

    def __init__(
        self,
        channels: int = len(CHANNEL8_NAMES),
        sample_length: int = 384,
        n1: int = 16,
        depth_multiplier: int = 2,
        kernel_length: int = 32,
        temporal_steps: int = 48,
    ) -> None:
        super().__init__()
        if channels <= 0 or n1 <= 0 or depth_multiplier <= 0:
            raise ValueError("channels, n1, and depth_multiplier must be positive")
        if kernel_length <= 0 or kernel_length > sample_length:
            raise ValueError("kernel_length must be in [1, sample_length]")
        output_steps = sample_length - kernel_length + 1
        if temporal_steps <= 0 or temporal_steps > output_steps:
            raise ValueError(f"temporal_steps must be in [1, {output_steps}]")

        feature_channels = n1 * depth_multiplier
        self.channels = channels
        self.sample_length = sample_length
        self.temporal_steps = temporal_steps
        self.feature_channels = feature_channels
        self.pointwise = nn.Conv2d(1, n1, (channels, 1))
        self.depthwise = nn.Conv2d(
            n1,
            feature_channels,
            (1, kernel_length),
            groups=n1,
        )
        self.activation = nn.ReLU()
        self.normalization = nn.GroupNorm(
            num_groups=_group_count(feature_channels),
            num_channels=feature_channels,
        )

    def forward(self, x: Tensor) -> Tensor:
        if x.ndim != 4 or x.shape[1:] != (1, self.channels, self.sample_length):
            raise ValueError(
                "expected input shape "
                f"[B, 1, {self.channels}, {self.sample_length}], got {tuple(x.shape)}"
            )
        features = self.pointwise(x)
        features = self.depthwise(features)
        features = self.activation(features)
        features = self.normalization(features)
        features = features.squeeze(2)
        return F.adaptive_avg_pool1d(features, self.temporal_steps)


class Channel8PilotANN(nn.Module):
    """Matched non-spiking control for the Hybrid-SNN pilot."""

    def __init__(self, classes: int = 2, **feature_kwargs: int) -> None:
        super().__init__()
        if classes <= 1:
            raise ValueError("classes must exceed one")
        self.features = Channel8FeatureExtractor(**feature_kwargs)
        self.classifier = nn.Linear(self.features.feature_channels, classes)

    def forward(self, x: Tensor) -> Tensor:
        features = self.features(x).mean(dim=-1)
        return self.classifier(features)


class Channel8HybridSNN(nn.Module):
    """CNN front end with a deterministic subtract-reset LIF readout."""

    def __init__(
        self,
        classes: int = 2,
        beta: float = 0.9,
        threshold: float = 1.0,
        surrogate_slope: float = 25.0,
        current_scale: float = 1.0,
        **feature_kwargs: int,
    ) -> None:
        super().__init__()
        if classes <= 1:
            raise ValueError("classes must exceed one")
        if not 0.0 <= beta < 1.0:
            raise ValueError("beta must be in [0, 1)")
        if threshold <= 0 or surrogate_slope <= 0 or current_scale <= 0:
            raise ValueError("threshold, surrogate_slope, and current_scale must be positive")
        self.features = Channel8FeatureExtractor(**feature_kwargs)
        self.classifier = nn.Linear(self.features.feature_channels, classes)
        self.beta = float(beta)
        self.threshold = float(threshold)
        self.surrogate_slope = float(surrogate_slope)
        self.current_scale = float(current_scale)

    def forward(self, x: Tensor) -> SNNForwardResult:
        currents = self.features(x) * self.current_scale
        membrane = torch.zeros_like(currents[:, :, 0])
        spike_counts = torch.zeros_like(membrane)
        for step in range(currents.shape[-1]):
            membrane = self.beta * membrane + currents[:, :, step]
            spikes = surrogate_spike(membrane - self.threshold, self.surrogate_slope)
            membrane = membrane - spikes.detach() * self.threshold
            spike_counts = spike_counts + spikes
        rates = spike_counts / currents.shape[-1]
        logits = self.classifier(rates)
        return SNNForwardResult(
            logits=logits,
            spike_counts=spike_counts,
            timesteps=int(currents.shape[-1]),
            mean_spike_rate=rates.mean(),
        )
