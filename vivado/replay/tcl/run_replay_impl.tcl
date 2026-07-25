# Non-project Vivado flow for the SNN fixed-vector replay wrapper.
# argv: <hls_rtl_dir> <out_dir>
set hls_rtl_dir [lindex $argv 0]
set out_dir [lindex $argv 1]
if {$hls_rtl_dir eq "" || $out_dir eq ""} { error "Usage: vivado -mode batch -source run_replay_impl.tcl -tclargs <hls_rtl_dir> <out_dir>" }
file mkdir $out_dir
set wrapper [file normalize [file join [file dirname [info script]] .. src hls_replay_wrapper.v]]
set xdc [file normalize [file join [file dirname [info script]] .. constraints replay_50mhz.xdc]]
set generated [glob -nocomplain -directory [file normalize $hls_rtl_dir] *.v]
if {[llength $generated] == 0} { error "No generated HLS Verilog found in $hls_rtl_dir" }
read_verilog -sv [concat $generated [list $wrapper]]
read_xdc $xdc
synth_design -top hls_replay_wrapper -part xc7z020clg400-1
write_checkpoint -force [file join $out_dir post_synth.dcp]
report_utilization -file [file join $out_dir utilization_synth.rpt]
report_timing_summary -file [file join $out_dir timing_synth.rpt]
opt_design
place_design
route_design
write_checkpoint -force [file join $out_dir post_route.dcp]
report_utilization -file [file join $out_dir utilization_impl.rpt]
report_timing_summary -file [file join $out_dir timing_impl.rpt]
report_drc -file [file join $out_dir drc_impl.rpt]
puts "SNN replay wrapper 50 MHz implementation PASS"
exit