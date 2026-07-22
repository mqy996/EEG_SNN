# SNN 阶段性实验汇报

**汇报日期：2026 年 7 月 22 日**  
**汇报范围：2026 年 7 月 17 日至 7 月 22 日完成的 6 个 Trellis 任务**

---

## 一、先给结论

这几天已经完成了 SNN 从“能不能训练”到“参数是否稳定、编码是否合理、结构是否值得扩展、是否具备定点实现基础”的一条完整探索链。

当前冻结的 SNN 候选为：

```text
Channel8 + GroupNorm 前端
+ direct-current 输入编码
+ Hybrid LIF head
+ beta = 0.90
+ threshold = 0.5
```

软件定点预研表明：

```text
Q12.6 是第一版 HLS 验证候选
Q16.8 作为高精度参考
Q8.4 暂不采用
```

但当前结论仍属于**探索性和兼容性协议证据**：

- 使用的是官方 balanced、class-blocked compatibility 数据顺序；
- 还不是严格 chronological replay；
- 还没有 HLS csim/csynth、板卡或功耗实测；
- 不能宣称 SNN 已经显著优于 ANN。

---

## 二、完成的 6 个任务

| 日期 | 任务 | 目的 | 状态 |
|---|---|---|---|
| 07-17 | Channel8 Hybrid-SNN pilot | 验证 Hybrid-SNN 能否训练并保持基本性能 | 完成 |
| 07-22 | SNN experiment roadmap | 将 SNN 拆成有门槛的实验路线 | 完成 |
| 07-22 | SNN stability sweep | 筛选稳定的 beta/threshold | 完成 |
| 07-22 | Encoding comparison | 比较 direct、amplitude/count、Delta | 完成 |
| 07-22 | Architecture ablation | 判断额外脉冲时间结构是否有收益 | 完成 |
| 07-22 | Fixed-point/FPGA feasibility | 判断是否值得进入定点和 HLS | 完成 |

其中第二项是路线统筹任务，另外五项包含实际代码、测试和 GPU 实验。

---

# 三、任务 1：Channel8 Hybrid-SNN 初始探索

## 实验设置

- 官方 balanced SADT 数据集：2022 samples × 30 channels；
- Channel8 输入；
- GroupNorm 前端；
- 11-fold LOSO compatibility；
- matched ANN 与 Hybrid-SNN；
- 纯 PyTorch subtract-reset LIF；
- RTX 3060 GPU。

## 完整 11-fold 结果

| 模型 | Accuracy | Macro-F1 | 参数量 |
|---|---:|---:|---:|
| Matched ANN | 71.80% | 70.02% | 1,330 |
| Hybrid-SNN | 71.99% | 70.07% | 1,330 |

Hybrid-SNN 相对 ANN：

```text
Accuracy: +0.19 pp
Macro-F1: +0.05 pp
Mean spike rate: 17.76%
Silent feature ratio: 13.08%
Saturated feature ratio: 4.36%
```

## 结论

简单 Hybrid-SNN 可以正常训练，并且没有明显损害匹配 ANN 的性能。它具备继续探索的价值，但目前不能说 SNN 显著优于 ANN。

---

# 四、任务 2：SNN 实验路线统筹

将后续工作拆成四个连续阶段：

```text
SNN-1：beta/threshold 稳定性
→ SNN-2：输入编码
→ SNN-3：架构消融
→ SNN-4：定点/FPGA 可行性
```

同时明确了实验边界：

- 不把 class-blocked 数据顺序称为 chronological；
- 不把 SynOps 称为真实能耗；
- 没有 HLS 和板卡证据时不宣称 FPGA 部署；
- 每一阶段必须有明确的 pass/no-go 决策。

## 结论

SNN 不再采用“不断堆叠新结构”的路线，而采用逐阶段筛选。只有前一阶段通过，才允许进入下一阶段。

---

# 五、任务 3：SNN-1 稳定性扫描

## 实验设置

比较 4 组参数：

| 配置 | beta | threshold |
|---|---:|---:|
| S1 | 0.90 | 1.0 |
| S2 | 0.90 | 0.5 |
| S3 | 0.90 | 1.5 |
| S4 | 0.95 | 1.0 |

实验阶段：

```text
4 个 smoke 任务
44 个单 seed screen 任务
2 个候选 × 3 seeds × 11 folds × ANN/SNN = 132 个稳定性任务
```

四个配置均通过 smoke gate，最终选择 S1 和 S2 进行多 seed 稳定性验证。

## 最终结果

| 配置 | Accuracy Δ vs ANN | Macro-F1 Δ vs ANN | Spike rate |
|---|---:|---:|---:|
| S1 | +0.23 pp | +0.33 pp | 17.85% |
| **S2** | **+0.72 pp** | **+0.87 pp** | 25.53% |

## 结论

S2 是后续主配置：

```text
beta = 0.90
threshold = 0.5
```

S1 保留为低 spike-rate 控制。S2 的性能增益较小，因此只能说它是当前稳定候选，不能说它已经证明 SNN 优于 ANN。

---

# 六、任务 4：输入编码对比

## 比较内容

在冻结 S2 后，比较 3 种编码：

1. direct-current；
2. deterministic amplitude/count；
3. signed Delta。

完成：

```text
3 种编码 × 11 folds = 33 个任务
```

## 结果

| 编码 | Accuracy | Balanced Accuracy | Macro-F1 | 输出 Spike Rate | 状态存储 |
|---|---:|---:|---:|---:|---:|
| **direct-current** | **72.39%** | **72.39%** | **71.00%** | 25.18% | 0 B |
| amplitude/count | 60.92% | 60.92% | 60.15% | 14.62% | 0 B |
| signed Delta | 55.35% | 55.35% | 52.59% | 11.60% | 128 B |

相对 direct-current：

```text
amplitude/count：Accuracy -11.47 pp，Macro-F1 -10.86 pp
signed Delta：Accuracy -17.04 pp，Macro-F1 -18.42 pp
```

## 结论

当前不采用事件化输入编码。

amplitude/count 和 Delta 虽然降低了 spike rate，但损失了大量分类信息。Delta 还增加了每特征参考状态，却没有带来性能收益。

因此冻结：

```text
direct-current
```

这说明在当前 CNN + GroupNorm 特征空间中，连续特征电流比阈值化事件编码更适合该任务。

---

# 七、任务 5：架构消融

## 比较内容

固定 S2 与 direct-current，比较：

1. Hybrid LIF head；
2. spiking temporal block；
3. ANN control。

完成：

```text
3 种结构 × 11 folds = 33 个任务
```

## 结果

| 结构 | Accuracy | Macro-F1 | Spike Rate | 参数量 | Ops proxy/sample |
|---|---:|---:|---:|---:|---:|
| **Hybrid LIF head** | **72.39%** | **71.00%** | 25.18% | 1,330 | 1,536 |
| spiking temporal block | 70.35% | 68.52% | 25.33% | 1,426 | 6,144 |
| ANN control | 71.25% | 69.70% | — | 1,330 | — |

spiking temporal block 相对 Hybrid LIF head：

```text
Macro-F1 -2.49 pp
参数量 +7.22%
运算代理约 4 倍
Spike rate 没有明显改善
```

## 结论

暂不继续增加复杂的 spiking temporal block。

当前性能主要来自：

```text
CNN 前端 + 简单 LIF readout
```

额外 temporal spiking convolution 没有带来性能或稀疏性收益。

---

# 八、任务 6：定点与 FPGA 可行性预研

## 冻结目标

```text
Target FPGA：xc7z020clg400-1
Clock assumption：100 MHz
Input：32 feature currents × 48 temporal steps
Model：Hybrid LIF head + direct-current
```

比较 3 种格式：

```text
Q8.4、Q12.6、Q16.8
```

## Fold-2 软件定点结果

| 格式 | Prediction Agreement | Logit MAE | Spike-rate Drift | Saturation |
|---|---:|---:|---:|---:|
| Q8.4 | 96.97% | 0.0405 | +0.46 pp | 0% |
| **Q12.6** | **99.24%** | **0.0090** | **+0.03 pp** | 0% |
| Q16.8 | 100.00% | 0.0032 | +0.03 pp | 0% |

分析得到的运算代理为：

```text
4,672 cycles/sample
46.72 us/sample @ 100 MHz
```

这只是软件分析代理，不是 Vivado/Vitis 报告。

## 结论

- Q8.4：一致率低于 99%，暂不采用；
- **Q12.6：作为第一版 HLS 候选；**
- Q16.8：作为高精度软件参考。

当前只验证了 LIF head 的 head-level 定点一致性，CNN/GroupNorm 前端还没有完成端到端定点化。

---

# 九、最终形成的 SNN 方案

```text
Channel8
→ GroupNorm
→ direct-current
→ 48 deterministic LIF steps
→ Hybrid LIF head
→ beta=0.90, threshold=0.5
→ Q12.6 first HLS candidate
```

## 已经排除的方向

```text
amplitude/count：精度损失过大
signed Delta：精度更差且增加状态
spiking temporal block：性能下降且运算量增加
Q8.4：定点一致率不足
```

---

# 十、当前结论的边界

本阶段结果不能表述为：

- SNN 已显著优于 ANN；
- 已经完成在线因果驾驶疲劳检测；
- 已经完成 FPGA 部署；
- SynOps 已经证明低功耗；
- 已经完成板端功耗测量。

正确表述是：

> 我们完成了一个可复现的 Channel8 Hybrid-SNN 探索链路。在官方 balanced class-blocked compatibility 协议下，筛选出 direct-current + Hybrid LIF head + S2 参数配置，并证明 Q12.6 具备进入 HLS csim/csynth 验证的初步条件。事件编码和额外脉冲时间结构在当前特征空间中没有带来收益。

---

# 十一、下一步计划

建议向老师汇报时明确：

## 近期第一步

继续完成已有的时间顺序和 BS=1 任务：

```text
07-14-chronological-bs1-gap-baseline
```

因为目前 SNN 实验使用的是 compatibility 数据顺序，还不能直接作为严格在线因果部署证据。

## 随后

1. 建立 chronology manifest；
2. 测量同一 checkpoint 的 full-batch 与 BS=1 gap；
3. 在确定协议后比较 HCSN/常量状态归一化；
4. 重新评估 Hybrid-SNN 是否在严格 BS=1 下仍然有价值；
5. 最后进行 Q12.6 HLS csim/csynth。

---

## 一分钟口头汇报版本

> 这几天我完成了 SNN 从可训练性、参数稳定性、输入编码、架构消融到定点可行性的完整探索。实验表明，当前最合适的方案是 Channel8 + GroupNorm + direct-current + Hybrid LIF head，LIF 参数为 beta=0.90、threshold=0.5。amplitude/count 和 Delta 事件编码虽然降低了脉冲率，但带来了 10 到 18 个百分点的性能损失；额外的 spiking temporal block 也没有带来收益，反而使运算代理增加约 4 倍。定点预研中 Q12.6 达到 99.24% 的 float/fixed prediction agreement，因此可以作为第一版 HLS 候选。但目前实验基于官方 class-blocked compatibility 数据，尚未完成 chronology、BS=1、HLS 和板端验证，所以现阶段结论是 SNN 具备可行性和硬件探索价值，还不能声称已经完成在线 FPGA 部署。
---

# 十二、术语说明

- **balanced（平衡数据集）**：不同类别的样本数量经过平衡处理，减少类别比例对准确率的影响。
- **class-blocked compatibility（类别分块兼容性顺序）**：为了复现历史实验而保留的文件排列顺序，不代表真实时间顺序。
- **chronological replay（时间顺序回放）**：按照样本实际发生的时间先后进行推理，用于检验在线因果部署。
- **LOSO（Leave-One-Subject-Out）**：每次留出一个被试测试，其余被试训练，用于检验跨被试泛化。
- **Macro-F1**：分别计算各类别 F1 后取平均，适合观察类别是否都得到较好识别。
- **GroupNorm（组归一化）**：对单个样本内部的特征归一化，不依赖 batch 内其他样本的运行统计量。
- **LIF（漏积分发放神经元）**：膜电位随时间积累并衰减，达到阈值后发放脉冲。
- **surrogate gradient（替代梯度）**：训练时用平滑近似函数代替脉冲函数的不可导梯度。
- **Q12.6**：总位宽 12 位、小数位 6 位的定点格式。
- **HLS csim/csynth**：分别表示高层次综合中的 C 级仿真和 C/C++ 到 RTL 电路的综合阶段。
- **pp（percentage point，百分点）**：例如准确率从 72% 变为 73%，表示增加 1 个百分点，而不是相对提升 1%。
