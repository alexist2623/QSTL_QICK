`timescale 1ns/1fs
module tb_square_dds_500us;
    // 2 kHz requested at 4.8 GSPS, rounded to the nearest 32-bit FTW.
    localparam [31:0] FTW = 32'd1790;
    localparam longint PERIOD_FLOOR = 64'd4294967296 / FTW;
    localparam longint HALF_FLOOR = 64'd2147483648 / FTW;
    reg clk=0, resetn=0, valid=0;
    reg [159:0] command=0;
    wire enabled;
    wire [255:0] samples;
    always #1.666666667 clk=~clk;
    square_dds dut(.aclk(clk), .aresetn(resetn), .command(command),
        .command_valid(valid), .mute(1'b0), .enabled(enabled), .samples(samples));

    // Scalar specification, independent of the DUT's parallel lane arithmetic.
    reg [31:0] phase_acc=0, ref_ftw=0, phase_offset=0;
    integer amplitude=0, output_enabled=0, clear_phase=0;
    reg [255:0] expected[4], next_word;
    reg [31:0] phase_with_offset;
    integer magnitude, value, level;
    longint sample_index=0, last_edge=-1, last_rise=-1, interval_samples;
    longint min_period=64'h7fffffffffffffff, max_period=0;
    longint min_half=64'h7fffffffffffffff, max_half=0;
    integer half_checks=0, period_checks=0;
    integer seen_positive[5], seen_negative[5];
    longint zero_samples=0;
    bit sign_known=0, previous_negative=0, negative_now;

    always @(posedge clk) begin
        if (!resetn) begin
            phase_acc=0; ref_ftw=0; phase_offset=0;
            amplitude=0; output_enabled=0; clear_phase=0;
            for(integer j=0;j<4;j=j+1) expected[j]=0;
            #0.001;
            if(samples !== 0) $fatal(1,"reset output");
        end else begin
            if(clear_phase) phase_acc=0;
            for(integer lane=0;lane<16;lane=lane+1) begin
                phase_with_offset=phase_acc+phase_offset;
                magnitude=output_enabled ? amplitude : 0;
                next_word[16*lane +: 16]=phase_with_offset[31] ? -magnitude : magnitude;
                phase_acc=phase_acc+ref_ftw;
            end
            for(integer j=3;j>0;j=j-1) expected[j]=expected[j-1];
            expected[0]=next_word;
            clear_phase=0;
            if(valid) begin
                ref_ftw=command[31:0]; phase_offset=command[63:32];
                amplitude=command[95:64]; output_enabled=command[128];
                clear_phase=command[129];
                $display("UPDATE: amplitude=%0d reset_phase=%0d",amplitude,clear_phase);
            end
            #0.001;
            if(samples !== expected[3])
                $fatal(1,"scalar reference or four-cycle command latency mismatch at sample %0d",sample_index);

            // Independently measure output edge spacing across nonzero amplitude
            // updates. A gain change must not move the next square-wave edge.
            for(integer lane=0;lane<16;lane=lane+1) begin
                value=$signed(samples[16*lane +: 16]);
                if(value==0) begin
                    zero_samples=zero_samples+1;
                    sign_known=0; last_edge=-1; last_rise=-1;
                end else begin
                    magnitude=value<0 ? -value : value;
                    case(magnitude)
                        800: level=0;
                        1920: level=1;
                        320: level=2;
                        4: level=3;
                        32764: level=4;
                        default: $fatal(1,"unexpected output magnitude %0d",magnitude);
                    endcase
                    negative_now=value<0;
                    if(negative_now) seen_negative[level]=seen_negative[level]+1;
                    else seen_positive[level]=seen_positive[level]+1;
                    if(sign_known && negative_now!=previous_negative) begin
                        if(last_edge>=0) begin
                            interval_samples=sample_index-last_edge;
                            if(interval_samples!=HALF_FLOOR && interval_samples!=HALF_FLOOR+1)
                                $fatal(1,"half-period changed: %0d samples",interval_samples);
                            if(interval_samples<min_half) min_half=interval_samples;
                            if(interval_samples>max_half) max_half=interval_samples;
                            half_checks=half_checks+1;
                        end
                        last_edge=sample_index;
                        if(!negative_now) begin
                            if(last_rise>=0) begin
                                interval_samples=sample_index-last_rise;
                                if(interval_samples!=PERIOD_FLOOR && interval_samples!=PERIOD_FLOOR+1)
                                    $fatal(1,"period changed: %0d samples",interval_samples);
                                if(interval_samples<min_period) min_period=interval_samples;
                                if(interval_samples>max_period) max_period=interval_samples;
                                period_checks=period_checks+1;
                            end
                            last_rise=sample_index;
                        end
                    end
                    sign_known=1; previous_negative=negative_now;
                end
                sample_index=sample_index+1;
            end
        end
    end

    task set_amplitude(input [31:0] gain, input bit clear);
        @(negedge clk); valid=1;
        command={30'd0,clear,1'b1,32'd0,gain,32'd0,FTW};
        @(negedge clk); valid=0;
    endtask

    initial begin
        for(integer k=0;k<5;k=k+1) begin seen_positive[k]=0; seen_negative[k]=0; end
        repeat(4) @(negedge clk); resetn=1;
        // Each nonzero gain is held for about 1.1 ms (> two full periods).
        // Updates occur inside a period, without clearing accumulated phase.
        set_amplitude(800,1); repeat(330000) @(negedge clk);
        set_amplitude(1920,0); repeat(330000) @(negedge clk);
        set_amplitude(320,0); repeat(330000) @(negedge clk);
        set_amplitude(4,0); repeat(330000) @(negedge clk);
        set_amplitude(32764,0); repeat(330000) @(negedge clk);
        set_amplitude(0,0); repeat(75000) @(negedge clk);
        set_amplitude(800,0); repeat(330000) @(negedge clk);
        if(period_checks<10 || half_checks<20 || zero_samples<1000000)
            $fatal(1,"insufficient period/zero-amplitude coverage");
        for(integer k=0;k<5;k=k+1) begin
            if(seen_positive[k]==0 || seen_negative[k]==0)
                $fatal(1,"missing amplitude polarity, level=%0d",k);
            $display("LEVEL: index=%0d positive_samples=%0d negative_samples=%0d",
                k,seen_positive[k],seen_negative[k]);
        end
        $display("TIMING: FTW=%0d frequency_hz=%0.9f nominal_period_us=%0.9f",
            FTW,FTW*4800000000.0/4294967296.0,4294967296.0/FTW/4800.0);
        $display("EDGES: period_checks=%0d full_samples=%0d..%0d half_checks=%0d half_samples=%0d..%0d",
            period_checks,min_period,max_period,half_checks,min_half,max_half);
        $display("PASS: 500 us requested period, amplitude changes, phase continuity; %0d scalar samples checked",sample_index);
        $finish;
    end
    initial begin #10000000; $fatal(1,"500 us test timeout"); end
endmodule
