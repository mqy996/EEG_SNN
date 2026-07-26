# HLS-5A.4：Vitis standalone 固定向量回放程序

## 目的

`src/main.c` 是给 Zynq PS 裸机环境使用的 UART 回放程序。它不包含 CNN 前端，只回放当前 HLS-5A.1 AXI memory-window wrapper 支持的三个 Q12.6 golden case：

- `threshold_edge`
- `signed_currents`
- `rounding_and_reset`

程序执行顺序为：读取版本 → soft reset → indexed 写入 feature/weight/bias → 校验硬件 XOR checksum → start → 轮询 done → 读回 logits/count → 输出逐向量 PASS/FAIL。

## 文件

- `include/snn_replay_regs.h`：寄存器偏移和控制位。AXI base 优先使用 Vitis 生成的 `XPAR_SNN_AXI_MEMORY_WINDOW_0_BASEADDR`，缺失时仅使用 `0x43C00000` 作为当前地址契约的离线 fallback。
- `include/golden_vectors_q12_6.h`：由 JSON 自动生成的 C 数组，不手工重复抄写 expected 值。
- `include/golden_vectors_manifest.json`：golden JSON SHA-256 和 case 清单。
- `scripts/export_golden_to_c.py`：从 `hls/hybrid_lif_head/golden/vectors_q12_6.json` 生成 header/manifest。
- `src/main.c`：standalone 应用主体。

生成 standalone platform/BSP（不创建 application ELF）：

```powershell
& "D:\vitis\2025.1\Vitis\bin\xsct.bat" `
  vivado/system/vitis/snn_replay_standalone/scripts/create_standalone_platform.tcl `
  vivado/system/artifacts/snn_replay_system.xsa `
  vivado/system/vitis_standalone_build
```

重新生成 header：

```powershell
python vivado/system/vitis/snn_replay_standalone/scripts/export_golden_to_c.py `
  hls/hybrid_lif_head/golden/vectors_q12_6.json `
  vivado/system/vitis/snn_replay_standalone/include/golden_vectors_q12_6.h `
  vivado/system/vitis/snn_replay_standalone/include/golden_vectors_manifest.json
```

## Vitis 构建边界

HLS-5A.3 已使用 **project-mode Vivado flow** 生成带有 PS7 handoff、`ps7_init.*`、`sysdef.xml`、HWH 和 bitstream 的 XSA。稳定交付文件应来自：

```text
vivado/system/snn_system_project_bitstream/snn_replay_system.xsa
vivado/system/snn_system_project_bitstream/snn_replay_system.bit
```

当前会话已经准备好 standalone 源码和 golden header；Vitis application 的正式 ELF 构建需要在可用的 Vitis platform/BSP 上执行。没有开发板时，不把源代码准备、Vitis 编译或 XSA 生成写成板端运行成功。

## 预期 UART 输出

```text
SNN standalone replay start
BASE=0x43c00000 VERSION=0x00010001 JSON_SHA256=<sha256>
VECTOR=threshold_edge PASS checksum=0x........ status=0x00000013
VECTOR=signed_currents PASS checksum=0x........ status=0x00000013
VECTOR=rounding_and_reset PASS checksum=0x........ status=0x00000013
SNN standalone replay PASS cases=3
```

实际板端输出必须另存 UART log，并同时记录 bitstream/XSA、输入 JSON SHA-256、Vitis ELF 和开发板型号；当前没有板端运行证据。
