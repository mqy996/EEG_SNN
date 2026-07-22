# Staged SNN stability sweep

This experiment freezes the existing Channel8 Hybrid-SNN pilot and changes only LIF `beta` and
`threshold`. It is SNN-1 in the roadmap. It uses official balanced class-blocked compatibility
LOSO data and is not chronological or hardware-energy evidence.

Run stages in order with one shared run ID:

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage smoke --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage screen-loso `
  --run-id <SMOKE_RUN_ID> --resume --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage stability `
  --run-id <SMOKE_RUN_ID> --resume --device cuda
```

Runtime outputs are ignored under `results/snn_stability/`. `RESULTS.md` is the only curated
summary intended for Git.
