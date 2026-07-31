# 硬件与工具来源

更新时间：2026-07-31

本文记录当前可复现版本的硬件配置、工程位置和证据边界。所有硬件数字都绑定到仓库内的报告或发布工件，不把历史试验配置混入当前主线。

## 当前结论

当前主线已经完成：

1. Direct-current 编码的 Hybrid LIF 读出头 HLS 验证；
2. Zynq-7020 PS7、SmartConnect、Processor System Reset 与 SNN AXI-Lite wrapper 集成；
3. Vivado synthesis、implementation、bitstream 和 XSA 生成；
4. Vitis 2025.1 standalone platform/application 构建；
5. 开发板 314 个样本的逐样本回放、输出一致性和分类结果验证。

当前系统仍是“软件前端 + FPGA LIF 读出头”的协同验证，不是完整 CNN/GroupNorm 前端已经全部硬件化的结果。

## 冻结硬件契约

| 项目 | 当前值 | 说明 |
|---|---|---|
| Vivado/Vitis | 2025.1 | 使用本机安装版本 |
| FPGA | `xc7z020clg400-2` | AX7020 对应 Zynq-7020 器件 |
| DDR | `MT41J256M16 RE-125` | PS7 DDR 配置 |
| PS 时钟 | FCLK0 = 50 MHz | 周期 20 ns |
| 串口 | UART1，MIO 48/49 | 115200 baud |
| PS 主接口 | `M_AXI_GP0` enabled | PS 通过 AXI-Lite 访问 SNN wrapper |
| HP/DMA | disabled / 未使用 | 当前不是 DDR 流式数据通路 |
| AXI 互连 | SmartConnect 1.0 | BD 中实例名仍为 `axi_interconnect_0` |
| 复位 | Processor System Reset 5.0 | `FCLK_RESET0_N` 先进入复位同步模块 |
| SNN AXI 基地址 | `0x43C00000` | 地址范围 `0x43C00000` 到 `0x43C0FFFF` |
| HLS top | `hybrid_lif_head_q12_6` | Q12.6 Hybrid LIF 读出头 |

## 数据通路

```text
PS7 M_AXI_GP0
    -> SmartConnect
    -> snn_axi_memory_window
    -> hybrid_lif_head_q12_6
    -> AXI-Lite indexed registers
    -> PS7
```

复位路径为：

```text
PS7 FCLK_RESET0_N
    -> Processor System Reset/ext_reset_in
    -> peripheral_aresetn
    -> SmartConnect、AXI wrapper 和 HLS 用户逻辑
```

当前输入通过 AXI-Lite indexed window 写入 PL 侧本地状态，不经过 HP 端口、DMA 或 DDR 读写。DDR 配置必须与开发板一致，但本次回放的输入数据由 ARM 软件逐项写入。

## 模型与定点边界

- 软件参考模型：Channel8 EEG、CNN/GroupNorm 前端、自适应平均池化、Direct-current 输入和 Hybrid LIF 读出头。
- HLS/IP 边界：池化后的单样本特征电流和 32 路、48 步 Hybrid LIF 读出头。
- 单样本接口布局：软件参考侧为 `[32, 48]`，HLS 内部接口为时间优先 `[48][32]`。
- 定点格式：Q12.6，即整数载荷除以 64 后表示实际数值。
- 冻结常量：`beta_q=58`，`threshold_q=32`。
- 输出：两个有符号 logits、32 个 spike counts 和错误状态。

术语说明：Direct-current 表示连续特征直接作为 LIF 输入电流；LIF 是漏积分发放神经元；GroupNorm 是不依赖 batch 统计量的组归一化；logit 是 softmax 前的未归一化分类分数。

## 证据路径

### Vivado

```text
脚本：vivado/evidence_rebuild/scripts/create_evidence_system.tcl
工程：vivado/evidence_rebuild/run_20260731_attempt1/project/snn_evidence_system.xpr
bitstream：vivado/evidence_rebuild/artifacts/snn_evidence_system.bit
XSA：vivado/evidence_rebuild/artifacts/snn_evidence_system.xsa
报告：vivado/evidence_rebuild/reports/
```

脚本使用只读的 AX7020 PS7 模板，不修改用户的 `project_AX7020_template`。发布目录中的报告来自实际成功运行；`run_20260731_attempt1` 仅作为本机原始重建工作区保留并被 Git 忽略。

### Vitis

```text
平台发布包：vitis/evidence_rebuild/artifacts/snn_evidence_platform.zip
XPFM：vitis/evidence_rebuild/artifacts/snn_evidence_platform.xpfm
基础回放 ELF：vitis/evidence_rebuild/artifacts/snn_best_fold9_replay.elf
延迟回放 ELF：vitis/evidence_rebuild/artifacts/snn_latency_replay.elf
基础回放源码：vitis/evidence_rebuild/source/
延迟回放源码：vitis/evidence_rebuild/latency_source/
```

Vitis 流程必须按 `XSA -> platform/domain -> platform build -> XPFM -> application -> ELF` 执行。应用源码使用平台自动生成的 `xparameters.h` 和 `xiltimer.h`，不复制内部 BSP 头文件。

## 复现命令

### Vivado 2025.1

在 PowerShell 中执行：

```powershell
$repo = 'D:\eeg_fpga\snn_hybrid_eeg'
& 'D:\vitis\2025.1\Vivado\bin\vivado.bat' -mode batch `
  -source "$repo\vivado\evidence_rebuild\scripts\create_evidence_system.tcl" `
  -tclargs $repo "$repo\vivado\evidence_rebuild\run_20260731_attempt1" project_bitstream
```

需要确认 Tcl 输出 `SYNTH_STATUS=...Complete`、`IMPL_STATUS=...Complete` 和 `EVIDENCE_VIVADO_RESULT=PASS`。

### Vitis 2025.1

使用 Vitis Unified component flow：

```text
1. 以 vivado/evidence_rebuild/artifacts/snn_evidence_system.xsa 创建 platform component。
2. 创建 standalone_ps7_cortexa9_0 domain，先 build platform。
3. 以生成的 XPFM 创建应用 component。
4. 导入 vitis/evidence_rebuild/source 或 latency_source 到 src/。
5. 删除或停用模板 helloworld.c，执行 application build target=hw。
6. 保留生成的 XPFM、ELF、构建日志和平台版本信息。
```

源文件修改只需要 clean/build application，不需要重建 Vivado 或 platform；只有 XSA、domain 或 platform 配置变化时才重建 platform。

## 关键哈希

完整清单见 [EVIDENCE_MANIFEST.json](../vivado/evidence_rebuild/EVIDENCE_MANIFEST.json)。当前主工件哈希为：

| 工件 | SHA-256 |
|---|---|
| bitstream | `12750C21C246C35B5142948EF9CE845C57514F54725848034EDDA9A8EAD777D0` |
| XSA | `B07F9386871D330B2276A354C3F845BFE0223422FAE4561D616788DA3ACB8776` |
| XPFM | `F0B4C016A2A948D1ADA5153BEB2033F457BC5B93B0A4C4E37251426F11318DEC` |
| 延迟回放 ELF | `77C423D0B20CF34C34F31A3788127FD08EB91598FC39EA4223E7CB422B6DC77B` |

## 不应混淆的配置

历史 HLS-3/HLS-5A OOC 报告曾使用 `xc7z020clg400-1` 和 100 MHz/50 MHz 独立约束；它们保留在 HLS 历史报告中。当前完整 Zynq 系统证据统一使用本页的 `xc7z020clg400-2`、`MT41J256M16 RE-125` 和 50 MHz 配置。
