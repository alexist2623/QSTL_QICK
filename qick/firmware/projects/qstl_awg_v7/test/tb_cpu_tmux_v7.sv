`timescale 1ns / 1ps
// Full fetch/decode/register/ALU/timed-FIFO CPU. Only the AXI host wrapper is
// excluded; the synchronous memories below model the host-loaded PMEM/DMEM.
module tb_cpu_tmux_v7;
reg clk = 0;
always #1.666667 clk = ~clk;
reg rstn = 0, start = 0;
wire [12:0] pmem_addr;
reg [63:0] pmem_do = 0, pmem[0:8191];
wire dmem_we;
wire [11:0] dmem_addr;
wire [31:0] dmem_di;
reg [31:0] dmem_do = 0, dmem[0:4095];
wire [159:0] cpu_word[0:7];
wire cpu_valid[0:7], cpu_ready[0:7];
reg [199:0] events[0:1023];
reg [31:0] meta[0:4];
reg [159:0] expected_word[0:2][0:511];
integer expected_time[0:2][0:511], expected_count[0:2];
integer cpu_seen[0:2], tmux_seen[0:2], cpu_cycle[0:2][0:511];
wire [159:0] acmd[0:2], rcmd[0:2];
wire av[0:2], rv[0:2];
wire [255:0] ar[0:2], rr[0:2], af[0:2], rf[0:2], sum[0:2];
integer cycle = 0, pc_high = 0, dmem_writes = 0, commands_fd, samples_fd;
integer sampled_t = 0, i, p, n;

tproc64x32_x8 #(
   .N(13),
   .M(12)
) cpu (
   .clk(clk),
   .rstn(rstn),
   .start(1'b0),
   .START_SRC_REG(1'b0),
   .START_REG(start),
   .pmem_addr(pmem_addr),
   .pmem_do(pmem_do),
   .dmem_we(dmem_we),
   .dmem_addr(dmem_addr),
   .dmem_di(dmem_di),
   .dmem_do(dmem_do),
   .s0_axis_tdata(64'd0),
   .s0_axis_tvalid(1'b0),
   .s1_axis_tdata(64'd0),
   .s1_axis_tvalid(1'b0),
   .s2_axis_tdata(64'd0),
   .s2_axis_tvalid(1'b0),
   .s3_axis_tdata(64'd0),
   .s3_axis_tvalid(1'b0),
   .m0_axis_tdata(cpu_word[0]),
   .m0_axis_tvalid(cpu_valid[0]),
   .m0_axis_tready(cpu_ready[0]),
   .m1_axis_tdata(cpu_word[1]),
   .m1_axis_tvalid(cpu_valid[1]),
   .m1_axis_tready(cpu_ready[1]),
   .m2_axis_tdata(cpu_word[2]),
   .m2_axis_tvalid(cpu_valid[2]),
   .m2_axis_tready(cpu_ready[2]),
   .m3_axis_tdata(cpu_word[3]),
   .m3_axis_tvalid(cpu_valid[3]),
   .m3_axis_tready(1'b1),
   .m4_axis_tdata(cpu_word[4]),
   .m4_axis_tvalid(cpu_valid[4]),
   .m4_axis_tready(1'b1),
   .m5_axis_tdata(cpu_word[5]),
   .m5_axis_tvalid(cpu_valid[5]),
   .m5_axis_tready(1'b1),
   .m6_axis_tdata(cpu_word[6]),
   .m6_axis_tvalid(cpu_valid[6]),
   .m6_axis_tready(1'b1),
   .m7_axis_tdata(cpu_word[7]),
   .m7_axis_tvalid(cpu_valid[7]),
   .m7_axis_tready(1'b1)
);

always @(posedge clk) begin
   pmem_do <= pmem[pmem_addr];
   dmem_do <= dmem[dmem_addr];
   if (rstn && dmem_we) begin
      if (dmem_addr < 4094) $fatal(1, "CPU unexpectedly overwrote command fixture addr=%0d", dmem_addr);
      dmem[dmem_addr] <= dmem_di;
      dmem_writes = dmem_writes + 1;
   end
end
for (genvar pair = 0; pair < 3; pair = pair + 1) begin : pairs
   axis_tmux_v1 #(
      .N(8),
      .B(160)
   ) tmux (
      .aclk(clk),
      .aresetn(rstn),
      .s_axis_tdata(cpu_word[pair]),
      .s_axis_tvalid(cpu_valid[pair]),
      .s_axis_tready(cpu_ready[pair]),
      .m0_axis_tdata(rcmd[pair]),
      .m0_axis_tvalid(rv[pair]),
      .m1_axis_tdata(acmd[pair]),
      .m1_axis_tvalid(av[pair])
   );
   cpu_native_pair #(
      .PAIR(pair)
   ) datapath (
      clk,
      rstn,
      acmd[pair],
      rcmd[pair],
      av[pair],
      rv[pair],
      ar[pair],
      rr[pair],
      af[pair],
      rf[pair],
      sum[pair]
   );
   cpu_pair_checker #(
      .PAIR(pair)
   ) check_i (
      clk,
      rstn,
      av[pair],
      acmd[pair],
      rv[pair],
      rcmd[pair],
      ar[pair],
      rr[pair],
      af[pair],
      rf[pair],
      sum[pair]
   );
end

always @(posedge clk) begin
   cycle = cycle + 1;
   sampled_t = cpu.t_cnt;
   if (rstn) begin
      if (pmem_addr > pc_high) pc_high = pmem_addr;
      for (integer q = 0; q < 3; q = q + 1) begin
         if (cpu_valid[q]) begin
            if (cpu_seen[q] >= expected_count[q]) $fatal(1, "Unexpected extra CPU command pair=%0d", q);
            if (cpu_word[q] !== expected_word[q][cpu_seen[q]])
               $fatal(1, "CPU command content pair=%0d idx=%0d", q, cpu_seen[q]);
            if (sampled_t != expected_time[q][cpu_seen[q]] + 1)
               $fatal(
                  1,
                  "CPU command timing pair=%0d idx=%0d actual=%0d timestamp=%0d",
                  q,
                  cpu_seen[q],
                  sampled_t,
                  expected_time[q][cpu_seen[q]]
               );
            cpu_cycle[q][cpu_seen[q]] = cycle;
            cpu_seen[q] = cpu_seen[q] + 1;
         end
         if (av[q] || rv[q]) begin
            if (av[q] && rv[q]) $fatal(1, "TMUX delivered two words from one input");
            if (tmux_seen[q] >= cpu_seen[q]) $fatal(1, "TMUX emitted unissued command");
            if ((av[q] ? acmd[q] : rcmd[q]) !== expected_word[q][tmux_seen[q]])
               $fatal(1, "TMUX payload mismatch");
            if (cycle - cpu_cycle[q][tmux_seen[q]] != 2)
               $fatal(1, "TMUX fixed transport was not two clocks");
            if (av[q] !== (expected_word[q][tmux_seen[q]][159:152] == 1))
               $fatal(1, "TMUX routing mismatch");
            $fwrite(commands_fd, "%0d,%0d,%0d,%0d,%0d,%0d,%040h\n", q, tmux_seen[q],
                    expected_time[q][tmux_seen[q]], cpu_cycle[q][tmux_seen[q]], cycle, av[q],
                    av[q] ? acmd[q] : rcmd[q]);
            tmux_seen[q] = tmux_seen[q] + 1;
         end
      end
      for (integer q = 3; q < 8; q = q + 1)
      if (cpu_valid[q]) $fatal(1, "Unexpected unused CPU port=%0d", q);
   end
   #0.03;
   // Three explicitly named required cases. Each scalar lane is a DAC sample;
   // time is exact clock + lane/16, never a rounded 3.33 ns GUI float.
   if (rstn && ((sampled_t >= 19990 && sampled_t < 20120) || (sampled_t >= 21990 && sampled_t < 22120) ||
                (sampled_t >= 33990 && sampled_t < 34120))) begin
      for (integer q = 0; q < 3; q = q + 1)
      for (integer lane = 0; lane < 16; lane = lane + 1)
      $fwrite(
         samples_fd,
         "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",
         sampled_t,
         q,
         lane,
         $signed(
            ar[q][16*lane+:16]
         ),
         $signed(
            af[q][16*lane+:16]
         ),
         $signed(
            rr[q][16*lane+:16]
         ),
         $signed(
            rf[q][16*lane+:16]
         ),
         $signed(
            sum[q][16*lane+:16]
         )
      );
   end
end

initial begin
   for (i = 0; i < 8192; i = i + 1) pmem[i] = 64'h3f00000000000000;
   for (i = 0; i < 4096; i = i + 1) dmem[i] = 0;
   for (p = 0; p < 3; p = p + 1) begin
      expected_count[p] = 0;
      cpu_seen[p] = 0;
      tmux_seen[p] = 0;
   end
   // Literal ASCII filenames avoid the Vivado 2023.1 dynamic-string readmemh
   // issue. The runner copies and hashes these immutable private inputs.
   $readmemh("fixture_meta.hex", meta);
   if (meta[0] !== 762 || meta[1] !== 116330 || meta[2] !== 5340 || meta[3] !== 3810 || meta[4] !== 49)
      $fatal(
         1,
         "Fixture metadata absent/corrupt or unexpected coverage: %h %h %h %h %h",
         meta[0],
         meta[1],
         meta[2],
         meta[3],
         meta[4]
      );
   $readmemh("pmem.hex", pmem, 0, meta[2] - 1);
   $readmemh("dmem.hex", dmem, 0, meta[3] - 1);
   $readmemh("expected_events.hex", events, 0, meta[0] - 1);
   if (pmem[0] === 64'h3f00000000000000 || $isunknown(events[meta[0]-1]) || dmem[3810-1] === 32'd0)
      $fatal(1, "PMEM/DMEM/expected command fixture failed to load");
   for (i = 0; i < meta[0]; i = i + 1) begin
      p = events[i][167:160];
      n = expected_count[p];
      expected_word[p][n] = events[i][159:0];
      expected_time[p][n] = events[i][199:168];
      expected_count[p] = n + 1;
   end
   commands_fd = $fopen("cpu_tmux_commands.csv", "w");
   samples_fd  = $fopen("required_waveforms.csv", "w");
   $fwrite(commands_fd, "pair,index,timestamp,cpu_sample_cycle,generator_sample_cycle,is_awg,word_hex\n");
   $fwrite(samples_fd, "tproc_clock,pair,lane,awg_raw,awg_final,rf_raw,rf_final,combined\n");
   repeat (20) @(negedge clk);
   rstn = 1;
   repeat (100) @(negedge clk);
   start = 1;
   repeat (20) @(negedge clk);
   start = 0;
   wait (dmem[4095] === 32'h07654321);
   repeat (20) @(negedge clk);
   if (dmem[4094] !== 32'h01234567 || dmem_writes != 2 || pc_high < meta[2] - 2)
      $fatal(1, "CPU fetch/data-memory execution proof failed");
   for (p = 0; p < 3; p = p + 1) begin
      if (cpu_seen[p] != expected_count[p] || tmux_seen[p] != expected_count[p])
         $fatal(1, "Missing CPU/TMUX commands");
   end
   $fclose(commands_fd);
   $fclose(samples_fd);
   $display(
      "V7_CPU_TMUX_PASS cases=49 pair_cases=147 commands=762 rf_cases=9 cpu_timestamp_plus=1 tmux=2 awg_native=27 rf_native=29 final=31"
         );
   $display("V7_REQUIRED_CASE_PASS rise1_hold1_fall1 pairs=3 scalar_assertions=pass");
   $display("V7_REQUIRED_CASE_PASS rise1_hold2_fall1 pairs=3 scalar_assertions=pass");
   $display("V7_REQUIRED_CASE_PASS rise2_hold1_fall2 pairs=3 scalar_assertions=pass");
   $finish;
end
initial begin
   #1000000;
   $fatal(1, "Full-CPU watchdog");
end
endmodule

// Independent logical command model plus *fixed* public latency. Inputs are
// independently checked against PMEM-fixture words by the enclosing bench.
module cpu_pair_checker #(
   parameter integer PAIR = 0
) (
   input wire clk,
   rstn,
   av,
   input wire [159:0] acmd,
   input wire rv,
   input wire [159:0] rcmd,
   input wire [255:0] ar,
   rr,
   af,
   rf,
   combined
);
longint tick = 0, accept_after = 0, checks = 0;
integer logical_current = 0, held = 0, start_value = 0, target = 0, duration = 1;
integer signed step = 0;
integer index = 0, remaining = 0, rf_start = -1000, rf_width = 0;
integer ramps = 0, sets = 0, rf_pulses = 0, rf_fd;
reg [255:0] immediate, history[0:31], rfhistory[0:2], wanted_sum, wanted_rf;
function automatic integer clamp(input integer value);
   return value > 32764 ? 32764 : (value < -32768 ? -32768 : value);
endfunction
function automatic integer quant(input longint signed value);
   longint signed code;
   begin
      code = value >>> 18;
      return clamp(integer'(code)) & (-4);
   end
endfunction
function automatic [15:0] round_sum(input integer value);
   integer v;
   begin
      if (value > 32764) v = 32764;
      else if (value < -32768) v = -32768;
      else v = ((value + 2) >>> 2) << 2;
      return v[15:0];
   end
endfunction
initial begin
   case (PAIR)
      0: rf_fd = $fopen("rf_native_pair0.csv", "w");
      1: rf_fd = $fopen("rf_native_pair1.csv", "w");
      2: rf_fd = $fopen("rf_native_pair2.csv", "w");
   endcase
   $fwrite(rf_fd,
           "tick,command_tick,width,raw_expected_nonzero,final_expected_nonzero,raw_hex,final_hex\n");
end
always @(posedge clk) begin
   if (!rstn) begin
      tick = 0;
      accept_after = 0;
      held = 0;
      logical_current = 0;
      remaining = 0;
      for (integer i = 0; i <= 31; i = i + 1) history[i] = 0;
      for (integer i = 0; i <= 2; i = i + 1) rfhistory[i] = 0;
   end else begin
      tick = tick + 1;
      for (integer lane = 0; lane < 16; lane = lane + 1) immediate[lane*16+:16] = held;
      if (av) begin
         if (tick < accept_after) $fatal(1, "Fixture violates ramp reservation pair=%0d", PAIR);
         if (acmd[145:144] == 1) begin
            logical_current = $signed(acmd[31:0]);
            held = quant(longint'(logical_current) <<< 18);
            for (integer lane = 0; lane < 16; lane = lane + 1) immediate[lane*16+:16] = held;
            sets = sets + 1;
            accept_after = tick + 1;
         end else if (acmd[145:144] == 2) begin
            start_value = clamp(logical_current);
            target = $signed(acmd[31:0]);
            step = $signed(acmd[127:96]);
            duration = acmd[86:64];
            if (duration == 0) duration = 1;
            remaining = (duration + 15) / 16;
            index = 0;
            accept_after = tick + remaining;
            logical_current = target;
            ramps = ramps + 1;
         end else $fatal(1, "Unexpected AWG opcode");
      end
      if (remaining > 0) begin
         for (integer lane = 0; lane < 16; lane = lane + 1) begin
            if (index + lane >= duration - 1) immediate[lane*16+:16] = quant(longint'(target) <<< 18);
            else
               immediate[lane*16+:16] = quant(
                  (longint'(start_value) <<< 18) + longint'(step) * (index + lane)
               );
         end
         index = index + 16;
         remaining = remaining - 1;
         if (remaining == 0) held = quant(longint'(target) <<< 18);
      end
      if (rv) begin
         if (rcmd[147] !== 1'b1)
            $fatal(1, "DDS fixture must explicitly select zero after pulse (stdysel=1)");
         rf_start  = tick;
         rf_width  = rcmd[143:128];
         rf_pulses = rf_pulses + 1;
      end
      for (integer i = 31; i > 0; i = i - 1) history[i] = history[i-1];
      history[0] = immediate;
      #0.02;
      for (integer i = 2; i > 0; i = i - 1) rfhistory[i] = rfhistory[i-1];
      rfhistory[0] = rr;
      for (integer lane = 0; lane < 16; lane = lane + 1) begin
         wanted_rf[16*lane+:16] = round_sum($signed(rfhistory[2][16*lane+:16]));
         wanted_sum[16*lane+:16] = round_sum(
            integer'($signed(history[31][16*lane+:16])) + integer'($signed(rfhistory[2][16*lane+:16])));
      end
      if (tick > 100) begin
         if (tick >= rf_start && tick <= rf_start + rf_width + 34)
            $fwrite(
               rf_fd,
               "%0d,%0d,%0d,%0d,%0d,%064h,%064h\n",
               tick,
               rf_start,
               rf_width,
               (tick >= rf_start + 29 && tick < rf_start + 29 + rf_width),
               (tick >= rf_start + 31 && tick < rf_start + 31 + rf_width),
               rr,
               rf
            );
         if (ar !== history[27])
            $fatal(
               1,
               "AWG native27 mismatch pair=%0d tick=%0d actual=%h expected=%h",
               PAIR,
               tick,
               ar,
               history[27]
            );
         if (af !== history[31])
            $fatal(
               1,
               "AWG bypass final31 mismatch pair=%0d tick=%0d actual=%h expected=%h",
               PAIR,
               tick,
               af,
               history[31]
            );
         if (rf !== wanted_rf || combined !== wanted_sum)
            $fatal(1, "Sum arithmetic/pipeline mismatch pair=%0d tick=%0d", PAIR, tick);
         if ((rr != 0) !== (tick >= rf_start + 29 && tick < rf_start + 29 + rf_width))
            $fatal(
               1,
               "DDS native29/width mismatch pair=%0d tick=%0d command=%0d width=%0d raw=%h",
               PAIR,
               tick,
               rf_start,
               rf_width,
               rr
            );
         if ((rf != 0) !== (tick >= rf_start + 31 && tick < rf_start + 31 + rf_width))
            $fatal(
               1,
               "DDS final31/width mismatch pair=%0d tick=%0d command=%0d width=%0d final=%h",
               PAIR,
               tick,
               rf_start,
               rf_width,
               rf
            );
         checks = checks + 16;
      end
   end
end
final begin
   $fclose(rf_fd);
   $display("CPU_PAIR_CHECK pair=%0d scalar_samples=%0d ramps=%0d sets=%0d rf_pulses=%0d", PAIR, checks,
            ramps, sets, rf_pulses);
   if (ramps != 98 || sets != 153 || rf_pulses != 3) $error("Pair coverage incomplete");
end
endmodule
