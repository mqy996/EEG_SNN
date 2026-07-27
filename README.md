# EEG 混合脉冲神经网络基线仓库

本仓库是给导师审阅和复现实验的 SNN/HLS/Vivado 基线仓库。当前验证对象是 **Direct-current 编码 + Hybrid LIF 读出头**，CNN/GroupNorm 前端仍然属于软件参考模型，不应把当前结果表述为完整 CNN-SNN 已经完成 FPGA 部署。

## 当前结论

截至 **2026 年 7 月 27 日**，固定向量回放链路已经完成开发板连接、bitstream 下载和 UART smoke test；AXI-Lite 读事务仍在板端调试：

- Vivado 2025.1 在 `xc7z020clg400-1` 上生成 bitstream/XSA；
- Zynq PS7 的 FCLK0 为 50 MHz；PS 通过 `M_AXI_GP0`、SmartConnect 访问 AXI-Lite SNN wrapper；
- 通过 JTAG 下载 bitstream，并由 Vitis 2025.1 生成 Cortex-A9 standalone ELF；
- COM5（Silicon Labs CP210x USB-UART，115200 8N1）已收到独立 UART smoke test；
- 当前 SNN ELF 访问 `0x43C00000` 时仍会阻塞，三个 golden case 尚不能写成板端 PASS；
- 板端验证只覆盖固定 Q12.6 向量和 HLS Hybrid LIF 读出头，不覆盖完整 EEG 输入、CNN 前端、整网准确率、实时吞吐或功耗。

完整证据见 [`vivado/system/reports/HLS5B_BOARD_RESULTS.md`](vivado/system/reports/HLS5B_BOARD_RESULTS.md)。

## 当前基线

| 项目 | 设置 |
|---|---|
| 输入 | Channel8 EEG 窗口，8 个通道 × 384 个采样点 |
| CNN 前端 | 逐点空间卷积 → 深度时间卷积 → ReLU → GroupNorm |
| 时间表示 | 自适应平均池化为 48 个时间步 |
| 编码 | Direct-current 直流编码 |
| 脉冲读出 | Hybrid LIF 漏积分发放读出头 |
| LIF 参数 | `beta=0.90`，`threshold=0.5` |
| HLS 定点 | Q12.6 |
| 目标器件 | `xc7z020clg400-1` |

## 已完成的证据

1. Direct-current + Hybrid LIF 软件基线和 Q12.6 定点契约。
2. HLS CSim、C 综合、Verilog C/RTL 协同仿真。
3. AXI-Lite memory-window wrapper 三组 golden case 的 RTL 验证。
4. Zynq PS7 + SmartConnect + 50 MHz FCLK0 + reset 的 Vivado project-mode 实现。
5. Vitis standalone platform/BSP/FSBL 和 Cortex-A9 ELF 构建。
6. 真实开发板 bitstream 下载、Vitis ELF 构建和 UART smoke test；AXI/板端回放问题已定位到下一轮调试。

## 关键文档

- [Direct-current HLS 架构与接口契约](docs/direct_current_hls_architecture.md)
- [教师阶段性汇报](docs/teacher_report.md)
- [Vivado PS/PL 系统说明](vivado/system/README.md)
- [板端回放证据](vivado/system/reports/HLS5B_BOARD_RESULTS.md)
- [AXI wrapper 三用例验证](vivado/system/reports/AXI_WINDOW_3CASE_RESULTS.md)
- [HLS 综合结果](hls/RESULTS.md)
- [HLS RTL 协同仿真结果](hls/RTL_COSIM_RESULTS.md)
- [数据集说明](data/README.md)

## 结果边界

- 当前硬件只实现 Hybrid LIF 读出头和 AXI-Lite 固定向量回放窗口。
- CNN、GroupNorm、EEG 数据预处理和整网分类仍未进入当前 bitstream。
- 当前板端 PASS 证明的是“PS→AXI wrapper→HLS readout→PS/UART”链路，不是整网 EEG 分类准确率。
- 后续若要形成论文级硬件结果，还需要完成 CNN 前端硬件化或明确软件/硬件分工，并测量整网准确率、吞吐、延迟、资源和功耗。

## 复现入口

数据文件不提交 Git。数据来源、形状和 SHA-256 校验值见 [`data/README.md`](data/README.md)。

Vivado 系统生成：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File vivado/system/scripts/run_snn_replay_system.ps1 `
  -Mode project_bitstream `
  -WorkDir D:/eeg_fpga/w_uart1_reset_20260727
```

Vitis standalone 构建：

```powershell
$env:SNN_REPLAY_XSA = (Resolve-Path vivado/system/artifacts/snn_replay_system.xsa).Path
$env:SNN_REPLAY_WORKSPACE = 'D:/eeg_fpga/vitis_board_replay_uart1_20260727'
$env:SNN_REPLAY_SOURCE = (Resolve-Path vivado/system/vitis/snn_replay_standalone).Path
& 'D:/vitis/2025.1/Vitis/bin/vitis.bat' -s `
  vivado/system/vitis/snn_replay_standalone/scripts/create_vitis_standalone_app.py
```

板端回放步骤和证据边界见 `HLS5B_BOARD_RESULTS.md`。
