`timescale 1ns/1ps
module tb_square_dds;
    reg clk=0, resetn=0, valid=0, mute=0;
    reg [159:0] cmd=0;
    wire enabled;
    wire [255:0] samples;
    always #1.666667 clk=~clk;
    square_dds dut(.aclk(clk), .aresetn(resetn), .command(cmd),
        .command_valid(valid), .mute(mute), .enabled(enabled), .samples(samples));
    reg [31:0] phi=0, f=0, p=0;
    integer amp=0, en=0, clr=0, checked=0;
    reg [255:0] expected[4];
    reg [255:0] word_samples;
    reg [31:0] lane_phi;
    integer mag;
    // Independent scalar reference: integrate each sample, never f*t.
    always @(posedge clk) begin
        if (!resetn) begin
            phi=0; f=0; p=0; amp=0; en=0; clr=0;
            for(integer j=0;j<4;j=j+1) expected[j]=0;
            #0.01;
            if (samples !== 0) $fatal(1,"reset output");
        end else begin
            if(clr) phi=0;
            for(integer k=0;k<16;k=k+1) begin
                lane_phi=phi+p;
                mag=en ? amp : 0;
                word_samples[16*k +: 16]=lane_phi[31] ? -mag : mag;
                phi=phi+f;
            end
            for(integer j=3;j>0;j=j-1) expected[j]=expected[j-1];
            expected[0]=word_samples;
            clr=0;
            if(valid) begin
                f=cmd[31:0]; p=cmd[63:32];
                amp=cmd[95:64]>32764 ? 32764 : (cmd[95:64]&32'h7ffc);
                en=cmd[128]; clr=cmd[129];
            end
            if(mute) en=0;
            #0.01;
            if(samples !== expected[3]) begin
                $display("got %h expected %h sample %0d", samples,expected[3],checked);
                $fatal(1,"DDS scalar reference mismatch");
            end
            checked=checked+16;
        end
    end
    task send(input [31:0] freq, phase, amplitude, control);
        @(negedge clk); valid=1; cmd={control,32'd0,amplitude,phase,freq};
    endtask
    task idle(input integer n);
        @(negedge clk); valid=0; repeat(n) @(negedge clk);
    endtask
    initial begin
        repeat(4) @(negedge clk); resetn=1;
        send(32'h00008bd0,0,800,3); idle(20000); // approximately 40 kHz
        send(32'h0a222222,0,800,1); idle(100); // 190 MHz at 4.8 GSPS
        send(32'h0a222222,0,1920,1); idle(100); // amplitude only
        send(32'h0a222222,32'h80000000,1920,1); idle(100); // phase only
        send(32'h71234567,32'hffffffff,32764,1); idle(100);
        send(0,32'h80000000,320,3); idle(20); // negative DC after clear
        send(0,0,320,1); idle(20); // positive DC without clear
        // Back-to-back atomic updates and both wrap directions.
        for(integer n=0;n<2000;n=n+1)
            send($random,$random,($random & 32'hffff),n%29==0 ? 3 : 1);
        idle(20);
        @(negedge clk); mute=1; @(negedge clk); mute=0; idle(20);
        send(32'hfffffff0,32'hfffffffa,4,1); idle(20);
        send(32'h12345678,0,0,1); idle(20);
        send(32'h12345678,0,100,0); idle(20);
        @(negedge clk); resetn=0; repeat(4) @(negedge clk); resetn=1;
        idle(10);
        $display("PASS: square DDS, %0d scalar samples checked",checked);
        $finish;
    end
    initial begin #2000000; $fatal(1,"timeout"); end
endmodule
