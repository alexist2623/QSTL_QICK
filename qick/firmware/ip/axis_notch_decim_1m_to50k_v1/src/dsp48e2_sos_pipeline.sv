// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

// DSP48E2 helpers for the time-multiplexed SOS engine.
//
// The target is ZCU216 (Zynq UltraScale+), whose arithmetic primitive is
// DSP48E2.  DSP58/DSP48E3 primitives belong to other device families.

(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module dsp48e2_mul17x17_pipe (
    input  wire                 clk,
    input  wire                 rstn,
    input  wire                 valid_i,
    input  wire signed [16:0]   a_i,
    input  wire signed [16:0]   b_i,
    output wire                 valid_o,
    output wire signed [47:0]   product_o
);

    logic [2:0] valid_pipe_r;

    always_ff @(posedge clk) begin
        if (!rstn)
            valid_pipe_r <= '0;
        else begin
            valid_pipe_r[0] <= valid_i;
            valid_pipe_r[1] <= valid_pipe_r[0];
            valid_pipe_r[2] <= valid_pipe_r[1];
        end
    end

    assign valid_o = valid_pipe_r[2];

`ifdef SIM_MODEL
    logic signed [47:0] product_pipe_r [0:2];

    always_ff @(posedge clk) begin
        if (!rstn) begin
            product_pipe_r[0] <= '0;
            product_pipe_r[1] <= '0;
            product_pipe_r[2] <= '0;
        end else begin
            product_pipe_r[0] <= a_i * b_i;
            product_pipe_r[1] <= product_pipe_r[0];
            product_pipe_r[2] <= product_pipe_r[1];
        end
    end

    assign product_o = product_pipe_r[2];
`else
    wire signed [29:0] a_ext = {{13{a_i[16]}}, a_i};
    wire signed [17:0] b_ext = {{1{b_i[16]}}, b_i};
    wire [47:0] p_out;

    // Three-cycle datapath latency: A/B input register, M register, P register.
    // OPMODE 000110101 selects P = C + A*B, with C tied to zero.
    DSP48E2 #(
        .ACASCREG(1),
        .ADREG(0),
        .ALUMODEREG(0),
        .AREG(1),
        .A_INPUT("DIRECT"),
        .BCASCREG(1),
        .BREG(1),
        .B_INPUT("DIRECT"),
        .CARRYINREG(0),
        .CARRYINSELREG(0),
        .CREG(0),
        .DREG(0),
        .INMODEREG(0),
        .MREG(1),
        .OPMODEREG(0),
        .PREG(1),
        .USE_MULT("MULTIPLY"),
        .USE_SIMD("ONE48")
    ) dsp48e2_i (
        .ACOUT(),
        .BCOUT(),
        .CARRYCASCOUT(),
        .CARRYOUT(),
        .MULTSIGNOUT(),
        .OVERFLOW(),
        .P(p_out),
        .PATTERNBDETECT(),
        .PATTERNDETECT(),
        .PCOUT(),
        .UNDERFLOW(),
        .XOROUT(),
        .A(a_ext),
        .ACIN(30'b0),
        .ALUMODE(4'b0000),
        .B(b_ext),
        .BCIN(18'b0),
        .C(48'b0),
        .CARRYCASCIN(1'b0),
        .CARRYIN(1'b0),
        .CARRYINSEL(3'b000),
        .CEA1(1'b0),
        .CEA2(1'b1),
        .CEAD(1'b0),
        .CEALUMODE(1'b0),
        .CEB1(1'b0),
        .CEB2(1'b1),
        .CEC(1'b0),
        .CECARRYIN(1'b0),
        .CECTRL(1'b0),
        .CED(1'b0),
        .CEINMODE(1'b0),
        .CEM(1'b1),
        .CEP(1'b1),
        .CLK(clk),
        .D(27'b0),
        .INMODE(5'b00000),
        .MULTSIGNIN(1'b0),
        .OPMODE(9'b000110101),
        .PCIN(48'b0),
        .RSTA(~rstn),
        .RSTALLCARRYIN(~rstn),
        .RSTALUMODE(~rstn),
        .RSTB(~rstn),
        .RSTC(~rstn),
        .RSTCTRL(~rstn),
        .RSTD(~rstn),
        .RSTINMODE(~rstn),
        .RSTM(~rstn),
        .RSTP(~rstn)
    );

    assign product_o = p_out;
`endif

endmodule


(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module dsp48e2_add47_pipe (
    input  wire                 clk,
    input  wire                 rstn,
    input  wire                 valid_i,
    input  wire [46:0]          a_i,
    input  wire [46:0]          b_i,
    input  wire                 carry_i,
    output wire                 valid_o,
    output wire [46:0]          sum_o,
    output wire                 carry_o
);

    wire [47:0] a_ext = {1'b0, a_i};
    wire [47:0] b_ext = {1'b0, b_i};

    logic [1:0] valid_pipe_r;

    always_ff @(posedge clk) begin
        if (!rstn)
            valid_pipe_r <= '0;
        else begin
            valid_pipe_r[0] <= valid_i;
            valid_pipe_r[1] <= valid_pipe_r[0];
        end
    end

    assign valid_o = valid_pipe_r[1];

`ifdef SIM_MODEL
    logic [47:0] p_pipe_r [0:1];

    always_ff @(posedge clk) begin
        if (!rstn) begin
            p_pipe_r[0] <= '0;
            p_pipe_r[1] <= '0;
        end else begin
            p_pipe_r[0] <= a_ext + b_ext + carry_i;
            p_pipe_r[1] <= p_pipe_r[0];
        end
    end

    assign sum_o   = p_pipe_r[1][46:0];
    assign carry_o = p_pipe_r[1][47];
`else
    wire [47:0] p_out;

    // Two-cycle DSP ALU stage: registered A/B/C/carry inputs followed by the
    // registered P output. Only 47 payload bits are used, so P[47] becomes
    // the registered carry forwarded to the next 68-bit chunk.
    DSP48E2 #(
        .ACASCREG(1),
        .ADREG(0),
        .ALUMODEREG(0),
        .AREG(1),
        .A_INPUT("DIRECT"),
        .BCASCREG(1),
        .BREG(1),
        .B_INPUT("DIRECT"),
        .CARRYINREG(1),
        .CARRYINSELREG(0),
        .CREG(1),
        .DREG(0),
        .INMODEREG(0),
        .MREG(0),
        .OPMODEREG(0),
        .PREG(1),
        .USE_MULT("NONE"),
        .USE_SIMD("ONE48")
    ) dsp48e2_i (
        .ACOUT(),
        .BCOUT(),
        .CARRYCASCOUT(),
        .CARRYOUT(),
        .MULTSIGNOUT(),
        .OVERFLOW(),
        .P(p_out),
        .PATTERNBDETECT(),
        .PATTERNDETECT(),
        .PCOUT(),
        .UNDERFLOW(),
        .XOROUT(),
        .A(a_ext[47:18]),
        .ACIN(30'b0),
        .ALUMODE(4'b0000),
        .B(a_ext[17:0]),
        .BCIN(18'b0),
        .C(b_ext),
        .CARRYCASCIN(1'b0),
        .CARRYIN(carry_i),
        .CARRYINSEL(3'b000),
        .CEA1(1'b0),
        .CEA2(1'b1),
        .CEAD(1'b0),
        .CEALUMODE(1'b0),
        .CEB1(1'b0),
        .CEB2(1'b1),
        .CEC(1'b1),
        .CECARRYIN(1'b1),
        .CECTRL(1'b0),
        .CED(1'b0),
        .CEINMODE(1'b0),
        .CEM(1'b0),
        .CEP(1'b1),
        .CLK(clk),
        .D(27'b0),
        .INMODE(5'b00000),
        .MULTSIGNIN(1'b0),
        .OPMODE(9'b000110011),
        .PCIN(48'b0),
        .RSTA(~rstn),
        .RSTALLCARRYIN(~rstn),
        .RSTALUMODE(~rstn),
        .RSTB(~rstn),
        .RSTC(~rstn),
        .RSTCTRL(~rstn),
        .RSTD(~rstn),
        .RSTINMODE(~rstn),
        .RSTM(~rstn),
        .RSTP(~rstn)
    );

    assign sum_o   = p_out[46:0];
    assign carry_o = p_out[47];
`endif

endmodule


(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module dsp48e2_add68_chunked_pipe (
    input  wire                 clk,
    input  wire                 rstn,
    input  wire                 valid_i,
    input  wire [67:0]          a_i,
    input  wire [67:0]          b_i,
    input  wire                 carry_i,
    output wire                 valid_o,
    output wire [67:0]          sum_o
);

    logic [20:0] high_a_r;
    logic [20:0] high_b_r;
    logic [46:0] low_sum_r;
    wire [46:0] low_sum;
    wire low_carry;
    wire low_valid;
    wire [46:0] high_sum;
    wire high_unused_carry;
    wire high_valid;

    // First chunk pipeline: add bits [46:0] and register the carry.
    dsp48e2_add47_pipe low_add_i (
        .clk(clk),
        .rstn(rstn),
        .valid_i(valid_i),
        .a_i(a_i[46:0]),
        .b_i(b_i[46:0]),
        .carry_i(carry_i),
        .valid_o(low_valid),
        .sum_o(low_sum),
        .carry_o(low_carry)
    );

    always_ff @(posedge clk) begin
        if (!rstn) begin
            high_a_r <= '0;
            high_b_r <= '0;
            low_sum_r <= '0;
        end else begin
            if (valid_i) begin
                high_a_r <= a_i[67:47];
                high_b_r <= b_i[67:47];
            end
            if (low_valid)
                low_sum_r <= low_sum;
        end
    end

    // Second chunk pipeline: add bits [67:47] with the registered carry.
    dsp48e2_add47_pipe high_add_i (
        .clk(clk),
        .rstn(rstn),
        .valid_i(low_valid),
        .a_i({26'b0, high_a_r}),
        .b_i({26'b0, high_b_r}),
        .carry_i(low_carry),
        .valid_o(high_valid),
        .sum_o(high_sum),
        .carry_o(high_unused_carry)
    );

    assign valid_o = high_valid;
    assign sum_o   = {high_sum[20:0], low_sum_r};

endmodule


(* keep_hierarchy = "yes", DONT_TOUCH = "true" *)
module dsp48e2_mul32x32_pipe (
    input  wire                 clk,
    input  wire                 rstn,
    input  wire                 valid_i,
    input  wire signed [31:0]   a_i,
    input  wire signed [31:0]   b_i,
    output wire                 valid_o,
    output wire signed [67:0]   product_o
);

    wire signed [16:0] a_lo = $signed({1'b0, a_i[15:0]});
    wire signed [16:0] a_hi = $signed({a_i[31], a_i[31:16]});
    wire signed [16:0] b_lo = $signed({1'b0, b_i[15:0]});
    wire signed [16:0] b_hi = $signed({b_i[31], b_i[31:16]});

    wire signed [47:0] product_ll;
    wire signed [47:0] product_lh;
    wire signed [47:0] product_hl;
    wire signed [47:0] product_hh;
    wire partial_valid;
    wire unused_valid_lh;
    wire unused_valid_hl;
    wire unused_valid_hh;

    dsp48e2_mul17x17_pipe mul_ll_i (
        .clk(clk), .rstn(rstn), .valid_i(valid_i),
        .a_i(a_lo), .b_i(b_lo), .valid_o(partial_valid), .product_o(product_ll)
    );
    dsp48e2_mul17x17_pipe mul_lh_i (
        .clk(clk), .rstn(rstn), .valid_i(valid_i),
        .a_i(a_lo), .b_i(b_hi), .valid_o(unused_valid_lh), .product_o(product_lh)
    );
    dsp48e2_mul17x17_pipe mul_hl_i (
        .clk(clk), .rstn(rstn), .valid_i(valid_i),
        .a_i(a_hi), .b_i(b_lo), .valid_o(unused_valid_hl), .product_o(product_hl)
    );
    dsp48e2_mul17x17_pipe mul_hh_i (
        .clk(clk), .rstn(rstn), .valid_i(valid_i),
        .a_i(a_hi), .b_i(b_hi), .valid_o(unused_valid_hh), .product_o(product_hh)
    );

    wire [67:0] term_ll = {{20{product_ll[47]}}, product_ll};
    wire [67:0] term_lh = $unsigned($signed({{20{product_lh[47]}}, product_lh}) <<< 16);
    wire [67:0] term_hl = $unsigned($signed({{20{product_hl[47]}}, product_hl}) <<< 16);
    wire [67:0] term_hh = $unsigned($signed({{20{product_hh[47]}}, product_hh}) <<< 32);

    wire [67:0] partial_sum_0;
    wire [67:0] partial_sum_1;
    wire partial_sum_valid;
    wire unused_partial_sum_valid;

    dsp48e2_add68_chunked_pipe partial_add_0_i (
        .clk(clk), .rstn(rstn), .valid_i(partial_valid),
        .a_i(term_ll), .b_i(term_lh), .carry_i(1'b0),
        .valid_o(partial_sum_valid), .sum_o(partial_sum_0)
    );
    dsp48e2_add68_chunked_pipe partial_add_1_i (
        .clk(clk), .rstn(rstn), .valid_i(partial_valid),
        .a_i(term_hl), .b_i(term_hh), .carry_i(1'b0),
        .valid_o(unused_partial_sum_valid), .sum_o(partial_sum_1)
    );

    wire [67:0] final_sum;
    dsp48e2_add68_chunked_pipe final_add_i (
        .clk(clk), .rstn(rstn), .valid_i(partial_sum_valid),
        .a_i(partial_sum_0), .b_i(partial_sum_1), .carry_i(1'b0),
        .valid_o(valid_o), .sum_o(final_sum)
    );

    assign product_o = $signed(final_sum);

endmodule
