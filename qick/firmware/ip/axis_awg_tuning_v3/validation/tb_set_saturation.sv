`timescale 1ns/1ps
// Check the public SET, override and terminal RAMP outputs against an integer
// clamp/quantization reference. No internal saturation function is called.
module tb_set_saturation;
    reg clk=0,rstn=0,command_valid=0,override_valid=0;
    always #1.6665 clk=~clk;
    reg [159:0] command=0;
    reg signed [31:0] override_value=0;
    wire [255:0] out;
    wire valid,ready;
    wire [31:0] status;
    integer checks=0;
    v3_awg_tuning_ctrl #(.EXTRA_Y_PIPE_STAGES(3)) dut(
        .aclk(clk),.aresetn(rstn),.s_axis_tdata(command),.s_axis_tvalid(command_valid),
        .s_axis_tready(ready),.axi_override_value(override_value),
        .axi_override_valid(override_valid),.m_axis_tdata(out),.m_axis_tvalid(valid),
        .m_axis_tready(1'b1),.status_o(status),.current_value_o());
    function automatic integer reference(input integer value);
        integer bounded;
        begin
            bounded=value>32764 ? 32764 : (value < -32768 ? -32768 : value);
            // Signed arithmetic shift rounds negative codes toward -infinity.
            reference=(bounded>>>2)*4;
        end
    endfunction
    task automatic tick; @(posedge clk); #0.1; endtask
    task automatic check(input integer value);
        integer expected;
        expected=reference(value);
        if(!valid || !ready) $fatal(1,"continuous output/command ready lost");
        for(integer lane=0;lane<16;lane=lane+1)
            if($signed(out[16*lane+:16])!==expected)
                $fatal(1,"saturation value=%0d lane=%0d expected=%0d got=%0d",value,lane,expected,$signed(out[16*lane+:16]));
        checks=checks+1;
    endtask
    task automatic set_value(input integer value,input bit use_override,input bit hold_zero);
        @(negedge clk);
        command=0;command[31:0]=use_override ? ~value : value;
        command[145:144]=1;command[146]=hold_zero;command_valid=1;
        override_value=value;override_valid=use_override;
        tick();check(value);
        if(hold_zero && !use_override) begin
            @(negedge clk);command_valid=0;command=0;
            tick();check(0);
        end
    endtask
    task automatic terminal_ramp(input integer value);
        integer timeout;
        @(negedge clk);command=0;command[31:0]=value;
        command[145:144]=2;command[86:64]=1;command_valid=1;override_valid=0;
        tick();@(negedge clk);command=0;command_valid=0;
        timeout=0;
        while(!status[0]) begin tick();timeout=timeout+1;if(timeout>20)$fatal(1,"RAMP timeout");end
        check(value);tick();check(value);
    endtask
    initial begin
        integer value;
        repeat(10)tick();@(negedge clk);rstn=1;repeat(5)tick();
        // Every 16-bit input, both clipping boundaries and adjacent values.
        for(integer value=-33000;value<=33000;value=value+1)
            set_value(value,0,value%257==0);
        set_value(32'sh80000000,0,0);set_value(32'sh7fffffff,0,0);
        set_value(32'sh80000000,1,0);set_value(32'sh7fffffff,1,0);
        // Back-to-back arbitrary 32-bit SETs and simultaneous AXI overrides.
        for(integer trial=0;trial<20000;trial=trial+1) begin
            value=$urandom;set_value(value,trial%2,trial%257==0);
        end
        for(integer value=-32772;value<=-32760;value=value+1) terminal_ramp(value);
        for(integer value=32760;value<=32772;value=value+1) terminal_ramp(value);
        terminal_ramp(32'sh80000000);terminal_ramp(32'sh7fffffff);
        $display("PASS SET/override/terminal RAMP saturation: %0d all-lane output checks",checks);
        $finish;
    end
    initial begin #1000000;$fatal(1,"watchdog");end
endmodule
