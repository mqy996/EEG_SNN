# Pilot Results

## Status

Completed on 2026-07-17 using the local RTX 3060 Laptop GPU.

- Run: `results/snn_pilot/loso-seed20260717-clean-4d8d0fe` (ignored runtime artifact).
- Code revision: 4d8d0fe, git_dirty=false.
- Dataset SHA-256: `53cc4ef14b1343f7f3fb5322dd2b541c031c6c2297bddf1817aed04dc687a6a4`.
- Protocol: one seed (`20260717`), 11-fold subject-independent LOSO.
- Models: matched GroupNorm ANN and Hybrid-SNN, both 1,330 parameters.
- Training: 11 epochs/fold, float32, temporal feature sequence pooled to 48 LIF steps.
- Evidence boundary: class-blocked compatibility pilot; not chronological, causal replay,
  fixed-point, FPGA, or measured energy evidence.

## Aggregate result

| Metric | Matched ANN | Hybrid-SNN | SNN - ANN |
|---|---:|---:|---:|
| Subject-mean accuracy | 71.80% ± 9.37% | 71.99% ± 12.15% | +0.19 pp |
| Subject-mean macro-F1 | 70.02% ± 11.09% | 70.07% ± 14.20% | +0.05 pp |
| Balanced accuracy | 71.80% | 71.99% | +0.19 pp |
| Sensitivity | 72.37% | 70.64% | -1.73 pp |
| Specificity | 71.24% | 73.34% | +2.11 pp |

SNN activity summary:

- mean spike rate: **17.76%**;
- mean silent sample-feature ratio: **13.08%**;
- mean saturated sample-feature ratio (rate >= 50%): **4.36%**;
- head SynOps proxy: **545.48 additions/sample**;
- completion decision: `worth_continuing = true`.

## Per-subject result

| Subject | ANN Acc. (%) | SNN Acc. (%) | Delta (pp) | ANN macro-F1 (%) | SNN macro-F1 (%) | Spike rate (%) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 84.04 | 83.51 | -0.53 | 84.04 | 83.50 | 16.41 |
| 2 | 58.33 | 54.55 | -3.79 | 54.35 | 50.89 | 17.11 |
| 3 | 60.67 | 56.67 | -4.00 | 55.97 | 47.39 | 18.66 |
| 4 | 73.65 | 74.32 | +0.68 | 73.38 | 74.31 | 15.88 |
| 5 | 61.16 | 66.07 | +4.91 | 54.63 | 61.66 | 19.97 |
| 6 | 82.53 | 88.55 | +6.02 | 82.30 | 88.43 | 17.61 |
| 7 | 63.73 | 60.78 | -2.94 | 62.69 | 59.22 | 17.92 |
| 8 | 73.48 | 76.52 | +3.03 | 72.14 | 76.02 | 17.30 |
| 9 | 82.17 | 87.90 | +5.73 | 81.74 | 87.90 | 17.02 |
| 10 | 81.48 | 82.41 | +0.93 | 80.82 | 82.06 | 19.66 |
| 11 | 68.58 | 60.62 | -7.96 | 68.19 | 59.41 | 17.77 |

## Interpretation

The first controlled pilot is positive: the Hybrid-SNN matched the ANN aggregate accuracy
and macro-F1 while maintaining a non-trivial 17.76% spike rate. The result satisfies the
predefined continuation gate (no more than five percentage points aggregate loss and a
5%–30% mean spike rate).

The subject variance is larger for the SNN, and individual effects are mixed: subjects 5, 6,
8, 9, and 10 improve, while subjects 2, 3, 7, and especially 11 decline. Therefore the next
SNN-specific experiment should be a small beta/threshold stability sweep with multiple seeds,
not an immediate energy or superiority claim.

The matched ANN is not the historical dynamic-BN float64 CompactCNN. Its lower 71.80% mean
accuracy reflects the deliberately batch-independent GroupNorm/pooling pilot boundary, so the
71.99% SNN result must not be compared directly with the approximately 78% historical
full-batch compatibility statistic.

## Validation performed

```text
17 pytest tests passed
Ruff passed
CUDA environment verified: PyTorch 2.13.0+cu130, RTX 3060 Laptop GPU
fold-2 3-epoch smoke passed: spike rate 12.31%
fold-2 11-epoch check: ANN 58.33%, SNN 54.55%, spike rate 17.11%
full 11-fold run completed: 22 fold/model results, finite=true
```
