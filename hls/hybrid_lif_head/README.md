# Direct-current Hybrid-SNN HLS 基线（更新至 AX7020 实际器件）

## 当前状态

HLS-6A 已完成：Hybrid LIF 读出头已经使用实际 AX7020 器件 `xc7z020clg400-2` 和 50 MHz（20 ns）约束重新验证。

- C simulation：3/3 PASS
- C/RTL co-simulation：3/3 PASS
- HLS/Vivado implementation：PASS
- 时序：PASS
- 可供后续 Vivado 集成的 HLS IP：已生成

## 目标网络边界

HLS Phase-1 仍只包含 Hybrid LIF 读出头，不包含完整 CNN/GroupNorm 前端：

```text
CNN/GroupNorm 软件前端
    → Direct-current 编码
    → 48-step Hybrid LIF
    → spike counts / rate
    → Linear(32, 2)
```

## HLS-6A 实现结果

| 指标 | 结果 |
|---|---:|
| 器件 | xc7z020clg400-2 |
| 时钟约束 | 20 ns / 50 MHz |
| LUT | 772 |
| FF | 640 |
| DSP | 34 |
| BRAM | 0 |
| 实现后关键路径周期 | 9.692 ns |
| WNS | 10.308 ns |
| 时序 | PASS |

HLS compile 阶段的 estimated Fmax 为约 75.92 MHz；实现后报告给出的关键路径周期为 9.692 ns。二者属于不同阶段，后续汇报时不要混写。

分类器循环的主要调度 II 包括 1 和 16；II=16 与 `weight_q` 存储器端口限制有关，后续如需提高吞吐，应单独研究数组分区/存储器端口。

## 接口契约

- 顶层：`hybrid_lif_head_q12_6`
- 控制协议：`ap_ctrl_hs`
- 输入：48×32 feature current、2×32 weight、2 bias
- 输出：2 logits、32 spike counts
- 定点：Q12.6 接口语义保持不变
- 旧/新生成 IP 的 component.xml 均为 30 个同名顶层端口，接口哈希对照已保留在 HLS-6A 任务证据中。

## 证据边界

当前结果证明 HLS 核在实际器件和 50 MHz 约束下通过 C、RTL 和实现验证，并已生成 IP 包。

当前结果尚不证明：

- SmartConnect + HLS wrapper 已集成；
- PS 已经能够访问 HLS 核；
- 固定向量已在开发板完成回放；
- CNN/GroupNorm 前端已经硬件化；
- 完整 EEG 在线端到端分类已完成。

下一步是 HLS-6B：保留已通过的 SmartConnect + AXI GPIO 健康检查，在同一系统中加入 SNN AXI-Lite wrapper/HLS IP。
