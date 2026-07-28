# HLS-6D XSCT download/run helper.
# argv: <elf> <ps7_init.tcl> <existing HLS-6B bitstream>
set elf [file normalize [lindex $argv 0]]
set ps7 [file normalize [lindex $argv 1]]
set bit [file normalize [lindex $argv 2]]
foreach path [list $elf $ps7 $bit] {
    if {![file exists $path]} { error "Missing board artifact: $path" }
}
connect -url tcp:localhost:3121
targets -set -nocase -filter {name =~ "xc7z020"}
fpga -f $bit
puts "HLS6D_FPGA_PROGRAMMED=$bit"
targets -set -nocase -filter {name =~ "ARM Cortex-A9 MPCore #0"}
rst -system
after 1000
source $ps7
ps7_init
ps7_post_config
dow $elf
puts "HLS6D_ELF_DOWNLOADED=$elf"
con
puts "HLS6D_CPU_CONTINUED"
after 30000
puts "HLS6D_CPU_RUN_WINDOW_COMPLETE"
exit
