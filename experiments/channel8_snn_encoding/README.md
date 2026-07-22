# SNN-2 输入编码对比

先运行 smoke（短时冒烟实验），检查候选编码器，再使用同一随机种子完成 11 折实验：

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_encoding.py `
  --config experiments/channel8_snn_encoding/encoding.yaml --stage smoke --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_encoding.py `
  --config experiments/channel8_snn_encoding/encoding.yaml --stage full `
  --run-id <SMOKE_RUN_ID> --resume --device cuda
```

三种编码都是确定性的。Direct-current（直流编码）是 SNN-1 基线；amplitude/count（幅值/计数编码）只根据当前值产生带符号阈值事件；Delta（差分编码）为每个特征保存参考值，在跨过阈值时产生带符号事件。运行产物位于被忽略的 `results/snn_encoding/`。

当前决策：冻结 `direct_current` 作为架构消融的输入编码。另两种事件编码虽然降低脉冲率，但相对直流编码损失 11.47–17.04 个百分点准确率。
