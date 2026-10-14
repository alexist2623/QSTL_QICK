`timescale 1ns/1ps
// Invalid-operation guard regression, independent of normal sweep evidence.
module tb_dc_faults;
    reg clk=0,rstn=0,command_valid=0,abort_i=0;
    always #1.6665 clk=~clk;
    reg [159:0] command=0;
    reg [255:0] raw=0;
    wire [255:0] output_word;
    wire valid,clear_rc,done,enabled,busy,fault;
    wire signed [63:0] area;
    wire [31:0] completed;
    v3_awg_dc_area dut(.clk(clk),.rstn(rstn),.valid_i(1'b1),.samples_i(raw),
        .command_i(command),.command_valid_i(command_valid),.abort_i(abort_i),
        .samples_o(output_word),.valid_o(valid),.clear_rc_o(clear_rc),.done_o(done),
        .enabled_o(enabled),.busy_o(busy),.fault_o(fault),.area_o(area),.completed_shots_o(completed));
    task automatic tick; @(posedge clk);#0.1;endtask
    task automatic send(input integer action,input reg [31:0] amplitude);
        @(negedge clk);command=0;command[150]=1;command[145:144]=3;
        command[147:146]=action;command[31:0]=amplitude;command_valid=1;tick();
        @(negedge clk);command_valid=0;command=0;
    endtask
    task automatic arm;
        @(negedge clk);raw=0;repeat(8)tick();send(0,0);repeat(8)tick();
        if(fault || !enabled || area!=0)$fatal(1,"failed to arm");
    endtask
    task automatic check_fault;
        repeat(3)tick();
        if(!fault || busy || output_word!=0 || dut.state!=5)
            $fatal(1,"fault did not latch safe state: state=%0d fault=%0d busy=%0d out=%h",dut.state,fault,busy,output_word);
    endtask
    initial begin
        repeat(10)tick();@(negedge clk);rstn=1;repeat(10)tick();
        send(1,1284);check_fault(); // not armed
        arm();send(1,0);check_fault();
        arm();send(1,5);check_fault(); // unaligned DAC amplitude
        arm();send(1,32768);check_fault(); // positive DAC range
        arm();send(2,0);check_fault(); // zero count/reciprocal
        // A sample arriving at the final PREPARE edge must not be overwritten
        // by the unconditional PREPARE -> EMIT transition.
        arm();send(1,1284);
        while(dut.setup_count<11)tick();
        @(negedge clk);raw={16{16'd4}};
        repeat(5)tick();check_fault();
        // Nonzero upstream data arriving during EMIT is also an invalid shot.
        arm();@(negedge clk);raw={16{16'd4000}};repeat(20)tick();
        @(negedge clk);raw=0;repeat(8)tick();send(1,4);
        while(dut.state!=2)tick();
        @(negedge clk);raw={16{16'd4}};repeat(6)tick();check_fault();
        // Explicit abort clears fault and disables accumulation.
        @(negedge clk);raw=0;abort_i=1;tick();
        if(fault || enabled || busy || area!=0 || !clear_rc)$fatal(1,"abort failed");
        @(negedge clk);abort_i=0;repeat(8)tick();
        $display("PASS FAULT GUARDS: invalid command, final PREPARE edge, EMIT input and abort");
        $finish;
    end
    initial begin #100000;$fatal(1,"watchdog");end
endmodule
