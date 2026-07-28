set bit [file normalize [lindex $argv 0]]
set ps7 [file normalize [lindex $argv 1]]
puts "HLS6D_GPIO_JTAG_START"
connect -url tcp:localhost:3121
targets -set -nocase -filter {name =~ "xc7z020"}
fpga -f $bit
puts "HLS6D_GPIO_JTAG_FPGA_PROGRAMMED"
targets -set -nocase -filter {name =~ "ARM Cortex-A9 MPCore #0"}
rst -system
after 1000
source $ps7
ps7_init
ps7_post_config
puts "HLS6D_GPIO_JTAG_PS7_READY"
foreach addr {0x41200000 0x41200004 0x43C00004 0x43C00008} {
  puts "HLS6D_GPIO_JTAG_READ_BEGIN addr=$addr"
  if {[catch {mrd -force $addr 1} result]} { puts "HLS6D_GPIO_JTAG_READ_ERROR addr=$addr error=$result" } else { puts "HLS6D_GPIO_JTAG_READ_RESULT addr=$addr result=$result" }
}
puts "HLS6D_GPIO_JTAG_COMPLETE"
exit 0