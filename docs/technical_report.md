# 技术报告摘要

## 已完成的实验性证据

- Hybrid-SNN 初始实验：验证 Channel8 + GroupNorm 前端的匹配 ANN/SNN 可行性。
- 稳定性扫描：比较 4 组 LIF 参数，完成筛选和 3 个随机种子的配对验证，选择 S2。
- 输入编码对比：比较 direct-current（直流编码）、amplitude/count（幅值/计数）和 signed Delta（带符号差分），选择直流编码。
- 架构消融：比较 Hybrid LIF 读出头、脉冲时间模块和 ANN 对照组，保留 Hybrid LIF。
- 定点预研：比较 Q8.4、Q12.6 和 Q16.8，选择 Q12.6 作为第一版 HLS 候选。

## 当前方案

```text
Channel8 + GroupNorm + direct-current + Hybrid LIF
beta=0.90，threshold=0.5，48 个时间步
```

完整表格见各 `experiments/*/RESULTS.md`。

## 主要数值结论

- 在兼容性协议下，SNN 初始实验总体表现与匹配 ANN 基本一致。
- 稳定性实验中，S2 相对于配对 ANN 的准确率提升 **0.72 个百分点**，Macro-F1 提升 **0.87 个百分点**。
- 事件编码虽然降低脉冲率，但相对直流编码损失 **11.47–17.04 个百分点**的准确率。
- 脉冲时间模块使 Macro-F1 下降 **2.49 个百分点**，运算代理约增加 **4 倍**。
- Q12.6 在读出头级别 fold-2 预研中达到 **99.24%** 浮点/定点预测一致率。

## 结论边界

所有结果使用官方平衡版 `class_blocked_compatibility` 数据文件，不是严格的时间顺序 BS=1 部署证据。运算次数和 SynOps 只是软件代理；Q12.6 是软件定点参考实现，不是 HLS 或板端证据。

准确表述应为：

> 已完成可复现的 Hybrid-SNN 探索链路，并筛选出可进入 HLS csim/csynth 验证的模型和定点格式；时间顺序、BS=1、端到端定点、FPGA 资源/时序和板端功耗仍需后续验证。
