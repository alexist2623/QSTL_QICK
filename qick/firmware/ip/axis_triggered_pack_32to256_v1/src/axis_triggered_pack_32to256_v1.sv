// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

// Trigger-aligned AXIS 32-bit to 256-bit packer.
//
// The packer drops input data until the first synchronized trigger rising edge.
// Each trigger rising edge clears any partial pack state, so the next accepted
// 32-bit input beat is placed in lane 0 of the next 256-bit output word.
//
// Trigger low is not a capture stop condition and does not discard a partial
// pack. The downstream DDR writer owns capture length through its own
// NBURST_REG configuration. This block only aligns the 32-to-256 packing
// boundary to the trigger event.
//
// Packing order is little-lane:
//   accepted sample 0 -> m_axis_tdata[ 31:  0]
//   accepted sample 1 -> m_axis_tdata[ 63: 32]
//   ...
//   accepted sample 7 -> m_axis_tdata[255:224]
//
// TLAST is not used as a capture stop condition. The DDR writer uses its own
// configured length, and software is expected to request capture lengths that
// are multiples of 128 input samples.

module axis_triggered_pack_32to256_v1 (
    input  wire         aclk,
    input  wire         aresetn,

    input  wire         trigger,

    output wire         s_axis_tready,
    input  wire         s_axis_tvalid,
    input  wire [31:0]  s_axis_tdata,

    input  wire         m_axis_tready,
    output wire         m_axis_tvalid,
    output wire [255:0] m_axis_tdata,
    output wire [31:0]  m_axis_tstrb,
    output wire         m_axis_tlast
);

    localparam int LANES = 8;

    logic trigger_meta;
    logic trigger_sync;
    logic trigger_sync_d;

    logic [255:0] pack_data_r;
    logic [2:0]   pack_count_r;

    logic [255:0] out_data_r;
    logic         out_valid_r;
    logic         align_valid_r;

    wire trigger_rise = trigger_sync & ~trigger_sync_d;

    wire out_fire = out_valid_r & m_axis_tready;
    wire can_emit = ~out_valid_r | out_fire;

    wire accept_aligned_would_emit = align_valid_r & (pack_count_r == (LANES-1));

    assign s_axis_tready = ~align_valid_r | ~accept_aligned_would_emit | can_emit;

    assign m_axis_tvalid = out_valid_r;
    assign m_axis_tdata  = out_data_r;
    assign m_axis_tstrb  = 32'hFFFF_FFFF;
    assign m_axis_tlast  = 1'b0;

    wire input_fire = s_axis_tvalid & s_axis_tready;

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            trigger_meta   <= 1'b0;
            trigger_sync   <= 1'b0;
            trigger_sync_d <= 1'b0;
        end else begin
            trigger_meta   <= trigger;
            trigger_sync   <= trigger_meta;
            trigger_sync_d <= trigger_sync;
        end
    end

    always_ff @(posedge aclk) begin
        logic [255:0] pack_next;
        logic [2:0]   count_next;
        logic [255:0] out_next;
        logic         out_valid_next;

        if (!aresetn) begin
            pack_data_r  <= '0;
            pack_count_r <= '0;
            out_data_r   <= '0;
            out_valid_r  <= 1'b0;
            align_valid_r <= 1'b0;
        end else begin
            pack_next      = pack_data_r;
            count_next     = pack_count_r;
            out_next       = out_data_r;
            out_valid_next = out_valid_r;

            if (out_fire) begin
                out_valid_next = 1'b0;
            end

            if (trigger_rise) begin
                pack_next  = '0;
                count_next = '0;
                align_valid_r <= 1'b1;
            end

            if (input_fire && align_valid_r) begin
                pack_next[count_next*32 +: 32] = s_axis_tdata;

                if (count_next == (LANES-1)) begin
                    out_next       = pack_next;
                    out_valid_next = 1'b1;
                    pack_next      = '0;
                    count_next     = '0;
                end else begin
                    count_next = count_next + 3'd1;
                end
            end

            pack_data_r  <= pack_next;
            pack_count_r <= count_next;
            out_data_r   <= out_next;
            out_valid_r  <= out_valid_next;
        end
    end

endmodule
