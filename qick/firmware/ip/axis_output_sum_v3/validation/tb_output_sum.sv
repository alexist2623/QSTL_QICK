`timescale 1ns/1ps
module tb_output_sum;
    reg clk=0; always #1.666667 clk=~clk;
    reg rstn=0;
    reg [255:0] a=0,b=0;
    reg va=0,vb=0,ready=1;
    wire [255:0] y,by;
    wire valid,bvalid,clip,bclip,ar,br;
    axis_output_sum_v3 dut(clk,rstn,a,va,ar,b,vb,br,y,valid,ready,clip);
    axis_output_sum_v3 #(.BYPASS(1)) bypass(clk,rstn,a,va,,b,vb,,by,bvalid,ready,bclip);
    reg [255:0] history[0:5];
    reg [5:0] history_valid=0;
    integer samples=0,positive_clips=0,negative_clips=0,rounding_checks=0;
    integer k,j,v1,v2,total,code,seed=1234567;
    reg [255:0] expect_y=0,expect_b=0,next_y,next_b;
    reg expect_v=0,expect_bv=0,expect_clip=0,expect_bc=0,next_c,next_bc;
    function automatic [15:0] reference(input integer value);
        integer result;
        begin
            if(value>32764) result=32764;
            else if(value< -32768) result=-32768;
            else begin
                // Floor division after ties-to-positive rounding. Independent
                // integer oracle; do not wrap before the bound comparison.
                result=value+2;
                if(result<0) result=-((-result+3)/4)*4;
                else result=(result/4)*4;
            end
            reference=result;
        end
    endfunction
    task check_cycle;
        begin
            next_y=0;next_b=0;next_c=0;next_bc=0;
            for(j=0;j<16;j=j+1) begin
                v1=history_valid[5] ? $signed(history[5][16*j+:16]) : 0;
                v2=vb ? $signed(b[16*j+:16]) : 0;
                total=v1+v2;
                next_y[16*j+:16]=reference(total);
                next_b[16*j+:16]=reference(v1);
                next_c=next_c || total>32764 || total< -32768;
                next_bc=next_bc || v1>32764 || v1< -32768;
                if(total>32764) positive_clips=positive_clips+1;
                if(total< -32768) negative_clips=negative_clips+1;
                if(total>=-32768 && total<=32764 && (total%4)!=0) rounding_checks=rounding_checks+1;
            end
            @(posedge clk);#0.01;
            if(y!==expect_y || by!==expect_b || valid!==expect_v || bvalid!==expect_bv
                || clip!==expect_clip || bclip!==expect_bc || ar!==1 || br!==1)
                $fatal(1,"value/latency/valid/clip mismatch at word %0d",k);
            samples=samples+16;
            expect_y=next_y;expect_b=next_b;
            expect_v=history_valid[5]|vb;expect_bv=history_valid[5];
            for(integer h=5;h>0;h=h-1) history[h]=history[h-1];
            history[0]=a;history_valid={history_valid[4:0],va};
            expect_clip=next_c;expect_bc=next_bc;
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);
        rstn=1;
        // Every signed input code with endpoint/zero/opposite/random partners,
        // mixed independently per lane; no carries may cross lane boundaries.
        for(k=0;k<65536;k=k+1) begin
            va=1;vb=1;ready=(k%3)!=0;
            for(j=0;j<16;j=j+1) begin
                a[16*j+:16]=k-32768;
                case(j%8)
                    0:b[16*j+:16]=16'h7ffc;
                    1:b[16*j+:16]=16'h8000;
                    2:b[16*j+:16]=0;
                    3:b[16*j+:16]=-(k-32768);
                    4:b[16*j+:16]=16'h7fff;
                    5:b[16*j+:16]=16'hffff;
                    6:b[16*j+:16]=16'h0001;
                    7:b[16*j+:16]=$random(seed);
                endcase
            end
            check_cycle;
        end
        for(k=0;k<4096;k=k+1) begin
            va=k%2;vb=(k/2)%2;ready=~ready;
            for(j=0;j<16;j=j+1) begin a[16*j+:16]=$random(seed);b[16*j+:16]=$random(seed);end
            check_cycle;
        end
                // Reset while the delayed AWG pipeline contains live nonzero words.
        va=1;vb=1;a={16{16'h7ffc}};b={16{16'h8000}};
        repeat(6)check_cycle;
        rstn=0;@(posedge clk);#0.01;
        if(y!==0 || by!==0 || valid!==0 || bvalid!==0 || clip!==0 || bclip!==0) $fatal(1,"midstream reset failed");
        @(negedge clk);rstn=1;
        history_valid=0;expect_y=0;expect_b=0;expect_v=0;expect_bv=0;expect_clip=0;expect_bc=0;
        va=0;vb=0;repeat(16)check_cycle;
        va=1;vb=1;a={16{16'h1234}};b={16{16'h0100}};repeat(20)check_cycle;
        va=0;vb=0;repeat(16)check_cycle;
        rstn=0;@(posedge clk);#0.01;
        if(y!==0 || by!==0 || valid!==0 || bvalid!==0 || clip!==0) $fatal(1,"reset failed");
        if(positive_clips==0 || negative_clips==0 || rounding_checks==0) $fatal(1,"coverage");
        $display("V6_OUTPUT_SUM_PASS samples=%0d positive_clips=%0d negative_clips=%0d rounding_checks=%0d sum_stages=2 awg_delay=6",samples,positive_clips,negative_clips,rounding_checks);
        $finish;
    end
    initial begin #500000; $fatal(1,"watchdog"); end
endmodule
