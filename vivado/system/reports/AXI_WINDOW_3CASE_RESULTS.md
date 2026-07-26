# HLS-5A.2：AXI-Lite wrapper 三用例验证结果

日期：2026-07-26

## 验证范围

从 `hls/hybrid_lif_head/golden/vectors_q12_6.json` 自动生成 3 组 AXI memory-window 输入和期望文件：

- `threshold_edge`
- `signed_currents`
- `rounding_and_reset`

每组用例执行：

1. AXI 写入 1536 个 feature、64 个 weight、2 个 bias；
2. `start`；
3. 第一次运行期间发送非法重复 start 和 input data 写入，确认 busy 保护；
4. 轮询 `done_latched` 并读回 2 个 logits、32 个 spike counts；
5. 使用 `clear_done` 后重复运行一次，验证 call-local 状态初始化；
6. 使用 `soft_reset` 清除 wrapper 输出和会话状态。

## 结果

XSim 输出：

```text
SNN AXI memory-window 3-case simulation PASS writes=9852 reads=3582
```

| case | 期望 logits | 期望 count 前四项 | 两次运行 | HLS kernel cycles |
|---|---|---|---|---:|
| `threshold_edge` | `(-116, 120)` | `(1, 48, 1, 1)` | 2/2 PASS | 1680 |
| `signed_currents` | `(1152, -1142)` | `(26, 2, 7, 7)` | 2/2 PASS | 1680 |
| `rounding_and_reset` | `(-4, 16)` | `(1, 0, 0, 1)` | 2/2 PASS | 1680 |

所有 3×2 次运行的 2 个 logits 和 32 个 spike counts 均与 golden 完全一致，没有 X/unknown、timeout 或 mismatch。

## AXI 统计

- 总写事务：9852。
- 总读事务：3582。
- 每次 kernel 的 HLS RTL 周期：1680。
- AXI `done_latched` 轮询次数约 558–561 次；这是 AXI 软件轮询开销，不等于 HLS kernel latency。

## 重要边界

重复调用验证使用 `clear_done` 而不是在两次调用之间插入 `soft_reset`：HLS 生成 RTL 的 `ap_memory` RAM 模块不直接响应 reset，HLS top 在新的 `ap_start` 时负责 call-local 初始化。`soft_reset` 仍单独验证了 wrapper 状态、logits/count 输出和会话状态清除，并在每组用例结束后执行。

本报告证明的是 AXI wrapper + HLS readout head 的 RTL 回放正确性，不证明 PS7、XSA、bitstream 或真实开发板运行。
