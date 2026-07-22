"""Deterministic input encoders and a matched encoded Channel8 SNN."""

from __future__ import annotations

from typing import NamedTuple

import torch
from torch import Tensor, nn

from .snn_models import Channel8FeatureExtractor, surrogate_spike


class EncodedSNNOutput(NamedTuple):
    logits: Tensor
    spike_counts: Tensor
    timesteps: int
    mean_spike_rate: Tensor
    input_event_rate: Tensor
    encoder_state_bytes: int
    encoder_ops_proxy_per_sample: float


class DirectCurrentEncoder(nn.Module):
    state_bytes = 0
    ops_per_value = 1.0

    def forward(self, current: Tensor) -> tuple[Tensor, Tensor]:
        return current, torch.full((), float("nan"), device=current.device, dtype=current.dtype)


class AmplitudeCountEncoder(nn.Module):
    """Deterministic signed threshold events from the current value only."""

    def __init__(self, threshold: float = 0.5) -> None:
        super().__init__()
        if threshold <= 0:
            raise ValueError("amplitude threshold must be positive")
        self.threshold = float(threshold)
        self.state_bytes = 0
        self.ops_per_value = 3.0

    def forward(self, current: Tensor) -> tuple[Tensor, Tensor]:
        bounded = torch.tanh(current)
        events = torch.sign(bounded) * (bounded.abs() >= self.threshold).to(current.dtype)
        return events, events.abs().mean()


class DeltaEncoder(nn.Module):
    """Causal positive/negative delta events with per-feature reference state."""

    def __init__(self, threshold: float = 0.5, state_bytes_per_feature: int = 4) -> None:
        super().__init__()
        if threshold <= 0:
            raise ValueError("delta threshold must be positive")
        self.threshold = float(threshold)
        self.state_bytes_per_feature = int(state_bytes_per_feature)
        self.state_bytes = 0
        self.ops_per_value = 4.0

    def forward(self, current: Tensor) -> tuple[Tensor, Tensor]:
        reference = torch.zeros_like(current[:, :, 0])
        event_steps: list[Tensor] = []
        for step in range(current.shape[-1]):
            delta = current[:, :, step] - reference
            positive = delta >= self.threshold
            negative = delta <= -self.threshold
            events = positive.to(current.dtype) - negative.to(current.dtype)
            reference = reference + events.detach() * self.threshold
            event_steps.append(events)
        events = torch.stack(event_steps, dim=-1)
        self.state_bytes = int(current.shape[1] * self.state_bytes_per_feature)
        return events, events.abs().mean()


def build_encoder(name: str, threshold: float) -> nn.Module:
    if name == "direct_current":
        return DirectCurrentEncoder()
    if name == "amplitude_count":
        return AmplitudeCountEncoder(threshold)
    if name == "delta":
        return DeltaEncoder(threshold)
    raise ValueError(f"unsupported encoder: {name}")


class Channel8EncodedSNN(nn.Module):
    """Matched SNN whose input-current path is selected by a deterministic encoder."""

    def __init__(
        self,
        encoder: str,
        encoder_threshold: float = 0.5,
        classes: int = 2,
        beta: float = 0.9,
        threshold: float = 0.5,
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
        self.encoder_name = encoder
        self.encoder = build_encoder(encoder, encoder_threshold)
        self.classifier = nn.Linear(self.features.feature_channels, classes)
        self.beta = float(beta)
        self.threshold = float(threshold)
        self.surrogate_slope = float(surrogate_slope)
        self.current_scale = float(current_scale)
        self.encoder_threshold = float(encoder_threshold)

    def forward(self, x: Tensor) -> EncodedSNNOutput:
        current = self.features(x) * self.current_scale
        encoded, input_rate = self.encoder(current)
        membrane = torch.zeros_like(encoded[:, :, 0])
        spike_counts = torch.zeros_like(membrane)
        for step in range(encoded.shape[-1]):
            membrane = self.beta * membrane + encoded[:, :, step]
            spikes = surrogate_spike(membrane - self.threshold, self.surrogate_slope)
            membrane = membrane - spikes.detach() * self.threshold
            spike_counts = spike_counts + spikes
        rates = spike_counts / encoded.shape[-1]
        return EncodedSNNOutput(
            logits=self.classifier(rates),
            spike_counts=spike_counts,
            timesteps=int(encoded.shape[-1]),
            mean_spike_rate=rates.mean(),
            input_event_rate=input_rate,
            encoder_state_bytes=int(getattr(self.encoder, "state_bytes", 0)),
            encoder_ops_proxy_per_sample=float(
                self.features.feature_channels
                * encoded.shape[-1]
                * getattr(self.encoder, "ops_per_value", 1.0)
            ),
        )
