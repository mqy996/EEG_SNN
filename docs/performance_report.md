# SNN FPGA 性能与资源结果

更新时间：2026-07-31

本文把软件模型结果、板端回放结果、资源/时序/功耗结果分开记录。它们对应不同的评估范围，不能直接互相替代。

## 1. 软件模型结果

Direct-current + Hybrid LIF head 在完整 11-fold compatibility 实验中的汇总结果为：

| 指标 | 结果 |
|---|---:|
| Accuracy | 72.39% |
| Macro-F1 | 71.00% |
| 平均 spike rate | 25.18% |
| 评估协议 | 11-fold、compatibility 数据顺序 |

这 72.39% 是完整 11 折软件实验的平均结果，不是下面 fold9 板端子集的准确率。

## 2. 板端 fold9 回放

板端应用回放固定的 fold9 测试集，共 314 个样本。每个样本都检查 checksum、两个 logits 和 32 个 spike counts。

| 指标 | 结果 | 解释 |
|---|---:|---|
| 输出一致性 | 314/314 PASS | 软件黄金值与板端输出逐项一致 |
| 分类正确数 | 277/314 | 使用测试集标签计算 |
| 分类准确率 | 88.2166% | `277 / 314`，只代表 fold9 测试子集 |
| 平均轮询次数 | 93 | ARM 软件轮询次数，不是 FPGA 时钟周期 |

因此，正确的汇报方式是：**fold9 板端回放输出与黄金值 100% 一致，在该 314 样本子集上的分类准确率为 88.2166%**。不能把 88.2166% 写成完整 11 折平均准确率。

## 3. 单样本延迟与吞吐率

计时程序使用平台自动生成的 `xiltimer.h` 接口，并在第一次 `XTime_GetTime()` 前通过 `usleep(1)` 启动计时器；串口输出包含 `TIMER_START_RESULT=PASS` 和 `COUNTS_PER_SECOND=333333343`。

| 范围 | 平均值 | 最小值 | 最大值 |
|---|---:|---:|---:|
| AXI-Lite 输入写入 | 317 us | 317 us | 317 us |
| START 写入到 DONE 状态 | 8 us | 8 us | 8 us |
| 完整回放：复位 + 输入写入 + 启动到 DONE | 326 us | 326 us | 326 us |

完整回放吞吐率为：

```text
mean_samples_per_s_x100 = 306748
实际吞吐率 = 3067.48 samples/s
```

上述三个时间是 ARM 端通过 AXI-Lite 观察到的软件到硬件范围，不是 HLS 内核单独的 RTL cycle latency。历史 HLS-3 C 综合报告的 1688 cycles @ 100 MHz 仍是综合估计，必须与板端 8 us 保持分开表述。

## 4. Vivado post-implementation 资源

目标器件为 `xc7z020clg400-2`，可用资源为 LUT 53200、FF 106400、BRAM tile 140、DSP 220。

| 范围 | LUT | FF | BRAM | DSP |
|---|---:|---:|---:|---:|
| 完整 routed top | 8902（16.73%） | 21076（19.81%） | 0 | 34（15.45%） |
| SNN AXI wrapper hierarchy | 8416（15.82%） | 20461（19.23%） | 0 | 34（15.45%） |
| 集成 HLS instance `u_hls` | 7725（14.52%） | 640（0.60%） | 0 | 34（15.45%） |

独立 HLS export report 的 IP-only 资源为 772 LUT、640 FF、34 DSP、0 BRAM。它与集成后的 `u_hls` hierarchy 是不同统计范围，不能用 772 替代完整系统的资源结果。

## 5. Vivado 时序与布线

| 指标 | 结果 |
|---|---:|
| 时钟约束 | 20.000 ns / 50 MHz |
| WNS | +4.776 ns |
| TNS | 0 ns |
| WHS | +0.072 ns |
| THS | 0 ns |
| setup failing endpoints | 0 |
| hold failing endpoints | 0 |
| fully routed nets | 26818 |
| routing errors | 0 |
| DRC errors | 0 |

实现报告中有 DSP 输入未流水化的优化警告，但没有造成 DRC 错误或时序失败。

## 6. 功耗

功耗来自 Vivado post-route vectorless/tool estimate，不是开发板电源仪器实测：

| 范围 | 总功耗 | 动态 | 静态 | 置信度 |
|---|---:|---:|---:|---|
| 完整 PS7 + SmartConnect + SNN 系统 | 1.769 W | 1.626 W | 0.143 W | Medium |
| HLS IP-only routed estimate | 0.129 W | 0.026 W | 0.103 W | Medium |

完整系统报告提示 reset/vectorless switching activity 会影响估计准确度。当前不能把这些数字写成板端实测功耗，也不能据此直接给出每次推理能耗。

## 7. 原始报告位置

- Vivado 资源、时序、功耗和 DRC：`vivado/evidence_rebuild/reports/`
- HLS C 综合历史结果：`hls/RESULTS.md`
- HLS 50 MHz OOC 结果：`hls/HLS5A_50MHZ_IMPL_RESULTS.md`
- 板端回放结果：`vitis/evidence_rebuild/E3_RESULTS.md`
- 统一工件哈希：`vivado/evidence_rebuild/EVIDENCE_MANIFEST.json`
