`timescale 1ns/1ps
// Compare one-cycle TMUX acceptance with the unchanged tProcessor dispatcher.
module tb_shared_command_spacing;
  reg clk=0; always #1.666667 clk=~clk;
  reg rstn=0;
  reg [47:0] counter=0;
  always @(posedge clk) if(!rstn) counter<=0; else counter<=counter+1;
  reg wr=0; reg [215:0] din=0;
  wire rd,empty,full,scheduled_valid,scheduled_ready;
  wire [215:0] dout;
  wire [159:0] scheduled_word;
  fifo #(.B(216),.N(16)) queue(rstn,clk,wr,din,rd,dout,full,empty);
  timed_ictrl dispatcher(clk,rstn,counter,rd,dout,empty,,1'b0,
                         scheduled_word,scheduled_valid,scheduled_ready);
  wire qv0,qv1;wire [159:0] qd0,qd1;
  tmux #(.N(8),.B(160)) queued_tmux(
    .aresetn(rstn),.aclk(clk),.s_axis_tready(scheduled_ready),
    .s_axis_tvalid(scheduled_valid),.s_axis_tdata(scheduled_word),
    .m0_axis_tvalid(qv0),.m0_axis_tdata(qd0),.m1_axis_tvalid(qv1),.m1_axis_tdata(qd1));
  reg direct_valid=0;reg [159:0] direct_word=0;
  wire dv0,dv1;wire [159:0] dd0,dd1;
  tmux #(.N(8),.B(160)) direct_tmux(
    .aresetn(rstn),.aclk(clk),.s_axis_tready(),
    .s_axis_tvalid(direct_valid),.s_axis_tdata(direct_word),
    .m0_axis_tvalid(dv0),.m0_axis_tdata(dd0),.m1_axis_tvalid(dv1),.m1_axis_tdata(dd1));
  integer direct_count=0,queued_count=0,gap=0,i;
  integer direct_last=-1,queued_last=-1;
  integer direct_intervals=0,queued_intervals=0;
  reg [159:0] observed;
  always @(posedge clk) begin
    #0.01;
    if(rstn && (dv0||dv1))begin
      if(dv0&&dv1)$fatal(1,"Direct TMUX sent a word to both destinations");
      observed=dv1 ? dd1 : dd0;
      if(observed[31:0]!==direct_count || dv1!==((direct_count%2)!=0))
        $fatal(1,"Direct TMUX word/order/destination mismatch");
      if(direct_last>=0)begin
        if(counter-direct_last!=1)$fatal(1,"Direct TMUX did not accept every clock");
        direct_intervals++;
      end
      direct_last=counter;direct_count++;
    end
    if(rstn && (qv0||qv1))begin
      if(qv0&&qv1)$fatal(1,"Queued TMUX duplicate destination");
      observed=qv1 ? qd1 : qd0;
      if(observed[31:0]!==queued_count || qv1!==((queued_count%2)!=0))
        $fatal(1,"Queued TMUX word/order/destination mismatch");
      if(queued_last>=0)begin
        $display("DISPATCH_INTERVAL requested=%0d actual=%0d from=%0d to=%0d",gap,counter-queued_last,queued_last,counter);
        if(counter-queued_last!=(gap<3 ? 3 : gap))$fatal(1,"Dispatcher interval differs from FSM analysis");
        queued_intervals++;
      end
      queued_last=counter;queued_count++;
    end
  end
  initial begin
    repeat(4)@(negedge clk);rstn=1;
    for(i=0;i<512;i++)begin
      direct_valid=1;direct_word=0;
      direct_word[159:152]=(i%2);direct_word[31:0]=i;
      @(negedge clk);
    end
    direct_valid=0;repeat(4)@(negedge clk);
    if(direct_count!=512 || direct_intervals!=511)$fatal(1,"Missing direct TMUX coverage");
    for(gap=1;gap<=4;gap++)begin
      rstn=0;wr=0;repeat(4)@(negedge clk);
      queued_count=0;queued_last=-1;rstn=1;
      for(i=0;i<4;i++)begin
        din=0;din[215:208]=8'h51;din[207:160]=100+i*gap;
        din[159:152]=i%2;din[31:0]=i;wr=1;
        @(negedge clk);
      end
      wr=0;repeat(140)@(negedge clk);
      if(queued_count!=4)$fatal(1,"Missing dispatcher commands");
    end
    if(queued_intervals!=12)$fatal(1,"Missing interval coverage");
    $display("SHARED_COMMAND_SPACING_PASS direct_tmux_words=%0d direct_gap=1 dispatcher_minimum_gap=3",direct_count);
    $finish;
  end
  initial begin #20000;$fatal(1,"watchdog");end
endmodule
