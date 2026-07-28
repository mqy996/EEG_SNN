# HLS-6A 板级器件与 50 MHz 重基线结果

- **日期**：2026-07-28
- **工具**：Vitis/Vivado HLS 2025.1
- **目标器件**：`xc7z020clg400-2`（工具显示为 `xc7z020-clg400-2`）
- **时钟约束**：20 ns，即 50 MHz
- **顶层**：`hybrid_lif_head_q12_6`

## 1. 本任务做了什么

本任务没有修改 Hybrid LIF 算法、Q12.6 定点语义、输入输出数组形状或 golden vectors，只把 HLS 目标从旧配置：

```text
xc7z020clg400-1
```

重新锁定为实际 AX7020 工作基线：

```text
xc7z020clg400-2
```

并使用 50 MHz（20 ns）重新执行 C simulation、C/RTL co-simulation 和 HLS/Vivado implementation。

## 2. 验证结果

```text
HLS-2 C simulation PASS cases=3
HLS-4 C/RTL co-simulation PASS cases=3
C/RTL co-simulation finished: PASS
HLS/Vivado implementation: PASS
Timing met
```

因此 HLS-6A 通过，可以进入后续 HLS-6B 的 SmartConnect + SNN wrapper 集成。

## 3. 实现资源与时序

Post-implementation 结果：

| 指标 | 结果 |
|---|---:|
| LUT | 772 |
| FF | 640 |
| DSP | 34 |
| BRAM | 0 |
| SRL | 17 |
| 目标周期 | 20.000 ns |
| 实现后关键路径周期 | 9.692 ns |
| WNS | 10.308 ns |
| 时序 | PASS |

HLS implementation compile 阶段给出的估算 Fmax 为约 **75.92 MHz**；实现后 9.692 ns 的关键路径对应约 **103.18 MHz**，在 50 MHz 约束下有较充分余量。论文或汇报中应优先引用实现后报告，而不是把估算 Fmax 与实现后 Fmax 混写。

循环调度中，主要分类循环的最终 II 包括 1 和 16；II=16 来自分类器权重存储器端口限制。该结果不影响 50 MHz 通过，但说明后续若要优化吞吐，应研究权重数组分区/存储器端口，而不是直接改变数值语义。

## 4. 接口兼容性

生成 RTL 顶层仍为：

```text
hybrid_lif_head_q12_6
```

协议仍为：

```text
ap_ctrl_hs
```

主要端口仍包括：

```text
ap_clk / ap_rst / ap_start / ap_done / ap_idle / ap_ready
feature_current_q
weight_q
bias_q
logits_q
spike_count_q
```

生成 IP 包：

```text
artifacts/board_target_50mhz/xilinx_com_hls_hybrid_lif_head_q12_6_1_0.zip
```

接口没有发生本任务范围外的变化，可以作为 HLS-6B 的输入。

## 5. 证据边界

本任务证明的是：

> 面向实际 AX7020 器件和 50 MHz 时钟约束，Hybrid LIF HLS 核通过了 C 仿真、C/RTL 协同仿真和 Vivado 实现，并生成了可供后续 Vivado 集成的 HLS IP 包。

本任务**没有**证明：

- SmartConnect + HLS wrapper 已经集成；
- Zynq PS 已经访问 HLS IP；
- 开发板已经完成 SNN 固定向量回放；
- 完整 CNN-SNN EEG 已经端到端部署。

这些属于 HLS-6B/HLS-6C。

## 6. 交付物

```text
config/hls_config.cfg                 # 已更新为 -2 / 20ns
config/hls_cosim_config.cfg           # 已更新为 -2 / 20ns
config/hls_impl_50mhz.cfg             # 已更新为 -2 / 20ns
artifacts/board_target_50mhz/          # 独立交付物和日志
scripts/run_board_target_50mhz.ps1    # 可复现实验入口
```

### 运行延迟与 II

- HLS 数据摘要中的顶层 latency 为 1687 cycles，顶层 interval 为 1688 cycles（以生成摘要中的 top-level schedule 为准）。
- 在 50 MHz 下，1687 cycles 约为 33.74 μs；1688-cycle interval 约为 33.76 μs。
- 该 HLS latency 是核级周期估计，不包含 PS 端 AXI-Lite 写入 1536 个 feature、64 个 weight、2 个 bias、轮询和读取输出的端到端软件时间。
