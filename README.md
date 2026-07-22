# Hybrid-SNN EEG baseline

This repository is a curated, teacher-facing snapshot of the verified Hybrid-SNN experiments
from `q1_deployment_causal_eeg`. It is intended for code review and reproduction, not as a copy
of the entire research workspace.

## Frozen baseline

```text
Input: Channel8 EEG window, 8 x 384
Front-end: pointwise spatial convolution -> depthwise temporal convolution -> ReLU -> GroupNorm
Temporal representation: adaptive average pool to 48 steps
Encoding: direct-current
Spiking head: subtract-reset LIF
beta: 0.90
threshold: 0.5
Fixed-point candidate: Q12.6
```

The initial pilot configuration is retained for historical comparison. The SNN-1 stability
sweep selected S2 (`beta=0.90`, `threshold=0.5`) for the encoding and architecture comparisons.

## Repository map

```text
src/dc_eeg/                  reusable model, data, metric and experiment modules
scripts/                     executable experiment entry points
experiments/                 versioned YAML configs and curated results
  channel8_hybrid_snn_pilot/ initial matched ANN/SNN pilot
  channel8_snn_stability/    beta/threshold stability sweep
  channel8_snn_encoding/     deterministic input encoding comparison
  channel8_snn_architecture/ architecture ablation
  channel8_snn_hardware/    fixed-point feasibility probe
tests/                       model and configuration contracts
docs/                        architecture, technical report and reproducibility notes
data/                        README only; official MAT is intentionally ignored
```

## Dataset

The code expects the official balanced MAT artifact at:

```text
data/dataset.mat
```

The file is not committed. See `data/README.md` for provenance, expected dimensions and SHA-256.

## Environment

Use the existing `eeg-causal` Conda environment or create an equivalent Python >=3.11 environment.
The project requires PyTorch, NumPy, SciPy, PyYAML, pytest and Ruff.

```powershell
conda run -n eeg-causal python scripts/verify_environment.py
conda run -n eeg-causal python -m ruff check src scripts tests
conda run -n eeg-causal python -m pytest
```

## Reproduction entry points

All commands are executed from the repository root. Run smoke/dry-run first; full runs write
ignored artifacts under `results/`.

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --dry-run --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage smoke --dry-run --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_encoding.py `
  --config experiments/channel8_snn_encoding/encoding.yaml --stage smoke --dry-run --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_architecture.py `
  --config experiments/channel8_snn_architecture/architecture.yaml --stage smoke --dry-run --device cuda

conda run -n eeg-causal python scripts/run_snn_hardware_feasibility.py `
  --config experiments/channel8_snn_hardware/hardware.yaml --device cuda --dry-run
```

## Evidence boundaries

- Current result summaries use the official balanced `class_blocked_compatibility` artifact; they are
  not chronological replay or causal BS=1 evidence.
- Spike rate, operation counts and SynOps are software proxies, not measured energy.
- Q12.6 is a software fixed-point candidate; it is not an HLS csim/csynth or board result.
- Generated results, checkpoints, datasets and FPGA tool outputs remain ignored.

See:

- `docs/hybrid_snn_architecture.md`
- `docs/technical_report.md`
- `docs/reproducibility.md`
- `experiments/*/RESULTS.md`
