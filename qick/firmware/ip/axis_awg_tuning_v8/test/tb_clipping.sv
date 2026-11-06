`timescale 1ns/1ps
module clipping_case #(parameter integer RC_VERSION=1)(output reg done=0);
   reg clk=0, axi_clk=0, rstn=0, cv=0;
   reg [159:0] command=0;
   reg [5:0] awaddr=0, araddr=0;
   reg [31:0] wdata=0;
   reg awvalid=0, wvalid=0, arvalid=0;
   wire awready,wready,bvalid,arready,rvalid;
   wire [1:0] bresp;
   wire [31:0] rdata;
   wire [255:0] samples;
   wire valid;
   always #1.6665 clk=~clk;
   always #5 axi_clk=~axi_clk;
   axis_awg_tuning_v8 #(.RC_PRECOMP_VERSION(RC_VERSION)) dut(
      .aclk(clk),.aresetn(rstn),.s_axi_aclk(axi_clk),.s_axi_aresetn(rstn),
      .s_axis_tdata(command),.s_axis_tvalid(cv),.m_axis_tdata(samples),.m_axis_tvalid(valid),.m_axis_tready(1'b1),
      .s_axi_awaddr(awaddr),.s_axi_awprot(3'd0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
      .s_axi_wdata(wdata),.s_axi_wstrb(4'hf),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
      .s_axi_bvalid(bvalid),.s_axi_bresp(bresp),.s_axi_bready(1'b1),
      .s_axi_araddr(araddr),.s_axi_arprot(3'd0),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
      .s_axi_rdata(rdata),.s_axi_rvalid(rvalid),.s_axi_rready(1'b1));
   task automatic write_reg(input integer addr,input reg [31:0] value,input bit error_expected=0);
      @(negedge axi_clk); awaddr=addr;wdata=value;awvalid=1;wvalid=1;
      do @(posedge axi_clk); while(!(awready && wready));
      if(bresp !== (error_expected ? 2'b10:2'b00)) $fatal(1,"unexpected AXI response");
      @(negedge axi_clk); awvalid=0;wvalid=0;
      repeat(10) @(posedge axi_clk);
   endtask
   task automatic read_reg(input integer addr,output reg [31:0] value);
      @(negedge axi_clk); araddr=addr;arvalid=1;
      do @(posedge axi_clk); while(!arready);
      value=rdata;
      @(negedge axi_clk); arvalid=0;
      repeat(2) @(posedge axi_clk);
   endtask
   task automatic send(input reg [159:0] packet);
      @(negedge clk);command=packet;cv=1;
      @(negedge clk);command=0;cv=0;
   endtask
   task automatic set_value(input integer v);
      reg [159:0] p;
      p=0;p[145:144]=1;p[31:0]=v;send(p);
      repeat(50) @(negedge clk);
   endtask
   task automatic expect_all(input integer value);
      for(int lane=0;lane<16;lane++)
         if($signed(samples[16*lane+:16])!==value) $fatal(1,"RC%0d lane%0d got%0d expected%0d",RC_VERSION,lane,$signed(samples[16*lane+:16]),value);
   endtask
   initial begin
      reg [31:0] status;
      reg [159:0] p;
      repeat(8) @(negedge axi_clk);rstn=1;
      repeat(50) @(negedge clk);
      read_reg(16,status); if(status!==32'hC1080000) $fatal(1,"capability/default disabled");
      set_value(10000);expect_all(10000);
      write_reg(8,-1000);write_reg(12,2000);expect_all(10000); // shadows only
      write_reg(16,3);expect_all(2000);
      read_reg(16,status);if(status[2:0]!==3'b001) $fatal(1,"clip apply not acknowledged");
      set_value(-10000);expect_all(-1000);
      set_value(1232);expect_all(1232);
      set_value(0);expect_all(0);
      write_reg(8,4);write_reg(16,3,1); // zero must remain representable
      set_value(-10000);expect_all(-1000);
      write_reg(8,-1001);write_reg(16,3,1); // effective DAC code alignment
      write_reg(8,-1000);write_reg(12,32768);write_reg(16,3,1);
      write_reg(12,2000);write_reg(16,2);expect_all(-10000); // disabled
      write_reg(16,3);expect_all(-1000);
      // All lanes, signed bounds and in-range transparency through real SET commands.
      for(int v=-32768;v<=32764;v+=2052) begin
         set_value(v);expect_all(v < -1000 ? -1000 : (v > 2000 ? 2000 : v));
      end
      // Fine lane transitions plus RC/DC compensation must also be bounded.
      for(int lane=0;lane<16;lane++) begin
         set_value(0);
         p=0;p[145:144]=2;p[151]=1;
         p[15:0]=10000;p[31:16]=-4000;
         p[66:32]=35'd873813334; // ceil(10000 * 2^18 / 3)
         p[101:67]=-35'sd734003200; // -14000 * 2^18 / 5
         p[105:102]=lane;
         p[110:106]=(lane+4)%16;
         p[143:134]=(lane+4)/16;
         p[133:111]=lane+10;
         send(p);repeat(45) @(negedge clk);expect_all(-1000);
      end
      if(RC_VERSION!=0) begin
         set_value(0);
         p=0;p[145:144]=3;p[149]=1;p[146]=1;p[147]=1;p[31:0]=32'hffff_ffff;send(p);
         set_value(1024);repeat(3000) @(negedge clk);
         expect_all(2000); // compensation pushes the unbounded output above max
      end
      write_reg(0,0);repeat(80) @(negedge clk);expect_all(0);
      // DC compensation produces negative output after a positive shot.
      p=0;p[145:144]=3;p[150]=1;send(p);repeat(30) @(negedge clk);
      set_value(10000);set_value(0);
      p[147:146]=1;p[31:0]=1284;send(p);
      repeat(100) @(negedge clk);expect_all(-1000);
      write_reg(0,0);repeat(80) @(negedge clk);expect_all(0);
      write_reg(16,3);
      read_reg(16,status);if(status[3:0]!==4'b0001) $fatal(1,"sticky clear/zero override");
      $display("PASS: AWG clipping RC_VERSION=%0d AXI shadows/atomic CDC/default bypass/signed bounds/stop/compensation",RC_VERSION);
      done=1;
   end
   always @(negedge clk) if(rstn && dut.clip_enable && valid) begin
      for(int i=0;i<16;i++) begin
         if($signed(samples[16*i+:16]) < dut.clip_min || $signed(samples[16*i+:16]) > dut.clip_max)
            $fatal(1,"lane output escaped limit");
      end
   end
endmodule
module tb_clipping;
   wire done0,done1;
   clipping_case #(.RC_VERSION(0)) a(done0);
   clipping_case #(.RC_VERSION(1)) b(done1);
   initial begin wait(done0 && done1); $finish; end
   initial begin #2000000;$fatal(1,"clipping watchdog"); end
endmodule
