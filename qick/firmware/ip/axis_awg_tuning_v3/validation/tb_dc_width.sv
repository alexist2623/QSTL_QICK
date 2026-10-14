`timescale 1ns/1ps
// Identical 100-point fixed-increment waveform for each accumulator width.
// Production area engine + production RC IIR; independent per-sample analog RC.
module tb_dc_width #(parameter integer AREA_WIDTH=64, POINTS=100);
    reg clk=0;
    always #1.6665 clk=~clk;
    reg rstn=0, command_valid=0;
    reg [255:0] raw=0;
    reg [159:0] command=0;
    wire [255:0] pre_rc, dac;
    wire pre_valid, clear_rc, done, enabled, busy, fault, dac_valid, clipped;
    wire signed [63:0] area;
    wire [31:0] completed;
    localparam [31:0] COEF=(64'd281474976710656+1440000)/2880000;
    v3_awg_dc_area #(.AREA_WIDTH(AREA_WIDTH)) dut(
        .clk(clk),.rstn(rstn),.valid_i(1'b1),.samples_i(raw),
        .command_i(command),.command_valid_i(command_valid),.abort_i(1'b0),
        .samples_o(pre_rc),.valid_o(pre_valid),.clear_rc_o(clear_rc),
        .done_o(done),.enabled_o(enabled),.busy_o(busy),.fault_o(fault),
        .area_o(area),.completed_shots_o(completed));
    v3_awg_rc_precomp rc(.clk(clk),.rstn(rstn),.valid_i(pre_valid),.active_i(1'b1),
        .enable_i(1'b1),.clear_i(clear_rc),.coefficient_i(COEF),
        .samples_i(pre_rc),.samples_o(dac),.valid_o(dac_valid),.clipped_o(clipped));
    reg [255:0] target_delay[11];
    longint signed measured_area=0, target_area=0, before_area=0;
    longint signed lane_value;
    longint clocks=0;
    integer fd, overflow_cases=0, valid_cases=0, done_before, comp_words;
    bit measuring=0, was_fault=0;
    real capacitor=0.0, analog_value=0.0, decay;
    real err, max_error=0.0, end_value=0.0, max_good_error=0.0;
    real sample, target;
    always @(posedge clk) begin
        target_delay[0]<=pre_rc;
        for(integer i=1;i<11;i=i+1) target_delay[i]<=target_delay[i-1];
        #0.01;
        clocks=clocks+1;
        if(rstn && measuring) begin
            if(fault) was_fault=1;
            if(pre_valid) for(integer i=0;i<16;i=i+1) begin
                lane_value=$signed(pre_rc[16*i+:16]);
                measured_area=measured_area+lane_value/4;
            end
            if(clipped) $fatal(1,"unexpected DAC clipping");
        end
        if(rstn && dac_valid) for(integer i=0;i<16;i=i+1) begin
            sample=$signed(dac[16*i+:16]);
            target=$signed(target_delay[10][16*i+:16]);
            // Exact zero-order-hold step of a separate physical high-pass RC.
            // The capacitor is NEVER reset between shots or sweep points.
            analog_value=sample-capacitor;
            capacitor=sample+(capacitor-sample)*decay;
            if(measuring) begin
                err=(analog_value-target)*800.0/32768.0;
                if(err<0) err=-err;
                if(err>max_error) max_error=err;
                end_value=analog_value*800.0/32768.0;
            end
        end
    end
    task automatic tick;
        @(posedge clk); #0.1;
    endtask
    task automatic wait_words(input integer count);
        repeat(count) tick();
    endtask
    task automatic hold_code(input integer code, input integer count);
        @(negedge clk);
        for(integer i=0;i<16;i=i+1) raw[16*i+:16]=code*4;
        target_area=target_area+64'(code)*16*count;
        wait_words(count);
    endtask
    task automatic packet(input integer action, input integer word_count);
        reg [127:0] numerator;
        @(negedge clk); command=0;
        command[150]=1; command[145:144]=3; command[147:146]=action;
        if(action==2) begin
            numerator=128'd1<<64;
            command[63:0]=numerator/(16*64'(word_count));
            command[95:64]=word_count;
        end else if(action==1) command[31:0]=8192; // 2048 effective codes: 200 mV
        command_valid=1; tick();
        @(negedge clk); command_valid=0; command=0;
    endtask
    initial begin
        decay=$exp(-1.0/(4.8e9*300e-6));
        fd=$fopen("width_sweep.csv","w");
        $fwrite(fd,"width,mode,point,target_area,hardware_area_before_dc,overflow,residual_area,completed,max_rc_error_mv,end_rc_mv\n");
        wait_words(10); @(negedge clk); rstn=1; wait_words(30);
        for(integer mode=0;mode<2;mode=mode+1) begin
            for(integer point=0;point<POINTS;point=point+1) begin
                packet(0,0); wait_words(25);
                measured_area=0; target_area=0; was_fault=0; max_error=0; measuring=1;
                done_before=completed;
                // 100 us / 10 us / 400 us, 300 MHz fabric, 16 samples/word.
                // Fixed integer increments intentionally match current sweeps.
                hold_code(-614+12*point,30000);
                hold_code(-205+4*point,3000);
                hold_code(-1229+24*point,120000);
                @(negedge clk); raw=0; wait_words(10);
                before_area=area;
                if(!was_fault && (area!=target_area || measured_area!=target_area))
                    $fatal(1,"area collection mismatch width=%0d point=%0d",AREA_WIDTH,point);
                packet(mode ? 2 : 1,60000);
                comp_words=mode ? 60000 : ((target_area<0 ? -target_area : target_area)+32767)/32768;
                wait_words(comp_words+50);
                if(!was_fault) begin
                    if(measured_area!=0 || area!=0 || completed!=done_before+1)
                        $fatal(1,"DC residual width=%0d point=%0d area=%0d",AREA_WIDTH,point,measured_area);
                    valid_cases=valid_cases+1;
                    if(max_error>max_good_error) max_good_error=max_error;
                    if(AREA_WIDTH>32 && max_error>0.09765625)
                        $fatal(1,"RC error exceeds one effective DAC LSB: %f mV",max_error);
                end else begin
                    overflow_cases=overflow_cases+1;
                    if(AREA_WIDTH>32) $fatal(1,"unexpected wide accumulator overflow");
                end
                $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%.12f,%.12f\n",
                    AREA_WIDTH,mode,point,target_area,before_area,was_fault,measured_area,
                    completed-done_before,max_error,end_value);
                $fflush(fd);
                measuring=0;
                if(point%10==9) begin
                    $fflush(fd);
                    $display("PROGRESS width=%0d mode=%0d point=%0d clock=%0d",AREA_WIDTH,mode,point,clocks);
                end
            end
        end
        $fclose(fd);
        if(AREA_WIDTH==32 && overflow_cases==0) $fatal(1,"32-bit overflow coverage missing");
        $display("PASS WIDTH %0d: valid=%0d overflow=%0d max_RC_error_valid=%f mV",AREA_WIDTH,valid_cases,overflow_cases,max_good_error);
        $finish;
    end
    initial begin #1000000000000.0; $fatal(1,"watchdog"); end
endmodule

// Separate tops avoid cmd.exe/batch-file splitting of NAME=VALUE arguments.
module tb_width32; tb_dc_width #(.AREA_WIDTH(32)) test(); endmodule
module tb_width48; tb_dc_width #(.AREA_WIDTH(48)) test(); endmodule
module tb_width64; tb_dc_width #(.AREA_WIDTH(64)) test(); endmodule
module tb_width_smoke; tb_dc_width #(.AREA_WIDTH(48),.POINTS(1)) test(); endmodule
