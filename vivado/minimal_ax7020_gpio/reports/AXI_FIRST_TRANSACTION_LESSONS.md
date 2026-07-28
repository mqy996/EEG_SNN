# AXI 首事务失败经验与当前 Zynq 基线

## 给导师的简短结论

在 AX7020 上，原 AXI Interconnect 版本的官方 XGpio 程序停在第一次方向寄存器写之前；在保持 PS7、DDR、时钟、UART、地址和复位连接不变的情况下，仅替换为 SmartConnect 后，程序完成了 GPIO 写入和读回，输出 `XGPIO_RESULT=PASS`。

因此当前可靠基线是 **PS7 + SmartConnect + AXI GPIO**。原 AXI Interconnect 版本作为失败对照保留。

## 这次失败说明了什么

- `XGpio_Initialize()` 成功不代表 AXI 链路已经验证；必须看到调用后的 marker，例如 `XGPIO_DIR_DONE`。
- 首次 AXI 写卡死时，应先保留失败工程，做单变量 SmartConnect/AXI Interconnect A/B，而不是同时改 DDR、PS7、地址、复位和软件。
- 旧 ELF 需要检查字符串和符号。PS MIO GPIO 程序运行成功，不能证明 AXI GPIO 正常。
- 如果已经出现 `XGPIO_READ_DONE`，但读回值不一致，应判断为 GPIO 回环/输入端问题，而不是 AXI 总线挂死。

## 当前 AX7020/Zynq 配置基线

```text
器件：xc7z020clg400-2
DDR：MT41J256M16 RE-125
FCLK0：50 MHz
串口：UART1，MIO48/49，LVCMOS 1.8 V
PS M_AXI_GP0：启用
AXI GPIO 地址：0x41200000
复位：FCLK_RESET0_N 直接连接 proc_sys_reset/ext_reset_in
外设复位：peripheral_aresetn 同时连接 SmartConnect 和 AXI GPIO
```

## 后续复用规则

1. SmartConnect 版本作为后续 HLS/SNN 接入的板端基线。
2. 每组 bitstream、XSA、HWH、FSBL 和 ELF 使用独立前缀，不覆盖失败证据。
3. 修改 PS7 或 DDR 后必须重新生成匹配的 FSBL、XSA 和 ELF。
4. 只有在需要保留 AXI Interconnect 或进行论文级根因分析时，才继续加入 ILA 分析 AXI 握手。

详细技术报告：

- `vivado/minimal_ax7020_gpio/reports/SMARTCONNECT_AXI_GPIO_AB_RESULTS.md`
- `vivado/minimal_ax7020_gpio/reports/AXI_GPIO_REFERENCE_COMPARISON.md`
