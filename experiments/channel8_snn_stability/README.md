# 分阶段 SNN 稳定性扫描

本实验冻结 Channel8 Hybrid-SNN 初始模型，只改变 LIF 的 `beta` 和 `threshold`，对应路线中的 SNN-1。数据使用官方平衡版、类别分块兼容性顺序和 LOSO 协议，因此不能解释为时间顺序或硬件能耗证据。

使用同一个运行 ID，依次执行：

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage smoke --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage screen-loso `
  --run-id <SMOKE_RUN_ID> --resume --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage stability `
  --run-id <SMOKE_RUN_ID> --resume --device cuda
```

运行产物位于 `results/snn_stability/`，`RESULTS.md` 是计划提交到 Git 的整理摘要。
