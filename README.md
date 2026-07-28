# EEG 混合 SNN / HLS 基线仓库

这是给导师查看和复现实验的精简仓库，当前主线是：**Direct-current（直流）编码 + Hybrid LIF（混合漏积分发放）读出头 + Zynq-7020 AXI-Lite 回放接口**。

## 当前状态（2026-07-28）

| 层级 | 状态 | 证据 |
|---|---|---|
| HLS-6A Hybrid LIF | 已通过 C Simulation、C/RTL 协同仿真和实现 | `hls/hybrid_lif_head/` |
| HLS-6B wrapper RTL | **PASS**：`threshold_edge`、`signed_currents`、`rounding_and_reset` 三组 golden case，含两次重复运行、reset、busy/start/error | `vivado/system/reports/hls6b_wrapper_sim_console.log` |
| Vivado 系统 | **PASS**：PS7 + SmartConnect + AXI GPIO + SNN wrapper，`xc7z020clg400-2`、50 MHz | `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/` |
| 综合/实现 | **PASS**：实现完成，DRC 0 errors，50 MHz 时序通过 | `vivado/system/reports/hls6b_*.rpt` |
| bitstream/XSA/HWH | 已生成并保留 SHA-256 | 同上 artifacts 目录 |
| 开发板 SNN 回放 | 尚未宣称 PASS | 需要 HLS-6C Vitis standalone 回放和 UART 输出 |

> 重要边界：当前结果证明的是 **PS7 → SmartConnect → AXI-Lite wrapper → HLS Hybrid LIF → PS7** 的预板级系统和 RTL 行为，不等于完整 CNN/EEG 在线推理，也不等于已经完成板端 SNN 回放。

## 硬件地址与时钟

- 器件：`xc7z020clg400-2`
- PS7：DDR `MT41J256M16 RE-125`，`M_AXI_GP0` 已启用
- UART1：MIO48/49，115200 baud
- FCLK0：50 MHz，20 ns
- AXI GPIO：`0x41200000`
- SNN wrapper：`0x43C00000`
- 复位：`PS7 FCLK_RESET0_N → proc_sys_reset/ext_reset_in`，保持 active-low；`peripheral_aresetn` 分发到 SmartConnect、GPIO 和 wrapper
- 当前没有 HP/DMA/DDR 数据通路；输入通过 AXI-Lite indexed window 写入 PL 本地存储

## 复现入口

### 1. Wrapper RTL/XSim 三组 golden case

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File vivado/system/scripts/run_hls6b_wrapper_sim.ps1 `
  -WorkDir D:/eeg_fpga/snn_hybrid_eeg/vivado/system/hls6b_wrapper_sim_work
```

脚本会把 `vivado/system/vectors/*.mem` 复制到 XSim 工作目录，避免 `$readmemh` 因当前工作目录不同而找不到向量。

### 2. 重新生成 Vivado 系统

```powershell
vivado -mode batch `
  -source vivado/system/tcl/create_hls6b_smartconnect_snn.tcl `
  -tclargs D:/eeg_fpga/snn_hybrid_eeg D:/eeg_fpga/hls6b_build project_bitstream
```

实际使用时应先加载 Vivado 2025.1 环境；Windows 环境见 `vivado-tcl` / Vitis 项目规范。脚本使用只读的 `minimal_ax7020_gpio/tcl/template_ps7_ax7020_reference.tcl`，不会修改用户的 `project_AX7020_template`。

## 目录导航

- `hls/`：HLS 源码、配置、golden contract 和 HLS 证据
- `vivado/system/src/`：AXI-Lite wrapper RTL
- `vivado/system/tb/`：三组 golden case 的 XSim testbench
- `vivado/system/vectors/`：可追踪的固定向量
- `vivado/system/tcl/`：SmartConnect 系统生成脚本
- `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/`：教师可直接查看的 BD、HWH、XSA、bitstream
- `vivado/system/reports/`：仿真、综合、实现、时序和 DRC 报告
- `docs/`：架构和接口说明

## 下一步：HLS-6C

1. 用 `smartconnect_snn_wrapper_50mhz.xsa` 创建 Vitis standalone platform；
2. 编写 AXI-Lite 固定向量回放程序，先读 VERSION，再写 feature/weight/bias，启动并轮询 STATUS；
3. 输出 UART 日志，逐项比较两个 logits、32 个 spike counts 和 ERROR_STATUS；
4. 仅当 bitstream、XSA、ELF、输入身份、UART 日志和输出比较全部保留后，才报告“板端 SNN wrapper 回放 PASS”。
