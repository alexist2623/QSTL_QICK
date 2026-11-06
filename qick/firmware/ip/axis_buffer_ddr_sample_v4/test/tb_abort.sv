`timescale 1ns/1ps
module tb_abort;
    tb_axis_buffer_ddr_sample_v4 #(.RUN_REGRESSION(0)) env();
    task automatic finish_abort;
        logic [31:0] value;
        integer limit;
        limit = 0;
        do begin
            env.axi_read32(14, value);
            if (++limit > 2000) $fatal(1, "abort did not acknowledge");
        end while (value[0]);
        if (value[31:16] != 16'hAB04 || !value[1]) $fatal(1, "bad abort status %h", value);
        env.read_status(value);
        if (value[3:0] != 0) $fatal(1, "capture status not cleared after abort: %h", value);
        if (env.aw_count || env.w_count || env.resp_pending || env.m_axi_bvalid)
            $fatal(1, "acknowledged with AXI transaction outstanding");
    endtask
    task automatic rearm_clean;
        env.set_axi_write_stalls(0,0,0);
        env.arm_capture(32'h800, 3, 1, 0);
        env.pulse_trigger();
        for (int k=0;k<3;k++) env.send_word_compliant(env.sample64(900+k));
        env.wait_done(); env.wait_not_busy();
        env.check(completed_count()==2,"rearm word count");
        env.expect_write(0,32'h800,{env.sample64(901),env.sample64(900)});
        env.expect_write(1,32'h820,{128'd0,env.sample64(902)});
    endtask
    function automatic integer completed_count;
        return env.completed_count;
    endfunction
    initial begin
        logic [31:0] value;
        env.reset_dut();
        env.axi_write32(14,1); finish_abort(); rearm_clean();
        // Waiting for trigger, partly packed event, and outstanding AW/W/B.
        for (int mode=0;mode<6;mode++) begin
            env.arm_capture(0,16,3000,0);
            if (mode==2) env.set_axi_write_stalls(1000,0,0);
            if (mode==3) env.set_axi_write_stalls(0,1000,0);
            if (mode==4) env.set_axi_write_stalls(0,0,1000);
            if (mode!=0) begin
                env.pulse_trigger();
                for(int k=0;k<((mode==1)?1:5);k++) env.send_word_compliant(env.sample64(k));
            end
            env.axi_write32(14,1);
            env.axi_read32(14,value);
            if (!value[0]) $fatal(1,"abort must expose pending before ack");
            // An ARM and duplicate abort while pending must not start work.
            env.axi_write32(0,1); env.axi_write32(14,1);
            if(mode>=2 && mode<=4) begin
                env.wait_axi(20); env.axi_read32(14,value);
                if(!value[0]) $fatal(1,"premature acknowledgement during AXI stall");
            end
            finish_abort(); rearm_clean();
        end
        // Stop a queued delayed trigger; no late event may leak into the next arm.
        env.arm_capture_delay(0,3,3000,0,500);
        env.pulse_trigger(); env.axi_write32(14,1); finish_abort();
        env.wait_s_axis(550); rearm_clean();
        // Repeat at varying asynchronous phases with randomized write stalls.
        for(int trial=0;trial<30;trial++) begin
            env.arm_capture(0,7,1000,0);
            env.set_axi_write_stalls($urandom_range(0,45),$urandom_range(0,45),$urandom_range(0,45));
            env.pulse_trigger();
            for(int k=0;k<3;k++) env.send_word_compliant(env.sample64(k+trial));
            env.wait_axi($urandom_range(0,9));
            env.axi_write32(14,1); finish_abort(); rearm_clean();
        end
        // The legacy reset alias must have the same drain guarantee.
        env.arm_capture(0,5,500,0);
        env.set_axi_write_stalls(60,90,80); env.pulse_trigger();
        env.send_word_compliant(env.sample64(0)); env.send_word_compliant(env.sample64(1));
        env.axi_write32(0,2); finish_abort(); rearm_clean();
        if(env.errors) $fatal(1,"AXI/data assertions failed: %0d",env.errors);
        $display("PASS: abort idle/missing-trigger/partial/queued/AW/W/B stalls/duplicate/rearm/random CDC, legacy safe reset");
        $finish;
    end
    initial begin #2000000; $fatal(1,"abort watchdog"); end
endmodule
