# HLS-4 RTL C/RTL 协同仿真结果

## 结论

**HLS-4 C/RTL 协同仿真通过。** Direct-current Q12.6 Hybrid LIF readout head 已由 Vitis HLS 生成 Verilog RTL，并使用 XSIM 完成 C/RTL 协同仿真。

该结果验证的是 HLS 读出头的顶层接口和定点行为，不是完整 CNN-SNN 在 EEG 数据集上的分类结果。

## 配置

| 项目 | 实际值 |
|---|---|
| 工具 | Vitis HLS 2025.1，HLS Build 6135595 |
| RTL 仿真器 | XSIM / Vivado 2025.1 |
| RTL 语言 | Verilog |
| Top function | `hybrid_lif_head_q12_6` |
| Target part | `xc7z020clg400-1` |
| HLS 时钟约束 | 10 ns / 100 MHz |
| C testbench | `tb_hybrid_lif_head_cosim.cpp` |
| C 测试用例 | 3/3 PASS |
| RTL transactions | 6/6 完成 |
| Final status | PASS |

## 运行入口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File hls/hybrid_lif_head/scripts/run_cosim.ps1
```

脚本先使用匹配的 HLS 配置重新生成 solution，再运行：

```text
vitis-run --mode hls --cosim
```

协同仿真关闭 `wave_debug`，以保证 Windows 环境下可以无人值守运行；不代表省略 RTL 验证。

## 验证内容

专用 cosim testbench 只调用正式 HLS top function，验证以下输出：

- `logits_q[2]`；
- `spike_count_q[32]`；
- 从 `spike_count_q` 推导的 `rate_q[32]`；
- 重复调用时的调用级状态复位。

黄金用例为：

```text
threshold_edge
signed_currents
rounding_and_reset
```

C 侧 3/3 用例通过，RTL 侧共完成 6/6 次 transaction。

## 证据边界

HLS-2 CSim 中用于调试的 `spikes[48][32]` 和 `membrane_after_reset[48][32]` 不是 HLS-4 当前正式 RTL top 的输出端口。因此，本报告只把它们作为 HLS-2 调试证据，不把它们误写成 HLS-4 RTL 接口结果。

当前证据等级如下：

| 证据 | 状态 | 可以支持的结论 |
|---|---|---|
| 软件 Q12.6 参考 | 已完成 | 定点范围和算法参考 |
| Vitis CSim | 已完成 | HLS C++ 与黄金向量一致 |
| Vitis CSynth | 已完成 | 综合阶段的资源和延迟估计 |
| Vitis C/RTL cosim | **已完成** | RTL 顶层输出与黄金向量一致 |
| Vivado implementation | 未完成 | 尚不能声称布局布线后时序收敛 |
| 50 MHz 系统集成 | 未完成 | 尚不能声称已接入原 CNN-LSTM/Zynq 系统 |
| 板端回放和功耗 | 未完成 | 尚不能声称端到端部署指标 |

## 已记录的问题与修复

1. 曾使用旧 HLS solution 直接运行 cosim，出现 `COSIM-5: C/RTL co-simulation file generation failed`。后来改为先用匹配配置重新执行 HLS build，再运行 cosim。
2. 原始 testbench 同时调用调试辅助函数和正式 top function；HLS-4 改为只调用正式 top function。
3. `cosim.wave_debug=true` 会在 Windows 启动 XSIM 图形界面并阻塞自动流程，最终设置为 `false`。
4. 本机 Vitis 2025.1 不支持 `vitis-run --cosim --setup`，脚本不再使用该选项。

## 下一步

下一步是将该读出头导入 Vivado，在 50 MHz/20 ns 的系统时钟参考下完成 IP 集成、接口回放和时序验证。此后再决定是否继续硬件化 CNN/GroupNorm 前端。