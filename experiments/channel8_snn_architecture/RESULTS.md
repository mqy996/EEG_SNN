# SNN-3 Architecture Ablation — Results

Status: **complete** (one-seed, 11-fold attribution study)

## Protocol

- Dataset: audited official balanced SADT artifact, `2022 x 30`, class-blocked compatibility order.
- Frozen input: Channel8, GroupNorm front end, 48 temporal steps, deterministic `direct_current` encoding.
- Frozen SNN-1 configuration: S2, `beta=0.90`, neuron threshold `0.5`.
- Seed: `20260717`; 11-fold subject holdout; 11 epochs per fold.
- Variants: Hybrid LIF head, depthwise spiking temporal block (`kernel=3`), and matched ANN control.
- The ANN-to-SNN conversion baseline was blocked because activation calibration and normalization handling were not yet testable.
- Parameter budget tolerance was declared as 10%; the temporal block overhead was 7.22%.

Run artifact: `results/snn_architecture/snn-architecture-20260722T041252Z/`.

## Aggregate results

| Variant | Accuracy | Balanced accuracy | Macro-F1 | Δ Macro-F1 vs Hybrid | Output spike rate | Parameters | Δ Parameters | Ops proxy/sample |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid LIF head | 72.39% | 72.39% | 71.00% | 0.00 pp | 25.18% | 1,330 | 0.00% | 1,536 |
| Spiking temporal block | 70.35% | 70.35% | 68.52% | -2.49 pp | 25.33% | 1,426 | +7.22% | 6,144 |
| ANN control | 71.25% | 71.25% | 69.70% | -1.31 pp | n/a | 1,330 | 0.00% | n/a |

## Attribution decision

**PASS — proceed to hardware-feasibility planning with the Hybrid LIF head and direct-current encoding frozen.**

The temporal block did not improve performance: it lost 2.49 percentage points of macro-F1 while increasing the architecture operation proxy by 4x and parameters by 7.22%. The simpler Hybrid LIF head is therefore the only selected SNN candidate. The ANN control was slightly below the Hybrid SNN on macro-F1 in this exploratory protocol; this does not establish an SNN advantage or energy benefit.

The result attributes the current performance primarily to the shared convolutional front end plus the simple LIF readout, not to an additional temporal convolution. No conversion baseline was invented because its calibration contract is currently underspecified.

## Reproducibility and limitations

- All 33 jobs completed: 3 variants x 11 held-out folds.
- Unit and contract tests: 30 passed; Ruff passed.
- This remains one-seed evidence on the class-blocked compatibility artifact, not a final paper statistic or chronological deployment claim.
- Operation counts are software proxies only; no energy, power, FPGA, HLS, or board measurement was performed.
