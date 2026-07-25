`timescale 1ns / 1ps

module tb_snn_axi_memory_window;
    reg clk = 1'b0;
    always #10 clk = ~clk; // 50 MHz

    reg rst_n = 1'b0;
    reg [5:0] awaddr = 6'd0;
    reg awvalid = 1'b0;
    wire awready;
    reg [31:0] wdata = 32'd0;
    reg [3:0] wstrb = 4'hf;
    reg wvalid = 1'b0;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready = 1'b0;
    reg [5:0] araddr = 6'd0;
    reg arvalid = 1'b0;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready = 1'b0;

    reg [11:0] feature_vec [0:1535];
    reg [11:0] weight0_vec [0:31];
    reg [11:0] weight1_vec [0:31];
    reg [11:0] bias_vec [0:1];
    integer i;
    integer failures = 0;
    reg [31:0] rd;

    snn_axi_memory_window dut (
        .s_axi_aclk(clk),
        .s_axi_aresetn(rst_n),
        .s_axi_awaddr(awaddr),
        .s_axi_awvalid(awvalid),
        .s_axi_awready(awready),
        .s_axi_wdata(wdata),
        .s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid),
        .s_axi_wready(wready),
        .s_axi_bresp(bresp),
        .s_axi_bvalid(bvalid),
        .s_axi_bready(bready),
        .s_axi_araddr(araddr),
        .s_axi_arvalid(arvalid),
        .s_axi_arready(arready),
        .s_axi_rdata(rdata),
        .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid),
        .s_axi_rready(rready)
    );

    task automatic check(input condition, input [8*96-1:0] message);
        begin
            if (!condition) begin
                $display("CHECK_FAIL: %0s", message);
                failures = failures + 1;
            end
        end
    endtask

    task automatic axi_write(input [5:0] addr, input [31:0] data);
        begin
            @(negedge clk);
            awaddr <= addr;
            wdata <= data;
            wstrb <= 4'hf;
            awvalid <= 1'b1;
            wvalid <= 1'b1;
            while (!(awready && wready)) @(posedge clk);
            @(negedge clk);
            awvalid <= 1'b0;
            wvalid <= 1'b0;
            bready <= 1'b1;
            while (!bvalid) @(posedge clk);
            check(bresp == 2'b00, "AXI write response is OK");
            @(negedge clk);
            bready <= 1'b0;
        end
    endtask

    task automatic axi_write_split(input [5:0] addr, input [31:0] data);
        begin
            @(negedge clk);
            awaddr <= addr;
            awvalid <= 1'b1;
            while (!awready) @(posedge clk);
            @(negedge clk);
            awvalid <= 1'b0;
            repeat (2) @(posedge clk);
            @(negedge clk);
            wdata <= data;
            wstrb <= 4'hf;
            wvalid <= 1'b1;
            while (!wready) @(posedge clk);
            @(negedge clk);
            wvalid <= 1'b0;
            bready <= 1'b1;
            while (!bvalid) @(posedge clk);
            check(bresp == 2'b00, "split AXI write response is OK");
            @(negedge clk);
            bready <= 1'b0;
        end
    endtask

    task automatic axi_read(input [5:0] addr, output [31:0] data);
        begin
            @(negedge clk);
            araddr <= addr;
            arvalid <= 1'b1;
            while (!arready) @(posedge clk);
            @(negedge clk);
            arvalid <= 1'b0;
            rready <= 1'b1;
            while (!rvalid) @(posedge clk);
            data = rdata;
            check(rresp == 2'b00, "AXI read response is OK");
            check(^rdata !== 1'bx, "AXI read data has no X bits");
            @(negedge clk);
            rready <= 1'b0;
        end
    endtask

    task automatic wait_done;
        integer timeout;
        begin
            timeout = 0;
            while (timeout < 5000) begin
                axi_read(6'h04, rd);
                if (rd[1]) begin
                    $display("INFO: done after %0d polls, status=0x%08x", timeout + 1, rd);
                    disable wait_done;
                end
                timeout = timeout + 1;
            end
            check(1'b0, "done_latched asserted before timeout");
        end
    endtask

    initial begin
        $readmemh("vivado/replay/vectors/threshold_edge_feature.mem", feature_vec);
        $readmemh("vivado/replay/vectors/threshold_edge_weight0.mem", weight0_vec);
        $readmemh("vivado/replay/vectors/threshold_edge_weight1.mem", weight1_vec);
        $readmemh("vivado/replay/vectors/threshold_edge_bias.mem", bias_vec);

        repeat (5) @(posedge clk);
        rst_n <= 1'b1;
        repeat (3) @(posedge clk);

        axi_read(6'h08, rd);
        check(rd == 32'h0001_0001, "version register matches 1.1");
        axi_write_split(6'h0c, 32'h20260725);
        axi_read(6'h0c, rd);
        check(rd == 32'h20260725, "VECTOR_ID supports split AW/W");

        // Bounds checking and write-one-to-clear error behavior.
        axi_write(6'h10, 32'd1536);
        axi_read(6'h3c, rd);
        check(rd[0] == 1'b1, "out-of-range feature index sets address error");
        axi_write(6'h3c, 32'h0000_0001);
        axi_read(6'h3c, rd);
        check(rd[0] == 1'b0, "ERROR_STATUS W1C clears address error");

        $display("INFO: loading 1536 features, 64 weights and 2 biases through AXI windows");
        for (i = 0; i < 1536; i = i + 1) begin
            axi_write(6'h10, i);
            axi_write(6'h14, {20'd0, feature_vec[i]});
        end
        for (i = 0; i < 32; i = i + 1) begin
            axi_write(6'h18, i);
            axi_write(6'h1c, {20'd0, weight0_vec[i]});
        end
        for (i = 0; i < 32; i = i + 1) begin
            axi_write(6'h18, i + 32);
            axi_write(6'h1c, {20'd0, weight1_vec[i]});
        end
        for (i = 0; i < 2; i = i + 1) begin
            axi_write(6'h20, i);
            axi_write(6'h24, {20'd0, bias_vec[i]});
        end

        axi_write(6'h00, 32'h0000_0001);
        repeat (2) @(posedge clk);
        axi_read(6'h04, rd);
        // This input write occurs while the core is busy and must be rejected.
        axi_write(6'h10, 32'd0);
        axi_write(6'h14, 32'h0000_0777);
        wait_done();
        axi_read(6'h3c, rd);
        check(rd[1] == 1'b1, "busy input write sets busy-write error");
        axi_write(6'h3c, 32'h0000_0002);

        axi_write(6'h28, 32'd0);
        axi_read(6'h2c, rd);
        check(rd == 32'hffff_ff8c, "logit[0] matches -116");
        axi_write(6'h28, 32'd1);
        axi_read(6'h2c, rd);
        check(rd == 32'd120, "logit[1] matches 120");
        for (i = 0; i < 4; i = i + 1) begin
            axi_write(6'h30, i);
            axi_read(6'h34, rd);
            if (i == 0) check(rd == 32'd1, "count[0] matches 1");
            if (i == 1) check(rd == 32'd48, "count[1] matches 48");
            if (i == 2) check(rd == 32'd1, "count[2] matches 1");
            if (i == 3) check(rd == 32'd1, "count[3] matches 1");
        end

        axi_write(6'h00, 32'h0000_0002);
        repeat (4) @(posedge clk);
        axi_read(6'h04, rd);
        check(rd[0] == 1'b1, "soft reset returns wrapper to idle");
        check(rd[1] == 1'b0, "soft reset clears done latch");
        axi_write(6'h30, 32'd0);
        axi_read(6'h34, rd);
        check(rd == 32'd0, "soft reset clears spike-count output");

        if (failures == 0) begin
            $display("SNN AXI memory-window simulation PASS");
            $finish;
        end else begin
            $display("SNN AXI memory-window simulation FAIL failures=%0d", failures);
            $fatal(1);
        end
    end
endmodule
