`timescale 1ns/1ps
// Production AWG SET/RAMP -> area -> IIR, at all three candidate widths.
// This direct-command bench is separate from the later real tProcessor test.
module width_awg_case #(parameter integer WIDTH=64)(
    input wire clk,rstn,command_valid,rc_enabled,
    input wire [159:0] command,
    output wire completed_now
);
    wire [255:0] dac;
    wire valid;
    axis_awg_tuning_v3 #(.DC_AREA_BITS(WIDTH),.EXTRA_Y_PIPE_STAGES(3)) dut(
        .s_axi_aclk(clk),.s_axi_aresetn(rstn),
        .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_awvalid(1'b0),
        .s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),.s_axi_wvalid(1'b0),.s_axi_bready(1'b1),
        .s_axi_araddr(6'd0),.s_axi_arprot(3'd0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1),
        .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(command_valid),
        .m_axis_tdata(dac),.m_axis_tvalid(valid),.m_axis_tready(1'b1));
    awg_v2_raw_checker #(.CHANNEL(WIDTH)) raw_checker(.clk(clk),.rstn(rstn),
        .command_valid(command_valid),.command(command),.raw_samples(dut.core_samples));
    longint signed actual_area=0;
    longint clocks=0,check_zero=-1,shots=0,bypass_checks=0;
    reg [255:0] pass_delay[16];
    reg [15:0] pass_valid=0;
    integer fd;
    assign completed_now=dut.area_done;
    initial fd=$fopen($sformatf("production_width%0d.csv",WIDTH),"w");
    always @(posedge clk) begin
        pass_delay[0]<=dut.core_samples;
        pass_valid<={pass_valid[14:0],!rc_enabled && !dut.area_enabled};
        for(integer i=1;i<16;i=i+1) pass_delay[i]<=pass_delay[i-1];
        #0.02;
        clocks=clocks+1;
        if(rstn) begin
            if(dut.area_fault || dut.rc_clipped) $fatal(1,"production fault width=%0d clock=%0d",WIDTH,clocks);
            if(dut.area_enabled && dut.area_valid)
                for(integer lane=0;lane<16;lane=lane+1)
                    actual_area=actual_area+$signed(dut.area_samples[16*lane+:16])/4;
            if(pass_valid==16'hffff && valid) begin
                if(dac!==pass_delay[15]) $fatal(1,"16-clock bypass mismatch width=%0d",WIDTH);
                bypass_checks=bypass_checks+1;
            end
            if(dut.area_done) begin
                if(actual_area!=0 || dut.area_sum!=0) $fatal(1,"production residual width=%0d actual=%0d",WIDTH,actual_area);
                check_zero=clocks+12; shots=shots+1;
                $fwrite(fd,"%0d,%0d,%0d\n",shots,actual_area,dut.area_sum);
            end
            if(clocks==check_zero) begin
                if(dac!==0 || dut.GEN_RC.rc.integral!==0)
                    $fatal(1,"post-shot IIR/output did not return to zero width=%0d",WIDTH);
            end
        end
    end
    final begin
        $fclose(fd);
        if(shots!=400 || bypass_checks<100) $fatal(1,"production coverage missing");
        $display("PASS PRODUCTION WIDTH %0d: %0d shots, zero residual, %0d bypass latency checks",WIDTH,shots,bypass_checks);
    end
endmodule

module tb_width_awg;
    reg clk=0,rstn=0,command_valid=0,rc_enabled=0;
    always #1.6665 clk=~clk;
    reg [159:0] command=0;
    wire done32,done48,done64;
    integer done_count=0;
    width_awg_case #(.WIDTH(32)) w32(clk,rstn,command_valid,rc_enabled,command,done32);
    width_awg_case #(.WIDTH(48)) w48(clk,rstn,command_valid,rc_enabled,command,done48);
    width_awg_case #(.WIDTH(64)) w64(clk,rstn,command_valid,rc_enabled,command,done64);
    always @(posedge clk) begin
        #0.03;
        if(rstn && (done32!==done48 || done32!==done64)) $fatal(1,"width-dependent completion time");
        if(done64) done_count=done_count+1;
    end
    task automatic tick; @(posedge clk); #0.1; endtask
    task automatic send(input reg [159:0] value);
        @(negedge clk); command=value;command_valid=1;tick();
        @(negedge clk);command=0;command_valid=0;
    endtask
    function automatic [159:0] set_command(input integer value);
        reg [159:0] c; c=0;c[31:0]=value;c[145:144]=1;return c;
    endfunction
    task automatic ramp(input integer start,input integer target,input integer words);
        reg [159:0] c;
        longint signed step;
        c=0;c[31:0]=target;c[86:64]=16*words;c[145:144]=2;
        step=((64'(target)-start)<<<18)/(16*words-1);c[127:96]=step;
        send(c); repeat(words+12) tick();
    endtask
    task automatic dc(input integer action);
        reg [159:0] c;
        reg [127:0] numerator;
        c=0;c[150]=1;c[145:144]=3;c[147:146]=action;
        if(action==1)c[31:0]=1284;
        if(action==2)begin
            numerator=128'd1<<64;c[63:0]=numerator/(16*97);c[95:64]=97;
        end
        send(c);
    endtask
    initial begin
        reg [159:0] rc;
        integer starting_done,timeout,start_value,target;
        repeat(10)tick();@(negedge clk);rstn=1;repeat(30)tick();
        // Normal/bypass paths must keep identical output latency.
        for(integer i=0;i<40;i=i+1)begin send(set_command((i-20)*4));repeat(4)tick();end
        send(set_command(0));repeat(25)tick();
        dc(0);repeat(25)tick();
        rc=0;rc[149]=1;rc[147]=1;rc[146]=1;rc[145:144]=3;
        rc[31:0]=(64'd281474976710656+1440000)/2880000;
        rc_enabled=1;send(rc);repeat(25)tick();
        for(integer mode=1;mode<=2;mode=mode+1)
            for(integer point=0;point<100;point=point+1)
                for(integer rep=0;rep<2;rep=rep+1)begin
                    start_value=(-1500+30*point)*4;target=(800-16*point)*4;
                    send(set_command(start_value));repeat(10+point%7)tick();
                    ramp(start_value,target,1+point%5);
                    send(set_command(0));repeat(20)tick();
                    starting_done=done_count;dc(mode);timeout=0;
                    while(done_count==starting_done)begin
                        tick();timeout=timeout+1;
                        if(timeout>2000)$fatal(1,"production DC timeout");
                    end
                    repeat(20)tick();
                end
        if(done_count!=400)$fatal(1,"missing production shots");
        $finish;
    end
    initial begin #10000000; $fatal(1,"watchdog"); end
endmodule
