# HLS-5A.3：Zynq PS/PL 预上板系统结果

## 结论

在没有连接开发板的条件下，已用 Vivado 2025.1 从空目录重建 Zynq-7020 PS/PL 系统，并通过 project-mode synthesis、implementation 和 bitstream 生成。当前产物是**目标器件级、可供后续 Vitis 使用的预上板系统**，不是板端下载或运行证据。

## 固定配置

| 项目 | 配置 / 证据 |
|---|---|
| 目标器件 | `xc7z020clg400-1` |
| 目标板 | 项目基线为 PYNQ-Z2；物理板卡序列号和实物尚未核验 |
| PS | `processing_system7:5.5`，M_AXI_GP0 开启 |
| PL 时钟 | PS `FCLK_CLK0 = 50 MHz`，Vivado timing clock `clk_fpga_0` 周期 20 ns |
| AXI | PS M_AXI_GP0 → AXI Interconnect → `snn_axi_memory_window/S_AXI` |
| reset | `FCLK_RESET0_N` → 自定义同步释放 reset → AXI/HLS wrapper |
| DDR | `MT41K256M16 RE-125`，沿用历史 PS 配置记录 |
| UART | UART1 使用 MIO 48/49；PL UART 引脚未加入 XDC |
| AXI base | `0x43C00000`，由 Vivado address editor 分配，Vitis 应以 `xparameters.h` 为准 |

## 开发板与 XDC 状态

- 目标器件和 PYNQ-Z2 项目方向由 `RESEARCH_OVERVIEW.md`、`THESIS_ROADMAP.md` 以及历史 CNN-LSTM PS 配置交叉确认。
- 历史 `cnn_lstm.xpr` 的 `BoardPart` 为空，因此不能把旧工程说成已经保存了物理 board preset。
- `constraints/PYNQ-Z2_v1.0.xdc` 已放入仓库，内容是官方 PYNQ-Z2 v1.0 master XDC 的 board-reference 版本；其端口行保持注释，避免把不存在的 PL 顶层端口误约束。
- PS DDR/FIXED_IO 由 PS7 BD 自动生成；当前没有外部 PL 时钟端口，所以 master XDC 的 125 MHz `sysclk` 行没有启用。

## 生成命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File vivado/system/scripts/run_snn_replay_system.ps1 `
  -Mode project_bitstream `
  -WorkDir vivado/system/snn_system_project_bitstream
```

本次运行结果：

```text
SYNTH_STATUS=synth_1 Complete!
IMPL_STATUS=write_bitstream Complete!
DRC before bitstream: 0 Errors
Bitgen Completed Successfully
SNN replay system PASS: project_bitstream
```

## Vivado 结果

- Bitstream：`artifacts/snn_replay_system.bit`，约 4.05 MB。
- XSA：`artifacts/snn_replay_system.xsa`，约 786 KB；包含 `snn_replay_system.hwh`、`sysdef.xml`、`ps7_init.*` 和 bitstream。
- Timing：50 MHz 时钟 `clk_fpga_0`，WNS `4.401 ns`，TNS `0 ns`，WHS `0.056 ns`，THS `0 ns`；报告中明确写出所有用户时序约束满足。
- Resource：Slice LUT `8539/53200 (16.05%)`，Slice Registers `21015/106400 (19.75%)`，DSP `34/220 (15.45%)`，BRAM `0/140`。

这些资源和时序是当前**Hybrid LIF 读出头 + AXI memory window + PS/AXI 系统**的实现结果，不代表完整 CNN 前端已经硬件化。

## 证据边界

已证明：

1. PS7、AXI Interconnect、50 MHz FCLK0、reset 和 SNN AXI wrapper 可以在目标 part 上完成 Vivado implementation。
2. bitstream 可以成功生成，XSA 包含 Vitis 所需的 PS handoff 文件。
3. 设计在 50 MHz timing report 下无 setup/hold violation。

尚未证明：

1. 开发板实物型号、板卡连接、JTAG 下载和 UART 输出；
2. bitstream 在 PYNQ-Z2 实物上成功启动；
3. Vitis ELF 已在板端执行并完成三组向量回放；
4. 完整 CNN-SNN 在线输入、准确率、功耗或端到端时延。
