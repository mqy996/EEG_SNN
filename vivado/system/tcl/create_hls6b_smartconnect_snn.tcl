# HLS-6B AX7020 SmartConnect + SNN wrapper integration.
# argv: <repo> <work_dir> <mode>
# mode: bd_only | project_synth | project_bitstream
set repo [file normalize [lindex $argv 0]]
set work_dir [file normalize [lindex $argv 1]]
set mode [lindex $argv 2]
if {$repo eq "" || $work_dir eq "" || $mode eq ""} { error "Usage: create_hls6b_smartconnect_snn.tcl <repo> <work_dir> <mode>" }
set part xc7z020clg400-2
set out_prefix smartconnect_snn_wrapper_50mhz
set bd_name ax7020_ps7_base
set project_dir [file join $work_dir project]
set system_dir [file join $repo vivado system]
set hls_rtl_dir [file join $system_dir hls_rtl board_target_50mhz]
set wrapper_rtl [file join $system_dir src snn_axi_memory_window_hls6a.v]
file mkdir $work_dir

create_project -force hls6b_smartconnect_snn $project_dir -part $part
set_property target_language Verilog [current_project]
set_property default_lib work [current_project]

set hls_files [glob -nocomplain -directory $hls_rtl_dir *.v]
if {[llength $hls_files] == 0} { error "HLS-6A RTL files not found: $hls_rtl_dir" }
if {![file exists $wrapper_rtl]} { error "HLS-6A wrapper not found: $wrapper_rtl" }
add_files -norecurse $hls_files
add_files -norecurse $wrapper_rtl
update_compile_order -fileset sources_1

# Reuse only the read-only PS7 configuration derived from the user's AX7020
# template. It configures xc7z020clg400-2, MT41J256M16 RE-125, UART1 MIO48/49,
# and FCLK0=50 MHz; the template itself is never modified.
source [file join $repo vivado minimal_ax7020_gpio tcl template_ps7_ax7020_reference.tcl]
current_bd_design ax7020_ps7_base
set ps [get_bd_cells processing_system7_0]
if {[llength $ps] != 1} { error "Template-derived PS7 cell was not created" }

set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0]
set axi_defs [get_ipdefs -all xilinx.com:ip:smartconnect:1.0]
if {[llength $axi_defs] == 0} { error "xilinx.com:ip:smartconnect:1.0 is unavailable" }
set axi [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_smc]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {2}] $axi
set gpio [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 axi_gpio_0]
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {0} CONFIG.C_ALL_OUTPUTS {1} CONFIG.C_IS_DUAL {0} CONFIG.C_INTERRUPT_PRESENT {0}] $gpio
set snn [create_bd_cell -type module -reference snn_axi_memory_window_hls6a snn_axi_memory_window_0]
if {[llength $snn] != 1} { error "SNN wrapper module reference was not created" }

connect_bd_intf_net [get_bd_intf_pins $ps/M_AXI_GP0] [get_bd_intf_pins $axi/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $axi/M00_AXI] [get_bd_intf_pins $gpio/S_AXI]
connect_bd_intf_net [get_bd_intf_pins $axi/M01_AXI] [get_bd_intf_pins $snn/S_AXI]
# FCLK_CLK0 is the single 50 MHz PL/AXI clock. The reset controller receives
# the PS active-low FCLK_RESET0_N and fans out peripheral_aresetn.
connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins $axi/aclk] [get_bd_pins $gpio/s_axi_aclk] [get_bd_pins $snn/s_axi_aclk] [get_bd_pins $rst/slowest_sync_clk]
connect_bd_net [get_bd_pins $ps/FCLK_RESET0_N] [get_bd_pins $rst/ext_reset_in]
connect_bd_net [get_bd_pins $rst/peripheral_aresetn] [get_bd_pins $axi/aresetn] [get_bd_pins $gpio/s_axi_aresetn] [get_bd_pins $snn/s_axi_aresetn]

assign_bd_address
set gpio_segs [get_bd_addr_segs -quiet $gpio/S_AXI/*]
set snn_segs [get_bd_addr_segs -quiet $snn/S_AXI/*]
if {[llength $gpio_segs] == 0} { error "AXI GPIO address segment was not inferred" }
if {[llength $snn_segs] == 0} { error "SNN wrapper address segment was not inferred" }
assign_bd_address -offset 0x41200000 -range 0x00010000 [lindex $gpio_segs 0]
assign_bd_address -offset 0x43C00000 -range 0x00010000 [lindex $snn_segs 0]
validate_bd_design
save_bd_design

set bd_file [get_files *ax7020_ps7_base.bd]
if {[llength $bd_file] != 1} { error "Block design file not found" }
generate_target all $bd_file
make_wrapper -files $bd_file -top -import
set wrapper_files [get_files -quiet -of_objects [get_filesets sources_1] *ax7020_ps7_base_wrapper.v]
if {[llength $wrapper_files] == 0} { error "Generated BD wrapper not found" }
set_property top ax7020_ps7_base_wrapper [current_fileset]
update_compile_order -fileset sources_1
report_property [get_bd_cells $ps] > [file join $work_dir ps7_properties.rpt]
report_property [get_bd_cells $axi] > [file join $work_dir smartconnect_properties.rpt]
report_property [get_bd_cells $snn] > [file join $work_dir snn_wrapper_properties.rpt]
report_ip_status -file [file join $work_dir ip_status.rpt]
if {$mode eq "bd_only"} { exit }

# No pin-level XDC is added until the exact AX7020 master XDC is confirmed.
# Therefore this flow is a pre-board implementation artifact, not a board claim.
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
