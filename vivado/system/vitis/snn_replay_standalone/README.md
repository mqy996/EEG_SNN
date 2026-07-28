# HLS-6C Vitis standalone 板端回放

本目录保存基于 HLS-6B SmartConnect SNN wrapper XSA 的 Cortex-A9 standalone 回放源代码。程序只使用 SNN wrapper AXI-Lite 窗口，不访问 DMA、HP 或 DDR 数据通路。

## 当前状态

截至 2026-07-28，本轮 HLS-6C 在 Vitis 2025.1 的 platform/BSP 构建阶段被阻塞：Vitis 生成了平台目录，但 `export/.buildstatus` 为 `export=ERROR`，没有生成可验证的 `.xpfm` 或应用 ELF。因此没有进行 bitstream 下载、UART 回放或板端 PASS 声明。完整证据见 `vivado/system/reports/HLS6C_VITIS_BOARD_REPLAY.md`。

## 输入身份

- XSA：`vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.xsa`
- bitstream：同目录的 `smartconnect_snn_wrapper_50mhz.bit`
- golden manifest：`include/golden_vectors_manifest.json`
- golden SHA-256：`8f73683b4448f8315af76151e36dacff494197c0caf8bcf2e8ace01ad301604a`
- target：`ps7_cortexa9_0` + `standalone_a9_0`

## 可复现构建

在 Windows Vitis 2025.1 环境中运行；`SNN_REPLAY_WORKSPACE` 应指向不存在的新目录，脚本会让 Vitis 初始化 workspace 元数据：

```powershell
$env:SNN_REPLAY_XSA = (Resolve-Path vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.xsa).Path
$env:SNN_REPLAY_WORKSPACE = 'D:/v6c_hls6c_20260728'
$env:SNN_REPLAY_PLATFORM = 'p6c'
$env:SNN_REPLAY_APP = 'a6c'
$env:SNN_REPLAY_SOURCE = (Resolve-Path vivado/system/vitis/snn_replay_standalone).Path
$env:SNN_REPLAY_PLATFORM = 'snn_replay_platform_hls6c_20260728'
$env:SNN_REPLAY_APP = 'snn_replay_app_hls6c_20260728'
& 'D:/vitis/2025.1/Vitis/bin/vitis.bat' -s `
  vivado/system/vitis/snn_replay_standalone/scripts/create_vitis_standalone_app.py
```

成功时脚本必须同时打印 `PLATFORM_XPFM=...`、`ELF=...` 和 SHA-256，并且对应 `.buildstatus` 必须为 `SUCCESS`；Vitis 进程退出码不能替代这些文件证据。

## 程序证据标记

程序在可能阻塞的 AXI 事务前输出 marker，依次覆盖 `VERSION_BEGIN`、`AXI_RESET_SENT`、`AXI_FIRST_FEATURE_WRITE`、`AXI_START_SENT`、`DONE`、`AXI_CLEAR_DONE_SENT`。每组 case 输出 checksum、status、poll 次数、error status、两个 logits 和 32 个 counts 的 actual/expected 对照。
