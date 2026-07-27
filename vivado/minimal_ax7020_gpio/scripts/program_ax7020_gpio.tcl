open_hw_manager
connect_hw_server -allow_non_jtag
set t [lindex [get_hw_targets] 0]
current_hw_target $t
open_hw_target
set d [get_hw_devices xc7z020_1]
set_property PROGRAM.FILE {D:/eeg_fpga/snn_hybrid_eeg/vivado/minimal_ax7020_gpio/artifacts/template_aligned/ax7020_gpio_template_aligned.bit} $d
program_hw_devices $d
refresh_hw_device $d
puts "PROGRAMMED=[get_property PROGRAM.FILE $d]"
exit
