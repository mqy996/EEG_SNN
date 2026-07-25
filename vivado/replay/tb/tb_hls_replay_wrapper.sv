`timescale 1ns / 1ps

module tb_hls_replay_wrapper;
    reg clk = 1'b0;
    reg rst = 1'b1;
    reg start_level = 1'b0;
    reg [4:0] count_index = 5'd0;
    wire ap_done;
    wire ap_idle;
    wire ap_ready;
    wire [17:0] logits0;
    wire [17:0] logits1;
    wire [5:0] count_value;

    hls_replay_wrapper dut (
        .clk(clk), .rst(rst), .start_level(start_level),
        .count_index(count_index), .ap_done(ap_done),
        .ap_idle(ap_idle), .ap_ready(ap_ready),
        .logits0(logits0), .logits1(logits1), .count_value(count_value)
    );

    always #10 clk = ~clk;

    integer failures;

    task check_count(input [4:0] index, input [5:0] expected);
        begin
            count_index = index;
            #1;
            if (count_value !== expected) begin
                $display("FAIL count[%0d] expected=%0d actual=%0d", index, expected, count_value);
                failures = failures + 1;
            end
        end
    endtask

    integer cycles;
    reg done_seen;
    always @(posedge clk) begin
        if (ap_done) done_seen <= 1'b1;
    end

    initial begin
        failures = 0;
        repeat (3) @(posedge clk);
        rst <= 1'b0;
        repeat (2) @(posedge clk);
        if (!ap_idle) begin
            $display("FAIL expected ap_idle before start");
            failures = failures + 1;
        end

        start_level <= 1'b1;
        @(posedge clk);
        start_level <= 1'b0;

        cycles = 0;
        done_seen = 1'b0;
        while (!done_seen && cycles < 3000) begin
            @(posedge clk);
            cycles = cycles + 1;
        end
        if (!done_seen && cycles >= 3000) begin
            $display("FAIL timeout waiting for ap_done cycles=%0d", cycles);
            failures = failures + 1;
        end

        #1;
        if ($signed(logits0) !== -18'sd116 || $signed(logits1) !== 18'sd120) begin
            $display("FAIL logits expected=(-116,120) actual=(%0d,%0d)", $signed(logits0), $signed(logits1));
            failures = failures + 1;
        end
        check_count(5'd0, 6'd1);
        check_count(5'd1, 6'd48);
        check_count(5'd2, 6'd1);
        check_count(5'd3, 6'd1);
        check_count(5'd4, 6'd0);

        if (failures != 0) begin
            $display("SNN replay simulation FAIL failures=%0d cycles=%0d", failures, cycles);
            $fatal(1);
        end
        $display("SNN replay simulation PASS cycles=%0d logits=(%0d,%0d)", cycles, $signed(logits0), $signed(logits1));
        $finish;
    end
endmodule

