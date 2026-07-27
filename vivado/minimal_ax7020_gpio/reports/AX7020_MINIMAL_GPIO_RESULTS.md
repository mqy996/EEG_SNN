# AX7020模板对齐最小AXI GPIO验证结果

日期：2026年7月27日

## 1. 任务边界

本验证工程没有修改参考模板：

```text
D:\ZYNQ7020_study\ZYNQ_project\project_AX7020_template
```

模板的 `.xpr`、HWH 和 PS7 参数文件在任务前后 SHA-256 完全一致。新工程只写入：

```text
snn_hybrid_eeg/vivado/minimal_ax7020_gpio/
```

## 2. 最终采用的实现

最终没有继续手动拼接 PS7 参数，而是从模板 Block Design 生成独立的 PS7 Tcl 参考脚本，再在新工程中创建最小系统：

```text
PS7 M_AXI_GP0
        |
        v
AXI Interconnect
        |
        v
AXI GPIO
```

AXI 时钟为 PS7 `FCLK_CLK0=50 MHz`。AXI 复位采用与本机已有 `Vitis_project\axi_gpio` 工程一致的连接：

```text
PS7 FCLK_RESET0_N（低有效）
        |
        v
proc_sys_reset/ext_reset_in（低有效）
        |
        v
proc_sys_reset/peripheral_aresetn
```

没有增加反相器。

## 3. 模板对齐证据

最终 HWH 中确认：

| 参数 | 最终值 |
|---|---:|
| FPGA part | `xc7z020clg400-2` |
| `M_AXI_GP0` | enabled |
| HP0~HP3 | disabled |
| `FCLK0` | 50 MHz |
| IO PLL FBDIV | 30 |
| IO PLL | 1000 MHz |
| FCLK0 divisor | 5 |
| UART divisor | 10 |
| DDR | `MT41J256M16 RE-125` |
| UART1 | MIO48/49 |
| MIO48/49电平 | LVCMOS 1.8 V |
| AXI GPIO | `0x41200000~0x4120FFFF` |

最终 HWH 文件：

```text
vivado/minimal_ax7020_gpio/artifacts/template_aligned/ax7020_gpio_template_aligned.hwh
```

## 4. 构建结果

Vivado 2025.1 已完成：

- Block Design 生成：通过；
- 综合：`synth_design Complete!`；
- 实现：通过；
- bitstream：生成成功；
- XSA：生成成功；
- DRC：无错误；
- timing/utilization报告：已保存。

产物：

```text
artifacts/template_aligned/ax7020_gpio_template_aligned.bit
artifacts/template_aligned/ax7020_gpio_template_aligned.xsa
artifacts/template_aligned/ax7020_gpio_template_aligned.hwh
```

Vitis 2025.1 已完成：

- standalone platform：生成成功；
- GPIO smoke test：编译成功；
- ELF：生成成功。

产物：

```text
artifacts/template_aligned/ax7020_gpio_smoke.elf
artifacts/template_aligned/ax7020_gpio_data_first.elf
artifacts/template_aligned/ax7020_gpio_data_read_first.elf
artifacts/template_aligned/ax7020_gpio_template_aligned.xpfm
```

## 5. 板端验证

开发板通过 JTAG 识别为：

```text
xc7z020
```

串口为：

```text
COM5, 115200 baud
```

bitstream 已成功下载，XSCT 也成功下载 ELF 并运行 CPU。

### 5.1 修复复位方向前

最小工程曾将 `FCLK_RESET0_N` 经过反相器后连接到 `proc_sys_reset`。该连接是错误的，板端首次 AXI 读取卡在：

```text
GPIO_TRI_READ_BEGIN
```

### 5.2 修复复位方向后

采用直接低有效复位连接后，PS7、UART、JTAG 下载流程均可正常工作。但使用带有唯一启动标记的当前 ELF 复测时，第一次 AXI 访问仍然阻塞：

```text
BOOT_DATA_FIRST_RESETFIX
UART_OK
GPIO_BASE=0x41200000
GPIO_WRITE_BEGIN
```

在 `GPIO_WRITE_BEGIN` 之后没有出现 `GPIO_WRITE_DONE`。

另一个“先读 DATA”的程序同样停在：

```text
BOOT_DATA_READ_FIRST
UART_OK
GPIO_BASE=0x41200000
GPIO_DATA_READ_BEGIN
```

之前 UART 捕获中出现过的 `GPIO_WRITE_DONE`、`GPIO_DATA_READ` 和 `DONE` 字符串来自串口缓冲中的前一轮程序输出，不能作为当前 ELF 已通过的证据。后续报告必须使用唯一启动标记区分当前回放与残留串口数据。

因此本轮已经确认：

1. PS7 可以正常启动；
2. UART1 配置正确；
3. bitstream、XSA、Vitis standalone ELF 的地址契约一致；
4. 复位反相错误已修复，但第一次 AXI 事务仍未完成。

### 5.3 当前仍可复现的现象

如果程序启动后把第一次 AXI 访问设置为读取：

```text
GPIO_DATA_READ_BEGIN
```

或者：

```text
GPIO_TRI_READ_BEGIN
```

程序会停在该阶段，后续 UART 输出不再出现。

因此当前最小验证的结论不是“所有 AXI 访问已经完全正常”，而是：

> 在当前可辨识的最新回放中，程序启动后的第一次 AXI 写事务和第一次 AXI 读事务都可能阻塞；串口残留输出曾经造成“后续读写成功”的假象，必须用唯一启动标记重新采集。

`GPIO_TRI_READ=0xFFFFFFFF` 是当前输出型 AXI GPIO 的观测值，不能直接当作方向寄存器正确性的充分证明，后续应使用官方 `XGpio` 驱动或进一步读取/写入验证。

## 6. 对 SmartConnect 和 PS7配置的结论

### 目前不能把问题归因于 SmartConnect，也不能排除它

本次模板对齐工程使用的是传统 AXI Interconnect。复位方向修正后，首次 AXI 事务仍然阻塞，因此当前证据只能说明：

- PS7 模板差异不是唯一根因；
- 复位反相是一个真实错误，但修复后问题仍存在；
- AXI Interconnect 版本目前没有通过“首次事务”验证；
- 之前 SmartConnect 版本的首次读取失败，不能单独证明 SmartConnect 是根因，也不能据此排除 SmartConnect。

下一轮应使用同一套模板对齐 PS7 和同一套软件，单独替换 Interconnect/SmartConnect，避免同时改变多个变量。

### PS7配置差异确实存在，但不是全部原因

模板对齐修复了真实存在的差异：

- DDR型号；
- IO PLL；
- FCLK分频；
- UART分频；
- MIO电平；
- FPGA speed grade。

但即使完全按照模板生成，第一次 AXI 读事务仍然会阻塞。因此，PS7配置不一致是之前工程的问题之一，但不是当前“首次读取阻塞”现象的唯一原因。

### 本次暴露出的真实工程错误

之前最小工程的复位方向确实写反了。这会使 AXI 外设保持在错误的复位状态，是此前测试失败的重要原因之一。该错误已经修复。

## 7. 下一步建议

不要马上重新接入 SNN。下一步应在这个已经模板对齐的最小工程上继续做一个很小的 AXI 访问实验：

1. 用官方 `XGpio_Initialize`、`XGpio_SetDataDirection`、`XGpio_DiscreteWrite`、`XGpio_DiscreteRead` 替换裸 `Xil_In32/Xil_Out32`；
2. 测试启动后延时 1 ms、10 ms、100 ms 再执行第一次读；
3. 测试先写 DATA、先写 TRI、先读 DATA、先读 TRI 四种访问顺序；
4. 若仍存在首读阻塞，再用 ILA 观察 GP0/Interconnect 的 `ARVALID/ARREADY/RVALID/RREADY`；
5. 只有确认最小 AXI 访问协议稳定后，才接回 SNN AXI wrapper。

当前最小工程已经完成了“模板对齐、复位纠正、bitstream/XSA/ELF生成和板端启动验证”，但 AXI 第一个事务仍未通过，不能把它写成板端 AXI 数据通路完全通过。
