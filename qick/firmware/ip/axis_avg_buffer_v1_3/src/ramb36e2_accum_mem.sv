// Banked accumulated IQ memory for axis_avg_buffer v1.3.
//
// Addressing:
//   addr_low = addr_i[9:0]
//   bank_sel = addr_i[N-1:10] when N > 10, otherwise bank 0
//
// For B=16 each accumulated word is 128 bits:
//   {Q_accum[63:0], I_accum[63:0]}
//
// Each 1024-deep bank is built from ceil(ACC_WORD_WIDTH/36) RAMB36E2
// width slices. The accumulation adders live inside each bank, after that
// bank's local RAM output. There is no shared wide add after a bank mux.
//
// Define SIM_MODEL for behavioral simulation. Without SIM_MODEL, each slice
// instantiates a RAMB36E2 primitive in 1024x36 simple dual-port form.

module ramb36e2_1k36_sdp (
    input  logic        clk,
    input  logic        rd_en_i,
    input  logic [9:0]  rd_addr_i,
    output logic [35:0] rd_data_o,
    input  logic        wr_en_i,
    input  logic [9:0]  wr_addr_i,
    input  logic [35:0] wr_data_i
);

`ifdef SIM_MODEL
    (* ram_style = "block" *) logic [35:0] mem [0:1023];

    always_ff @(posedge clk) begin
        if (rd_en_i)
            rd_data_o <= mem[rd_addr_i];
        if (wr_en_i)
            mem[wr_addr_i] <= wr_data_i;
    end
`else
    wire [31:0] doa;
    wire [3:0]  dopa;
    wire [31:0] dob_unused;
    wire [3:0]  dopb_unused;

    assign rd_data_o = {dopa, doa};

    RAMB36E2 #(
        .CASCADE_ORDER_A("NONE"),
        .CASCADE_ORDER_B("NONE"),
        .CLOCK_DOMAINS("COMMON"),
        .DOA_REG(0),
        .DOB_REG(0),
        .EN_ECC_PIPE("FALSE"),
        .EN_ECC_READ("FALSE"),
        .EN_ECC_WRITE("FALSE"),
        .INIT_A(36'h000000000),
        .INIT_B(36'h000000000),
        .READ_WIDTH_A(36),
        .READ_WIDTH_B(36),
        .RSTREG_PRIORITY_A("RSTREG"),
        .RSTREG_PRIORITY_B("RSTREG"),
        .SIM_COLLISION_CHECK("ALL"),
        .SLEEP_ASYNC("FALSE"),
        .WRITE_MODE_A("READ_FIRST"),
        .WRITE_MODE_B("READ_FIRST"),
        .WRITE_WIDTH_A(36),
        .WRITE_WIDTH_B(36)
    ) ramb36e2_i (
        .CASDOUTA(),
        .CASDOUTB(),
        .CASDOUTPA(),
        .CASDOUTPB(),
        .DBITERR(),
        .DOUTADOUT(doa),
        .DOUTBDOUT(dob_unused),
        .DOUTPADOUTP(dopa),
        .DOUTPBDOUTP(dopb_unused),
        .ECCPARITY(),
        .RDADDRECC(),
        .SBITERR(),
        .ADDRARDADDR({rd_addr_i, 5'b00000}),
        .ADDRBWRADDR({wr_addr_i, 5'b00000}),
        .ADDRENA(1'b1),
        .CASDIMUXA(1'b0),
        .CASDIMUXB(1'b0),
        .CASDOMUXA(1'b0),
        .CASDOMUXB(1'b0),
        .CASDOMUXEN_A(1'b0),
        .CASDOMUXEN_B(1'b0),
        .CASOREGIMUXA(1'b0),
        .CASOREGIMUXB(1'b0),
        .CASOREGIMUXEN_A(1'b0),
        .CASOREGIMUXEN_B(1'b0),
        .CLKARDCLK(clk),
        .CLKBWRCLK(clk),
        .DINADIN(32'h00000000),
        .DINBDIN(wr_data_i[31:0]),
        .DINPADINP(4'h0),
        .DINPBDINP(wr_data_i[35:32]),
        .ENARDEN(rd_en_i),
        .ENBWREN(wr_en_i),
        .INJECTDBITERR(1'b0),
        .INJECTSBITERR(1'b0),
        .REGCEAREGCE(1'b1),
        .REGCEB(1'b1),
        .RSTRAMARSTRAM(1'b0),
        .RSTRAMB(1'b0),
        .RSTREGARSTREG(1'b0),
        .RSTREGB(1'b0),
        .SLEEP(1'b0),
        .WEA(4'b0000),
        .WEBWE({8{wr_en_i}})
    );
`endif

endmodule

module ramb36e2_accum_bank #(
    parameter integer B = 16,
    parameter integer ACC_CH_WIDTH = 4 * B,
    parameter integer ACC_WORD_WIDTH = 8 * B,
    parameter integer SLICE_WIDTH = 36
) (
    input  logic                         clk,
    input  logic                         rstn,
    input  logic                         valid_i,
    input  logic [1:0]                   op_i,
    input  logic [9:0]                   addr_i,
    input  logic [ACC_WORD_WIDTH-1:0]    delta_i,
    input  logic [31:0]                  full_addr_i,
    output logic                         read_valid_o,
    output logic [31:0]                  read_addr_o,
    output logic [ACC_WORD_WIDTH-1:0]    read_data_o
);

    localparam logic [1:0] OP_CLEAR  = 2'd0;
    localparam logic [1:0] OP_UPDATE = 2'd1;
    localparam logic [1:0] OP_READ   = 2'd2;
    localparam integer NUM_SLICES = (ACC_WORD_WIDTH + SLICE_WIDTH - 1) / SLICE_WIDTH;
    localparam integer PAD_WIDTH = NUM_SLICES * SLICE_WIDTH;

    logic                         rd_en;
    logic [9:0]                   rd_addr;
    logic                         wr_en;
    logic [9:0]                   wr_addr;
    logic [PAD_WIDTH-1:0]         wr_data_pad;
    logic [PAD_WIDTH-1:0]         rd_data_pad;
    logic [ACC_WORD_WIDTH-1:0]    rd_word;

    logic                         stage_valid_r;
    logic                         stage_update_r;
    logic                         stage_read_r;
    logic [9:0]                   stage_addr_r;
    logic [31:0]                  stage_full_addr_r;
    logic [ACC_WORD_WIDTH-1:0]    stage_delta_r;

    wire signed [ACC_CH_WIDTH-1:0] old_i_s =
        $signed(rd_word[ACC_CH_WIDTH-1:0]);
    wire signed [ACC_CH_WIDTH-1:0] old_q_s =
        $signed(rd_word[ACC_WORD_WIDTH-1:ACC_CH_WIDTH]);
    wire signed [ACC_CH_WIDTH-1:0] delta_i_s =
        $signed(stage_delta_r[ACC_CH_WIDTH-1:0]);
    wire signed [ACC_CH_WIDTH-1:0] delta_q_s =
        $signed(stage_delta_r[ACC_WORD_WIDTH-1:ACC_CH_WIDTH]);

    (* use_dsp = "yes" *) logic signed [ACC_CH_WIDTH-1:0] sum_i_dsp;
    (* use_dsp = "yes" *) logic signed [ACC_CH_WIDTH-1:0] sum_q_dsp;
    logic [ACC_WORD_WIDTH-1:0] sum_word;

    assign rd_word = rd_data_pad[ACC_WORD_WIDTH-1:0];

    always_comb begin
        sum_i_dsp = old_i_s + delta_i_s;
        sum_q_dsp = old_q_s + delta_q_s;
        sum_word  = {sum_q_dsp, sum_i_dsp};

        rd_en      = valid_i && (op_i == OP_UPDATE || op_i == OP_READ);
        rd_addr    = addr_i;
        wr_en      = 1'b0;
        wr_addr    = addr_i;
        wr_data_pad = '0;

        if (valid_i && op_i == OP_CLEAR) begin
            wr_en       = 1'b1;
            wr_addr     = addr_i;
            wr_data_pad = '0;
        end
        else if (stage_valid_r && stage_update_r) begin
            wr_en       = 1'b1;
            wr_addr     = stage_addr_r;
            wr_data_pad = {{(PAD_WIDTH-ACC_WORD_WIDTH){1'b0}}, sum_word};
        end
    end

    genvar slice_idx;
    generate
        for (slice_idx = 0; slice_idx < NUM_SLICES; slice_idx = slice_idx + 1) begin : gen_slices
            localparam int unsigned LSB = slice_idx * SLICE_WIDTH;
            ramb36e2_1k36_sdp slice_i (
                .clk       (clk),
                .rd_en_i   (rd_en),
                .rd_addr_i (rd_addr),
                .rd_data_o (rd_data_pad[LSB +: SLICE_WIDTH]),
                .wr_en_i   (wr_en),
                .wr_addr_i (wr_addr),
                .wr_data_i (wr_data_pad[LSB +: SLICE_WIDTH])
            );
        end
    endgenerate

    always_ff @(posedge clk) begin
        if (!rstn) begin
            stage_valid_r     <= 1'b0;
            stage_update_r    <= 1'b0;
            stage_read_r      <= 1'b0;
            stage_addr_r      <= '0;
            stage_full_addr_r <= '0;
            stage_delta_r     <= '0;
            read_valid_o      <= 1'b0;
            read_addr_o       <= '0;
            read_data_o       <= '0;
        end
        else begin
            stage_valid_r     <= valid_i && (op_i == OP_UPDATE || op_i == OP_READ);
            stage_update_r    <= valid_i && (op_i == OP_UPDATE);
            stage_read_r      <= valid_i && (op_i == OP_READ);
            stage_addr_r      <= addr_i;
            stage_full_addr_r <= full_addr_i;
            stage_delta_r     <= delta_i;

            read_valid_o <= stage_valid_r && stage_read_r;
            read_addr_o  <= stage_full_addr_r;
            read_data_o  <= rd_word;
        end
    end

endmodule

module ramb36e2_accum_mem #(
    parameter integer N = 10,
    parameter integer B = 16,
    parameter integer ACC_CH_WIDTH = 4 * B,
    parameter integer ACC_WORD_WIDTH = 8 * B,
    parameter integer LOCAL_ADDR_BITS = 10,
    parameter integer SLICE_WIDTH = 36
) (
    input  logic                         clk,
    input  logic                         rstn,
    input  logic                         valid_i,
    input  logic [1:0]                   op_i,
    input  logic [N-1:0]                 addr_i,
    input  logic [ACC_WORD_WIDTH-1:0]    delta_i,
    output logic                         read_valid_o,
    output logic [N-1:0]                 read_addr_o,
    output logic [ACC_WORD_WIDTH-1:0]    read_data_o
);

    localparam integer NUM_BANKS = (N > LOCAL_ADDR_BITS) ? (1 << (N - LOCAL_ADDR_BITS)) : 1;
    localparam integer PIPE_STAGES = (N > LOCAL_ADDR_BITS) ? (N - LOCAL_ADDR_BITS) : 0;
    localparam integer NUM_SLICES = (ACC_WORD_WIDTH + SLICE_WIDTH - 1) / SLICE_WIDTH;
    localparam integer BANK_SEL_BITS = (N > LOCAL_ADDR_BITS) ? (N - LOCAL_ADDR_BITS) : 1;
    localparam integer ADDR_PAD_BITS = (N < 32) ? (32 - N) : 1;

    typedef struct packed {
        logic                         valid;
        logic [1:0]                   op;
        logic [LOCAL_ADDR_BITS-1:0]   addr_low;
        logic [BANK_SEL_BITS-1:0]     bank_sel;
        logic [N-1:0]                 full_addr;
        logic [ACC_WORD_WIDTH-1:0]    delta;
    } req_t;

    req_t req_pipe [0:PIPE_STAGES];
    req_t req_in;
    req_t req_out;

    function automatic [LOCAL_ADDR_BITS-1:0] make_addr_low(input logic [N-1:0] addr);
        begin
            make_addr_low = '0;
            for (int bit_idx = 0; bit_idx < LOCAL_ADDR_BITS; bit_idx = bit_idx + 1) begin
                if (bit_idx < N)
                    make_addr_low[bit_idx] = addr[bit_idx];
            end
        end
    endfunction

    function automatic [BANK_SEL_BITS-1:0] make_bank_sel(input logic [N-1:0] addr);
        begin
            make_bank_sel = '0;
            for (int bit_idx = 0; bit_idx < BANK_SEL_BITS; bit_idx = bit_idx + 1) begin
                if ((bit_idx + LOCAL_ADDR_BITS) < N)
                    make_bank_sel[bit_idx] = addr[bit_idx + LOCAL_ADDR_BITS];
            end
        end
    endfunction

    always_comb begin
        req_in.valid    = valid_i;
        req_in.op       = op_i;
        req_in.addr_low = make_addr_low(addr_i);
        req_in.full_addr = addr_i;
        req_in.delta    = delta_i;
        req_in.bank_sel = make_bank_sel(addr_i);
    end

    integer pipe_idx;
    always_ff @(posedge clk) begin
        if (!rstn) begin
            for (pipe_idx = 0; pipe_idx <= PIPE_STAGES; pipe_idx = pipe_idx + 1)
                req_pipe[pipe_idx] <= '0;
        end
        else begin
            req_pipe[0] <= req_in;
            for (pipe_idx = 1; pipe_idx <= PIPE_STAGES; pipe_idx = pipe_idx + 1)
                req_pipe[pipe_idx] <= req_pipe[pipe_idx-1];
        end
    end

    always_comb begin
        req_out = req_pipe[PIPE_STAGES];
    end

    logic [NUM_BANKS-1:0] bank_read_valid;
    logic [NUM_BANKS-1:0][31:0] bank_read_addr;
    logic [NUM_BANKS-1:0][ACC_WORD_WIDTH-1:0] bank_read_data;

    genvar bank_idx;
    generate
        for (bank_idx = 0; bank_idx < NUM_BANKS; bank_idx = bank_idx + 1) begin : gen_banks
            localparam logic [BANK_SEL_BITS-1:0] BANK_ID = bank_idx;
            wire bank_hit = req_out.valid && (req_out.bank_sel == BANK_ID);

            ramb36e2_accum_bank #(
                .B              (B),
                .ACC_CH_WIDTH   (ACC_CH_WIDTH),
                .ACC_WORD_WIDTH (ACC_WORD_WIDTH),
                .SLICE_WIDTH    (SLICE_WIDTH)
            ) bank_i (
                .clk          (clk),
                .rstn         (rstn),
                .valid_i      (bank_hit),
                .op_i         (req_out.op),
                .addr_i       (req_out.addr_low),
                .delta_i      (req_out.delta),
                .full_addr_i  ({{ADDR_PAD_BITS{1'b0}}, req_out.full_addr}),
                .read_valid_o (bank_read_valid[bank_idx]),
                .read_addr_o  (bank_read_addr[bank_idx]),
                .read_data_o  (bank_read_data[bank_idx])
            );
        end
    endgenerate

    integer bank_mux_idx;
    always_comb begin
        read_valid_o = 1'b0;
        read_addr_o  = '0;
        read_data_o  = '0;
        for (bank_mux_idx = 0; bank_mux_idx < NUM_BANKS; bank_mux_idx = bank_mux_idx + 1) begin
            if (bank_read_valid[bank_mux_idx]) begin
                read_valid_o = 1'b1;
                read_addr_o  = bank_read_addr[bank_mux_idx][N-1:0];
                read_data_o  = bank_read_data[bank_mux_idx];
            end
        end
    end

endmodule
