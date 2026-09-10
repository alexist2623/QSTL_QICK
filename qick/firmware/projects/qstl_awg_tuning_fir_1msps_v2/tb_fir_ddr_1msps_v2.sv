// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

// Exercise the real continuous FIR -> DDR V2 path, including the BD trigger
// synchronizer. Reuse the DDR regression's independent AXI memory responder.
module tb_fir_ddr_1msps_v2;
    localparam int SAMPLES = 13;
    localparam int SHOTS = 4;
    localparam int SHOT_CYCLES = 7500; // 40 kHz at 300 MHz
    tb_axis_buffer_ddr_sample_v2 #(
        .RUN_REGRESSION(1'b0), .SOURCE_HALF_PERIOD_NS(5.0/3.0)
    ) harness();

    logic raw_trigger = 0;
    wire synced_trigger;
    logic [31:0] input_data = 0;
    wire input_ready;
    wire [31:0] fir_data;
    wire fir_valid;
    wire fir_capture_trigger;
    int cycle = 0;
    int previous_valid_cycle = -1;
    int valid_count = 0;
    bit monitor_capture = 0;
    bit previous_raw_trigger = 0;
    int configured_delay = 0;
    int due_cycle [0:SHOTS-1];
    int accepted = 0;
    int shot = 0;
    int sample_index = 0;
    int first_cycle [0:SHOTS-1];
    logic [255:0] expected [0:SHOTS*2-1];

    axis_trigger_sync_v1 trigger_sync (
        .aclk(harness.s_axis_aclk), .aresetn(harness.s_axis_aresetn),
        .trigger_in(raw_trigger), .trigger_pulse(synced_trigger)
    );
    axis_fir_decim_300to1_v1 fir (
        .aclk(harness.s_axis_aclk), .aresetn(harness.s_axis_aresetn),
        .trigger(1'b0), .capture_trigger(fir_capture_trigger),
        .s_axis_tdata(input_data), .s_axis_tvalid(harness.s_axis_aresetn),
        .s_axis_tready(input_ready), .s_axis_tlast(1'b0),
        .m_axis_tdata(fir_data), .m_axis_tvalid(fir_valid),
        .m_axis_tready(harness.s_axis_tready), .m_axis_tlast()
    );

    // Override the harness's synthetic source; its reset/task assignments do
    // not drive the stream used in this integration test.
    initial begin
        force harness.s_axis_tdata = fir_data;
        force harness.s_axis_tvalid = fir_valid;
        force harness.trigger = synced_trigger;
    end

    always @(negedge harness.s_axis_aclk) begin
        // Distinct signed I/Q with transitions across capture boundaries.
        input_data = ((cycle / 6000) % 2) ? 32'hFB5004B0 : 32'h0190FE70;
    end

    always @(posedge harness.s_axis_aclk) begin
        cycle = cycle + 1;
        if (harness.s_axis_aresetn) begin
            harness.check(input_ready, "continuous 300 MSPS source remains ready");
            harness.check(!fir_capture_trigger, "FIR trigger alignment stays disabled");
            if (fir_valid) begin
                if (previous_valid_cycle >= 0)
                    harness.check(cycle - previous_valid_cycle == 300,
                        "FIR output spacing stays 300 clocks across triggers and re-arm");
                previous_valid_cycle = cycle;
                valid_count++;
            end
            if (monitor_capture) begin
                if (raw_trigger && !previous_raw_trigger) begin
                    // From the first raw-trigger sampling edge: three edges
                    // through axis_trigger_sync_v1, then two through DDR V2.
                    due_cycle[accepted] = cycle + 5 + configured_delay;
                    accepted++;
                end
                if (fir_valid && shot < accepted && cycle >= due_cycle[shot]) begin
                    if (sample_index == 0) begin
                        first_cycle[shot] = cycle;
                        harness.check(cycle - due_cycle[shot] < 300,
                            "capture uses first FIR valid at or after programmed deadline");
                    end
                    expected[shot*2 + sample_index/8][32*(sample_index%8) +: 32] = fir_data;
                    sample_index++;
                    if (sample_index == SAMPLES) begin
                        sample_index = 0;
                        shot++;
                    end
                end
            end
            previous_raw_trigger = raw_trigger;
        end
    end

    task automatic run_capture(input int delay_cycles);
        logic [31:0] status;
        int trigger_cycle;
        begin
            configured_delay = delay_cycles;
            accepted = 0;
            shot = 0;
            sample_index = 0;
            for (int i = 0; i < SHOTS*2; i++) expected[i] = 0;
            harness.arm_capture_delay(0, SAMPLES, SHOTS, 0, delay_cycles);
            monitor_capture = 1;
            for (int i = 0; i < SHOTS; i++) begin
                @(negedge harness.s_axis_aclk);
                raw_trigger = 1;
                trigger_cycle = cycle;
                repeat (4) @(negedge harness.s_axis_aclk);
                raw_trigger = 0;
                while (cycle < trigger_cycle + SHOT_CYCLES - 1)
                    @(negedge harness.s_axis_aclk);
            end
            harness.wait_done();
            harness.wait_not_busy();
            monitor_capture = 0;
            harness.check(accepted == SHOTS && shot == SHOTS,
                "all four 40 kHz triggers captured with no FIR restart limit");
            harness.check(harness.completed_count == SHOTS*2,
                "13-sample captures produce two padded AXI words per trigger");
            for (int i = 0; i < SHOTS*2; i++) begin
                harness.check(harness.completed_addr[i] == i*32,
                    "DDR word address and event order");
                harness.check(harness.completed_data[i] === expected[i],
                    $sformatf("delay=%0d word=%0d matches independently selected FIR samples", delay_cycles, i));
            end
            harness.read_status(status);
            harness.check(!status[2], "no queue or data overflow at 1 MSPS");
            $display("CAPTURE delay=%0d cycles: %0d shots, %0d samples/shot, first wait=%0d cycles",
                delay_cycles, shot, SAMPLES, first_cycle[0] - due_cycle[0]);
        end
    endtask

    initial begin
        harness.reset_dut();
        repeat (20000) @(negedge harness.s_axis_aclk);
        run_capture(0);
        // Delay exceeds the trigger period, so at least two future events
        // coexist in the timestamp queue. No FIR reset occurs between arms.
        run_capture(8677);
        harness.check(valid_count > 200, "sustained 1 MSPS FIR stream observed");
        if (harness.errors != 0)
            $fatal(1, "FAIL: FIR DDR 1 MSPS V2 had %0d errors", harness.errors);
        $display("PASS: FIR DDR 1 MSPS V2 continuous phase, 40 kHz triggers, programmable delay, packing and CDC");
        $finish;
    end
endmodule
