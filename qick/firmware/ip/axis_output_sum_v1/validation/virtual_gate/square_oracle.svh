// Command-level phase accumulator, independently checks every scalar raw lane.
// The existing output filter is checked separately with exact scalar recurrence.
begin: VIRTUAL_SQUARE_ORACLE
 logic [31:0] ftw=0,phase=0,accumulator=0,lane_phase;
 integer amplitude=0;
 bit enabled=0,clear_phase=0;
 logic [255:0] expected[4], filtered[11];
 logic signed [71:0] integral=0,previous=0,step_value,corrected,rounded;
 logic [159:0] command;
 longint samples=0,commands=0;
 integer raw;
 initial begin
  for(integer i=0;i<4;i=i+1)expected[i]=0;
  for(integer i=0;i<11;i=i+1)filtered[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=3;i>0;i=i-1)expected[i]=expected[i-1];
  for(integer lane=0;lane<16;lane=lane+1) begin
   lane_phase=(clear_phase ? 0 : accumulator)+phase+lane*ftw;
   expected[0][16*lane+:16]=enabled ? (lane_phase[31] ? -amplitude : amplitude) : 0;
  end
  accumulator=(clear_phase ? 0 : accumulator)+16*ftw;
  clear_phase=0;
  if(dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tvalid) begin
   command=dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tdata;
   ftw=command[31:0];phase=command[63:32];amplitude=command[79:64]&16'hfffc;
   enabled=command[128];clear_phase=command[129];commands=commands+1;
  end
  for(integer i=10;i>0;i=i-1)filtered[i]=filtered[i-1];
  if(dut.sim_bd_i.axis_square_pulse_v1_0.rc_clear)begin integral=0;previous=0;end
  for(integer lane=0;lane<16;lane=lane+1) begin
   raw=$signed(dut.sim_bd_i.axis_square_pulse_v1_0.raw_samples[16*lane+:16]);
   step_value=(!dut.sim_bd_i.axis_square_pulse_v1_0.samples_active || raw==0) ? 0 :
      (raw<0 ? -72'(dut.sim_bd_i.axis_square_pulse_v1_0.rc_half_step) : 72'(dut.sim_bd_i.axis_square_pulse_v1_0.rc_half_step));
   if(dut.sim_bd_i.axis_square_pulse_v1_0.rc_enabled && dut.sim_bd_i.axis_square_pulse_v1_0.samples_active)
    integral=integral+step_value+previous;
   previous=step_value;
   corrected=(72'(raw)<<<48)+integral;
   rounded=(corrected+(72'sd1<<49))>>>50;
   if(rounded>8191 || rounded< -8192)$fatal(1,"Unexpected Square clipping");
   filtered[0][16*lane+:16]=!dut.sim_bd_i.axis_square_pulse_v1_0.samples_active ? 0 :
      (dut.sim_bd_i.axis_square_pulse_v1_0.rc_enabled ? 16'(rounded*4) : 16'(raw));
  end
  #0.004;
  if(cycle>30)begin
   if(dut.sim_bd_i.axis_square_pulse_v1_0.raw_samples!==expected[3])$fatal(1,"Square phase/amplitude mismatch cycle=%0d",cycle);
   if(dut.sim_bd_i.axis_square_pulse_v1_0.m_axis_tdata!==filtered[10])$fatal(1,"Square filter mismatch cycle=%0d",cycle);
   samples=samples+16;
  end
 end
 final begin
  if(commands<2 || samples==0)$fatal(1,"Square not exercised");
  $display("VIRTUAL_SQUARE_RESULT commands=%0d raw_and_filtered_samples=%0d",commands,samples);
 end
end
