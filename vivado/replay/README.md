# Vivado replay wrapper

本目录是 Hybrid LIF HLS IP 的 **固定向量集成烟雾测试（smoke test）**，用于在进入真实 Zynq PS/PL 和开发板回放前，先验证 HLS 生成 RTL、`ap_memory` 存储器接口和 50 MHz Vivado 实现链路。

> 当前结果不是开发板验证，也不是完整 EEG 端到端部署。没有生成 bitstream/XSA，也没有加入开发板引脚约束。

## 当前基线

- HLS top：`hybrid_lif_head_q12_6`
- 算术契约：有符号 Q12.6，输入布局 `feature_current_q[48][32]`，时间主序
- HLS 存储接口：`feature_current_q`、扁平化的 `weight_q`、`bias_q`、`logits_q`、`spike_count_q`
- 目标器件：`xc7z020clg400-1`
- 时钟约束：20 ns，即 50 MHz
- 使用工具：Vivado/Vitis 2025.1
- 测试向量：HLS golden contract 的 `threshold_edge`

## 已完成证据

1. HLS IP 生成并通过 50 MHz out-of-context implementation。
2. `hls_replay_wrapper` 连接 HLS 的 `ap_ctrl_hs` 和同步 `ap_memory` 读写端口。
3. Vivado 固定向量 wrapper implementation 通过：
   - WNS：9.074 ns
   - TNS：0 ns
   - WHS：0.129 ns
   - THS：0 ns
   - 未布线网络：0
   - LUT：954
   - FF：885
   - DSP：34
   - BRAM：0.5 Tile（1 个 RAMB18）
4. Vivado XSim RTL 仿真通过：
   - `logits=(-116, 120)`
   - `spike_count[0..3]=(1,48,1,1)`
   - 运行约 1680 个 50 MHz 时钟周期

## 重要边界

- `replay_50mhz.xdc` 只约束 wrapper 内部 `clk`，并明确将复位、启动和查询端口作为 smoke harness 输入处理。由于没有开发板 I/O 时序和 I/O 标准，DRC 仍会报告 `NSTD-1`/`UCIO-1` critical warning；这不是最终 bitstream 的合格约束。
- 当前 wrapper 使用固定向量初始化片上存储器，目标是验证接口和数据通路，不代表 PS 可以动态写入模型数据。
- `logits` 和 `spike_count` 的软件参考值来自 `hls/hybrid_lif_head/golden/vectors_q12_6.json`；该文件是合成参考向量，不是训练模型或真实 EEG 结果。

## 复现

在 `snn_hybrid_eeg` 根目录运行：

```powershell
# RTL 仿真（会重新生成临时 HLS RTL）
.\vivado\replay\scripts\run_replay_sim.ps1 -WorkDir D:\tmp\snn_replay_sim

# Vivado synthesis/implementation（不会生成 bitstream）
.\vivado\replay\scripts\run_replay_impl.ps1 -WorkDir D:\tmp\snn_replay_impl
```

脚本使用本机 Vitis/Vivado 2025.1 安装位置 `D:\vitis\2025.1`，工具不在 PATH 时也可以运行。

## 下一步

1. 确认开发板精确型号、master XDC、JTAG/UART 连接和板端时钟来源。
2. 将固定初始化 wrapper 改为可由 Zynq PS/AXI 或 BRAM 控制器访问的系统 wrapper。
3. 为最终系统加入板级 XDC、PS 配置、bitstream/XSA、Vitis standalone 回放程序和 UART 日志。
4. 只有保留 bitstream/XSA、输入身份、输出对照、UART 日志和测量方法后，才宣称完成板端验证。
