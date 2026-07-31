# Rebuild the successful SNN replay system with the authoritative AX7020 configuration.
# Vivado 2025.1, xc7z020clg400-2, MT41J256M16 RE-125, FCLK0=50 MHz.
# argv: <repo> <work_dir> <mode>; mode=project_bitstream or bd_only
set repo [file normalize [lindex $argv 0]]
set work_dir [file normalize [lindex $argv 1]]
set mode [lindex $argv 2]
if {$repo eq "" || $work_dir eq "" || $mode eq ""} { error "Usage: create_evidence_system.tcl <repo> <work_dir> <mode>" }
set part xc7z020clg400-2
set bd_name ax7020_ps7_base
set system_dir [file join $repo vivado system]
set hls_rtl_dir [file join $system_dir hls_rtl board_target_50mhz]
set wrapper_rtl [file join $system_dir src snn_axi_memory_window.v]
set template_tcl [file join $repo vivado minimal_ax7020_gpio tcl template_ps7_ax7020_reference.tcl]
set project_dir [file join $work_dir project]
set artifact_dir [file join $work_dir artifacts]
file mkdir $work_dir
file mkdir $artifact_dir
if {[version -short] ni {2025.1 2025.1.0}} { error "Expected Vivado 2025.1, got [version -short]" }
if {![file exists $template_tcl]} { error "Missing read-only PS7 template: $template_tcl" }
if {![file exists $wrapper_rtl]} { error "Missing AXI wrapper: $wrapper_rtl" }
set hls_files [glob -nocomplain -directory $hls_rtl_dir *.v]
if {[llength $hls_files] == 0} { error "No HLS RTL files: $hls_rtl_dir" }

create_project -force snn_evidence_system $project_dir -part $part
set_property target_language Verilog [current_project]
set_property default_lib work [current_project]
add_files -norecurse $hls_files
add_files -norecurse $wrapper_rtl
update_compile_order -fileset sources_1

# The template is read-only and is the source of the authoritative PS7/DDR/UART setup.
source $template_tcl
current_bd_design $bd_name
set ps [get_bd_cells processing_system7_0]
if {[llength $ps] != 1} { error "PS7 cell missing after template import" }
set ps_part [get_property CONFIG.PCW_UIPARAM_DDR_PARTNO $ps]
set ps_fclk [get_property CONFIG.PCW_CLK0_FREQ $ps]
set ps_uart [get_property CONFIG.PCW_UART1_UART1_IO $ps]
if {$ps_part ne "MT41J256M16 RE-125"} { error "Unexpected DDR part: $ps_part" }
if {$ps_fclk ne "50000000"} { error "Unexpected FCLK0: $ps_fclk" }
if {$ps_uart ne "MIO 48 .. 49"} { error "Unexpected UART1 IO: $ps_uart" }

set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0]
set defs [get_ipdefs -all xilinx.com:ip:smartconnect:1.0]
if {[llength $defs] == 0} { error "SmartConnect 1.0 IP definition unavailable" }
set axi [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_interconnect_0]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $axi
set snn [create_bd_cell -type module -reference snn_axi_memory_window snn_axi_memory_window_0]
if {[llength $snn] != 1} { error "SNN AXI wrapper module reference unavailable" }

connect_bd_intf_net [get_bd_intf_pins $ps/M_AXI_GP0] [get_bd_intf_pins $axi/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $axi/M00_AXI] [get_bd_intf_pins $snn/S_AXI]
connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins $ps/M_AXI_GP0_ACLK] [get_bd_pins $axi/aclk] [get_bd_pins $axi/S00_ACLK] [get_bd_pins $axi/M00_ACLK] [get_bd_pins $snn/s_axi_aclk] [get_bd_pins $rst/slowest_sync_clk]
connect_bd_net [get_bd_pins $ps/FCLK_RESET0_N] [get_bd_pins $rst/ext_reset_in]
connect_bd_net [get_bd_pins $rst/peripheral_aresetn] [get_bd_pins $axi/aresetn] [get_bd_pins $axi/S00_ARESETN] [get_bd_pins $axi/M00_ARESETN] [get_bd_pins $snn/s_axi_aresetn]
assign_bd_address
set snn_segs [get_bd_addr_segs -quiet $snn/S_AXI/*]
if {[llength $snn_segs] == 0} { error "SNN AXI address segment was not inferred" }
assign_bd_address -offset 0x43C00000 -range 0x00010000 [lindex $snn_segs 0]
validate_bd_design
save_bd_design
set bd_file [get_files *$bd_name.bd]
generate_target all $bd_file
make_wrapper -files $bd_file -top -import
set wrapper_files [get_files -quiet -of_objects [get_filesets sources_1] *${bd_name}_wrapper.v]
if {[llength $wrapper_files] == 0} { error "Generated BD wrapper missing" }
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1
report_ip_status -file [file join $artifact_dir ip_status.rpt]
report_property $ps > [file join $artifact_dir ps7_properties.rpt]
if {$mode eq "bd_only"} { exit }

launch_runs synth_1 -jobs 4
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "SYNTH_STATUS=$synth_status"
if {![string match *Complete* $synth_status]} { error "synth failed: $synth_status" }
open_run synth_1
report_utilization -file [file join $artifact_dir utilization_synth.rpt]
report_timing_summary -file [file join $artifact_dir timing_synth.rpt]
close_design
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "IMPL_STATUS=$impl_status"
if {![string match *Complete* $impl_status]} { error "implementation failed: $impl_status" }
open_run impl_1
write_bitstream -force [file join $artifact_dir snn_evidence_system.bit]
write_hw_platform -fixed -include_bit -force -file [file join $artifact_dir snn_evidence_system.xsa]
report_utilization -hierarchical -file [file join $artifact_dir utilization_impl_hierarchical.rpt]
report_timing_summary -file [file join $artifact_dir timing_impl.rpt]
report_power -file [file join $artifact_dir power_impl.rpt]
report_drc -file [file join $artifact_dir drc_impl.rpt]
report_route_status -file [file join $artifact_dir route_status_impl.rpt]
write_checkpoint -force [file join $artifact_dir post_route.dcp]
puts "EVIDENCE_VIVADO_RESULT=PASS"
exit
