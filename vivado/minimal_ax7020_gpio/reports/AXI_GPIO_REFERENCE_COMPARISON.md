# Vitis AXI GPIO 参考工程对照验证报告

- **日期**：2026-07-28
- **开发板/JTAG**：AX7020，`xc7z020`，Digilent JTAG-HS1 `210512180081`
- **串口**：COM5，115200 baud
- **目的**：确认 `D:\ZYNQ7020_study\Vitis_project\axi_gpio` 是否也会在第一次真实 AXI-Lite 访问处卡死。

## 1. 结论摘要

### 结论

**参考工程的硬件 AXI GPIO 通路可以正常完成真实 AXI-Lite 写事务；当前问题没有在参考硬件上复现。**

但是，参考工程原有的 `app_component.elf` 并不是有效的 AXI GPIO 对照程序：其字符串和符号表显示它实际主要使用 PS MIO GPIO（`XGpioPs_*`），没有使用 `XGpio_*` AXI GPIO 驱动。因此，仅运行参考工程原有 ELF 不能证明 AXI GPIO 正常。

为获得有效对照，本次额外使用**参考工程 XSA**单独生成了一个干净的官方 `XGpio` 程序，并在参考工程 bitstream 上运行。结果如下：

```text
BOOT_XGPIO
UART_OK
XGPIO_BASE=0x41200000
XGPIO_INIT_BEGIN
XGPIO_INIT_STATUS=0
XGPIO_INIT_DONE
XGPIO_DIR_BEGIN
XGPIO_DIR_DONE
XGPIO_WRITE_BEGIN
XGPIO_WRITE_DONE
XGPIO_READ_BEGIN
XGPIO_READ_VALUE=0x00000000
XGPIO_READ_DONE
XGPIO_RESULT=DATA_MISMATCH
DONE
```

关键点是：

- `XGpio_Initialize()` 成功；
- `XGpio_SetDataDirection()` 成功返回；
- `XGpio_DiscreteWrite()` 成功返回；
- 程序能够执行到 `DONE`；
- 失败的只是读回值为 `0`，这是因为 AXI GPIO 的输入端没有形成回环，不能视为 AXI 事务失败。

因此，当前最小工程中“卡在 `XGPIO_DIR_BEGIN`”不是 `XGpio` API 或编译方式本身造成的，而是当前 Vivado 硬件系统中仍存在 AXI 通路差异。

## 2. 参考工程原有 ELF 的有效性检查

参考工程原有 ELF：

```text
D:\ZYNQ7020_study\Vitis_project\axi_gpio\vitis\app_component\build\app_component.elf
```

板端输出：

```text
MIO Interrupt_gpio TEST!
```

对 ELF 进行字符串和符号检查发现：

- 存在 `XGpioPs_*`、`XScuGic_*` 等 PS MIO GPIO/中断符号；
- 没有发现 `XGpio_Initialize`、`XGpio_DiscreteWrite` 等 AXI GPIO 驱动符号；
- 其输出字符串也不是源码当前显示的 `AXI GPIO Interrupt TEST!`，而是 `MIO Interrupt_gpio TEST!`。

所以该 ELF 是历史遗留的 PS MIO GPIO 程序，不能作为 AXI GPIO 首事务的有效基准。

## 3. 有效对照实验

### 3.1 参考硬件产物

- 参考 bitstream：
  `D:\ZYNQ7020_study\Vitis_project\axi_gpio\axi_gpio.runs\impl_1\system_wrapper.bit`
- 参考 XSA：
  `D:\ZYNQ7020_study\Vitis_project\axi_gpio\vitis\axi_gpio.xsa`
- 参考硬件 AXI GPIO 地址：`0x41200000`

### 3.2 干净对照程序

没有修改参考工程，而是使用参考工程 XSA 在独立临时 Vitis 工作区生成新的 standalone 应用：

```text
任务产物：artifacts/ref_xgpio_app.elf
构建平台：参考工程 axi_gpio.xsa
测试程序：与当前 driver_only 官方 XGpio 测试相同
```

同时使用参考 XSA 对应的 FSBL 完成 PS/DDR 初始化，然后下载应用运行。

### 3.3 结果解释

结果完整经过：

```text
XGPIO_INIT_DONE
XGPIO_DIR_DONE
XGPIO_WRITE_DONE
XGPIO_READ_DONE
DONE
```

这证明参考工程的：

```text
PS M_AXI_GP0 → AXI SmartConnect → AXI GPIO S_AXI
```

能够完成至少一次 AXI GPIO 写事务。

`XGPIO_READ_VALUE=0x00000000` 不代表 AXI 读事务挂死，因为程序已经继续执行到 `XGPIO_READ_DONE` 和 `DONE`。它只说明 GPIO 输入端没有返回此前写入的值，当前工程没有建立输入输出物理回环。

## 4. 与当前最小工程的差异

| 项目 | 参考工程 | 当前 template-aligned 工程 |
|---|---|---|
| AXI 互连 | `axi_smc` / SmartConnect | `axi_interconnect_0` |
| FCLK0 | 50 MHz | 50 MHz |
| PS M_AXI_GP0 | 已启用 | 已启用 |
| UART | UART1 | UART1 |
| AXI GPIO 地址 | `0x41200000` | `0x41200000` |
| DDR 型号 | `MT41K256M16 RE-125` | `MT41J256M16 RE-125` |
| AXI GPIO 结果 | 官方驱动写入成功 | 在 `XGPIO_DIR_BEGIN` 停止 |

当前已知现象：

```text
XGPIO_INIT_DONE
XGPIO_DIR_BEGIN
```

之后没有 `XGPIO_DIR_DONE`。

## 5. 当前阶段能得出的科学/工程结论

1. **不是官方 `XGpio` 驱动普遍有问题。**
2. **不是 AXI GPIO 地址 `0x41200000` 本身必然错误。**参考工程使用相同地址并成功完成写事务。
3. **不是开发板、JTAG、UART 或 ARM 程序完全无法运行。**参考程序和新生成的对照程序均可通过 JTAG 下载和运行。
4. **当前工程的真实差异集中在 Vivado 硬件系统。**最显眼的差异是 AXI SmartConnect 与 AXI Interconnect 的不同，同时还存在 DDR/PS7 配置差异。
5. **本次实验不能证明 SmartConnect 是唯一根因。**它只能证明：已知可工作的参考拓扑包含 SmartConnect，而当前卡死拓扑使用 AXI Interconnect；因此 SmartConnect-only A/B 实验现在具有最高信息价值。

## 6. 下一步建议

不要立即加入 ILA，也不要同时修改 PS7、DDR、复位和地址。最小下一步应当是：

1. 保留当前 template-aligned PS7 设置不变；
2. 只把当前 `axi_interconnect_0` 替换为 SmartConnect；
3. 保持 GPIO 地址 `0x41200000` 不变；
4. 保持当前官方 `XGpio` ELF 不变；
5. 重新生成 bitstream/XSA；
6. 运行同一组 UART marker。

判据：

- 如果 SmartConnect 版本通过 `XGPIO_DIR_DONE`，说明问题高度集中在当前 AXI Interconnect 拓扑/参数/复位连接；
- 如果 SmartConnect 版本仍卡住，再进入 ILA 观察 GP0 的 `AWVALID/AWREADY/WVALID/WREADY/BVALID`；
- 如果两者都卡住，再回到 PS7 时钟、复位释放和板级初始化检查。

## 7. 保留的证据

本任务保留以下日志和脚本：

- `reference_board_replay.log`：首次未正确初始化时的失败记录；
- `reference_board_replay_with_fsbl.log`：参考旧 ELF 的运行记录；
- `reference_board_replay_with_reset2.log`：参考旧 ELF 在正确 reset/FSBL 流程下运行记录；
- `reference_xgpio_board_replay.log`：干净官方 XGpio 对照实验，结论性证据；
- `run_reference_xgpio.xsdb.tcl`：参考硬件回放脚本；
- `artifacts/ref_xgpio_app.elf`：参考 XSA 构建的干净官方 XGpio ELF；
- `artifacts/ref_fsbl.elf`：独立生成的参考 XSA 对应 FSBL。

参考工程和模板工程的原始源码、XSA、bitstream、BSP、ELF 均未被修改。
