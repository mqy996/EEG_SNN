# XSCT 2025.1 platform/BSP generation for the SNN replay system.
# argv: <xsa> <work_dir>
set xsa [file normalize [lindex $argv 0]]
set work [file normalize [lindex $argv 1]]
if {![file exists $xsa]} { error "Missing XSA: $xsa" }
file mkdir $work
setws $work
platform create -name snn_replay_platform \
    -hw $xsa \
    -proc ps7_cortexa9_0 \
    -os standalone \
    -out [file join $work platform]
platform generate
puts "SNN standalone platform PASS: [file join $work platform]"
exit
