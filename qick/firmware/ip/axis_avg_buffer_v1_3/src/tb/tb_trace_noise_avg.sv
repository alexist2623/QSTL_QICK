// Self-checking trace-average test for axis_avg_buffer v1.3.
//
// This test verifies trace averaging with deterministic random noise.
// It covers ramp, signed-negative ramp, and complex sinusoidal traces.
// K = AVG_DECIM_LOG2_REG[3:0], and the AVG time group size is 2**K.
// AVG_LEN_REG is the number of stored output samples.
// Consumed input samples per repetition = AVG_LEN_REG * 2**K.
//
// Input samples are packed as {Q[B-1:0], I[B-1:0]}.
// AVG memory readout words are packed as {Q[2*B-1:0], I[2*B-1:0]}.
module tb;

    localparam int B = 16;
    localparam int N_AVG = 8;
    localparam int N_BUF = 8;
    localparam int MAX_AVG_DECIM_LOG2 = 6;
    localparam int TRACE_LEN = 64;
    localparam int N_REPS = 100;
    localparam real TWO_PI = 6.2831853071795864769;

    localparam logic [5:0] REG_AVG_START      = 6'h00;
    localparam logic [5:0] REG_AVG_ADDR       = 6'h04;
    localparam logic [5:0] REG_AVG_LEN        = 6'h08;
    localparam logic [5:0] REG_AVG_DR_START   = 6'h0c;
    localparam logic [5:0] REG_AVG_DR_ADDR    = 6'h10;
    localparam logic [5:0] REG_AVG_DR_LEN     = 6'h14;
    localparam logic [5:0] REG_BUF_START      = 6'h18;
    localparam logic [5:0] REG_BUF_ADDR       = 6'h1c;
    localparam logic [5:0] REG_BUF_LEN        = 6'h20;
    localparam logic [5:0] REG_BUF_DR_START   = 6'h24;
    localparam logic [5:0] REG_BUF_DR_ADDR    = 6'h28;
    localparam logic [5:0] REG_BUF_DR_LEN     = 6'h2c;
    localparam logic [5:0] REG_AVG_DECIM_LOG2 = 6'h3c;

    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic rstn;

    logic [5:0]  s_axi_awaddr;
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
    logic [5:0]  s_axi_araddr;
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

    wire         m0_axis_tvalid;
    logic        m0_axis_tready;
    wire [4*B-1:0] m0_axis_tdata;
    wire         m0_axis_tlast;
    wire         m1_axis_tvalid;
    logic        m1_axis_tready;
    wire [2*B-1:0] m1_axis_tdata;
    wire         m1_axis_tlast;
    wire         m2_axis_tvalid;
    logic        m2_axis_tready;
    wire [4*B-1:0] m2_axis_tdata;

    longint signed expected_i [0:TRACE_LEN-1];
    longint signed expected_q [0:TRACE_LEN-1];

    axis_avg_buffer #(
        .N_AVG(N_AVG),
        .N_BUF(N_BUF),
        .B(B),
        .MAX_AVG_DECIM_LOG2(MAX_AVG_DECIM_LOG2)
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

    function automatic signed [B-1:0] get_i(input logic [2*B-1:0] iq);
        get_i = $signed(iq[B-1:0]);
    endfunction

    function automatic signed [B-1:0] get_q(input logic [2*B-1:0] iq);
        get_q = $signed(iq[2*B-1:B]);
    endfunction

    function automatic logic [2*B-1:0] pack_iq(input int signed i, input int signed q);
        logic signed [B-1:0] ii;
        logic signed [B-1:0] qq;
        begin
            ii = i;
            qq = q;
            pack_iq = {qq, ii};
        end
    endfunction

    function automatic longint signed arshift(input longint signed value, input int unsigned shift);
        if (shift == 0)
            arshift = value;
        else
            arshift = value >>> shift;
    endfunction

    function automatic longint signed avg_repetitions(input longint signed value);
        // Non-power-of-two repetition counts use the same signed division
        // truncation policy as trace_avg.sv.
        avg_repetitions = value / N_REPS;
    endfunction

    function automatic int signed noise(input int rep, input int n, input int salt);
        int unsigned x;
        int signed mag;
        int group4;
        begin
            // Stable pseudo-random noise. It is constant within groups of four
            // and sign-balanced across the eight repetitions.
            group4 = n >> 2;
            x = 32'h1234_5678 ^ ((rep % (N_REPS/2)) * 32'h045d_9f3b);
            x = x ^ (group4 * 32'h119d_e1f3) ^ salt;
            x = (x ^ (x >> 16)) * 32'h045d_9f3b;
            mag = int'(x % 31) - 15;
            noise = (rep < (N_REPS/2)) ? mag : -mag;
        end
    endfunction

    function automatic int signed base_i(input int n, input bit negative_case);
        base_i = negative_case ? (-1000 + 5*n) : (1000 + 3*n);
    endfunction

    function automatic int signed base_q(input int n, input bit negative_case);
        base_q = negative_case ? (-2000 + 7*n) : (-500 + 2*n);
    endfunction

    function automatic int signed complex_base_i(input int n);
        real x;
        int signed step;
        begin
            x = TWO_PI * real'(n) / real'(TRACE_LEN);
            step = (n < (TRACE_LEN/2)) ? 350 : -350;
            complex_base_i = $rtoi(
                1400.0*$sin(3.0*x) +
                 650.0*$sin(9.0*x + 0.35) +
                 220.0*$cos(17.0*x - 0.15) +
                 step +
                 25.0*real'((n % 7) - 3)
            );
        end
    endfunction

    function automatic int signed complex_base_q(input int n);
        real x;
        real chirp_x;
        int signed shelf;
        begin
            x = TWO_PI * real'(n) / real'(TRACE_LEN);
            chirp_x = TWO_PI * (1.0 + 2.0*real'(n)/real'(TRACE_LEN)) *
                      real'(n) / real'(TRACE_LEN);
            shelf = ((n >= 16) && (n < 48)) ? 280 : -180;
            complex_base_q = $rtoi(
                -250.0 +
                1250.0*$cos(5.0*x + 0.20) -
                 520.0*$sin(13.0*x - 0.40) +
                 360.0*$sin(4.0*chirp_x) +
                 shelf
            );
        end
    endfunction

    function automatic int signed sample_i(input int rep, input int n, input bit negative_case);
        sample_i = base_i(n, negative_case) + noise(rep, n, 32'h0000_0123);
    endfunction

    function automatic int signed sample_q(input int rep, input int n, input bit negative_case);
        sample_q = base_q(n, negative_case) + noise(rep, n, 32'h0000_0456);
    endfunction

    function automatic int signed stimulus_i(input int rep, input int n, input int waveform);
        case (waveform)
            0: stimulus_i = sample_i(rep, n, 1'b0);
            1: stimulus_i = sample_i(rep, n, 1'b1);
            2: stimulus_i = complex_base_i(n) + noise(rep, n, 32'h0000_0789);
            default: stimulus_i = sample_i(rep, n, 1'b0);
        endcase
    endfunction

    function automatic int signed stimulus_q(input int rep, input int n, input int waveform);
        case (waveform)
            0: stimulus_q = sample_q(rep, n, 1'b0);
            1: stimulus_q = sample_q(rep, n, 1'b1);
            2: stimulus_q = complex_base_q(n) + noise(rep, n, 32'h0000_0abc);
            default: stimulus_q = sample_q(rep, n, 1'b0);
        endcase
    endfunction

    function automatic logic [4*B-1:0] pack_avg_word(input longint signed i, input longint signed q);
        logic signed [2*B-1:0] ii;
        logic signed [2*B-1:0] qq;
        begin
            ii = i;
            qq = q;
            pack_avg_word = {qq, ii};
        end
    endfunction

    task automatic check_iq(
        input logic [4*B-1:0] actual_avg_word,
        input longint signed exp_i,
        input longint signed exp_q,
        input string tag
    );
        longint signed act_i;
        longint signed act_q;
        begin
            if ($isunknown(actual_avg_word))
                $fatal(1, "%s: AVG word contains X/Z: %h", tag, actual_avg_word);

            act_i = $signed(actual_avg_word[2*B-1:0]);
            act_q = $signed(actual_avg_word[4*B-1:2*B]);

            if ((act_i != exp_i) || (act_q != exp_q)) begin
                $fatal(1,
                    "%s: expected I=%0d Q=%0d, got I=%0d Q=%0d word=%h",
                    tag, exp_i, exp_q, act_i, act_q, actual_avg_word);
            end
        end
    endtask

    task automatic check_raw_iq(
        input logic [2*B-1:0] actual_word,
        input int signed exp_i,
        input int signed exp_q,
        input string tag
    );
        longint signed act_i;
        longint signed act_q;
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

    task automatic axi_write32(input logic [5:0] addr, input logic [31:0] data);
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
            s_axi_wvalid <= 1'b0;
            s_axi_bready <= 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            s_axi_bready <= 1'b0;
        end
    endtask

    task automatic axi_read32(input logic [5:0] addr, output logic [31:0] data);
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
            s_axi_rready <= 1'b1;
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
            m0_axis_tready = 1'b1;
            m1_axis_tready = 1'b1;
            m2_axis_tready = 1'b1;
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
            repeat (6) @(posedge clk);
        end
    endtask

    task automatic feed_sample(input int signed i, input int signed q);
        begin
            @(negedge clk);
            s_axis_tdata <= pack_iq(i, q);
            s_axis_tvalid <= 1'b1;
            @(posedge clk);
            #1;
            if (!s_axis_tready)
                $fatal(1, "DUT deasserted s_axis_tready");
            @(negedge clk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata <= '0;
            @(posedge clk);
        end
    endtask

    task automatic compute_expected_trace(
        input int unsigned k,
        input int unsigned input_len,
        input int waveform
    );
        int group_size;
        int stored_len;
        longint signed group_sum_i;
        longint signed group_sum_q;
        longint signed rep_sum_i;
        longint signed rep_sum_q;
        longint signed decim_i;
        longint signed decim_q;
        begin
            group_size = 1 << k;
            stored_len = input_len / group_size;

            for (int m = 0; m < TRACE_LEN; m++) begin
                expected_i[m] = 0;
                expected_q[m] = 0;
            end

            for (int m = 0; m < stored_len; m++) begin
                rep_sum_i = 0;
                rep_sum_q = 0;
                for (int rep = 0; rep < N_REPS; rep++) begin
                    group_sum_i = 0;
                    group_sum_q = 0;
                    for (int g = 0; g < group_size; g++) begin
                        group_sum_i += stimulus_i(rep, m*group_size + g, waveform);
                        group_sum_q += stimulus_q(rep, m*group_size + g, waveform);
                    end
                    decim_i = arshift(group_sum_i, k);
                    decim_q = arshift(group_sum_q, k);
                    rep_sum_i += decim_i;
                    rep_sum_q += decim_q;
                end
                expected_i[m] = avg_repetitions(rep_sum_i);
                expected_q[m] = avg_repetitions(rep_sum_q);
            end
        end
    endtask

    task automatic compute_expected_single_rep(input int unsigned k, input int unsigned input_len);
        int group_size;
        int stored_len;
        longint signed group_sum_i;
        longint signed group_sum_q;
        begin
            group_size = 1 << k;
            stored_len = input_len / group_size;
            for (int m = 0; m < TRACE_LEN; m++) begin
                expected_i[m] = 0;
                expected_q[m] = 0;
            end
            for (int m = 0; m < stored_len; m++) begin
                group_sum_i = 0;
                group_sum_q = 0;
                for (int g = 0; g < group_size; g++) begin
                    group_sum_i += sample_i(0, m*group_size + g, 1'b0);
                    group_sum_q += sample_q(0, m*group_size + g, 1'b0);
                end
                expected_i[m] = arshift(group_sum_i, k);
                expected_q[m] = arshift(group_sum_q, k);
            end
        end
    endtask

    task automatic arm_trace_avg(
        input int unsigned k,
        input int unsigned stored_len,
        input int unsigned reps
    );
        logic [31:0] start_word;
        begin
            start_word = ((reps & 32'hffff) << 16) | 32'h0000_0003;
            axi_write32(REG_AVG_START, 32'd0);
            repeat (4) @(posedge clk);
            axi_write32(REG_AVG_ADDR, 32'd0);
            axi_write32(REG_AVG_LEN, stored_len);
            axi_write32(REG_AVG_DECIM_LOG2, k);
            axi_write32(REG_AVG_START, start_word);
            repeat ((1 << N_AVG) + 40) @(posedge clk);
        end
    endtask

    task automatic start_avg_read(input int unsigned stored_len);
        begin
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

    task automatic start_buf_read(input int unsigned raw_len);
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
            guard = 0;
            while (!m0_axis_tvalid) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 2000)
                    $fatal(1, "%s[%0d]: timeout waiting for AVG stream", tag, idx);
            end
            full_tag = $sformatf("%s[%0d]", tag, idx);
            check_iq(m0_axis_tdata, expected_i[idx], expected_q[idx], full_tag);
            if (m0_axis_tlast !== expect_last)
                $fatal(1, "%s: expected m0_axis_tlast=%0b got %0b",
                    full_tag, expect_last, m0_axis_tlast);
            @(posedge clk);
            #1;
        end
    endtask

    task automatic expect_raw_sample(input int idx, input string tag, input bit expect_last);
        int guard;
        int signed exp_i;
        int signed exp_q;
        string full_tag;
        begin
            guard = 0;
            exp_i = sample_i(0, idx, 1'b0);
            exp_q = sample_q(0, idx, 1'b0);
            while (!m1_axis_tvalid) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 2000)
                    $fatal(1, "%s[%0d]: timeout waiting for RAW stream", tag, idx);
            end
            full_tag = $sformatf("%s[%0d]", tag, idx);
            check_raw_iq(m1_axis_tdata, exp_i, exp_q, full_tag);
            if (m1_axis_tlast !== expect_last)
                $fatal(1, "%s: expected m1_axis_tlast=%0b got %0b",
                    full_tag, expect_last, m1_axis_tlast);
            @(posedge clk);
            #1;
        end
    endtask

    task automatic read_and_check_avg(input int unsigned stored_len, input string tag);
        begin
            start_avg_read(stored_len);
            for (int idx = 0; idx < stored_len; idx++)
                expect_avg_sample(idx, tag, idx == (stored_len - 1));
            stop_avg_read();
        end
    endtask

    task automatic read_and_check_raw(input int unsigned raw_len, input string tag);
        begin
            start_buf_read(raw_len);
            for (int idx = 0; idx < raw_len; idx++)
                expect_raw_sample(idx, tag, idx == (raw_len - 1));
            stop_buf_read();
        end
    endtask

    task automatic feed_trace_repetition(input int rep, input int unsigned input_len, input int waveform);
        begin
            pulse_trigger();
            for (int n = 0; n < input_len; n++)
                feed_sample(stimulus_i(rep, n, waveform), stimulus_q(rep, n, waveform));
            repeat (30) @(posedge clk);
        end
    endtask

    task automatic run_trace_noise_case(
        input string tag,
        input int unsigned k,
        input int waveform
    );
        int stored_len;
        begin
            stored_len = TRACE_LEN >> k;
            $display("Running %s: K=%0d, reps=%0d, input_len=%0d, stored_len=%0d",
                tag, k, N_REPS, TRACE_LEN, stored_len);

            compute_expected_trace(k, TRACE_LEN, waveform);
            arm_trace_avg(k, stored_len, N_REPS);
            for (int rep = 0; rep < N_REPS; rep++)
                feed_trace_repetition(rep, TRACE_LEN, waveform);

            repeat (400) @(posedge clk);
            axi_write32(REG_AVG_START, 32'd0);
            repeat (20) @(posedge clk);
            read_and_check_avg(stored_len, tag);
        end
    endtask

    task automatic run_raw_buffer_unchanged_test;
        int stored_len;
        begin
            stored_len = TRACE_LEN >> 2;
            $display("Running raw buffer unchanged test: K=2, input_len=%0d, avg_len=%0d",
                TRACE_LEN, stored_len);

            compute_expected_single_rep(2, TRACE_LEN);
            axi_write32(REG_AVG_START, 32'd0);
            axi_write32(REG_BUF_START, 32'd0);
            repeat (6) @(posedge clk);

            axi_write32(REG_BUF_ADDR, 32'd0);
            axi_write32(REG_BUF_LEN, TRACE_LEN);
            axi_write32(REG_BUF_START, 32'd1);
            arm_trace_avg(2, stored_len, 1);

            feed_trace_repetition(0, TRACE_LEN, 0);

            repeat (400) @(posedge clk);
            axi_write32(REG_AVG_START, 32'd0);
            axi_write32(REG_BUF_START, 32'd0);
            repeat (20) @(posedge clk);

            read_and_check_avg(stored_len, "raw-test avg decimated");
            read_and_check_raw(TRACE_LEN, "raw-test raw buffer");
        end
    endtask

    task automatic run_axi_register_test;
        logic [31:0] readback;
        begin
            $display("Running AXI-Lite AVG_DECIM_LOG2 register test");
            axi_write32(REG_AVG_DECIM_LOG2, 32'd2);
            axi_read32(REG_AVG_DECIM_LOG2, readback);
            if (readback[3:0] != 4'd2)
                $fatal(1, "AVG_DECIM_LOG2_REG readback mismatch: %h", readback);
            axi_write32(REG_AVG_DECIM_LOG2, 32'd0);
        end
    endtask

    initial begin
        reset_dut();
        run_axi_register_test();
        run_trace_noise_case("trace-noise K0", 0, 1'b0);
        run_trace_noise_case("trace-noise K1", 1, 0);
        run_trace_noise_case("trace-noise K2", 2, 0);
        run_trace_noise_case("trace-noise negative K2", 2, 1);
        run_trace_noise_case("trace-noise complex-sine K0", 0, 2);
        run_trace_noise_case("trace-noise complex-sine K1", 1, 2);
        run_trace_noise_case("trace-noise complex-sine K2", 2, 2);
        run_raw_buffer_unchanged_test();
        $display("PASS: tb_trace_noise_avg completed trace noise averaging tests");
        $finish;
    end

endmodule
