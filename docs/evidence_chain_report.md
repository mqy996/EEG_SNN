# Direct-current SNN FPGA 证据链

更新时间：2026-07-31

## 一句话结论

本项目已经把 Direct-current 编码的 Hybrid LIF 读出头从软件定点参考推进到 HLS、RTL、Vivado Zynq 系统、Vitis standalone 和开发板逐样本回放。当前 314 个 fold9 测试样本全部通过 checksum/logit/count 一致性检查，分类正确 277 个，准确率为 88.2166%。

这个结论只覆盖当前冻结的“软件前端输出特征 + FPGA LIF 读出头”协同系统，不代表完整 CNN/GroupNorm 前端已经在 FPGA 上运行。

## 证据链总览

```text
软件 SNN 选择与 11-fold 结果
        |
        v
Q12.6 定点契约、黄金向量、HLS CSim/CSynth
        |
        v
AXI-Lite wrapper + 3 组 golden case RTL 验证
        |
        v
Vivado PS7 + SmartConnect + Processor System Reset
        |
        v
bitstream + XSA + post-implementation 报告
        |
        v
Vitis platform/domain + application ELF
        |
        v
开发板 314 样本回放、UART、一致性、准确率、延迟和吞吐
```

## 阶段 1：软件模型选择

已冻结的基线为：

```text
Channel8 EEG
-> CNN 空间/时间卷积
-> ReLU + GroupNorm
-> 自适应平均池化，32 features x 48 steps
-> Direct-current 输入
-> 48 步 Hybrid LIF
-> spike counts / rate
-> Linear(32, 2)
```

11-fold compatibility 实验中，Direct-current + Hybrid LIF head 的 Accuracy 为 72.39%，Macro-F1 为 71.00%。amplitude/count 和 signed Delta 编码在当前特征空间产生明显精度损失，因此没有作为 FPGA 基线。

## 阶段 2：HLS 与定点

- HLS top：`hybrid_lif_head_q12_6`；
- 输入布局：单样本 `[48][32]`，第一个维度为时间；
- 定点：有符号 Q12.6，缩放因子 64；
- 常量：`beta_q=58`、`threshold_q=32`；
- 输出：两个 logits、32 个 spike counts；
- HLS-2：`threshold_edge`、`signed_currents`、`rounding_and_reset` 三组 CSim golden case 通过；
- HLS-4：对应 RTL C/RTL 协同仿真通过；
- HLS-3/HLS-5A：保留独立 OOC 资源、时序和综合结果。

这一步验证的是读出头数值规则和硬件边界，不是完整 EEG CNN 前端已经完成 HLS 化。

## 阶段 3：AXI-Lite wrapper 与 Vivado

wrapper 暴露版本、状态、特征索引/数据、权重索引/数据、偏置索引/数据、logit 索引/数据、count 索引/数据、checksum 和 error status。输入和参数通过 AXI-Lite indexed registers 写入。

Vivado 主系统配置：

```text
xc7z020clg400-2
MT41J256M16 RE-125
FCLK0 = 50 MHz
UART1 = MIO 48/49
M_AXI_GP0 = enabled
HP = disabled
SmartConnect 1.0
Processor System Reset 5.0
SNN AXI base = 0x43C00000
```

复位没有把 PS 的异步 `FCLK_RESET0_N` 直接连接到 AXI 和用户逻辑，而是通过 Processor System Reset 生成同步的 `peripheral_aresetn`。这是此前 GPIO/AXI 试验中发现并固化的关键规范。

Vivado 结果：bitstream 和 XSA 生成成功，50 MHz 时序满足，WNS +4.776 ns，TNS 0，WHS +0.072 ns，路由错误 0，DRC 错误 0。

## 阶段 4：Vitis platform/application

Vitis Unified 2025.1 采用以下生命周期：

```text
XSA
-> snn_evidence_platform platform component
-> standalone_ps7_cortexa9_0 domain
-> platform build / XPFM
-> snn_best_fold9_replay 或 snn_latency_replay application
-> source import / application build
-> ELF
```

应用使用平台自动生成的 `xparameters.h` 获取 `0x43C00000`，使用平台自动生成的 `xiltimer.h` 进行时间测量。不能把 BSP 内部 `libsrc` 头文件复制进应用目录，否则可能出现 `XPAR_CPU_CORTEXA9_0_CPU_CLK_FREQ_HZ` 等旧宏不匹配问题。

## 阶段 5：开发板回放

延迟回放程序对 314 个样本逐个执行：

```text
soft reset
-> 写入 vector id
-> 写入 1536 个 feature words
-> 写入 64 个 weight words
-> 写入 2 个 bias words
-> 比较 checksum
-> START
-> 轮询 DONE
-> 读取 2 个 logits 和 32 个 counts
-> CLEAR_DONE
```

板端 UART 结果：

| 项目 | 结果 |
|---|---:|
| 314 个样本 checksum/logit/count | 314/314 PASS |
| 分类 | 277/314 |
| fold9 子集准确率 | 88.2166% |
| AXI-Lite 输入观察时间 | 317 us/sample |
| START 到 DONE 观察时间 | 8 us/sample |
| 完整回放时间 | 326 us/sample |
| 完整回放吞吐率 | 3067.48 samples/s |
| 平均 ARM 轮询次数 | 93 |

计时器自检输出 `TIMER_START_RESULT=PASS`。这些是 PS 端观察到的事务范围；不要把 8 us 直接称为 HLS 内核 RTL latency。

## 复现入口

### Vivado 重建

```powershell
$repo = 'D:\eeg_fpga\snn_hybrid_eeg'
& 'D:\vitis\2025.1\Vivado\bin\vivado.bat' -mode batch `
  -source "$repo\vivado\evidence_rebuild\scripts\create_evidence_system.tcl" `
  -tclargs $repo "$repo\vivado\evidence_rebuild\run_20260731_attempt1" project_bitstream
```

### Vitis 重建

以 `vivado/evidence_rebuild/artifacts/snn_evidence_system.xsa` 创建 platform，先 build platform，再创建 standalone application，导入 `vitis/evidence_rebuild/latency_source/`，clean/build application，最后使用 XSA/bitstream/ELF 进行板端下载和 UART 观察。

## 证据文件导航

| 内容 | 位置 |
|---|---|
| 硬件配置与来源 | `docs/hardware_provenance.md` |
| 性能、资源、时序、功耗 | `docs/performance_report.md` |
| Vivado 脚本和发布工件 | `vivado/evidence_rebuild/` |
| Vitis 源码、平台包和 ELF | `vitis/evidence_rebuild/` |
| 三组 golden case | `hls/hybrid_lif_head/golden/` 与 `vivado/system/` |
| 工件哈希 | `vivado/evidence_rebuild/EVIDENCE_MANIFEST.json` |

## 结论边界

目前不能宣称：

- 完整 CNN/GroupNorm 前端已经硬件化；
- 已经实现 HP/DMA/DDR 流式输入；
- 88.2166% 是完整 11-fold 平均准确率；
- 8 us 是 HLS IP 单独的 cycle latency；
- 1.769 W 或 0.129 W 是开发板实测功耗；
- 已经完成在线 EEG 连续采集和端到端部署。
