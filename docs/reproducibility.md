# Reproducibility Guide

## 1. Prepare data

Obtain the official balanced SADT MAT artifact used by the experiments and place it at:

```text
data/dataset.mat
```

Expected SHA-256:

```text
53cc4ef14b1343f7f3fb5322dd2b541c031c6c2297bddf1817aed04dc687a6a4
```

Expected shape and protocol:

```text
2022 samples x 30 channels x 384 time points
11 subjects
class_blocked_compatibility
```

Do not commit the MAT file. The code validates the hash before execution.

## 2. Verify the environment

```powershell
conda run -n eeg-causal python scripts/verify_environment.py
conda run -n eeg-causal python -m ruff check src scripts tests
conda run -n eeg-causal python -m pytest
```

## 3. Run experiments

Start with dry-run/smoke commands in the root README. Full runs are resumable and write to ignored
`results/` directories. Use the same config, seed and device when reproducing curated results.

## 4. Reproducibility boundaries

The summaries are compatibility evidence on the class-blocked official MAT. They do not establish
chronological order, causal replay or online deployment. Do not interpret SynOps as measured power.
The Q12.6 fixed-point report is a software head-level feasibility probe; HLS csim/csynth and board
validation are separate future evidence levels.
