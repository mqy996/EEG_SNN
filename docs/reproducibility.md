# 复现实验指南

## 1. 准备数据

将官方平衡版 SADT MAT 文件放置到：

```text
data/dataset.mat
```

预期 SHA-256：

```text
53cc4ef14b1343f7f3fb5322dd2b541c031c6c2297bddf1817aed04dc687a6a4
```

预期形状：`2022 × 30 × 384`，共 11 个被试，数据顺序为 `class_blocked_compatibility`（类别分块兼容性顺序）。不要提交 MAT 文件，程序会先验证哈希值。

## 2. 验证环境

```powershell
conda run -n eeg-causal python scripts/verify_environment.py
conda run -n eeg-causal python -m ruff check src scripts tests
conda run -n eeg-causal python -m pytest
```

Ruff 是 Python 静态检查工具，pytest 是自动化测试框架。

## 3. 运行实验

先运行根目录 README 中的 dry-run（只检查配置）或 smoke（短时冒烟实验）命令。完整实验支持断点恢复，并将结果写入被 `.gitignore` 忽略的 `results/` 目录。复现整理结果时应保持配置、随机种子和计算设备一致。

## 4. 复现边界

这些结果是类别分块兼容性协议上的证据，不能证明严格时间顺序、因果回放或在线部署。SynOps 和运算次数是软件代理，不等于实测功耗。Q12.6 只是读出头级别软件定点预研；HLS csim/csynth 和板卡验证是后续证据等级。
