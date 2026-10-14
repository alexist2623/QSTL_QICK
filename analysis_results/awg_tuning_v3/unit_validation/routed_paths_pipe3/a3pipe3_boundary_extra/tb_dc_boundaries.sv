`timescale 1ns/1ps
// Arithmetic boundary coverage. Hierarchical area seeding is intentional and
// is NOT evidence of a real multi-hour waveform run. Natural sweeps are separate.
module dc_boundary_case #(parameter integer WIDTH=64)(output reg finished=0);
    reg clk=0, rstn=0, command_valid=0;
    always #1.6665 clk=~clk;
    reg [255:0] raw=0;
    reg [159:0] command=0;
    wire [255:0] out;
    wire valid, clear_rc, done, enabled, busy, fault;
    wire signed [63:0] area;
    wire [31:0] completed;
    v3_awg_dc_area #(.AREA_WIDTH(WIDTH)) dut(
        .clk(clk),.rstn(rstn),.valid_i(1'b1),.samples_i(raw),
        .command_i(command),.command_valid_i(command_valid),.abort_i(1'b0),
        .samples_o(out),.valid_o(valid),.clear_rc_o(clear_rc),.done_o(done),
        .enabled_o(enabled),.busy_o(busy),.fault_o(fault),.area_o(area),
        .completed_shots_o(completed));
    localparam signed [63:0] MAX_AREA=(64'h7fff_ffff_ffff_ffff >> (64-WIDTH));
    localparam signed [63:0] MIN_AREA=-MAX_AREA-1;
    integer quotient_cases=0;

    task automatic tick;
        @(posedge clk); #0.1;
    endtask
    task automatic arm;
        @(negedge clk); raw=0; command=0;
        repeat(6) tick();
        @(negedge clk);
        command[150]=1; command[145:144]=3; command_valid=1;
        tick(); @(negedge clk); command_valid=0; command=0;
        repeat(8) tick();
        if(fault || area!=0 || !enabled) $fatal(1,"ARM width=%0d",WIDTH);
    endtask
    task automatic overflow_test(input bit negative);
        longint signed seed;
        arm();
        seed=negative ? MIN_AREA+8 : MAX_AREA-8;
        @(negedge clk); dut.area=seed[WIDTH-1:0];
        for(integer lane=0;lane<16;lane=lane+1) raw[16*lane+:16]=negative ? -4 : 4;
        repeat(8) tick();
        if(!fault || area!==seed) $fatal(1,"overflow wrapped width=%0d sign=%0d area=%0d",WIDTH,negative,area);
        if(out!=0) $fatal(1,"fault output was not zero");
        $display("BOUNDARY width=%0d sign=%0d overflow detected without wrap",WIDTH,negative);
    endtask
    task automatic overflow_predicate_test;
        longint signed seed;
        reg signed [17:0] increment;
        reg signed [64:0] direct_sum;
        bit expected;
        arm();
        for(integer trial=0;trial<3000;trial=trial+1) begin
            case(trial%3)
                0: seed=MAX_AREA-($urandom%262144);
                1: seed=MIN_AREA+($urandom%262144);
                2: begin
                    seed={$urandom,$urandom};
                    seed=$signed(seed[WIDTH-1:0]);
                end
            endcase
            increment=$urandom;
            direct_sum=$signed({seed[63],seed})+$signed(increment);
            expected=(direct_sum>MAX_AREA || direct_sum<MIN_AREA);
            @(negedge clk);
            dut.area=seed[WIDTH-1:0]; dut.sum16=increment; dut.valid[3]=1;
            #0.1;
            if(dut.raw_overflow!==expected || dut.raw_area_next!==direct_sum)
                $fatal(1,"carry overflow mismatch width=%0d seed=%0d increment=%0d",WIDTH,seed,increment);
        end
        $display("BOUNDARY WIDTH %0d: 3000 signed carry/overflow comparisons passed",WIDTH);
    endtask
    task automatic quotient_test(input longint signed seeded_area, input reg [31:0] words);
        reg [127:0] numerator;
        reg [63:0] magnitude, count, q, r;
        integer expected_lane, actual_lane, timeout;
        if(seeded_area<=MAX_AREA && seeded_area>=MIN_AREA && seeded_area!=64'sh8000000000000000) begin
            arm();
            magnitude=seeded_area<0 ? -seeded_area : seeded_area;
            count={words,4'b0}; q=magnitude/count; r=magnitude%count;
            if((seeded_area>0 && q<=8192 && (q<8192 || r==0)) ||
               (seeded_area<=0 && q<=8191 && (q<8191 || r==0))) begin
                @(negedge clk); dut.area=seeded_area[WIDTH-1:0];
                numerator=128'd1<<64;
                command=0; command[150]=1; command[145:144]=3;
                command[147:146]=2; command[63:0]=numerator/count;
                command[95:64]=words; command_valid=1;
                tick(); @(negedge clk); command_valid=0; command=0;
                timeout=0;
                // Inspect division before the lookahead planner consumes the
                // first word's remainder. Output timing is checked separately.
                while(!(dut.state==1 && dut.setup_count==15) && !fault) begin
                    tick(); timeout=timeout+1;
                    if(timeout>30) $fatal(1,"quotient setup timeout");
                end
                if(fault) $fatal(1,"quotient setup fault width=%0d area=%0d",WIDTH,seeded_area);
                if(dut.base_code!=q || dut.remainder!=r)
                    $fatal(1,"quotient/remainder mismatch width=%0d area=%0d expected %0d/%0d got %0d/%0d",
                        WIDTH,seeded_area,q,r,dut.base_code,dut.remainder);
                tick(); // Queue first word; no compensation output yet.
                tick(); // Emit that word at the unchanged 17-clock latency.
                for(integer lane=0;lane<16;lane=lane+1) begin
                    expected_lane=(q+(lane<r))*4;
                    if(seeded_area>0) expected_lane=-expected_lane;
                    actual_lane=$signed(out[16*lane+:16]);
                    if(actual_lane!=expected_lane) $fatal(1,"first compensation lane mismatch");
                end
                quotient_cases=quotient_cases+1;
            end
        end
    endtask
    task automatic minimum_area_command;
        arm();
        @(negedge clk);dut.area=MIN_AREA[WIDTH-1:0];
        command=0;command[150]=1;command[145:144]=3;
        command[147:146]=1;command[31:0]=32764;command_valid=1;
        tick();
        if(fault!==(WIDTH==64)) $fatal(1,"minimum area acceptance width=%0d",WIDTH);
        @(negedge clk);command=0;command_valid=0;
        if(WIDTH!=64) begin
            tick();
            if(dut.remaining!==(-MIN_AREA)) $fatal(1,"minimum area magnitude width=%0d",WIDTH);
        end
        arm();
    endtask
    task automatic partial_voltage_word(input integer amount,input integer amp);
        integer timeout,magnitude,expected,leftover;
        arm();
        @(negedge clk);dut.area=amount;
        command=0;command[150]=1;command[145:144]=3;
        command[147:146]=1;command[31:0]=amp*4;command_valid=1;
        tick();@(negedge clk);command=0;command_valid=0;
        timeout=0;
        while(!(dut.state==1 && dut.setup_count==15) && !fault) begin
            tick();timeout=timeout+1;if(timeout>30)$fatal(1,"partial word timeout");
        end
        if(fault)$fatal(1,"partial word setup fault");
        tick();tick();leftover=amount<0 ? -amount : amount;
        for(integer lane=0;lane<16;lane=lane+1) begin
            magnitude=leftover>amp ? amp : leftover;
            expected=(amount>0 ? -magnitude : magnitude)*4;
            if($signed(out[16*lane+:16])!=expected)
                $fatal(1,"partial lane width=%0d area=%0d amp=%0d lane=%0d",WIDTH,amount,amp,lane);
            leftover=leftover-magnitude;
        end
        if(leftover!=0 || area!=0)$fatal(1,"partial word ledger residual");
        repeat(4)tick();
        if(fault)$fatal(1,"partial word completion fault");
    endtask
    initial begin
        repeat(10) tick(); @(negedge clk); rstn=1;
        overflow_predicate_test();
        overflow_test(0); overflow_test(1);
        minimum_area_command();
        // Partial-lane prefixes cross bit14 at large amplitudes. Both signs,
        // every lane boundary and its neighbors must still cancel exactly.
        for(integer sign=-1;sign<=1;sign=sign+2)
            for(integer amp=5000;amp<=8191;amp=amp+3191)
                for(integer lane=0;lane<16;lane=lane+1)
                    for(integer delta=-1;delta<=1;delta=delta+1)
                        if(lane*amp+delta>=0) partial_voltage_word(sign*(lane*amp+delta),amp);
        quotient_test(16*8192,1);
        quotient_test(-(16*8191),1);
        quotient_test(16*8191+1,1);
        // Around quotient thresholds and high-order bits of all three widths.
        for(integer sign=-1;sign<=1;sign=sign+2) begin
            quotient_test(sign*64'sd2147483627,32'd65537);
            quotient_test(sign*64'sd140737488355309,32'hffffffff);
            quotient_test(sign*64'sd450359962737001,32'hffffffff);
            for(integer delta=-1;delta<=1;delta=delta+1) begin
                quotient_test(sign*(64'sd16*65537*1000+delta),32'd65537);
                quotient_test(sign*(64'sd16*64'd4294967295*1000+delta),32'hffffffff);
            end
        end
        quotient_test(MIN_AREA,32'hffffffff);
        quotient_test(0,32'd97);
        arm(); finished=1;
        $display("PASS BOUNDARY WIDTH %0d: two signed overflow edges, %0d seeded quotient/remainder cases",WIDTH,quotient_cases);
    end
endmodule

module tb_dc_boundaries;
    wire done32,done48,done64;
    dc_boundary_case #(.WIDTH(32)) w32(done32);
    dc_boundary_case #(.WIDTH(48)) w48(done48);
    dc_boundary_case #(.WIDTH(64)) w64(done64);
    initial begin wait(done32 && done48 && done64); $finish; end
    initial begin #100000; $fatal(1,"watchdog"); end
endmodule
