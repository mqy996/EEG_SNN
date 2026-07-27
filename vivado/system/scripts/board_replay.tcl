# XSCT fixed-vector board replay.
# argv: <bitstream> <elf> <ps7_init.tcl>
set bit [file normalize [lindex $argv 0]]
set elf [file normalize [lindex $argv 1]]
set ps7 [file normalize [lindex $argv 2]]
if {![file exists $bit] || ![file exists $elf] || ![file exists $ps7]} {
    error "bitstream, ELF or ps7_init.tcl is missing"
}
connect -url tcp:localhost:3121
targets -set -nocase -filter {name =~ "xc7z020"}
fpga -f $bit
puts "FPGA_PROGRAMMED=$bit"
targets -set -nocase -filter {name =~ "ARM Cortex-A9 MPCore #0"}
rst -system
after 1000
source $ps7
ps7_init
ps7_post_config
dow $elf
puts "ELF_DOWNLOADED=$elf"
con
after 30000
puts "CPU_RUN_WINDOW_COMPLETE"
exit
