# HLS-5A.4/5B：Vitis standalone 固定向量回放程序

## 作用

`src/main.c` 在 Zynq PS 裸机环境中回放三个 Q12.6 golden case：

- `threshold_edge`
- `signed_currents`
- `rounding_and_reset`

程序按“读取版本 → soft reset → indexed 写入 → XOR checksum → start → 轮询 done → 读回 logits/count → UART 输出”的顺序执行。

## 生成 ELF

使用 Vitis 2025.1 Python API：

```powershell
$env:SNN_REPLAY_XSA = (Resolve-Path vivado/system/artifacts/snn_replay_system.xsa).Path
$env:SNN_REPLAY_WORKSPACE = 'D:/eeg_fpga/vitis_board_replay_uart1_20260727'
$env:SNN_REPLAY_SOURCE = (Resolve-Path vivado/system/vitis/snn_replay_standalone).Path
& 'D:/vitis/2025.1/Vitis/bin/vitis.bat' -s `
  vivado/system/vitis/snn_replay_standalone/scripts/create_vitis_standalone_app.py
```

脚本使用 `empty_application` 模板，避免 Vitis 2025.1 中不存在的 `empty` 模板；脚本会检查最终 ELF 是否真实存在，不以 Vitis Python 进程退出码代替构建结果。

## 板端 UART 输出

板端使用 UART1 MIO48/49，COM5，115200-8N-1。独立 UART smoke test 已确认串口路径；SNN ELF 当前在首次 AXI 读 `VERSION` 时阻塞，以下 PASS 文本是软件/RTL 预期格式，不是本轮板端已确认结果：

```text
SNN standalone replay start
BASE=0x43C00000 VERSION=0x00010001 JSON_SHA256=8f73683b4448f8315af76151e36dacff494197c0caf8bcf2e8ace01ad301604a
VECTOR=threshold_edge PASS checksum=0x00000FB5 status=0x00000003
VECTOR=signed_currents PASS checksum=0x00000130 status=0x00000003
VECTOR=rounding_and_reset PASS checksum=0x00000E50 status=0x00000003
SNN standalone replay PASS cases=3
```

构建和板端证据见 [`../../reports/HLS5B_BOARD_RESULTS.md`](../../reports/HLS5B_BOARD_RESULTS.md)。
