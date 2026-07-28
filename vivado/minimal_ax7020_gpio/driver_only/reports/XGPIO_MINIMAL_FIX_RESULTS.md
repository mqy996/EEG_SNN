# 官方 XGpio 最小修复实验结果

日期：2026年7月28日

## 1. 实验目的

只替换软件访问层，不修改现有 AX7020 模板对齐硬件系统：

```text
现有 bitstream/XSA
        +
Xilinx 官方 XGpio standalone 驱动
```

本实验不加入 ILA、不修改 AXI Interconnect、不重新生成 Vivado bitstream，也不接入 SNN。

## 2. 参考工程

只读查看：

```text
D:\ZYNQ7020_study\Vitis_project\axi_gpio
```

参考工程使用 AXI GPIO 官方驱动模式，当前实验采用同一类 API：

```c
XGpio_Initialize()
XGpio_SetDataDirection()
XGpio_DiscreteWrite()
XGpio_DiscreteRead()
```

当前基线 AXI GPIO 地址：

```text
0x41200000
```

## 3. 构建结果

Vitis 2025.1 编译成功：

```text
vivado/minimal_ax7020_gpio/driver_only/artifacts/ax7020_xgpio_driver.elf
```

使用的是现有基线：

```text
vivado/minimal_ax7020_gpio/artifacts/template_aligned/ax7020_gpio_template_aligned.bit
vivado/minimal_ax7020_gpio/artifacts/template_aligned/ax7020_gpio_template_aligned.xsa
```

没有重新生成 Vivado 硬件工程。

## 4. 板端 UART 结果

JTAG 下载和 UART 输出正常，唯一启动标记如下：

```text
BOOT_XGPIO
UART_OK
XGPIO_BASE=0x41200000
XGPIO_INIT_BEGIN
XGPIO_INIT_STATUS=0
XGPIO_INIT_DONE
XGPIO_DIR_BEGIN
```

程序没有继续输出：

```text
XGPIO_DIR_DONE
XGPIO_WRITE_BEGIN
XGPIO_READ_BEGIN
DONE
```

## 5. 结论

### 官方驱动没有修复问题

`XGpio_Initialize()` 成功返回，但第一次真正的 AXI GPIO 配置访问：

```c
XGpio_SetDataDirection(&gpio, 1, 0x00000000U);
```

在 `XGPIO_DIR_BEGIN` 之后阻塞。

因此可以排除以下解释：

- 不是因为只使用了裸 `Xil_In32/Xil_Out32`；
- 不是简单更换为官方 XGpio API 就能解决；
- 不是 Vitis ELF 没有成功下载；
- 不是 UART 或 PS7 软件初始化完全失败。

当前证据更接近：

> 第一个 AXI GPIO 写事务在硬件访问层仍未完成，官方驱动没有绕过该问题。

## 6. 按要求停止后续实验

本次实验失败后立即停止，没有执行：

- ILA；
- SmartConnect/AXI Interconnect 对比；
- 新的 Vivado 硬件重建；
- SNN 接入；
- 其它软件访问顺序实验。

下一步是否继续，等待单独决定。
