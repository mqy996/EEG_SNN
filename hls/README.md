# HLS 协同设计状态

HLS（High-Level Synthesis，高层次综合）是将受约束的 C/C++ 算法描述综合为 FPGA RTL 的流程；`csim` 是 C 级仿真，`csynth` 是综合阶段。二者都不是板端运行或功耗测量。

**HLS-3 status: Q12.6 no-float C++ baseline completed Vitis HLS C synthesis for `xc7z020clg400-1` with a 10 ns clock constraint.** CSim 的 3 个黄金用例全部通过；CSynth 给出了资源、延迟和估计时钟结果。详细摘要见 [RESULTS.md](./RESULTS.md)。这仍不是 Vivado implementation、bitstream、板端回放或功耗实测。完整接口契约见 [Direct-current Hybrid-SNN and HLS Phase-1 interface contract](../docs/direct_current_hls_architecture.md)。

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
| 目标器件 | `xc7z020clg400-1`。HLS-3 已在该器件目标上完成 C 综合；这不等于已完成 Vivado 实现。 |
| 时钟假设 | 100 MHz，即 10 ns 综合约束。HLS-3 的估计时钟为 7.249 ns；这是综合估计，不是布局布线后的实测时序。 |
| 输入 | `feature_current_q[48][32]`：时间优先，`t=0…47` 在第 0 维，32 个 CNN 特征通道在第 1 维；每个元素为有符号 Q12.6 整数。 |
| 软件到 HLS 布局 | Python/软件参考的单样本形状为 `[32, 48]`（通道、时间）；边界处转为 `[48][32]`（时间、通道）。这是转置适配，不改变数值、时间顺序或通道编号。 |
| 编码与 LIF | Direct-current（直流编码）；`beta=0.90`、`threshold=0.5`、subtract-reset。外部 Q12.6 常量为 `beta_q=58`、`threshold_q=32`。`beta_q=58` 表示 `58/64=0.90625`，不是精确十进制 0.90。 |
| 状态复位 | 每次 top function 调用前，32 个膜电位和 32 个脉冲计数都清零；不跨样本、被试或数据折保持状态。 |
| 模型常量 | HLS-2/HLS-3 为便于 C 仿真和综合，`weight_q[2][32]` 与 `bias_q[2]` 作为 Q12.6 只读参数传入；后续若做 IP 集成，再决定是否绑定为版本化 ROM/静态常量。 |
| 输出 | `logits_q[2]`：两个未归一化分类分数，以保留 6 个小数位缩放的有符号宽整数对外表示；读取语义为 raw integer `/ 64`；无 softmax。 |
| HLS-2/HLS-3 已冻结的内部细节 | 乘法/累加器/膜电位使用 HLS-1 全域安全边界确定的显式 `ap_int` 位宽；舍入、溢出边界和 subtract-reset 语义已由三组黄金向量与 Vitis CSim 锁定。 |

当前 `src/dc_eeg/snn_hardware.py` 的 Q12.6 路径是软件可行性参考，而不是完整 CNN-SNN FPGA 内核。HLS-3 只综合了冻结的 Hybrid LIF 读出头，不包含 CNN 前端。

## HLS-3 复现

在安装 Vitis/Vivado 2025.1 且路径与脚本一致的 Windows 环境中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File hls/hybrid_lif_head/scripts/run_csynth.ps1
```

脚本通过 Vitis 2025.1 的 `v++ -c --mode hls` 入口执行 HLS C 综合；Vitis 2025.1 的 `vitis-run` 不提供本任务使用的 `--csynth` 选项。工具生成的 solution、日志、报告和压缩包均被 `.gitignore` 忽略，不应提交到仓库。

## 证据边界与后续阶段

- Python 软件代理：用于算法和定点范围预研，不是硬件资源或功耗测量。
- Vitis CSim：验证 C++ 与黄金向量逐位一致；不提供模型分类 Accuracy。
- Vitis CSynth：生成资源、延迟和估计时钟；不等于 Vivado implementation 或 bitstream。
- Vivado implementation：尚未执行，因此不能声称布局布线后达到 100 MHz。
- 板端回放与功耗：尚未执行，因此不能声称板端准确率、吞吐或能耗。

下一步可以在保持 HLS-3 基线不变的前提下，单独开展 ROM/接口绑定、循环并行化和 CNN 前端边界的优化实验，并为每次优化保留相同黄金向量和综合报告，避免把综合估计误写成完整部署结果。
