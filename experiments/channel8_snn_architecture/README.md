# SNN-3 Architecture Ablation

Status: **complete**.

This experiment freezes SNN-1 S2 (`beta=0.90`, threshold `0.5`) and SNN-2
`direct_current` encoding. It compares a Hybrid LIF head, a depthwise spiking temporal
block, and a matched ANN control. The temporal block did not improve macro-F1 and cost
4x the operation proxy, so the Hybrid LIF head remains the only selected candidate.

The ANN-to-SNN conversion baseline is explicitly blocked because activation calibration
and normalization handling have not yet been specified and tested. See `RESULTS.md` for
the complete 33-job result and attribution decision.
