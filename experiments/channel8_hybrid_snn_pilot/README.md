# Channel8 Hybrid-SNN 初始试验

本实验只回答一个问题：匹配的 GroupNorm CompactCNN 前端能否接入确定性的 LIF 脉冲计数读出头，同时不让 LOSO 准确率大幅下降，并产生一定脉冲稀疏性。

## 证据边界

- 数据：官方平衡版 Cui/SADT MAT 文件。
- 通道：C3、Cz、C4、CP3、CPz、CP4、Oz、O2。
- 协议：被试独立 LOSO（留一被试交叉验证）兼容性评估。
- 顺序：`class_blocked_compatibility`，不是 chronology（时间顺序）。
- 不包含 HCSN、Delta/Rate 编码、定点、HLS 或板端功耗测量。
- Spike rate（脉冲率）和 SynOps（突触操作数）是软件代理，不是能耗实测。

代码位于 `src/dc_eeg/`，命令行入口位于 `scripts/`，运行产物写入 `results/snn_pilot/`。

## 运行命令

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --dry-run

conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --fold 2 --device cuda --smoke
```

只有当 smoke 文件报告 `smoke_gate_passed: true` 后才运行完整实验：

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --device cuda
```
