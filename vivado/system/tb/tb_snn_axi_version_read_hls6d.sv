`timescale 1ns / 1ps

// HLS-6D focused AXI4-Lite read-channel test.
// This deliberately stubs the HLS compute core so it checks only the wrapper's
// AR/R protocol and registered VERSION/STATUS read responses.
module tb_snn_axi_version_read_hls6d;
    reg clk = 1'b0;
    always #10 clk = ~clk; // 50 MHz

    reg rst_n = 1'b0;
    reg [5:0] araddr = 6'd0;
    reg arvalid = 1'b0;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready = 1'b0;

    wire awready;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;

    integer failures = 0;
    integer cycle_count = 0;
    reg [31:0] held_rdata;
    reg [1:0] held_rresp;

    always @(posedge clk) cycle_count = cycle_count + 1;

    snn_axi_memory_window_hls6a dut (
        .s_axi_aclk(clk),
        .s_axi_aresetn(rst_n),
        .s_axi_awaddr(6'd0),
        .s_axi_awvalid(1'b0),
        .s_axi_awready(awready),
        .s_axi_wdata(32'd0),
        .s_axi_wstrb(4'd0),
        .s_axi_wvalid(1'b0),
        .s_axi_wready(wready),
        .s_axi_bresp(bresp),
        .s_axi_bvalid(bvalid),
        .s_axi_bready(1'b0),
        .s_axi_araddr(araddr),
        .s_axi_arvalid(arvalid),
        .s_axi_arready(arready),
        .s_axi_rdata(rdata),
        .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid),
        .s_axi_rready(rready)
    );

    task automatic check(input condition, input [8*160-1:0] message);
        begin
            if (!condition) begin
                $display("HLS6D_AXI_VERSION_CHECK_FAIL cycle=%0d: %0s", cycle_count, message);
                failures = failures + 1;
            end
        end
    endtask

    // Accept an address with RREADY low.  The response must be registered on
    // the AR handshake, remain asserted and stable while stalled, then clear
    // only after the R handshake.
    task automatic stalled_read(input [5:0] addr, input [31:0] expected_data,
                                input [8*48-1:0] name);
        begin
            @(negedge clk);
            check(arready, "ARREADY asserted before request");
            araddr <= addr;
            arvalid <= 1'b1;
            rready <= 1'b0;

            @(posedge clk); // AR handshake
            $display("HLS6D_EVT=AR_HANDSHAKE name=%0s cycle=%0d addr=0x%02h", name, cycle_count, addr);
            @(negedge clk);
            arvalid <= 1'b0;
            check(rvalid, "RVALID asserted within one clock after AR handshake");
            check(rresp == 2'b00, "RRESP is OKAY");
            check(rdata == expected_data, "registered read data matches expected value");
            held_rdata = rdata;
            held_rresp = rresp;
            $display("HLS6D_EVT=RVALID_STALLED name=%0s cycle=%0d rdata=0x%08h rresp=0x%0h", name, cycle_count, rdata, rresp);

            repeat (2) begin
                @(negedge clk);
                check(rvalid, "RVALID remains high while RREADY is low");
                check(rdata == held_rdata, "RDATA remains stable while stalled");
                check(rresp == held_rresp, "RRESP remains stable while stalled");
            end

            rready <= 1'b1;
            @(posedge clk); // R handshake
            $display("HLS6D_EVT=R_HANDSHAKE name=%0s cycle=%0d", name, cycle_count);
            @(negedge clk);
            rready <= 1'b0;
            check(!rvalid, "RVALID clears after R handshake");
            check(arready, "ARREADY reasserts after R handshake");
        end
    endtask

    // This covers a master that keeps RREADY high, as SmartConnect may do.
    task automatic ready_high_version_read;
        begin
            @(negedge clk);
            check(arready, "ARREADY asserted before ready-high VERSION request");
            araddr <= 6'h08;
            arvalid <= 1'b1;
            rready <= 1'b1;

            @(posedge clk); // AR handshake
            $display("HLS6D_EVT=AR_HANDSHAKE name=VERSION_READY_HIGH cycle=%0d addr=0x08", cycle_count);
            @(negedge clk);
            arvalid <= 1'b0;
            check(rvalid, "RVALID asserted for ready-high VERSION request");
            check(rresp == 2'b00, "ready-high VERSION RRESP is OKAY");
            check(rdata == 32'h0001_0001, "ready-high VERSION returns 0x00010001");
            $display("HLS6D_EVT=RVALID_READY_HIGH cycle=%0d rdata=0x%08h rresp=0x%0h", cycle_count, rdata, rresp);

            @(posedge clk); // R handshake
            $display("HLS6D_EVT=R_HANDSHAKE name=VERSION_READY_HIGH cycle=%0d", cycle_count);
            @(negedge clk);
            rready <= 1'b0;
            check(!rvalid, "ready-high VERSION response clears after R handshake");
            check(arready, "ARREADY reasserts after ready-high VERSION response");
        end
    endtask

    initial begin
        $dumpfile("hls6d_axi_lite_version.vcd");
        $dumpvars(0, tb_snn_axi_version_read_hls6d);

        repeat (4) @(posedge clk);
        @(negedge clk);
        rst_n <= 1'b1;
        @(negedge clk);
        check(arready, "ARREADY exits reset high with no read response pending");

        stalled_read(6'h08, 32'h0001_0001, "VERSION");
        stalled_read(6'h04, 32'h0000_0011, "STATUS");
        ready_high_version_read();

        if (failures == 0) begin
            $display("HLS6D_AXI_VERSION_SIM_PASS cycles=%0d version=0x00010001", cycle_count);
            $finish;
        end else begin
            $display("HLS6D_AXI_VERSION_SIM_FAIL failures=%0d cycles=%0d", failures, cycle_count);
            $fatal(1);
        end
    end
endmodule

// The focused read test intentionally removes the generated HLS datapath from
// the proof boundary. Its always-idle outputs make STATUS deterministic while
// preserving every port used by the wrapper.
module hybrid_lif_head_q12_6 (
    input wire ap_clk,
    input wire ap_rst,
    input wire ap_start,
    output wire ap_done,
    output wire ap_idle,
    output wire ap_ready,
    output wire [10:0] feature_current_q_address0,
    output wire feature_current_q_ce0,
    input wire [11:0] feature_current_q_q0,
    output wire [5:0] weight_q_address0,
    output wire weight_q_ce0,
    input wire [11:0] weight_q_q0,
    output wire [5:0] weight_q_address1,
    output wire weight_q_ce1,
    input wire [11:0] weight_q_q1,
    output wire [0:0] bias_q_address0,
    output wire bias_q_ce0,
    input wire [11:0] bias_q_q0,
    output wire [0:0] logits_q_address0,
    output wire logits_q_ce0,
    output wire logits_q_we0,
    output wire [17:0] logits_q_d0,
    output wire [4:0] spike_count_q_address0,
    output wire spike_count_q_ce0,
    output wire spike_count_q_we0,
    output wire [5:0] spike_count_q_d0,
    input wire [5:0] spike_count_q_q0,
    output wire [4:0] spike_count_q_address1,
    output wire spike_count_q_ce1,
    input wire [5:0] spike_count_q_q1
);
    assign ap_done = 1'b0;
    assign ap_idle = 1'b1;
    assign ap_ready = 1'b1;
    assign feature_current_q_address0 = 11'd0;
    assign feature_current_q_ce0 = 1'b0;
    assign weight_q_address0 = 6'd0;
    assign weight_q_ce0 = 1'b0;
    assign weight_q_address1 = 6'd0;
    assign weight_q_ce1 = 1'b0;
    assign bias_q_address0 = 1'b0;
    assign bias_q_ce0 = 1'b0;
    assign logits_q_address0 = 1'b0;
    assign logits_q_ce0 = 1'b0;
    assign logits_q_we0 = 1'b0;
    assign logits_q_d0 = 18'd0;
    assign spike_count_q_address0 = 5'd0;
    assign spike_count_q_ce0 = 1'b0;
    assign spike_count_q_we0 = 1'b0;
    assign spike_count_q_d0 = 6'd0;
    assign spike_count_q_address1 = 5'd0;
    assign spike_count_q_ce1 = 1'b0;
endmodule
