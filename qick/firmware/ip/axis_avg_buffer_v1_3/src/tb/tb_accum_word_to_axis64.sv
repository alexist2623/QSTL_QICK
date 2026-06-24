// Self-checking unit test for axis_accum_word_to_axis64.
//
// The serializer converts one internal accumulated IQ word into either two
// full-precision 64-bit AXIS beats or one compact 64-bit AXIS beat when B=16:
//   beat 0: signed I accumulator
//   beat 1: signed Q accumulator
//   compact: {Q_accum[31:0], I_accum[31:0]}
module tb_accum_word_to_axis64;

    localparam int B = 16;
    localparam int OUT_WIDTH = 4*B;
    localparam int WORD_WIDTH = 8*B;

    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic rstn;
    logic in_valid;
    wire  in_ready;
    logic [WORD_WIDTH-1:0] in_word;
    logic in_last;
    logic compact;
    wire  m_axis_tvalid;
    logic m_axis_tready;
    wire [OUT_WIDTH-1:0] m_axis_tdata;
    wire  m_axis_tlast;

    axis_accum_word_to_axis64 #(
        .B(B)
    ) dut (
        .clk(clk),
        .rstn(rstn),
        .in_valid_i(in_valid),
        .in_ready_o(in_ready),
        .in_word_i(in_word),
        .in_last_i(in_last),
        .compact_i(compact),
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tready(m_axis_tready),
        .m_axis_tdata(m_axis_tdata),
        .m_axis_tlast(m_axis_tlast)
    );

    task automatic reset_dut;
        begin
            rstn = 1'b0;
            in_valid = 1'b0;
            in_word = '0;
            in_last = 1'b0;
            compact = 1'b0;
            m_axis_tready = 1'b0;
            repeat (8) @(posedge clk);
            rstn = 1'b1;
            repeat (3) @(posedge clk);
        end
    endtask

    task automatic send_word(
        input logic [OUT_WIDTH-1:0] i_value,
        input logic [OUT_WIDTH-1:0] q_value,
        input bit last_value
    );
        begin
            @(negedge clk);
            while (!in_ready)
                @(negedge clk);
            in_word <= {q_value[OUT_WIDTH-1:0], i_value[OUT_WIDTH-1:0]};
            in_last <= last_value;
            in_valid <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            in_valid <= 1'b0;
            in_word <= '0;
            in_last <= 1'b0;
        end
    endtask

    task automatic expect_beat(
        input logic [OUT_WIDTH-1:0] expected,
        input bit expected_last,
        input string tag
    );
        int guard;
        begin
            guard = 0;
            do begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 100)
                    $fatal(1, "%s: timeout waiting for output beat", tag);
            end while (!m_axis_tvalid);

            if (m_axis_tdata != expected)
                $fatal(1, "%s: expected data %h, got %h",
                    tag, expected, m_axis_tdata);
            if (m_axis_tlast !== expected_last)
                $fatal(1, "%s: expected tlast=%0b got %0b",
                    tag, expected_last, m_axis_tlast);

            @(negedge clk);
            m_axis_tready <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            m_axis_tready <= 1'b0;
        end
    endtask

    initial begin
        reset_dut();
        if ($bits(m_axis_tdata) != OUT_WIDTH)
            $fatal(1, "Unexpected serializer output width");

        compact = 1'b0;
        send_word(64'h0123_4567_89ab_cdef, 64'hfedc_ba98_7654_3210, 1'b1);
        expect_beat(64'h0123_4567_89ab_cdef, 1'b0, "known full I");
        expect_beat(64'hfedc_ba98_7654_3210, 1'b1, "known full Q");

        send_word(64'sd123, -64'sd456, 1'b0);
        expect_beat(64'sd123, 1'b0, "word0 I");
        expect_beat(-64'sd456, 1'b0, "word0 Q");

        send_word(-64'sd987654321, 64'sd1122334455, 1'b1);
        expect_beat(-64'sd987654321, 1'b0, "word1 I");
        expect_beat(64'sd1122334455, 1'b1, "word1 Q");

        @(negedge clk);
        m_axis_tready <= 1'b0;
        send_word(64'sd17, -64'sd18, 1'b1);
        repeat (3) begin
            @(posedge clk);
            #1;
            if (!m_axis_tvalid)
                $fatal(1, "backpressure: output valid dropped");
            if ($signed(m_axis_tdata) != 64'sd17)
                $fatal(1, "backpressure: I beat changed while stalled");
            if (m_axis_tlast)
                $fatal(1, "backpressure: I beat asserted tlast");
        end
        expect_beat(64'sd17, 1'b0, "backpressure I");
        expect_beat(-64'sd18, 1'b1, "backpressure Q");

        compact = 1'b1;
        @(negedge clk);
        m_axis_tready <= 1'b1;
        in_word <= {64'hfedc_ba98_7654_3210, 64'h0123_4567_89ab_cdef};
        in_last <= 1'b1;
        in_valid <= 1'b1;
        @(posedge clk);
        #1;
        if (!m_axis_tvalid || !in_ready)
            $fatal(1, "compact known: expected valid and ready");
        if (m_axis_tdata != 64'h7654_3210_89ab_cdef)
            $fatal(1, "compact known: expected 7654321089abcdef, got %h", m_axis_tdata);
        if (!m_axis_tlast)
            $fatal(1, "compact known: expected tlast");
        @(negedge clk);
        in_valid <= 1'b0;
        in_last <= 1'b0;
        in_word <= '0;
        m_axis_tready <= 1'b0;

        @(negedge clk);
        in_word <= {64'h1111_2222_3333_4444, 64'haaaa_bbbb_cccc_dddd};
        in_last <= 1'b1;
        in_valid <= 1'b1;
        repeat (3) begin
            @(posedge clk);
            #1;
            if (!m_axis_tvalid)
                $fatal(1, "compact backpressure: valid dropped");
            if (in_ready)
                $fatal(1, "compact backpressure: input ready asserted while output stalled");
            if (m_axis_tdata != 64'h3333_4444_cccc_dddd)
                $fatal(1, "compact backpressure: data changed while stalled");
            if (!m_axis_tlast)
                $fatal(1, "compact backpressure: tlast dropped while stalled");
        end
        @(negedge clk);
        m_axis_tready <= 1'b1;
        @(posedge clk);
        #1;
        if (!in_ready || !m_axis_tvalid || m_axis_tdata != 64'h3333_4444_cccc_dddd)
            $fatal(1, "compact backpressure: stalled beat was not accepted cleanly");
        @(negedge clk);
        in_valid <= 1'b0;
        in_last <= 1'b0;
        in_word <= '0;
        m_axis_tready <= 1'b0;

        $display("PASS: tb_accum_word_to_axis64 completed");
        $finish;
    end

endmodule
