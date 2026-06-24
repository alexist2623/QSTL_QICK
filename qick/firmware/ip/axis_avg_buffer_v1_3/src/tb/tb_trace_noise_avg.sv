// Self-checking accumulation test for axis_avg_buffer v1.3.
//
// This test verifies direct accumulation. AVG_ACCUM_LEN_REG[23:0] selects M
// input samples accumulated per stored output point. AVG_TRACE_REPS_REG[23:0]
// selects R trace repetitions accumulated per stored output trace.
//
// AVG_LEN_REG is the number of stored output points.
// Consumed input samples per trace trigger = AVG_LEN_REG * effective_M.
// Total samples accumulated in trace mode = AVG_LEN_REG * effective_M * effective_R.
//
// Input samples are packed as {Q[B-1:0], I[B-1:0]}.
// Internal AVG accumulation words stay 8*B bits wide and are packed as
// {Q_lane[4*B-1:0], I_lane[4*B-1:0]}.
// The external processed AXIS ports are 4*B bits wide. Each stored output
// point is read as two AXIS beats: I_lane first, then Q_lane.
module tb;

    localparam int B = 16;
    localparam int N_AVG = 10;
    localparam int N_BUF = 8;
    localparam int ACC_WIDTH = 4 * B;
    localparam int LANE_WIDTH = 4 * B;
    localparam int ACC_WORD_WIDTH = 8 * B;
    localparam int AVG_AXIS_WIDTH = 4 * B;
`ifdef FAST_SIM
    localparam int TRACE_REPS_STRESS = 8;
    localparam int TRACE_STRESS_STORED = 48;
`else
    localparam int TRACE_REPS_STRESS = 10000;
    localparam int TRACE_STRESS_STORED = 945;
`endif
    localparam int MAX_STORED = 1024;
    localparam real TWO_PI = 6.2831853071795864769;

    localparam logic [6:0] REG_AVG_START      = 7'h00;
    localparam logic [6:0] REG_AVG_ADDR       = 7'h04;
    localparam logic [6:0] REG_AVG_LEN        = 7'h08;
    localparam logic [6:0] REG_AVG_DR_START   = 7'h0c;
    localparam logic [6:0] REG_AVG_DR_ADDR    = 7'h10;
    localparam logic [6:0] REG_AVG_DR_LEN     = 7'h14;
    localparam logic [6:0] REG_BUF_START      = 7'h18;
    localparam logic [6:0] REG_BUF_ADDR       = 7'h1c;
    localparam logic [6:0] REG_BUF_LEN        = 7'h20;
    localparam logic [6:0] REG_BUF_DR_START   = 7'h24;
    localparam logic [6:0] REG_BUF_DR_ADDR    = 7'h28;
    localparam logic [6:0] REG_BUF_DR_LEN     = 7'h2c;
    localparam logic [6:0] REG_AVG_ACCUM_LEN  = 7'h3c;
    localparam logic [6:0] REG_AVG_TRACE_REPS = 7'h40;

    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic rstn;

    logic [6:0]  s_axi_awaddr;
    logic [2:0]  s_axi_awprot;
    logic        s_axi_awvalid;
    wire         s_axi_awready;
    logic [31:0] s_axi_wdata;
    logic [3:0]  s_axi_wstrb;
    logic        s_axi_wvalid;
    wire         s_axi_wready;
    wire  [1:0]  s_axi_bresp;
    wire         s_axi_bvalid;
    logic        s_axi_bready;
    logic [6:0]  s_axi_araddr;
    logic [2:0]  s_axi_arprot;
    logic        s_axi_arvalid;
    wire         s_axi_arready;
    wire  [31:0] s_axi_rdata;
    wire  [1:0]  s_axi_rresp;
    wire         s_axi_rvalid;
    logic        s_axi_rready;

    logic trigger;
    logic s_axis_tvalid;
    wire  s_axis_tready;
    logic [2*B-1:0] s_axis_tdata;

    wire                 m0_axis_tvalid;
    logic                m0_axis_tready;
    wire [AVG_AXIS_WIDTH-1:0] m0_axis_tdata;
    wire                 m0_axis_tlast;
    wire                 m1_axis_tvalid;
    logic                m1_axis_tready;
    wire [2*B-1:0]       m1_axis_tdata;
    wire                 m1_axis_tlast;
    wire                 m2_axis_tvalid;
    logic                m2_axis_tready;
    wire [AVG_AXIS_WIDTH-1:0] m2_axis_tdata;

    longint signed expected_i [0:MAX_STORED-1];
    longint signed expected_q [0:MAX_STORED-1];
    longint signed m2_capture_beats [0:2*MAX_STORED-1];
    int m2_capture_count;
    bit m2_capture_enable;

    axis_avg_buffer #(
        .N_AVG(N_AVG),
        .N_BUF(N_BUF),
        .B(B)
    ) dut (
        .s_axi_aclk(clk),
        .s_axi_aresetn(rstn),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awprot(s_axi_awprot),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .trigger(trigger),
        .s_axis_aclk(clk),
        .s_axis_aresetn(rstn),
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready),
        .s_axis_tdata(s_axis_tdata),
        .m_axis_aclk(clk),
        .m_axis_aresetn(rstn),
        .m0_axis_tvalid(m0_axis_tvalid),
        .m0_axis_tready(m0_axis_tready),
        .m0_axis_tdata(m0_axis_tdata),
        .m0_axis_tlast(m0_axis_tlast),
        .m1_axis_tvalid(m1_axis_tvalid),
        .m1_axis_tready(m1_axis_tready),
        .m1_axis_tdata(m1_axis_tdata),
        .m1_axis_tlast(m1_axis_tlast),
        .m2_axis_tvalid(m2_axis_tvalid),
        .m2_axis_tready(m2_axis_tready),
        .m2_axis_tdata(m2_axis_tdata)
    );

    always @(posedge clk) begin
        if (!rstn) begin
            m2_capture_count <= 0;
        end else if (m2_capture_enable && m2_axis_tvalid && m2_axis_tready) begin
            if (m2_capture_count >= 2*MAX_STORED)
                $fatal(1, "m2 AXIS capture overflow");
            m2_capture_beats[m2_capture_count] <= $signed(m2_axis_tdata);
            m2_capture_count <= m2_capture_count + 1;
        end
    end

    function automatic logic [2*B-1:0] pack_iq(input int signed i, input int signed q);
        logic signed [B-1:0] ii;
        logic signed [B-1:0] qq;
        begin
            ii = i;
            qq = q;
            pack_iq = {qq, ii};
        end
    endfunction

    function automatic int signed get_i(input logic [2*B-1:0] iq);
        get_i = $signed(iq[B-1:0]);
    endfunction

    function automatic int signed get_q(input logic [2*B-1:0] iq);
        get_q = $signed(iq[2*B-1:B]);
    endfunction

    function automatic int signed noise(input int rep, input int n, input int salt);
        int unsigned x;
        int unsigned pair_rep;
        int signed base_noise;
        begin
            pair_rep = rep >> 1;
            x = 32'h1234_5678 ^ (pair_rep * 32'h045d_9f3b) ^ (n * 32'h119d_e1f3) ^ salt;
            x = (x ^ (x >> 16)) * 32'h045d_9f3b;
            base_noise = int'(x[5:0]) - 32;
            noise = ((rep % 2) == 0) ? base_noise : -base_noise;
        end
    endfunction

    function automatic int signed stimulus_i(
        input int rep,
        input int n,
        input int input_len,
        input int waveform
    );
        real x;
        begin
            x = TWO_PI * real'(n) / real'(input_len);
            case (waveform)
                0: stimulus_i = 1000 + 3*n + noise(rep, n, 32'h101);
                1: stimulus_i = -1800 + 5*n + noise(rep, n, 32'h202);
                2: begin
                    stimulus_i = $rtoi(
                        1800.0*$sin(4.0*x + 0.25)
                    ) + 100*noise(rep, n, 32'h303);
                end
                3: stimulus_i = 32767;
                default: stimulus_i = n + noise(rep, n, 32'h404);
            endcase
        end
    endfunction

    function automatic int signed stimulus_q(
        input int rep,
        input int n,
        input int input_len,
        input int waveform
    );
        real x;
        real phase;
        real trapezoid;
        begin
            x = TWO_PI * real'(n) / real'(input_len);
            case (waveform)
                0: stimulus_q = -500 + 2*n + noise(rep, n, 32'h505);
                1: stimulus_q = -2600 + 7*n + noise(rep, n, 32'h606);
                2: begin
                    phase = 4.0*real'(n)/real'(input_len) + 0.0557;
                    phase = phase - $floor(phase);
                    if (phase < 0.20) begin
                        trapezoid = -1400.0;
                    end else if (phase < 0.40) begin
                        trapezoid = -1400.0 + 2800.0*(phase - 0.20)/0.20;
                    end else if (phase < 0.70) begin
                        trapezoid = 1400.0;
                    end else if (phase < 0.90) begin
                        trapezoid = 1400.0 - 2800.0*(phase - 0.70)/0.20;
                    end else begin
                        trapezoid = -1400.0;
                    end
                    stimulus_q = $rtoi(trapezoid) + 100*noise(rep, n, 32'h707);
                end
                3: stimulus_q = -32768;
                default: stimulus_q = -n + noise(rep, n, 32'h808);
            endcase
        end
    endfunction

    task automatic check_avg_beat(
        input logic [AVG_AXIS_WIDTH-1:0] actual_avg_beat,
        input longint signed expected,
        input string tag
    );
        longint signed actual;
        begin
            if ($isunknown(actual_avg_beat))
                $fatal(1, "%s: AVG beat contains X/Z: %h", tag, actual_avg_beat);

            actual = $signed(actual_avg_beat);

            if (actual != expected) begin
                $fatal(1,
                    "%s: expected %0d, got %0d beat=%h",
                    tag, expected, actual, actual_avg_beat);
            end
        end
    endtask

    task automatic check_raw_word(
        input logic [2*B-1:0] actual_word,
        input int signed exp_i,
        input int signed exp_q,
        input string tag
    );
        int signed act_i;
        int signed act_q;
        begin
            if ($isunknown(actual_word))
                $fatal(1, "%s: RAW word contains X/Z: %h", tag, actual_word);

            act_i = get_i(actual_word);
            act_q = get_q(actual_word);
            if ((act_i != exp_i) || (act_q != exp_q)) begin
                $fatal(1,
                    "%s: expected RAW I=%0d Q=%0d, got I=%0d Q=%0d word=%h",
                    tag, exp_i, exp_q, act_i, act_q, actual_word);
            end
        end
    endtask

    task automatic axi_write32(input logic [6:0] addr, input logic [31:0] data);
        int guard;
        bit aw_done;
        bit w_done;
        begin
            @(negedge clk);
            s_axi_awaddr  <= addr;
            s_axi_awprot  <= 3'b000;
            s_axi_awvalid <= 1'b1;
            s_axi_wdata   <= data;
            s_axi_wstrb   <= 4'hf;
            s_axi_wvalid  <= 1'b1;
            s_axi_bready  <= 1'b0;

            guard = 0;
            aw_done = 1'b0;
            w_done = 1'b0;
            while (!(aw_done && w_done)) begin
                @(posedge clk);
                #1;
                if (s_axi_awvalid && s_axi_awready)
                    aw_done = 1'b1;
                if (s_axi_wvalid && s_axi_wready)
                    w_done = 1'b1;
                guard++;
                if (guard > 200)
                    $fatal(1, "AXI write timeout at address 0x%02h", addr);
            end

            guard = 0;
            while (!s_axi_bvalid) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 200)
                    $fatal(1, "AXI BRESP timeout at address 0x%02h", addr);
            end
            if (s_axi_bresp != 2'b00)
                $fatal(1, "AXI BRESP error at address 0x%02h: %b", addr, s_axi_bresp);

            @(negedge clk);
            s_axi_awvalid <= 1'b0;
            s_axi_wvalid  <= 1'b0;
            s_axi_bready  <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            s_axi_bready <= 1'b0;
        end
    endtask

    task automatic axi_read32(input logic [6:0] addr, output logic [31:0] data);
        int guard;
        begin
            @(negedge clk);
            s_axi_araddr  <= addr;
            s_axi_arprot  <= 3'b000;
            s_axi_arvalid <= 1'b1;
            s_axi_rready  <= 1'b0;

            guard = 0;
            while (!s_axi_arready) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 200)
                    $fatal(1, "AXI read address timeout at address 0x%02h", addr);
            end

            guard = 0;
            while (!s_axi_rvalid) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 200)
                    $fatal(1, "AXI RDATA timeout at address 0x%02h", addr);
            end
            if (s_axi_rresp != 2'b00)
                $fatal(1, "AXI RRESP error at address 0x%02h: %b", addr, s_axi_rresp);
            data = s_axi_rdata;

            @(negedge clk);
            s_axi_arvalid <= 1'b0;
            s_axi_rready  <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            s_axi_rready <= 1'b0;
        end
    endtask

    task automatic reset_dut;
        begin
            rstn = 1'b0;
            s_axi_awaddr = '0;
            s_axi_awprot = '0;
            s_axi_awvalid = 1'b0;
            s_axi_wdata = '0;
            s_axi_wstrb = 4'hf;
            s_axi_wvalid = 1'b0;
            s_axi_bready = 1'b0;
            s_axi_araddr = '0;
            s_axi_arprot = '0;
            s_axi_arvalid = 1'b0;
            s_axi_rready = 1'b0;
            trigger = 1'b0;
            s_axis_tvalid = 1'b0;
            s_axis_tdata = '0;
            m0_axis_tready = 1'b0;
            m1_axis_tready = 1'b1;
            m2_axis_tready = 1'b1;
            m2_capture_enable = 1'b0;
            m2_capture_count = 0;
            repeat (12) @(posedge clk);
            rstn = 1'b1;
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic pulse_trigger;
        begin
            @(negedge clk);
            trigger <= 1'b1;
            @(negedge clk);
            trigger <= 1'b0;
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic feed_stimulus_trace(
        input int rep,
        input int input_len,
        input int waveform
    );
        begin
            feed_stimulus_trace_gap(rep, input_len, waveform, 0);
        end
    endtask

    task automatic feed_stimulus_trace_gap(
        input int rep,
        input int input_len,
        input int waveform,
        input int gap_cycles
    );
        begin
            pulse_trigger();
            for (int n = 0; n < input_len; n++) begin
                @(negedge clk);
                s_axis_tdata  <= pack_iq(
                    stimulus_i(rep, n, input_len, waveform),
                    stimulus_q(rep, n, input_len, waveform)
                );
                s_axis_tvalid <= 1'b1;
                @(posedge clk);
                #1;
                if (!s_axis_tready)
                    $fatal(1, "DUT deasserted s_axis_tready");
                if (gap_cycles > 0) begin
                    @(negedge clk);
                    s_axis_tvalid <= 1'b0;
                    s_axis_tdata  <= '0;
                    repeat (gap_cycles) @(posedge clk);
                end
            end
            @(negedge clk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata  <= '0;
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic compute_expected(
        input int m_len,
        input int reps,
        input int stored_len,
        input int waveform
    );
        int input_len;
        longint signed sum_i;
        longint signed sum_q;
        begin
            input_len = stored_len * m_len;
            for (int idx = 0; idx < MAX_STORED; idx++) begin
                expected_i[idx] = 0;
                expected_q[idx] = 0;
            end

            for (int out_idx = 0; out_idx < stored_len; out_idx++) begin
                sum_i = 0;
                sum_q = 0;
                for (int rep = 0; rep < reps; rep++) begin
                    for (int g = 0; g < m_len; g++) begin
                        sum_i += stimulus_i(rep, out_idx*m_len + g, input_len, waveform);
                        sum_q += stimulus_q(rep, out_idx*m_len + g, input_len, waveform);
                    end
                end
                expected_i[out_idx] = sum_i;
                expected_q[out_idx] = sum_q;
            end
        end
    endtask

    task automatic arm_normal_accum(input int m_len, input int stored_len);
        begin
            axi_write32(REG_AVG_START, 32'd0);
            repeat (6) @(posedge clk);
            axi_write32(REG_AVG_ADDR, 32'd0);
            axi_write32(REG_AVG_LEN, stored_len);
            axi_write32(REG_AVG_ACCUM_LEN, m_len[23:0]);
            axi_write32(REG_AVG_TRACE_REPS, 32'd1);
            axi_write32(REG_AVG_START, 32'd1);
            repeat (12) @(posedge clk);
        end
    endtask

    task automatic arm_trace_accum(input int m_len, input int stored_len, input int reps);
        begin
            axi_write32(REG_AVG_START, 32'd0);
            repeat (6) @(posedge clk);
            axi_write32(REG_AVG_ADDR, 32'd0);
            axi_write32(REG_AVG_LEN, stored_len);
            axi_write32(REG_AVG_ACCUM_LEN, m_len[23:0]);
            axi_write32(REG_AVG_TRACE_REPS, reps[23:0]);
            axi_write32(REG_AVG_START, 32'd3);
            repeat ((1 << N_AVG) + 40) @(posedge clk);
        end
    endtask

    task automatic start_avg_read(input int stored_len);
        begin
            m0_axis_tready = 1'b0;
            axi_write32(REG_AVG_DR_START, 32'd0);
            axi_write32(REG_AVG_DR_ADDR, 32'd0);
            axi_write32(REG_AVG_DR_LEN, stored_len);
            axi_write32(REG_AVG_DR_START, 32'd1);
        end
    endtask

    task automatic stop_avg_read;
        begin
            axi_write32(REG_AVG_DR_START, 32'd0);
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic start_m2_capture;
        begin
            @(negedge clk);
            m2_capture_count = 0;
            m2_capture_enable = 1'b1;
        end
    endtask

    task automatic wait_and_check_m2(input int stored_len, input string tag);
        int guard;
        string full_tag;
        begin
            guard = 0;
            while (m2_capture_count < 2*stored_len) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 10000)
                    $fatal(1, "%s: timeout waiting for m2 AXIS, captured %0d beats",
                        tag, m2_capture_count);
            end

            @(negedge clk);
            m2_capture_enable = 1'b0;

            for (int idx = 0; idx < stored_len; idx++) begin
                full_tag = $sformatf("%s m2[%0d].I", tag, idx);
                if (m2_capture_beats[2*idx] != expected_i[idx])
                    $fatal(1, "%s: expected %0d, got %0d",
                        full_tag, expected_i[idx], m2_capture_beats[2*idx]);
                full_tag = $sformatf("%s m2[%0d].Q", tag, idx);
                if (m2_capture_beats[2*idx + 1] != expected_q[idx])
                    $fatal(1, "%s: expected %0d, got %0d",
                        full_tag, expected_q[idx], m2_capture_beats[2*idx + 1]);
            end
        end
    endtask

    task automatic start_buf_read(input int raw_len);
        begin
            axi_write32(REG_BUF_DR_START, 32'd0);
            axi_write32(REG_BUF_DR_ADDR, 32'd0);
            axi_write32(REG_BUF_DR_LEN, raw_len);
            axi_write32(REG_BUF_DR_START, 32'd1);
        end
    endtask

    task automatic stop_buf_read;
        begin
            axi_write32(REG_BUF_DR_START, 32'd0);
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic expect_avg_sample(input int idx, input string tag, input bit expect_last);
        int guard;
        string full_tag;
        begin
            @(negedge clk);
            m0_axis_tready <= 1'b0;
            guard = 0;
            do begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 5000)
                    $fatal(1, "%s[%0d].I: timeout waiting for AVG stream", tag, idx);
            end while (!m0_axis_tvalid);
            full_tag = $sformatf("%s[%0d].I", tag, idx);
            check_avg_beat(m0_axis_tdata, expected_i[idx], full_tag);
            if (m0_axis_tlast !== 1'b0)
                $fatal(1, "%s: I beat asserted m0_axis_tlast", full_tag);

            @(negedge clk);
            m0_axis_tready <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            m0_axis_tready <= 1'b0;

            guard = 0;
            do begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 5000)
                    $fatal(1, "%s[%0d].Q: timeout waiting for AVG stream", tag, idx);
            end while (!m0_axis_tvalid);
            full_tag = $sformatf("%s[%0d].Q", tag, idx);
            check_avg_beat(m0_axis_tdata, expected_q[idx], full_tag);
            if (m0_axis_tlast !== expect_last)
                $fatal(1, "%s: expected m0_axis_tlast=%0b got %0b",
                    full_tag, expect_last, m0_axis_tlast);

            @(negedge clk);
            m0_axis_tready <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            m0_axis_tready <= 1'b0;
        end
    endtask

    task automatic expect_raw_sample(
        input int idx,
        input int input_len,
        input int waveform,
        input string tag,
        input bit expect_last
    );
        int guard;
        string full_tag;
        begin
            guard = 0;
            do begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 5000)
                    $fatal(1, "%s[%0d]: timeout waiting for RAW stream", tag, idx);
            end while (!m1_axis_tvalid);
            full_tag = $sformatf("%s[%0d]", tag, idx);
            check_raw_word(
                m1_axis_tdata,
                stimulus_i(0, idx, input_len, waveform),
                stimulus_q(0, idx, input_len, waveform),
                full_tag
            );
            if (m1_axis_tlast !== expect_last)
                $fatal(1, "%s: expected m1_axis_tlast=%0b got %0b",
                    full_tag, expect_last, m1_axis_tlast);
        end
    endtask

    task automatic read_and_check_avg(input int stored_len, input string tag);
        begin
            start_avg_read(stored_len);
            for (int idx = 0; idx < stored_len; idx++)
                expect_avg_sample(idx, tag, idx == (stored_len - 1));
            stop_avg_read();
        end
    endtask

    task automatic read_and_check_raw(input int input_len, input int waveform, input string tag);
        begin
            start_buf_read(input_len);
            for (int idx = 0; idx < input_len; idx++)
                expect_raw_sample(idx, input_len, waveform, tag, idx == (input_len - 1));
            stop_buf_read();
        end
    endtask

    task automatic run_normal_case(
        input string tag,
        input int m_len,
        input int stored_len,
        input int waveform
    );
        int input_len;
        begin
            input_len = m_len * stored_len;
            $display("Running %s: normal AVG M=%0d stored_len=%0d input_len=%0d",
                tag, m_len, stored_len, input_len);
            compute_expected(m_len, 1, stored_len, waveform);
            arm_normal_accum(m_len, stored_len);
            start_m2_capture();
            feed_stimulus_trace_gap(0, input_len, waveform, 3);
            repeat (80) @(posedge clk);
            wait_and_check_m2(stored_len, tag);
            read_and_check_avg(stored_len, tag);
            axi_write32(REG_AVG_START, 32'd0);
        end
    endtask

    task automatic run_trace_case(
        input string tag,
        input int m_len,
        input int reps,
        input int stored_len,
        input int waveform
    );
        int input_len;
        begin
            input_len = m_len * stored_len;
            $display("Running %s: trace AVG M=%0d R=%0d stored_len=%0d input_len/rep=%0d",
                tag, m_len, reps, stored_len, input_len);
            compute_expected(m_len, reps, stored_len, waveform);
            arm_trace_accum(m_len, stored_len, reps);
            for (int rep = 0; rep < reps; rep++)
                feed_stimulus_trace(rep, input_len, waveform);
            repeat (160) @(posedge clk);
            read_and_check_avg(stored_len, tag);
            axi_write32(REG_AVG_START, 32'd0);
        end
    endtask

    task automatic run_raw_buffer_unchanged_test;
        int m_len;
        int stored_len;
        int reps;
        int input_len;
        int waveform;
        begin
            m_len = 5;
            stored_len = 12;
            reps = 1;
            waveform = 2;
            input_len = m_len * stored_len;
            $display("Running raw buffer unchanged test with AVG M=%0d input_len=%0d", m_len, input_len);

            compute_expected(m_len, reps, stored_len, waveform);
            axi_write32(REG_AVG_START, 32'd0);
            axi_write32(REG_BUF_START, 32'd0);
            repeat (6) @(posedge clk);
            axi_write32(REG_BUF_ADDR, 32'd0);
            axi_write32(REG_BUF_LEN, input_len);
            axi_write32(REG_BUF_START, 32'd1);
            arm_trace_accum(m_len, stored_len, reps);

            feed_stimulus_trace(0, input_len, waveform);

            repeat (160) @(posedge clk);
            read_and_check_avg(stored_len, "raw-test AVG accumulation");
            read_and_check_raw(input_len, waveform, "raw-test RAW buffer");
            axi_write32(REG_AVG_START, 32'd0);
            axi_write32(REG_BUF_START, 32'd0);
        end
    endtask

    task automatic run_register_test;
        logic [31:0] readback;
        begin
            $display("Running 24-bit AXI-Lite accumulation register readback test");
            axi_write32(REG_AVG_ACCUM_LEN, 32'hffff_ffff);
            axi_read32(REG_AVG_ACCUM_LEN, readback);
            if (readback != 32'h00ff_ffff)
                $fatal(1, "AVG_ACCUM_LEN_REG readback mismatch: %h", readback);
            axi_write32(REG_AVG_TRACE_REPS, 32'hffff_ffff);
            axi_read32(REG_AVG_TRACE_REPS, readback);
            if (readback != 32'h00ff_ffff)
                $fatal(1, "AVG_TRACE_REPS_REG readback mismatch: %h", readback);
            axi_write32(REG_AVG_ACCUM_LEN, 32'd1);
            axi_write32(REG_AVG_TRACE_REPS, 32'd1);
        end
    endtask

    task automatic run_64bit_boundary_test;
        int m_len;
        int reps;
        int stored_len;
        int input_len;
        begin
            m_len = 65535;
            reps = 2;
            stored_len = 1;
            input_len = m_len * stored_len;
            expected_i[0] = 64'sd32767 * m_len * reps;
            expected_q[0] = -64'sd32768 * m_len * reps;
            if (expected_i[0] <= 64'sd2147483647)
                $fatal(1, "Boundary test expected I does not cross 32-bit positive range");
            if (expected_q[0] >= -64'sd2147483648)
                $fatal(1, "Boundary test expected Q does not cross 32-bit negative range");

            $display("Running 64-bit channel boundary smoke test: M=%0d R=%0d", m_len, reps);
            arm_trace_accum(m_len, stored_len, reps);
            for (int rep = 0; rep < reps; rep++)
                feed_stimulus_trace(rep, input_len, 3);
            repeat (120) @(posedge clk);
            read_and_check_avg(stored_len, "64-bit boundary");
            axi_write32(REG_AVG_START, 32'd0);
        end
    endtask

    initial begin
        reset_dut();
        if ($bits(m0_axis_tdata) != 4*B)
            $fatal(1, "m0_axis_tdata width mismatch: expected %0d got %0d", 4*B, $bits(m0_axis_tdata));
        if ($bits(m2_axis_tdata) != 4*B)
            $fatal(1, "m2_axis_tdata width mismatch: expected %0d got %0d", 4*B, $bits(m2_axis_tdata));
        if ($bits(m1_axis_tdata) != 2*B)
            $fatal(1, "m1_axis_tdata width mismatch: expected %0d got %0d", 2*B, $bits(m1_axis_tdata));
        run_register_test();
        run_normal_case("M1 R1 compatibility", 1, 16, 0);
        run_normal_case("M2 direct accumulation", 2, 16, 0);
        run_normal_case("M3 direct accumulation", 3, 15, 0);
        run_normal_case("M5 direct accumulation", 5, 12, 2);
        run_trace_case("M3 R4 trace accumulation", 3, 4, 15, 0);
        run_trace_case("negative signed M5 R4", 5, 4, 12, 1);
        run_trace_case("sine/ramped-square M20 stress window", 20, TRACE_REPS_STRESS, TRACE_STRESS_STORED, 2);
        run_raw_buffer_unchanged_test();
        run_64bit_boundary_test();
        $display("PASS: tb_trace_noise_avg completed v1.3 direct accumulation tests");
        $finish;
    end

endmodule
