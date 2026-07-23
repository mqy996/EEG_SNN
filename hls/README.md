# HLS 协同设计状态

HLS（High-Level Synthesis，高层次综合）是将受约束的 C/C++ 算法描述综合为 FPGA RTL 的流程；`csim` 是 C 级仿真，`csynth` 是综合阶段。二者都不是板端运行或功耗测量。

**当前状态：HLS-0 已冻结 Phase-1 的外部接口；仓库仍只有 PyTorch 浮点/定点软件参考。** 尚未提交 HLS C++ 源码、黄金向量、csim/csynth 报告、Vivado 工程或板端证据。完整图、布局与术语请先阅读 [Direct-current Hybrid-SNN 与 HLS Phase-1 接口契约](../docs/direct_current_hls_architecture.md)。

## Phase-1 范围

Phase-1 只实现单样本的 Hybrid LIF 读出头：48 个时间步、32 个特征通道、脉冲计数/发放率和 `Linear(32, 2)` 分类器。CNN、ReLU、GroupNorm（组归一化）与自适应平均池化留在软件参考侧，它们不是本阶段 HLS 交付物。

```text
软件前端特征 [B, 32, 48]
  → 逐样本布局转换为 [48][32]
  → Q12.6 feature_current_q
  → 48 步 subtract-reset LIF
  → spike_count[32] / rate_q[32]
  → 冻结 Linear(32, 2)
  → logits_q[2]
```

## 冻结的外部接口

| 项目 | Phase-1 契约 |
|---|---|
| 目标器件 | `xc7z020clg400-1`。这是目标规划，不是已完成的实现或资源报告。 |
| 时钟假设 | 100 MHz。此为规划假设，不是已验证的时序或 Fmax。 |
| 输入 | `feature_current_q[48][32]`：时间优先，`t=0…47` 在第 0 维，32 个 CNN 特征通道在第 1 维；每个元素为有符号 Q12.6 整数。 |
| 软件到 HLS 布局 | Python/软件参考的单样本形状为 `[32, 48]`（通道、时间）；边界处转为 `[48][32]`（时间、通道）。这是转置适配，不改变数值、时间顺序或通道编号。 |
| 编码与 LIF | Direct-current（直流编码）；`beta=0.90`、`threshold=0.5`、subtract-reset。外部 Q12.6 常量为 `beta_q=58`、`threshold_q=32`。`beta_q=58` 表示 `58/64=0.90625`，不是精确十进制 0.90。 |
| 状态复位 | 每次 top function 调用前，32 个膜电位和 32 个脉冲计数都清零；不跨样本、被试或数据折保持状态。 |
| 模型常量 | `weight_q[2][32]` 与 `bias_q[2]`：有符号 Q12.6，来自版本化模型常量头；无运行时权重加载。 |
| 输出 | `logits_q[2]`：两个未归一化分类分数，以保留 6 个小数位缩放的有符号宽整数对外表示；读取语义为 raw integer `/ 64`；无 softmax。 |
| 尚未冻结的内部细节 | 乘法/累加器/膜电位的最小安全位宽、舍入、溢出与饱和策略，由 HLS-1 的范围分析和黄金向量对齐固定。 |

当前 `src/dc_eeg/snn_hardware.py` 的 Q12.6 路径是软件可行性参考，而不是已综合的 HLS 内核。HLS-1 必须将固定输入布局、版本化权重/偏置、调用级复位以及输出缩放写入可测试的 C++ 接口，并用黄金向量验证。

## 证据边界与后续阶段

软件预研把 Q12.6 作为第一版 HLS 候选；目标器件和 100 MHz 时钟也只是在该软件预研中使用的规划条件。现有 SynOps、存储和延迟数值均为软件代理，不能解释为 FPGA 实测能耗或已实现延迟。详细软件结果见 [SNN-4 定点数与 FPGA 可行性](../experiments/channel8_snn_hardware/RESULTS.md)。

后续顺序应为：

1. 导出版本化 Q12.6 常量与黄金输入/输出向量，验证 `[32, 48] → [48][32]` 转置和每调用复位；
2. 实现并测试固定接口的 C++ 参考与 HLS top function；
3. 运行并记录 `csim`；
4. 运行并记录 `csynth`，包括工具版本、目标器件、时钟约束、资源、延迟和 II；
5. 只有保留 bitstream/XSA、主机日志和输出对比后，才讨论板端回放；功耗结论还需要明确仪器与测量方法。

因此，目前不作 HLS 完成、Vivado 已通过、时序已收敛、板端部署或实测低功耗的结论。