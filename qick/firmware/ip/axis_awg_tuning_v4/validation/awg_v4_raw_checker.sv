`timescale 1ns/1ps
// Independent integer command model followed by a fixed public latency.
// No DUT pipeline registers, helpers, or arithmetic results are inspected.
module awg_v4_raw_checker #(parameter integer CHANNEL=0, STARTUP=7)(
 input wire clk, rstn, command_valid,
 input wire [159:0] command,
 input wire [255:0] raw_samples,
 input wire override_valid,
 input wire signed [31:0] override_value
);
 longint tick=0, accept_after=0, checks=0, ramps=0, sets=0, dropped=0, overrides=0;
 integer logical_current=0, held=0, start_value=0, target=0, duration=1;
 integer signed step=0;
 integer index=0, remaining=0;
 reg [255:0] immediate, history[0:STARTUP], expected;
 function automatic integer clamp(input integer value);
   return value>32764 ? 32764 : (value< -32768 ? -32768 : value);
 endfunction
 function automatic integer quant(input longint signed value);
   longint signed code;
   begin
     code=value>>>18;
     if(code>32764) code=32764;
     if(code< -32768) code=-32768;
     return integer'(code)&(-4);
   end
 endfunction
 always @(posedge clk) begin
   if(!rstn) begin
     tick=0; accept_after=0; held=0; logical_current=0; remaining=0;
     for(integer i=0;i<=STARTUP;i=i+1) history[i]=0;
   end else begin
     tick=tick+1;
     for(integer lane=0;lane<16;lane=lane+1) immediate[lane*16+:16]=held;
     // Override has priority; the simultaneous AXIS word is not an ordinary
     // busy rejection and must not contaminate the issue-guard coverage.
     if(override_valid!==1'b1 && command_valid && (command[145:144]==1 || command[145:144]==2)) begin
       if(tick<accept_after) dropped=dropped+1;
       else if(command[145:144]==1) begin
         logical_current=$signed(command[31:0]); held=quant(longint'(logical_current)<<<18);
         for(integer lane=0;lane<16;lane=lane+1) immediate[lane*16+:16]=held;
         if(command[146]) begin held=0; logical_current=0; end
         sets=sets+1; accept_after=tick+1;
       end else begin
         start_value=clamp(logical_current); target=$signed(command[31:0]);
         step=$signed(command[127:96]); duration=command[86:64];
         if(duration==0) duration=1;
         remaining=(duration+15)/16; index=0; accept_after=tick+remaining;
         logical_current=target; ramps=ramps+1;
       end
     end
     if(remaining>0) begin
       for(integer lane=0;lane<16;lane=lane+1) begin
         if(index+lane>=duration-1)
           immediate[lane*16+:16]=quant(longint'(target)<<<18);
         else immediate[lane*16+:16]=quant((longint'(start_value)<<<18)+longint'(step)*(index+lane));
       end
       index=index+16; remaining=remaining-1;
       if(remaining==0) held=quant(longint'(target)<<<18);
     end
     for(integer i=STARTUP;i>0;i=i-1) history[i]=history[i-1];
     history[0]=immediate; expected=history[STARTUP];
     if(override_valid===1'b1) begin
       logical_current=override_value; held=quant(longint'(override_value)<<<18);
       for(integer lane=0;lane<16;lane=lane+1) expected[lane*16+:16]=held;
       for(integer i=0;i<=STARTUP;i=i+1) history[i]=expected;
       accept_after=tick+1; remaining=0; overrides=overrides+1;
     end
     #0.01;
     if(raw_samples!==expected)
       $fatal(1,"AWG V4 mismatch ch=%0d tick=%0d actual=%h expected=%h",CHANNEL,tick,raw_samples,expected);
     checks=checks+16;
   end
 end
 final $display("RAW_AWG_V4_RESULT ch=%0d samples=%0d ramps=%0d sets=%0d ignored_busy=%0d overrides=%0d",CHANNEL,checks,ramps,sets,dropped,overrides);
endmodule
