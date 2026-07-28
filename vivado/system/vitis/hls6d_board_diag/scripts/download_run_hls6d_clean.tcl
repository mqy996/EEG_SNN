# HLS-6D clean PS7 reset/download sequence. argv: <elf> <ps7_init.tcl> <bitstream>
set elf [file normalize [lindex $argv 0]]
set ps7 [file normalize [lindex $argv 1]]
set bit [file normalize [lindex $argv 2]]
foreach path [list $elf $ps7 $bit] { if {![file exists $path]} { error "Missing board artifact: $path" } }
connect -url tcp:localhost:3121
targets -set -nocase -filter {name =~ "xc7z020"}
fpga -f $bit
after 500
targets -set -nocase -filter {name =~ "ARM Cortex-A9 MPCore #0"}
stop
rst -system
after 1000
source $ps7
ps7_init
ps7_post_config
after 500
rst -system
after 500
dow $elf
puts "HLS6D_ELF_DOWNLOADED=$elf"
con
after 30000
puts "HLS6D_CPU_RUN_WINDOW_COMPLETE"
exit
