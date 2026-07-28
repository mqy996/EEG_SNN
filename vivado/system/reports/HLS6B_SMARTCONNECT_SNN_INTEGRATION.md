# HLS-6B SmartConnect + SNN Wrapper 集成报告

日期：2026-07-28  
目标：在已验证的 AX7020 SmartConnect 基线上接入 HLS-6A `hybrid_lif_head_q12_6` 和 AXI-Lite memory-window wrapper。

## 1. 结果摘要

- Wrapper XSim：**PASS**。
- Vivado BD/validate：**PASS**。
- Synthesis：**PASS**。
- Implementation：**PASS**。
- DRC：**0 errors**；存在 53 个性能/可选优化类 warning，不阻塞当前实现。
- Bitstream/XSA/HWH：**已生成**。
- 板端 SNN 回放：**未执行，不能宣称 PASS**。

## 2. RTL wrapper 验证

测试入口：`vivado/system/scripts/run_hls6b_wrapper_sim.ps1`  
报告：`hls6b_wrapper_sim_console.log`

三组 case 均完成两次运行并通过：

| case | run 1 logits | run 2 logits | 关键覆盖 |
|---|---:|---:|---|
| `threshold_edge` | `-116, 120` | `-116, 120` | 阈值边界、busy 写入、非法地址 |
| `signed_currents` | `1152, -1142` | `1152, -1142` | 有符号电流 |
| `rounding_and_reset` | `-4, 16` | `-4, 16` | 舍入、reset、重复调用 |

每组还检查了 start/done、done clear、error status、AXI split AW/W、同步 ap_memory 读时序以及 32 个 spike counts。总计 `writes=9852`、`reads=3582`。

## 3. Vivado 系统合同

| 项目 | 值 |
|---|---|
| Part | `xc7z020clg400-2` |
| DDR | `MT41J256M16 RE-125` |
| PS master | `M_AXI_GP0` |
| SmartConnect | 1 SI / 2 MI |
| AXI GPIO | `0x41200000` |
| SNN wrapper | `0x43C00000` |
| FCLK0 | 50 MHz / 20 ns |
| UART1 | MIO48/49 |
| reset | `FCLK_RESET0_N` 直接接 `ext_reset_in`；`peripheral_aresetn` 扇出 |
| 数据路径 | AXI-Lite indexed window；不接 HP、DMA 或 DDR 数据流 |

HWH 已由 `ax7020_ps7_base.hwh` 解析确认上述地址、GP0、UART1、50 MHz 和 reset 合同。

## 4. 实现结果

- WNS：`4.849 ns`
- TNS：`0 ns`
- WHS：`0.105 ns`
- 时钟：`clk_fpga_0`，50 MHz，20 ns
- Slice LUT：`9,106 / 53,200`（17.12%）
- Slice Registers：`21,369 / 106,400`（20.08%）
- DSP48E1：`34 / 220`（15.45%）
- Block RAM Tile：`0 / 140`；当前小型窗口被实现为 distributed memory/RAMD32
- DRC：0 errors；warning 主要是 DSP 输入/输出 pipelining 建议和 1 个无可布线负载提示

这些是当前固定向量 wrapper 系统的资源和时序，不是完整 CNN-SNN 网络的资源预测。

## 5. 交付物

- `artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.bit`
- `artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.xsa`
- `artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.hwh`
- `artifacts/smartconnect_snn_wrapper_50mhz/ax7020_ps7_base.bd`
- `hls6b_timing_impl.rpt`、`hls6b_utilization_impl.rpt`、`hls6b_drc_impl.rpt`

SHA-256：

```text
bit  D5E90C144C02DDDF4AF94EC85208DFD285B2F672EE13BB18CA7C18B4950BAB8D
xsa  373543B2A9A283339F3D48BCD20CB38CC299A0F416FAAE84BA3B0DCC303BA98B
hwh  8C5F1D0C93DC8141E1D985C8F4D42F6DC5BDA2AB69D871B31FF3D3566B9C521D
```

## 6. 证据边界与下一步

本任务没有连接开发板，也没有执行 Vitis/PS 端 SNN 固定向量回放。因此当前结论是“wrapper RTL 和 Vivado 实现通过”，不是“板端 SNN 已验证”。下一步 HLS-6C 需要使用上述 XSA 编译 standalone 回放程序，保留 ELF、UART log、输入 manifest、输出比较和复位/超时信息。
