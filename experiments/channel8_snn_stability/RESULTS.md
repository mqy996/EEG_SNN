# SNN-1 Stability Results

## Status

Completed on 2026-07-22 with the RTX 3060 Laptop GPU. Runtime artifacts are ignored under
`results/snn_stability/snn-stability-20260722T024708Z/`.

- q1 implementation is based on the existing committed pilot and this stability runner.
- Dataset SHA-256: `53cc4ef14b1343f7f3fb5322dd2b541c031c6c2297bddf1817aed04dc687a6a4`.
- Protocol: official balanced class-blocked compatibility data, 11-fold subject-independent LOSO.
- Four configurations screened; S2 and S1 selected; two configurations × three seeds × 11 folds × two models = 132 stability jobs completed.
- This is not chronology, BS=1 causal replay, fixed-point, FPGA or measured-energy evidence.

## Stage results

### Fold-2 smoke, 3 epochs

| Config | beta | threshold | Accuracy | Macro-F1 | Mean spike rate | Silent ratio | Saturated ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| S1 | 0.90 | 1.0 | 45.45% | 44.83% | 12.31% | 18.49% | 0.00% |
| S2 | 0.90 | 0.5 | 49.24% | 48.75% | 20.45% | 12.93% | 5.78% |
| S3 | 0.90 | 1.5 | 42.42% | 41.94% | 8.58% | 28.13% | 0.00% |
| S4 | 0.95 | 1.0 | 46.21% | 45.69% | 12.58% | 23.60% | 0.12% |

All four passed the smoke rejection gate. These short smoke accuracies are not used as final
performance claims.

### One-seed screen

| Rank | Config | Mean macro-F1 | Subject std | Mean spike rate | Selected |
|---:|---|---:|---:|---:|---|
| 1 | S2 | 71.47% | 12.79% | 25.49% | yes |
| 2 | S1 | 70.07% | 14.20% | 17.76% | yes |
| 3 | S4 | 70.04% | 12.95% | 18.08% | no |
| 4 | S3 | 69.25% | 14.40% | 13.81% | no |

### Three-seed paired stability

Accuracy/F1 deltas are Hybrid-SNN minus matched ANN under the same seed.

| Config | Seed | ANN Acc. | SNN Acc. | Delta pp | ANN F1 | SNN F1 | Delta pp | SNN spike rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S2 | 20260717 | 71.80 | 73.22 | +1.42 | 70.02 | 71.47 | +1.45 | 25.49 |
| S2 | 20260718 | 74.12 | 74.13 | +0.02 | 72.53 | 72.70 | +0.17 | 25.51 |
| S2 | 20260719 | 70.85 | 71.60 | +0.74 | 69.30 | 70.29 | +0.99 | 25.61 |
| S1 | 20260717 | 71.80 | 71.99 | +0.19 | 70.02 | 70.07 | +0.05 | 17.76 |
| S1 | 20260718 | 74.12 | 73.44 | -0.68 | 72.53 | 71.95 | -0.59 | 17.90 |
| S1 | 20260719 | 70.85 | 72.04 | +1.18 | 69.30 | 70.83 | +1.53 | 17.89 |

### Cross-seed summary

| Config | Mean accuracy delta (pp) | Mean macro-F1 delta (pp) | Mean spike rate | Delta std (accuracy pp) | Delta std (F1 pp) |
|---|---:|---:|---:|---:|---:|
| S2 | +0.72 | +0.87 | 25.53 | 0.57 | 0.53 |
| S1 | +0.23 | +0.33 | 17.85 | 0.76 | 0.89 |

## Gate decision

```text
SNN-1 gate: PASS
Next task: SNN-2 encoding comparison
```

Both selected configurations satisfy the final gate:

- all three seeds have complete 11-fold ANN/SNN results;
- S1 mean spike rate: 17.85%; S2 mean spike rate: 25.53%;
- S1 mean accuracy delta: +0.23 pp; S2: +0.72 pp;
- S1 mean macro-F1 delta: +0.33 pp; S2: +0.87 pp;
- no seed has a spike-rate or finite-metric failure.

S2 is the preferred next candidate because it produced the highest screen macro-F1 and a
higher but still acceptable firing rate. S1 remains the lower-spike control.

## Interpretation boundary

This is a reproducibility/feasibility result, not evidence that SNN is intrinsically superior.
The gain is small and the experiment uses one fixed architecture, one balanced dataset and
three seeds. SNN-2 should compare input encodings using S2 and S1 as the only frozen candidates;
it should not expand the architecture or begin FPGA work yet.
