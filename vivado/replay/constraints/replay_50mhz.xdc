# Smoke-harness clock only. Board pin mapping is intentionally deferred until
# the exact development-board model and its master XDC are confirmed.
create_clock -name replay_clk -period 20.000 [get_ports clk]
set_false_path -from [get_ports rst]
set_false_path -from [get_ports start_level]
set_false_path -from [get_ports count_index[*]]