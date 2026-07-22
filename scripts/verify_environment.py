"""Verify that the isolated eeg-causal environment can run the canonical stack."""

from __future__ import annotations

import platform
import sys

import pytest
import torch


def main() -> int:
    print("python=", sys.version.split()[0])
    print("platform=", platform.platform())
    print("torch=", torch.__version__)
    print("torch_cuda=", torch.version.cuda)
    print("cuda_available=", torch.cuda.is_available())
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; the eeg-causal GPU environment is not ready")
    print("cuda_device=", torch.cuda.get_device_name(0))
    value = (torch.arange(8, device="cuda", dtype=torch.float64) * 2).sum().item()
    if value != 56.0:
        raise RuntimeError(f"unexpected CUDA tensor result: {value}")
    print("cuda_tensor_smoke=", value)
    print("pytest=", pytest.__version__)
    try:
        import ruff
    except ImportError as exc:  # pragma: no cover - defensive installation diagnostic
        raise RuntimeError("Ruff is not installed in eeg-causal") from exc
    print("ruff=", getattr(ruff, "__version__", "installed"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
