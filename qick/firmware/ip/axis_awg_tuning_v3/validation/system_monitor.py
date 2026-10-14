"""Independent all-clock area/output oracle for the real tProcessor harness."""


def area_monitor(channel, root, shots, expected_path):
    return r'''
begin: AREA_CHECK_@CH@
 logic [255:0] delayed_raw[5];
 logic signed [63:0] planned[0:@LAST@];
 logic [159:0] command;
 bit accepted;
 longint signed total=0, captured=0, magnitude=0, amp=0, q=0, r=0;
 longint start_cycle=-1, end_cycle=-1, zero_check=-1, cmd_cycle=-1;
 longint words=0, index=0, desired=0, remaining=0, expected_done=-1;
 longint samples=0, completed=0, latency_checks=0;
 integer fd,mode=0,sgn=0;
 logic [255:0] expected_word;
 initial begin
  for(integer i=0;i<5;i=i+1)delayed_raw[i]=0;
  $readmemh("@PATH@",planned);
  wait(resetn);
  fd=$fopen({output_dir,"/area_ch@CH@.csv"},"w");
  if(!fd) $fatal(1,"Cannot open area evidence ch=@CH@");
  $fwrite(fd,"shot,command_cycle,first_area_cycle,done_cycle,input_area,residual_area\n");
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=4;i>0;i=i-1)delayed_raw[i]=delayed_raw[i-1];
  delayed_raw[0]=@ROOT@.core_samples;
  command=@ROOT@.s_axis_tdata;
  accepted=@ROOT@.s_axis_tvalid && command[150] && !command[149] &&
           command[145:144]==3 && (command[147:146]==1 || command[147:146]==2);
  #0.002;
  if(@ROOT@.area_fault || @ROOT@.rc_clipped)
   $fatal(1,"AWG v3 area fault or RC clipping ch=@CH@ cycle=%0d",cycle);
  expected_word=delayed_raw[4];
  if(cycle>=start_cycle && cycle<end_cycle && start_cycle>=0) begin
   for(integer lane=0;lane<16;lane=lane+1) begin
    index=(cycle-start_cycle)*16+lane;
    if(mode==2) desired=q+(index<r);
    else begin
     remaining=magnitude-index*amp;
     desired=remaining<=0 ? 0 : (remaining>=amp ? amp : remaining);
    end
    expected_word[16*lane+:16]=16'(sgn*desired*4);
   end
  end
  if(@ROOT@.area_valid) begin
   if(@ROOT@.area_samples!==expected_word)
    $fatal(1,"Area output mismatch ch=@CH@ cycle=%0d actual=%h expected=%h",cycle,@ROOT@.area_samples,expected_word);
   samples=samples+16;
   if(@ROOT@.area_enabled)
    for(integer lane=0;lane<16;lane=lane+1)
     total=total+($signed(@ROOT@.area_samples[16*lane+:16])>>>2);
  end
  if(accepted) begin
   if(completed>=@SHOTS@ || expected_done>=cycle)
    $fatal(1,"Unexpected overlapping compensation ch=@CH@");
   captured=total;
   if(captured!==@ROOT@.area_sum || captured!==planned[completed])
    $fatal(1,"Collected area differs from GUI ledger ch=@CH@ shot=%0d actual=%0d IP=%0d plan=%0d",completed,captured,@ROOT@.area_sum,planned[completed]);
   magnitude=captured<0 ? -captured : captured;
   sgn=captured<0 ? 1 : -1; mode=command[147:146];
   amp=command[15:2];
   if(mode==2) begin
    words=command[95:64]; q=magnitude/(words*16); r=magnitude%(words*16);
   end else words=magnitude==0 ? 1 : (magnitude+amp*16-1)/(amp*16);
   cmd_cycle=cycle; start_cycle=cycle+17; end_cycle=start_cycle+words;
   expected_done=end_cycle+1;
  end
  if(@ROOT@.area_done || cycle==expected_done) begin
   if(!@ROOT@.area_done || cycle!=expected_done || total!=0 || @ROOT@.area_sum!=0)
    $fatal(1,"DC completion/residual mismatch ch=@CH@ cycle=%0d expected=%0d total=%0d",cycle,expected_done,total);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d\n",completed,cmd_cycle,start_cycle,cycle,captured,total);
   completed=completed+1; zero_check=cycle+12;
  end
  if(cycle==zero_check) begin
   if(@ROOT@.m_axis_tdata!==0 || @ROOT@.GEN_RC.rc.integral!==0 || @ROOT@.area_sum!==0)
    $fatal(1,"DC/IIR histories not zero ch=@CH@");
   latency_checks=latency_checks+1;
  end
 end
 final begin
  $fclose(fd);
  if(completed!=@SHOTS@ || latency_checks!=@SHOTS@)
   $fatal(1,"Missing DC shots/reset checks ch=@CH@ completed=%0d checks=%0d",completed,latency_checks);
  $display("AREA_V3_RESULT ch=@CH@ shots=%0d samples=%0d reset_checks=%0d residual=0",completed,samples,latency_checks);
 end
end
'''.replace('@CH@',str(channel)).replace('@ROOT@',root).replace('@SHOTS@',str(shots)).replace('@LAST@',str(shots-1)).replace('@PATH@',expected_path.as_posix())
