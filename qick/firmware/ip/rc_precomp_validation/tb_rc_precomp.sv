`timescale 1ns/1ps
module tb_rc_precomp;
localparam N=5;
logic clk=0,rstn=0;
always #1.666666667 clk=~clk;
logic [159:0] awg_cmd[N],sq_cmd[N];
logic awg_valid=0,sq_valid=0;
wire [255:0] awg_y[N],sq_y[N];
wire [255:0] bypass_y;
wire [159:0] bypass_cmd={awg_cmd[0][159:147],1'b0,awg_cmd[0][145:0]};
real taus[N]='{10.0,100.0,1000.0,100000.0,1000000.0};
logic [31:0] coefficients[N]='{32'd2932031007,32'd293203101,32'd29320310,32'd293203,32'd29320};
logic [47:0] steps1[N]='{48'd3002399751580,48'd300239975158,48'd30023997516,48'd300239975,48'd30023998},steps2[N]='{48'd6004799503161,48'd600479950316,48'd60047995032,48'd600479950,48'd60047995};
integer cycles=0, errors=0, samples_checked=0, csv;
real max_awg_error[N],max_sq_error[N];
for(genvar ch=0;ch<N;ch=ch+1) begin: CHANNEL
  axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) awg (
    .aclk(clk),.aresetn(rstn),.s_axis_tdata(awg_cmd[ch]),.s_axis_tvalid(awg_valid),
    .m_axis_tdata(awg_y[ch]),.m_axis_tready(1'b1),
    .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awvalid(1'b0),.s_axi_wvalid(1'b0),
    .s_axi_arvalid(1'b0),.s_axi_bready(1'b1),.s_axi_rready(1'b1),
    .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),
    .s_axi_araddr(6'd0),.s_axi_arprot(3'd0));
  axis_square_pulse_v1 square (
    .aclk(clk),.aresetn(rstn),.s_axis_tdata(sq_cmd[ch]),.s_axis_tvalid(sq_valid),
    .m_axis_tdata(sq_y[ch]),.m_axis_tready(1'b1),
    .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awvalid(1'b0),.s_axi_wvalid(1'b0),
    .s_axi_arvalid(1'b0),.s_axi_bready(1'b1),.s_axi_rready(1'b1),
    .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),
    .s_axi_araddr(6'd0),.s_axi_arprot(3'd0));

  logic signed [71:0] aq=0,sq=0,aq_lane,sq_lane,value;
  logic signed [71:0] aq_history[0:8],sq_history[0:8];
  logic signed [15:0] prev_x=0;
  logic signed [48:0] prev_step=0,current_step;
  logic [255:0] aq_expected[0:10],sq_expected[0:10],nom_awg[0:10],nom_sq[0:10];
  real za=0,zs=0,decay,da,ds,error_a,error_s,xa,xs;
  integer raw_a,raw_s,actual_a,actual_s;
  logic signed [71:0] tmp;
  function automatic signed [15:0] quant(input logic signed [71:0] y);
    logic signed [71:0] r;
    begin
      r=(y+(72'sd1<<49)) >>> 50;
      if(r>8191) quant=32764;
      else if(r< -8192) quant=-32768;
      else quant=r*4;
    end
  endfunction
  initial begin
    max_awg_error[ch]=0; max_sq_error[ch]=0;
    for(integer s=0;s<11;s=s+1) begin
      aq_expected[s]=0;sq_expected[s]=0;nom_awg[s]=0;nom_sq[s]=0;
    end
    for(integer s=0;s<9;s=s+1) begin aq_history[s]=0;sq_history[s]=0;end
    decay=$exp(-1.0/(4800.0*taus[ch]));
  end
  // Scalar reference follows the published recurrence, independent of the
  // parallel prefix/multiplier/accumulator implementation inside the DUT.
  always @(posedge clk) if(rstn) begin
    for(integer s=8;s>0;s=s-1) begin aq_history[s]=aq_history[s-1];sq_history[s]=sq_history[s-1];end
    for(integer s=10;s>0;s=s-1) begin
      aq_expected[s]=aq_expected[s-1]; sq_expected[s]=sq_expected[s-1];
      nom_awg[s]=nom_awg[s-1]; nom_sq[s]=nom_sq[s-1];
    end
    if(awg.rc_clear) begin aq=0;prev_x=0;end
    if(square.rc_clear) begin sq=0;prev_step=0;end
    for(integer lane=0;lane<16;lane=lane+1) begin
      raw_a=$signed(awg.core_samples[16*lane+:16]);
      raw_s=$signed(square.raw_samples[16*lane+:16]);
      nom_awg[0][16*lane+:16]=raw_a;nom_sq[0][16*lane+:16]=raw_s;
      if(awg.rc_enabled && awg.core_valid) begin
        tmp=raw_a+prev_x;
        aq=aq+tmp*$signed({1'b0,awg.rc_coefficient});
      end
      if(awg.core_valid) prev_x=raw_a;
      value=(72'(raw_a) <<< 48)+aq;
      aq_expected[0][16*lane+:16]=awg.rc_enabled ? quant(value) : raw_a;
      current_step=(!square.samples_active || raw_s==0) ? 49'sd0 :
        ((raw_s<0) ? -$signed({1'b0,square.rc_half_step}) : $signed({1'b0,square.rc_half_step}));
      if(square.rc_enabled && square.samples_active) sq=sq+current_step+prev_step;
      prev_step=current_step;
      value=(72'(raw_s) <<< 48)+sq;
      sq_expected[0][16*lane+:16]=!square.samples_active ? 0 :
        (square.rc_enabled ? quant(value) : raw_s);
    end
    aq_history[0]=aq;sq_history[0]=sq;
    #0.1;
    if(cycles>20) begin
      if(awg.GEN_RC.rc.integral !== aq_history[8]) $fatal(1,"AWG fractional history mismatch ch=%0d cycle=%0d",ch,cycles);
      if(square.GEN_RC.rc.integral !== sq_history[8]) $fatal(1,"Square fractional history mismatch ch=%0d cycle=%0d",ch,cycles);
      if(awg_y[ch] !== aq_expected[10]) $fatal(1,"AWG exact mismatch ch=%0d cycle=%0d got=%h expected=%h",ch,cycles,awg_y[ch],aq_expected[10]);
      if(sq_y[ch] !== sq_expected[10]) $fatal(1,"Square exact mismatch ch=%0d cycle=%0d got=%h expected=%h",ch,cycles,sq_y[ch],sq_expected[10]);
      if(ch==0 && bypass_y !== nom_awg[10]) $fatal(1,"Bypass latency mismatch cycle=%0d",cycles);
      samples_checked=samples_checked+32;
    end
    // Real RC circuit with exact zero-order-hold state transition. This uses
    // the requested analog tau, not the rounded digital coefficient.
    for(integer lane=0;lane<16;lane=lane+1) begin
      actual_a=$signed(awg_y[ch][16*lane+:16]);actual_s=$signed(sq_y[ch][16*lane+:16]);
      da=actual_a-za; ds=actual_s-zs;
      xa=$signed(nom_awg[10][16*lane+:16]);xs=$signed(nom_sq[10][16*lane+:16]);
      error_a=da-xa;error_s=ds-xs;
      if(error_a<0)error_a=-error_a;if(error_s<0)error_s=-error_s;
      if(error_a>max_awg_error[ch])max_awg_error[ch]=error_a;
      if(error_s>max_sq_error[ch])max_sq_error[ch]=error_s;
      if(cycles>100 && (error_a>4.2 || error_s>4.2))
        $fatal(1,"RC circuit error ch=%0d cycle=%0d lane=%0d awg=%f square=%f",ch,cycles,lane,error_a,error_s);
      za=decay*za+(1.0-decay)*actual_a;zs=decay*zs+(1.0-decay)*actual_s;
      if(ch==0 && lane==0 && cycles>20)
        $fwrite(csv,"%0d,%0d,%f,%f,%0d,%f,%f\n",cycles,actual_a,xa,da,actual_s,xs,ds);
    end
  end
end
axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) bypass (
    .aclk(clk),.aresetn(rstn),.s_axis_tdata(bypass_cmd),.s_axis_tvalid(awg_valid),
    .m_axis_tdata(bypass_y),.m_axis_tready(1'b1),
    .s_axi_aclk(clk),.s_axi_aresetn(rstn),.s_axi_awvalid(1'b0),.s_axi_wvalid(1'b0),
    .s_axi_arvalid(1'b0),.s_axi_bready(1'b1),.s_axi_rready(1'b1),
    .s_axi_awaddr(6'd0),.s_axi_awprot(3'd0),.s_axi_wdata(32'd0),.s_axi_wstrb(4'd0),
    .s_axi_araddr(6'd0),.s_axi_arprot(3'd0));

task awg_set(input integer voltage);
  awg_valid=1;
  for(integer c=0;c<N;c=c+1) begin awg_cmd[c]=0;awg_cmd[c][31:0]=voltage;awg_cmd[c][145:144]=1;end
endtask
task square_update(input integer amp,input integer freq,input integer phase,input bit clear);
  sq_valid=1;
  for(integer c=0;c<N;c=c+1) begin
    sq_cmd[c]=0;sq_cmd[c][31:0]=freq;sq_cmd[c][63:32]=phase;sq_cmd[c][79:64]=amp;
    sq_cmd[c][127:80]=(amp==1024) ? steps1[c] : steps2[c];
    sq_cmd[c][128]=1;sq_cmd[c][130]=1;sq_cmd[c][131]=clear;
  end
endtask
initial begin
  csv=$fopen("rc_traces.csv","w");
  $fwrite(csv,"cycle,awg_dac,awg_target,awg_after_rc,square_dac,square_target,square_after_rc\n");
  for(integer c=0;c<N;c=c+1)begin awg_cmd[c]=0;sq_cmd[c]=0;end
  repeat(12) @(negedge clk);rstn=1;
  for(cycles=0;cycles<30000;cycles=cycles+1)begin
    @(negedge clk);awg_valid=0;sq_valid=0;
    if(cycles==10) begin
      awg_valid=1;
      for(integer c=0;c<N;c=c+1)begin
        awg_cmd[c]=0;awg_cmd[c][31:0]=coefficients[c];awg_cmd[c][149]=1;
        awg_cmd[c][145:144]=3;awg_cmd[c][146]=1;awg_cmd[c][147]=1;
      end
      square_update(1024,32'd89478,0,1); // About 100 kHz.
    end
    if(cycles>=100 && cycles%3000==100) awg_set(2048);
    if(cycles>=100 && cycles%3000==1600) awg_set(-2048);
    // Insert a genuine production AWG RAMP between two flat sections.
    if(cycles==7000)begin
      awg_valid=1;
      for(integer c=0;c<N;c=c+1)begin
        awg_cmd[c]=0;awg_cmd[c][31:0]=-2048;awg_cmd[c][86:64]=6400;
        awg_cmd[c][119:96]=-24'sd41950;awg_cmd[c][145:144]=2;
      end
    end
    if(cycles==10000) square_update(2048,32'd89478,0,0);
    if(cycles==15000) square_update(2048,32'd44739,0,0);
    if(cycles==20000) square_update(2048,32'd44739,32'h40000000,0);
  end
  $fclose(csv);
  for(integer c=0;c<N;c=c+1)
    $display("RC_RESULT tau_us=%f max_awg_error_codes=%f max_square_error_codes=%f",taus[c],max_awg_error[c],max_sq_error[c]);
  $display("PASS: real AWG/Square IP, five taus, repeats, updates, matched bypass; scalar comparisons=%0d",samples_checked);
  $finish;
end
endmodule
