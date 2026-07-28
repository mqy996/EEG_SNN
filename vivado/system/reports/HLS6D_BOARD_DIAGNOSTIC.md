# HLS-6D bounded SNN AXI-Lite board diagnostic

Date: 2026-07-28
Tool: Vitis/Vivado 2025.1 (Vitis SW Build 6137779; Vivado SW Build 6140274)
Scope: existing HLS-6B bitstream plus a new standalone diagnostic ELF. No HLS-6B
RTL, bitstream, or full replay software was changed.

## Result

**Single-run board diagnostic PASS.** After programming the retained HLS-6B
bitstream and downloading the diagnostic ELF, one complete COM5 capture reached
all markers in the required order:

```text
HLS6D_DIAG_START
GPIO_READ_BEGIN addr=0x41200000
GPIO_READ_DONE value=0x00000000
SNN_VERSION_BEGIN addr=0x43C00008
SNN_VERSION_DONE value=0x00010001 expected=0x00010001
SNN_STATUS_BEGIN addr=0x43C00004
SNN_STATUS_DONE value=0x00000001
HLS6D_DIAG_COMPLETE gpio=0x00000000 version=0x00010001 status=0x00000001
```

The complete UART capture is retained as:

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_board_diag_board_run_pass.log
```

A later repeat **without a physical reset/power cycle** stopped after
`GPIO_READ_BEGIN`; it did not reach `GPIO_READ_DONE`, VERSION, or STATUS. That
run is retained as:

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_board_diag_board_run_retry3.log
```

Therefore the claim is **single-run PASS; repeatability UNCONFIRMED**. Do not
attribute the later block to the SNN wrapper until a physical reset/power cycle
and a fresh bounded diagnostic run are available.

| Stage | Result | Evidence |
|---|---|---|
| Vitis platform | PASS | `hls6d_board_diag_build.txt`, platform `export=SUCCESS` |
| Diagnostic ELF | PASS | `hls6d_diag_app_20260728.elf`, SHA-256 below |
| Existing HLS-6B bitstream programming | PASS | `hls6d_program_hls6b_vivado.log`, `HLS6D_PROGRAM_RESULT=PASS` |
| Complete first diagnostic run | PASS | `hls6d_board_diag_board_run_pass.log` |
| Later no-physical-reset repeat | BLOCKED at GPIO | `hls6d_board_diag_board_run_retry3.log` |
| SNN VERSION/STATUS in first run | PASS | `0x00010001` / `0x00000001` in pass log |

## Artifact identity and hashes

The build manifest is the source of truth for the curated copies:

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_board_diag_build.txt
```

```text
HLS-6B XSA SHA-256:       373543b2a9a283339f3d48bcd20cb38cc299a0f416faae84ba3b0dcc303ba98b
HLS-6B bitstream SHA-256: d5e90c144c02dddf4af94ec85208dfd285b2f672ee13bb18ca7c18b4950bab8d
HLS-6D XPFM SHA-256:      01687fd4a74fbbe0fd547382d09407f6140f4b068a87e6eca80e989d86e4062d
HLS-6D ELF SHA-256:       5e5bc7f83961f9861f0f26443a5b8163b32364ecaae091b97f2e63b5eae1c6ca
```

The XSA, bitstream, XPFM, and ELF are all retained under the
`hls6d_board_diag`/HLS-6B artifact prefix without overwriting the existing
HLS-6C `a6c.elf` or replay artifacts. The XPFM hash is for the curated copied
file, not an unretained external workspace path.

## Diagnostic contract

`main.c` performs exactly these operations:

1. one AXI GPIO read at `0x41200000`;
2. one SNN VERSION read at `0x43C00008`;
3. one SNN STATUS read at `0x43C00004`, only after VERSION returns.

It contains no `Xil_Out32` call and no SNN control, feature, weight, bias, index,
or replay-vector access. The application exits nonzero if VERSION differs from
`0x00010001`, but it does not write a recovery or test value.

## Capture and verification

- The Python capture helper has per-marker timeouts plus a 90-second global
  timeout; it stops at the first missing marker and retains XSCT, UART, and
  serial-error sections.
- The HLS-6D Python scripts pass `python -m py_compile` and `ruff check`.
- The custom Tcl/Python sources are UTF-8 without a BOM.
- The curated HLS-6B bitstream hash is recorded in the build manifest and matches
  the bitstream passed to the programming helper.
- No ILA, full replay, SNN writes, or HLS-6B RTL/bitstream modification was
  attempted as part of this diagnostic.
## Post-power-cycle follow-up (2026-07-28)

The first post-power-cycle run did **not** reproduce the complete pass. The
same retained HLS-6B bitstream and diagnostic ELF downloaded successfully, but
UART stopped at:

```text
HLS6D_DIAG_START
GPIO_READ_BEGIN addr=0x41200000
```

The bounded evidence is retained as:

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_board_diag_post_power_cycle_pass_20260728.log
```

To separate the SNN wrapper from the system path, the previously built AXI GPIO
smoke ELF was run against the current HLS-6B bitstream. It also stopped before
reading the GPIO TRI register:

```text
AXI_GPIO_TEST_20260727_V1
AXI_GPIO_BASE=0x41200000
```

The same behavior was observed with the older AXI-GPIO bitstream. Therefore,
this run does **not** support an SNN RTL or SNN VERSION/STATUS-specific root
cause; the first blocking transaction is the PS M_AXI_GP0 -> AXI fabric -> AXI
GPIO path.

### PS7/DDR bounded check

A download-free XSCT check was added before changing any RTL. With the current
HLS-6B bitstream and its generated `ps7_init.tcl`, PS7 initialization completed
and the key reads were:

```text
pss_rst_ctrl_after = 0x00000000
ddr_ctrl           = 0x00000081
ddr_dci_status     = 0x00000001
ddr_phy_ctrl       = 0x77010800
ddr_cmd_status     = 0x00000101
```

A following bounded `dow` check also completed successfully, so the earlier
`Cannot access DDR: the controller is held in reset` message is intermittent
state evidence rather than a permanent failure of the current ELF/XSA pair.
The diagnostic logs are:

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_ps7_ddr_diag_current_20260728.log
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_ps7_dow_check_20260728.log
```

### Bounded conclusions and next gate

1. The SNN-first diagnostic remains **stopped**; it is not useful to build or
   replay SNN workloads while the standard AXI GPIO read can block.
2. A direct-reset SmartConnect/GPIO probe was synthesized and implemented, but
   its smoke run did not pass; it is not evidence that bypassing
   `proc_sys_reset` fixes the design.
3. The template PS7 init script was not substituted into the current bitstream:
   the one-off trial failed to expose the ARM target after programming, so the
   template remains read-only reference material.
4. After repeated programming attempts, XSCT no longer exposes the ARM target
   reliably. The next hardware gate is another cold power cycle, followed by
   exactly one bounded sequence: program HLS-6B -> run current `ps7_init` ->
   verify a single AXI GPIO read. Only if that succeeds should we add ILA or
   return to SNN VERSION/STATUS.

No HLS-6B RTL, production bitstream, or user template project was modified by
this follow-up.
