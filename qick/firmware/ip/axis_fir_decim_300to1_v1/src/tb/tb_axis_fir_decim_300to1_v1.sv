// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

module tb_axis_fir_decim_300to1_v1;

    localparam int CLK_HALF_NS = 2;

    logic aclk = 1'b0;
    logic aresetn = 1'b0;
    logic trigger = 1'b0;
    wire  capture_trigger;

    logic [31:0] s_axis_tdata = '0;
    logic        s_axis_tvalid = 1'b0;
    wire         s_axis_tready;
    logic        s_axis_tlast = 1'b0;

    wire [31:0]  m_axis_tdata;
    wire         m_axis_tvalid;
    logic        m_axis_tready = 1'b1;
    wire         m_axis_tlast;

    logic ddr_trigger_meta;
    logic ddr_trigger_sync;
    logic ddr_trigger_sync_d;
    logic ddr_capture_active;
    logic ddr_first_word_valid;
    logic [31:0] ddr_first_word;

    string vector_dir;
    int errors = 0;
    int max_lane_error = 0;

    axis_fir_decim_300to1_v1 dut (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .trigger       (trigger),
        .capture_trigger(capture_trigger),
        .s_axis_tdata  (s_axis_tdata),
        .s_axis_tvalid (s_axis_tvalid),
        .s_axis_tready (s_axis_tready),
        .s_axis_tlast  (s_axis_tlast),
        .m_axis_tdata  (m_axis_tdata),
        .m_axis_tvalid (m_axis_tvalid),
        .m_axis_tready (m_axis_tready),
        .m_axis_tlast  (m_axis_tlast)
    );

    always #(CLK_HALF_NS) aclk = ~aclk;

    // Source-clock portion of axis_buffer_ddr_sample_v1: synchronize the FIR
    // capture trigger, arm capture, and retain the first valid FIR word.
    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            ddr_trigger_meta     <= 1'b0;
            ddr_trigger_sync     <= 1'b0;
            ddr_trigger_sync_d   <= 1'b0;
            ddr_capture_active   <= 1'b0;
            ddr_first_word_valid <= 1'b0;
            ddr_first_word       <= '0;
        end else begin
            ddr_trigger_meta   <= capture_trigger;
            ddr_trigger_sync   <= ddr_trigger_meta;
            ddr_trigger_sync_d <= ddr_trigger_sync;

            if (ddr_trigger_sync && !ddr_trigger_sync_d)
                ddr_capture_active <= 1'b1;

            if (ddr_capture_active && m_axis_tvalid && !ddr_first_word_valid) begin
                ddr_first_word       <= m_axis_tdata;
                ddr_first_word_valid <= 1'b1;
                ddr_capture_active   <= 1'b0;
            end
        end
    end

    function automatic string vec_path(input string leaf);
        vec_path = {vector_dir, "/", leaf};
    endfunction

    function automatic int abs_int(input int value);
        abs_int = (value < 0) ? -value : value;
    endfunction

    function automatic int signed lane0(input logic [31:0] word);
        logic [15:0] raw;
        begin
            raw = word[15:0];
            lane0 = $signed(raw);
        end
    endfunction

    function automatic int signed lane1(input logic [31:0] word);
        logic [15:0] raw;
        begin
            raw = word[31:16];
            lane1 = $signed(raw);
        end
    endfunction

    task automatic check(input bit cond, input string message);
        if (!cond) begin
            errors++;
            $error("%s", message);
        end
    endtask

    function automatic int count_hex_lines(input string filename);
        int fd;
        int count;
        string line;
        begin
            count = 0;
            fd = $fopen(filename, "r");
            if (fd == 0)
                $fatal(1, "Could not open %s", filename);
            while ($fgets(line, fd))
                if (line.len() > 0)
                    count++;
            $fclose(fd);
            count_hex_lines = count;
        end
    endfunction

    task automatic load_hex_file(input string filename, output logic [31:0] data[]);
        int fd;
        int code;
        int idx;
        int value;
        begin
            data = new[count_hex_lines(filename)];
            fd = $fopen(filename, "r");
            if (fd == 0)
                $fatal(1, "Could not open %s", filename);
            idx = 0;
            while (!$feof(fd)) begin
                code = $fscanf(fd, "%h\n", value);
                if (code == 1) begin
                    data[idx] = value[31:0];
                    idx++;
                end
            end
            $fclose(fd);
            check(idx == data.size(), $sformatf("hex load count mismatch for %s", filename));
        end
    endtask

    task automatic reset_dut();
        begin
            s_axis_tvalid <= 1'b0;
            s_axis_tdata  <= '0;
            s_axis_tlast  <= 1'b0;
            m_axis_tready <= 1'b1;
            trigger <= 1'b0;
            aresetn <= 1'b0;
            repeat (8) @(posedge aclk);
            check(m_axis_tvalid === 1'b0, "m_axis_tvalid must be low during reset");
            check(capture_trigger === 1'b0, "capture_trigger must be low during reset");
            aresetn <= 1'b1;
            repeat (8) @(posedge aclk);
            check(m_axis_tvalid === 1'b0, "m_axis_tvalid must remain low immediately after reset");
        end
    endtask

    task automatic capture_trigger_compensation_case();
        localparam int EXPECTED_SKIPPED_OUTPUTS = 28;
        localparam int EXPECTED_RESIDUAL_INPUT_SAMPLES = 22;
        logic [31:0] input_vec[];
        logic [31:0] expected_vec[];
        int outputs_seen;
        int timeout;
        bit trigger_seen;
        begin
            $display("TEST: FIR group-delay-compensated DDR capture trigger");
            load_hex_file(vec_path("tone_input.txt"), input_vec);
            load_hex_file(vec_path("tone_expected.txt"), expected_vec);
            reset_dut();
            pulse_trigger();

            outputs_seen = 0;
            timeout = 0;
            trigger_seen = 1'b0;
            fork
                drive_inputs(input_vec, 1'b0);
                begin
                    while (!trigger_seen && timeout < 2_000_000) begin
                        @(negedge aclk);
                        if (m_axis_tvalid)
                            outputs_seen++;
                        if (capture_trigger) begin
                            trigger_seen = 1'b1;
                            check(outputs_seen == EXPECTED_SKIPPED_OUTPUTS,
                                  $sformatf("capture trigger followed %0d outputs, expected %0d",
                                            outputs_seen, EXPECTED_SKIPPED_OUTPUTS));
                        end
                        timeout++;
                    end

                    check(trigger_seen, "capture trigger must be emitted");
                    @(negedge aclk);
                    check(capture_trigger === 1'b0, "capture trigger must be one clock wide");

                    timeout = 0;
                    while (!ddr_first_word_valid && timeout < 2_000) begin
                        @(negedge aclk);
                        timeout++;
                    end
                    check(ddr_first_word_valid, "DDR trigger synchronizer must capture a compensated FIR output");
                    check(ddr_first_word === expected_vec[EXPECTED_SKIPPED_OUTPUTS],
                          $sformatf("first DDR-visible word mismatch: actual=%08x expected=%08x",
                                    ddr_first_word, expected_vec[EXPECTED_SKIPPED_OUTPUTS]));
                    $display("  skipped %0d FIR outputs; residual alignment=%0d input samples",
                             EXPECTED_SKIPPED_OUTPUTS, EXPECTED_RESIDUAL_INPUT_SAMPLES);
                end
            join
        end
    endtask

    task automatic pulse_trigger();
        begin
            @(negedge aclk);
            trigger <= 1'b1;
            repeat (4) @(posedge aclk);
            @(negedge aclk);
            trigger <= 1'b0;
            repeat (4) @(posedge aclk);
        end
    endtask

    task automatic drive_inputs(input logic [31:0] input_vec[], input bit valid_gaps);
        int idx;
        int cyc;
        logic [31:0] held_word;
        bit was_stalled;
        begin
            idx = 0;
            cyc = 0;
            held_word = '0;
            was_stalled = 1'b0;

            while (idx < input_vec.size()) begin
                @(negedge aclk);
                if (valid_gaps && ((cyc % 7) == 3 || (cyc % 19) == 5)) begin
                    s_axis_tvalid = 1'b0;
                end else begin
                    s_axis_tvalid = 1'b1;
                    s_axis_tdata = input_vec[idx];
                end

                if (s_axis_tvalid && !s_axis_tready) begin
                    if (was_stalled)
                        check(s_axis_tdata === held_word, "source data changed while s_axis_tvalid && !s_axis_tready");
                    held_word = s_axis_tdata;
                    was_stalled = 1'b1;
                end else begin
                    was_stalled = 1'b0;
                end

                @(posedge aclk);
                if (s_axis_tvalid && s_axis_tready) begin
                    check(!$isunknown(s_axis_tdata), "input transfer contains X/Z");
                    idx++;
                end
                cyc++;
            end

            @(negedge aclk);
            s_axis_tvalid = 1'b0;
            s_axis_tdata = '0;
        end
    endtask

    task automatic monitor_outputs(input logic [31:0] expected_vec[], input bit toggle_ready, output int observed_count);
        int cyc;
        int exp_idx;
        int e0;
        int e1;
        begin
            cyc = 0;
            exp_idx = 0;
            m_axis_tready = 1'b1;

            while (exp_idx < expected_vec.size() && cyc < 2_000_000) begin
                @(negedge aclk);
                if (toggle_ready)
                    m_axis_tready = !(((cyc % 17) >= 5 && (cyc % 17) <= 7) || ((cyc % 31) == 11));
                else
                    m_axis_tready = 1'b1;

                if (m_axis_tvalid) begin
                    check(!$isunknown(m_axis_tdata), "output transfer contains X/Z");
                    check(m_axis_tlast === 1'b0, "m_axis_tlast must remain low");
                    if (m_axis_tdata !== expected_vec[exp_idx]) begin
                        e0 = abs_int(lane0(m_axis_tdata) - lane0(expected_vec[exp_idx]));
                        e1 = abs_int(lane1(m_axis_tdata) - lane1(expected_vec[exp_idx]));
                        if (e0 > max_lane_error) max_lane_error = e0;
                        if (e1 > max_lane_error) max_lane_error = e1;
                        errors++;
                        $error("Output mismatch idx=%0d actual=%08x expected=%08x lane_err=(%0d,%0d)",
                               exp_idx, m_axis_tdata, expected_vec[exp_idx], e0, e1);
                    end
                    exp_idx++;
                end
                cyc++;
            end

            observed_count = exp_idx;
            check(exp_idx == expected_vec.size(), $sformatf("observed %0d outputs, expected %0d", exp_idx, expected_vec.size()));
            m_axis_tready = 1'b1;
        end
    endtask

    task automatic run_vector_case(
        input string tag,
        input string input_file,
        input string expected_file,
        input bit valid_gaps,
        input bit backpressure
    );
        logic [31:0] input_vec[];
        logic [31:0] expected_vec[];
        int observed;
        begin
            $display("TEST: %s", tag);
            load_hex_file(vec_path(input_file), input_vec);
            load_hex_file(vec_path(expected_file), expected_vec);
            reset_dut();
            pulse_trigger();
            fork
                drive_inputs(input_vec, valid_gaps);
                monitor_outputs(expected_vec, backpressure, observed);
            join
            repeat (600) @(posedge aclk);
            check(m_axis_tvalid === 1'b0, {tag, ": no extra output after expected sequence"});
            $display("  observed %0d outputs", observed);
        end
    endtask

    task automatic trigger_alignment_case();
        logic [31:0] pre_vec[];
        logic [31:0] input_vec[];
        logic [31:0] expected_vec[];
        int observed;
        begin
            $display("TEST: trigger phase alignment with preserved FIR history");
            load_hex_file(vec_path("trigger_align_pre_input.txt"), pre_vec);
            load_hex_file(vec_path("trigger_align_post_input.txt"), input_vec);
            load_hex_file(vec_path("trigger_align_expected.txt"), expected_vec);
            reset_dut();

            drive_inputs(pre_vec, 1'b0);
            repeat (20) @(posedge aclk);

            pulse_trigger();
            fork
                drive_inputs(input_vec, 1'b0);
                monitor_outputs(expected_vec, 1'b0, observed);
            join
            repeat (600) @(posedge aclk);
            check(m_axis_tvalid === 1'b0, "trigger alignment: no extra output after expected sequence");
            $display("  observed %0d outputs after trigger phase realignment", observed);
        end
    endtask

    task automatic reset_mid_stream_case();
        logic [31:0] input_vec[];
        logic [31:0] expected_vec[];
        int idx;
        int observed;
        begin
            $display("TEST: reset mid-stream");
            load_hex_file(vec_path("reset_after_input.txt"), input_vec);
            load_hex_file(vec_path("reset_after_expected.txt"), expected_vec);
            reset_dut();
            pulse_trigger();
            idx = 0;
            while (idx < 1200) begin
                @(negedge aclk);
                s_axis_tvalid = 1'b1;
                s_axis_tdata = input_vec[idx];
                @(posedge aclk);
                if (s_axis_tvalid && s_axis_tready)
                    idx++;
            end
            reset_dut();
            pulse_trigger();
            fork
                drive_inputs(input_vec, 1'b0);
                monitor_outputs(expected_vec, 1'b0, observed);
            join
            $display("  observed %0d outputs after reset", observed);
        end
    endtask

    initial begin
        if (!$value$plusargs("VECTOR_DIR=%s", vector_dir))
            vector_dir = "../../vectors";

        $display("Vector directory: %s", vector_dir);

        reset_dut();
        run_vector_case("impulse", "impulse_input.txt", "impulse_expected.txt", 1'b0, 1'b0);
        run_vector_case("tone", "tone_input.txt", "tone_expected.txt", 1'b0, 1'b0);
        run_vector_case("noisy", "noisy_input.txt", "noisy_expected.txt", 1'b0, 1'b0);
        run_vector_case("tone with output ready toggled", "tone_input.txt", "tone_expected.txt", 1'b0, 1'b1);
        run_vector_case("valid gaps", "valid_gap_input.txt", "valid_gap_expected.txt", 1'b1, 1'b0);
        trigger_alignment_case();
        capture_trigger_compensation_case();
        reset_mid_stream_case();

        if (errors == 0) begin
            $display("PASS: axis_fir_decim_300to1_v1 max_lane_error=%0d", max_lane_error);
            $finish;
        end

        $fatal(1, "FAIL: axis_fir_decim_300to1_v1 errors=%0d max_lane_error=%0d", errors, max_lane_error);
    end

endmodule
