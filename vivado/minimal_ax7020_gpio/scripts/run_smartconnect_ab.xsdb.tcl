connect -url tcp:127.0.0.1:3121
targets -set -filter {name =~ "APU*" && jtag_cable_name =~ "Digilent JTAG-HS1 210512180081"}
loadhw -hw D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/smartconnect_ab/ax7020_gpio_smartconnect_ab.xsa -mem-ranges [list {0x00000000 0x3fffffff} {0x40000000 0xbfffffff}]
configparams force-mem-access 1
targets -set -filter {name =~ "ARM Cortex-A9 MPCore #0" && jtag_cable_name =~ "Digilent JTAG-HS1 210512180081"}
catch {rst -processor}
after 100
source D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/smartconnect_ab/ax7020_smartconnect_ab_ps7_init.tcl
ps7_init
ps7_post_config
puts "SMARTCONNECT_AB_PS7_INITIALIZED"
catch {rst -processor}
after 100
loadhw -hw D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/smartconnect_ab/ax7020_gpio_smartconnect_ab.xsa -mem-ranges [list {0x00000000 0x3fffffff} {0x40000000 0xbfffffff}]
configparams force-mem-access 1
targets -set -filter {name =~ "ARM Cortex-A9 MPCore #0" && jtag_cable_name =~ "Digilent JTAG-HS1 210512180081"}
dow D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/smartconnect_ab/ax7020_smartconnect_ab_fsbl.elf
puts "SMARTCONNECT_AB_FSBL_DOWNLOADED"
con
puts "SMARTCONNECT_AB_FSBL_CONTINUED"
after 5000
catch {stop}
puts "SMARTCONNECT_AB_FSBL_STOPPED"
dow D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/smartconnect_ab/ax7020_xgpio_smartconnect_ab.elf
puts "SMARTCONNECT_AB_XGPIO_ELF_DOWNLOADED"
con
puts "SMARTCONNECT_AB_CPU_CONTINUED"
after 8000
catch {stop}
puts "SMARTCONNECT_AB_CPU_STOPPED"
exit
