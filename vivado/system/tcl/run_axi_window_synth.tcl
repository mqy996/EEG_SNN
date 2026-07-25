# Out-of-context synthesis for the AXI-Lite memory-window wrapper.
# argv: <hls_rtl_dir> <out_dir>
set hls_rtl_dir [lindex $argv 0]
set out_dir [lindex $argv 1]
if {$hls_rtl_dir eq "" || $out_dir eq ""} { error "Usage: vivado -mode batch -source run_axi_window_synth.tcl -tclargs <hls_rtl_dir> <out_dir>" }
file mkdir $out_dir
set script_dir [file dirname [info script]]
set wrapper [file normalize [file join $script_dir .. src snn_axi_memory_window.v]]
set xdc [file normalize [file join $script_dir .. constraints system_50mhz.xdc]]
set generated [glob -nocomplain -directory [file normalize $hls_rtl_dir] *.v]
if {[llength $generated] == 0} { error "No generated HLS Verilog found in $hls_rtl_dir" }
read_verilog -sv [concat $generated [list $wrapper]]
read_xdc $xdc
synth_design -top snn_axi_memory_window -part xc7z020clg400-1 -mode out_of_context
write_checkpoint -force [file join $out_dir post_synth.dcp]
report_utilization -file [file join $out_dir utilization_synth.rpt]
report_timing_summary -file [file join $out_dir timing_synth.rpt]
report_drc -file [file join $out_dir drc_synth.rpt]
puts "SNN AXI memory-window wrapper synthesis PASS"
exit
