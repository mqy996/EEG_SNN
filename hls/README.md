# HLS 协同设计状态

## 当前状态

软件定点预研将 Q12.6 选为 Hybrid LIF 读出头的第一版 HLS 候选。本仓库目前只有 PyTorch 浮点/定点参考实现，没有 HLS C++ 源码、csim/csynth 报告或板端证据。

HLS（High-Level Synthesis，高层次综合）是把 C/C++ 算法转换为 FPGA RTL 电路的流程；`csim` 是 C 级仿真，`csynth` 是综合阶段。

## 第一版 HLS 接口

```text
目标器件：xc7z020clg400-1
时钟假设：100 MHz
输入：feature_current_q，32 个特征通道 × 48 个时间步
状态：32 个膜电位值，每个样本复位
编码：direct-current（直流编码）
LIF：beta=0.90，threshold=0.5，subtract-reset（减阈值复位）
定点格式：Q12.6
输出：两个 logits（未归一化分类分数）
```

## 后续阶段

1. 将 `src/dc_eeg/snn_hardware.py` 转换为逐位一致的 C++ 参考实现。
2. 使用 JSON 可行性结果作为 golden vector（黄金测试向量）契约。
3. 运行主机端 C++ 测试和 Vitis HLS `csim`。
4. 运行 `csynth`，记录资源和延迟报告。
5. 只有 csim/csynth 通过后再考虑板端回放。

当前报告中的 SynOps、分析延迟和存储量都是软件代理，不是实测能耗。
