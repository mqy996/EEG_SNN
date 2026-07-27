# HLS-5A.1：AXI-Lite memory-window 预上板接口

## 目的

本目录把已经通过固定向量 XSim 验证的 `hybrid_lif_head_q12_6` HLS IP 包装为一个可由 Zynq PS 访问的 32-bit AXI4-Lite 从设备。当前目标是完成**无开发板条件下的 PS/PL 接口契约、RTL 验证和综合证据**，不是宣称已经生成 bitstream 或完成板端运行。

## 当前实现

- `src/snn_axi_memory_window.v`：AXI4-Lite slave、indexed data window、HLS `ap_ctrl_hs` 连接和同步 `ap_memory` 适配。
- `tb/tb_snn_axi_memory_window.sv`：XSim 主机模型，覆盖独立 AW/W、边界检查、W1C、1536 个 feature、64 个 weight、2 个 bias、start/done、busy 写保护、logit/count 读回和 soft reset。
- `constraints/system_50mhz.xdc`：50 MHz/20 ns 预上板时钟契约；未包含开发板引脚约束。
- `scripts/run_axi_window_sim.ps1`：编译 HLS 生成 RTL、wrapper 和 testbench，并运行 XSim。
- `scripts/run_axi_window_synth.ps1`：运行 `xc7z020clg400-1` out-of-context synthesis。
- `tcl/run_axi_window_synth.tcl`：可复现的 Vivado batch synthesis 流程。
- `reports/AXI_WINDOW_50MHZ_RESULTS.md`：当前仿真与综合证据摘要。

## AXI-Lite 寄存器契约

地址为字节偏移，32-bit little-endian data，低位字段有效。

| 偏移 | 名称 | 访问 | 说明 |
|---:|---|---|---|
| `0x00` | `CONTROL` | W | bit0=start；bit1=soft_reset；bit2=clear_done |
| `0x04` | `STATUS` | R | bit0=idle；bit1=done_latched；bit2=busy；bit3=busy_write_error；bit4=ready |
| `0x08` | `VERSION` | R | 当前为 `0x00010001` |
| `0x0C` | `VECTOR_ID` | RW | 回放向量标识 |
| `0x10/0x14` | `FEATURE_INDEX/DATA` | RW/W | 1536 个有符号 Q12.6 feature word |
| `0x18/0x1C` | `WEIGHT_INDEX/DATA` | RW/W | 64 个有符号 Q12.6 weight word；对应 HLS `weight_q[2][32]` 的扁平存储 |
| `0x20/0x24` | `BIAS_INDEX/DATA` | RW/W | 2 个有符号 Q12.6 bias word |
| `0x28/0x2C` | `LOGIT_INDEX/DATA` | RW/R | 2 个有符号 18-bit logits，读出时符号扩展到 32 bit |
| `0x30/0x34` | `COUNT_INDEX/DATA` | RW/R | 32 个无符号 6-bit spike count |
| `0x38` | `CHECKSUM` | R | 当前写入数据的可复现 XOR 累计值 |
| `0x3C` | `ERROR_STATUS` | R/W1C | bit0=地址越界；bit1=busy 时写入 input；bit2=非法控制操作 |

### 软件回放顺序

1. 读取 `VERSION`，写入 `VECTOR_ID`。
2. 对每个数组执行 `INDEX` → `DATA` 写入；所有写入必须在 `STATUS.busy=0` 时完成。
3. 写 `CONTROL.start=1`。
4. 轮询 `STATUS.done_latched=1`；不能使用单周期 `ap_done` 作为软件事件。
5. 写 `LOGIT_INDEX`/`COUNT_INDEX`，读取对应 `DATA`。
6. 需要重新开始时写 `CONTROL.clear_done`，需要清除状态/输出时写 `CONTROL.soft_reset`。

## 验证结果

运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File vivado/system/scripts/run_axi_window_sim.ps1

powershell -NoProfile -ExecutionPolicy Bypass `
  -File vivado/system/scripts/run_axi_window_synth.ps1
```

固定向量 `threshold_edge` 的 RTL 回放结果为：

- XSim：`SNN AXI memory-window 3-case simulation PASS`。
- `threshold_edge`：`logits_q=(-116, 120)`，`spike_count_q[0..3]=(1, 48, 1, 1)`。
- `signed_currents`：`logits_q=(1152, -1142)`。
- `rounding_and_reset`：`logits_q=(-4, 16)`。
- 三组用例均连续运行两次，全部 logits 和 32 个 spike counts bit-exact 一致。
- AXI 错误/控制行为覆盖：越界访问、busy 写保护、非法 start、clear_done 和 soft reset。
- Vivado synthesis：目标 `xc7z020clg400-1`，50 MHz/20 ns，WNS `11.476 ns`，TNS `0 ns`，WHS `0.220 ns`，THS `0 ns`。
- 综合资源：LUT `8468`，FF `20553`，DSP `34`，BRAM `0`。该资源结果包含 HLS 读出头和 wrapper 的寄存器型 memory window，不是最终 PS/PL 实现资源。

## 边界与下一步

当前目录仍然没有：

- Zynq Processing System（PS7）实例；
- 开发板 master XDC 和外部引脚约束；
- bitstream、XSA、Vitis ELF；
- UART/板端日志。

因此当前证据等级是“AXI wrapper RTL + out-of-context synthesis”，不能表述为上板验证。下一步 HLS-5A.2 验证三组 golden case，随后 HLS-5A.3 建立 Zynq PS/PL 系统。

## HLS-5A.3：Zynq PS/PL 预上板系统

- `tcl/create_snn_replay_system.tcl`：从空目录创建 PS7、AXI Interconnect、reset 和 SNN wrapper；`project_bitstream` 模式使用 project-mode flow 生成 Vitis-ready XSA。
- `scripts/run_snn_replay_system.ps1`：可复现入口。
- `constraints/PYNQ-Z2_v1.0.xdc`：PYNQ-Z2 v1.0 board-reference master XDC，未启用不存在的 PL 端口。
- `artifacts/snn_replay_system.bit`：目标 part 的候选 bitstream。
- `artifacts/snn_replay_system.xsa`：包含 HWH、sysdef、PS7 初始化文件和 bitstream 的 XSA。
- 详细结果见 [HLS5A3_SYSTEM_RESULTS.md](reports/HLS5A3_SYSTEM_RESULTS.md)。

## HLS-5A.4：Vitis standalone 回放程序

`vitis/snn_replay_standalone/` 提供寄存器协议、三组 golden case C header、自动生成脚本和 `main.c`。当前已完成源代码与 standalone BSP 语法检查；正式 ELF 和板端 UART 回放尚未宣称完成。详见 [HLS5A4_VITIS_STANDALONE_RESULTS.md](reports/HLS5A4_VITIS_STANDALONE_RESULTS.md)。


### UART1 配置说明

PS7 的 UART1 需要同时设置外围设备使能和 MIO 路由，不能只设置 `PCW_EN_UART1`：

```text
PCW_UART1_PERIPHERAL_ENABLE=1
PCW_UART1_UART1_IO=MIO 48 .. 49
```

旧生成的 `snn_system_project_bitstream/project/snn_replay_system.xpr` 是修正前的工作副本；修正后的可查看工程为 `snn_system_project_bitstream_uart1/project/snn_replay_system.xpr`。最终 XSA/bitstream 已覆盖更新到 `artifacts/`。

### AXI Interconnect 与 SmartConnect

当前 Tcl 明确创建的是 `xilinx.com:ip:axi_interconnect:2.1`，不是 SmartConnect。Vivado 标记 `discontinued` 表示该 IP 已不推荐用于新设计，但在当前 Vivado 2025.1 中仍能生成、综合、实现和打包 XSA。当前拓扑只有 PS M_AXI_GP0 到一个 AXI-Lite S_AXI，功能上没有立即影响；后续若迁移到 SmartConnect，必须重新生成 BD、重新验证地址映射、时序、资源和 XSA。
