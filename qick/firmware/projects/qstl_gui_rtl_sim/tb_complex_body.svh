// Actual dual-AWG path: full and focused DUTs execute the same PMEM image.
integer cycle=0,events_file,commands_file,samples_file,gpio_file,checks_file;
integer run_cycles=0,cycle_at_start=0,sample_words=0,errors=0;
string case_dir,output_dir;
wire [47:0] tproc_time=dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.t_cnt;
wire [255:0] awg1=ext_axis_register_slice_8_m_axis_tdata;
wire [255:0] awg3=ext_axis_register_slice_10_m_axis_tdata;
wire [6:0] gpio={ext_qick_vec2bit_0_dout6,ext_qick_vec2bit_0_dout5,
 ext_qick_vec2bit_0_dout4,ext_qick_vec2bit_0_dout3,ext_qick_vec2bit_0_dout2,
 ext_qick_vec2bit_0_dout1,ext_qick_vec2bit_0_dout0};
logic [255:0] last_awg1=0,last_awg3=0;
logic [6:0] last_gpio=0;

task automatic host_write(input integer target,input logic [31:0] address,input logic [31:0] data);
 integer timeout;
 begin
  @(negedge clk_99999985);
  selected=target;host_addr=address;host_data=data;host_aw=1;host_w=1;host_bready=0;
  timeout=0;
  while(host_aw || host_w) begin
   @(posedge clk_99999985);
   if(awready[target]) host_aw<=0;
   if(wready[target]) host_w<=0;
   timeout=timeout+1;
   if(timeout>1000) $fatal(1,"AXI request timeout");
   @(negedge clk_99999985);
  end
  host_bready=1;
  while(!bvalid[target]) begin
   @(negedge clk_99999985);timeout=timeout+1;
   if(timeout>1000) $fatal(1,"AXI response timeout");
  end
  if(bresp[target]!==0) $fatal(1,"AXI write error");
  @(negedge clk_99999985);selected=-1;host_bready=0;
 end
endtask

always @(posedge clk_300000000)
 pmem_data<=pmem[ext_axis_tproc64x32_x8_0_pmem_addr>>3];
always @(negedge clk_300000000) if(resetn) cycle=cycle+1;

always @(posedge clk_300000000) if(resetn) begin
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m1_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,0,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m1_axis_tdata);
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m2_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,1,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m2_axis_tdata);
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m8_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,7,%040h\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m8_axis_tdata);
 if(dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tvalid && dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tready)
  $fwrite(commands_file,"%0d,1,%040h\n",cycle,dut.sim_bd_i.axis_awg_tuning_v1_4.s_axis_tdata);
 if(dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tvalid && dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tready)
  $fwrite(commands_file,"%0d,3,%040h\n",cycle,dut.sim_bd_i.axis_awg_tuning_v1_5.s_axis_tdata);
 #0.001;
 if(cycle>16) begin
  sample_words=sample_words+1;
  if($isunknown(awg1) || $isunknown(awg3)) begin
   errors=errors+1;
   if(errors<4) $display("Unknown AWG sample at %0d",cycle);
  end
 end
 if(awg1!==last_awg1 || awg3!==last_awg3 || cycle%128==0) begin
  $fwrite(samples_file,"%0d,%064h,%064h\n",cycle,awg1,awg3);
  last_awg1=awg1;last_awg3=awg3;
 end
 if(gpio!==last_gpio) begin
  $fwrite(gpio_file,"%0d,%0d,%h\n",cycle,tproc_time,gpio);last_gpio=gpio;
 end
end

initial begin : test
 integer f,scan,addr,data,require_end;
 string pmem_path;
 resetn=0;
 if(!$value$plusargs("CASE=%s",case_dir)) $fatal(1,"Missing CASE");
 if(!$value$plusargs("OUT=%s",output_dir)) $fatal(1,"Missing OUT");
 if(!$value$plusargs("CYCLES=%d",run_cycles)) $fatal(1,"Missing CYCLES");
 if(!$value$plusargs("REQUIRE_END=%d",require_end)) require_end=1;
 for(integer j=0;j<8192;j=j+1) pmem[j]=64'h3f00000000000000;
 pmem_path=$sformatf("%s/pmem.hex",case_dir);$readmemh(pmem_path,pmem);
 if($isunknown(pmem[0])) $fatal(1,"PMEM not loaded");
 events_file=$fopen({output_dir,"/rtl_events.csv"},"w");
 commands_file=$fopen({output_dir,"/rtl_commands.csv"},"w");
 samples_file=$fopen({output_dir,"/rtl_samples.csv"},"w");
 gpio_file=$fopen({output_dir,"/rtl_gpio.csv"},"w");
 $fwrite(events_file,"cycle,tproc_time,port,word\n");
 $fwrite(commands_file,"cycle,gen,word\n");
 $fwrite(samples_file,"cycle,awg1,awg3\n");
 $fwrite(gpio_file,"cycle,tproc_time,value\n");
 repeat(50) @(negedge clk_99999985);resetn=1;
 host_write(TPROC,0,0);host_write(TPROC,4,0);
 f=$fopen({case_dir,"/dmem.txt"},"r");
 while(!$feof(f)) begin
  scan=$fscanf(f,"%h %h\n",addr,data);
  if(scan==2) host_write(TPROC,256+4*addr,data);
 end
 $fclose(f);
 repeat(100) @(negedge clk_300000000);
 cycle_at_start=cycle;host_write(TPROC,4,1);
 repeat(run_cycles) @(negedge clk_300000000);
 if(require_end && dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.ir_r[63:56]!==8'h3f)
  $fatal(1,"Program did not reach END");
 checks_file=$fopen({output_dir,"/rtl_checks.txt"},"w");
 $fwrite(checks_file,"samples_per_channel=%0d\nerrors=%0d\nstart_cycle=%0d\nend_cycle=%0d\nend_required=%0d\n",sample_words*16,errors,cycle_at_start,cycle,require_end);
 $fclose(checks_file);$fclose(events_file);$fclose(commands_file);$fclose(samples_file);$fclose(gpio_file);
 $display("RTL COMPLETE two-AWG samples/channel=%0d errors=%0d",sample_words*16,errors);
 if(errors) $fatal(1,"Unknown AWG output");
 $finish;
end
