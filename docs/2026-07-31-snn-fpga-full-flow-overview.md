# 2026-07-31 SNN FPGA 全流程与结果总览

更新时间：2026-07-31
用途：导师快速了解当前 Direct-current SNN 基准网络从软件实验到开发板验证的完整证据链。

## 1. 先给结论

当前已经完成一条可复现的工程链路：

```text
软件 SNN 实验
  -> Direct-current + Hybrid LIF 基准选择
  -> Q12.6 定点参考与 HLS CSim/CSynth
  -> AXI-Lite wrapper 与 RTL 协同仿真
  -> Vivado Zynq-7020 系统、bitstream、XSA
  -> Vitis standalone platform、application、ELF
  -> 开发板 314 个固定窗口逐样本回放
```

当前最重要的结论是：

1. 软件 11-fold compatibility 实验选择了 `Direct-current + Hybrid LIF head`，准确率 `72.39%`，Macro-F1 `71.00%`。
2. Q12.6 是当前第一版 HLS 定点格式；三个黄金用例通过 CSim，生成 RTL 后的 C/RTL 协同仿真也通过。
3. 当前完整 Zynq 系统在 `xc7z020clg400-2`、`MT41J256M16 RE-125`、50 MHz 下完成 Vivado、Vitis 和 bitstream/XSA 构建。
4. 开发板对 fold9 的 314 个固定测试窗口全部完成 checksum、logit、spike count 一致性检查，结果为 `314/314 PASS`；其中分类正确 `277/314`，该子集准确率为 `88.2166%`。
5. 板端测得的是 PS 端观察到的 AXI-Lite 回放范围：输入写入约 `317 us`，START 到 DONE 约 `8 us`，完整回放约 `326 us`，吞吐率约 `3067.48 samples/s`。

> 关键边界：当前 FPGA 实现的是池化后特征到 Hybrid LIF 读出头的协同回放，不是完整 CNN/GroupNorm 前端已经全部硬件化；88.2166% 不是完整 11-fold 平均准确率；功耗是 Vivado 工具估算，不是开发板仪器实测。

## 2. 项目基准和硬件边界

### 2.1 软件模型

```text
Channel8 EEG
  -> 空间卷积
  -> 深度时间卷积
  -> ReLU + GroupNorm
  -> 自适应平均池化：32 个特征 x 48 个时间步
  -> Direct-current 输入编码
  -> 48 步 Hybrid LIF
  -> 32 路脉冲计数/发放率
  -> Linear(32, 2)
  -> 两类 logits
```

模型冻结参数：

| 项目 | 当前值 | 说明 |
|---|---:|---|
| 输入通道 | Channel8 | 从 Channel8 EEG 特征开始验证 |
| 编码 | Direct-current | 连续特征直接作为 LIF 输入电流 |
| LIF 衰减 | `beta=0.90` | 软件模型参数 |
| LIF 阈值 | `threshold=0.5` | 软件模型参数 |
| 时间步 | 48 | 每个样本的时间维度 |
| 特征数 | 32 | LIF head 的并行特征通道 |
| 输出类别 | 2 | 输出两个 logits |

### 2.2 HLS/IP 边界

本项目实际进入 HLS 和 FPGA 的边界是：

```text
软件前端输出的 32 x 48 特征电流
  -> AXI-Lite indexed window 写入
  -> hybrid_lif_head_q12_6
  -> spike counts + logits
```

CNN、ReLU、GroupNorm 和自适应平均池化仍属于软件前端。当前系统没有使用 HP 端口、DMA 或 DDR 流式读取；开发板回放由 ARM 软件逐项写入 AXI-Lite 寄存器窗口。

### 2.3 当前硬件契约

| 项目 | 当前值 |
|---|---|
| Vivado/Vitis | 2025.1 |
| FPGA | `xc7z020clg400-2` |
| DDR | `MT41J256M16 RE-125` |
| FCLK0 | 50 MHz，周期 20 ns |
| 串口 | UART1，MIO48/49，115200 baud |
| PS 主接口 | `M_AXI_GP0` enabled |
| HP/DMA | 未使用 |
| AXI 互连 | SmartConnect 1.0 |
| 复位 | Processor System Reset 5.0，同步释放 `peripheral_aresetn` |
| SNN AXI-Lite 基地址 | `0x43C00000` |
| HLS top | `hybrid_lif_head_q12_6` |
| 定点格式 | 有符号 Q12.6，整数载荷除以 64 |
| 定点常量 | `beta_q=58`，`threshold_q=32` |

复位路径为：

```text
PS7 FCLK_RESET0_N
  -> Processor System Reset/ext_reset_in
  -> peripheral_aresetn
  -> SmartConnect、AXI wrapper、用户 RTL/HLS 逻辑
```

这样避免把 PS 产生的异步复位直接接到 AXI 和用户逻辑，保证复位释放在 AXI 时钟域内同步。

## 3. 软件 SNN 实验结果

这部分是基准网络选择过程，使用的是官方 balanced、class-blocked compatibility 数据顺序。它证明模型选择和定点化方向，不等同于在线 chronological EEG 部署。

### 3.1 初始可训练性

| 模型 | Accuracy | Macro-F1 | 参数量 |
|---|---:|---:|---:|
| Matched ANN | 71.80% | 70.02% | 1,330 |
| Hybrid-SNN | 71.99% | 70.07% | 1,330 |

初始 Hybrid-SNN 与匹配 ANN 的准确率相差 `+0.19` 个百分点，说明结构可以训练，但不能据此宣称 SNN 已显著优于 ANN。

### 3.2 稳定性扫描

| 配置 | beta | threshold | 相对 ANN 的 Accuracy 变化 | 相对 ANN 的 Macro-F1 变化 | Spike rate |
|---|---:|---:|---:|---:|---:|
| S1 | 0.90 | 1.0 | +0.23 pp | +0.33 pp | 17.85% |
| **S2** | **0.90** | **0.5** | **+0.72 pp** | **+0.87 pp** | **25.53%** |

因此冻结 `beta=0.90`、`threshold=0.5` 作为后续主配置，S1 作为低脉冲率控制配置。

### 3.3 输入编码对比

| 编码 | Accuracy | Balanced Accuracy | Macro-F1 | Spike rate | 额外状态 |
|---|---:|---:|---:|---:|---:|
| **Direct-current** | **72.39%** | **72.39%** | **71.00%** | 25.18% | 0 B |
| Amplitude/count | 60.92% | 60.92% | 60.15% | 14.62% | 0 B |
| Signed Delta | 55.35% | 55.35% | 52.59% | 11.60% | 128 B |

相对于 Direct-current，Amplitude/count 的准确率下降 `11.47` 个百分点，Signed Delta 下降 `17.04` 个百分点。因此当前不采用事件化输入编码。

### 3.4 结构消融

| 结构 | Accuracy | Macro-F1 | Spike rate | 参数量 | Ops proxy/sample |
|---|---:|---:|---:|---:|---:|
| **Hybrid LIF head** | **72.39%** | **71.00%** | 25.18% | 1,330 | 1,536 |
| Spiking temporal block | 70.35% | 68.52% | 25.33% | 1,426 | 6,144 |
| ANN control | 71.25% | 69.70% | - | 1,330 | - |

额外的 spiking temporal block 没有提高准确率，Macro-F1 下降 `2.49` 个百分点，运算代理约为 Hybrid LIF head 的 4 倍。因此不把它作为当前 FPGA 基准。

### 3.5 定点格式比较

| 格式 | Float/fixed prediction agreement | Logit MAE | Spike-rate drift | Saturation |
|---|---:|---:|---:|---:|
| Q8.4 | 96.97% | 0.0405 | +0.46 pp | 0% |
| **Q12.6** | **99.24%** | **0.0090** | **+0.03 pp** | 0% |
| Q16.8 | 100.00% | 0.0032 | +0.03 pp | 0% |

Q12.6 在精度和硬件成本之间取得了当前可接受的平衡，作为第一版 HLS 候选；Q16.8 保留为高精度软件参考，Q8.4 暂不采用。`4672 cycles/sample` 是软件分析代理，不是后续 Vivado 或开发板测量值。

## 4. HLS 与 RTL 验证结果

### 4.1 接口和 golden case

HLS top 为 `hybrid_lif_head_q12_6`，输入为时间优先的 `[48][32]` Q12.6 特征，输出为两个有符号 logits 和 32 个 spike counts。验证用例为：

- `threshold_edge`：阈值边界行为；
- `signed_currents`：有符号电流和符号扩展；
- `rounding_and_reset`：定点舍入和重复调用状态复位。

### 4.2 各阶段结果

| 阶段 | 结果 | 能证明什么 |
|---|---|---|
| HLS-2 CSim | 3/3 PASS | C 参考与 Q12.6 golden case 一致 |
| HLS-3 CSynth | PASS | HLS C/C++ 能综合为 RTL，给出周期和资源估计 |
| HLS-4 RTL C/RTL co-sim | 3 个用例、6/6 transaction PASS | 生成 RTL 的调用、输出和复位行为与 C 参考一致 |
| HLS-5A 50 MHz OOC | PASS | 历史 HLS IP 在独立 Vivado OOC 约束下可实现 |

### 4.3 HLS 工具结果

HLS-3 的目标器件是历史配置 `xc7z020clg400-1`、100 MHz；它是读出头的综合估计，不是当前完整 Zynq 系统结果。

| 指标 | HLS-3 C 综合值 |
|---|---:|
| Estimated clock | 7.249 ns |
| Estimated Fmax | 137.95 MHz |
| Top latency | 1688 cycles |
| Top latency @ 100 MHz | 16.880 us |
| LUT | 2405 |
| FF | 1980 |
| DSP | 33 |
| BRAM/URAM | 0/0 |

历史 HLS-5A 独立 50 MHz OOC 结果为：周期 `9.692 ns`、WNS `11.169745 ns`、WHS `0.146518 ns`、LUT `747`、FF `645`、DSP `34`、BRAM `0`。这些数字必须标注为历史 OOC/IP 范围，不能替代当前完整系统的 post-implementation 结果。

详细报告：[HLS 综合结果](../hls/RESULTS.md)、[HLS 50 MHz OOC 结果](../hls/HLS5A_50MHZ_IMPL_RESULTS.md)、[RTL 协同仿真结果](../hls/RTL_COSIM_RESULTS.md)。

## 5. Vivado 系统构建结果

### 5.1 系统拓扑

```text
PS7 M_AXI_GP0
  -> SmartConnect
      -> AXI GPIO 0x41200000
      -> SNN AXI-Lite wrapper 0x43C00000
          -> indexed feature/weight/bias window
          -> Hybrid LIF HLS instance
```

Vivado 2025.1 使用当前开发板器件和 DDR 配置完成 synthesis、implementation、bitstream 和 XSA 导出。当前发布脚本为 [`create_evidence_system.tcl`](../vivado/evidence_rebuild/scripts/create_evidence_system.tcl)。

### 5.2 资源利用率

目标器件可用资源：LUT `53200`、FF `106400`、BRAM tile `140`、DSP `220`。

| 统计范围 | LUT | FF | BRAM | DSP |
|---|---:|---:|---:|---:|
| 完整 routed top | 8902（16.73%） | 21076（19.81%） | 0 | 34（15.45%） |
| SNN AXI wrapper hierarchy | 8416（15.82%） | 20461（19.23%） | 0 | 34（15.45%） |
| 集成 HLS instance `u_hls` | 7725（14.52%） | 640（0.60%） | 0 | 34（15.45%） |

独立 HLS export report 的 IP-only 资源为 LUT `772`、FF `640`、DSP `34`、BRAM `0`，与集成 hierarchy 的统计范围不同，不能混用。

### 5.3 时序、布线和功耗

| 指标 | 结果 |
|---|---:|
| 时钟约束 | 20.000 ns / 50 MHz |
| WNS | +4.776 ns |
| TNS | 0 ns |
| WHS | +0.072 ns |
| THS | 0 ns |
| setup/hold failing endpoints | 0 / 0 |
| fully routed nets | 26818 |
| routing errors | 0 |
| DRC errors | 0 |

功耗是 Vivado post-route vectorless/tool estimate：

| 范围 | 总功耗 | 动态 | 静态 | 置信度 |
|---|---:|---:|---:|---|
| 完整 PS7 + SmartConnect + SNN 系统 | 1.769 W | 1.626 W | 0.143 W | Medium |
| HLS IP-only routed estimate | 0.129 W | 0.026 W | 0.103 W | Medium |

reset switching activity 和 vectorless 活动率会影响估算准确度，因此不能把上述数值称为开发板实测功耗，也不能直接换算成实测单次推理能耗。

## 6. Vitis platform/application 和开发板结果

### 6.1 软件构建流程

当前 Vitis Unified 2025.1 流程为：

```text
XSA
  -> snn_evidence_platform platform component
  -> standalone_ps7_cortexa9_0 domain
  -> platform build / XPFM
  -> snn_best_fold9_replay 或 snn_latency_replay application
  -> 导入源码并 build / ELF
  -> 下载 bitstream、ELF，打开 UART 观察
```

应用使用平台自动生成的 `xparameters.h` 获取 AXI 地址，使用平台自动生成的 `xiltimer.h` 进行计时。不能把旧 BSP 目录中的头文件复制进应用，否则可能出现 CPU 时钟宏不匹配。

### 6.2 单样本回放顺序

每个样本执行：

```text
soft reset
  -> 写 vector id
  -> 写 1536 个 feature words
  -> 写 64 个 weight words
  -> 写 2 个 bias words
  -> 读取并比较 checksum
  -> START
  -> 轮询 DONE
  -> 读取 2 个 logits 和 32 个 counts
  -> CLEAR_DONE
```

### 6.3 板端证据

| 指标 | 结果 | 解释 |
|---|---:|---|
| VERSION/STATUS/AXI-Lite 路径 | PASS | 版本、状态和寄存器访问可返回 |
| checksum/logit/count 一致性 | 314/314 PASS | 板端输出逐项等于软件 golden 值 |
| 分类正确数 | 277/314 | 使用 fold9 测试标签计算 |
| fold9 子集准确率 | 88.2166% | 仅代表这 314 个固定回放样本 |
| AXI-Lite 输入写入 | 317 us/sample | PS 端测得的软件到 AXI 写入范围 |
| START 到 DONE | 8 us/sample | PS 端观察到的计算事务范围 |
| 完整回放 | 326 us/sample | 复位、写入、启动到 DONE 的总范围 |
| 完整回放吞吐率 | 3067.48 samples/s | `mean_samples_per_s_x100=306748` 除以 100 |
| 平均 ARM 轮询次数 | 93 | 软件轮询次数，不是 HLS 时钟周期 |

计时器自检输出 `TIMER_START_RESULT=PASS`，计数频率为 `333333343 counts/s`。

### 6.4 两个准确率不能混写

| 结果 | 样本范围 | 含义 |
|---|---|---|
| 72.39% | 完整 11-fold compatibility 软件实验 | 用于选择 Direct-current + Hybrid LIF 基准 |
| 88.2166% | fold9 固定回放子集 314 个样本 | 用于验证当前导出参数在板端的分类结果 |
| 314/314 PASS | 同一 fold9 子集 | 用于证明板端输出和软件 golden 的逐项一致性 |

正确汇报方式是：**软件 11-fold 基线为 72.39%；当前 fold9 的 314 个板端回放样本与软件输出 100% 一致，该子集按标签计算准确率为 88.2166%。**

## 7. 证据文件与工程位置

| 证据 | 仓库位置 |
|---|---|
| 本总览 | `docs/2026-07-31-snn-fpga-full-flow-overview.md` |
| 软件/HLS 基线摘要 | [`docs/direct_current_hls_baseline_summary.md`](direct_current_hls_baseline_summary.md) |
| 完整证据链细节 | [`docs/evidence_chain_report.md`](evidence_chain_report.md) |
| 硬件配置与工具来源 | [`docs/hardware_provenance.md`](hardware_provenance.md) |
| 性能、资源、时序、功耗 | [`docs/performance_report.md`](performance_report.md) |
| 软件六项 SNN 探索记录 | [`docs/teacher_report.md`](teacher_report.md) |
| HLS CSim/CSynth | [`hls/RESULTS.md`](../hls/RESULTS.md) |
| HLS RTL 协同仿真 | [`hls/RTL_COSIM_RESULTS.md`](../hls/RTL_COSIM_RESULTS.md) |
| Vivado 构建结果 | [`vivado/evidence_rebuild/E1_RESULTS.md`](../vivado/evidence_rebuild/E1_RESULTS.md) |
| Vivado 资源/时序/功耗结果 | [`vivado/evidence_rebuild/E4_RESULTS.md`](../vivado/evidence_rebuild/E4_RESULTS.md) |
| Vivado 发布工件 | [`vivado/evidence_rebuild/artifacts/`](../vivado/evidence_rebuild/artifacts/) |
| Vivado 原始报告 | [`vivado/evidence_rebuild/reports/`](../vivado/evidence_rebuild/reports/) |
| Vitis 板端结果 | [`vitis/evidence_rebuild/E3_RESULTS.md`](../vitis/evidence_rebuild/E3_RESULTS.md) |
| Vitis 回放源码 | [`vitis/evidence_rebuild/source/`](../vitis/evidence_rebuild/source/)、[`latency_source/`](../vitis/evidence_rebuild/latency_source/) |
| Vitis 平台和 ELF | [`vitis/evidence_rebuild/artifacts/`](../vitis/evidence_rebuild/artifacts/) |
| 工件 SHA-256 清单 | [`vivado/evidence_rebuild/EVIDENCE_MANIFEST.json`](../vivado/evidence_rebuild/EVIDENCE_MANIFEST.json) |

当前发布工件包括 bitstream、XSA、XPFM、平台 ZIP、两个 ELF 和 post-route DCP。工件哈希以 `EVIDENCE_MANIFEST.json` 为准。

## 8. 从头复现的最短路径

### 8.1 Vivado

环境要求：Vivado/Vitis 2025.1，目标器件 `xc7z020clg400-2`，使用 AX7020 模板派生的 PS7 配置。

```powershell
$repo = 'D:\eeg_fpga\snn_hybrid_eeg'
& 'D:\vitis\2025.1\Vivado\bin\vivado.bat' -mode batch `
  -source "$repo\vivado\evidence_rebuild\scripts\create_evidence_system.tcl" `
  -tclargs $repo "$repo\vivado\evidence_rebuild\run_20260731_attempt1" project_bitstream
```

预期得到 synthesis、implementation、bitstream、XSA 以及资源/时序/功耗报告。原始工作区被 Git 忽略，发布工件应复制到 `vivado/evidence_rebuild/artifacts/`。

### 8.2 Vitis

1. 使用 `vivado/evidence_rebuild/artifacts/snn_evidence_system.xsa` 创建 platform component。
2. 创建 `standalone_ps7_cortexa9_0` domain，先 build platform。
3. 使用生成的 XPFM 创建 application component。
4. 导入 `vitis/evidence_rebuild/latency_source/`，停用模板 `helloworld.c`，clean/build application。
5. 使用匹配的 bitstream、XSA、platform 和 ELF 下载开发板。
6. UART 选择 115200 baud，确认 VERSION、STATUS、checksum、logit、count 和最终 PASS 标记。

源文件只改变时，只需重建 application；XSA、domain 或 platform 配置改变时，才需要重建 platform。详细步骤见 [`docs/hardware_provenance.md`](hardware_provenance.md)。

## 9. 证据边界和下一步

当前不能宣称：

- 完整 CNN/GroupNorm 前端已经 HLS 化并部署到 PL；
- 已经实现 HP/DMA/DDR 流式输入；
- 88.2166% 是完整 11-fold 平均准确率；
- `8 us` 是 HLS IP 独立的 RTL cycle latency；
- `1.769 W` 或 `0.129 W` 是开发板实测功耗；
- 已经完成在线 EEG 连续采集、滤波、分段和端到端部署。

下一步建议按以下顺序推进：

1. 明确完整 CNN/GroupNorm 前端的硬件边界和数据搬运方案；
2. 评估 AXI-Lite indexed window 向 DMA/AXI-Stream 或 DDR 缓冲的演进；
3. 在 chronology/BS=1 协议明确后，重新计算严格在线场景的模型准确率；
4. 若论文需要功耗结论，使用板端仪器或明确的电源监测方法测量，而不是引用 vectorless estimate；
5. 保留当前 Hybrid LIF 读出头作为稳定的硬件回归基线。

## 10. 术语说明

- **Direct-current 编码**：把连续特征值直接作为 LIF 神经元的输入电流，不先转换成事件计数。
- **Hybrid LIF**：使用漏积分发放神经元完成时间累积，再用脉冲计数或发放率生成分类读出。
- **Q12.6**：总位宽 12 位、小数位 6 位的有符号定点格式，整数载荷除以 64 得到实际值。
- **AXI-Lite**：适合寄存器访问的轻量 AXI 总线，当前用于 PS7 写入特征和读取结果。
- **XSA/XPFM/ELF**：XSA 是 Vivado 硬件平台导出文件，XPFM 是 Vitis 软件平台文件，ELF 是 Cortex-A9 应用可执行文件。
- **WNS/TNS/WHS/THS**：分别表示 setup 最差裕量、setup 总负裕量、hold 最差裕量和 hold 总负裕量；正裕量且失败端点为 0 表示当前约束下时序通过。
- **Parity/一致性**：板端输出和软件 golden 值逐项相同；它与按标签统计的分类准确率是两个不同指标。
- **fold9 子集**：第 9 折固定测试样本。本次板端 314 个样本来自该子集，不能替代全 11 折统计。
