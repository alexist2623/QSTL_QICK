`timescale 1ns/1ps
module tb_dc_area;
    reg clk=0;
    always #1.6665 clk=~clk;
    reg rstn=0, valid=1, command_valid=0, abort_i=0;
    reg [255:0] raw=0;
    reg [159:0] command=0;
    wire [255:0] output_word;
    wire output_valid, clear_rc, done, enabled, busy, fault;
    wire signed [63:0] area;
    wire [31:0] completed;
    v3_awg_dc_area dut(.clk(clk),.rstn(rstn),.valid_i(valid),.samples_i(raw),
        .command_i(command),.command_valid_i(command_valid),.abort_i(abort_i),
        .samples_o(output_word),.valid_o(output_valid),.clear_rc_o(clear_rc),
        .done_o(done),.enabled_o(enabled),.busy_o(busy),.fault_o(fault),
        .area_o(area),.completed_shots_o(completed));
    reg [255:0] pipeline[5];
    longint signed actual_area=0;
    longint signed expected_area=0;
    longint signed value;
    integer clocks=0, shots=0, fd, pass_words=0;
    reg check_fault=1;
    always @(posedge clk) begin
        pipeline[0]<=raw;
        for(integer i=1;i<5;i=i+1) pipeline[i]<=pipeline[i-1];
        #0.01;
        clocks=clocks+1;
        if(rstn) begin
            if(check_fault && fault) $fatal(1,"unexpected DC fault at clock %0d state %0d",clocks,dut.state);
            if(enabled && output_valid) begin
                for(integer i=0;i<16;i=i+1) begin
                    value=$signed(output_word[16*i+:16]);
                    if(value%4!=0) $fatal(1,"unaligned DAC code");
                    actual_area=actual_area+value/4;
                end
            end
            if(enabled && !busy && !fault && output_valid && clocks>20) begin
                if(output_word!==pipeline[4]) $fatal(1,"bypass latency mismatch at clock %0d",clocks);
                pass_words=pass_words+1;
            end
            if(done) begin
                if(actual_area!=0 || area!=0 || !clear_rc)
                    $fatal(1,"residual area shot %0d: actual %0d hardware %0d",shots,actual_area,area);
                $fwrite(fd,"%0d,%0d,%0d,%0d\n",shots,clocks,actual_area,completed);
                shots=shots+1;
            end
        end
    end
    task automatic tick;
        @(posedge clk); #0.1;
    endtask
    task automatic set_word(input integer code, input bit lanes);
        @(negedge clk);
        for(integer i=0;i<16;i=i+1) begin
            raw[16*i+:16]=(code+(lanes ? i-7 : 0))*4;
            expected_area=expected_area+code+(lanes ? i-7 : 0);
        end
        tick();
    endtask
    task automatic zeros(input integer count);
        @(negedge clk); raw=0;
        repeat(count) tick();
    endtask
    task automatic packet(input integer action, input integer parameter0, input integer words);
        reg [127:0] one;
        @(negedge clk); command=0;
        command[150]=1; command[145:144]=3; command[147:146]=action;
        if(action==2) begin
            one=128'd1<<64;
            command[63:0]=one/(16*64'(words));
            command[95:64]=words;
        end else command[31:0]=parameter0;
        command_valid=1;
        tick();
        @(negedge clk); command_valid=0; command=0;
    endtask
    task automatic balance(input bit time_mode, input integer words);
        integer start, timeout;
        zeros(8);
        if(area!==expected_area || actual_area!==expected_area)
            $fatal(1,"raw sum mismatch hardware %0d reference %0d expected %0d",area,actual_area,expected_area);
        start=shots;
        packet(time_mode ? 2 : 1, 321*4, words);
        timeout=0;
        while(shots==start) begin
            tick(); timeout=timeout+1;
            if(timeout>2000000) $fatal(1,"DC completion timeout");
        end
        zeros(5);
        if(actual_area!=0 || area!=0) $fatal(1,"area leaked after reset");
        expected_area=0;
    endtask
    initial begin
        fd=$fopen("dc_area_shots.csv","w");
        $fwrite(fd,"shot,clock,residual_effective_code_samples,completed\n");
        repeat(10) tick();
        @(negedge clk); rstn=1;
        zeros(12); packet(0,0,0); zeros(8);
        for(integer mode=0;mode<2;mode=mode+1)
            for(integer point=0;point<100;point=point+1)
                for(integer rep=0;rep<2;rep=rep+1) begin
                    for(integer word_index=0;word_index<10+point%7;word_index=word_index+1)
                        set_word(-1500+30*point,1);
                    balance(mode,97+point%5);
                end
        // Sub-clock compensation, including both signs and exactly zero.
        for(integer mode=0;mode<2;mode=mode+1)
            for(integer tiny=-7;tiny<=7;tiny=tiny+7) begin
                @(negedge clk); raw=0; raw[15:0]=tiny*4;
                expected_area=tiny; tick();
                balance(mode,1);
            end
        // Deliberately exceeds signed 32-bit area; no hierarchical seeding.
        repeat(50000) set_word(7000,0);
        if(expected_area<=64'sh7fffffff) $fatal(1,"wide-area coverage missing");
        balance(1,65537);
        // Full-scale signs and all-lane mixed sign extension. Fixed time must
        // allow the asymmetric +8191/-8192 effective DAC limits.
        for(integer mode=0;mode<2;mode=mode+1) begin
            set_word(-8192,0); balance(mode,2);
            set_word(8191,0); balance(mode,2);
            @(negedge clk);
            for(integer lane=0;lane<16;lane=lane+1) begin
                raw[16*lane+:16]=(lane%2 ? 8191 : -8192)*4;
                expected_area=expected_area+(lane%2 ? 8191 : -8192);
            end
            tick();balance(mode,2);
            for(integer word_index=0;word_index<64;word_index=word_index+1) begin
                @(negedge clk);
                for(integer lane=0;lane<16;lane=lane+1) begin
                    value=integer'($urandom_range(0,16383))-8192;
                    raw[16*lane+:16]=value*4;expected_area=expected_area+value;
                end
                tick();
            end
            balance(mode,128);
        end
        if(shots!=415 || completed!=415) $fatal(1,"missing shots %0d",shots);
        $fclose(fd);
        $display("PASS: 100-point voltage sweeps x 2 repeats x both DC modes; %0d shots, zero residual; %0d pass words",shots,pass_words);
        $finish;
    end
    initial begin #100000000; $fatal(1,"watchdog"); end
endmodule
