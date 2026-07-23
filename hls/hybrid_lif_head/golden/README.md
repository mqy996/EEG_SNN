# HLS-1 Q12.6 golden vectors

This directory contains the deterministic, synthetic reference vectors for the
HLS-2 Hybrid LIF implementation. They are an executable contract, not a model
checkpoint or an experiment result.

## Regenerate and verify

Run from `snn_hybrid_eeg`:

```powershell
python scripts/export_hls_golden_vectors.py --output hls/hybrid_lif_head/golden/vectors_q12_6.json
python scripts/export_hls_golden_vectors.py --check
```

The exporter does not read EEG, MAT files, checkpoints, or generated result
folders. JSON keys are sorted, indentation is stable, and the file ends with a
newline. The expected SHA-256 of the checked-in vector file is:

```text
8f73683b4448f8315af76151e36dacff494197c0caf8bcf2e8ace01ad301604a
```

## Contract

- External Q12.6 values use `scale=64`, with saturated input/weight/bias range
  `[-2048, 2047]`.
- Floating-point quantization and every integer rescale use explicit
  round-half-to-even. Signed ties are symmetric; for example, `-3 / 2` rounds
  to `-2`, while `-5 / 2` rounds to `-2` because the result magnitude is even.
- The input layout is time-major `feature_current_q[48][32]`.
- The reference uses `beta_q=58`, `threshold_q=32`, subtract-reset LIF, and
  fresh zero membrane/count state on every call.
- `rate_q[c] = round_half_even(spike_count[c] * 64 / 48)`.
- `logits_q[k] = round_half_even(sum(rate_q[c] * weight_q[k][c]) / 64) + bias_q[k]`.
- Python arithmetic is checked against signed int64 bounds after each critical
  operation. There is no implicit wrap, intermediate saturation, or C/C++
  negative-division behavior in the reference.

## JSON schema

The top level contains `schema_version`, `contract_metadata`, `generation`, and
three `cases`:

1. `threshold_edge`: exact threshold equality, continuous threshold current,
   and subtract-reset behavior.
2. `signed_currents`: positive, negative, zero, maximum, and minimum external
   Q12.6 currents.
3. `rounding_and_reset`: positive and negative midpoint-rescaling inputs plus
   repeated-call reset coverage in the test suite.

Each case contains `case_name`, `feature_current_q[48][32]`,
`weight_q[2][32]`, `bias_q[2]`, `beta_q`, `threshold_q`, `spikes[48][32]`,
`membrane_after_reset[48][32]`, `spike_count[32]`, `rate_q[32]`, `logits_q[2]`,
and a `range_report` containing the extrema observed in that synthetic case only. The file also stores mathematically justified `contract_domain_bounds` metadata for HLS-2 width planning; the observed report must not be used as a global bound. The file contains no raw EEG,
full weights from a trained model, checkpoint, or unbounded run output.

## 范围报告边界

`range_report` 仅记录当前合成案例中实际观察到的中间值范围，不能代表所有合法 Q12.6 输入的全域范围。HLS-2 选择 `ap_int` 位宽时必须使用 `contract_metadata.contract_domain_bounds` 中的解析安全界，并再次进行独立范围检查；不能根据某一个黄金案例的最大/最小值决定硬件位宽。

This is software-reference evidence for HLS-1. It is not csim, csynth, Vivado,
board, latency, resource, or energy evidence.

