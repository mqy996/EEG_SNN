# Technical Report Summary

## Completed evidence

The curated repository includes the following verified exploratory stages:

- Hybrid-SNN pilot: matched ANN/SNN feasibility on Channel8 + GroupNorm.
- Stability sweep: four configurations, screen and three-seed paired stability; S2 selected.
- Encoding comparison: direct-current, amplitude/count and signed Delta; direct-current selected.
- Architecture ablation: Hybrid LIF head, spiking temporal block and ANN control; Hybrid LIF retained.
- Fixed-point probe: Q8.4, Q12.6 and Q16.8; Q12.6 selected for first HLS work.

## Selected result

```text
Channel8 + GroupNorm + direct-current + Hybrid LIF
beta=0.90, threshold=0.5, 48 steps
```

The complete curated tables are in each `experiments/*/RESULTS.md`.

## Main numerical conclusions

- SNN pilot matched ANN performance under the compatibility protocol.
- S2 reached +0.72 percentage points accuracy delta and +0.87 percentage points Macro-F1 delta
  versus paired ANN in the stability sweep.
- Event encoders reduced spike rate but lost 11.47–17.04 percentage points accuracy versus
  direct-current.
- The spiking temporal block lost 2.49 percentage points Macro-F1 and cost approximately 4x the
  architecture operation proxy.
- Q12.6 achieved 99.24% float/fixed prediction agreement in the head-level fold-2 probe.

## Claim boundary

All existing results use the official balanced `class_blocked_compatibility` artifact. They are
not chronological BS=1 deployment evidence. Operation counts and SynOps are proxies. Q12.6 is a
software fixed-point reference, not HLS or board evidence.
