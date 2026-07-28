# HLS-6C Vitis standalone / AXI-Lite board replay report

**当前结果：Vitis platform/domain、ELF 和 bitstream 下载通过；首个 AXI-Lite VERSION 读取在板端阻塞。**

日期：2026-07-28
工具：Vitis 2025.1，SW Build 6137779
范围：HLS-6B SmartConnect SNN wrapper，不修改 HLS-6B 硬件产物。

## 1. 证据等级

| 等级 | 结果 | 证据 |
|---|---|---|
| HLS-6B XSA/bitstream/HWH | AVAILABLE | `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/` |
| Vitis platform/domain | **PASS** | `D:/v6c_hls6c_20260728/p6c/export/.buildstatus` 为 `export=SUCCESS`，存在 `p6c.xpfm` |
| standalone application / ELF | **PASS** | `D:/v6c_hls6c_20260728/a6c/build/.buildstatus` 为 `hw=SUCCESS`，存在 `a6c.elf` |
| bitstream 下载 | **PASS** | Vivado Hardware Manager `PROGRAM_RESULT=PASS` |
| UART smoke / AXI 首次事务 | **BLOCKED** | UART 到达 `VERSION_BEGIN`，未返回 VERSION |
| 三组板端 replay | NOT ATTEMPTED | 首次 AXI 事务停止门，当前不宣称 board PASS |

只有 platform 状态文件、真实 XPFM 和真实 ELF 同时存在，才把软件构建标记为 PASS；Vitis 进程退出码不单独作为证据。

## 2. 输入硬件身份

| Artifact | SHA-256 |
|---|---|
| HLS-6B XSA | `373543b2a9a283339f3d48bcd20cb38cc299a0f416faae84ba3b0dcc303ba98b` |
| HLS-6B bitstream | `d5e90c144c02dddf4af94ec85208dfd285b2f672ee13bb18ca7c18b4950bab8d` |
| HLS-6B HWH | `8c5f1d0c93dc8141e1d985c8f4d42f6dc5bda2ab69d871b31ff3d3566b9c521d` |

注意：XSA 正确 SHA-256 为：

```text
373543b2a9a283339f3d48bcd20cb38cc299a0f416faae84ba3b0dcc303ba98b
```

bitstream 和 HWH 正确 SHA-256 为：

```text
d5e90c144c02dddf4af94ec85208dfd285b2f672ee13bb18ca7c18b4950bab8d
8c5f1d0c93dc8141e1d985c8f4d42f6dc5bda2ab69d871b31ff3d3566b9c521d
```

Golden manifest SHA-256：

```text
8f73683b4448f8315af76151e36dacff494197c0caf8bcf2e8ace01ad301604a
```

## 3. 创建流程修正

本次成功流程相对于之前失败流程做了三项关键修正：

1. 删除 standalone platform/domain 创建中的 `generate_dtb=True`；
2. 使用短路径和短名称：
   ```text
   Workspace: D:\v6c_hls6c_20260728
   Platform:  p6c
   App:       a6c
   ```
3. 启动 Vitis 前显式加载：
   ```text
   D:\vitis\2025.1\Vivado\.settings64-Vivado.bat
   D:\vitis\2025.1\Vitis\.settings64-Vitis.bat
   ```

同时，platform 构建后使用 `client.find_platform_in_repos()` 获取 platform 引用，再创建应用。

## 4. 成功构建结果

```text
PLATFORM_BUILD_RETURN=0
export=SUCCESS
PLATFORM_XPFM=D:\v6c_hls6c_20260728\p6c\export\p6c\p6c.xpfm
APP_BUILD_RETURN=0
hw=SUCCESS
ELF=D:\v6c_hls6c_20260728\a6c\build\a6c.elf
```

Curated artifacts：

```text
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6c_vitis_standalone/p6c.xpfm
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6c_vitis_standalone/a6c.elf
vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/hls6c_vitis_standalone/fsbl.elf
```

文件 SHA-256：

```text
p6c.xpfm  44E06148A523700FD6B88619EF59CA3E4324FEBA0D240ECA9A7086AAB434E3E7
a6c.elf   834EC82E9F30FE45232089E0528E84995551B769DF8D8D7FC334CDF4DCB8BD2B
fsbl.elf  24778243FF6CDB7DEC0B2A2B50CE5EE2AA7F6E854B93EC4F1ABBAE4221355DA4
```

## 5. 对之前失败的解释

之前两个长路径 workspace 的结果仍然保留：

```text
export=ERROR
```

其日志出现 CMake 编译器识别依赖文件缺失和 `CMAKE_OBJECT_PATH_MAX` 路径警告。它们不是 XSA 硬件设计失败，而是 Vitis standalone 创建参数和 Windows 构建路径组合导致的 platform/BSP 构建失败。

成功的短路径流程说明：

- `write_hw_platform -fixed` 不是问题；
- `xc7z020clg400-2` 不是问题；
- SmartConnect/AXI 地址不是问题；
- standalone platform 创建、BSP、FSBL 和应用 ELF 均可成功生成。

## 6. 板端最小回放结果（2026-07-28）

### 下载与 CPU 入口

- 目标：`xc7z020_1` / `xc7z020`
- bitstream：`smartconnect_snn_wrapper_50mhz.bit`
- Vivado Hardware Manager：`PROGRAM_RESULT=PASS`
- XSCT：`FPGA_PROGRAMMED`、`ELF_DOWNLOADED=.../a6c.elf`、`CPU_RUN_WINDOW_COMPLETE`
- UART：COM5，115200 8-N-1

### UART 原始关键输出

```text
SNN standalone replay start
AXI_PROBE=VERSION_BEGIN base=0x43C00000
```

在 `VERSION_BEGIN` 之后没有收到 `BASE=... VERSION=...` 或 `VERSION_PASS`。XSCT 返回码为 0，但这只能证明 FPGA/ELF 下载流程完成，不能证明 AXI-Lite 事务完成。

### 结论

```text
bitstream download PASS
  -> ELF download PASS
  -> CPU enters main PASS
  -> first SNN wrapper AXI-Lite read at 0x43C00000 BLOCKED
```

因此没有继续写入 feature/weight/bias，也没有执行 START、DONE、logits/counts 或三组 golden replay。HLS-6B XSim 和 Vivado implementation 结果保持有效，但尚不能宣称板端 SNN wrapper PASS。

剩余问题已经从 Vitis platform/ELF 创建阶段推进到板端 PS7 GP0 → SmartConnect → SNN wrapper 的首次 AXI-Lite 访问。AXI GPIO SmartConnect 对照实验曾经通过，因此下一步应做针对 SNN wrapper 分支的最小硬件诊断，不应继续重复完整 vector 回放。

## 7. 证据文件

- `vivado/system/reports/HLS6C_SHORT_PLATFORM_BUILD.log`
- `vivado/system/reports/HLS6C_BITSTREAM_PROGRAM.log`
- `vivado/system/reports/HLS6C_BOARD_REPLAY.log`
- `vivado/system/reports/HLS6C_VITIS_PLATFORM_BUILD_EVIDENCE.txt`
- `vivado/system/reports/HLS6C_VITIS_BOARD_REPLAY.md`
