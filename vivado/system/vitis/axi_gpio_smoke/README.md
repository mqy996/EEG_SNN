# HLS-5B.2 AXI GPIO smoke test

独立验证 `PS M_AXI_GP0 -> SmartConnect -> AXI GPIO` 标准 AXI-Lite 路径。测试不访问 SNN wrapper `0x43C00000`，也不运行 golden replay。GPIO 为 32-bit 单通道输出，基地址 `0x41200000`。
