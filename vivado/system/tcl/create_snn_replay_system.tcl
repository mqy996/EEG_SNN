# Rebuildable Zynq-7020 PS/PL system for the SNN AXI-Lite replay wrapper.
# argv: <repo> <work_dir> <mode>
# mode=bd_only | candidate_impl | candidate_bitstream
set repo [file normalize [lindex $argv 0]]
set work_dir [file normalize [lindex $argv 1]]
set mode [lindex $argv 2]
if {$repo eq "" || $work_dir eq "" || $mode eq ""} { error "Usage: create_snn_replay_system.tcl <repo> <work_dir> <mode>" }
set part xc7z020clg400-1
set system_dir [file join $repo vivado system]
set hls_rtl [file join $repo hls hybrid_lif_head hls impl verilog]
set wrapper_rtl [file join $system_dir src snn_axi_memory_window.v]
set bd_name snn_replay_system
file mkdir $work_dir
create_project -force snn_replay_system [file join $work_dir project] -part $part
set_property target_language Verilog [current_project]
set_property default_lib work [current_project]
if {![file exists $wrapper_rtl]} { error "Missing wrapper RTL: $wrapper_rtl" }
if {![file isdirectory $hls_rtl]} { error "Missing HLS RTL directory: $hls_rtl. Run HLS implementation first." }
add_files -norecurse $wrapper_rtl
set hls_files [glob -nocomplain -directory $hls_rtl *.v]
if {[llength $hls_files] == 0} { error "No HLS generated Verilog found in $hls_rtl" }
add_files -norecurse $hls_files
update_compile_order -fileset sources_1
create_bd_design $bd_name
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0]
# Historical CNN-LSTM BD and project documentation agree on Zynq-7020,
# The connected board exposes its USB-UART through PS UART1 on MIO 48/49, and FCLK_CLK0=50 MHz. SmartConnect bridges the PS GP0 master to the AXI-Lite wrapper. The exact board preset is
# not inferred from the old project because its BoardPart is empty.
set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_USE_S_AXI_HP0 {0} CONFIG.PCW_USE_S_AXI_HP1 {0} CONFIG.PCW_USE_S_AXI_HP2 {0} CONFIG.PCW_USE_S_AXI_HP3 {0} \
    CONFIG.PCW_FPGA_FCLK0_ENABLE {1} CONFIG.PCW_CLK0_FREQ {50000000} CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ {50.000000} \
    CONFIG.PCW_EN_UART1 {1} \
    CONFIG.PCW_UART1_PERIPHERAL_ENABLE {1} CONFIG.PCW_UART1_UART1_IO {MIO 48 .. 49} \
    CONFIG.PCW_MIO_48_IOTYPE {LVCMOS 1.8V} CONFIG.PCW_MIO_49_IOTYPE {LVCMOS 1.8V} \
    CONFIG.PCW_MIO_48_PULLUP {enabled} CONFIG.PCW_MIO_49_PULLUP {enabled} \
    CONFIG.PCW_MIO_48_SLEW {slow} CONFIG.PCW_MIO_49_SLEW {slow} \
    CONFIG.PCW_UIPARAM_DDR_PARTNO {MT41K256M16 RE-125} \
] $ps
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 -config {make_external "FIXED_IO, DDR"} $ps
update_compile_order -fileset sources_1
set axi [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_interconnect_0]
set_property CONFIG.NUM_SI {1} $axi
set_property CONFIG.NUM_MI {1} $axi
set snn [create_bd_cell -type module -reference snn_axi_memory_window snn_axi_memory_window_0]
connect_bd_intf_net [get_bd_intf_pins $ps/M_AXI_GP0] [get_bd_intf_pins $axi/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $axi/M00_AXI] [get_bd_intf_pins $snn/S_AXI]
connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins $ps/M_AXI_GP0_ACLK]
connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins $axi/ACLK] [get_bd_pins $axi/S00_ACLK] [get_bd_pins $axi/M00_ACLK] [get_bd_pins $snn/s_axi_aclk]
connect_bd_net [get_bd_pins $ps/FCLK_RESET0_N] [get_bd_pins $axi/ARESETN] [get_bd_pins $axi/S00_ARESETN] [get_bd_pins $axi/M00_ARESETN] [get_bd_pins $snn/s_axi_aresetn]
assign_bd_address
set segs [get_bd_addr_segs -quiet $snn/S_AXI/*]
if {[llength $segs] == 0} { error "SNN AXI address segment was not inferred" }
assign_bd_address -offset 0x43C00000 -range 0x00010000 [lindex $segs 0]
validate_bd_design
save_bd_design
set bd_file [get_files *$bd_name.bd]
generate_target all $bd_file
make_wrapper -files $bd_file -top -import
set wrapper_files [get_files -quiet -of_objects [get_filesets sources_1] *${bd_name}_wrapper.v]
if {[llength $wrapper_files] == 0} {
    set wrapper_candidates [glob -nocomplain -directory [file join $work_dir project ${bd_name}.gen sources_1 bd $bd_name hdl] *${bd_name}_wrapper.v]
    if {[llength $wrapper_candidates] == 0} { error "Generated BD wrapper was not found" }
    add_files -norecurse [lindex $wrapper_candidates 0]
}
if {[llength $wrapper_files] == 0} {
    set wrapper_files [get_files -quiet *${bd_name}_wrapper.v]
}
if {[llength $wrapper_files] == 0} { error "BD wrapper file is not in the project" }
set wrapper_file [lindex $wrapper_files 0]
update_compile_order -fileset sources_1
set_property top ${bd_name}_wrapper [current_fileset]
if {$mode eq "bd_only"} {
    report_ip_status -file [file join $work_dir ip_status.rpt]
    report_property [get_bd_cells $ps] > [file join $work_dir ps7_properties.rpt]
    exit
}
set wrapper_candidates [glob -nocomplain -directory [file join $work_dir project ${bd_name}.gen sources_1 bd $bd_name hdl] *${bd_name}_wrapper.v]
if {[llength $wrapper_candidates] == 0} { error "Generated BD wrapper was not found" }
set wrapper_file [lindex $wrapper_candidates 0]
set xdc [file join $system_dir constraints PYNQ-Z2_v1.0.xdc]
# Project-mode implementation is the authoritative path for deliverable
# bitstream/XSA generation. It preserves BD/IP handoff metadata that an
# in-memory implementation cannot package into a Vitis-ready XSA.
if {$mode eq "project_impl" || $mode eq "project_bitstream"} {
    if {[file exists $xdc]} { add_files -fileset constrs_1 -norecurse $xdc }
    set_property top ${bd_name}_wrapper [current_fileset]
    update_compile_order -fileset sources_1
    launch_runs synth_1 -jobs 4
    wait_on_run synth_1
    set synth_status [get_property STATUS [get_runs synth_1]]
    puts "SYNTH_STATUS=$synth_status"
    if {![string match *Complete* $synth_status]} { error "synth failed: $synth_status" }
    if {$mode eq "project_bitstream"} {
        launch_runs impl_1 -to_step write_bitstream -jobs 4
        wait_on_run impl_1
        set impl_status [get_property STATUS [get_runs impl_1]]
        puts "IMPL_STATUS=$impl_status"
        if {![string match *Complete* $impl_status]} { error "impl failed: $impl_status" }
        open_run impl_1
        write_bitstream -force [file join $work_dir snn_replay_system.bit]
        write_hw_platform -fixed -include_bit -force -file [file join $work_dir snn_replay_system.xsa]
        report_timing_summary -file [file join $work_dir timing_project.rpt]
        report_utilization -file [file join $work_dir utilization_project.rpt]
    } else {
        open_run synth_1
        report_timing_summary -file [file join $work_dir timing_project.rpt]
        report_utilization -file [file join $work_dir utilization_project.rpt]
    }
    exit
}
# Use a clean in-memory synthesis project so generated BD sources are not
# duplicated or hidden by the project fileset's AutoDisabled markers.
close_project
create_project -in_memory -part $part
proc find_verilog {dir} {
    set result {}
    foreach item [glob -nocomplain -directory $dir *] {
        if {[file isdirectory $item]} {
            set result [concat $result [find_verilog $item]]
        } elseif {([string match *.v $item] || [string match *.sv $item] || ([string match *.vhd $item] && (![string match */ipshared/* $item] || [string match *proc_sys_reset_v5_0_vh_rfs.vhd $item]))) && ![string match */sim/* $item] && ![string match *_vip* $item]} {
            lappend result $item
        }
    }
    return $result
}
set generated_bd_rtl [find_verilog [file join $work_dir project ${bd_name}.gen sources_1 bd $bd_name]]
set include_dirs {}
foreach item $generated_bd_rtl { lappend include_dirs [file dirname $item] }
set_property include_dirs [lsort -unique $include_dirs] [current_fileset]
read_verilog -sv $hls_files
read_verilog -sv $wrapper_rtl
foreach item $generated_bd_rtl {
    if {[string match *.vhd $item]} { read_vhdl $item } else { read_verilog -sv $item }
}
read_verilog -sv $wrapper_file
if {[file exists $xdc]} { read_xdc $xdc }
set_property SEVERITY Warning [get_drc_checks UCIO-1 -quiet]
set_property SEVERITY Warning [get_drc_checks NSTD-1 -quiet]
synth_design -top ${bd_name}_wrapper -part $part
write_checkpoint -force [file join $work_dir post_synth.dcp]
report_utilization -file [file join $work_dir utilization_synth.rpt]
report_timing_summary -file [file join $work_dir timing_synth.rpt]
if {$mode eq "candidate_impl" || $mode eq "candidate_bitstream"} {
    opt_design
    place_design
    route_design
    write_checkpoint -force [file join $work_dir post_route.dcp]
    report_utilization -file [file join $work_dir utilization_impl.rpt]
    report_timing_summary -file [file join $work_dir timing_impl.rpt]
    report_drc -file [file join $work_dir drc_impl.rpt]
}
if {$mode eq "candidate_bitstream"} {
    write_bitstream -force [file join $work_dir snn_replay_system.bit]
    write_hw_platform -fixed -force -file [file join $work_dir snn_replay_system.xsa]
}
exit

