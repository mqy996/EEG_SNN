# HLS Co-design Status

## Current status

The software fixed-point probe selected Q12.6 as the first HLS candidate for the Hybrid LIF head.
This repository currently contains the PyTorch float/fixed-point reference only. No HLS C++ source,
csim/csynth report or board evidence is claimed yet.

## Frozen first HLS contract

```text
Target: xc7z020clg400-1
Clock assumption: 100 MHz
Input: feature_current_q, 32 feature channels x 48 steps
State: 32 membrane values, reset per sample
Encoding: direct-current
LIF: beta=0.90, threshold=0.5, subtract-reset
Fixed point: Q12.6
Output: two logits
```

## Next implementation stages

1. Translate `src/dc_eeg/snn_hardware.py` into a bit-accurate C++ reference.
2. Use the JSON feasibility artifact as the golden vector contract.
3. Run host C++ tests and Vitis HLS `csim`.
4. Run `csynth` and record resource/latency reports separately from software proxies.
5. Only after csim/csynth closure consider board replay.

SynOps, analytical latency and memory values in the current reports are proxies, not measured
energy or board measurements.
