> 状态说明：该文档记录的是开发板连接前的阶段性结果。2026-07-27 已完成开发板连接、下载和 UART smoke test，但 AXI-Lite 板端回放仍在调试，最新结论见 [`HLS5B_BOARD_RESULTS.md`](HLS5B_BOARD_RESULTS.md)。

# HLS-5A.4：Vitis standalone 回放程序结果

## 已完成

- `vitis/snn_replay_standalone/src/main.c`：完成版本检查、soft reset、三组 vector 的 indexed 写入、硬件 XOR checksum 校验、start/done 轮询、logit/count 读回和 UART PASS/FAIL 输出。
- `vitis/snn_replay_standalone/include/snn_replay_regs.h`：寄存器和控制位集中定义；优先使用 Vitis 的 `XPAR_SNN_AXI_MEMORY_WINDOW_0_BASEADDR`。
- `vitis/snn_replay_standalone/scripts/export_golden_to_c.py`：从版本化 `vectors_q12_6.json` 自动生成 C header 和 SHA-256 manifest。
- `include/golden_vectors_q12_6.h`：三组 golden case 的 feature、weight、bias 和 expected logits/count。

## 编译检查

- 已用由 HLS-5A.3 XSA 生成的 standalone BSP 头文件执行 ARM Cortex-A9 GCC syntax-only 检查，`main.c` 通过。
- 已用 XSCT 2025.1 创建 standalone platform 并生成 BSP/FSBL，说明 XSA 的 PS handoff 可被 Vitis/XSCT 读取。
- 由于 XSCT 2025.1 的旧 XSCT application workspace 注册流程在本机对新建 platform 返回 `No platforms available in repository`，本次没有把一个未生成的 ELF 伪称为完成。保留日志于本地构建目录，不提交生成目录。

## 结论边界

当前状态为：**standalone 源码和 golden 数据契约完成；C 语法级通过；Vitis platform/BSP 已可生成；正式 application ELF 和板端 UART 回放仍待下一步 Vitis GUI/Python flow 或连接开发板后完成。**

没有开发板时，不能把 `main.c` 编译检查、XSA 生成或 bitstream 生成写成板端 PASS。

## 后续最短路径

1. 用 Vitis GUI 或 `vitis -s` 新 Python flow 导入 `artifacts/snn_replay_system.xsa`，创建 `ps7_cortexa9_0/standalone` application。
2. 把 `src/main.c` 和 `include/` 加入 application，生成 ELF。
3. 连接开发板后下载 `artifacts/snn_replay_system.bit`，运行 ELF，保存 UART log。
4. 用三组 golden expected 逐项核对 logits/count，形成板端证据。
