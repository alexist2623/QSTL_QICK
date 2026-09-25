// Actual tProcessor instruction execution, with host AXI and RFDC/DDR BFMs.
integer cycle=0, events_file, commands_file, samples_file, input_file;
integer gpio_file, fir_file, checks_file, capture_file, epoch_file;
integer checked_samples=0, errors=0, ddr_beats=0, tproc_events=0;
integer run_cycles=150000, cycle_at_start=0;
integer adc_cw=0;
string root_dir, case_dir;
wire [47:0] tproc_time = dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.t_cnt;
wire [159:0] square_cmd = dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tdata;
wire square_valid = dut.sim_bd_i.axis_square_pulse_v1_0.s_axis_tvalid;
wire [255:0] square_samples = dut.sim_bd_i.axis_square_pulse_v1_0.m_axis_tdata;
wire [255:0] dac_samples = ext_axis_register_slice_12_m_axis_tdata;
wire [255:0] awg_samples = ext_axis_register_slice_8_m_axis_tdata;
wire [255:0] rf_samples = ext_axis_register_slice_2_m_axis_tdata;
wire [127:0] fir_samples = dut.sim_bd_i.ddr4_axis_fir_decim_300to1_v2_0.m_axis_tdata;
wire fir_valid = dut.sim_bd_i.ddr4_axis_fir_decim_300to1_v2_0.m_axis_tvalid;
wire [6:0] gpio = {ext_qick_vec2bit_0_dout6,ext_qick_vec2bit_0_dout5,
 ext_qick_vec2bit_0_dout4,ext_qick_vec2bit_0_dout3,ext_qick_vec2bit_0_dout2,
 ext_qick_vec2bit_0_dout1,ext_qick_vec2bit_0_dout0};
logic [6:0] last_gpio=0;
logic [255:0] last_square=0,last_awg=0,last_rf=0,last_dac=0;
logic [31:0] ref_phase=0,ref_ftw=0,ref_offset=0;
integer ref_amp=0;
bit ref_enable=0, ref_clear=0;
logic [255:0] reference_pipe[0:3];
logic [255:0] dac_pipe[0:9];
logic [255:0] reference_word, expected_word, last_core=0;
logic [31:0] phase_for_lane;
integer i,k, code;

task automatic host_write(input integer target,input logic [31:0] address,input logic [31:0] data);
 integer timeout;
 begin
  @(negedge clk_99999985);
  selected=target; host_addr=address; host_data=data;host_aw=1;host_w=1;host_bready=0;
  timeout=0;
  while(host_aw || host_w) begin
   @(posedge clk_99999985);
   if(awready[target]) host_aw<=0;
   if(wready[target]) host_w<=0;
   timeout=timeout+1;
   if(timeout>1000) $fatal(1,"AXI request timeout target=%0d address=%h",target,address);
   @(negedge clk_99999985);
  end
  host_bready=1;
  while(!bvalid[target]) begin
   @(negedge clk_99999985); timeout=timeout+1;
   if(timeout>1000) $fatal(1,"AXI response timeout target=%0d address=%h",target,address);
  end
  if(bresp[target]!==0) $fatal(1,"AXI write error target=%0d",target);
  @(negedge clk_99999985);selected=-1;host_bready=0;
 end
endtask

always @(posedge clk_300000000) begin
 pmem_data <= pmem[ext_axis_tproc64x32_x8_0_pmem_addr >> 3];
 if(!resetn) begin adc_index<=0;adc_data<=0;end
 else begin
  if(adc_cw) adc_data<=adc_rom[adc_index];
  else for(integer lane=0;lane<8;lane=lane+1)
   adc_data[lane*16+:16] <= rf_samples[(2*lane)*16+:16];
  adc_index <= adc_index==29 ? 0 : adc_index+1;
 end
end
always @(negedge clk_300000000) if(resetn) cycle=cycle+1;

// Integer phase-integral reference: deliberately scalar sample-by-sample.
// No copy of the RTL's parallel lane multiplication or adder pipeline.
always @(posedge clk_300000000) begin
 if(!resetn) begin
  ref_phase=0;ref_ftw=0;ref_offset=0;ref_amp=0;ref_enable=0;ref_clear=0;
  for(integer j=0;j<4;j=j+1) reference_pipe[j]=0;
  for(integer j=0;j<10;j=j+1) dac_pipe[j]=0;
 end else begin
  if(ref_clear) ref_phase=0;
  for(integer lane=0;lane<16;lane=lane+1) begin
   phase_for_lane=ref_phase+ref_offset;
   code=ref_enable ? (phase_for_lane[31] ? -ref_amp : ref_amp) : 0;
   reference_word[16*lane+:16]=code;
   ref_phase=ref_phase+ref_ftw;
  end
  for(integer j=3;j>0;j=j-1) reference_pipe[j]=reference_pipe[j-1];
  reference_pipe[0]=reference_word; expected_word=reference_pipe[3];
  ref_clear=0;
  if(square_valid) begin
   ref_ftw=square_cmd[31:0];ref_offset=square_cmd[63:32];
   ref_amp=square_cmd[95:64]>32764 ? 32764 : (square_cmd[95:64]&32'h7ffc);
   ref_enable=square_cmd[128];ref_clear=square_cmd[129];
  end
  // Wait for nonblocking updates in the real DDS and register slice.
  #0.001;
  if(cycle>16) begin
   checked_samples=checked_samples+16;
   if(square_samples !== expected_word) begin
    errors=errors+1;
    if(errors<10) $display("DDS mismatch cycle=%0d actual=%h expected=%h",cycle,square_samples,expected_word);
   end
   if(dac_samples !== dac_pipe[9]) begin
    errors=errors+1;
    if(errors<10) $display("DAC slice mismatch cycle=%0d",cycle);
   end
  end
  for(integer j=9;j>0;j=j-1) dac_pipe[j]=dac_pipe[j-1];
  dac_pipe[0]=square_samples;
  if(square_samples!==last_square || dac_samples!==last_dac || awg_samples!==last_awg || rf_samples!==last_rf || cycle%128==0) begin
   $fwrite(samples_file,"%0d,%h,%h,%h,%h,%h\n",cycle,expected_word,square_samples,dac_samples,awg_samples,rf_samples);
   last_square=square_samples;last_dac=dac_samples;last_awg=awg_samples;last_rf=rf_samples;
  end
  if(gpio!==last_gpio) begin
   $fwrite(gpio_file,"%0d,%0d,%h\n",cycle,tproc_time,gpio);last_gpio=gpio;
  end
  if(fir_valid) $fwrite(fir_file,"%0d,%h\n",cycle,fir_samples);
 end
end

always @(posedge clk_300000000) if(resetn) begin
 if(dut.sim_bd_i.ddr4_axis_buffer_ddr_sample_v3_0.inst.trigger_accept_s)
  $fwrite(capture_file,"%0d,accept,0\n",cycle);
 if(dut.sim_bd_i.ddr4_axis_buffer_ddr_sample_v3_0.inst.trigger_mature_s)
  $fwrite(capture_file,"%0d,mature,0\n",cycle);
 if(dut.sim_bd_i.ddr4_axis_buffer_ddr_sample_v3_0.inst.fifo_wen)
  $fwrite(capture_file,"%0d,sample,%h\n",cycle,dut.sim_bd_i.ddr4_axis_buffer_ddr_sample_v3_0.s_axis_tdata);
end

// Ordered, single-beat AXI memory sink. The real capture engine packs IQ64.
always @(posedge clk_333250000) begin
 if(!resetn) mem_bvalid<=0;
 else begin
  if(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid) begin
   mem_address<=ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr;
   if(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awlen!=0) $fatal(1,"Expected single-beat DDR writes");
  end
  if(mem_bvalid && ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_bready) mem_bvalid<=0;
  if(ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wvalid) begin
   mem_bvalid<=1;ddr_beats=ddr_beats+1;
   $fwrite(memory_file,"%0d,%h,%h,%h\n",cycle,
     ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awvalid ?
       ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_awaddr : mem_address,
     ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wdata,ext_ddr4_axis_buffer_ddr_sample_v3_0_m_axi_wstrb);
  end
 end
end

initial begin : test
 integer f,scan,addr,data,ntrig,seed_mode;
 string pmem_path,adc_path,seed_path;
 resetn=0;
 if(!$value$plusargs("ROOT=%s",root_dir)) $fatal(1,"Missing ROOT");
 if(!$value$plusargs("CASE=%s",case_dir)) $fatal(1,"Missing CASE");
 if(!$value$plusargs("CYCLES=%d",run_cycles)) $fatal(1,"Missing CYCLES");
 if(!$value$plusargs("NTRIG=%d",ntrig)) $fatal(1,"Missing NTRIG");
 if(!$value$plusargs("SEED=%d",seed_mode)) seed_mode=0;
 if(!$value$plusargs("ADC_CW=%d",adc_cw)) adc_cw=0;
 for(integer j=0;j<8192;j=j+1) pmem[j]=64'h3f00000000000000;
 pmem_path=$sformatf("%s/pmem.hex",case_dir);
 adc_path=$sformatf("%s/adc190.hex",root_dir);
 seed_path=$sformatf("%s/seed_pmem.hex",case_dir);
 $readmemh(pmem_path,pmem);
 $readmemh(adc_path,adc_rom);
 if(pmem[0]===64'h3f00000000000000 || $isunknown(pmem[0]) || $isunknown(adc_rom[0]))
  $fatal(1,"PMEM/ADC image was not loaded");
 events_file=$fopen({case_dir,"/rtl_events.csv"},"w");
 commands_file=$fopen({case_dir,"/rtl_commands.csv"},"w");
 samples_file=$fopen({case_dir,"/rtl_samples.csv"},"w");
 gpio_file=$fopen({case_dir,"/rtl_gpio.csv"},"w");
 fir_file=$fopen({case_dir,"/rtl_fir.csv"},"w");
 memory_file=$fopen({case_dir,"/rtl_ddr.csv"},"w");
 capture_file=$fopen({case_dir,"/rtl_capture.csv"},"w");
 epoch_file=$fopen({case_dir,"/rtl_epochs.csv"},"w");
 $fwrite(events_file,"cycle,tproc_time,port,word\n");
 $fwrite(commands_file,"cycle,kind,word\n");
 $fwrite(samples_file,"cycle,expected,core,dac,awg,rf\n");
 $fwrite(gpio_file,"cycle,tproc_time,value\n");
 $fwrite(fir_file,"cycle,iq\n");
 $fwrite(memory_file,"cycle,address,data,strobe\n");
 $fwrite(capture_file,"cycle,kind,iq\n");
 $fwrite(epoch_file,"cycle,kind\n");
 repeat(50) @(negedge clk_99999985);resetn=1;
 host_write(TPROC,0,0);host_write(TPROC,4,0);
 f=$fopen({case_dir,"/dmem.txt"},"r");
 while(!$feof(f)) begin
  scan=$fscanf(f,"%h %h\n",addr,data);
  if(scan==2) host_write(TPROC,256+4*addr,data);
 end
 $fclose(f);
 host_write(SWITCH,0,0);host_write(SWITCH,64,0);host_write(SWITCH,0,2);
 host_write(DDR,0,4);host_write(DDR,4,0);host_write(DDR,8,8);
 host_write(DDR,12,ntrig);host_write(DDR,16,0);host_write(DDR,32,1);
 host_write(DDR,36,8712);host_write(DDR,0,1);
 if(seed_mode) begin
  $readmemh(seed_path,pmem);
  $fwrite(epoch_file,"%0d,seed_start\n",cycle);
  host_write(TPROC,4,1);
  repeat(1200) @(negedge clk_300000000);
  if(dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.ir_r[63:56] !== 8'h3f)
   $fatal(1,"Seed program did not reach END");
  $fwrite(epoch_file,"%0d,seed_end_confirmed\n",cycle);
  // No reset of any generator: END and a new main program must not stop DDS.
  repeat(30000) @(negedge clk_300000000);
  host_write(TPROC,4,0);
  repeat(50) @(negedge clk_300000000);
  $readmemh(pmem_path,pmem);
 end
 repeat(100) @(negedge clk_300000000);
 cycle_at_start=cycle;
 $fwrite(epoch_file,"%0d,gui_start\n",cycle);
 host_write(TPROC,4,1);
 repeat(run_cycles) @(negedge clk_300000000);
 checks_file=$fopen({case_dir,"/rtl_checks.txt"},"w");
 $fwrite(checks_file,"samples=%0d\nerrors=%0d\nddr_beats=%0d\nstart_cycle=%0d\nend_cycle=%0d\n",checked_samples,errors,ddr_beats,cycle_at_start,cycle);
 $fclose(checks_file);
 $display("RTL COMPLETE samples=%0d errors=%0d DDR_beats=%0d",checked_samples,errors,ddr_beats);
 $fclose(events_file);$fclose(commands_file);$fclose(samples_file);$fclose(gpio_file);$fclose(fir_file);$fclose(memory_file);$fclose(capture_file);$fclose(epoch_file);
 if(errors) $fatal(1,"RTL sample comparison failed");
 $finish;
end
