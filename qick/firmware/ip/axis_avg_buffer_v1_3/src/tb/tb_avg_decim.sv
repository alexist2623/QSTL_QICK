module tb;

    localparam int N_AVG = 4;
    localparam int N_BUF = 4;
    localparam int B = 16;
    localparam int MAX_AVG_DECIM_LOG2 = 6;

    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic rstn;

    // Standalone decimator DUT.
    logic decim_clear;
    logic [3:0] decim_log2;
    logic decim_din_valid;
    logic [2*B-1:0] decim_din;
    logic decim_dout_valid;
    logic [2*B-1:0] decim_dout;

    avg_decimator_iq #(
        .B(B),
        .MAX_AVG_DECIM_LOG2(MAX_AVG_DECIM_LOG2)
    ) decim_dut (
        .rstn(rstn),
        .clk(clk),
        .clear_i(decim_clear),
        .decim_log2_i(decim_log2),
        .din_valid_i(decim_din_valid),
        .din_i(decim_din),
        .dout_valid_o(decim_dout_valid),
        .dout_i(decim_dout)
    );

    // axis_avg_buffer DUT.
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

    function automatic [2*B-1:0] pack_iq(input int signed i, input int signed q);
        logic signed [B-1:0] ii;
        logic signed [B-1:0] qq;
        begin
            ii = i;
            qq = q;
            pack_iq = {qq, ii};
        end
    endfunction

    function automatic [4*B-1:0] pack_acc_iq(input int signed i, input int signed q);
        logic signed [2*B-1:0] ii;
        logic signed [2*B-1:0] qq;
        begin
            ii = i;
            qq = q;
            pack_acc_iq = {qq, ii};
        end
    endfunction

    task automatic check_decim_output(input bit expect_valid, input int signed exp_i, input int signed exp_q, input string label);
        logic [2*B-1:0] expected;
        begin
            expected = pack_iq(exp_i, exp_q);
            if (expect_valid && !decim_dout_valid)
                $fatal(1, "%s: expected decimator output", label);
            if (!expect_valid && decim_dout_valid)
                $fatal(1, "%s: unexpected decimator output %h", label, decim_dout);
            if (expect_valid && decim_dout !== expected)
                $fatal(1, "%s: expected %h got %h", label, expected, decim_dout);
        end
    endtask

    task automatic drive_decim(input int signed i, input int signed q, input bit expect_valid, input int signed exp_i, input int signed exp_q, input string label);
        begin
            @(negedge clk);
            decim_din <= pack_iq(i, q);
            decim_din_valid <= 1'b1;
            @(posedge clk);
            #1;
            check_decim_output(expect_valid, exp_i, exp_q, label);
            @(negedge clk);
            decim_din_valid <= 1'b0;
            decim_din <= '0;
        end
    endtask

    task automatic clear_decimator;
        begin
            @(negedge clk);
            decim_clear <= 1'b1;
            @(posedge clk);
            #1;
            if (decim_dout_valid)
                $fatal(1, "decimator produced output while clear was asserted");
            @(negedge clk);
            decim_clear <= 1'b0;
        end
    endtask

    task automatic axi_write(input int unsigned reg_index, input logic [31:0] data);
        int guard;
        begin
            @(negedge clk);
            s_axi_awaddr  <= reg_index[5:0] << 2;
            s_axi_wdata   <= data;
            s_axi_awvalid <= 1'b1;
            s_axi_wvalid  <= 1'b1;
            s_axi_bready  <= 1'b1;
            guard = 0;
            do begin
                @(posedge clk);
                guard++;
                if (guard > 100)
                    $fatal(1, "AXI write address/data timeout for reg %0d", reg_index);
            end while (!(s_axi_awready && s_axi_wready));
            @(negedge clk);
            s_axi_awvalid <= 1'b0;
            s_axi_wvalid  <= 1'b0;
            guard = 0;
            do begin
                @(posedge clk);
                guard++;
                if (guard > 100)
                    $fatal(1, "AXI write response timeout for reg %0d", reg_index);
            end while (!s_axi_bvalid);
            @(negedge clk);
            s_axi_bready <= 1'b0;
        end
    endtask

    task automatic axi_read(input int unsigned reg_index, output logic [31:0] data);
        int guard;
        begin
            @(negedge clk);
            s_axi_araddr  <= reg_index[5:0] << 2;
            s_axi_arvalid <= 1'b1;
            s_axi_rready  <= 1'b1;
            guard = 0;
            do begin
                @(posedge clk);
                guard++;
                if (guard > 100)
                    $fatal(1, "AXI read address timeout for reg %0d", reg_index);
            end while (!s_axi_arready);
            @(negedge clk);
            s_axi_arvalid <= 1'b0;
            guard = 0;
            do begin
                @(posedge clk);
                guard++;
                if (guard > 100)
                    $fatal(1, "AXI read data timeout for reg %0d", reg_index);
            end while (!s_axi_rvalid);
            data = s_axi_rdata;
            @(negedge clk);
            s_axi_rready <= 1'b0;
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

    task automatic arm_trace(input int unsigned address, input int unsigned length, input int unsigned decim_k);
        begin
            axi_write(0, 32'd0);
            repeat (4) @(posedge clk);
            axi_write(1, address);
            axi_write(2, length);
            axi_write(15, decim_k);
            axi_write(0, 32'h0001_0003);
            repeat (40) @(posedge clk);
        end
    endtask

    task automatic wait_capture_done;
        begin
            repeat (120) @(posedge clk);
            axi_write(0, 32'd0);
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic expect_avg_word(input logic [4*B-1:0] expected, input string label);
        int guard;
        begin
            guard = 0;
            while (!m0_axis_tvalid) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 1000)
                    $fatal(1, "%s: timeout waiting for AVG stream", label);
            end
            if (m0_axis_tdata !== expected)
                $fatal(1, "%s: expected AVG %h got %h", label, expected, m0_axis_tdata);
            @(posedge clk);
            #1;
        end
    endtask

    task automatic start_avg_read(input int unsigned address, input int unsigned length);
        begin
            axi_write(3, 32'd0);
            axi_write(4, address);
            axi_write(5, length);
            axi_write(3, 32'd1);
        end
    endtask

    task automatic stop_avg_read;
        begin
            axi_write(3, 32'd0);
            repeat (6) @(posedge clk);
        end
    endtask

    task automatic expect_buf_word(input logic [2*B-1:0] expected, input string label);
        int guard;
        begin
            guard = 0;
            while (!m1_axis_tvalid) begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 1000)
                    $fatal(1, "%s: timeout waiting for BUF stream", label);
            end
            if (m1_axis_tdata !== expected)
                $fatal(1, "%s: expected BUF %h got %h", label, expected, m1_axis_tdata);
            @(posedge clk);
            #1;
        end
    endtask

    task automatic start_buf_read(input int unsigned address, input int unsigned length);
        begin
            axi_write(9, 32'd0);
            axi_write(10, address);
            axi_write(11, length);
            axi_write(9, 32'd1);
        end
    endtask

    task automatic stop_buf_read;
        begin
            axi_write(9, 32'd0);
            repeat (6) @(posedge clk);
        end
    endtask

    task automatic run_decimator_unit_tests;
        begin
            $display("Running avg_decimator_iq directed tests");
            decim_log2 = 4'd0;
            clear_decimator();
            drive_decim(3, -7, 1'b1, 3, -7, "K0 sample 0");
            drive_decim(-2, 9, 1'b1, -2, 9, "K0 sample 1");

            decim_log2 = 4'd1;
            clear_decimator();
            drive_decim(0, 10, 1'b0, 0, 0, "K1 first");
            drive_decim(2, 14, 1'b1, 1, 12, "K1 second");
            drive_decim(4, 18, 1'b0, 0, 0, "K1 third");
            drive_decim(6, 22, 1'b1, 5, 20, "K1 fourth");

            decim_log2 = 4'd2;
            clear_decimator();
            drive_decim(0, 0, 1'b0, 0, 0, "K2 a0");
            drive_decim(4, -4, 1'b0, 0, 0, "K2 a1");
            drive_decim(8, -8, 1'b0, 0, 0, "K2 a2");
            drive_decim(12, -12, 1'b1, 6, -6, "K2 a3");

            decim_log2 = 4'd1;
            clear_decimator();
            drive_decim(-1, -4, 1'b0, 0, 0, "signed first");
            drive_decim(-2, -5, 1'b1, -2, -5, "signed arithmetic shift");

            decim_log2 = 4'd1;
            clear_decimator();
            drive_decim(100, 0, 1'b0, 0, 0, "alignment stale half group");
            clear_decimator();
            drive_decim(0, 0, 1'b0, 0, 0, "alignment new group first");
            drive_decim(10, 0, 1'b1, 5, 0, "alignment new group second");

            decim_log2 = 4'd2;
            clear_decimator();
            drive_decim(1, 1, 1'b0, 0, 0, "partial 0");
            drive_decim(2, 2, 1'b0, 0, 0, "partial 1");
            drive_decim(3, 3, 1'b0, 0, 0, "partial 2");
            clear_decimator();
            $display("avg_decimator_iq directed tests passed");
        end
    endtask

    task automatic run_axi_register_test;
        logic [31:0] readback;
        begin
            $display("Running AVG_DECIM_LOG2 AXI-Lite register test");
            axi_write(15, 32'd2);
            axi_read(15, readback);
            if (readback[3:0] !== 4'd2)
                $fatal(1, "AVG_DECIM_LOG2_REG readback mismatch: %h", readback);
            axi_write(15, 32'd0);
        end
    endtask

    task automatic run_trace_top_tests;
        begin
            $display("Running top-level trace AVG decimation tests");

            arm_trace(0, 4, 0);
            pulse_trigger();
            feed_sample(0, 10);
            feed_sample(2, 12);
            feed_sample(4, 14);
            feed_sample(6, 16);
            wait_capture_done();
            start_avg_read(0, 4);
            expect_avg_word(pack_acc_iq(0, 10), "K0 trace y0");
            expect_avg_word(pack_acc_iq(2, 12), "K0 trace y1");
            expect_avg_word(pack_acc_iq(4, 14), "K0 trace y2");
            expect_avg_word(pack_acc_iq(6, 16), "K0 trace y3");
            stop_avg_read();

            arm_trace(0, 2, 1);
            pulse_trigger();
            feed_sample(0, 10);
            feed_sample(2, 14);
            feed_sample(4, 18);
            feed_sample(6, 22);
            wait_capture_done();
            start_avg_read(0, 2);
            expect_avg_word(pack_acc_iq(1, 12), "K1 trace y0");
            expect_avg_word(pack_acc_iq(5, 20), "K1 trace y1");
            stop_avg_read();

            arm_trace(0, 2, 2);
            pulse_trigger();
            feed_sample(0, 0);
            feed_sample(4, -4);
            feed_sample(8, -8);
            feed_sample(12, -12);
            feed_sample(16, -16);
            feed_sample(20, -20);
            feed_sample(24, -24);
            feed_sample(28, -28);
            wait_capture_done();
            start_avg_read(0, 2);
            expect_avg_word(pack_acc_iq(6, -6), "K2 trace y0");
            expect_avg_word(pack_acc_iq(22, -22), "K2 trace y1");
            stop_avg_read();

            arm_trace(0, 2, 1);
            pulse_trigger();
            feed_sample(-1, -4);
            feed_sample(-2, -5);
            feed_sample(3, 7);
            feed_sample(4, 8);
            wait_capture_done();
            start_avg_read(0, 2);
            expect_avg_word(pack_acc_iq(-2, -5), "signed trace y0");
            expect_avg_word(pack_acc_iq(3, 7), "signed trace y1");
            stop_avg_read();

            arm_trace(0, 1, 1);
            pulse_trigger();
            feed_sample(100, 0);
            feed_sample(102, 0);
            wait_capture_done();
            start_avg_read(0, 1);
            expect_avg_word(pack_acc_iq(101, 0), "alignment first capture");
            stop_avg_read();

            arm_trace(0, 1, 1);
            pulse_trigger();
            feed_sample(0, 0);
            feed_sample(10, 0);
            wait_capture_done();
            start_avg_read(0, 1);
            expect_avg_word(pack_acc_iq(5, 0), "alignment second capture");
            stop_avg_read();

            $display("top-level trace AVG decimation tests passed");
        end
    endtask

    task automatic run_raw_buffer_unchanged_test;
        begin
            $display("Running raw BUF unchanged test with AVG_DECIM_LOG2=2");
            axi_write(0, 32'd0);
            axi_write(6, 32'd0);
            repeat (4) @(posedge clk);
            axi_write(15, 32'd2);
            axi_write(7, 32'd0);
            axi_write(8, 32'd4);
            axi_write(6, 32'd1);
            repeat (6) @(posedge clk);
            pulse_trigger();
            feed_sample(10, -1);
            feed_sample(20, -2);
            feed_sample(30, -3);
            feed_sample(40, -4);
            repeat (40) @(posedge clk);
            axi_write(6, 32'd0);
            start_buf_read(0, 4);
            expect_buf_word(pack_iq(10, -1), "raw buf x0");
            expect_buf_word(pack_iq(20, -2), "raw buf x1");
            expect_buf_word(pack_iq(30, -3), "raw buf x2");
            expect_buf_word(pack_iq(40, -4), "raw buf x3");
            stop_buf_read();
            $display("raw BUF unchanged test passed");
        end
    endtask

    initial begin
        rstn = 1'b0;
        decim_clear = 1'b1;
        decim_log2 = 4'd0;
        decim_din_valid = 1'b0;
        decim_din = '0;
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

        repeat (10) @(posedge clk);
        rstn = 1'b1;
        repeat (6) @(posedge clk);
        decim_clear = 1'b0;

        run_decimator_unit_tests();
        run_axi_register_test();
        run_trace_top_tests();
        run_raw_buffer_unchanged_test();

        $display("PASS: axis_avg_buffer_v1_3 AVG_DECIM_LOG2 tests passed");
        $finish;
    end

endmodule
