# Hybrid-SNN Technical Design

## Model data flow

The selected baseline is a matched compact CNN front-end followed by a deterministic LIF readout.
The front-end produces a 32-channel temporal representation with 48 steps. Direct-current encoding
passes each feature current to the corresponding simulation step; no Poisson/random rate encoder is
used.

```text
EEG [B, 1, 8, 384]
  -> pointwise Conv2d over 8 EEG channels
  -> depthwise temporal Conv2d
  -> ReLU
  -> GroupNorm
  -> adaptive average pool [B, 32, 48]
  -> direct-current temporal current
  -> 48-step subtract-reset LIF (beta=0.90, threshold=0.5)
  -> spike counts / 48
  -> Linear(32, 2)
  -> alert / drowsy logits
```

## State and reset

For every forward/sample, the LIF membrane and spike-count tensors are initialized to zero.
The software models do not carry hidden state across samples, subjects or folds. The Delta encoder
and HCSN/chronology modules are intentionally not part of this curated baseline.

## Parameter and implementation contract

- Channels: 8 selected EEG channels.
- Window: 384 samples at 128 Hz (3 seconds).
- Temporal steps: 48.
- Feature channels: 32.
- LIF: subtract-reset, deterministic hard spike with surrogate gradient for training.
- Classifier: 32-to-2 linear head.
- Frozen exploratory configuration: S2, `beta=0.90`, `threshold=0.5`.
- First fixed-point candidate: Q12.6 for the head-level reference.

## Architecture diagram

See `docs/hybrid_snn_architecture.md` for the Mermaid diagram and explanatory table.

## Non-claims

This repository does not claim chronological streaming, measured energy, FPGA deployment, HLS
synthesis, or board power. Those require separate manifests and tool/board evidence.
