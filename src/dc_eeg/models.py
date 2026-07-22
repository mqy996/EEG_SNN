"""Manual Channel8 CompactCNN reference models for compatibility experiments."""

from __future__ import annotations

from torch import Tensor, nn

from .data import CHANNEL8_NAMES


class Channel8CompactCNN(nn.Module):
    """E04-style manual Channel8 CompactCNN.

    `dynamic_batchnorm` mirrors the historical transductive compatibility
    reference. It is not a causal BS=1 deployment method.
    """

    supported_norm_modes = {
        "dynamic_batchnorm",
        "running_batchnorm",
        "no_norm",
        "groupnorm",
        "layernorm",
    }

    def __init__(
        self,
        channels: int = len(CHANNEL8_NAMES),
        classes: int = 2,
        sample_length: int = 384,
        n1: int = 16,
        depth_multiplier: int = 2,
        kernel_length: int = 32,
        norm_mode: str = "dynamic_batchnorm",
    ) -> None:
        super().__init__()
        if channels <= 0 or classes <= 1:
            raise ValueError("channels must be positive and classes must exceed one")
        if kernel_length <= 0 or kernel_length > sample_length:
            raise ValueError("kernel_length must be in [1, sample_length]")
        if norm_mode not in self.supported_norm_modes:
            raise ValueError(f"unsupported norm_mode: {norm_mode}")

        depth_channels = n1 * depth_multiplier
        self.channels = channels
        self.sample_length = sample_length
        self.norm_mode = norm_mode
        self.pointwise = nn.Conv2d(1, n1, (channels, 1))
        self.depthwise = nn.Conv2d(n1, depth_channels, (1, kernel_length), groups=n1)
        self.activation = nn.ReLU()
        if norm_mode == "dynamic_batchnorm":
            self.normalization: nn.Module = nn.BatchNorm2d(
                depth_channels, track_running_stats=False
            )
        elif norm_mode == "running_batchnorm":
            self.normalization = nn.BatchNorm2d(depth_channels, track_running_stats=True)
        elif norm_mode == "no_norm":
            self.normalization = nn.Identity()
        elif norm_mode == "groupnorm":
            self.normalization = nn.GroupNorm(num_groups=min(16, depth_channels), num_channels=depth_channels)
        else:
            self.normalization = nn.GroupNorm(num_groups=1, num_channels=depth_channels)
        self.gap = nn.AvgPool2d((1, sample_length - kernel_length + 1))
        self.classifier = nn.Linear(depth_channels, classes)

    def forward(self, x: Tensor) -> Tensor:
        if x.ndim != 4 or x.shape[1:] != (1, self.channels, self.sample_length):
            raise ValueError(
                "expected input shape "
                f"[B, 1, {self.channels}, {self.sample_length}], got {tuple(x.shape)}"
            )
        x = self.pointwise(x)
        x = self.depthwise(x)
        x = self.activation(x)
        x = self.normalization(x)
        x = self.gap(x)
        x = x.flatten(start_dim=1)
        return self.classifier(x)
