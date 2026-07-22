# SNN-2 Encoding Comparison — Results

Status: **complete** (one-seed, 11-fold comparison)

## Protocol

- Dataset: audited official balanced SADT artifact, `2022 x 30`, class-blocked compatibility order.
- Input: Channel8, GroupNorm front end, 48 temporal steps.
- Frozen SNN-1 configuration: S2, `beta=0.90`, neuron threshold `0.5`.
- Seed: `20260717`.
- Training: 11-fold subject holdout, 11 epochs per fold, matched optimizer and parameter budget.
- Encoders: exactly `direct_current`, `amplitude_count`, and signed causal `delta`.
- This is software evidence only. Operation counts are proxies, not energy or power measurements.

Run artifact: `results/snn_encoding/snn-encoding-20260722T035356Z/`.

## Aggregate results

| Encoder | Accuracy | Balanced accuracy | Macro-F1 | Accuracy Δ vs direct | Macro-F1 Δ vs direct | Output spike rate | Input event rate | State bytes | Ops proxy/sample | Silent ratio | Saturated ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direct-current | 72.39% | 72.39% | 71.00% | 0.00 pp | 0.00 pp | 25.18% | n/a | 0 | 1,536 | 8.99% | 12.33% |
| amplitude/count | 60.92% | 60.92% | 60.15% | -11.47 pp | -10.86 pp | 14.62% | 38.15% | 0 | 4,608 | 6.91% | 0.26% |
| signed Delta | 55.35% | 55.35% | 52.59% | -17.04 pp | -18.42 pp | 11.60% | 39.25% | 128 | 6,144 | 0.23% | 0.00% |

## Decision

**Go for the next architecture-ablation task with direct-current as the frozen encoding.**

The deterministic event encoders are not promoted as replacements in this setting. Both reduce output spike rate and saturation, but the reduction is accompanied by a large accuracy/F1 loss. Delta additionally requires per-feature reference state and has the largest operation proxy. This is a useful negative result: on the current normalized feature representation, converting the feature current into threshold events discards information that the matched LIF head needs.

The direct-current baseline is selected because it is the only candidate satisfying the exploratory selection gate (macro-F1 not more than 5 pp below direct, output spike rate between 5% and 30%, saturation below 50%). The selection is not a claim of lower energy; no hardware power measurement was performed.

## Reproducibility and limitations

- All 33 jobs completed: 3 encoders x 11 held-out folds.
- Unit and contract tests: 26 passed; Ruff passed.
- The comparison uses one seed and the existing class-blocked compatibility artifact. It is not yet suitable as a final paper claim.
- The result supports freezing direct-current for architecture ablation; it does not rule out event encodings after a representation redesign or threshold calibration study.
