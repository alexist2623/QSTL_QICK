module tb();

// =============================================================================
// Parameters
// =============================================================================
parameter N_AVG = 16;   // AVG memory depth: 2^10 = 1024
parameter N_BUF = 16;   // RAW buffer depth
parameter B     = 16;   // per-channel width

// ---- Trace/Stimulus setup ----
localparam int LEN          = 1280;     // samples per trace (AVG_LEN_REG)
localparam int REPS         = 1000;      // number of shots (triggers)
localparam int BASE_ADDR    = 32;      // AVG_ADDR_REG
localparam int AMP_LSB      = 12000;   // sine amplitude in LSBs (safe margin)
localparam int NOISE_LSB    = 1000;    // uniform noise range: [-NOISE_LSB, +NOISE_LSB]

// =============================================================================
// Ports & DUT I/O
// =============================================================================
reg               s_axis_aclk;
reg               s_axis_aresetn;

reg               trigger;

reg               s_axis_tvalid;
wire              s_axis_tready;
reg   [2*B-1:0]   s_axis_tdata;

reg               m_axis_aclk;
reg               m_axis_aresetn;

wire              m0_axis_tvalid;
reg               m0_axis_tready;
wire  [4*B-1:0]   m0_axis_tdata;
wire              m0_axis_tlast;

wire              m1_axis_tvalid;
reg               m1_axis_tready;
wire  [2*B-1:0]   m1_axis_tdata;
wire              m1_axis_tlast;

reg   [1:0]       AVG_START_REG;
reg   [N_AVG-1:0] AVG_ADDR_REG;
reg   [31:0]      AVG_LEN_REG;
reg               AVG_DR_START_REG;
reg   [N_AVG-1:0] AVG_DR_ADDR_REG;
reg   [N_AVG-1:0] AVG_DR_LEN_REG;
reg               BUF_START_REG;
reg   [N_BUF-1:0] BUF_ADDR_REG;
reg   [N_BUF-1:0] BUF_LEN_REG;
reg               BUF_DR_START_REG;
reg   [N_BUF-1:0] BUF_DR_ADDR_REG;
reg   [N_BUF-1:0] BUF_DR_LEN_REG;

// Input data (I/Q channel, B-bit signed each)
reg   [B-1:0]     di_r, dq_r;

int mism = 0;
int signed avg_i;
int signed avg_q;
// DUT
avg_buffer
   #(
      .N_AVG   (N_AVG),
      .N_BUF   (N_BUF),
      .B       (B    )
   )
   DUT
   (
      // s-domain reset/clock
      .s_axis_aclk               (s_axis_aclk),
      .s_axis_aresetn            (s_axis_aresetn),

      // Trigger input
      .trigger                   (trigger),

      // AXIS Slave (input data)
      .s_axis_tvalid             (s_axis_tvalid),
      .s_axis_tready             (s_axis_tready),
      .s_axis_tdata              (s_axis_tdata),

      // m-domain reset/clock
      .m_axis_aclk               (m_axis_aclk),
      .m_axis_aresetn            (m_axis_aresetn),

      // AXIS Master (averaged/accumulated output)
      .m0_axis_tvalid            (m0_axis_tvalid),
      .m0_axis_tready            (m0_axis_tready),
      .m0_axis_tdata             (m0_axis_tdata),
      .m0_axis_tlast             (m0_axis_tlast),

      // AXIS Master (raw output)
      .m1_axis_tvalid            (m1_axis_tvalid),
      .m1_axis_tready            (m1_axis_tready),
      .m1_axis_tdata             (m1_axis_tdata),
      .m1_axis_tlast             (m1_axis_tlast),

      // Registers (AXI-Lite proxy)
      .AVG_START_REG             ({REPS, 14'h0, AVG_START_REG}),
      .AVG_ADDR_REG              (AVG_ADDR_REG),
      .AVG_LEN_REG               (AVG_LEN_REG),
      .AVG_PHOTON_MODE_REG       ('d0),
      .AVG_H_THRSH_REG           ('d0),
      .AVG_L_THRSH_REG           ('d0),
      .AVG_DR_START_REG          (AVG_DR_START_REG),
      .AVG_DR_ADDR_REG           (AVG_DR_ADDR_REG),
      .AVG_DR_LEN_REG            (AVG_DR_LEN_REG),
      .BUF_START_REG             (BUF_START_REG),
      .BUF_ADDR_REG              (BUF_ADDR_REG),
      .BUF_LEN_REG               (BUF_LEN_REG),
      .BUF_DR_START_REG          (BUF_DR_START_REG),
      .BUF_DR_ADDR_REG           (BUF_DR_ADDR_REG),
      .BUF_DR_LEN_REG            (BUF_DR_LEN_REG)
   );

// Pack IQ into 2*B
assign s_axis_tdata = {dq_r, di_r};

// =============================================================================
// Utilities: noise & saturation & scoreboard
// =============================================================================
function automatic int signed noise_uni(input int amp);
   // Uniform noise in [-amp, +amp]
   int unsigned r;
   r = $urandom();
   noise_uni = (r % (2*amp + 1)) - amp;
endfunction

function automatic int signed satB(input int signed v);
   int signed vmax = (1 <<< (B-1)) - 1;
   int signed vmin = - (1 <<< (B-1));
   if (v >  vmax) satB =  vmax;
   else if (v < vmin) satB = vmin;
   else               satB = v;
endfunction

// Golden accumulators and readback capture
int signed golden_i   [0:LEN-1];
int signed golden_q   [0:LEN-1];
int signed read_i     [0:LEN-1];
int signed read_q     [0:LEN-1];

// Clear arrays
task automatic clear_scoreboard();
   for (int k=0; k<LEN; k++) begin
      golden_i[k] = 0;
      golden_q[k] = 0;
      read_i[k]   = 0;
      read_q[k]   = 0;
   end
endtask

// =============================================================================
// Sine-shot generator (trace-wise, two clocks per sample for RMW)
// =============================================================================
task automatic send_one_shot(input int rep);
   real ang;
   int  s_i, s_q;

   // One-cycle trigger pulse at s_axis domain
   @(posedge s_axis_aclk);
   trigger <= 1'b1;
   ang = 6.283185307179586 * 0 / real'(LEN); // 2*pi*k/LEN

   s_i = satB( $rtoi( AMP_LSB * $sin(ang) ) + noise_uni(NOISE_LSB) );
   s_q = satB( $rtoi( AMP_LSB * $cos(ang) ) + noise_uni(NOISE_LSB) );

   di_r <= s_i;   // low B bits kept (two's complement)
   dq_r <= s_q;

   // Scoreboard accumulation in TB
   golden_i[0] += s_i;
   golden_q[0] += s_q;
   @(posedge s_axis_aclk);
   trigger <= 1'b0;
   
   // LEN samples: hold each sample for 2 s_axis cycles (RMW: READ->WRITE)
   for (int k=1; k<LEN; k++) begin
      ang = 6.283185307179586 * k / real'(LEN); // 2*pi*k/LEN

      s_i = satB( $rtoi( AMP_LSB * $sin(ang) ) + noise_uni(NOISE_LSB) );
      s_q = satB( $rtoi( AMP_LSB * $cos(ang) ) + noise_uni(NOISE_LSB) );

      di_r <= s_i;   // low B bits kept (two's complement)
      dq_r <= s_q;

      // Scoreboard accumulation in TB
      golden_i[k] += s_i;
      golden_q[k] += s_q;

      @(posedge s_axis_aclk);
   end
endtask

// =============================================================================
// Clocks
// =============================================================================
always begin
   s_axis_aclk <= 1'b0; #15;
   s_axis_aclk <= 1'b1; #15;
end

always begin
   m_axis_aclk <= 1'b0; #4;
   m_axis_aclk <= 1'b1; #4;
end

// =============================================================================
// Reset & Stimulus (s-axis)
// =============================================================================
event ev_shots_done;

initial begin
   // Defaults
   s_axis_aresetn    <= 0;
   trigger           <= 0;
   s_axis_tvalid     <= 0;
   di_r              <= '0;
   dq_r              <= '0;
   AVG_START_REG     <= 0;
   AVG_ADDR_REG      <= '0;
   AVG_LEN_REG       <= '0;
   BUF_START_REG     <= 0;
   BUF_ADDR_REG      <= '0;
   BUF_LEN_REG       <= '0;

   // Release reset
   #200;
   s_axis_aresetn    <= 1;

   // Program registers for trace-accumulate
   @(posedge s_axis_aclk);
   AVG_ADDR_REG      <= BASE_ADDR[N_AVG-1:0];
   AVG_LEN_REG       <= LEN;
   s_axis_tvalid     <= 1'b1;

   @(posedge s_axis_aclk);
   AVG_START_REG     <= 2'b11;

   repeat ((2**N_AVG) + 100) @(posedge s_axis_aclk);

   // Send REPS shots
   clear_scoreboard();
   for (int r=0; r<REPS; r++) begin
      send_one_shot(r);
      repeat(100) @(posedge s_axis_aclk);
   end

   -> ev_shots_done;
end

// =============================================================================
// Readback & Check (m-axis)
// =============================================================================
event ev_read_done;
int unsigned rd_idx;

always @(posedge m_axis_aclk or negedge m_axis_aresetn) begin
   if (!m_axis_aresetn) begin
      rd_idx <= 0;
   end
   else if (m0_axis_tvalid && m0_axis_tready) begin
      // m0_axis_tdata = {acc_q[2*B-1:0], acc_i[2*B-1:0]}
      read_i[rd_idx] <= $signed(m0_axis_tdata[2*B-1:0]);
      read_q[rd_idx] <= $signed(m0_axis_tdata[4*B-1:2*B]);
      rd_idx         <= rd_idx + 1;
      if (m0_axis_tlast) -> ev_read_done;
   end
end

initial begin
   // m-axis defaults
   m_axis_aresetn    <= 0;
   m0_axis_tready    <= 1;
   m1_axis_tready    <= 1;
   AVG_DR_START_REG  <= 0;
   AVG_DR_ADDR_REG   <= '0;
   AVG_DR_LEN_REG    <= '0;
   BUF_DR_START_REG  <= 0;
   BUF_DR_ADDR_REG   <= '0;
   BUF_DR_LEN_REG    <= '0;

   // Release reset
   #200;
   m_axis_aresetn    <= 1;

   // Wait until shots are done on s-axis
   @ev_shots_done;

   // Small guard time
   repeat (15000) @(posedge m_axis_aclk);

   // Program DR to read back LEN words from BASE_ADDR
   @(posedge m_axis_aclk);
   AVG_DR_ADDR_REG   <= BASE_ADDR[N_AVG-1:0];
   AVG_DR_LEN_REG    <= LEN;

   @(posedge m_axis_aclk);
   AVG_DR_START_REG  <= 1'b1;

   @(posedge m_axis_aclk);
   AVG_DR_START_REG  <= 1'b0;

   // Wait for readback to complete
   @ev_read_done;
   
   #100;
   
   // ----------------------------------------------------------------------------
   // Compare & print
   // ----------------------------------------------------------------------------
   $display("LAST idx: %d",rd_idx);
   $display("\n=== TRACE ACCUM READBACK (LEN=%0d, REPS=%0d) ===", LEN, REPS);
   $display(" idx |   golden_I   read_I   (avg_I) |   golden_Q   read_Q   (avg_Q)");
   $display("-----+--------------------------------+--------------------------------");

   for (int k=0; k<LEN; k++) begin
      // Check equality (exact sum match expected)
      if (read_i[k] !== golden_i[k]) mism++;
      if (read_q[k] !== golden_q[k]) mism++;

      // Integer average for display (sum/REPS)
      avg_i = read_i[k] / REPS;
      avg_q = read_q[k] / REPS;

      if ((k % (LEN/8)) == 0 || k==LEN-1) begin
         $display(" %3d | %10d %10d (%7d) | %10d %10d (%7d)",
            k, golden_i[k], read_i[k], avg_i, golden_q[k], read_q[k], avg_q);
      end
   end

   if (mism==0) $display("RESULT: PASS (all sums match)");
   else         $display("RESULT: FAIL (%0d mismatches)", mism);

   #200;
   $finish;
end

endmodule
