`timescale 1ns/1ps
// Independent command-to-sample oracle. No internal DUT arithmetic is read.
module awg_v2_raw_checker #(parameter integer CHANNEL=0, STARTUP=7)(
 input wire clk, rstn, command_valid,
 input wire [159:0] command,
 input wire [255:0] raw_samples
);
 longint tick=0, first_cycle=0, last_cycle=0, checks=0, ramps=0, sets=0;
 integer current_value=0, held=0, start_value=0, target=0, duration=0;
 integer signed step=0;
 bit busy=0;
 reg [255:0] expected;
 function automatic integer quant(input longint signed v);
   longint signed code;
   begin
     code=v>>>18;
     if(code>32764)code=32764;
     if(code< -32768)code=-32768;
     quant=integer'(code)&(-4);
   end
 endfunction
 always @(posedge clk) begin
  if(!rstn) begin tick=0;busy=0;held=0;current_value=0;end
  else begin
   tick=tick+1;
   for(integer lane=0;lane<16;lane=lane+1) expected[lane*16+:16]=held;
   if(command_valid && (command[145:144]==1 || command[145:144]==2)) begin
    if(busy) $fatal(1,"AWG command overlaps busy ramp ch=%0d tick=%0d",CHANNEL,tick);
    if(command[145:144]==1) begin
      current_value=$signed(command[31:0]);held=quant(longint'(current_value)<<<18);
      for(integer lane=0;lane<16;lane=lane+1)expected[lane*16+:16]=held;
      if(command[146]) begin held=0;current_value=0;end
      sets=sets+1;
    end else begin
      busy=1;start_value=current_value;target=$signed(command[31:0]);
      step=$signed(command[127:96]);duration=command[86:64];if(duration==0)duration=1;
      first_cycle=tick+STARTUP;last_cycle=first_cycle+(duration+15)/16-1;ramps=ramps+1;
    end
   end
   if(busy && tick>=first_cycle) begin
    for(integer lane=0;lane<16;lane=lane+1) begin
      if((tick-first_cycle)*16+lane >= duration-1)
        expected[lane*16+:16]=quant(longint'(target)<<<18);
      else expected[lane*16+:16]=quant((longint'(start_value)<<<18)+longint'(step)*((tick-first_cycle)*16+lane));
    end
    if(tick==last_cycle) begin busy=0;held=quant(longint'(target)<<<18);current_value=target;end
   end
   #0.01;
   if(raw_samples!==expected) $fatal(1,"AWG V2 raw samples mismatch ch=%0d tick=%0d actual=%h expected=%h",CHANNEL,tick,raw_samples,expected);
   checks=checks+16;
  end
 end
 final $display("RAW_AWG_V2_RESULT ch=%0d samples=%0d ramps=%0d sets=%0d",CHANNEL,checks,ramps,sets);
endmodule
