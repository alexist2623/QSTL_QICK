`timescale 1ns/1ps
// Uses the actual synchronous BRAM FIFO, not an idealized FWFT source.
module tb_timed_ictrl_v2;
  reg clk=0;
  always #5 clk=~clk;
  reg rstn=0, wr_en=0, ready=1, ack=0, clock_running=1;
  reg [215:0] din=0;
  reg [47:0] t_cnt=0;
  wire [215:0] dout;
  wire rd_en, full, empty, valid, waitt;
  wire [159:0] data;
  fifo #(.B(216),.N(16)) source_fifo(
    .clk(clk),.rstn(rstn),.wr_en(wr_en),.din(din),.rd_en(rd_en),
    .dout(dout),.full(full),.empty(empty));
  timed_ictrl dut(.clk(clk),.rstn(rstn),.t_cnt(t_cnt),.fifo_rd_en(rd_en),
    .fifo_dout(dout),.fifo_empty(empty),.waitt(waitt),.waitt_ack(ack),
    .m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(ready));

  // A verbatim v1 controller (entity name changed by the runner) establishes
  // the unchanged isolated-command timestamp-to-output latency.
  wire [215:0] old_dout;
  wire old_rd, old_full, old_empty, old_valid, old_wait;
  wire [159:0] old_data;
  reg compare_v1=0;
  fifo #(.B(216),.N(16)) old_fifo(
    .clk(clk),.rstn(rstn),.wr_en(wr_en && compare_v1),.din(din),.rd_en(old_rd),
    .dout(old_dout),.full(old_full),.empty(old_empty));
  timed_ictrl_v1_reference old_dut(.clk(clk),.rstn(rstn),.t_cnt(t_cnt),
    .fifo_rd_en(old_rd),.fifo_dout(old_dout),.fifo_empty(old_empty),
    .waitt(old_wait),.waitt_ack(ack),.m_axis_tdata(old_data),
    .m_axis_tvalid(old_valid),.m_axis_tready(ready));

  reg [159:0] expected_data[0:1023];
  reg [7:0] expected_opcode[0:1023];
  longint signed expected_cycle[0:1023];
  integer head=0, tail=0, total_outputs=0, checks=0, scenarios=0;
  integer wait_edges=0, csv;
  reg previous_wait=0, stalled=0;
  reg [159:0] stalled_data;

  always @(posedge clk) begin
    if (!rstn) t_cnt<=0;
    else if (clock_running) t_cnt<=t_cnt+1;
    if (rstn) begin
      checks=checks+1;
      if (rd_en && empty) $fatal(1,"Read asserted on empty FIFO");
      if (waitt && valid) $fatal(1,"WAIT and output overlap");
      if (compare_v1) begin
        if (valid !== old_valid || waitt !== old_wait)
          $fatal(1,"Isolated v1 timing changed at cycle %0d",t_cnt);
        if (valid && data !== old_data) $fatal(1,"Isolated v1 payload changed");
      end
      if (waitt && !previous_wait) begin
        wait_edges=wait_edges+1;
        $fwrite(csv,"wait,%0d,0,0\n",t_cnt);
      end
      previous_wait=waitt;
      if (stalled && (!valid || data !== stalled_data))
        $fatal(1,"Blocking output changed during backpressure");
      stalled=0;
      if (valid) begin
        if (head>=tail) $fatal(1,"Unexpected or duplicate output at %0d",t_cnt);
        if (data !== expected_data[head]) $fatal(1,"Payload/order mismatch item%0d",head);
        if ((expected_opcode[head]==8'h58 || expected_opcode[head]==8'h1a) && !ready) begin
          stalled=1;
          stalled_data=data;
        end else begin
          if (expected_cycle[head]>=0 && t_cnt!==expected_cycle[head][47:0])
            $fatal(1,"Timestamp mismatch item%0d expected%0d actual%0d",head,expected_cycle[head],t_cnt);
          $fwrite(csv,"set,%0d,%0h,%040h\n",t_cnt,expected_opcode[head],data);
          head=head+1;
          total_outputs=total_outputs+1;
        end
      end
    end else begin
      previous_wait=0;
      stalled=0;
    end
  end

  function automatic [159:0] payload(input integer id);
    payload={32'hfedc0000+id,32'hba980000+id,32'h76540000+id,32'h32100000+id,32'hdeaf0000+id};
  endfunction
  task automatic reset_case;
    @(negedge clk);
    rstn=0;wr_en=0;ready=1;ack=0;clock_running=1;compare_v1=0;
    repeat(3) @(negedge clk);
    head=0;tail=0;wait_edges=0;rstn=1;
    scenarios=scenarios+1;
  endtask
  task automatic enqueue(input [7:0] op,input [47:0] stamp,input integer id,input longint signed sample_cycle);
    @(negedge clk);
    while(full) @(negedge clk);
    if(op==8'h51 || op==8'h58 || op==8'h13 || op==8'h1a) begin
      expected_data[tail]=(op==8'h13 || op==8'h1a)?{128'b0,(32'hdeaf0000+id)}:payload(id);
      expected_opcode[tail]=op;expected_cycle[tail]=sample_cycle;tail=tail+1;
    end
    din={op,stamp,payload(id)};wr_en=1;
    @(negedge clk);wr_en=0;
  endtask
  task automatic reach(input [47:0] cycle);
    while(t_cnt<cycle) @(negedge clk);
  endtask
  task automatic drained;
    if(head!=tail) $fatal(1,"Missing outputs expected%0d received%0d",tail,head);
  endtask
  integer i;
  initial begin
    csv=$fopen("timed_dispatch_events.csv","w");
    $fwrite(csv,"kind,t_cnt,opcode,payload\n");
    reset_case();
    repeat(12) @(negedge clk);
    if(valid || waitt || rd_en) $fatal(1,"Empty FIFO produced activity");
    compare_v1=1;
    enqueue(8'h13,40,1,41);
    enqueue(8'h51,60,2,61);
    enqueue(8'h1a,80,3,81);
    enqueue(8'h58,100,4,101);
    reach(110);drained();
    $display("PASS isolated_v1_latency_and_empty");

    reset_case();
    for(i=0;i<16;i=i+1) enqueue((i%2)?8'h13:8'h51,100+i,100+i,101+i);
    reach(130);drained();
    $display("PASS sixteen_queued_consecutive_timestamps");

    reset_case();
    enqueue(8'hff,90,1,-1); // Original ISA behavior: ignore unknown timed opcode.
    enqueue(8'h51,100,200,101);
    enqueue(8'h51,100,201,102);
    enqueue(8'h13,100,202,103);
    enqueue(8'h51,50,203,104); // Deliberately late behind a later timestamp.
    enqueue(8'h51,105,204,106);
    reach(115);drained();
    enqueue(8'h51,0,205,-1); // Late arrival into an empty synchronous FIFO.
    repeat(6) @(negedge clk);drained();
    $display("PASS_equal_late_order_and_unknown_opcode");

    reset_case();ready=0;
    enqueue(8'h58,100,300,140);
    for(i=1;i<16;i=i+1) enqueue(8'h51,100+i,300+i,140+i);
    reach(140);ready=1;
    reach(160);drained();
    $display("PASS_full_prefetch_backpressure_and_continuous_refill");

    reset_case();ready=0;
    enqueue(8'h1a,100,400,110);
    enqueue(8'h51,101,401,111);
    reach(110);ready=1;
    reach(115);drained();
    ready=0;
    enqueue(8'h13,130,402,131);
    enqueue(8'h51,131,403,132);
    reach(140);drained();
    $display("PASS_setbi_and_nonblocking_ready_semantics");

    reset_case();
    enqueue(8'h15,100,500,-1);
    enqueue(8'h51,101,501,121);
    reach(101);
    if(!waitt) $fatal(1,"WAITI timestamp changed");
    reach(120);
    if(!waitt || head!=0) $fatal(1,"WAITI did not block following command");
    ack=1;
    reach(125);drained();
    if(wait_edges!=1 || waitt) $fatal(1,"WAITI acknowledgement mismatch");
    $display("PASS_waiti_acknowledgement");

    reset_case();ack=1;
    enqueue(8'h54,100,510,-1);
    enqueue(8'h51,101,511,102);
    reach(110);drained();
    if(wait_edges!=1) $fatal(1,"WAIT with early ack missing");
    $display("PASS_wait_with_already_asserted_ack");

    reset_case();
    enqueue(8'h51,100,600,-1);
    enqueue(8'h51,101,601,-1);
    reset_case();
    reach(120);drained();
    if(valid || waitt) $fatal(1,"Reset leaked prefetched commands");
    ready=0;
    enqueue(8'h58,140,602,-1);
    reach(142);
    if(!valid) $fatal(1,"Blocking reset setup failed");
    reset_case();reach(160);drained();
    $display("PASS_reset_pending_prefetch_and_stalled_output");

    reset_case();
    enqueue(8'h51,100,700,101);
    reach(80);t_cnt=5; // Master epoch rollback is not a queue reset in v1 or v2.
    reach(99);clock_running=0;
    repeat(6) begin
      @(negedge clk);
      if(valid || head!=0) $fatal(1,"Frozen clock caused early output");
    end
    clock_running=1;
    reach(110);drained();
    $display("PASS_timestamp_rollback_and_stopped_counter");

    reset_case();
    enqueue(8'h51,48'h800000000040,800,48'h800000000041);
    reach(20);t_cnt=48'h800000000030;
    reach(48'h800000000045);drained();
    $display("PASS_full_unsigned_48bit_timestamp");
    $display("TIMED_V2_PASS scenarios=%0d outputs=%0d checked_cycles=%0d",scenarios,total_outputs,checks);
    $fclose(csv);$finish;
  end
  initial begin #100000; $fatal(1,"Unit test timeout"); end
endmodule
