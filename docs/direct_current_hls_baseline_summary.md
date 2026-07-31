# Direct-current Hybrid-SNN 的 HLS 与 FPGA 基线摘要

## 1. 当前网络

当前基线保留 CNN 前端，将读出部分替换为 Direct-current Hybrid LIF：

```text
Channel8 EEG
    ↓
CNN 前端：空间卷积 → 深度时间卷积 → ReLU → GroupNorm
    ↓
自适应平均池化：32 个特征 × 48 个时间步
    ↓
Direct-current 编码
    ↓
48 步 Hybrid LIF
    ↓
脉冲计数与平均发放率
    ↓
Linear(32, 2)
    ↓
两类输出
```

冻结参数为 `beta=0.90`、`threshold=0.5`。定点候选为 Q12.6。HLS Phase-1 的边界是 Hybrid LIF 读出头，不包含完整 CNN/GroupNorm 前端。

## 2. HLS 阶段结果

| 阶段 | 内容 | 状态 |
|---|---|---|
| HLS-0 | 架构图、硬件边界和接口契约 | 已完成 |
| HLS-1 | Q12.6 定点接口和软件参考 | 已完成 |
| HLS-2 | HLS CSim，3 个黄金用例 | 3/3 PASS |
| HLS-3 | Vitis HLS C 综合 | PASS |
| HLS-4 | Verilog RTL C/RTL 协同仿真 | PASS，3 个用例、6/6 次 transaction |

## 3. HLS-3 综合摘要

工具报告来自 Vitis HLS 2025.1，目标器件为 `xc7z020clg400-1`，时钟约束为 10 ns，也就是 100 MHz。

| 指标 | 报告值 |
|---|---:|
| Estimated clock | 7.249 ns |
| Estimated Fmax | 137.95 MHz |
| Top latency | 1688 cycles |
| Top latency @ 100 MHz | 16.880 µs |
| Interval | 1689 cycles |
| BRAM_18K | 0 |
| DSP | 33，约 15% |
| FF | 1980，约 1% |
| LUT | 2405，约 4% |
| URAM | 0 |

这些是 C 综合阶段的工具估计，不是布局布线后的时序结果。具体报告见 [HLS-3 综合结果](../hls/RESULTS.md)。

## 4. HLS-4 协同仿真摘要

HLS-4 使用 Vitis HLS 2025.1 和 XSIM 对生成的 Verilog RTL 进行 C/RTL 协同仿真。验证的正式顶层输出包括：

- `logits_q[2]`
- `spike_count_q[32]`
- 由脉冲计数得到的发放率
- 重复调用时的调用级状态复位

3 个黄金用例为 `threshold_edge`、`signed_currents` 和 `rounding_and_reset`，C 侧 3/3 通过，RTL 侧 6/6 次 transaction 完成。完整工具边界和故障记录见 [HLS-4 报告](../hls/RTL_COSIM_RESULTS.md)。

## 5. 当前系统级证据

当前完整系统的结果不再停留在 HLS OOC：

- Vivado post-implementation：完整 routed top 为 8902 LUT、21076 FF、34 DSP，50 MHz WNS +4.776 ns；
- Vitis standalone：平台和应用 ELF 构建通过；
- 开发板：314/314 样本 checksum、logit、count 一致，277/314 分类正确，fold9 子集准确率 88.2166%；
- 完整回放：326 us/sample，吞吐率 3067.48 samples/s；
- 功耗：1.769 W 为 Vivado vectorless estimate，不是板端测量。

完整来源、报告和哈希见 [硬件与工具来源](hardware_provenance.md)、[性能报告](performance_report.md) 和 [证据链报告](evidence_chain_report.md)。

## 6. 结论边界

当前证据可以支持：

- Q12.6 Hybrid LIF 读出头具有可复现的软件、C 仿真、综合和 RTL 协同仿真链路；
- 该读出头可以进入后续 Vivado/IP 集成阶段；
- 当前接口和状态复位行为已经有测试用例覆盖。

当前证据不能支持：

- 完整 CNN/GroupNorm 已经 HLS 化；
- 完整 CNN/GroupNorm 前端已经完成 FPGA 硬件化；
- 88.2166% 是完整 11-fold 平均准确率；
- 已经完成开发板实测功耗；
- HLS 读出头结果等于完整 EEG 分类系统的部署结果。

## 7. 后续工作

当前最小闭环已经完成。下一步应把重点放在完整 CNN/GroupNorm 前端的硬件边界评估、数据搬运架构和在线 EEG 输入方案，而不是把当前 AXI-Lite 回放准确率直接当作完整端到端部署准确率。
