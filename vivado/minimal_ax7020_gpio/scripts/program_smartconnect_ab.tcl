open_hw_manager
connect_hw_server -url localhost:3121
set t [lindex [get_hw_targets] 0]
current_hw_target $t
open_hw_target
set d [get_hw_devices xc7z020_1]
if {[llength $d] != 1} { error "Expected one xc7z020_1, got $d" }
set_property PROGRAM.FILE {D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/smartconnect_ab/ax7020_gpio_smartconnect_ab.bit} $d
program_hw_devices $d
refresh_hw_device $d
puts "SMARTCONNECT_AB_PROGRAMMED=[get_property PROGRAM.FILE $d]"
close_hw_target
close_hw_manager
exit
