"""Bit-accurate software reference and hardware proxies for the frozen SNN head."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import Tensor, nn
import yaml

from .artifacts import write_json
from .data import EEGDataset, select_channels
from .experiment import set_deterministic_seed, torch_dtype
from .metrics import binary_metrics
from .snn_architecture import build_architecture, forward_architecture
from .snn_pilot import SNNPilotConfig, _loader
from .splits import iter_loso_splits


@dataclass(frozen=True)
class FixedPointConfig:
    total_bits: int
    frac_bits: int

    @property
    def scale(self) -> int:
        return 1 << self.frac_bits

    @property
    def min_int(self) -> int:
        return -(1 << (self.total_bits - 1))

    @property
    def max_int(self) -> int:
        return (1 << (self.total_bits - 1)) - 1

    def __post_init__(self) -> None:
        if self.total_bits not in (8, 12, 16):
            raise ValueError("total_bits must be one of 8, 12, or 16")
        if not 0 < self.frac_bits < self.total_bits:
            raise ValueError("frac_bits must be positive and smaller than total_bits")


@dataclass(frozen=True)
class HardwareConfig:
    base_config_path: Path
    results_root: Path
    seed: int
    fold: int
    epochs: int
    train_batch_size: int
    eval_batch_size: int
    target_part: str
    clock_mhz: float
    input_format: str
    fixed_points: tuple[FixedPointConfig, ...]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], repository_root: Path) -> "HardwareConfig":
        required = {
            "base_config",
            "results_root",
            "seed",
            "fold",
            "epochs",
            "train_batch_size",
            "eval_batch_size",
            "target_part",
            "clock_mhz",
            "input_format",
            "fixed_points",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"hardware config is missing keys: {missing}")
        fixed_points = tuple(
            FixedPointConfig(total_bits=int(item["total_bits"]), frac_bits=int(item["frac_bits"]))
            for item in raw["fixed_points"]
        )
        if not fixed_points:
            raise ValueError("fixed_points must not be empty")
        config = cls(
            base_config_path=_resolve_path(str(raw["base_config"]), repository_root),
            results_root=_resolve_path(str(raw["results_root"]), repository_root),
            seed=int(raw["seed"]),
            fold=int(raw["fold"]),
            epochs=int(raw["epochs"]),
            train_batch_size=int(raw["train_batch_size"]),
            eval_batch_size=int(raw["eval_batch_size"]),
            target_part=str(raw["target_part"]),
            clock_mhz=float(raw["clock_mhz"]),
            input_format=str(raw["input_format"]),
            fixed_points=fixed_points,
        )
        if config.fold <= 0 or config.epochs <= 0 or config.train_batch_size <= 0 or config.eval_batch_size <= 0:
            raise ValueError("fold, epochs, and batch sizes must be positive")
        if config.clock_mhz <= 0:
            raise ValueError("clock_mhz must be positive")
        if config.input_format != "feature_current_q":
            raise ValueError("input_format must be feature_current_q")
        if config.target_part != "xc7z020clg400-1":
            raise ValueError("target_part must be the frozen xc7z020clg400-1")
        return config


def _resolve_path(value: str, repository_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (repository_root / path).resolve()


def load_hardware_config(path: Path, repository_root: Path) -> HardwareConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"configuration must be a mapping: {path}")
    return HardwareConfig.from_mapping(raw, repository_root)


def quantize(value: Tensor, config: FixedPointConfig) -> tuple[Tensor, Tensor]:
    scaled = torch.round(value * config.scale)
    clipped = scaled.clamp(config.min_int, config.max_int)
    saturation = (scaled != clipped).to(value.dtype).mean()
    return clipped.to(torch.int64), saturation


def dequantize(value: Tensor, config: FixedPointConfig) -> Tensor:
    return value.to(torch.float64) / config.scale


def float_lif_head(currents: Tensor, weight: Tensor, bias: Tensor, beta: float, threshold: float) -> tuple[Tensor, Tensor]:
    membrane = torch.zeros_like(currents[:, :, 0])
    spike_counts = torch.zeros_like(membrane)
    for step in range(currents.shape[-1]):
        membrane = beta * membrane + currents[:, :, step]
        spikes = (membrane >= threshold).to(currents.dtype)
        membrane = membrane - spikes * threshold
        spike_counts = spike_counts + spikes
    rates = spike_counts / currents.shape[-1]
    return rates @ weight.t() + bias, spike_counts


def fixed_lif_head(
    currents: Tensor,
    weight: Tensor,
    bias: Tensor,
    beta: float,
    threshold: float,
    config: FixedPointConfig,
) -> tuple[Tensor, Tensor, dict[str, float]]:
    current_q, current_saturation = quantize(currents, config)
    weight_q, weight_saturation = quantize(weight, config)
    bias_q, bias_saturation = quantize(bias, config)
    beta_q, beta_saturation = quantize(torch.tensor(beta, dtype=torch.float64), config)
    threshold_q, threshold_saturation = quantize(torch.tensor(threshold, dtype=torch.float64), config)
    membrane_q = torch.zeros_like(current_q[:, :, 0])
    spike_counts_q = torch.zeros_like(membrane_q)
    for step in range(current_q.shape[-1]):
        membrane_q = torch.round(beta_q * membrane_q / config.scale) + current_q[:, :, step]
        spikes = (membrane_q >= threshold_q).to(torch.int64)
        membrane_q = membrane_q - spikes * threshold_q
        spike_counts_q = spike_counts_q + spikes
    rate_q = torch.round(spike_counts_q * config.scale / current_q.shape[-1]).to(torch.int64)
    logits_q = torch.round(rate_q @ weight_q.t() / config.scale) + bias_q
    saturation = {
        "current": float(current_saturation),
        "weight": float(weight_saturation),
        "bias": float(bias_saturation),
        "beta": float(beta_saturation),
        "threshold": float(threshold_saturation),
    }
    return dequantize(logits_q, config), spike_counts_q, saturation


def estimate_hardware_proxies(feature_channels: int, temporal_steps: int, classes: int, config: FixedPointConfig, target_part: str, clock_mhz: float) -> dict[str, float | int | str]:
    lif_steps = feature_channels * temporal_steps
    classifier_macs = feature_channels * classes
    cycle_proxy = lif_steps * 3 + classifier_macs
    return {
        "target_part": target_part,
        "clock_mhz": clock_mhz,
        "evidence_level": "software_proxy",
        "parameter_storage_bytes": int((feature_channels * classes + classes) * config.total_bits / 8),
        "membrane_state_bytes": int(feature_channels * config.total_bits / 8),
        "feature_stream_bytes_per_sample": int(feature_channels * temporal_steps * config.total_bits / 8),
        "lif_add_compare_ops": int(lif_steps * 3),
        "classifier_mac_ops": int(classifier_macs),
        "synops_proxy": int(lif_steps * 2 + classifier_macs),
        "latency_cycles_proxy": int(cycle_proxy),
        "latency_us_proxy": float(cycle_proxy / (clock_mhz * 1_000_000) * 1_000_000),
    }


def train_reference_fold(dataset: EEGDataset, pilot: SNNPilotConfig, config: HardwareConfig, device: torch.device) -> tuple[nn.Module, Tensor, np.ndarray]:
    set_deterministic_seed(config.seed + config.fold)
    dtype = torch_dtype(pilot.dtype)
    selected = select_channels(dataset.samples)
    split = iter_loso_splits(dataset.subject_ids, fold=config.fold)[0]
    model = build_architecture("hybrid_lif_head", pilot, type("ArchitectureOverride", (), {
        "beta": pilot.snn["beta"],
        "threshold": 0.5,
        "temporal_kernel": 3,
    })()).to(device=device, dtype=dtype)
    optimizer = torch.optim.Adam(model.parameters(), lr=pilot.learning_rate)
    train_loader = _loader(selected[split.train_indices], dataset.labels[split.train_indices], config.train_batch_size, True, dtype, config.seed + config.fold)
    model.train()
    for _ in range(config.epochs):
        for inputs, targets in train_loader:
            inputs = inputs.to(device=device, non_blocking=True)
            targets = targets.to(device=device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            output = forward_architecture(model, "hybrid_lif_head", inputs)
            loss = nn.CrossEntropyLoss()(output.logits, targets)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite reference loss")
            loss.backward()
            optimizer.step()
    test_loader = _loader(selected[split.test_indices], dataset.labels[split.test_indices], config.eval_batch_size, False, dtype, config.seed + config.fold)
    inputs_list = []
    with torch.no_grad():
        for inputs, _ in test_loader:
            inputs_list.append(inputs.to(device=device, non_blocking=True))
    return model, torch.cat(inputs_list, dim=0), dataset.labels[split.test_indices]


def run_feasibility_probe(dataset: EEGDataset, pilot: SNNPilotConfig, config: HardwareConfig, device: torch.device) -> dict[str, Any]:
    model, test_inputs, test_labels = train_reference_fold(dataset, pilot, config, device)
    model.eval()
    with torch.no_grad():
        currents = model.features(test_inputs) * pilot.snn["current_scale"]
        float_logits, float_counts = float_lif_head(currents.double().cpu(), model.classifier.weight.detach().double().cpu(), model.classifier.bias.detach().double().cpu(), pilot.snn["beta"], 0.5)
    rows = []
    for fixed in config.fixed_points:
        fixed_logits, fixed_counts, saturation = fixed_lif_head(currents.double().cpu(), model.classifier.weight.detach().double().cpu(), model.classifier.bias.detach().double().cpu(), pilot.snn["beta"], 0.5, fixed)
        float_pred = float_logits.argmax(dim=1).numpy()
        fixed_pred = fixed_logits.argmax(dim=1).numpy()
        rows.append({
            "total_bits": fixed.total_bits,
            "frac_bits": fixed.frac_bits,
            "logit_mae": float(torch.mean(torch.abs(float_logits - fixed_logits))),
            "spike_rate_float": float(float_counts.mean() / currents.shape[-1]),
            "spike_rate_fixed": float(fixed_counts.float().mean() / currents.shape[-1]),
            "spike_rate_drift": float(fixed_counts.float().mean() / currents.shape[-1] - float_counts.mean() / currents.shape[-1]),
            "prediction_agreement": float(np.mean(float_pred == fixed_pred)),
            "float_metrics": binary_metrics(test_labels, float_pred).to_dict(),
            "fixed_metrics": binary_metrics(test_labels, fixed_pred).to_dict(),
            "saturation": saturation,
            "hardware_proxy": estimate_hardware_proxies(currents.shape[1], currents.shape[2], 2, fixed, config.target_part, config.clock_mhz),
        })
    return {
        "target": {"part": config.target_part, "clock_mhz": config.clock_mhz, "input_format": config.input_format, "fold": config.fold, "epochs": config.epochs},
        "float_reference": {"model": "hybrid_lif_head", "encoding": "direct_current", "feature_channels": int(currents.shape[1]), "temporal_steps": int(currents.shape[2])},
        "fixed_point_rows": rows,
        "decision": "go_to_hls_csim" if any(row["prediction_agreement"] >= 0.99 and max(abs(row["spike_rate_drift"]), 0.0) <= 0.01 and max(row["saturation"].values()) < 0.05 for row in rows) else "no_go_pending_calibration",
    }


def write_probe_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, result)
