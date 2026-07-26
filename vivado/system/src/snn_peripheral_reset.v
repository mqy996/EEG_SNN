`timescale 1ns / 1ps
module snn_peripheral_reset (
    input wire slowest_sync_clk,
    input wire ext_reset_in,
    output wire peripheral_aresetn
);
    reg [3:0] sync_pipe = 4'b0000;
    always @(posedge slowest_sync_clk) begin
        if (ext_reset_in) sync_pipe <= 4'b0000;
        else sync_pipe <= {sync_pipe[2:0], 1'b1};
    end
    assign peripheral_aresetn = sync_pipe[3];
endmodule
