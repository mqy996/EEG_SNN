`timescale 1ns / 1ps

// AXI4-Lite controlled PS/PL boundary for the verified Hybrid LIF HLS head.
//
// This first version deliberately uses indexed data windows instead of DMA or
// DDR. It is intended for deterministic PS/PL replay and pre-board simulation.
// The HLS core and its synchronous ap_memory contract remain unchanged.
module snn_axi_memory_window #(
    parameter integer C_S_AXI_ADDR_WIDTH = 6,
    parameter integer C_S_AXI_DATA_WIDTH = 32
) (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 S_AXI_ACLK CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 50000000" *)
    input  wire                         s_axi_aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 S_AXI_ARESETN RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input  wire                         s_axi_aresetn,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *)
    input  wire [C_S_AXI_ADDR_WIDTH-1:0] s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input  wire                         s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire                         s_axi_awready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input  wire [C_S_AXI_DATA_WIDTH-1:0] s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input  wire                         s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire                         s_axi_wready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output reg  [1:0]                   s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output reg                          s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input  wire                         s_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input  wire [C_S_AXI_ADDR_WIDTH-1:0] s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input  wire                         s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire                         s_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output reg  [C_S_AXI_DATA_WIDTH-1:0] s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output reg  [1:0]                   s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output reg                          s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input  wire                         s_axi_rready
);
    localparam [31:0] VERSION_VALUE = 32'h0001_0001;
    localparam [5:0] ADDR_CONTROL      = 6'h00;
    localparam [5:0] ADDR_STATUS       = 6'h04;
    localparam [5:0] ADDR_VERSION      = 6'h08;
    localparam [5:0] ADDR_VECTOR_ID    = 6'h0c;
    localparam [5:0] ADDR_FEATURE_IDX  = 6'h10;
    localparam [5:0] ADDR_FEATURE_DATA = 6'h14;
    localparam [5:0] ADDR_WEIGHT_IDX   = 6'h18;
    localparam [5:0] ADDR_WEIGHT_DATA  = 6'h1c;
    localparam [5:0] ADDR_BIAS_IDX     = 6'h20;
    localparam [5:0] ADDR_BIAS_DATA    = 6'h24;
    localparam [5:0] ADDR_LOGIT_IDX    = 6'h28;
    localparam [5:0] ADDR_LOGIT_DATA   = 6'h2c;
    localparam [5:0] ADDR_COUNT_IDX    = 6'h30;
    localparam [5:0] ADDR_COUNT_DATA   = 6'h34;
    localparam [5:0] ADDR_CHECKSUM     = 6'h38;
    localparam [5:0] ADDR_ERROR_STATUS = 6'h3c;

    reg aw_pending;
    reg [C_S_AXI_ADDR_WIDTH-1:0] awaddr_reg;
    reg w_pending;
    reg [C_S_AXI_DATA_WIDTH-1:0] wdata_reg;
    reg [(C_S_AXI_DATA_WIDTH/8)-1:0] wstrb_reg;

    reg [10:0] feature_index;
    reg [5:0]  weight_index;
    reg        bias_index;
    reg        logit_index;
    reg [4:0]  count_index;
    reg [31:0] vector_id;
    reg [31:0] checksum_reg;
    reg [31:0] error_status;
    reg        done_latched;
    reg        start_pulse;
    reg [2:0]  soft_reset_count;

    reg [11:0] feature_mem [0:1535];
    reg [11:0] weight_mem [0:63];
    reg [11:0] bias_mem [0:1];
    reg [17:0] logits_mem [0:1];
    reg [5:0]  count_mem [0:31];

    wire ap_rst = (~s_axi_aresetn) | (soft_reset_count != 3'd0);
    wire ap_done;
    wire ap_idle;
    wire ap_ready;
    wire busy = ~ap_idle;

    wire aw_hs = s_axi_awvalid && s_axi_awready;
    wire w_hs  = s_axi_wvalid && s_axi_wready;
    wire write_fire = !s_axi_bvalid &&
                      (aw_pending || aw_hs) &&
                      (w_pending || w_hs);
    wire [C_S_AXI_ADDR_WIDTH-1:0] write_addr = aw_hs ? s_axi_awaddr : awaddr_reg;
    wire [31:0] write_data = w_hs ? s_axi_wdata : wdata_reg;
    wire [3:0] write_strb = w_hs ? s_axi_wstrb : wstrb_reg;

    assign s_axi_awready = !aw_pending && !s_axi_bvalid && (soft_reset_count == 3'd0);
    assign s_axi_wready  = !w_pending && !s_axi_bvalid && (soft_reset_count == 3'd0);
    assign s_axi_arready = !s_axi_rvalid && (soft_reset_count == 3'd0);

    wire [10:0] feature_addr;
    wire feature_ce;
    reg [10:0] feature_addr_q;
    wire [11:0] feature_q = feature_mem[feature_addr_q];
    wire [5:0] weight0_addr;
    wire weight0_ce;
    reg [5:0] weight0_addr_q;
    wire [11:0] weight0_q = weight_mem[weight0_addr_q];
    wire [5:0] weight1_addr;
    wire weight1_ce;
    reg [5:0] weight1_addr_q;
    wire [11:0] weight1_q = weight_mem[weight1_addr_q];
    wire [0:0] bias_addr;
    wire bias_ce;
    reg bias_addr_q;
    wire [11:0] bias_q = bias_mem[bias_addr_q];
    wire [0:0] logits_addr;
    wire logits_ce;
    wire logits_we;
    wire [17:0] logits_d;
    wire [4:0] count_addr0;
    wire count_ce0;
    wire count_we0;
    wire [5:0] count_d0;
    wire [4:0] count_addr1;
    wire count_ce1;
    reg [4:0] count_addr0_q;
    reg [4:0] count_addr1_q;
    wire [5:0] count_q0 = count_mem[count_addr0_q];
    wire [5:0] count_q1 = count_mem[count_addr1_q];

    function automatic [31:0] read_data_for_addr(input [5:0] addr);
        reg [31:0] status_value;
        begin
            status_value = 32'd0;
            status_value[0] = ap_idle;
            status_value[1] = done_latched;
            status_value[2] = busy;
            status_value[3] = error_status[1];
            status_value[4] = ap_ready;
            case (addr)
                ADDR_STATUS:       read_data_for_addr = status_value;
                ADDR_VERSION:      read_data_for_addr = VERSION_VALUE;
                ADDR_VECTOR_ID:    read_data_for_addr = vector_id;
                ADDR_FEATURE_IDX:  read_data_for_addr = {{21{1'b0}}, feature_index};
                ADDR_WEIGHT_IDX:   read_data_for_addr = {{26{1'b0}}, weight_index};
                ADDR_BIAS_IDX:     read_data_for_addr = {{31{1'b0}}, bias_index};
                ADDR_LOGIT_IDX:    read_data_for_addr = {{31{1'b0}}, logit_index};
                ADDR_LOGIT_DATA:   read_data_for_addr = {{14{logits_mem[logit_index][17]}}, logits_mem[logit_index]};
                ADDR_COUNT_IDX:    read_data_for_addr = {{27{1'b0}}, count_index};
                ADDR_COUNT_DATA:   read_data_for_addr = {{26{1'b0}}, count_mem[count_index]};
                ADDR_CHECKSUM:     read_data_for_addr = checksum_reg;
                ADDR_ERROR_STATUS: read_data_for_addr = error_status;
                default:           read_data_for_addr = 32'd0;
            endcase
        end
    endfunction

    // Wrapper state, AXI write assembly, and synchronous ap_memory modeling.
    integer i;
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            aw_pending <= 1'b0;
            awaddr_reg <= {C_S_AXI_ADDR_WIDTH{1'b0}};
            w_pending <= 1'b0;
            wdata_reg <= 32'd0;
            wstrb_reg <= 4'd0;
            s_axi_bvalid <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            s_axi_rdata <= 32'd0;
            s_axi_rresp <= 2'b00;
            feature_index <= 11'd0;
            weight_index <= 6'd0;
            bias_index <= 1'd0;
            logit_index <= 1'd0;
            count_index <= 5'd0;
            vector_id <= 32'd0;
            checksum_reg <= 32'd0;
            error_status <= 32'd0;
            done_latched <= 1'b0;
            start_pulse <= 1'b0;
            soft_reset_count <= 3'd0;
            feature_addr_q <= 11'd0;
            weight0_addr_q <= 6'd0;
            weight1_addr_q <= 6'd0;
            bias_addr_q <= 1'd0;
            count_addr0_q <= 5'd0;
            count_addr1_q <= 5'd0;
            for (i = 0; i < 1536; i = i + 1) feature_mem[i] <= 12'd0;
            for (i = 0; i < 64; i = i + 1) weight_mem[i] <= 12'd0;
            for (i = 0; i < 2; i = i + 1) begin
                bias_mem[i] <= 12'd0;
                logits_mem[i] <= 18'd0;
            end
            for (i = 0; i < 32; i = i + 1) count_mem[i] <= 6'd0;
        end else begin
            if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 1'b0;
            if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 1'b0;
            if (aw_hs) begin
                aw_pending <= 1'b1;
                awaddr_reg <= s_axi_awaddr;
            end
            if (w_hs) begin
                w_pending <= 1'b1;
                wdata_reg <= s_axi_wdata;
                wstrb_reg <= s_axi_wstrb;
            end
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rdata <= read_data_for_addr(s_axi_araddr[5:0]);
                s_axi_rresp <= (s_axi_araddr[5:0] <= ADDR_ERROR_STATUS) ? 2'b00 : 2'b10;
            end

            // The pending pulse gives the HLS core one complete active-high
            // reset cycle after a software reset write is acknowledged.
            if (soft_reset_count != 3'd0) begin
                soft_reset_count <= soft_reset_count - 3'd1;
                feature_index <= 11'd0;
                weight_index <= 6'd0;
                bias_index <= 1'd0;
                logit_index <= 1'd0;
                count_index <= 5'd0;
                checksum_reg <= 32'd0;
                error_status <= 32'd0;
                done_latched <= 1'b0;
                start_pulse <= 1'b0;
                feature_addr_q <= 11'd0;
                weight0_addr_q <= 6'd0;
                weight1_addr_q <= 6'd0;
                bias_addr_q <= 1'd0;
                count_addr0_q <= 5'd0;
                count_addr1_q <= 5'd0;
                for (i = 0; i < 2; i = i + 1) begin
                    bias_mem[i] <= 12'd0;
                    logits_mem[i] <= 18'd0;
                end
                for (i = 0; i < 32; i = i + 1) count_mem[i] <= 6'd0;
            end else begin
                start_pulse <= 1'b0;
                feature_addr_q <= feature_addr;
                weight0_addr_q <= weight0_addr;
                weight1_addr_q <= weight1_addr;
                bias_addr_q <= bias_addr;
                count_addr0_q <= count_addr0;
                count_addr1_q <= count_addr1;

                if (ap_done) begin
                    done_latched <= 1'b1;
                end

                if (logits_ce && logits_we)
                    logits_mem[logits_addr] <= logits_d;
                if (count_ce0 && count_we0)
                    count_mem[count_addr0] <= count_d0;

                if (write_fire) begin
                    aw_pending <= 1'b0;
                    w_pending <= 1'b0;
                    s_axi_bvalid <= 1'b1;
                    s_axi_bresp <= 2'b00;
                    if (write_addr > ADDR_ERROR_STATUS)
                        s_axi_bresp <= 2'b10;

                    case (write_addr[5:0])
                        ADDR_CONTROL: begin
                            if (write_strb[0]) begin
                                if (write_data[1]) begin
                                    soft_reset_count <= 3'd4;
                                    if (write_data[0]) error_status[2] <= 1'b1;
                                end else if (write_data[0]) begin
                                    if (ap_idle) begin
                                        start_pulse <= 1'b1;
                                        done_latched <= 1'b0;
                                    end else begin
                                        error_status[2] <= 1'b1;
                                    end
                                end
                                if (write_data[2]) done_latched <= 1'b0;
                            end
                        end
                        ADDR_VECTOR_ID: begin
                            if (write_strb[0]) vector_id <= write_data;
                        end
                        ADDR_FEATURE_IDX: begin
                            if (write_strb[0]) begin
                                if (write_data > 32'd1535) error_status[0] <= 1'b1;
                                else feature_index <= write_data[10:0];
                            end
                        end
                        ADDR_FEATURE_DATA: begin
                            if (write_strb[0]) begin
                                if (busy) error_status[1] <= 1'b1;
                                else if (feature_index <= 11'd1535) begin
                                    feature_mem[feature_index] <= write_data[11:0];
                                    checksum_reg <= checksum_reg ^ {20'd0, write_data[11:0]};
                                end else error_status[0] <= 1'b1;
                            end
                        end
                        ADDR_WEIGHT_IDX: begin
                            if (write_strb[0]) begin
                                if (write_data > 32'd63) error_status[0] <= 1'b1;
                                else weight_index <= write_data[5:0];
                            end
                        end
                        ADDR_WEIGHT_DATA: begin
                            if (write_strb[0]) begin
                                if (busy) error_status[1] <= 1'b1;
                                else begin
                                    weight_mem[weight_index] <= write_data[11:0];
                                    checksum_reg <= checksum_reg ^ {20'd0, write_data[11:0]};
                                end
                            end
                        end
                        ADDR_BIAS_IDX: begin
                            if (write_strb[0]) begin
                                if (write_data > 32'd1) error_status[0] <= 1'b1;
                                else bias_index <= write_data[0];
                            end
                        end
                        ADDR_BIAS_DATA: begin
                            if (write_strb[0]) begin
                                if (busy) error_status[1] <= 1'b1;
                                else begin
                                    bias_mem[bias_index] <= write_data[11:0];
                                    checksum_reg <= checksum_reg ^ {20'd0, write_data[11:0]};
                                end
                            end
                        end
                        ADDR_LOGIT_IDX: begin
                            if (write_strb[0]) begin
                                if (write_data > 32'd1) error_status[0] <= 1'b1;
                                else logit_index <= write_data[0];
                            end
                        end
                        ADDR_COUNT_IDX: begin
                            if (write_strb[0]) begin
                                if (write_data > 32'd31) error_status[0] <= 1'b1;
                                else count_index <= write_data[4:0];
                            end
                        end
                        ADDR_ERROR_STATUS: begin
                            if (write_strb[0]) begin
                                error_status <= error_status & ~write_data;
                            end
                        end
                        default: begin
                            s_axi_bresp <= 2'b10;
                            error_status[0] <= 1'b1;
                        end
                    endcase
                end
            end
        end
    end

    // The HLS-generated memory ports are synchronous-read. The address is
    // captured above and the addressed word is presented for the next edge.
    hybrid_lif_head_q12_6 u_hls (
        .ap_clk(s_axi_aclk),
        .ap_rst(ap_rst),
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
