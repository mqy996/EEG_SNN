# HLS-5B.2：AXI GPIO 隔离验证结果

**日期：2026-07-27**  
**结论：FAIL（隔离实验成功，系统级 AXI 访问仍阻塞）**

## 实验目的

在不访问 SNN wrapper、不运行 SNN golden replay 的前提下，验证：

```text
Cortex-A9 → PS M_AXI_GP0 → SmartConnect → 标准 AXI GPIO
```

AXI GPIO 配置为 32-bit、单通道、全输出、无中断，地址为 `0x41200000`。

## 构建结果

- Vivado 2025.1 project-mode synthesis/implementation/bitstream：PASS。
- DRC：0 errors。
- Bitgen：PASS。
- Vitis 2025.1 platform/BSP/FSBL：PASS。
- GPIO smoke ELF：PASS，真实文件已生成。
- GPIO build ID：`AXI_GPIO_TEST_20260727_V1`。

## 板端结果

UART 有效输出：

```text
AXI_GPIO_TEST_20260727_V1
AXI_GPIO_BASE=0x41200000
```

随后程序在首次读取 GPIO TRI 寄存器时阻塞，未出现：

```text
AXI_GPIO_TRI=...
AXI_GPIO_READ1=...
```

这说明问题不只存在于 `snn_axi_memory_window`，因为标准 AXI GPIO 也无法完成 Cortex-A9 读事务。

## 结论

HLS-5B.2 将问题范围进一步缩小为系统级路径：

```text
PS M_AXI_GP0 / SmartConnect / AXI 时钟复位 / 地址映射 /
Vitis 初始化与 bitstream-ELF 配对
```

当前不能进入 SNN wrapper 修改，也不能进行三个 golden case 的板端验证。

## 下一步

1. 用 Vivado Block Design 自动连接规则重新生成 GP0→SmartConnect→AXI GPIO 的最小系统。
2. 检查 SmartConnect 的 `S00_ACLK/M00_ACLK`、`ARESETN` 和地址段是否与 XSA 一致。
3. 使用 AXI GPIO 的标准驱动/API 做一次读写，而不是直接裸 `Xil_In32`，排除寄存器偏移和 GPIO 配置问题。
4. 若标准驱动仍阻塞，再加入 ILA 观察 `ARVALID/ARREADY/RVALID/RREADY`。
5. 只有 GPIO 读写通过后，才回到 `snn_axi_memory_window`。
