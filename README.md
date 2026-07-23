# EEG 混合脉冲神经网络（Hybrid-SNN）基准仓库

本仓库是从 `q1_deployment_causal_eeg` 整理出的、面向老师审阅和复现实验的独立仓库。它不是完整研究工作区副本；完整研究历史、时间顺序规划和其他实验仍保留在 q1 仓库。

## 当前冻结基线

“冻结”表示后续对比实验暂时不修改这些设置，以保证实验公平。

```text
输入：Channel8 EEG 窗口，8 个通道 × 384 个采样点
前端：逐点空间卷积 → 深度时间卷积 → ReLU → GroupNorm
时间表示：自适应平均池化为 48 个时间步
编码：direct-current（直流编码，将连续特征直接作为输入电流）
脉冲读出：Hybrid LIF（混合漏积分发放神经元）
beta：0.90（膜电位历史记忆系数）
threshold：0.5（发放脉冲的膜电位阈值）
定点候选：Q12.6（总位宽 12 位，小数位 6 位）
```

SNN-1 稳定性实验选择 S2（`beta=0.90`、`threshold=0.5`）。

## HLS 基线状态

第一阶段 HLS 只冻结 Hybrid LIF 读出头的外部 Q12.6 接口；CNN/GroupNorm 前端仍在软件参考侧。接口、`[B, 32, 48] → [48][32]` 布局转换、调用级状态复位、目标器件/时钟假设和非结论见 [Direct-current Hybrid-SNN 与 HLS Phase-1 接口契约](docs/direct_current_hls_architecture.md)。

?? HLS ??? HLS-0 ? HLS-3?????? HLS C++?Vitis CSim????? `xc7z020clg400-1`?10 ns/100 MHz ??? C ???????????? CNN/GroupNorm ????? Hybrid LIF readout head????? CNN-SNN FPGA ???????? [hls/README.md](hls/README.md)?[hls/RESULTS.md](hls/RESULTS.md) ? [Direct-current SNN HLS ????](docs/direct_current_hls_baseline_summary.md)??? Vivado ??????? CNN-LSTM ??? 50 MHz PS FCLK0?

## 术语说明

| 术语 | 解释 |
|---|---|
| SNN | Spiking Neural Network，脉冲神经网络；通过离散脉冲传递信息 |
| Hybrid-SNN | 混合脉冲神经网络；本项目保留 CNN 前端，仅将读出部分改为脉冲神经元 |
| LIF | Leaky Integrate-and-Fire，漏积分发放神经元；膜电位积累到阈值后发放脉冲并复位 |
| Direct-current | 直流编码；把连续特征值直接送入各个时间步，不使用随机脉冲编码 |
| GroupNorm | 组归一化；每个样本独立归一化，不依赖 batch 内统计量 |
| LOSO | Leave-One-Subject-Out，留一被试交叉验证 |
| Macro-F1 | 各类别 F1 分数的平均值，用于观察类别是否均衡 |
| Spike rate | 脉冲发放率；产生脉冲的时间步比例 |
| SynOps | 突触操作数估计；当前仅为软件代理，不等于实测能耗 |
| HLS | High-Level Synthesis，高层次综合；将 C/C++ 算法转换为 FPGA 电路 |
| csim/csynth | HLS 中的 C 级仿真和综合阶段 |
| Q12.6 | 总位宽 12 位、小数位 6 位的定点格式 |

## 目录结构

```text
src/dc_eeg/                  模型、数据、指标和实验模块
scripts/                     可执行实验入口
experiments/                 YAML 配置和整理后的实验结果
data/                        数据说明；官方 MAT 文件被忽略
hls/                         HLS 协同设计说明
tests/                       模型和配置契约测试
docs/                        架构、技术报告和复现说明
```

## 数据集

将官方平衡版 MAT 文件放到：

```text
data/dataset.mat
```

该文件不提交到 Git。数据来源、预期尺寸和 SHA-256 校验值见 `data/README.md`。

## 环境和验证

使用已有的 `eeg-causal` Conda 环境，或创建等价的 Python >=3.11 环境。依赖包括 PyTorch、NumPy、SciPy、PyYAML、pytest 和 Ruff。

```powershell
conda run -n eeg-causal python scripts/verify_environment.py
conda run -n eeg-causal python -m ruff check src scripts tests
conda run -n eeg-causal python -m pytest
```

Ruff 是 Python 静态检查工具，pytest 是自动化测试框架。

## 复现实验入口

所有命令均从仓库根目录执行。建议先运行 `--dry-run` 或 smoke（短时冒烟实验）；完整结果会写入被 Git 忽略的 `results/` 目录。

```powershell
conda run -n eeg-causal python scripts/run_channel8_snn_pilot.py `
  --config experiments/channel8_hybrid_snn_pilot/pilot.yaml --dry-run --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_stability.py `
  --config experiments/channel8_snn_stability/sweep.yaml --stage smoke --dry-run --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_encoding.py `
  --config experiments/channel8_snn_encoding/encoding.yaml --stage smoke --dry-run --device cuda

conda run -n eeg-causal python scripts/run_channel8_snn_architecture.py `
  --config experiments/channel8_snn_architecture/architecture.yaml --stage smoke --dry-run --device cuda

conda run -n eeg-causal python scripts/run_snn_hardware_feasibility.py `
  --config experiments/channel8_snn_hardware/hardware.yaml --device cuda --dry-run
```

## 结论边界

当前结果基于官方平衡版 `class_blocked_compatibility` 数据顺序，不能直接解释为严格时间顺序、BS=1 因果回放、FPGA 部署或实测低功耗证据。详细限制见 `docs/teacher_report.md` 和各实验目录的 `RESULTS.md`。
