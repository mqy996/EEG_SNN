`timescale 1ns / 1ps

module tb_snn_axi_memory_window_hls6a;
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
    reg [11:0] weight_vec [0:63];
    reg [11:0] bias_vec [0:1];
    reg [17:0] expected_logits [0:1];
    reg [5:0] expected_counts [0:31];
    integer i;
    integer failures = 0;
    integer write_transactions = 0;
    integer read_transactions = 0;
    integer kernel_cycle_counter = 0;
    integer kernel_cycles_last = 0;
    reg kernel_running = 1'b0;
    reg [31:0] rd;

    snn_axi_memory_window_hls6a dut (
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

    // Count only HLS kernel cycles, not AXI polling cycles.
    always @(posedge clk) begin
        if (!rst_n) begin
            kernel_cycle_counter <= 0;
            kernel_cycles_last <= 0;
            kernel_running <= 1'b0;
        end else if (dut.start_pulse) begin
            kernel_cycle_counter <= 0;
            kernel_running <= 1'b1;
        end else if (kernel_running) begin
            kernel_cycle_counter <= kernel_cycle_counter + 1;
            if (dut.ap_done) begin
                kernel_cycles_last <= kernel_cycle_counter + 1;
                kernel_running <= 1'b0;
            end
        end
    end

    task automatic check(input condition, input [8*128-1:0] message);
        begin
            if (!condition) begin
                $display("CHECK_FAIL: %0s", message);
                failures = failures + 1;
            end
        end
    endtask

    task automatic axi_write(input [5:0] addr, input [31:0] data);
        integer guard;
        begin
            @(negedge clk);
            awaddr <= addr;
            wdata <= data;
            wstrb <= 4'hf;
            awvalid <= 1'b1;
            wvalid <= 1'b1;
            guard = 0;
            while (!(awready && wready)) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "AXI write address/data handshake timeout");
                    awvalid <= 1'b0;
                    wvalid <= 1'b0;
                    disable axi_write;
                end
            end
            @(negedge clk);
            awvalid <= 1'b0;
            wvalid <= 1'b0;
            bready <= 1'b1;
            guard = 0;
            while (!bvalid) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "AXI write response timeout");
                    bready <= 1'b0;
                    disable axi_write;
                end
            end
            check(bresp == 2'b00, "AXI write response is OK");
            write_transactions = write_transactions + 1;
            @(negedge clk);
            bready <= 1'b0;
        end
    endtask

    task automatic axi_write_split(input [5:0] addr, input [31:0] data);
        integer guard;
        begin
            @(negedge clk);
            awaddr <= addr;
            awvalid <= 1'b1;
            guard = 0;
            while (!awready) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "split AXI AW handshake timeout");
                    awvalid <= 1'b0;
                    disable axi_write_split;
                end
            end
            @(negedge clk);
            awvalid <= 1'b0;
            repeat (2) @(posedge clk);
            @(negedge clk);
            wdata <= data;
            wstrb <= 4'hf;
            wvalid <= 1'b1;
            guard = 0;
            while (!wready) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "split AXI W handshake timeout");
                    wvalid <= 1'b0;
                    disable axi_write_split;
                end
            end
            @(negedge clk);
            wvalid <= 1'b0;
            bready <= 1'b1;
            guard = 0;
            while (!bvalid) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "split AXI write response timeout");
                    bready <= 1'b0;
                    disable axi_write_split;
                end
            end
            check(bresp == 2'b00, "split AXI write response is OK");
            write_transactions = write_transactions + 1;
            @(negedge clk);
            bready <= 1'b0;
        end
    endtask

    task automatic axi_read(input [5:0] addr, output [31:0] data);
        integer guard;
        begin
            @(negedge clk);
            araddr <= addr;
            arvalid <= 1'b1;
            guard = 0;
            while (!arready) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "AXI read address handshake timeout");
                    arvalid <= 1'b0;
                    data = 32'd0;
                    disable axi_read;
                end
            end
            @(negedge clk);
            arvalid <= 1'b0;
            rready <= 1'b1;
            guard = 0;
            while (!rvalid) begin
                @(posedge clk);
                guard = guard + 1;
                if (guard >= 100) begin
                    check(1'b0, "AXI read response timeout");
                    rready <= 1'b0;
                    data = 32'd0;
                    disable axi_read;
                end
            end
            data = rdata;
            check(rresp == 2'b00, "AXI read response is OK");
            check(^rdata !== 1'bx, "AXI read data has no X bits");
            read_transactions = read_transactions + 1;
            @(negedge clk);
            rready <= 1'b0;
        end
    endtask

    task automatic wait_done(output integer polls);
        integer guard;
        begin
            polls = 0;
            guard = 0;
            while (guard < 5000) begin
                axi_read(6'h04, rd);
                polls = polls + 1;
                if (rd[1]) begin
                    disable wait_done;
                end
                guard = guard + 1;
            end
            check(1'b0, "done_latched asserted before timeout");
        end
    endtask

    task automatic compare_case(input string case_name, input integer case_index);
        integer polls;
        integer run_number;
        integer case_write_start;
        integer case_read_start;
        integer sign_extended_logit;
        reg [31:0] expected_word;
        begin
            $readmemh($sformatf("vivado/system/vectors/%s_feature.mem", case_name), feature_vec);
            $readmemh($sformatf("vivado/system/vectors/%s_weight.mem", case_name), weight_vec);
            $readmemh($sformatf("vivado/system/vectors/%s_bias.mem", case_name), bias_vec);
            $readmemh($sformatf("vivado/system/vectors/%s_logits.mem", case_name), expected_logits);
            $readmemh($sformatf("vivado/system/vectors/%s_count.mem", case_name), expected_counts);
            check(^feature_vec[0] !== 1'bx, "feature vector file loaded");
            check(^weight_vec[0] !== 1'bx, "weight vector file loaded");
            check(^bias_vec[0] !== 1'bx, "bias vector file loaded");
            check(^expected_logits[0] !== 1'bx, "logit golden file loaded");
            check(^expected_counts[0] !== 1'bx, "count golden file loaded");

            case_write_start = write_transactions;
            case_read_start = read_transactions;
            // Each case starts from a clean membrane/output/error state while
            // retaining the AXI input memories for the next invocation.
            axi_write(6'h00, 32'h0000_0002);
            repeat (4) @(posedge clk);

            if (case_index == 0) begin
                axi_write(6'h10, 32'd1536);
                axi_read(6'h3c, rd);
                check(rd[0] == 1'b1, "out-of-range index sets address error");
                axi_write(6'h3c, 32'h0000_0001);
            end

            $display("INFO: loading case %0s", case_name);
            for (i = 0; i < 1536; i = i + 1) begin
                axi_write(6'h10, i);
                axi_write(6'h14, {20'd0, feature_vec[i]});
            end
            for (i = 0; i < 64; i = i + 1) begin
                axi_write(6'h18, i);
                axi_write(6'h1c, {20'd0, weight_vec[i]});
            end
            for (i = 0; i < 2; i = i + 1) begin
                axi_write(6'h20, i);
                axi_write(6'h24, {20'd0, bias_vec[i]});
            end

            for (run_number = 0; run_number < 2; run_number = run_number + 1) begin
                kernel_cycles_last = 0;
                axi_write(6'h00, 32'h0000_0001);
                if (run_number == 0) begin
                    // Start and input writes while busy must be rejected but
                    // must not change the current inference memory.
                    axi_write(6'h00, 32'h0000_0001);
                    axi_write(6'h10, 32'd0);
                    axi_write(6'h14, 32'h0000_0777);
                end
                wait_done(polls);
                if (run_number == 0) begin
                    axi_read(6'h3c, rd);
                    check((rd[1] == 1'b1) && (rd[2] == 1'b1), "busy write and illegal start are recorded");
                    axi_write(6'h3c, 32'h0000_0006);
                end

                for (i = 0; i < 2; i = i + 1) begin
                    axi_write(6'h28, i);
                    axi_read(6'h2c, rd);
                    expected_word = {{14{expected_logits[i][17]}}, expected_logits[i]};
                    $display("LOGIT case=%0s run=%0d idx=%0d actual=%08x expected=%08x raw=%05x", case_name, run_number + 1, i, rd, expected_word, expected_logits[i]);
                    check(rd == expected_word, "signed logit matches golden");
                end
                for (i = 0; i < 32; i = i + 1) begin
                    axi_write(6'h30, i);
                    axi_read(6'h34, rd);
                    check(rd == {{26{1'b0}}, expected_counts[i]}, "spike count matches golden");
                end

                $display("CASE %0s run=%0d write_transactions=%0d read_transactions=%0d kernel_cycles=%0d polls=%0d", case_name, run_number + 1, write_transactions - case_write_start, read_transactions - case_read_start, kernel_cycles_last, polls);
                case_write_start = write_transactions;
                case_read_start = read_transactions;

                if (run_number == 0) begin
                    // A plain done clear is the repeat-invocation path. The
                    // HLS top must reinitialize call-local state on start.
                    axi_write(6'h00, 32'h0000_0004);
                    axi_read(6'h04, rd);
                    check(rd[1] == 1'b0, "clear_done clears done latch");
                end
            end

            axi_write(6'h00, 32'h0000_0002);
            repeat (4) @(posedge clk);
            axi_read(6'h04, rd);
            check(rd[0] == 1'b1 && rd[1] == 1'b0, "soft reset clears idle/done state");
            axi_write(6'h28, 32'd0);
            axi_read(6'h2c, rd);
            check(rd == 32'd0, "soft reset clears logits");
            axi_write(6'h30, 32'd0);
            axi_read(6'h34, rd);
            check(rd == 32'd0, "soft reset clears spike counts");
            axi_read(6'h3c, rd);
            check(rd == 32'd0, "case ends with no wrapper error status");
        end
    endtask

    initial begin
        repeat (5) @(posedge clk);
        rst_n <= 1'b1;
        repeat (3) @(posedge clk);

        axi_read(6'h08, rd);
        check(rd == 32'h0001_0001, "version register matches 1.1");
        axi_write_split(6'h0c, 32'h20260726);
        axi_read(6'h0c, rd);
        check(rd == 32'h20260726, "VECTOR_ID supports split AW/W");

        compare_case("threshold_edge", 0);
        compare_case("signed_currents", 1);
        compare_case("rounding_and_reset", 2);

        if (failures == 0) begin
            $display("SNN AXI memory-window 3-case simulation PASS writes=%0d reads=%0d", write_transactions, read_transactions);
            $finish;
        end else begin
            $display("SNN AXI memory-window 3-case simulation FAIL failures=%0d writes=%0d reads=%0d", failures, write_transactions, read_transactions);
            $fatal(1);
        end
    end
endmodule
