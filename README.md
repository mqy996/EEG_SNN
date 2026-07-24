# EEG 混合脉冲神经网络基线仓库

本仓库是从 `q1_deployment_causal_eeg` 整理出的、供导师审阅和复现实验的独立仓库。它不包含完整研究历史；历史实验、研究规划和其他探索仍保留在 q1 仓库。

## 一句话结论

当前已完成一个可复现的 Channel8 Hybrid-SNN 软件基线，并完成 Hybrid LIF 读出头的 Q12.6 定点 HLS 验证链路：C 仿真、C 综合和 Verilog C/RTL 协同仿真均已通过。下一步是把该读出头接入实际 50 MHz 的 FPGA 系统，并补充完整 CNN-SNN 的端到端证据。

## 当前基线

| 项目 | 当前设置 |
|---|---|
| 输入 | Channel8 EEG 窗口，8 个通道 × 384 个采样点 |
| CNN 前端 | 逐点空间卷积 → 深度时间卷积 → ReLU → GroupNorm |
| 时间表示 | 自适应平均池化为 48 个时间步 |
| 编码 | Direct-current 直流编码，将连续特征直接输入各时间步 |
| 脉冲读出 | Hybrid LIF 漏积分发放读出头 |
| LIF 参数 | `beta=0.90`，`threshold=0.5` |
| HLS 定点候选 | Q12.6，总位宽 12 位，小数位 6 位 |
| 目标器件 | `xc7z020clg400-1` |

## 已完成的证据

1. 完成 SNN 参数稳定性、编码方式、架构消融和定点可行性探索。
2. 选择 `Direct-current + Hybrid LIF` 作为当前基准网络。
3. Q12.6 在读出头软件预研中达到 99.24% 的浮点/定点预测一致率。
4. HLS-2：Q12.6 无浮点 CSim，黄金用例 3/3 通过。
5. HLS-3：Vitis HLS C 综合完成，报告了资源和延迟估计。
6. HLS-4：Verilog RTL C/RTL 协同仿真完成，3 个测试用例、6/6 次 RTL transaction 通过。

详细证据：

- [Direct-current Hybrid-SNN 与 HLS Phase-1 接口契约](docs/direct_current_hls_architecture.md)
- [HLS 综合结果](hls/RESULTS.md)
- [HLS-4 RTL 协同仿真结果](hls/RTL_COSIM_RESULTS.md)
- [Direct-current HLS 基线摘要](docs/direct_current_hls_baseline_summary.md)
- [教师阶段性汇报](docs/teacher_report.md)

## 必须明确的边界

当前 HLS 只实现 Hybrid LIF 读出头，CNN/GroupNorm 前端仍由软件参考模型负责。因此，已有 HLS 结果不能表述为完整 CNN-SNN 已经完成 FPGA 部署。

- HLS-3 和 HLS-4 使用 100 MHz、10 ns 作为综合与协同仿真约束。
- 现有 CNN-LSTM 系统记录的 Zynq PS `FCLK_CLK0` 为 50 MHz、20 ns；这是后续系统集成的时钟参考，不是 SNN 已完成的板级结果。
- 尚未完成完整 CNN 前端的 HLS、Vivado implementation、bitstream、板上回放、整网准确率和功耗测量。
- 当前软件结果使用官方平衡版 `class_blocked_compatibility` 数据顺序，不能直接等同于严格时间顺序或在线因果部署证据。

## 下一步工作

1. 将 Hybrid LIF HLS 读出头接入 50 MHz 的 Zynq/Vivado 系统，确认接口和时序。
2. 用软件参考模型与 RTL/IP 逐样本对齐，形成端到端接口回放证据。
3. 再决定是否继续完成 CNN/GroupNorm 前端的硬件化，以及板端整网验证。
4. 在独立实验中补充严格时间顺序、BS=1 和在线因果协议，避免把兼容性数据顺序的结果过度外推。

## 复现入口

数据文件不提交到 Git。请将官方平衡版 MAT 文件放到 `data/dataset.mat`，数据来源、预期形状和 SHA-256 校验值见 [数据集说明](data/README.md)。

环境检查：

```powershell
conda run -n eeg-causal python scripts/verify_environment.py
conda run -n eeg-causal python -m ruff check src scripts tests
conda run -n eeg-causal python -m pytest
```

建议先运行 dry-run 或 smoke 命令，具体入口见 [复现实验指南](docs/reproducibility.md)。HLS 读出头协同仿真入口为：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File hls/hybrid_lif_head/scripts/run_cosim.ps1
```

## 目录导航

```text
src/        软件模型、数据和指标
scripts/    可执行实验入口
experiments/实验配置和整理后的结果
hls/        HLS 源码、脚本和验证报告
docs/       架构、实验汇报和复现说明
data/       数据来源与校验说明，不含原始 MAT 文件
tests/      模型和配置契约测试
```

## 术语

- **Hybrid-SNN**：保留 CNN 前端、将读出部分替换为脉冲神经元的混合模型。
- **LIF**：漏积分发放神经元，膜电位累积到阈值后发放脉冲并复位。
- **Direct-current**：直流编码，把连续特征直接送入各个时间步，不使用随机脉冲编码。
- **GroupNorm**：组归一化，不依赖 batch 内运行统计量，适合当前小批量和单样本推理场景。
- **HLS**：高层次综合，将 C/C++ 算法转换为 FPGA 电路。
- **Q12.6**：总位宽 12 位、小数位 6 位的定点格式。