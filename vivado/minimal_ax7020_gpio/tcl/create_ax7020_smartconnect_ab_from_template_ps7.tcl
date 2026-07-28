# AX7020 SmartConnect A/B GPIO system using a generated PS7 configuration script
# derived read-only from project_AX7020_template.
# argv: <repo> <work_dir> <mode>
# mode: bd_only | project_synth | project_bitstream
set repo [file normalize [lindex $argv 0]]
set work_dir [file normalize [lindex $argv 1]]
set mode [lindex $argv 2]
if {$repo eq "" || $work_dir eq "" || $mode eq ""} { error "Usage: create_ax7020_gpio_from_template_ps7.tcl <repo> <work_dir> <mode>" }
set part xc7z020clg400-2
set out_prefix smartconnect_ab
set bd_name ax7020_ps7_base
set project_dir [file join $work_dir project]
file mkdir $work_dir
create_project -force smartconnect_ab $project_dir -part $part
set_property target_language Verilog [current_project]
set_property default_lib work [current_project]

# This Tcl was generated from the read-only AX7020 template BD and then
# patched only for a new design name/non-remote flow. It creates PS7 only.
source [file join $repo vivado minimal_ax7020_gpio tcl template_ps7_ax7020_reference.tcl]
current_bd_design $bd_name
set ps [get_bd_cells processing_system7_0]
if {[llength $ps] != 1} { error "Template-derived PS7 cell was not created" }

set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0]
set axi_defs [get_ipdefs -all xilinx.com:ip:smartconnect:1.0]
if {[llength $axi_defs] == 0} { error "xilinx.com:ip:smartconnect:1.0 is unavailable" }
set axi [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_smc]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $axi
set gpio [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 axi_gpio_0]
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {0} CONFIG.C_ALL_OUTPUTS {1} CONFIG.C_IS_DUAL {0} CONFIG.C_INTERRUPT_PRESENT {0}] $gpio

connect_bd_intf_net [get_bd_intf_pins $ps/M_AXI_GP0] [get_bd_intf_pins $axi/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $axi/M00_AXI] [get_bd_intf_pins $gpio/S_AXI]
# The template-derived PS7 script already connects FCLK_CLK0 to M_AXI_GP0_ACLK.
connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins $axi/aclk] [get_bd_pins $gpio/s_axi_aclk] [get_bd_pins $rst/slowest_sync_clk]
connect_bd_net [get_bd_pins $ps/FCLK_RESET0_N] [get_bd_pins $rst/ext_reset_in]
connect_bd_net [get_bd_pins $rst/peripheral_aresetn] [get_bd_pins $axi/aresetn] [get_bd_pins $gpio/s_axi_aresetn]
assign_bd_address
set gpio_segs [get_bd_addr_segs -quiet $gpio/S_AXI/*]
if {[llength $gpio_segs] == 0} { error "AXI GPIO address segment was not inferred" }
assign_bd_address -offset 0x41200000 -range 0x00010000 [lindex $gpio_segs 0]
validate_bd_design
save_bd_design
set bd_file [get_files *${bd_name}.bd]
generate_target all $bd_file
make_wrapper -files $bd_file -top -import
set wrapper_files [get_files -quiet -of_objects [get_filesets sources_1] *${bd_name}_wrapper.v]
if {[llength $wrapper_files] == 0} { error "Generated BD wrapper not found" }
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1
report_property [get_bd_cells $ps] > [file join $work_dir ps7_properties.rpt]
report_property [get_bd_cells $axi] > [file join $work_dir smartconnect_properties.rpt]
report_property [get_bd_cells $gpio] > [file join $work_dir axi_gpio_properties.rpt]
if {$mode eq "bd_only"} { exit }
# No PYNQ-Z2 XDC is used here: the reference project has an empty user
# constraint set and the exact AX7020 master XDC is not yet confirmed.
# Keep synthesis independent of a potentially wrong board pinout.
launch_runs synth_1 -jobs 4
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "SYNTH_STATUS=$synth_status"
if {![string match *Complete* $synth_status]} { error "synth failed: $synth_status" }
open_run synth_1
report_utilization -file [file join $work_dir utilization_synth.rpt]
report_timing_summary -file [file join $work_dir timing_synth.rpt]
if {$mode eq "project_synth"} { exit }
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "IMPL_STATUS=$impl_status"
if {![string match *Complete* $impl_status]} { error "implementation failed: $impl_status" }
open_run impl_1
write_bitstream -force [file join $work_dir ${out_prefix}.bit]
write_hw_platform -fixed -include_bit -force -file [file join $work_dir ${out_prefix}.xsa]
report_utilization -file [file join $work_dir utilization_impl.rpt]
report_timing_summary -file [file join $work_dir timing_impl.rpt]
report_drc -file [file join $work_dir drc_impl.rpt]
exit
