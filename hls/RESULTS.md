# HLS-3 综合结果：Direct-current Hybrid LIF head

## 结论

**HLS-3 C 综合：PASS。** 已使用 Vitis HLS 2025.1 对 HLS-2 完全相同的 Q12.6、无浮点 Hybrid LIF head 执行 C 综合，目标器件为 `xc7z020clg400-1`，时钟约束为 10.00 ns（100 MHz）。综合报告中顶层 estimated clock 为 7.249 ns，对应 estimated Fmax 137.95 MHz；因此从 **C 综合估计** 看，10 ns 约束有正裕量。

这不是布局布线后的时序结论，也不是 bitstream、板端运行或功耗结论。

## 可复现配置

| 字段 | 实际值 |
|---|---|
| 工具 | Vitis HLS 2025.1，Build 6135595（2025-05-21） |
| Flow | Vivado IP Flow Target / `v++ -c --mode hls` |
| Top function | `hybrid_lif_head_q12_6` |
| Target part | `xc7z020-clg400-1` |
| Clock constraint | 10.00 ns / 100 MHz |
| CSim | HLS-2 golden cases：3/3 PASS |
| CSynth | completed successfully |

运行入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File hls/hybrid_lif_head/scripts/run_csynth.ps1
```

脚本会加载本机 Vitis/Vivado 2025.1 环境，并把完整工具输出写入被忽略的 `hls/hybrid_lif_head/logs/hls_run_csynth.log`。原始综合报告位于被忽略的 `hls/hybrid_lif_head/hls/syn/report/csynth.rpt`。

## 综合摘要

数据来自 Vitis HLS 2025.1 的 `csynth.rpt` 顶层表格；百分比是相对于目标器件资源的工具估计。

| 指标 | 报告值 | 解释 |
|---|---:|---|
| Estimated clock | 7.249 ns | C 综合估计的时钟周期 |
| Estimated Fmax | 137.95 MHz | 由综合估计时钟换算的最大频率 |
| Top latency | 1688 cycles | 单次顶层调用的估计延迟 |
| Top latency @ 100 MHz | 16.880 µs | `1688 × 10 ns` |
| Interval | 1689 cycles | 报告的顶层 interval；当前报告没有独立、明确的 top II 字段，因此不把它称为 II |
| BRAM_18K | 0（0%） | 综合估计 |
| DSP | 33（15%） | 综合估计 |
| FF | 1980（1%） | 综合估计 |
| LUT | 2405（4%） | 综合估计 |
| URAM | 0 | 综合估计 |

顶层报告还给出 0.05 ns 的 slack 字段。这里同时保留报告的 `Estimated clock = 7.249 ns` 和顶层表格中的 slack，不将任一字段解释为 post-place-and-route 时序。

## 结果如何理解

1. **功能层面**：CSim 的 3/3 黄金用例通过，说明当前 C++ HLS top 与 Q12.6 契约逐位一致。它不等于完整模型在 EEG 数据集上的分类 Accuracy。
2. **综合层面**：CSynth 成功并给出了资源/延迟估计，说明当前读出头可以进入后续 RTL/IP 设计流程。
3. **性能层面**：在 10 ns 综合约束下，工具估计周期为 7.249 ns；这只是综合阶段的正向信号。仍需 Vivado synthesis/implementation 才能判断真实时序收敛。
4. **资源层面**：当前基线使用 33 个 DSP、2405 个 LUT、1980 个 FF，BRAM/URAM 为 0。模型权重和偏置目前是 CSim/CSynth 的只读数组接口，不应误写成已完成的 AXI、DMA 或片上 ROM 集成。

## 证据等级与明确未完成项

| 证据等级 | 本任务状态 | 能支持的结论 |
|---|---|---|
| 软件代理 | 已有 | 定点范围和算法参考 |
| Vitis CSim | 已完成 | HLS C++ 与黄金向量逐位一致 |
| Vitis CSynth | **本报告已完成** | 综合估计资源、延迟、时钟 |
| Vivado implementation | 未执行 | 暂不能声称布局布线后达到 100 MHz |
| Bitstream/板端回放 | 未执行 | 暂不能声称板端准确率、吞吐或端到端延迟 |
| 功耗测量 | 未执行 | 暂不能声称能耗或低功耗 |

本报告不包含自动生成的 Vitis 工作目录、日志、RTL、IP 压缩包或 checkpoint；这些产物被 `.gitignore` 忽略并在提交前清理。
