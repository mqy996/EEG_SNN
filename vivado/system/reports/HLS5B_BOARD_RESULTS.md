# HLS-5B：真实开发板回放调试结果

**日期：2026-07-27**  
**状态：部分完成，AXI-Lite 板端回放阻塞**

## 已确认

- JTAG target：`localhost:3121/xilinx_tcf/Digilent/210512180081`。
- 目标器件：`xc7z020`，目标 part `xc7z020clg400-1`。
- Vivado 2025.1 已生成 bitstream/XSA，DRC 0 errors，Bitgen PASS。
- Vivado Hardware Manager 下载 bitstream：`PROGRAM_RESULT=PASS`，startup status HIGH。
- Vitis 2025.1 platform/BSP/FSBL 和 standalone ELF 构建 PASS。
- COM5 为 Silicon Labs CP210x USB-UART，115200-8N-1；UART1/MIO48/49 独立 smoke test 输出 `UART_TEST_START`、`UART_TEST_UART1`。
- FCLK0 配置为 50 MHz，PS `M_AXI_GP0` 为软件访问路径。

## 当前失败点

SNN standalone ELF 在首次访问 `0x43C00000` 的 `VERSION` 寄存器时阻塞，因此没有可靠的三个 golden case 板端 PASS 证据。串口本身正常，问题发生在 UART 之后的 AXI/PL 路径，不是 BS=1 或 HLS 数值误差。

独立 AXI smoke test 的有效输出只有：

```text
AXI2_START
```

预期的 `AXI2_VERSION=0x00010001` 没有返回。

## 当前硬件配置

- PS7：Zynq-7020，FCLK0 50 MHz。
- AXI：当前 Tcl 已从 discontinued `axi_interconnect:2.1` 切换为 `smartconnect:1.0`，单主单从。
- Reset：PS `FCLK_RESET0_N` 直接连接到 SmartConnect 和 wrapper AXI reset；此前自定义 reset 模块的极性问题已不再参与当前 BD。
- Address：wrapper `0x43C00000-0x43C0FFFF`。
- HP0..3 未启用；数据路径不是 DDR DMA。

## 下一轮调试顺序

1. 在 Vivado BD 中加入标准 AXI GPIO/AXI BRAM slave，使用同一个 GP0/SmartConnect 地址路径，先证明 PS→SmartConnect→标准 IP 可读写。
2. 若标准 IP 可访问，再把问题缩小到 `snn_axi_memory_window` 的 AXI-Lite 接口实现或模块参考封装。
3. 若标准 IP 也阻塞，检查 PS GP0 的地址重映射、FCLK/reset 运行状态和 Vitis 初始化顺序。
4. AXI 读事务通过后，再重新运行三个 golden case，并只在 UART 出现以下三行时写板端 PASS：

```text
VECTOR=threshold_edge PASS
VECTOR=signed_currents PASS
VECTOR=rounding_and_reset PASS
```

## 证据边界

当前可以向导师汇报：**板卡识别、bitstream 下载、Vitis ELF 构建和 UART smoke test 已完成；AXI-Lite 板端回放仍需继续调试。** 不能把前一轮软件/RTL PASS 或串口 smoke test 表述成真实板端 SNN PASS。
