# SNN-4 定点数与 FPGA 可行性

状态：**软件可行性门槛通过；下一步进行 HLS 验证**。

当前契约为 Channel8 + GroupNorm、direct-current（直流编码）和 Hybrid LIF 读出头，目标器件 `xc7z020clg400-1`，时钟暂按 100 MHz 规划。Q12.6 在 fold-2 预研中达到 99.24% 浮点/定点预测一致率，脉冲率漂移为 0.03 个百分点，因此作为第一版 HLS 候选。Q8.4 低于 99% 一致率，Q16.8 作为高精度参考。

这是读出头级别的软件预研，不包含板卡、HLS csim、Vivado 资源/时序或功耗结论。详细结果见 `RESULTS.md`。
