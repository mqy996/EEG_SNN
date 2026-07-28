# MT41K256M16 鏈€灏?AXI GPIO 瀵圭収宸ョ▼

姝ょ洰褰曟槸褰撳墠 HLS-6B 绯荤粺鐨勯殧绂诲鐓у彉浣擄紝涓嶄慨鏀圭敓浜?bitstream銆丠LS RTL 鎴?`D:\ZYNQ7020_study`銆?
- PS7 DDR锛歚MT41K256M16 RE-125`
- FCLK0锛?0 MHz
- AXI锛歅S M_AXI_GP0 -> SmartConnect -> AXI GPIO
- GPIO 鍦板潃锛歚0x41200000`
- 涓嶅寘鍚?SNN wrapper锛涘彧鐢ㄤ簬鏈€灏?GPIO 鏉跨楠岃瘉銆?
鍒涘缓鑴氭湰锛歚create_mt41k_smartconnect_gpio_minimal.tcl`
鏋勫缓妯″紡锛歏ivado project-mode `project_bitstream`

瀹為獙缁撴灉搴斾笌鍖归厤鐨?`ps7_init.tcl`銆乥itstream銆丟PIO smoke ELF 涓€璧疯褰曪紝涓嶅緱鎶婅鍙樹綋鐨勭粨鏋滅洿鎺ュ綋浣?HLS-6B 鐢熶骇 bitstream 缁撴灉銆
## 单次板端结果（2026-07-28）

变体成功完成 Vivado 综合、实现、DRC、bitstream 和 XSA 生成；HWH 确认
`PCW_UIPARAM_DDR_PARTNO=MT41K256M16 RE-125`，GPIO 地址为 `0x41200000`。

使用该变体匹配的 `ps7_init.tcl` 和现有 GPIO smoke ELF 进行了一次板端测试：

```text
FPGA_PROGRAMMED
ELF_DOWNLOADED=...
CPU_RUN_WINDOW_COMPLETE

AXI_GPIO_TEST_20260727_V1
AXI_GPIO_BASE=0x41200000
```

串口没有出现 `AXI_GPIO_TRI=...`，因此本次最小板端测试仍然阻塞在第一次
`0x41200004` TRI 寄存器读取之前。该结果不能证明 MT41K 变体解决了 AXI
GPIO 访问问题；但它证明 MT41K 变体可以正常生成 bitstream/XSA，且 ELF
能够下载到 CPU。

板端日志和复制后的硬件产物位于：

```text
vivado/system/artifacts/mt41k_gpio_minimal_20260728/
```
