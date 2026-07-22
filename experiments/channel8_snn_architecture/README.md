# SNN-3 架构消融

状态：**已完成**。

本实验冻结 SNN-1 的 S2（`beta=0.90`、threshold `0.5`）和 SNN-2 的 `direct_current` 编码，比较：

1. Hybrid LIF head（混合 LIF 读出头）；
2. depthwise spiking temporal block（深度可分离脉冲时间模块）；
3. matched ANN control（匹配的 ANN 对照组）。

时间模块没有提升 Macro-F1，却使运算代理增加约 4 倍，因此继续保留 Hybrid LIF 读出头。ANN-to-SNN conversion（ANN 到 SNN 转换）基线暂不执行，因为激活校准和归一化处理还没有形成可测试契约。完整结果见 `RESULTS.md`。
