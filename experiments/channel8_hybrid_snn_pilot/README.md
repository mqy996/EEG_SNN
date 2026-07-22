# Channel8 Hybrid-SNN Pilot

This isolated exploratory folder answers one narrow question: can a matched GroupNorm
CompactCNN front end use a deterministic LIF spike-count head without a large LOSO accuracy
collapse while producing non-trivial spike sparsity?

## Evidence boundary

- Dataset: official balanced Cui/SADT MAT artifact.
- Channels: C3, Cz, C4, CP3, CPz, CP4, Oz, O2.
- Protocol: subject-disjoint LOSO compatibility evaluation.
- Stored MAT order: `class_blocked_compatibility`, not chronology.
- This pilot does not implement HCSN, Delta/Rate encoding, fixed point, HLS, or board power.
- Spike rate and SynOps are software proxies, not measured energy.

Reusable code is kept in `src/dc_eeg/`; the CLI is in `scripts/`. Runtime artifacts are
written to ignored `results/snn_pilot/`.

## Commands

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --dry-run

conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --fold 2 --device cuda --smoke
```

Only after the smoke completion file reports `smoke_gate_passed: true`:

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --device cuda
```
