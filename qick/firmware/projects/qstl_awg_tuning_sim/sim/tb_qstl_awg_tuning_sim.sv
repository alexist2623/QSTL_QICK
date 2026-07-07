// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps
`default_nettype none

module tb_qstl_awg_tuning_sim;
    localparam int N_PTS = 16;
    localparam int B = 16;
    localparam int FRAC = 16;
    localparam int CMD_WIDTH = 160;
    localparam int SIGGEN_ACLK_MHZ = 100;
    localparam int SIGGEN_SAMPLE_RATE_MHZ = SIGGEN_ACLK_MHZ * N_PTS;
    localparam int SIGGEN_FOUT_MHZ = 25;
    localparam logic [31:0] SIGGEN_FREQ_WORD = 32'h0400_0000;

    localparam bit [1:0] OP_IDLE = 2'd0;
    localparam bit [1:0] OP_SET  = 2'd1;
    localparam bit [1:0] OP_RAMP = 2'd2;

    logic aclk = 1'b0;
    logic aresetn = 1'b0;

    logic [CMD_WIDTH-1:0] awg_s_axis_tdata = '0;
    logic awg_s_axis_tvalid = 1'b0;
    wire  awg_s_axis_tready;

    logic [CMD_WIDTH-1:0] siggen_s_axis_tdata = '0;
    logic siggen_s_axis_tvalid = 1'b0;
    wire  siggen_s_axis_tready;

    wire [255:0] awg_dac_tdata;
    wire         awg_dac_tvalid;
    logic        awg_dac_tready = 1'b1;

    wire [255:0] siggen_dac_tdata;
    wire         siggen_dac_tvalid;
    logic        siggen_dac_tready = 1'b1;

    logic awg_x16_clk = 1'b0;
    logic awg_x16_valid = 1'b0;
    logic signed [15:0] awg_x16_tdata = '0;
    int unsigned awg_x16_word = 0;
    int unsigned awg_x16_lane = 0;
    int unsigned awg_x16_index = 0;

    logic siggen_x16_clk = 1'b0;
    logic siggen_x16_valid = 1'b0;
    logic signed [15:0] siggen_x16_tdata = '0;
    int unsigned siggen_x16_word = 0;
    int unsigned siggen_x16_lane = 0;
    int unsigned siggen_x16_index = 0;

    logic [255:0] awg_serializer_word = '0;
    logic awg_serializer_active = 1'b0;
    int unsigned awg_serializer_lane = 0;
    int unsigned awg_serializer_word_index = 0;

    logic [255:0] siggen_serializer_word = '0;
    logic siggen_serializer_active = 1'b0;
    int unsigned siggen_serializer_lane = 0;
    int unsigned siggen_serializer_word_index = 0;

    int awg_packed_fd;
    int awg_x16_fd;
    int siggen_packed_fd;
    int siggen_x16_fd;
    int compare_fd;
    int events_fd;

    int unsigned cycle_count = 0;
    int unsigned awg_word_count = 0;
    int unsigned siggen_word_count = 0;
    int unsigned siggen_cmd_cycle = 0;
    bit siggen_wait_first_output = 1'b0;
    bit siggen_first_output_logged = 1'b0;

    qstl_awg_tuning_sim_bd_wrapper dut (
        .aclk(aclk),
        .aresetn(aresetn),
        .awg_s_axis_tdata(awg_s_axis_tdata),
        .awg_s_axis_tvalid(awg_s_axis_tvalid),
        .awg_s_axis_tready(awg_s_axis_tready),
        .siggen_s_axis_tdata(siggen_s_axis_tdata),
        .siggen_s_axis_tvalid(siggen_s_axis_tvalid),
        .siggen_s_axis_tready(siggen_s_axis_tready),
        .awg_dac_axis_tdata(awg_dac_tdata),
        .awg_dac_axis_tvalid(awg_dac_tvalid),
        .awg_dac_axis_tready(awg_dac_tready),
        .siggen_dac_axis_tdata(siggen_dac_tdata),
        .siggen_dac_axis_tvalid(siggen_dac_tvalid),
        .siggen_dac_axis_tready(siggen_dac_tready)
    );

    always #5.000 aclk = ~aclk;
    always #0.312 awg_x16_clk = ~awg_x16_clk;
    always #0.312 siggen_x16_clk = ~siggen_x16_clk;

    function automatic logic [CMD_WIDTH-1:0] make_cmd(
        input bit [1:0] op,
        input int signed target,
        input int unsigned duration
    );
        logic [CMD_WIDTH-1:0] cmd;
        begin
            cmd = '0;
            cmd[31:0] = target[31:0];
            cmd[95:64] = duration[31:0];
            cmd[145:144] = op;
            make_cmd = cmd;
        end
    endfunction

    function automatic logic [CMD_WIDTH-1:0] make_siggen_cmd(
        input logic [31:0] freq,
        input logic [31:0] phase,
        input logic [15:0] addr,
        input logic [15:0] gain,
        input logic [15:0] nsamp,
        input logic [1:0] outsel,
        input logic mode,
        input logic stdysel,
        input logic phrst
    );
        logic [CMD_WIDTH-1:0] cmd;
        begin
            cmd = '0;
            cmd[31:0] = freq;
            cmd[63:32] = phase;
            cmd[79:64] = addr;
            cmd[111:96] = gain;
            cmd[143:128] = nsamp;
            cmd[145:144] = outsel;
            cmd[146] = mode;
            cmd[147] = stdysel;
            cmd[148] = phrst;
            make_siggen_cmd = cmd;
        end
    endfunction

    function automatic int signed clamp_i64_to_i16(input longint signed value);
        begin
            if (value > 32767) begin
                clamp_i64_to_i16 = 32767;
            end else if (value < -32768) begin
                clamp_i64_to_i16 = -32768;
            end else begin
                clamp_i64_to_i16 = int'(value);
            end
        end
    endfunction

    function automatic logic [255:0] scalar_word(input int signed sample);
        logic [255:0] word;
        logic [15:0] sample_bits;
        int lane;
        begin
            word = '0;
            sample_bits = sample[15:0];
            for (lane = 0; lane < N_PTS; lane = lane + 1) begin
                word[lane*B +: B] = sample_bits;
            end
            scalar_word = word;
        end
    endfunction

    function automatic logic signed [31:0] calc_step(
        input int signed current,
        input int signed target,
        input int unsigned duration
    );
        longint signed numerator;
        begin
            if (duration <= 1) begin
                calc_step = '0;
            end else begin
                numerator = (longint'(target - current)) <<< FRAC;
                calc_step = numerator / longint'(duration - 1);
            end
        end
    endfunction

    function automatic logic [255:0] expected_ramp_word(
        input int signed start_sample,
        input int signed target_sample,
        input int unsigned duration,
        input logic signed [31:0] step,
        input int unsigned word_offset
    );
        logic [255:0] word;
        longint signed base_fixed;
        longint signed fixed_value;
        int unsigned sample_index;
        int signed sample;
        int lane;
        begin
            word = '0;
            base_fixed = longint'(start_sample) <<< FRAC;
            for (lane = 0; lane < N_PTS; lane = lane + 1) begin
                sample_index = word_offset * N_PTS + lane;
                if ((duration <= 1) || (sample_index >= duration - 1)) begin
                    sample = target_sample;
                end else begin
                    fixed_value = base_fixed + (longint'(sample_index) * longint'(step));
                    sample = clamp_i64_to_i16(fixed_value >>> FRAC);
                end
                word[lane*B +: B] = sample[15:0];
            end
            expected_ramp_word = word;
        end
    endfunction

    task automatic expect_no_x(input logic [255:0] data, input string label);
        begin
            if ($isunknown(data)) begin
                $fatal(1, "%s contains X/Z at cycle %0d: %h", label, cycle_count, data);
            end
        end
    endtask

    task automatic expect_awg_word(input logic [255:0] expected, input string label);
        begin
            @(posedge aclk);
            #1;
            if (awg_dac_tvalid !== 1'b1) begin
                $fatal(1, "AWG m_axis_tvalid low during %s at cycle %0d", label, cycle_count);
            end
            expect_no_x(awg_dac_tdata, "AWG m_axis_tdata");
            if (awg_dac_tdata !== expected) begin
                $fatal(1, "%s mismatch at cycle %0d: expected=%h actual=%h", label, cycle_count, expected, awg_dac_tdata);
            end
        end
    endtask

    task automatic expect_awg_current_word(input logic [255:0] expected, input string label);
        begin
            #1;
            if (awg_dac_tvalid !== 1'b1) begin
                $fatal(1, "AWG m_axis_tvalid low during %s at cycle %0d", label, cycle_count);
            end
            expect_no_x(awg_dac_tdata, "AWG m_axis_tdata");
            if (awg_dac_tdata !== expected) begin
                $fatal(1, "%s mismatch at cycle %0d: expected=%h actual=%h", label, cycle_count, expected, awg_dac_tdata);
            end
        end
    endtask

    task automatic log_latency_event(
        input string path,
        input string label,
        input int unsigned setting_cycle,
        input int unsigned output_cycle,
        input string detail
    );
        begin
            $fwrite(events_fd, "%s,%s,%0d,%0d,%0d,%s\n",
                    path, label, setting_cycle, output_cycle,
                    output_cycle - setting_cycle, detail);
        end
    endtask

    task automatic send_awg_cmd(input logic [CMD_WIDTH-1:0] cmd, output int unsigned accept_cycle);
        begin
            @(negedge aclk);
            awg_s_axis_tdata <= cmd;
            awg_s_axis_tvalid <= 1'b1;
            @(posedge aclk);
            #1;
            if (awg_s_axis_tready !== 1'b1) begin
                $fatal(1, "AWG command interface was not ready at cycle %0d", cycle_count);
            end
            accept_cycle = cycle_count;
            @(negedge aclk);
            awg_s_axis_tvalid <= 1'b0;
            awg_s_axis_tdata <= '0;
        end
    endtask

    task automatic send_siggen_cmd(input logic [CMD_WIDTH-1:0] cmd, output int unsigned accept_cycle);
        begin
            @(negedge aclk);
            siggen_s_axis_tdata <= cmd;
            siggen_s_axis_tvalid <= 1'b1;
            do begin
                @(posedge aclk);
                #1;
            end while (siggen_s_axis_tready !== 1'b1);
            accept_cycle = cycle_count;
            siggen_cmd_cycle = cycle_count;
            siggen_wait_first_output = 1'b1;
            siggen_first_output_logged = 1'b0;
            @(negedge aclk);
            siggen_s_axis_tvalid <= 1'b0;
            siggen_s_axis_tdata <= '0;
        end
    endtask

    task automatic run_set(input int signed target);
        int unsigned cmd_cycle;
        begin
            send_awg_cmd(make_cmd(OP_SET, target, 0), cmd_cycle);
            expect_awg_current_word(scalar_word(target), "SET command word");
            log_latency_event("awg", $sformatf("SET_%0d", target), cmd_cycle, cycle_count,
                              $sformatf("target=%0d", target));
            expect_awg_word(scalar_word(target), "SET hold word");
        end
    endtask

    task automatic run_ramp(input int signed current, input int signed target, input int unsigned duration);
        logic signed [31:0] step;
        int unsigned word_count;
        int unsigned idx;
        int unsigned cmd_cycle;
        begin
            step = calc_step(current, target, duration);
            word_count = (duration + N_PTS - 1) / N_PTS;
            send_awg_cmd(make_cmd(OP_RAMP, target, duration), cmd_cycle);
            expect_awg_current_word(expected_ramp_word(current, target, duration, step, 0), "RAMP command word");
            log_latency_event("awg", $sformatf("RAMP_%0d_first", target), cmd_cycle, cycle_count,
                              $sformatf("from=%0d target=%0d duration=%0d", current, target, duration));
            for (idx = 1; idx < word_count; idx = idx + 1) begin
                expect_awg_word(expected_ramp_word(current, target, duration, step, idx), "RAMP word");
            end
            expect_awg_word(scalar_word(target), "RAMP final hold");
            log_latency_event("awg", $sformatf("RAMP_%0d_final", target), cmd_cycle, cycle_count,
                              $sformatf("from=%0d target=%0d duration=%0d", current, target, duration));
        end
    endtask

    task automatic open_csvs;
        begin
            awg_packed_fd = $fopen("qstl_awg_tuning_sim_awg_packed.csv", "w");
            awg_x16_fd = $fopen("qstl_awg_tuning_sim_awg_x16.csv", "w");
            siggen_packed_fd = $fopen("qstl_awg_tuning_sim_siggen_packed.csv", "w");
            siggen_x16_fd = $fopen("qstl_awg_tuning_sim_siggen_x16.csv", "w");
            compare_fd = $fopen("qstl_awg_tuning_sim_compare.csv", "w");
            events_fd = $fopen("qstl_awg_tuning_sim_events.csv", "w");

            if ((awg_packed_fd == 0) || (awg_x16_fd == 0) || (siggen_packed_fd == 0) ||
                (siggen_x16_fd == 0) || (compare_fd == 0) || (events_fd == 0)) begin
                $fatal(1, "Failed to open one or more CSV output files");
            end

            $fwrite(awg_packed_fd, "cycle,word_index,tvalid,tready,tdata_hex\n");
            $fwrite(awg_x16_fd, "sample_index,slow_word,lane,value\n");
            $fwrite(siggen_packed_fd, "cycle,word_index,tvalid,tready,tdata_hex\n");
            $fwrite(siggen_x16_fd, "sample_index,slow_word,lane,value\n");
            $fwrite(compare_fd, "sample_index,awg_value,siggen_value,diff\n");
            $fwrite(events_fd, "path,label,setting_cycle,output_cycle,delay_cycles,detail\n");
        end
    endtask

    task automatic close_csvs;
        begin
            $fclose(awg_packed_fd);
            $fclose(awg_x16_fd);
            $fclose(siggen_packed_fd);
            $fclose(siggen_x16_fd);
            $fclose(compare_fd);
            $fclose(events_fd);
        end
    endtask

    always_ff @(posedge aclk) begin
        cycle_count <= cycle_count + 1;
    end

    always @(posedge aclk) begin
        #1;
        if (!aresetn) begin
            awg_word_count <= 0;
            siggen_word_count <= 0;
            awg_serializer_active <= 1'b0;
            siggen_serializer_active <= 1'b0;
            siggen_wait_first_output <= 1'b0;
        end else begin
            if (awg_dac_tvalid && awg_dac_tready) begin
                $fwrite(awg_packed_fd, "%0d,%0d,%0d,%0d,%064h\n",
                        cycle_count, awg_word_count, awg_dac_tvalid, awg_dac_tready, awg_dac_tdata);
                awg_serializer_word <= awg_dac_tdata;
                awg_serializer_word_index <= awg_word_count;
                awg_serializer_lane <= 0;
                awg_serializer_active <= 1'b1;
                awg_word_count <= awg_word_count + 1;
            end

            if (siggen_dac_tvalid && siggen_dac_tready) begin
                $fwrite(siggen_packed_fd, "%0d,%0d,%0d,%0d,%064h\n",
                        cycle_count, siggen_word_count, siggen_dac_tvalid, siggen_dac_tready, siggen_dac_tdata);
                siggen_serializer_word <= siggen_dac_tdata;
                siggen_serializer_word_index <= siggen_word_count;
                siggen_serializer_lane <= 0;
                siggen_serializer_active <= 1'b1;
                if (siggen_wait_first_output && !siggen_first_output_logged) begin
                    log_latency_event("siggen", "DDS_25MHz_first", siggen_cmd_cycle, cycle_count,
                                      $sformatf("freq_word=0x%08h fout_mhz=%0d fs_mhz=%0d",
                                                SIGGEN_FREQ_WORD, SIGGEN_FOUT_MHZ, SIGGEN_SAMPLE_RATE_MHZ));
                    siggen_first_output_logged <= 1'b1;
                    siggen_wait_first_output <= 1'b0;
                end
                siggen_word_count <= siggen_word_count + 1;
            end

            if (awg_dac_tvalid && awg_dac_tready && siggen_dac_tvalid && siggen_dac_tready) begin
                for (int cmp_lane = 0; cmp_lane < N_PTS; cmp_lane = cmp_lane + 1) begin
                    automatic int signed awg_sample;
                    automatic int signed siggen_sample;
                    awg_sample = $signed(awg_dac_tdata[cmp_lane*B +: B]);
                    siggen_sample = $signed(siggen_dac_tdata[cmp_lane*B +: B]);
                    $fwrite(compare_fd, "%0d,%0d,%0d,%0d\n",
                            awg_word_count * N_PTS + cmp_lane,
                            awg_sample, siggen_sample, awg_sample - siggen_sample);
                end
            end
        end
    end

    always_ff @(posedge awg_x16_clk) begin
        if (!aresetn) begin
            awg_x16_valid <= 1'b0;
            awg_x16_tdata <= '0;
            awg_x16_word <= 0;
            awg_x16_lane <= 0;
            awg_x16_index <= 0;
        end else if (awg_serializer_active) begin
            awg_x16_valid <= 1'b1;
            awg_x16_word <= awg_serializer_word_index;
            awg_x16_lane <= awg_serializer_lane;
            awg_x16_index <= awg_serializer_word_index * N_PTS + awg_serializer_lane;
            awg_x16_tdata <= $signed(awg_serializer_word[awg_serializer_lane*B +: B]);
            $fwrite(awg_x16_fd, "%0d,%0d,%0d,%0d\n",
                    awg_serializer_word_index * N_PTS + awg_serializer_lane,
                    awg_serializer_word_index,
                    awg_serializer_lane,
                    $signed(awg_serializer_word[awg_serializer_lane*B +: B]));

            if (awg_serializer_lane == N_PTS - 1) begin
                awg_serializer_active <= 1'b0;
                awg_serializer_lane <= 0;
            end else begin
                awg_serializer_lane <= awg_serializer_lane + 1;
            end
        end else begin
            awg_x16_valid <= 1'b0;
        end
    end

    always_ff @(posedge siggen_x16_clk) begin
        if (!aresetn) begin
            siggen_x16_valid <= 1'b0;
            siggen_x16_tdata <= '0;
            siggen_x16_word <= 0;
            siggen_x16_lane <= 0;
            siggen_x16_index <= 0;
        end else if (siggen_serializer_active) begin
            siggen_x16_valid <= 1'b1;
            siggen_x16_word <= siggen_serializer_word_index;
            siggen_x16_lane <= siggen_serializer_lane;
            siggen_x16_index <= siggen_serializer_word_index * N_PTS + siggen_serializer_lane;
            siggen_x16_tdata <= $signed(siggen_serializer_word[siggen_serializer_lane*B +: B]);
            $fwrite(siggen_x16_fd, "%0d,%0d,%0d,%0d\n",
                    siggen_serializer_word_index * N_PTS + siggen_serializer_lane,
                    siggen_serializer_word_index,
                    siggen_serializer_lane,
                    $signed(siggen_serializer_word[siggen_serializer_lane*B +: B]));

            if (siggen_serializer_lane == N_PTS - 1) begin
                siggen_serializer_active <= 1'b0;
                siggen_serializer_lane <= 0;
            end else begin
                siggen_serializer_lane <= siggen_serializer_lane + 1;
            end
        end else begin
            siggen_x16_valid <= 1'b0;
        end
    end

    always @(posedge aclk) begin
        #1;
        if (aresetn) begin
            if (awg_s_axis_tready !== 1'b1) begin
                $fatal(1, "AWG s_axis_tready is not high at cycle %0d", cycle_count);
            end
            if (awg_dac_tvalid !== 1'b1) begin
                $fatal(1, "AWG m_axis_tvalid is not high at cycle %0d", cycle_count);
            end
            expect_no_x(awg_dac_tdata, "AWG m_axis_tdata");
            if (siggen_dac_tvalid) begin
                expect_no_x(siggen_dac_tdata, "signal-generator m_axis_tdata");
            end
        end
    end

    initial begin
        open_csvs();

        awg_dac_tready = 1'b1;
        siggen_dac_tready = 1'b1;
        aresetn = 1'b0;
        repeat (8) @(posedge aclk);
        @(negedge aclk);
        aresetn = 1'b1;

        begin
            int unsigned siggen_accept_cycle;
            send_siggen_cmd(make_siggen_cmd(
            SIGGEN_FREQ_WORD,
            32'h0000_0000,
            16'h0000,
            16'sd30000,
            16'd96,
            2'd1,
            1'b0,
            1'b0,
            1'b1
            ), siggen_accept_cycle);
        end

        repeat (2) expect_awg_word(scalar_word(0), "RESET zero hold");

        run_set(1000);
        run_ramp(1000, 2000, 64);
        run_set(-500);
        run_ramp(-500, -1500, 64);
        run_set(0);

        repeat (32) @(posedge aclk);
        if (siggen_word_count == 0) begin
            $fatal(1, "axis_signal_gen_v6_0 produced no valid output for %0d MHz command", SIGGEN_FOUT_MHZ);
        end
        close_csvs();
        $display("PASS: qstl_awg_tuning_sim completed. Captured %0d AWG words and %0d real axis_signal_gen_v6 words at %0d MHz (Fs=%0d MHz, freq_word=0x%08h).",
                 awg_word_count, siggen_word_count, SIGGEN_FOUT_MHZ, SIGGEN_SAMPLE_RATE_MHZ, SIGGEN_FREQ_WORD);
        $finish;
    end
endmodule

`default_nettype wire
