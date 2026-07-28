# HLS-6D bounded SNN AXI-Lite board diagnostic

Date: 2026-07-28
Tool: Vitis/Vivado 2025.1 (Vitis SW Build 6137779; Vivado SW Build 6140274)
Scope: existing HLS-6B bitstream, new standalone diagnostic ELF only.

## Result

The diagnostic ELF was built successfully and downloaded after programming the
existing HLS-6B bitstream. The board run stopped at the first missing marker:
`GPIO_READ_BEGIN` was printed, but `GPIO_READ_DONE` was not received within the
bounded capture window. Therefore the diagnostic did not reach SNN VERSION or
STATUS. No SNN write, golden replay, ILA, or HLS-6B RTL/bitstream change was made.

| Stage | Result | Evidence |
|---|---|---|
| Vitis platform | PASS | `hls6d_board_diag_build.txt`, platform `export=SUCCESS` |
| Diagnostic ELF | PASS | `hls6d_diag_app_20260728.elf`, SHA-256 below |
| Existing HLS-6B bitstream programming | PASS | `hls6d_program_hls6b_vivado.log`, `HLS6D_PROGRAM_RESULT=PASS` |
| CPU/ELF download | PASS | `hls6d_board_diag_board_run.log`, `HLS6D_ELF_DOWNLOADED=...` |
| GPIO read transaction | BLOCKED | UART reached `GPIO_READ_BEGIN`, no `GPIO_READ_DONE` |
| SNN VERSION read | NOT REACHED | first missing marker was GPIO completion |
| SNN STATUS read | NOT REACHED | VERSION was not reached |

## Exact UART result (COM5, 115200 8-N-1)

```text
HLS6D_DIAG_START
GPIO_READ_BEGIN addr=0x41200000
```

The capture controller stopped after the missing `GPIO_READ_DONE` marker. The
full XSCT and COM5 capture is retained at:

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6d_board_diag/hls6d_board_diag_board_run.log
```

XSCT also reported:

```text
HLS6D_FPGA_PROGRAMMED=.../smartconnect_snn_wrapper_50mhz.bit
HLS6D_ELF_DOWNLOADED=.../hls6d_diag_app_20260728.elf
HLS6D_CPU_CONTINUED
HLS6D_CPU_RUN_WINDOW_COMPLETE
```

## Artifact identity

```text
HLS-6B XSA SHA-256:       373543b2a9a283339f3d48bcd20cb38cc299a0f416faae84ba3b0dcc303ba98b
HLS-6B bitstream SHA-256: d5e90c144c02dddf4af94ec85208dfd285b2f672ee13bb18ca7c18b4950bab8d
HLS-6D ELF SHA-256:       5e5bc7f83961f9861f0f26443a5b8163b32364ecaae091b97f2e63b5eae1c6ca
```

Curated artifacts use the distinct `hls6d_board_diag` prefix. The existing
HLS-6C `a6c.elf` and artifacts were not overwritten.

## Diagnostic contract

`main.c` performs exactly one AXI GPIO read at `0x41200000`, then reads SNN
VERSION at `0x43C00008`, and only after that read returns reads STATUS at
`0x43C00004`. It contains no `Xil_Out32` call, no SNN control/feature/weight/
bias access, and no replay vector data.

## Verification

- `python -m py_compile` passed for the HLS-6D Python scripts.
- Vitis 2025.1 platform and application build passed; ELF exists and hash is retained.
- `ruff check` passed for the HLS-6D Python scripts.
- HLS-6B bitstream hash before/after programming matches the retained identity above.
- Board run was intentionally stopped at the first missing marker; no ILA or full replay was attempted.


## 重复运行边界

首次最小诊断运行完整通过；后续未物理复位的重复运行在 `GPIO_READ_BEGIN` 后阻塞，故当前板端结果标记为“单次 PASS、重复性未确认”。
