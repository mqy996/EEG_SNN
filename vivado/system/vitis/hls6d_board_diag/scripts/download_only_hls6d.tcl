# Bounded HLS-6D PS7 init + ELF download check.
set bit [file normalize [lindex $argv 0]]
set elf [file normalize [lindex $argv 1]]
set ps7 [file normalize [lindex $argv 2]]
puts "HLS6D_DOW_START"
connect -url tcp:localhost:3121
targets -set -nocase -filter {name =~ "xc7z020"}
fpga -f $bit
puts "HLS6D_DOW_FPGA_PROGRAMMED"
targets -set -nocase -filter {name =~ "ARM Cortex-A9 MPCore #0"}
rst -system
after 1000
source $ps7
ps7_init
ps7_post_config
puts "HLS6D_DOW_PS7_READY"
if {[catch {dow $elf} result]} {
    puts "HLS6D_DOW_ERROR error=$result"
    exit 10
}
puts "HLS6D_DOW_ELF_DOWNLOADED=$elf"
exit 0