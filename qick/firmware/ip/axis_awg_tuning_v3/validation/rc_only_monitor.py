"""Read-only RTL assertions for GUI RC enabled with area/DC disabled."""


def rc_only_monitor(channel, root, shots):
    return r'''
begin: RC_ONLY_CHECK_@CH@
 logic [255:0] raw_history[5], nominal_history[11];
 logic [159:0] command;
 longint resets=0, zero_checks=0, check_at=-1, bypass_samples=0;
 longint disable_commands=0, correction_samples=0, rc_active_samples=0;
 integer fd;
 initial begin
  for(integer i=0;i<5;i=i+1)raw_history[i]=0;
  for(integer i=0;i<11;i=i+1)nominal_history[i]=0;
  wait(resetn);
  fd=$fopen({output_dir,"/rc_only_ch@CH@.csv"},"w");
  if(!fd)$fatal(1,"Cannot open RC-only evidence");
  $fwrite(fd,"reset_index,reset_cycle,zero_check_cycle\n");
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=4;i>0;i=i-1)raw_history[i]=raw_history[i-1];
  raw_history[0]=@ROOT@.core_samples;
  for(integer i=10;i>0;i=i-1)nominal_history[i]=nominal_history[i-1];
  nominal_history[0]=@ROOT@.area_samples;
  command=@ROOT@.s_axis_tdata;
  if(@ROOT@.s_axis_tvalid && command[150] && !command[149]) begin
   if(command[145:144]!=3 || command[147:146]!=3)
    $fatal(1,"RC-only emitted DC ARM/EXEC ch=@CH@ cycle=%0d",cycle);
   disable_commands=disable_commands+1;
  end
  if(@ROOT@.rc_clear && @ROOT@.rc_enabled) begin
   resets=resets+1; check_at=cycle+12;
   if(@ROOT@.core_samples!==0 || @ROOT@.area_samples!==0)
    $fatal(1,"RC-only history reset before nominal zero ch=@CH@ cycle=%0d",cycle);
  end
  #0.002;
  if(@ROOT@.area_enabled || @ROOT@.area_busy || @ROOT@.area_done ||
     @ROOT@.area_sum!==0 || @ROOT@.area_completed_shots!==0 || @ROOT@.area_fault || @ROOT@.rc_clipped)
   $fatal(1,"RC-only must keep DC engine disabled and fault-free ch=@CH@ cycle=%0d",cycle);
  if(@ROOT@.area_valid) begin
   if(@ROOT@.area_samples!==raw_history[4])
    $fatal(1,"RC-only area path inserted unexpected samples ch=@CH@ cycle=%0d",cycle);
   bypass_samples=bypass_samples+16;
  end
  if(@ROOT@.rc_enabled && @ROOT@.m_axis_tvalid) begin
   rc_active_samples=rc_active_samples+16;
   for(integer lane=0;lane<16;lane=lane+1)
    if(@ROOT@.m_axis_tdata[16*lane+:16]!==nominal_history[10][16*lane+:16])
     correction_samples=correction_samples+1;
  end
  if(cycle==check_at) begin
   if(@ROOT@.m_axis_tdata!==0 || @ROOT@.GEN_RC.rc.integral!==0)
    $fatal(1,"RC-only output/history not zero after reset ch=@CH@ cycle=%0d",cycle);
   zero_checks=zero_checks+1;
   $fwrite(fd,"%0d,%0d,%0d\n",zero_checks-1,check_at-12,cycle);
  end
 end
 final begin
  $fclose(fd);
  if(resets!=@RESETS@ || zero_checks!=@RESETS@ || disable_commands!=1 ||
     bypass_samples==0 || rc_active_samples==0 || correction_samples==0)
   $fatal(1,"Incomplete RC-only checks ch=@CH@: resets=%0d zero=%0d disable=%0d corrected=%0d",
          resets,zero_checks,disable_commands,correction_samples);
  $display("RC_ONLY_RESULT ch=@CH@ shots=@SHOTS@ dc_execute=0 dc_disable=%0d rc_resets=%0d zero_checks=%0d bypass_samples=%0d rc_active_samples=%0d corrected_samples=%0d",
           disable_commands,resets,zero_checks,bypass_samples,rc_active_samples,correction_samples);
 end
end
'''.replace('@CH@',str(channel)).replace('@ROOT@',root).replace('@SHOTS@',str(shots)).replace('@RESETS@',str(shots+1))
