# SNN-2 Encoding Comparison

Run smoke first, inspect survivors, then run the surviving encoders for one seed and 11 folds:

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_encoding.py `
  --config experiments/channel8_snn_encoding/encoding.yaml --stage smoke --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_encoding.py `
  --config experiments/channel8_snn_encoding/encoding.yaml --stage full `
  --run-id <SMOKE_RUN_ID> --resume --device cuda
```

The encoders are deterministic. Direct-current is the SNN-1 baseline; amplitude/count uses
current-only signed threshold events; Delta keeps a per-feature reference and emits signed
threshold-crossing events. Runtime artifacts are ignored under `results/snn_encoding/`.

The completed comparison is summarized in `RESULTS.md`. The current decision is to retain
`direct_current` as the frozen encoding for architecture ablation: the two event encoders
reduced spike rate but lost 11.47–17.04 percentage points of accuracy versus direct-current.
