# HLS-5A/5B：Zynq PS/PL 与 AXI-Lite 固定向量回放系统

## 目的

本目录把已经通过 HLS/RTL 固定向量验证的 `hybrid_lif_head_q12_6` 包装为一个可由 Zynq PS 访问的 32-bit AXI4-Lite 从设备，并完成 Vivado、Vitis 和真实开发板连接/下载/串口 smoke test；AXI-Lite 板端读事务仍未闭环。

当前系统验证的是 **PS → AXI-Lite wrapper → HLS Hybrid LIF → PS/UART**，不是完整 CNN-SNN EEG 分类部署。

## 架构

```text
Cortex-A9 / Vitis standalone
        │  AXI GP0
        ▼
Zynq PS7 ── AXI Interconnect ── snn_axi_memory_window
        │                         │ indexed feature/weight/bias
        │                         ▼
        │                  hybrid_lif_head_q12_6 HLS RTL
        │                         │ logits / spike counts
        └── UART1 MIO48/49 ── CP210x COM5
```

- `FCLK_CLK0 = 50 MHz`。
- `PS M_AXI_GP0` 是当前软件访问 wrapper 的主路径。
- `S_AXI_HP0..3` 未启用；当前数据不是从 DDR 直接 DMA 到 PL，而是由 Cortex-A9 通过 AXI-Lite indexed window 写入 wrapper 本地存储。
- UART 使用 UART1，MIO48/49；该配置已经通过 COM5 板端输出实测确认。
- 当前 Tcl 仍使用 `axi_interconnect:2.1`，它在 Vivado 中显示 discontinued，但当前单主单从拓扑已通过综合、实现和板端回放。后续若扩展多主机/高吞吐，再迁移 SmartConnect 并重新验证。

## AXI-Lite 寄存器契约

地址为字节偏移，32-bit little-endian data，低位字段有效。

| 偏移 | 名称 | 访问 | 说明 |
|---:|---|---|---|
| `0x00` | `CONTROL` | W | bit0=start；bit1=soft_reset；bit2=clear_done |
| `0x04` | `STATUS` | R | idle、done、busy、错误和 ready |
| `0x08` | `VERSION` | R | `0x00010001` |
| `0x0C` | `VECTOR_ID` | RW | 回放向量标识 |
| `0x10/0x14` | `FEATURE_INDEX/DATA` | RW/W | 1536 个 Q12.6 feature word |
| `0x18/0x1C` | `WEIGHT_INDEX/DATA` | RW/W | 64 个 Q12.6 weight word |
| `0x20/0x24` | `BIAS_INDEX/DATA` | RW/W | 2 个 Q12.6 bias word |
| `0x28/0x2C` | `LOGIT_INDEX/DATA` | RW/R | 2 个有符号 18-bit logits |
| `0x30/0x34` | `COUNT_INDEX/DATA` | RW/R | 32 个 6-bit spike count |
| `0x38` | `CHECKSUM` | R | 当前输入 XOR checksum |
| `0x3C` | `ERROR_STATUS` | R/W1C | 地址、busy 写入和控制错误 |

## 关键修正

板端第一次访问 `0x43C00000` 时，CPU 读事务无法返回。根因是自定义 reset 模块把 PS 的 active-low `FCLK_RESET0_N` 按 active-high 处理，导致 `peripheral_aresetn` 一直保持复位。现已修正为：

```verilog
if (!ext_reset_in) sync_pipe <= 4'b0000;
else              sync_pipe <= {sync_pipe[2:0], 1'b1};
```

修正后重新生成 bitstream/XSA、重新构建 Vitis ELF，并完成板端三用例 PASS。

## 复现入口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File vivado/system/scripts/run_snn_replay_system.ps1 `
  -Mode project_bitstream `
  -WorkDir D:/eeg_fpga/w_uart1_reset_20260727
```

Vitis Python 入口：

```text
vitis/snn_replay_standalone/scripts/create_vitis_standalone_app.py
```

稳定交付产物：

```text
vivado/system/artifacts/snn_replay_system.bit
vivado/system/artifacts/snn_replay_system.xsa
vivado/system/artifacts/snn_replay_system.hwh
vivado/system/artifacts/ps7_init.tcl
```

板端结果见 [`reports/HLS5B_BOARD_RESULTS.md`](reports/HLS5B_BOARD_RESULTS.md)。
