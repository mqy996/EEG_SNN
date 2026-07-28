# HLS-6D existing-bitstream programming helper
# argv: <bitstream>
set bit [file normalize [lindex $argv 0]]
if {![file exists $bit]} { error "Missing bitstream: $bit" }
open_hw_manager
connect_hw_server -url localhost:3121
set target [lindex [get_hw_targets] 0]
open_hw_target $target
set dev [lindex [get_hw_devices -quiet xc7z020_1] 0]
if {$dev eq ""} { error "xc7z020_1 not found" }
puts "HLS6D_PROGRAM_DEVICE=[get_property NAME $dev] PART=[get_property PART $dev]"
set_property PROGRAM.FILE $bit $dev
program_hw_devices $dev
refresh_hw_device $dev
puts "HLS6D_PROGRAM_RESULT=PASS"
close_hw_target
 disconnect_hw_server
close_hw_manager
exit
