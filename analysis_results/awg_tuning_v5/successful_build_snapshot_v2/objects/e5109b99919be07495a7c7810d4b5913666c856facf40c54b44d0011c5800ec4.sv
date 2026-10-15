`timescale 1ns/1ps
// Direct native commands: 10 us RAMP, HOLD, RAMP, HOLD at 300 MHz.
// RF spans exactly the first or second HOLD; all three physical pairs.
module tb_ramp_hold_alignment;
 reg clk=0;always #1.666667 clk=~clk;
 reg rstn=0,av=0,rv=0;
 reg [159:0] acmd[3],rcmd[3];
 wire [255:0] ar[3],rr[3],af[3],rf[3],y[3];
 for(genvar p=0;p<3;p=p+1)begin: pairs
  native_pair #(.PAIR(p)) dut(clk,rstn,acmd[p],rcmd[p],av,rv,ar[p],rr[p],af[p],rf[p],y[p]);
 end
 integer cycle=0,start_cycle,hold_number,rf_start,checks=0,fd;
 reg checking=0;
 always @(posedge clk)begin
  cycle=cycle+1;#0.02;
  if(checking) for(integer p=0;p<3;p=p+1)begin
   if($isunknown({af[p],rf[p],y[p]}))$fatal(1,"unknown RAMP/HOLD output");
   if((rf[p]!=0)!=(cycle>=rf_start && cycle<rf_start+3000))
    $fatal(1,"RF outside selected 10us HOLD: hold=%0d pair=%0d cycle=%0d expected_start=%0d",hold_number,p,cycle,rf_start);
   if(cycle>=rf_start && cycle<rf_start+3000)begin
    for(integer lane=0;lane<16;lane=lane+1)
     if($signed(af[p][lane*16+:16])!=(hold_number==1 ? (p+1)*4096 : 0))
      $fatal(1,"RF is not on flat HOLD hold=%0d pair=%0d cycle=%0d lane=%0d",hold_number,p,cycle,lane);
    checks=checks+16;
   end
   if(p==0 && cycle>=start_cycle && cycle<start_cycle+12060)
    $fwrite(fd,"%0d,%0d,%0d,%064h,%064h,%064h\n",hold_number,cycle,start_cycle,af[p],rf[p],y[p]);
  end
 end
 task tick;@(posedge clk);#0.1;endtask
 function automatic [159:0] setc(input integer value);
  reg [159:0] c;c=0;c[145:144]=1;c[31:0]=value;return c;
 endfunction
 function automatic [159:0] rampc(input integer a,b);
  reg [159:0] c;longint signed step;
  c=0;c[145:144]=2;c[31:0]=b;c[86:64]=48000;
  step=((64'(b)-a)<<<18)/47999;c[127:96]=step;return c;
 endfunction
 initial begin
  fd=$fopen("ramp_hold.csv","w");$fwrite(fd,"hold,cycle,start,awg,rf,sum\n");
  for(hold_number=1;hold_number<=2;hold_number=hold_number+1)begin
   checking=0;rstn=0;av=0;rv=0;
   for(integer p=0;p<3;p=p+1)begin acmd[p]=0;rcmd[p]=0;end
   repeat(12)tick();@(negedge clk);rstn=1;repeat(100)tick();@(negedge clk);
   start_cycle=cycle+20;rf_start=start_cycle+(hold_number==1?3000:9000)+31;checking=1;
   for(integer n=0;n<12100;n=n+1)begin
    av=(cycle+1==start_cycle || cycle+1==start_cycle+3000 || cycle+1==start_cycle+6000 || cycle+1==start_cycle+9000);
    rv=(cycle+1==rf_start-31);
    for(integer p=0;p<3;p=p+1)begin
     if(cycle+1==start_cycle)acmd[p]=rampc(0,(p+1)*4096);
     else if(cycle+1==start_cycle+3000)acmd[p]=setc((p+1)*4096);
     else if(cycle+1==start_cycle+6000)acmd[p]=rampc((p+1)*4096,0);
     else acmd[p]=setc(0);
     rcmd[p]=0;rcmd[p][31:0]=894785;rcmd[p][111:96]=2000;
     rcmd[p][143:128]=3000;rcmd[p][145:144]=1;rcmd[p][148]=1;
    end
    tick();@(negedge clk);
   end
  end
  $fclose(fd);$display("V5_RAMP_HOLD_PASS pairs=3 hold_cases=2 rf_width_clocks=3000 scalar_hold_checks=%0d",checks);$finish;
 end
 initial begin #200000;$fatal(1,"watchdog");end
endmodule
