// Power-of-two time-domain boxcar average for packed signed I/Q samples.
//
// K=0 passes one input sample to one output sample.
// K>0 averages 2**K consecutive input samples and emits one decimated sample.
// The arithmetic right shift rounds toward negative infinity.
module avg_decimator_iq #(
    parameter int unsigned B = 16,
    parameter int unsigned MAX_AVG_DECIM_LOG2 = 6,
    parameter int unsigned ACC_WIDTH = B + MAX_AVG_DECIM_LOG2 + 1
) (
    input  wire                 rstn,
    input  wire                 clk,
    input  wire                 clear_i,
    input  wire [3:0]           decim_log2_i,
    input  wire                 din_valid_i,
    input  wire [2*B-1:0]       din_i,
    output logic                dout_valid_o,
    output logic [2*B-1:0]      dout_i
);

wire signed [B-1:0] din_i_s = din_i[B-1:0];
wire signed [B-1:0] din_q_s = din_i[2*B-1:B];

logic signed [ACC_WIDTH-1:0] acc_i_r;
logic signed [ACC_WIDTH-1:0] acc_q_r;
logic [MAX_AVG_DECIM_LOG2:0] sample_cnt_r;

logic [3:0] effective_k;
logic [MAX_AVG_DECIM_LOG2:0] group_last;
logic signed [ACC_WIDTH-1:0] next_sum_i;
logic signed [ACC_WIDTH-1:0] next_sum_q;
logic signed [ACC_WIDTH-1:0] avg_i_ext;
logic signed [ACC_WIDTH-1:0] avg_q_ext;

function automatic [3:0] clamp_decim_log2(input [3:0] decim_log2);
    if (decim_log2 > MAX_AVG_DECIM_LOG2)
        clamp_decim_log2 = MAX_AVG_DECIM_LOG2;
    else
        clamp_decim_log2 = decim_log2;
endfunction

always_comb begin
    effective_k = clamp_decim_log2(decim_log2_i);
    group_last = ({{MAX_AVG_DECIM_LOG2{1'b0}}, 1'b1} << effective_k) - 1'b1;
    next_sum_i = acc_i_r + {{(ACC_WIDTH-B){din_i_s[B-1]}}, din_i_s};
    next_sum_q = acc_q_r + {{(ACC_WIDTH-B){din_q_s[B-1]}}, din_q_s};
    avg_i_ext = next_sum_i >>> effective_k;
    avg_q_ext = next_sum_q >>> effective_k;
end

always_ff @(posedge clk) begin
    if (!rstn) begin
        acc_i_r      <= '0;
        acc_q_r      <= '0;
        sample_cnt_r <= '0;
        dout_valid_o <= 1'b0;
        dout_i       <= '0;
    end
    else begin
        dout_valid_o <= 1'b0;

        if (clear_i) begin
            acc_i_r      <= '0;
            acc_q_r      <= '0;
            sample_cnt_r <= '0;
        end
        else if (din_valid_i) begin
            if (sample_cnt_r == group_last) begin
                dout_valid_o <= 1'b1;
                dout_i       <= {avg_q_ext[B-1:0], avg_i_ext[B-1:0]};
                acc_i_r      <= '0;
                acc_q_r      <= '0;
                sample_cnt_r <= '0;
            end
            else begin
                acc_i_r      <= next_sum_i;
                acc_q_r      <= next_sum_q;
                sample_cnt_r <= sample_cnt_r + 1'b1;
            end
        end
    end
end

endmodule
