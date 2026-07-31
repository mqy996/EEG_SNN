# EEG 混合 SNN / HLS 基线仓库

这是给导师查看和复现实验的精简仓库，当前主线是：**Direct-current（直流）编码 + Hybrid LIF（混合漏积分发放）读出头 + Zynq-7020 AXI-Lite 回放接口**。

## 当前状态（2026-07-31）

| 层级 | 状态 | 入口 |
|---|---|---|
| 软件模型选择 | PASS | `docs/direct_current_hls_baseline_summary.md` |
| HLS CSim/CSynth/RTL | PASS | `hls/`、`vivado/system/` |
| Vivado 系统 | PASS | `vivado/evidence_rebuild/` |
| bitstream/XSA | PASS | `vivado/evidence_rebuild/artifacts/` |
| Vitis platform/application | PASS | `vitis/evidence_rebuild/` |
| 开发板 314 样本回放 | PASS | `vitis/evidence_rebuild/E3_RESULTS.md` |
| 资源、时序、功耗估计 | PASS | `docs/performance_report.md` |

核心板端证据为：314/314 个样本的 checksum、logit、spike count 与黄金值一致；分类正确 277/314，fold9 测试子集准确率 88.2166%。

> 重要边界：当前结果证明的是 **软件前端特征 → PS7 AXI-Lite → FPGA Hybrid LIF 读出头 → PS7** 的协同回放，不等于完整 CNN/GroupNorm 前端已经在 FPGA 上运行，也不等于在线 EEG 流水线。

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
$repo = 'D:\eeg_fpga\snn_hybrid_eeg'
& 'D:\vitis\2025.1\Vivado\bin\vivado.bat' -mode batch `
  -source "$repo\vivado\evidence_rebuild\scripts\create_evidence_system.tcl" `
  -tclargs $repo "$repo\vivado\evidence_rebuild\run_20260731_attempt1" project_bitstream
```

脚本使用只读的 `minimal_ax7020_gpio/tcl/template_ps7_ax7020_reference.tcl`，不会修改用户的 `project_AX7020_template`。

### 3. 运行 Vitis 回放

使用 `vivado/evidence_rebuild/artifacts/snn_evidence_system.xsa` 创建 Vitis 2025.1 platform，先编译 platform，再创建 standalone application，导入 `vitis/evidence_rebuild/latency_source/`，编译得到 ELF 后下载 bitstream/ELF 到开发板。完整过程与边界见 [证据链报告](docs/evidence_chain_report.md)。

## 目录导航

- `hls/`：HLS 源码、配置、golden contract 和 HLS 证据
- `vivado/system/src/`：AXI-Lite wrapper RTL
- `vivado/system/tb/`：三组 golden case 的 XSim testbench
- `vivado/system/vectors/`：可追踪的固定向量
- `vivado/system/tcl/`：SmartConnect 系统生成脚本
- `vivado/evidence_rebuild/`：当前器件的脚本、发布工件和 Vivado 报告
- `vitis/evidence_rebuild/`：平台包、回放源码、ELF 和板端结果
- `vivado/system/`：AXI wrapper、旧阶段仿真与历史证据
- `docs/`：架构、硬件来源、性能和完整证据链

## 汇报入口

1. [2026-07-31 SNN FPGA 全流程与结果总览](docs/2026-07-31-snn-fpga-full-flow-overview.md)
2. [硬件与工具来源](docs/hardware_provenance.md)
3. [性能、资源、时序与功耗](docs/performance_report.md)
4. [完整证据链](docs/evidence_chain_report.md)
5. [统一工件哈希](vivado/evidence_rebuild/EVIDENCE_MANIFEST.json)
