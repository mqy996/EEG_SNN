# HLS-5A 工作总结：2026 年 7 月 25 日

## 一句话结论

截至 **2026 年 7 月 25 日**，Direct-current Hybrid-SNN 的 Hybrid LIF 定点读出头已经完成：

```text
Q12.6 软件参考
    ↓
HLS CSim / C 综合 / C-RTL 协同仿真
    ↓
固定向量 RTL wrapper
    ↓
Vivado 50 MHz synthesis / place / route
```

当前还没有完成真正的开发板验证。距离上板还差 Zynq PS/PL 系统封装、板级约束、bitstream/XSA、Vitis 控制程序和 UART 回放证据。

## 一、今天完成的工作

### 1. 确认本机 FPGA 工具链和目标条件

- Vitis/Vivado 版本：2025.1。
- 工具目录：`D:\vitis\2025.1`。
- 目标器件：`xc7z020clg400-1`。
- 系统时钟约束：20 ns，即 50 MHz。
- 50 MHz 条件参考了已有 CNN-LSTM Zynq 工程中的 PS FCLK0 配置，但不把旧工程结果直接当作 SNN 板端结果。

### 2. 梳理 HLS 顶层接口

当前 HLS top 为：

```text
hybrid_lif_head_q12_6
```

接口类型为：

```text
ap_ctrl_hs + ap_memory
```

主要接口包括：

- 控制：`ap_clk`、active-high `ap_rst`、`ap_start`、`ap_done`、`ap_idle`、`ap_ready`；
- 输入：`feature_current_q`、`weight_q`、`bias_q`；
- 输出：`logits_q`、`spike_count_q`。

这说明当前 HLS IP 不是可以直接由 ARM 通过 AXI-Lite 访问的完整系统 IP。后续仍需要增加 AXI/BRAM 或其他存储器和控制接口。

### 3. 创建固定向量 replay wrapper

在教师仓库新增：

```text
vivado/replay/src/hls_replay_wrapper.v
```

wrapper 的功能是：

```text
固定 Q12.6 输入向量
    ↓
feature / weight / bias 存储器
    ↓
hybrid_lif_head_q12_6
    ↓
logits / spike_count
```

当前使用 HLS golden contract 中的 `threshold_edge` 测试用例。它用于验证接口、地址、时序和数值一致性，不是训练模型、真实 EEG 数据或完整 CNN-SNN 系统。

### 4. 修复 `ap_memory` 同步读时序问题

最初 wrapper 将存储器建模为组合读。虽然可以通过综合和布局布线，但 RTL 仿真出现了错误的 spike count 和 `x` logits。

根因是：

> Vitis HLS 生成的 `ap_memory` 接口需要按照同步 RAM 语义处理，地址在时钟沿被采样，数据在后续阶段提供。

修复后：

- wrapper 对 HLS 输出地址进行寄存；
- 下一时钟阶段提供对应存储器数据；
- feature、weight、bias 和 spike count 均按同步读方式处理；
- testbench 对结果不一致时返回失败，不再出现“打印错误但最终 PASS”的假通过。

这个问题非常重要：

```text
Vivado 综合通过 ≠ RTL 功能正确
Vivado 布线通过 ≠ 硬件接口时序正确
```

### 5. 修复多维 weight 数组映射

C++ 中的权重定义是：

```text
weight_q[2][32]
```

从生成 RTL 的地址接口确认，它被扁平化为一个 64-word 逻辑存储区域，而不是两个完全独立的 32-word 存储器。

wrapper 因此使用：

```text
weight_mem[0..63]
```

并让两个 HLS 读端口访问这块共享的扁平存储区域。

### 6. 完成 XSim RTL 仿真

最终仿真输出：

```text
SNN replay simulation PASS cycles=1680 logits=(-116,120)
```

关键结果：

| 项目 | 结果 |
|---|---:|
| `logits[0]` | -116 |
| `logits[1]` | 120 |
| `spike_count[0]` | 1 |
| `spike_count[1]` | 48 |
| `spike_count[2]` | 1 |
| `spike_count[3]` | 1 |
| 仿真周期 | 约 1680 个时钟周期 |

这些结果与 HLS golden vector 和软件参考一致。

### 7. 完成 Vivado 50 MHz implementation

在修正后的 wrapper 上完成：

```text
synthesis
opt_design
place_design
route_design
timing analysis
utilization analysis
DRC
```

结果如下：

| 指标 | 结果 |
|---|---:|
| Part | `xc7z020clg400-1` |
| Clock | 20 ns / 50 MHz |
| WNS | 9.074 ns |
| TNS | 0 ns |
| WHS | 0.129 ns |
| THS | 0 ns |
| Unrouted nets | 0 |
| LUT | 954 |
| FF | 885 |
| DSP | 34 |
| BRAM | 0.5 Tile，约 1 个 RAMB18 |

这证明当前固定向量 wrapper 在目标器件和 50 MHz 内部时钟约束下可以完成 Vivado implementation。

## 二、今天没有完成的工作

今天没有完成：

- Zynq Processing System 7 系统封装；
- AXI-Lite、AXI BRAM 或 DDR 数据接口；
- 开发板精确型号对应的 master XDC；
- 时钟输入、UART、I/O standard 等板级约束；
- bitstream；
- XSA/HWH；
- Vitis standalone 控制程序；
- JTAG 下载和 UART 回放；
- 实际开发板输出日志；
- 板端延迟、吞吐率和功耗测量；
- CNN 前端和完整 CNN-SNN 端到端硬件部署。

## 三、距离上板还差什么

### 阶段 1：确认板级信息

必须首先确认：

- 开发板完整型号；
- 官方 master XDC；
- PL 时钟输入引脚和频率；
- UART 使用 PS MIO 还是 PL 引脚；
- JTAG 连接方式；
- 板级 I/O standard 和电压；
- Vivado board part 或 PS preset。

当前已有 CNN-LSTM 工程记录了 Zynq-7020 和 50 MHz PS FCLK0，但旧工程存在历史绝对路径、旧 HLS IP 路径和 Windows 长路径问题，因此只能作为参考，不能直接作为 SNN 工程使用。

### 阶段 2：建立最小 PS/PL 系统

推荐的第一版结构：

```text
Zynq PS7
    ├── FCLK_CLK0 = 50 MHz
    ├── Processor System Reset
    ├── AXI-Lite 控制接口
    └── AXI BRAM / BRAM 数据接口
             ↓
       SNN replay memory wrapper
             ↓
       hybrid_lif_head_q12_6
```

第一版不需要马上硬件化 CNN 前端，只需要让 ARM 能够：

1. 写入固定 feature vector；
2. 写入 weight 和 bias；
3. 清空输出存储器；
4. 触发 `ap_start`；
5. 等待 `ap_done`；
6. 读取 logits 和 spike count。

### 阶段 3：生成 bitstream/XSA

完成 PS/PL wrapper 和板级 XDC 后，生成：

```text
.bit
.xsa
.hwh
```

同时保留：

- Vivado/Vitis 版本；
- target part；
- 时钟约束；
- utilization/timing/DRC 报告；
- bitstream 和 XSA 的校验值。

### 阶段 4：编写 Vitis 板端程序

Vitis 程序需要完成：

```text
UART 初始化
    ↓
写入 feature / weight / bias
    ↓
启动 HLS IP
    ↓
轮询 ap_done
    ↓
读取 logits / spike_count
    ↓
UART 打印结果
```

第一版仍然只回放 `threshold_edge`，预期结果为：

```text
logits=(-116,120)
spike_count[0..3]=(1,48,1,1)
```

### 阶段 5：形成板端证据

真正的板端验证至少要保留：

- bitstream/XSA；
- Vitis 工程或可复现程序；
- 输入向量身份和 hash；
- 软件参考输出；
- UART 日志；
- 板端输出；
- 软件/RTL/板端结果对照；
- 运行周期或墙钟时间；
- 测量方法和环境说明。

只有这些证据齐全后，才能称为“完成开发板固定向量回放验证”。

## 四、当前可以向老师汇报的结论

可以这样汇报：

> 截至 2026 年 7 月 25 日，Direct-current Hybrid-SNN 的 Hybrid LIF Q12.6 定点读出头已经完成 HLS、RTL wrapper、XSim 和 50 MHz Vivado implementation 验证。固定向量仿真输出与软件参考一致，Vivado 在 `xc7z020clg400-1` 上实现通过。当前尚未完成 Zynq PS/PL 系统、bitstream/XSA 和开发板 UART 回放，下一步将先完成最小 PS/PL 数据通路，再进行固定向量上板验证。

不应表述为：

```text
已经完成 SNN FPGA 部署
已经完成开发板验证
已经完成完整 CNN-SNN 端到端实现
```

## 五、Git 与文档记录

教师仓库本次提交：

```text
df1027f feat(vivado): add fixed-vector SNN replay wrapper evidence
```

课题根仓库本次提交：

```text
e73461c chore(task): record corrected HLS replay integration evidence
```

相关文件：

- `vivado/replay/README.md`
- `vivado/replay/reports/REPLAY_WRAPPER_50MHZ_RESULTS.md`
- `vivado/replay/src/hls_replay_wrapper.v`
- `vivado/replay/tb/tb_hls_replay_wrapper.sv`
- `.trellis/tasks/07-25-hls-5a-vivado-50mhz/implement.md`
- `.trellis/spec/compactcnn/fpga/hls-structure.md`

## 六、总结机制说明

### 不是只依赖对话记忆

正常情况下，我会综合以下信息来总结：

1. 当前会话中实际执行过的命令和修改；
2. Git diff、commit 和仓库状态；
3. Trellis task 的 `prd.md`、`design.md`、`implement.md`、`check.jsonl`；
4. HLS/Vivado/XSim 的实际日志和报告；
5. 教师仓库中的 README、结果报告和复现脚本；
6. `.trellis/workspace/` 中的工作日志；
7. 当前会话上下文中的历史结论。

对今天的总结，主要依据的是实际文件和报告，而不是凭空回忆。特别是最终的 WNS、WHS、LUT、FF、DSP、BRAM 和 XSim 输出，都是从本地生成的报告和日志中核对后的结果。

### Trellis 是否每次自动生成总结

不是每一次普通对话都会自动生成一份完整的总结 Markdown。

Trellis 更准确地说是分层记录：

- 任务目标：`prd.md`；
- 技术设计：`design.md`；
- 执行过程和结果：`implement.md`；
- 检查过程：`check.jsonl`；
- 会话经验：`.trellis/workspace/` journal；
- 长期规则：`.trellis/spec/`。

因此，今天的工作已经被记录在：

```text
.trellis/tasks/07-25-hls-5a-vivado-50mhz/implement.md
.trellis/spec/compactcnn/fpga/hls-structure.md
```

本文件是面向你和老师阅读的**阶段性总结**，不是单纯依赖会话记忆生成的临时文字。

### 仍然存在的限制

如果过去某次工作没有：

- 建立 Trellis task；
- 更新 `implement.md`；
- 保存实验脚本或报告；
- 形成 Git commit；

那么以后恢复时就不能保证能够完整重建当时的全部细节，只能结合 Git、文件、日志和对话上下文进行恢复。因此，重要实验最好都保留：

```text
任务记录 + 可执行脚本 + 原始报告 + 结论 Markdown + Git commit
```
