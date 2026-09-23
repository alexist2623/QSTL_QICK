`timescale 1ns/1ps
module tb_axis_square_pulse_v1;
    reg clk=0, axi_clk=0, resetn=0, axi_resetn=0;
    always #1.666667 clk=~clk;
    always #5 axi_clk=~axi_clk;
    reg [159:0] cmd=0;
    reg valid=0, ready=1;
    wire cmd_ready, out_valid;
    wire [255:0] data;
    reg [5:0] awaddr=0, araddr=0;
    reg awvalid=0, wvalid=0, bready=0, arvalid=0, rready=0;
    reg [3:0] wstrb=15;
    wire awready,wready,bvalid,arready,rvalid;
    wire [1:0] bresp,rresp;
    wire [31:0] rdata;
    axis_square_pulse_v1 dut(
        .aclk(clk),.aresetn(resetn),.s_axis_tdata(cmd),.s_axis_tvalid(valid),.s_axis_tready(cmd_ready),
        .m_axis_tdata(data),.m_axis_tvalid(out_valid),.m_axis_tready(ready),
        .s_axi_aclk(axi_clk),.s_axi_aresetn(axi_resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(3'd0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(32'd0),.s_axi_wstrb(wstrb),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
        .s_axi_araddr(araddr),.s_axi_arprot(3'd0),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
        .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready));
    task write_mute(input integer address_delay, data_delay, response_delay);
        fork
            begin
                repeat(address_delay) @(negedge axi_clk); awvalid=1;
                do @(posedge axi_clk); while(!awready);
                @(negedge axi_clk); awvalid=0;
            end
            begin
                repeat(data_delay) @(negedge axi_clk); wvalid=1;
                do @(posedge axi_clk); while(!wready);
                @(negedge axi_clk); wvalid=0;
            end
        join
        wait(bvalid);
        repeat(response_delay) begin
            @(negedge axi_clk);
            if(!bvalid || bresp!=0) $fatal(1,"write response lost");
        end
        bready=1; @(negedge axi_clk); bready=0;
    endtask
    task read_reg(input [5:0] address,input [31:0] expected);
        @(negedge axi_clk); araddr=address; arvalid=1;
        do @(posedge axi_clk); while(!arready);
        @(negedge axi_clk); arvalid=0;
        wait(rvalid);
        repeat(4) begin
            @(negedge axi_clk);
            if(!rvalid || rresp!=0 || rdata!==expected) $fatal(1,"read mismatch/stall");
        end
        rready=1; @(negedge axi_clk); rready=0;
    endtask
    task start;
        @(negedge clk); cmd={32'd3,32'd0,32'd800,32'd0,32'd0}; valid=1;
        @(negedge clk); valid=0;
        repeat(8) @(negedge clk);
        if(data !== {16{16'd800}}) $fatal(1,"start output");
    endtask
    initial begin
        repeat(5) @(negedge axi_clk); axi_resetn=1; resetn=1;
        read_reg(0,32'h53515031); read_reg(8,4); read_reg(12,16);
        start(); ready=0; repeat(5) @(negedge clk);
        if(data !== {16{16'd800}} || !out_valid || !cmd_ready) $fatal(1,"realtime sink stalled");
        write_mute(1,6,5); repeat(20) @(negedge axi_clk);
        if(data !== 0) $fatal(1,"CDC mute AW first");
        read_reg(4,0);
        start(); write_mute(7,1,3); repeat(20) @(negedge axi_clk);
        if(data !== 0) $fatal(1,"CDC mute W first");
        start(); write_mute(1,1,0); repeat(20) @(negedge axi_clk);
        if(data !== 0) $fatal(1,"CDC mute simultaneous");
        $display("PASS: AXIS wrapper, independent AXI channels, stalls, CDC mute"); $finish;
    end
    initial begin #20000; $fatal(1,"AXI timeout"); end
endmodule
