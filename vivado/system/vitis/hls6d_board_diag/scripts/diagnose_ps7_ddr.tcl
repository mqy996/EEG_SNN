# HLS-6D bounded PS7/DDR initialization diagnostic.
# Usage: xsct diagnose_ps7_ddr.tcl <bitstream> <ps7_init.tcl> <label>
set bit [file normalize [lindex $argv 0]]
set ps7 [file normalize [lindex $argv 1]]
set label [lindex $argv 2]

proc read_reg {name addr} {
    puts "HLS6D_DDR_READ_BEGIN name=$name addr=$addr"
    if {[catch {mrd -force $addr 1} result]} {
        puts "HLS6D_DDR_READ_ERROR name=$name error=$result"
    } else {
        puts "HLS6D_DDR_READ_RESULT name=$name result=$result"
    }
}

puts "HLS6D_DDR_DIAG_START label=$label"
puts "HLS6D_DDR_BITSTREAM=$bit"
puts "HLS6D_DDR_PS7_INIT=$ps7"

if {[catch {connect -url tcp:localhost:3121} result]} {
    puts "HLS6D_DDR_CONNECT_ERROR error=$result"
    exit 2
}
if {[catch {targets -set -nocase -filter {name =~ "xc7z020"}} result]} {
    puts "HLS6D_DDR_FPGA_TARGET_ERROR error=$result"
    exit 3
}
if {[catch {fpga -f $bit} result]} {
    puts "HLS6D_DDR_FPGA_PROGRAM_ERROR error=$result"
    exit 4
}
puts "HLS6D_DDR_FPGA_PROGRAMMED"

if {[catch {targets -set -nocase -filter {name =~ "ARM Cortex-A9 MPCore #0"}} result]} {
    puts "HLS6D_DDR_ARM_TARGET_ERROR error=$result"
    exit 5
}
if {[catch {rst -system} result]} {
    puts "HLS6D_DDR_RESET_ERROR error=$result"
}
after 1000

# Capture the reset state before PS7 initialization.
read_reg pss_rst_ctrl_before 0xF8000008
read_reg slcr_lock 0xF8000004
read_reg ddr_dci_status_before 0xF8006054

if {[catch {source $ps7} result]} {
    puts "HLS6D_DDR_SOURCE_ERROR error=$result"
    exit 6
}
if {[catch {ps7_init} result]} {
    puts "HLS6D_DDR_PS7_INIT_ERROR error=$result"
    exit 7
}
puts "HLS6D_DDR_PS7_INIT_DONE"
if {[catch {ps7_post_config} result]} {
    puts "HLS6D_DDR_PS7_POST_CONFIG_ERROR error=$result"
    exit 8
}
puts "HLS6D_DDR_PS7_POST_CONFIG_DONE"

after 100
read_reg pss_rst_ctrl_after 0xF8000008
read_reg slcr_lock_after 0xF8000004
read_reg ddr_ctrl 0xF8006000
read_reg ddr_dci_status 0xF8006054
read_reg ddr_phy_ctrl 0xF8006050
read_reg ddr_dram_param 0xF80061A0
read_reg ddr_ecc_ctrl 0xF80060A0
read_reg ddr_cmd_status 0xF8006058

puts "HLS6D_DDR_DIAG_COMPLETE label=$label"
exit 0