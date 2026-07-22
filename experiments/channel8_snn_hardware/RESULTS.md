# SNN-4 Fixed-Point / FPGA Feasibility — Results

Status: **software feasibility gate passed; HLS csim is the next gated step**.

## Frozen target contract

- Target part: `xc7z020clg400-1` (Zynq-7020 family, consistent with existing project HLS configurations).
- Clock assumption: 100 MHz. This is a planning assumption, not a timing report.
- Selected model: Channel8 + GroupNorm front end, direct-current encoding, Hybrid LIF head.
- Head-level interface: 32 feature currents x 48 temporal steps, represented as `feature_current_q`; one sample per invocation.
- Reset: membrane and spike-count state are reinitialized for every sample.
- Fixed-point candidates: Q8.4, Q12.6, Q16.8, signed saturating round-to-nearest.

The front end remains a float software reference in this probe. Therefore this is a head-level
fixed-point feasibility result, not an end-to-end quantized deployment result.

Run artifact: `results/snn_hardware/snn-hardware-20260722T042835Z/feasibility.json`.

## Fold-2 probe results

The probe trained the frozen Hybrid LIF reference for 3 epochs on held-out fold 2, then compared
float and fixed LIF/classifier outputs on 132 test samples.

| Format | Prediction agreement | Logit MAE | Float spike rate | Fixed spike rate | Spike-rate drift | Saturation | Feature stream/sample | Membrane state | Latency proxy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q8.4 | 96.97% | 0.0405 | 20.79% | 21.25% | +0.46 pp | 0% | 1,536 B | 32 B | 4,672 cycles / 46.72 µs |
| Q12.6 | 99.24% | 0.0090 | 20.79% | 20.82% | +0.03 pp | 0% | 2,304 B | 48 B | 4,672 cycles / 46.72 µs |
| Q16.8 | 100.00% | 0.0032 | 20.79% | 20.82% | +0.03 pp | 0% | 3,072 B | 64 B | 4,672 cycles / 46.72 µs |

Parameter storage proxies for the 32-to-2 classifier are 66 B, 99 B and 132 B respectively.
The operation counts, memory sizes and latency are analytical software proxies; they are not
Vivado/Vitis reports and are not energy measurements.

## Decision

**GO to an isolated HLS csim/csynth task, starting with Q12.6.**

Q8.4 does not meet the exploratory prediction-agreement target of 99%. Q12.6 meets the target
with no observed saturation and negligible spike-rate drift; Q16.8 is the higher-fidelity reference.
No board deployment or power claim is made. HLS work must first reproduce the fixed-point tensor
contract and compare csim outputs against this JSON artifact.

## Validation and limitations

- `python -m ruff check src scripts tests` — **PASS**.
- `python -m pytest` — **PASS**, 33 tests.
- Dry-run validates the pinned dataset, target part, clock, input format and three fixed-point formats.
- This is one held-out fold and 3 training epochs; it is a feasibility probe, not paper-level accuracy evidence.
- The convolutional front end is not yet quantized. End-to-end fixed-point closure remains open.
- No HLS csim/csynth, Vivado timing/resource report, board replay or power measurement was performed.
