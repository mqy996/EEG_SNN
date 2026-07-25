`timescale 1ns / 1ps

// Fixed-vector replay wrapper for the HLS ap_memory interface.
// This is an integration smoke harness, not the final PS/PL board shell.
module hls_replay_wrapper (
    input  wire        clk,
    input  wire        rst,
    input  wire        start_level,
    input  wire [4:0]  count_index,
    output wire        ap_done,
    output wire        ap_idle,
    output wire        ap_ready,
    output wire [17:0] logits0,
    output wire [17:0] logits1,
    output wire [5:0]  count_value
);
    reg [11:0] feature_mem [0:1535];
    // HLS flattens weight_q[2][32] into one 64-word ap_memory array.
    // Both generated read ports address this same logical storage.
    reg [11:0] weight_mem [0:63];
    reg [11:0] bias_mem [0:1];
    reg [17:0] logits_mem [0:1];
    reg [17:0] logits_pending;
    reg [5:0]  count_mem [0:31];
    reg        start_d;
    integer i;

    wire start_pulse = start_level & ~start_d;
    wire [10:0] feature_addr;
    wire         feature_ce;
    wire [11:0]  feature_q;
    reg  [10:0]  feature_addr_q;
    wire [5:0]   weight0_addr;
    wire         weight0_ce;
    wire [11:0]  weight0_q;
    reg  [5:0]   weight0_addr_q;
    wire [5:0]   weight1_addr;
    wire         weight1_ce;
    wire [11:0]  weight1_q;
    reg  [5:0]   weight1_addr_q;
    wire [0:0]   bias_addr;
    wire         bias_ce;
    wire [11:0]  bias_q;
    reg  [0:0]   bias_addr_q;
    wire [0:0]   logits_addr;
    wire         logits_ce;
    wire         logits_we;
    wire [17:0]  logits_d;
    wire [4:0]   count_addr0;
    wire         count_ce0;
    wire         count_we0;
    wire [5:0]   count_d0;
    wire [4:0]   count_addr1;
    wire         count_ce1;
    wire [5:0]   count_q0;
    reg  [4:0]   count_addr0_q;
    wire [5:0]   count_q1;
    reg  [4:0]   count_addr1_q;

    // Deterministic threshold_edge vector from the checked-in HLS golden
    // contract. Explicit assignments keep the smoke harness portable in
    // Vivado/xsim; this is not the final PS/PL board shell.
    initial begin
        for (i = 0; i < 1536; i = i + 1) feature_mem[i] = 12'd0;
        for (i = 0; i < 64; i = i + 1) weight_mem[i] = 12'd0;
        for (i = 0; i < 32; i = i + 1) count_mem[i] = 6'd0;
        for (i = 0; i < 2; i = i + 1) begin
            bias_mem[i] = 12'd0;
            logits_mem[i] = 18'd0;
        end
        feature_mem[0] = 12'h020;
        feature_mem[1] = 12'h020;
        feature_mem[2] = 12'h021;
        feature_mem[33] = 12'h020;
        feature_mem[34] = 12'hfff;
        feature_mem[65] = 12'h020;
        feature_mem[67] = 12'h043;
        feature_mem[97] = 12'h020;
        feature_mem[99] = 12'hfe0;
        feature_mem[129] = 12'h020;
        feature_mem[161] = 12'h020;
        feature_mem[193] = 12'h020;
        feature_mem[225] = 12'h020;
        feature_mem[257] = 12'h020;
        feature_mem[289] = 12'h020;
        feature_mem[321] = 12'h020;
        feature_mem[353] = 12'h020;
        feature_mem[385] = 12'h020;
        feature_mem[417] = 12'h020;
        feature_mem[449] = 12'h020;
        feature_mem[481] = 12'h020;
        feature_mem[513] = 12'h020;
        feature_mem[545] = 12'h020;
        feature_mem[577] = 12'h020;
        feature_mem[609] = 12'h020;
        feature_mem[641] = 12'h020;
        feature_mem[673] = 12'h020;
        feature_mem[705] = 12'h020;
        feature_mem[737] = 12'h020;
        feature_mem[769] = 12'h020;
        feature_mem[801] = 12'h020;
        feature_mem[833] = 12'h020;
        feature_mem[865] = 12'h020;
        feature_mem[897] = 12'h020;
        feature_mem[929] = 12'h020;
        feature_mem[961] = 12'h020;
        feature_mem[993] = 12'h020;
        feature_mem[1025] = 12'h020;
        feature_mem[1057] = 12'h020;
        feature_mem[1089] = 12'h020;
        feature_mem[1121] = 12'h020;
        feature_mem[1153] = 12'h020;
        feature_mem[1185] = 12'h020;
        feature_mem[1217] = 12'h020;
        feature_mem[1249] = 12'h020;
        feature_mem[1281] = 12'h020;
        feature_mem[1313] = 12'h020;
        feature_mem[1345] = 12'h020;
        feature_mem[1377] = 12'h020;
        feature_mem[1409] = 12'h020;
        feature_mem[1441] = 12'h020;
        feature_mem[1473] = 12'h020;
        feature_mem[1505] = 12'h020;
        weight_mem[0] = 12'hf90;
        weight_mem[1] = 12'hfa0;
        weight_mem[2] = 12'hfb0;
        weight_mem[3] = 12'hfc0;
        weight_mem[4] = 12'hfd0;
        weight_mem[5] = 12'hfe0;
        weight_mem[6] = 12'hff0;
        weight_mem[8] = 12'h010;
        weight_mem[9] = 12'h020;
        weight_mem[10] = 12'h030;
        weight_mem[11] = 12'h040;
        weight_mem[12] = 12'h050;
        weight_mem[13] = 12'h060;
        weight_mem[14] = 12'h070;
        weight_mem[15] = 12'h080;
        weight_mem[16] = 12'h090;
        weight_mem[17] = 12'h0a0;
        weight_mem[18] = 12'h0b0;
        weight_mem[19] = 12'h0c0;
        weight_mem[20] = 12'h0d0;
        weight_mem[21] = 12'h0e0;
        weight_mem[22] = 12'h0f0;
        weight_mem[23] = 12'h100;
        weight_mem[24] = 12'h110;
        weight_mem[25] = 12'h120;
        weight_mem[26] = 12'h130;
        weight_mem[27] = 12'h140;
        weight_mem[28] = 12'h150;
        weight_mem[29] = 12'h160;
        weight_mem[30] = 12'h170;
        weight_mem[31] = 12'h180;
        weight_mem[32] = 12'h06e;
        weight_mem[33] = 12'h05c;
        weight_mem[34] = 12'h04a;
        weight_mem[35] = 12'h038;
        weight_mem[36] = 12'h026;
        weight_mem[37] = 12'h014;
        weight_mem[38] = 12'h002;
        weight_mem[39] = 12'hff0;
        weight_mem[40] = 12'hfde;
        weight_mem[41] = 12'hfcc;
        weight_mem[42] = 12'hfba;
        weight_mem[43] = 12'hfa8;
        weight_mem[44] = 12'hf96;
        weight_mem[45] = 12'hf84;
        weight_mem[46] = 12'hf72;
        weight_mem[47] = 12'hf60;
        weight_mem[48] = 12'hf4e;
        weight_mem[49] = 12'hf3c;
        weight_mem[50] = 12'hf2a;
        weight_mem[51] = 12'hf18;
        weight_mem[52] = 12'hf06;
        weight_mem[53] = 12'hef4;
        weight_mem[54] = 12'hee2;
        weight_mem[55] = 12'hed0;
        weight_mem[56] = 12'hebe;
        weight_mem[57] = 12'heac;
        weight_mem[58] = 12'he9a;
        weight_mem[59] = 12'he88;
        weight_mem[60] = 12'he76;
        weight_mem[61] = 12'he64;
        weight_mem[62] = 12'he52;
        weight_mem[63] = 12'he40;
        bias_mem[0] = 12'hff0;
        bias_mem[1] = 12'h018;
        start_d = 1'b0;
    end

    // HLS ap_memory read data is presented from the addressed storage word.
    // The generated kernel samples q on its clock edge after asserting CE.
    assign feature_q = feature_mem[feature_addr_q];
    assign weight0_q = weight_mem[weight0_addr_q];
    assign weight1_q = weight_mem[weight1_addr_q];
    assign bias_q = bias_mem[bias_addr_q];
    assign count_q0 = count_mem[count_addr0_q];
    assign count_q1 = count_mem[count_addr1_q];

    assign logits0 = logits_mem[0];
    assign logits1 = logits_mem[1];
    assign count_value = count_mem[count_index];

    always @(posedge clk) begin
        if (rst) begin
            start_d <= 1'b0;
            feature_addr_q <= 11'd0;
            weight0_addr_q <= 6'd0;
            weight1_addr_q <= 6'd0;
            bias_addr_q <= 1'd0;
            count_addr0_q <= 5'd0;
            count_addr1_q <= 5'd0;
            logits_mem[0] <= 18'd0;
            logits_mem[1] <= 18'd0;
            logits_pending <= 18'd0;
            for (i = 0; i < 32; i = i + 1) count_mem[i] <= 6'd0;
        end else begin
            start_d <= start_level;
            // Model ap_memory as a synchronous-read RAM: capture each
            // address on the clock edge and expose its word for the next
            // HLS clock edge. Capturing even when CE is low keeps q defined
            // during the first transaction after reset.
            feature_addr_q <= feature_addr;
            weight0_addr_q <= weight0_addr;
            weight1_addr_q <= weight1_addr;
            bias_addr_q <= bias_addr;
            count_addr0_q <= count_addr0;
            count_addr1_q <= count_addr1;
            if (logits_ce && logits_we) begin
                logits_pending <= logits_d;
                if (logits_addr == 1'b0)
                    logits_mem[0] <= logits_d;
                else
                    logits_mem[1] <= logits_d;
            end
            if (count_ce0 && count_we0)
                count_mem[count_addr0] <= count_d0;
        end
    end

    hybrid_lif_head_q12_6 u_hls (
        .ap_clk(clk),
        .ap_rst(rst),
        .ap_start(start_pulse),
        .ap_done(ap_done),
        .ap_idle(ap_idle),
        .ap_ready(ap_ready),
        .feature_current_q_address0(feature_addr),
        .feature_current_q_ce0(feature_ce),
        .feature_current_q_q0(feature_q),
        .weight_q_address0(weight0_addr),
        .weight_q_ce0(weight0_ce),
        .weight_q_q0(weight0_q),
        .weight_q_address1(weight1_addr),
        .weight_q_ce1(weight1_ce),
        .weight_q_q1(weight1_q),
        .bias_q_address0(bias_addr),
        .bias_q_ce0(bias_ce),
        .bias_q_q0(bias_q),
        .logits_q_address0(logits_addr),
        .logits_q_ce0(logits_ce),
        .logits_q_we0(logits_we),
        .logits_q_d0(logits_d),
        .spike_count_q_address0(count_addr0),
        .spike_count_q_ce0(count_ce0),
        .spike_count_q_we0(count_we0),
        .spike_count_q_d0(count_d0),
        .spike_count_q_q0(count_q0),
        .spike_count_q_address1(count_addr1),
        .spike_count_q_ce1(count_ce1),
        .spike_count_q_q1(count_q1)
    );
endmodule
