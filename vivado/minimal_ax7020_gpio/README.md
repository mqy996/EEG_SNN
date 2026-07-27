# AX7020模板对齐最小AXI GPIO验证

本目录是基于现有 `snn_hybrid_eeg` 工程建立的独立验证切片，不覆盖 `vivado/system`，也不修改 AX7020 参考模板。

## 目标

验证：

```text
PS7 M_AXI_GP0 -> AXI Interconnect -> AXI GPIO
```

参考模板：

```text
D:\ZYNQ7020_study\ZYNQ_project\project_AX7020_template
```

## 重要配置

最终使用模板生成的 PS7 配置：

- FPGA part：`xc7z020clg400-2`；
- DDR：`MT41J256M16 RE-125`；
- IO PLL：1000 MHz；
- FCLK0：50 MHz，divisor 5；
- UART1：MIO48/49，LVCMOS 1.8 V；
- M_AXI_GP0：启用；
- AXI GPIO：`0x41200000`。

复位必须直接连接：

```text
FCLK_RESET0_N -> proc_sys_reset/ext_reset_in
```

两者都是低有效，不要增加反相器。

## 可复现生成

由于 Windows 路径长度限制，建议使用短的临时构建目录：

```powershell
& 'D:\Vitis\2025.1\Vivado\bin\vivado.bat' `
  -mode batch `
  -source 'D:\eeg_fpga\snn_hybrid_eeg\vivado\minimal_ax7020_gpio\tcl\create_ax7020_gpio_from_template_ps7.tcl' `
  -tclargs 'D:\eeg_fpga\snn_hybrid_eeg' 'D:\a7gpio_build' project_bitstream
```

主脚本：

```text
vivado/minimal_ax7020_gpio/tcl/create_ax7020_gpio_from_template_ps7.tcl
```

模板派生的 PS7 配置脚本：

```text
vivado/minimal_ax7020_gpio/tcl/template_ps7_ax7020_reference.tcl
```

## Vitis

GPIO 测试源码：

```text
vivado/minimal_ax7020_gpio/vitis/src/main.c
vivado/minimal_ax7020_gpio/vitis/src/main_data_first.c
vivado/minimal_ax7020_gpio/vitis/src/main_data_read_first.c
```

Vitis 生成脚本：

```text
vivado/minimal_ax7020_gpio/scripts/create_vitis_gpio_smoke.py
```

## 结果

完整结论见：

```text
vivado/minimal_ax7020_gpio/reports/AX7020_MINIMAL_GPIO_RESULTS.md
```

当前已完成模板对齐、bitstream/XSA/ELF生成和板端启动验证；启动后的第一个 AXI 事务仍然阻塞，不能宣称AXI数据通路已完全通过。
