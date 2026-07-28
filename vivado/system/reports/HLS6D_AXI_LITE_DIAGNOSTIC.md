# HLS-6D AXI-Lite First-Read Diagnostic

**Date:** 2026-07-28
**Scope:** `snn_axi_memory_window_hls6a` AXI4-Lite AR/R behavior only. This is not a board PASS and does not validate feature/weight writes, HLS execution, or golden-vector replay.

## Static interface evidence

The HLS-6B hardware handoff (`artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.hwh`) states:

- `snn_axi_memory_window_0` is `snn_axi_memory_window_hls6a`, with `C_S_AXI_ADDR_WIDTH=6`, `C_S_AXI_DATA_WIDTH=32`, base `0x43C00000`, and high address `0x43C0FFFF`.
- Its `s_axi_aclk` is `processing_system7_0/FCLK_CLK0` at 50 MHz.
- Its active-low `s_axi_aresetn` is `proc_sys_reset_0/peripheral_aresetn`.
- SmartConnect `M01_AXI` connects all AR/R signals to the wrapper: `araddr`, `arvalid`, `arready`, `rdata`, `rresp`, `rvalid`, and `rready`.
- The same HWH gives AXI GPIO base `0x41200000` on the 50 MHz/active-low-reset domain, so it remains the valid M00-path comparison point.

The retained HLS-6B implementation workspace contains the routed checkpoint and module-ref shell for the wrapper. The generated shell identifies the same `snn_axi_memory_window_hls6a` module with address width 6 and data width 32. No implementation was regenerated for this diagnostic.

## Read-channel comparison

| Concern | Read-only `breath_led_ip` reference | Current SNN wrapper | Result |
|---|---|---|---|
| AR acceptance | Registered FSM enters an address-ready state after reset. | `s_axi_arready = !s_axi_rvalid && !soft_reset_active`. | Both allow one outstanding read; SNN is combinationally ready when idle. |
| Address capture / response creation | Captures `ARADDR` on AR handshake and asserts `RVALID`. | On `ARVALID && ARREADY`, registers `RVALID`, `RDATA`, and `RRESP`. | SNN response is explicitly registered on the handshake. |
| Read-data timing | `RDATA` is a continuous decode of the captured address. | `RDATA` is captured from `read_data_for_addr()` at the AR handshake. | SNN avoids a stale mutable-status decode and meets the project rule. |
| Backpressure | Holds `RVALID` until `RREADY`; then returns to address-ready state. | Holds `RVALID` until `RREADY`; after that edge it clears `RVALID` and re-enables `ARREADY`. | Equivalent one-transaction behavior. |
| VERSION | Not applicable. | Offset `0x08` returns `0x00010001`. | Verified in focused simulation. |

## Focused simulation evidence

Run:

```powershell
& .\snn_hybrid_eeg\vivado\system\scripts\run_hls6d_axi_lite_version_sim.ps1
```

This compiles the production wrapper and a focused testbench. The testbench supplies an always-idle HLS stub so the proof boundary is the AXI-Lite wrapper, not the generated compute core.

`HLS6D_AXI_VERSION_SIM_PASS` was emitted by Vivado Simulator 2025.1. The trace records:

- VERSION AR handshake at cycle 6, followed by `RVALID`, `RRESP=OKAY`, and `RDATA=0x00010001` at cycle 7.
- `RVALID`, `RDATA`, and `RRESP` remain stable for two cycles while `RREADY=0`.
- A STATUS read produces `0x00000011` from the deterministic idle stub.
- A second VERSION request with `RREADY=1` also returns `0x00010001` and completes normally.

Artifacts:

- `reports/HLS6D_AXI_LITE_VERSION_SIM.log` (UTF-8 evidence log)
- `hls6d_axi_lite_version_sim_work/hls6d_axi_lite_version.vcd`
- `hls6d_axi_lite_version_sim_work/xsim.log`

## Regression evidence

The existing full generated-HLS wrapper regression was rerun without RTL modification. It passed all three retained cases, including repeated runs and the wrapper's STATUS polling, AXI-Lite writes, and logits reads. The focused simulation above is the VERSION-specific assertion:

```text
SNN AXI memory-window 3-case simulation PASS writes=9852 reads=3582
```

The retained log is `reports/HLS6D_FULL_WRAPPER_REGRESSION.log`.

## Decision

**No AXI-Lite wrapper RTL fix is justified by the static comparison or RTL simulations.** The wrapper already registers `RDATA`/`RRESP` on AR handshake and holds the response through R-channel backpressure. Changing it would be speculative and risks altering a path that passes both focused and full-wrapper RTL simulation.

The first board read remains **unresolved**: this evidence excludes a wrapper AR/R FSM defect in source RTL, but it does not prove the delivered board image, reset release, or PS7-to-SmartConnect-to-M01 transaction on hardware.

## Next narrow board diagnostic

Use the existing HLS-6B bitstream and a diagnostic ELF that performs no vector replay and prints UART stage markers in exactly this order:

1. `AXI_PROBE=GPIO_BEGIN base=0x41200000`; read GPIO data at `0x41200000`; print `AXI_PROBE=GPIO_VALUE value=...`.
2. `AXI_PROBE=VERSION_BEGIN base=0x43C00000`; read `0x43C00008`; print `AXI_PROBE=VERSION value=...`.
3. Only if VERSION returns, print `AXI_PROBE=STATUS_BEGIN`; read `0x43C00004`; print `AXI_PROBE=STATUS value=...`.

Do not write feature, weight, bias, control, or replay registers in this diagnostic. If GPIO returns but the VERSION marker still has no following value, create the minimum ILA capture on M01 only: `s_axi_aresetn`, `ARVALID`, `ARREADY`, `ARADDR`, `RVALID`, `RREADY`, `RRESP`, and `RDATA`.
