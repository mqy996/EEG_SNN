# E1 Vivado 重建结果

状态：**PASS**
日期：2026-07-31

## 冻结配置

```text
Vivado 2025.1
FPGA: xc7z020clg400-2
DDR: MT41J256M16 RE-125
FCLK0: 50 MHz / 20 ns
UART1: MIO 48/49
M_AXI_GP0: enabled
HP: disabled
SNN AXI base: 0x43C00000
```

## 工程位置

```text
D:/eeg_fpga/snn_hybrid_eeg/vivado/evidence_rebuild/run_20260731_attempt1/project/snn_evidence_system.xpr
D:/eeg_fpga/snn_hybrid_eeg/vivado/evidence_rebuild/run_20260731_attempt1/artifacts/snn_evidence_system.bit
D:/eeg_fpga/snn_hybrid_eeg/vivado/evidence_rebuild/run_20260731_attempt1/artifacts/snn_evidence_system.xsa
```

## 构建结果

- Vivado 2025.1 启动成功；
- PS7 模板导入成功；
- Processor System Reset 已加入；
- SmartConnect VLNV：`xilinx.com:ip:smartconnect:1.0`；
- SNN AXI wrapper 地址段固定为 `0x43C00000`；
- synthesis PASS；
- implementation PASS；
- bitstream PASS；
- XSA PASS；
- 路由错误为 0。

## 报告位置

```text
artifacts/utilization_synth.rpt
artifacts/utilization_impl_hierarchical.rpt
artifacts/timing_synth.rpt
artifacts/timing_impl.rpt
artifacts/power_impl.rpt
artifacts/drc_impl.rpt
artifacts/route_status_impl.rpt
artifacts/ip_status.rpt
artifacts/ps7_properties.rpt
```

## 当前实现后关键结果

- 完整系统顶层 routed hierarchy：8902 LUT、21076 FF、34 DSP、0 BRAM；
- SNN AXI wrapper hierarchy：8416 LUT、20461 FF、34 DSP；
- HLS instance hierarchy：7725 LUT、640 FF、34 DSP；
- WNS：4.776 ns；
- TNS：0 ns；
- WHS：0.072 ns；
- THS：0 ns；
- 时钟：50 MHz；
- 所有用户时序约束满足；
- 完全布线 nets：26818；
- 布线错误：0。

## 功耗边界

`artifacts/power_impl.rpt` 是完整 PS7 + SmartConnect + SNN 系统的 Vivado post-route tool estimate：

- Total On-Chip Power：1.769 W；
- Dynamic：1.626 W；
- Device Static：0.143 W；
- Confidence：Medium。

Vivado 提示 reset switching activity 可能使无向量功耗估计不准确，因此该数值不能写成开发板实测功耗。

## 错误处理

Vivado 主构建第一次尝试即 PASS。此前生成 Tcl 时 PowerShell 的 `utf8NoBOM` 参数错误已通过 Python 无 BOM UTF-8 写入修复，未进入 Vivado 构建错误重试；没有第二次 Vivado 修复尝试。
