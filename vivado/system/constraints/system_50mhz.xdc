# Pre-board AXI-Lite wrapper timing contract.
# Board pin and PS clock routing are intentionally deferred to HLS-5A.3.
create_clock -name s_axi_aclk -period 20.000 [get_ports s_axi_aclk]
set_false_path -from [get_ports s_axi_aresetn]
