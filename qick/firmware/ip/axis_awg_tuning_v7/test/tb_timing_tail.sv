`timescale 1ns/1ps
module tb_timing_tail;
    reg clk=0,rstn=0;
    always #1.6665 clk=~clk;
    reg [159:0] command=0;
    reg command_valid=0;
    wire [255:0] ramp_out;
    v7_awg_tuning_ctrl #(.EXTRA_Y_PIPE_STAGES(3)) ctrl(
        .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(command_valid),
        .s_axis_tready(),.axi_override_value(32'sd0),.axi_override_valid(1'b0),
        .m_axis_tdata(ramp_out),.m_axis_tvalid(),.m_axis_tready(1'b1),
        .status_o(),.current_value_o());
    awg_v7_raw_checker oracle(.clk(clk),.rstn(rstn),.command_valid(command_valid),
        .command(command),.raw_samples(ramp_out));
    reg [255:0] square_in=0;
    wire [255:0] square_out;
    wire square_valid;
    reg square_enable=0;
    square_rc_precomp square(.clk(clk),.rstn(rstn),.valid_i(1'b1),
        .enable_i(square_enable),.clear_i(1'b0),.active_i(1'b1),
        .samples_i(square_in),.half_step_i(48'd0),.samples_o(square_out),
        .valid_o(square_valid),.clipped_o());
    bit ramp_done=0,square_done=0;
    integer ramp_cases=0,round_cases=0;
    task automatic tick;@(posedge clk);#0.1;endtask
    task automatic send(input reg [159:0] packet);
        @(negedge clk);command=packet;command_valid=1;tick();
        @(negedge clk);command=0;command_valid=0;
    endtask
    // Wide mathematical reference: its rounding addition cannot overflow.
    function automatic integer reference(input reg signed [71:0] value);
        reg signed [72:0] wide;
        begin
            wide=($signed({value[71],value})+(73'sd1<<<49))>>>50;
            if(wide>8191)reference=32764;
            else if(wide< -8192)reference=-32768;
            else reference=integer'(wide)*4;
        end
    endfunction
    task automatic check_round(input reg signed [71:0] value);
        integer expected;
        expected=reference(value);
        @(negedge clk);
        // Seed only the output quantizer's input stage, leaving its public
        // output register and saturation logic active for the edge under test.
        square.valid[9]=1;square.active[9]=1;square.enabled[9]=1;
        for(integer lane=0;lane<16;lane=lane+1)square.corrected[lane]=value;
        tick();
        if(!square_valid)$fatal(1,"square output validity lost");
        for(integer lane=0;lane<16;lane=lane+1)
            if($signed(square_out[16*lane+:16])!==expected)
                $fatal(1,"square round mismatch value=%h expected=%0d actual=%0d",value,expected,$signed(square_out[16*lane+:16]));
        round_cases=round_cases+1;
    endtask
    initial begin
        repeat(10)tick();@(negedge clk);rstn=1;
    end
    initial begin
        reg [159:0] packet;
        integer start_value,target,step,duration;
        wait(rstn);repeat(20)tick();
        for(integer rep=0;rep<8;rep=rep+1)
            for(integer n=0;n<130;n=n+1) begin
                // Include unaligned starts, both rails, fractional and large
                // 32-bit steps, and every terminal lane in partial words.
                start_value=-32768+integer'($urandom_range(0,65532));
                target=$signed($urandom);step=$signed($urandom);
                if(rep%2)step=step>>>5;
                packet=0;packet[145:144]=1;packet[31:0]=start_value;send(packet);
                repeat(2)tick();
                packet=0;packet[145:144]=2;packet[31:0]=target;
                packet[86:64]=n;packet[127:96]=step;send(packet);
                duration=n==0 ? 1 : n;
                repeat(10+(duration+15)/16)tick();ramp_cases=ramp_cases+1;
            end
        ramp_done=1;
    end
    initial begin
        reg [255:0] history[11];
        reg signed [71:0] value,base;
        integer fill;
        wait(rstn);repeat(20)tick();
        // Half-step zero makes the independent 11-clock enable/bypass latency
        // reference simply the raw input history, including both signs.
        for(integer mode=0;mode<2;mode=mode+1) begin
            square_enable=mode;fill=0;
            repeat(200) begin
                @(negedge clk);
                for(integer lane=0;lane<16;lane=lane+1)
                    square_in[16*lane+:16]=($urandom_range(0,16383)-8192)*4;
                for(integer j=10;j>0;j=j-1)history[j]=history[j-1];
                history[0]=square_in;tick();fill=fill+1;
                if(fill>=11 && square_out!==history[10])$fatal(1,"square 11-clock latency mismatch mode=%0d",mode);
            end
        end
        @(negedge clk);square_in=0;repeat(20)tick();
        for(integer code=-8193;code<=8192;code=code+1) begin
            base=72'(code)<<<50;
            check_round(base);
            check_round(base+(72'sd1<<<49)-1);
            check_round(base+(72'sd1<<<49));
            check_round(base+(72'sd1<<<49)+1);
            check_round(base+(72'sd1<<<50)-1);
        end
        check_round({1'b0,{71{1'b1}}});check_round({1'b1,{71{1'b0}}});
        for(integer i=0;i<20000;i=i+1)begin value={$urandom,$urandom,$urandom};check_round(value);end
        square_done=1;
    end
    initial begin
        wait(ramp_done && square_done);
        $display("PASS TIMING TAIL: %0d boundary/random RAMP commands, %0d square quantizer words, 11-clock enable/bypass latency",ramp_cases,round_cases);
        $finish;
    end
    initial begin #10000000;$fatal(1,"watchdog");end
endmodule
