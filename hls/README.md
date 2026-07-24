# Hybrid LIF Head HLS 说明

本目录保存 Direct-current Hybrid-SNN 读出头的 HLS 协同设计文件。当前阶段只实现固定点 Hybrid LIF readout head，不代表完整 CNN-SNN 已经完成 FPGA 部署。

## 当前状态

- HLS-2：Q12.6 无浮点 CSim，3/3 黄金用例通过。
- HLS-3：Vitis HLS 2025.1 C 综合完成。
- HLS-4：Verilog RTL C/RTL 协同仿真完成，3 个测试用例、6/6 次 RTL transaction 通过。
- 目标器件：`xc7z020clg400-1`。
- HLS 约束：10 ns，也就是 100 MHz。

## 接口边界

软件参考模型将池化后的特征视为 `[B, 32, 48]`，HLS 读出头按 `[48][32]` 处理。每个时间步输入 32 个 Q12.6 电流，经过 48 步 Hybrid LIF 后输出脉冲计数、发放率和两类 logits。

当前 HLS 边界不包含：

- CNN 空间卷积和时间卷积；
- ReLU、GroupNorm 和自适应池化；
- AXI、DMA、DDR 或片上存储器系统集成；
- 完整 EEG 数据流和分类评估。

## 时钟说明

HLS-3 和 HLS-4 使用 100 MHz/10 ns 作为独立的综合与协同仿真约束。已有 CNN-LSTM Vivado 系统记录的 Zynq PS `FCLK_CLK0` 为 50 MHz/20 ns，这是后续系统集成的参考时钟，不是当前 SNN 已完成的板级验证结果。

## 运行验证

在已配置 Vitis HLS 2025.1 的环境中，从仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File hls/hybrid_lif_head/scripts/run_cosim.ps1
```

HLS-3 综合入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File hls/hybrid_lif_head/scripts/run_csynth.ps1
```

临时 Vitis、XSIM、日志和综合目录会被 `.gitignore` 忽略，不应作为源代码提交。

## 结果文档

- [HLS-3 综合结果](RESULTS.md)
- [HLS-4 RTL C/RTL 协同仿真结果](RTL_COSIM_RESULTS.md)
- [HLS Phase-1 接口契约](../docs/direct_current_hls_architecture.md)
- [Direct-current HLS 基线摘要](../docs/direct_current_hls_baseline_summary.md)