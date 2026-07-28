# HLS-6D board diagnostic XSCT runner
# argv: <elf> <ps7_init.tcl>
set elf [file normalize [lindex $argv 0]]
set ps7 [file normalize [lindex $argv 1]]
if {![file exists $elf]} { error "Missing ELF: $elf" }
if {![file exists $ps7]} { error "Missing ps7_init.tcl: $ps7" }
connect
targets -set -nocase -filter {name =~ "ARM*#0"}
stop
source $ps7
rst -system
after 500
fpga -f [file normalize [lindex $argv 2]]
after 500
targets -set -nocase -filter {name =~ "ARM*#0"}
dow $elf
puts "HLS6D_ELF_DOWNLOADED=$elf"
con
after 12000
puts "HLS6D_CPU_RUN_WINDOW_COMPLETE"
exit
