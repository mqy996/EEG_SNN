# 固定向量 replay wrapper：50 MHz Vivado 结果

日期：2026-07-25

## 结论

`hybrid_lif_head_q12_6` 已经能够被放入一个最小 RTL wrapper，并在 `xc7z020clg400-1`、20 ns/50 MHz 时钟约束下完成 Vivado synthesis、place 和 route；同时，XSim 对 HLS golden `threshold_edge` 向量的输出与软件参考一致。

这证明的是 **HLS RTL + ap_memory 接口 + 固定向量 wrapper 的集成可行性**，还不等于开发板部署。

## 数值回放

| 项目 | 结果 |
|---|---:|
| `logits[0]` | -116 |
| `logits[1]` | 120 |
| `spike_count[0]` | 1 |
| `spike_count[1]` | 48 |
| `spike_count[2]` | 1 |
| `spike_count[3]` | 1 |
| RTL 仿真周期 | 约 1680 |

## Vivado implementation

| 指标 | 数值 |
|---|---:|
| Part | `xc7z020clg400-1` |
| Clock | 20.000 ns / 50 MHz |
| WNS | 9.074 ns |
| TNS | 0 ns |
| WHS | 0.129 ns |
| THS | 0 ns |
| Unrouted nets | 0 |
| LUT | 954 |
| FF | 885 |
| DSP | 34 |
| BRAM | 0.5 Tile（1 个 RAMB18） |

## 证据文件

- Vivado Tcl：`vivado/replay/tcl/run_replay_impl.tcl`
- Vivado XDC：`vivado/replay/constraints/replay_50mhz.xdc`
- RTL wrapper：`vivado/replay/src/hls_replay_wrapper.v`
- XSim testbench：`vivado/replay/tb/tb_hls_replay_wrapper.sv`
- 固定向量：`vivado/replay/vectors/`
- 临时本机报告：`D:\tmp\snn_replay_wrapper_impl_fixed\vivado`（不提交生成目录）

## 限制与风险

- 顶层没有开发板引脚约束和 I/O 标准，DRC 的 `NSTD-1`、`UCIO-1` 需要在最终板级工程中解决。
- 当前 wrapper 的存储器由固定向量初始化，尚未提供 PS 动态写入 feature/weight/bias 的通路。
- 当前未生成 bitstream/XSA，未连接 PS、UART、DDR，也未测量真实板端延迟、吞吐或功耗。
- 因此本报告不能写成“已完成开发板验证”。
