// Per-shot DC area balancing BEFORE the RC inverse filter.
// Area units are one effective DAC code (four transport codes) * scalar sample.
// All 16 lanes are counted. Normal/bypass traffic has five register stages.
`timescale 1ns/1ps
`default_nettype none

// Five-stage unsigned multiply; each DSP operand fits a 16x16 product.
module v3_dc_mul64(input wire clk, rstn,
    input wire [63:0] a, b, output logic [127:0] product);
    (* use_dsp="yes" *) logic [31:0] pp[4][4];
    logic [47:0] pairs[4][2];
    logic [79:0] rows[4];
    logic [95:0] halves[2];
    always_ff @(posedge clk) begin
        if (!rstn) begin
            product<=0;
            for(integer i=0;i<4;i=i+1) begin
                rows[i]<=0;
                for(integer j=0;j<4;j=j+1) pp[i][j]<=0;
                for(integer j=0;j<2;j=j+1) pairs[i][j]<=0;
            end
            halves[0]<=0; halves[1]<=0;
        end else begin
            for(integer i=0;i<4;i=i+1) begin
                for(integer j=0;j<4;j=j+1)
                    pp[i][j]<=a[16*i+:16]*b[16*j+:16];
                for(integer j=0;j<2;j=j+1)
                    pairs[i][j]<={16'd0,pp[i][2*j]}+{pp[i][2*j+1],16'd0};
                rows[i]<={32'd0,pairs[i][0]}+{pairs[i][1],32'd0};
            end
            halves[0]<={16'd0,rows[0]}+{rows[1],16'd0};
            halves[1]<={16'd0,rows[2]}+{rows[3],16'd0};
            product<={32'd0,halves[0]}+{halves[1],32'd0};
        end
    end
endmodule

module v3_awg_dc_area # (parameter integer N_PTS=16, parameter integer AREA_WIDTH=48)(
    input wire clk, rstn, valid_i,
    input wire [16*N_PTS-1:0] samples_i,
    input wire [159:0] command_i,
    input wire command_valid_i, abort_i,
    output logic [16*N_PTS-1:0] samples_o,
    output logic valid_o, clear_rc_o, done_o,
    output wire enabled_o, busy_o,
    output logic fault_o,
    output wire signed [63:0] area_o,
    output logic [31:0] completed_shots_o
);
    // The five-word command uses the previously reserved bit 150. IDLE means
    // these packets cannot be mistaken for a SET or a RAMP by the AWG core.
    // action[147:146]: 0 arm/clear, 1 fixed voltage, 2 fixed time, 3 disable.
    // fixed voltage: word0 = positive amplitude in transport codes.
    // fixed time: words0/1 = floor(2^64/(16*word_count)), word2 = word_count.
    localparam [2:0] PASS=0, PREPARE=1, EMIT=2, ZERO_EDGE=3, RESET_SHOT=4, FAULT=5;
    logic [2:0] state;
    logic enabled, fixed_time, negative;
    logic [4:0] setup_count;
    logic signed [AREA_WIDTH-1:0] area, captured_area;
    wire signed [63:0] area_extended={{(64-AREA_WIDTH){area[AREA_WIDTH-1]}},area};
    logic [63:0] remaining, reciprocal, absolute_area;
    logic [35:0] sample_count;
    logic [31:0] words_left;
    logic [13:0] amplitude, quotient, base_code;
    logic [17:0] lane_before[16], lane_after[16];
    logic [63:0] remainder;
    // Plan a word before it is emitted. The ledger then adds only a registered
    // signed delta, not the compare/remainder/lane-selection arithmetic.
    logic [16*N_PTS-1:0] planned_samples;
    logic signed [18:0] planned_delta;
    logic planned_last;
    (* use_dsp="yes" *) logic [49:0] used_area1;
    logic [49:0] used_area2;
    wire [127:0] product;
    v3_dc_mul64 reciprocal_mult(.clk(clk),.rstn(rstn),
        .a(absolute_area),.b(reciprocal),.product(product));

    logic [16*N_PTS-1:0] raw[4];
    logic [3:0] valid;
    logic signed [14:0] sum2[8];
    logic signed [15:0] sum4[4];
    logic signed [16:0] sum8[2];
    logic signed [17:0] sum16;
    logic raw_nonzero3;
    wire dc_command=command_valid_i && command_i[150] &&
        !command_i[149] && command_i[145:144]==2'b11;
    wire [1:0] action=command_i[147:146];
    wire signed [AREA_WIDTH:0] raw_sum=$signed({area[AREA_WIDTH-1],area})+
        ((enabled && valid[3]) ? $signed({{(AREA_WIDTH-17){sum16[17]}},sum16}) :
         $signed({(AREA_WIDTH+1){1'b0}}));
    wire signed [64:0] raw_area_next={{(64-AREA_WIDTH){raw_sum[AREA_WIDTH]}},raw_sum};
    // Overflow detection uses the small increment's carry and the upper-area
    // boundary pattern. Avoid a full-width adder followed by a sign test on the
    // fault/state-enable path. AREA_WIDTH is 32, 48 or 64, always greater than18.
    wire [18:0] raw_low_sum={1'b0,area[17:0]}+{1'b0,sum16};
    wire raw_overflow=enabled && valid[3] &&
        ((!sum16[17] && !area[AREA_WIDTH-1] && (&area[AREA_WIDTH-2:18]) && raw_low_sum[18]) ||
         (sum16[17] && area[AREA_WIDTH-1] && !(|area[AREA_WIDTH-2:18]) && !raw_low_sum[18]));
    wire [17:0] voltage_word_area={amplitude,4'b0};
    wire [4:0] extra=(remainder>=16) ? 5'd16 : remainder[4:0];
    wire [17:0] time_word_area={base_code,4'b0}+extra;
    wire [17:0] emitted_area=fixed_time ? time_word_area :
        ((remaining>{46'd0,voltage_word_area}) ? voltage_word_area : remaining[17:0]);
    wire signed [18:0] emitted_signed=negative ? -$signed({1'b0,emitted_area}) :
        $signed({1'b0,emitted_area});
    wire signed [AREA_WIDTH:0] comp_area_next=$signed({area[AREA_WIDTH-1],area})+
        $signed({{(AREA_WIDTH-18){planned_delta[18]}},planned_delta});
    wire next_last=fixed_time ? (words_left==1) : (remaining<={46'd0,voltage_word_area});
    wire signed [63:0] captured_extended={{(64-AREA_WIDTH){captured_area[AREA_WIDTH-1]}},captured_area};
    assign area_o=area_extended;
    assign enabled_o=enabled;
    assign busy_o=(state!=PASS && state!=FAULT);
    // Fault priority must precede every state transition, including the final
    // PREPARE/EMIT cycle. A late raw word cannot be omitted from the ledger.
    wire invalid_busy=busy_o && ((valid[3] && raw_nonzero3) ||
        (command_valid_i && (command_i[145:144]==1 || command_i[145:144]==2 ||
         (dc_command && (action==1 || action==2)))));

    function automatic [15:0] compensation_lane(input integer lane);
        logic [17:0] before_lane;
        logic [14:0] magnitude;
        logic signed [15:0] signed_code;
        begin
            before_lane=lane_before[lane];
            if(fixed_time) magnitude={1'b0,base_code}+(lane<extra);
            else if(remaining>={46'd0,voltage_word_area})
                magnitude={1'b0,amplitude};
            else if(remaining[17:0]>=lane_after[lane])
                magnitude={1'b0,amplitude};
            else if(remaining[17:0]>before_lane)
                magnitude=remaining[17:0]-before_lane;
            else magnitude=0;
            signed_code=negative ? -$signed({1'b0,magnitude}) : $signed({1'b0,magnitude});
            compensation_lane={signed_code[13:0],2'b00};
        end
    endfunction

    always_ff @(posedge clk) begin
        if(!rstn) begin
            valid<=0; sum16<=0; raw_nonzero3<=0;
            for(integer i=0;i<4;i=i+1) begin raw[i]<=0; sum4[i]<=0; end
            for(integer i=0;i<8;i=i+1) sum2[i]<=0;
            for(integer i=0;i<2;i=i+1) sum8[i]<=0;
        end else begin
            valid<={valid[2:0],valid_i}; raw[0]<=samples_i;
            raw_nonzero3<=|raw[2];
            for(integer i=1;i<4;i=i+1) raw[i]<=raw[i-1];
            for(integer i=0;i<8;i=i+1)
                sum2[i]<=$signed(samples_i[32*i+2+:14])+$signed(samples_i[32*i+18+:14]);
            for(integer i=0;i<4;i=i+1) sum4[i]<=sum2[2*i]+sum2[2*i+1];
            for(integer i=0;i<2;i=i+1) sum8[i]<=sum4[2*i]+sum4[2*i+1];
            sum16<=sum8[0]+sum8[1];
        end
    end

    always_ff @(posedge clk) begin
        if(!rstn) begin
            state<=PASS; enabled<=0; area<=0; captured_area<=0; fault_o<=0;
            samples_o<=0; valid_o<=0; clear_rc_o<=0; done_o<=0;
            completed_shots_o<=0; setup_count<=0;
            fixed_time<=0; negative<=0; remaining<=0; reciprocal<=0;
            absolute_area<=0; sample_count<=0; words_left<=0;
            amplitude<=0; quotient<=0; base_code<=0; remainder<=0;
            used_area1<=0; used_area2<=0;
            planned_samples<=0; planned_delta<=0; planned_last<=0;
            for(integer i=0;i<16;i=i+1) begin lane_before[i]<=0; lane_after[i]<=0; end
        end else begin
            samples_o<=0; valid_o<=valid[3]; clear_rc_o<=0; done_o<=0;
            if(invalid_busy) begin
                fault_o<=1; state<=FAULT;
            end else case(state)
                PASS: begin
                    if(valid[3]) samples_o<=raw[3];
                    if(enabled && valid[3]) begin
                        if(raw_overflow) begin
                            fault_o<=1; state<=FAULT;
                        end else area<=raw_area_next[AREA_WIDTH-1:0];
                    end
                    if(dc_command && (action==1 || action==2)) begin
                        // Caller must first SET zero and drain the raw pipeline.
                        // Include this last emitted word in the captured area.
                        if(!enabled || raw_overflow ||
                           raw_area_next[63:0]==64'h8000000000000000) begin
                            fault_o<=1; state<=FAULT;
                        end else begin
                            state<=PREPARE; setup_count<=0;
                            fixed_time<=(action==2);
                            captured_area<=raw_area_next[AREA_WIDTH-1:0];
                            reciprocal<=command_i[63:0];
                            amplitude<=command_i[15:2];
                            words_left<=command_i[95:64];
                            sample_count<={command_i[95:64],4'b0};
                            if((action==1 && (command_i[31:0]==0 || command_i[31:0]>32764 || command_i[1:0]!=0)) ||
                               (action==2 && (command_i[95:64]==0 || command_i[63:0]==0))) begin
                                fault_o<=1; state<=FAULT;
                            end
                        end
                    end
                end
                PREPARE: begin
                    setup_count<=setup_count+1'b1;
                    // Amplitude is constant for a compensation pulse. Move the
                    // lane-prefix multiply/add out of the per-word output path.
                    if(setup_count==0) begin
                        // Separate the final raw-area addition from absolute
                        // value conversion and the multiplier input register.
                        negative<=!captured_extended[63];
                        absolute_area<=captured_extended[63] ? -captured_extended : captured_extended;
                        remaining<=captured_extended[63] ? -captured_extended : captured_extended;
                        for(integer i=0;i<16;i=i+1) lane_before[i]<=amplitude*i;
                    end
                    if(setup_count==1)
                        for(integer i=0;i<16;i=i+1) lane_after[i]<=lane_before[i]+amplitude;
                    if(setup_count==6) begin
                        quotient<=product[77:64];
                        if(fixed_time && product[127:64]>8192) begin fault_o<=1; state<=FAULT; end
                    end
                    if(setup_count==7) used_area1<=quotient*sample_count;
                    if(setup_count==8) used_area2<=used_area1;
                    if(setup_count==9) remainder<=absolute_area-used_area2;
                    if(setup_count==10) begin
                        // A truncated reciprocal underestimates the quotient by
                        // at most one for |area|<2^63. Correct that final unit.
                        if(remainder>={28'd0,sample_count}) begin
                            base_code<=quotient+1'b1;
                            remainder<=remainder-sample_count;
                        end else base_code<=quotient;
                    end
                    if(setup_count==11 && fixed_time) begin
                        if((negative && (base_code>8192 || (base_code==8192 && remainder!=0))) ||
                           (!negative && (base_code>8191 || (base_code==8191 && remainder!=0))) ||
                           remainder>={28'd0,sample_count}) begin fault_o<=1; state<=FAULT; end
                    end
                    // Common startup for both modes: first output is 17 clocks
                    // after command acceptance. See the production RTL tests.
                    if(setup_count==15) begin
                        for(integer i=0;i<N_PTS;i=i+1) planned_samples[16*i+:16]<=compensation_lane(i);
                        planned_delta<=emitted_signed; planned_last<=next_last;
                        if(fixed_time) begin
                            remainder<=remainder-extra;
                            words_left<=words_left-1'b1;
                        end else remaining<=remaining-emitted_area;
                        state<=EMIT;
                    end
                end
                EMIT: begin
                    samples_o<=planned_samples;
                    area<=comp_area_next[AREA_WIDTH-1:0];
                    if(planned_last) state<=ZERO_EDGE;
                    else begin
                        for(integer i=0;i<N_PTS;i=i+1) planned_samples[16*i+:16]<=compensation_lane(i);
                        planned_delta<=emitted_signed; planned_last<=next_last;
                        if(fixed_time) begin
                            remainder<=remainder-extra;
                            words_left<=words_left-1'b1;
                        end else remaining<=remaining-emitted_area;
                    end
                end
                ZERO_EDGE: begin
                    // The IIR must see the final nonzero -> zero trapezoid
                    // before its previous-sample history is cleared.
                    // Check the registered final ledger, avoiding a long
                    // remainder -> add/subtract -> zero-test -> state path.
                    if(area!=0) begin fault_o<=1; state<=FAULT; end
                    else state<=RESET_SHOT;
                end
                RESET_SHOT: begin
                    area<=0; clear_rc_o<=1; done_o<=1;
                    completed_shots_o<=completed_shots_o+1'b1;
                    state<=PASS;
                end
                FAULT: samples_o<=0;
                default: begin state<=FAULT; fault_o<=1; end
            endcase
            if(abort_i || (dc_command && (action==0 || action==3))) begin
                area<=0; state<=PASS; fault_o<=0;
                planned_samples<=0; planned_delta<=0; planned_last<=0;
                enabled<=!abort_i && action==0;
                // ARM/DISABLE are issued only with nominal zero, e.g. program
                // initialization. AXI stop also aborts in-progress balancing.
                clear_rc_o<=1;
            end
        end
    end
endmodule
`default_nettype wire
