# SmartConnect AXI GPIO A/B 对照实验结果

- **日期**：2026-07-28
- **开发板**：AX7020，JTAG 目标 `xc7z020_1`
- **串口**：COM5，115200 baud
- **对照变量**：仅将当前 AXI Interconnect 替换为 SmartConnect

## 1. 实验目的

当前 template-aligned 工程使用 AXI Interconnect 时，官方 XGpio 程序停在：

```text
XGPIO_DIR_BEGIN
```

参考工程使用 SmartConnect，且用参考 XSA 构建的干净 XGpio 程序能够完成 AXI 写事务。因此本实验只替换 AXI 互连 IP，判断 SmartConnect 是否能够修复当前问题。

## 2. 保持不变的内容

- PS7 template-aligned 配置；
- 器件 `xc7z020clg400-2`；
- DDR `MT41J256M16 RE-125`；
- FCLK0 = 50 MHz；
- UART1；
- `M_AXI_GP0`；
- AXI GPIO 地址 `0x41200000`；
- `FCLK_RESET0_N → proc_sys_reset/ext_reset_in` 直接连接；
- `proc_sys_reset/peripheral_aresetn` 同时连接 SmartConnect 和 AXI GPIO；
- 官方 XGpio 测试源码。

## 3. 只改变的内容

```text
原设计：
PS7/M_AXI_GP0 → AXI Interconnect → AXI GPIO/S_AXI

A/B 设计：
PS7/M_AXI_GP0 → SmartConnect → AXI GPIO/S_AXI
```

SmartConnect 配置：

```text
VLNV: xilinx.com:ip:smartconnect:1.0
NUM_SI: 1
NUM_MI: 1
ACLK: FCLK_CLK0
ARESETN: peripheral_aresetn
```

## 4. 构建结果

Vivado 2025.1 构建成功：

```text
SYNTH_STATUS=已完成
IMPL_STATUS=已完成
DRC Errors=0
Bitstream=生成成功
XSA=生成成功
```

HWH 检查确认：

```text
smartconnect 存在
axi_interconnect 不存在
M_AXI_GP0 存在
FCLK0=50 MHz
DDR=MT41J256M16 RE-125
AXI GPIO=0x41200000
C_EXT_RESET_HIGH=0
```

## 5. 板端结果

使用 SmartConnect A/B bitstream、匹配 XSA 生成的 FSBL 和 XGpio ELF，在同一块开发板上运行。

完整 UART 输出：

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
XGPIO_READ_VALUE=0x12345678
XGPIO_READ_DONE
XGPIO_RESULT=PASS
DONE
```

## 6. 结论

### 结论：SmartConnect A/B 通过，当前问题被修复

在保持 PS7、DDR、FCLK、UART、地址和复位策略不变的情况下，仅将 AXI Interconnect 替换为 SmartConnect 后：

- `XGpio_SetDataDirection()` 不再卡死；
- AXI GPIO 写事务正常完成；
- AXI GPIO 读事务正常完成；
- 程序最终输出 `XGPIO_RESULT=PASS` 和 `DONE`。

因此，目前可以高度确定：

> 当前首次 AXI 事务卡死的主要原因位于 AXI Interconnect 拓扑、参数或其与 AXI GPIO/复位链路的组合，而不是 DDR、XGpio 驱动或 GPIO 地址。

本实验不能进一步区分“AXI Interconnect IP 本体参数”和“Interconnect 复位/接口连接细节”哪个是唯一根因，但已经足以确定 SmartConnect 是当前可工作的修复方案。

## 7. 下一步建议

暂时不要继续做 ILA 或 DDR 对照实验。建议：

1. 将 SmartConnect 版本保留为当前板端基线；
2. 在 SmartConnect 版本上继续接入 HLS/SNN wrapper；
3. 保留原 AXI Interconnect 失败工程作为失败对照证据；
4. 后续如果需要论文级根因分析，再单独做 Interconnect 复现和 AXI 握手 ILA。

## 8. 产物

```text
artifacts/smartconnect_ab/ax7020_gpio_smartconnect_ab.bit
artifacts/smartconnect_ab/ax7020_gpio_smartconnect_ab.xsa
artifacts/smartconnect_ab/ax7020_gpio_smartconnect_ab.hwh
artifacts/smartconnect_ab/ax7020_xgpio_smartconnect_ab.elf
artifacts/smartconnect_ab/ax7020_smartconnect_ab_fsbl.elf
artifacts/smartconnect_ab/smartconnect_ab_board_replay.log
```
