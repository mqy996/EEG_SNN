# AXI-Lite memory-window 50 MHz 结果摘要

日期：2026-07-25

## 命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File vivado/system/scripts/run_axi_window_sim.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File vivado/system/scripts/run_axi_window_synth.ps1
```

## RTL 仿真

XSim 输出：`SNN AXI memory-window simulation PASS`。测试使用 HLS 已有 `threshold_edge` 固定向量，并通过 AXI-Lite indexed window 写入：1536 个 feature、64 个 weight 和 2 个 bias。

| 检查项 | 结果 |
|---|---|
| 独立 AW/W 到达顺序 | PASS |
| 版本和向量 ID 读写 | PASS |
| 越界 index 错误 | PASS |
| `ERROR_STATUS` W1C | PASS |
| `start → done_latched` | PASS |
| busy 时 input 写保护 | PASS |
| logits 读回 | `(-116, 120)` |
| spike count 前四项 | `(1, 48, 1, 1)` |
| soft reset 清除输出/完成状态 | PASS |

## Vivado synthesis

工具：Vivado 2025.1；器件：`xc7z020clg400-1`；时钟：`s_axi_aclk=50 MHz`，周期 20 ns。

| 指标 | 结果 |
|---|---:|
| WNS | 11.476 ns |
| TNS | 0 ns |
| WHS | 0.220 ns |
| THS | 0 ns |
| LUT | 8,468 |
| FF | 20,553 |
| DSP48E1 | 34 |
| BRAM Tile | 0 |

综合报告中的 DRC warning 主要是 out-of-context 阶段的 PS7 缺失和 DSP 输入寄存器建议；本任务没有把它们误报成完整 Zynq 系统通过。

## 结论

AXI-Lite 控制面、indexed data window、同步 `ap_memory` 适配和 HLS golden 输出读回已经具备可继续系统集成的基线。还不能据此声称“已上板”，因为 PS7、master XDC、XSA/bitstream、Vitis 程序和 UART 日志尚未产生。
