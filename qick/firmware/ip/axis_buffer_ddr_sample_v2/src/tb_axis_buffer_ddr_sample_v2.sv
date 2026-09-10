// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps
`default_nettype none

// The project integration bench can reuse the AXI memory model and tasks
// while supplying a real FIR stream and its own stimulus.
module tb_axis_buffer_ddr_sample_v2 #(
    parameter bit RUN_REGRESSION = 1'b1,
    parameter realtime SOURCE_HALF_PERIOD_NS = 4.0
);

    localparam int ID_WIDTH = 1;
    localparam int FIFO_ADDR_WIDTH = 4;
    localparam int TRIGGER_QUEUE_ADDR_WIDTH = 3;
    localparam int AXI_WORD_BYTES = 32;
    localparam int LANES = 8;
    localparam int MAX_WRITES = 512;
    localparam int MAX_PENDING = 64;
    localparam int REG_CONTROL = 0;
    localparam int REG_WADDR = 1;
    localparam int REG_NSAMP = 2;
    localparam int REG_NTRIG = 3;
    localparam int REG_STRIDE = 4;
    localparam int REG_STATUS = 5;
    localparam int REG_SAMPLE_COUNT = 6;
    localparam int REG_TRIGGER_COUNT = 7;
    localparam int REG_SAMPLE_DECIM = 8;
    localparam int REG_TRIGGER_DELAY = 9;
    localparam int STATUS_BUSY = 0;
    localparam int STATUS_DONE = 1;
    localparam int STATUS_OVERFLOW = 2;
    localparam int STATUS_ARMED = 3;

    logic s_axis_aclk = 1'b0;
    logic m_axi_aclk  = 1'b0;
    logic s_axi_aclk  = 1'b0;

    logic s_axis_aresetn = 1'b0;
    logic m_axi_aresetn  = 1'b0;
    logic s_axi_aresetn  = 1'b0;
    logic trigger = 1'b0;

    wire         s_axis_tready;
    logic [31:0] s_axis_tdata = '0;
    logic        s_axis_tvalid = 1'b0;
    logic        s_axis_tlast = 1'b0;

    logic [7:0]  s_axi_awaddr = '0;
    logic [2:0]  s_axi_awprot = '0;
    logic        s_axi_awvalid = 1'b0;
    wire         s_axi_awready;
    logic [31:0] s_axi_wdata = '0;
    logic [3:0]  s_axi_wstrb = 4'hF;
    logic        s_axi_wvalid = 1'b0;
    wire         s_axi_wready;
    wire [1:0]   s_axi_bresp;
    wire         s_axi_bvalid;
    logic        s_axi_bready = 1'b0;
    logic [7:0]  s_axi_araddr = '0;
    logic [2:0]  s_axi_arprot = '0;
    logic        s_axi_arvalid = 1'b0;
    wire         s_axi_arready;
    wire [31:0]  s_axi_rdata;
    wire [1:0]   s_axi_rresp;
    wire         s_axi_rvalid;
    logic        s_axi_rready = 1'b0;

    wire [ID_WIDTH-1:0] m_axi_awid;
    wire [31:0]         m_axi_awaddr;
    wire [7:0]          m_axi_awlen;
    wire [2:0]          m_axi_awsize;
    wire [1:0]          m_axi_awburst;
    wire                m_axi_awlock;
    wire [3:0]          m_axi_awcache;
    wire [2:0]          m_axi_awprot;
    wire [3:0]          m_axi_awregion;
    wire [3:0]          m_axi_awqos;
    wire                m_axi_awvalid;
    logic               m_axi_awready = 1'b0;

    wire [255:0]        m_axi_wdata;
    wire [31:0]         m_axi_wstrb;
    wire                m_axi_wlast;
    wire                m_axi_wvalid;
    logic               m_axi_wready = 1'b0;

    logic [ID_WIDTH-1:0] m_axi_bid = '0;
    logic [1:0]          m_axi_bresp = 2'b00;
    logic                m_axi_bvalid = 1'b0;
    wire                 m_axi_bready;

    int errors = 0;
    int completed_count = 0;

    logic [31:0]  completed_addr [0:MAX_WRITES-1];
    logic [255:0] completed_data [0:MAX_WRITES-1];
    logic [31:0]  completed_strb [0:MAX_WRITES-1];

    logic [31:0]  aw_addr_q [0:MAX_PENDING-1];
    logic [255:0] w_data_q [0:MAX_PENDING-1];
    logic [31:0]  w_strb_q [0:MAX_PENDING-1];

    int aw_head = 0;
    int aw_tail = 0;
    int aw_count = 0;
    int w_head = 0;
    int w_tail = 0;
    int w_count = 0;

    logic [31:0]  resp_addr = '0;
    logic [255:0] resp_data = '0;
    logic [31:0]  resp_strb = '0;
    logic         resp_pending = 1'b0;
    int           resp_delay_count = 0;
    int           b_delay_cycles = 0;
    int           aw_stall_count = 0;
    int           w_stall_count = 0;
    int           s_axis_cycle_count = 0;
    bit           delay_monitor_enable = 1'b0;
    int           delay_accept_count = 0;
    int           delay_start_count = 0;
    int           delay_accept_cycle [0:MAX_PENDING-1];
    int           delay_start_cycle [0:MAX_PENDING-1];
    logic [31:0]  delay_start_data [0:MAX_PENDING-1];

    logic aw_prev_backpressured = 1'b0;
    logic [31:0] aw_prev_addr = '0;
    logic [7:0]  aw_prev_len = '0;
    logic [2:0]  aw_prev_size = '0;
    logic [1:0]  aw_prev_burst = '0;

    logic w_prev_backpressured = 1'b0;
    logic [255:0] w_prev_data = '0;
    logic [31:0]  w_prev_strb = '0;
    logic         w_prev_last = 1'b0;

    logic s_prev_backpressured = 1'b0;
    logic [31:0] s_prev_data = '0;

    always #5 s_axi_aclk = ~s_axi_aclk;
    always #(SOURCE_HALF_PERIOD_NS) s_axis_aclk = ~s_axis_aclk;
    always #3 m_axi_aclk = ~m_axi_aclk;

    initial begin
        #600000;
        $fatal(1, "FAIL: global simulation timeout");
    end

    axis_buffer_ddr_sample_v2 #(
        .TARGET_SLAVE_BASE_ADDR(32'h0000_0000),
        .ID_WIDTH(ID_WIDTH),
        .S_AXIS_DATA_WIDTH(32),
        .M_AXI_DATA_WIDTH(256),
        .FIFO_ADDR_WIDTH(FIFO_ADDR_WIDTH),
        .TRIGGER_QUEUE_ADDR_WIDTH(TRIGGER_QUEUE_ADDR_WIDTH)
    ) dut (
        .s_axis_aclk(s_axis_aclk),
        .s_axis_aresetn(s_axis_aresetn),
        .m_axi_aclk(m_axi_aclk),
        .m_axi_aresetn(m_axi_aresetn),
        .s_axi_aclk(s_axi_aclk),
        .s_axi_aresetn(s_axi_aresetn),
        .trigger(trigger),
        .s_axis_tready(s_axis_tready),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tlast(s_axis_tlast),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awprot(s_axi_awprot),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .m_axi_awid(m_axi_awid),
        .m_axi_awaddr(m_axi_awaddr),
        .m_axi_awlen(m_axi_awlen),
        .m_axi_awsize(m_axi_awsize),
        .m_axi_awburst(m_axi_awburst),
        .m_axi_awlock(m_axi_awlock),
        .m_axi_awcache(m_axi_awcache),
        .m_axi_awprot(m_axi_awprot),
        .m_axi_awregion(m_axi_awregion),
        .m_axi_awqos(m_axi_awqos),
        .m_axi_awvalid(m_axi_awvalid),
        .m_axi_awready(m_axi_awready),
        .m_axi_wdata(m_axi_wdata),
        .m_axi_wstrb(m_axi_wstrb),
        .m_axi_wlast(m_axi_wlast),
        .m_axi_wvalid(m_axi_wvalid),
        .m_axi_wready(m_axi_wready),
        .m_axi_bid(m_axi_bid),
        .m_axi_bresp(m_axi_bresp),
        .m_axi_bvalid(m_axi_bvalid),
        .m_axi_bready(m_axi_bready)
    );

    always @(posedge s_axis_aclk) begin
        if (!s_axis_aresetn) begin
            s_axis_cycle_count = 0;
        end else begin
            s_axis_cycle_count = s_axis_cycle_count + 1;
            if (delay_monitor_enable && dut.trigger_accept_s) begin
                delay_accept_cycle[delay_accept_count] = s_axis_cycle_count;
                delay_accept_count = delay_accept_count + 1;
            end
            if (delay_monitor_enable && dut.trigger_start_s) begin
                delay_start_cycle[delay_start_count] = s_axis_cycle_count;
                delay_start_data[delay_start_count] = s_axis_tdata;
                delay_start_count = delay_start_count + 1;
            end
        end
    end

    task automatic fail(input string msg);
        begin
            $display("FAIL: %s at %0t", msg, $time);
            errors++;
        end
    endtask

    task automatic check(input bit cond, input string msg);
        begin
            if (!cond)
                fail(msg);
        end
    endtask

    task automatic wait_s_axis(input int cycles);
        begin
            repeat (cycles) @(posedge s_axis_aclk);
        end
    endtask

    task automatic wait_m_axi(input int cycles);
        begin
            repeat (cycles) @(posedge m_axi_aclk);
        end
    endtask

    task automatic wait_axi(input int cycles);
        begin
            repeat (cycles) @(posedge s_axi_aclk);
        end
    endtask

    task automatic reset_dut();
        begin
            s_axis_aresetn <= 1'b0;
            m_axi_aresetn  <= 1'b0;
            s_axi_aresetn  <= 1'b0;
            trigger <= 1'b0;
            s_axis_tdata <= '0;
            s_axis_tvalid <= 1'b0;
            s_axis_tlast <= 1'b0;
            s_axi_awaddr <= '0;
            s_axi_awprot <= '0;
            s_axi_awvalid <= 1'b0;
            s_axi_wdata <= '0;
            s_axi_wstrb <= 4'hF;
            s_axi_wvalid <= 1'b0;
            s_axi_bready <= 1'b0;
            s_axi_araddr <= '0;
            s_axi_arprot <= '0;
            s_axi_arvalid <= 1'b0;
            s_axi_rready <= 1'b0;
            clear_scoreboard();
            wait_axi(5);
            s_axis_aresetn <= 1'b1;
            m_axi_aresetn  <= 1'b1;
            s_axi_aresetn  <= 1'b1;
            wait_axi(10);
            wait_s_axis(6);
            wait_m_axi(6);
        end
    endtask

    task automatic clear_scoreboard();
        begin
            completed_count = 0;
            aw_head = 0;
            aw_tail = 0;
            aw_count = 0;
            w_head = 0;
            w_tail = 0;
            w_count = 0;
            resp_pending = 1'b0;
            resp_delay_count = 0;
            b_delay_cycles = 0;
            aw_stall_count = 0;
            w_stall_count = 0;
        end
    endtask

    task automatic axi_write32(input int reg_index, input logic [31:0] data);
        int timeout;
        bit aw_done;
        bit w_done;
        begin
            timeout = 0;
            aw_done = 1'b0;
            w_done = 1'b0;
            @(negedge s_axi_aclk);
            s_axi_awaddr  <= reg_index[7:0] << 2;
            s_axi_wdata   <= data;
            s_axi_wstrb   <= 4'hF;
            s_axi_awvalid <= 1'b1;
            s_axi_wvalid  <= 1'b1;
            s_axi_bready  <= 1'b0;

            while (!(aw_done && w_done)) begin
                @(posedge s_axi_aclk);
                if (s_axi_awvalid && s_axi_awready)
                    aw_done = 1'b1;
                if (s_axi_wvalid && s_axi_wready)
                    w_done = 1'b1;
                @(negedge s_axi_aclk);
                if (aw_done)
                    s_axi_awvalid <= 1'b0;
                if (w_done)
                    s_axi_wvalid <= 1'b0;
                timeout++;
                if (timeout > 128) begin
                    fail("AXI-Lite write independent AW/W handshake timeout");
                    s_axi_awvalid <= 1'b0;
                    s_axi_wvalid <= 1'b0;
                    break;
                end
            end

            @(negedge s_axi_aclk);
            s_axi_bready <= 1'b1;
            timeout = 0;
            while (!s_axi_bvalid) begin
                @(posedge s_axi_aclk);
                timeout++;
                if (timeout > 128) begin
                    fail("AXI-Lite write response timeout");
                    break;
                end
            end
            check(s_axi_bresp == 2'b00, "AXI-Lite BRESP should be OKAY");
            @(negedge s_axi_aclk);
            s_axi_bready <= 1'b0;
        end
    endtask

    task automatic axi_read32(input int reg_index, output logic [31:0] data);
        int timeout;
        bit ar_done;
        begin
            timeout = 0;
            ar_done = 1'b0;
            @(negedge s_axi_aclk);
            s_axi_araddr  <= reg_index[7:0] << 2;
            s_axi_arvalid <= 1'b1;
            s_axi_rready  <= 1'b0;

            while (!ar_done) begin
                @(posedge s_axi_aclk);
                if (s_axi_arvalid && s_axi_arready)
                    ar_done = 1'b1;
                @(negedge s_axi_aclk);
                if (ar_done)
                    s_axi_arvalid <= 1'b0;
                timeout++;
                if (timeout > 128) begin
                    fail("AXI-Lite read address timeout");
                    s_axi_arvalid <= 1'b0;
                    break;
                end
            end

            @(negedge s_axi_aclk);
            s_axi_rready <= 1'b1;
            timeout = 0;
            while (!s_axi_rvalid) begin
                @(posedge s_axi_aclk);
                timeout++;
                if (timeout > 128) begin
                    fail("AXI-Lite read response timeout");
                    break;
                end
            end
            data = s_axi_rdata;
            check(s_axi_rresp == 2'b00, "AXI-Lite RRESP should be OKAY");
            @(negedge s_axi_aclk);
            s_axi_rready <= 1'b0;
        end
    endtask

    task automatic read_status(output logic [31:0] status);
        begin
            axi_read32(REG_STATUS, status);
        end
    endtask

    task automatic wait_done();
        logic [31:0] status;
        int timeout;
        begin
            timeout = 0;
            status = '0;
            while (!status[STATUS_DONE]) begin
                axi_read32(REG_STATUS, status);
                wait_axi(2);
                timeout++;
                if (timeout > 500) begin
                    fail("timeout waiting for done status");
                    break;
                end
            end
        end
    endtask

    task automatic wait_not_busy();
        logic [31:0] status;
        int timeout;
        begin
            timeout = 0;
            status = '0;
            axi_read32(REG_STATUS, status);
            while (status[STATUS_BUSY]) begin
                wait_axi(2);
                axi_read32(REG_STATUS, status);
                timeout++;
                if (timeout > 500) begin
                    fail("timeout waiting for busy status to clear");
                    break;
                end
            end
        end
    endtask

    task automatic wait_armed();
        logic [31:0] status;
        int timeout;
        begin
            timeout = 0;
            status = '0;
            while (!status[STATUS_ARMED]) begin
                axi_read32(REG_STATUS, status);
                wait_axi(2);
                timeout++;
                if (timeout > 500) begin
                    fail("timeout waiting for armed status");
                    break;
                end
            end
        end
    endtask

    task automatic clear_done_and_errors();
        begin
            axi_write32(REG_CONTROL, 32'h0000_0004);
            wait_axi(8);
        end
    endtask

    task automatic soft_reset_capture();
        begin
            axi_write32(REG_CONTROL, 32'h0000_0002);
            wait_s_axis(8);
            wait_m_axi(8);
            wait_axi(8);
            wait_not_busy();
            clear_done_and_errors();
        end
    endtask

    task automatic arm_capture(
        input logic [31:0] waddr,
        input logic [31:0] nsamp,
        input logic [31:0] ntrig,
        input logic [31:0] stride
    );
        begin
            arm_capture_decim(waddr, nsamp, ntrig, stride, 32'd1);
        end
    endtask

    task automatic arm_capture_decim(
        input logic [31:0] waddr,
        input logic [31:0] nsamp,
        input logic [31:0] ntrig,
        input logic [31:0] stride,
        input logic [31:0] sample_decim
    );
        begin
            clear_scoreboard();
            wait_not_busy();
            clear_done_and_errors();
            axi_write32(REG_WADDR, waddr);
            axi_write32(REG_NSAMP, nsamp);
            axi_write32(REG_NTRIG, ntrig);
            axi_write32(REG_STRIDE, stride);
            axi_write32(REG_SAMPLE_DECIM, sample_decim);
            axi_write32(REG_TRIGGER_DELAY, 32'd0);
            axi_write32(REG_CONTROL, 32'h0000_0001);
            if ((nsamp != 0) && (ntrig != 0) && (waddr[4:0] == 5'd0) &&
                ((stride == 0) || (stride[4:0] == 5'd0))) begin
                wait_armed();
                // The previous done sticky can be re-sampled for a few AXI-Lite
                // cycles while the new arm crosses into the DDR clock domain.
                // Clear after the valid arm is visible so each test starts from
                // a clean status baseline before the trigger.
                clear_done_and_errors();
            end else begin
                wait_axi(20);
            end
            wait_s_axis(8);
            wait_m_axi(8);
        end
    endtask

    task automatic arm_capture_delay(
        input logic [31:0] waddr,
        input logic [31:0] nsamp,
        input logic [31:0] ntrig,
        input logic [31:0] stride,
        input logic [31:0] trigger_delay_cycles
    );
        begin
            clear_scoreboard();
            wait_not_busy();
            clear_done_and_errors();
            axi_write32(REG_WADDR, waddr);
            axi_write32(REG_NSAMP, nsamp);
            axi_write32(REG_NTRIG, ntrig);
            axi_write32(REG_STRIDE, stride);
            axi_write32(REG_SAMPLE_DECIM, 32'd1);
            axi_write32(REG_TRIGGER_DELAY, trigger_delay_cycles);
            axi_write32(REG_CONTROL, 32'h0000_0001);
            wait_armed();
            clear_done_and_errors();
            wait_s_axis(8);
            wait_m_axi(8);
        end
    endtask

    task automatic pulse_trigger();
        begin
            @(negedge s_axis_aclk);
            trigger <= 1'b1;
            wait_s_axis(5);
            @(negedge s_axis_aclk);
            trigger <= 1'b0;
            wait_s_axis(2);
        end
    endtask

    task automatic send_word_compliant(input logic [31:0] data);
        int timeout;
        begin
            timeout = 0;
            @(negedge s_axis_aclk);
            s_axis_tdata <= data;
            s_axis_tvalid <= 1'b1;
            do begin
                @(posedge s_axis_aclk);
                timeout++;
                if (timeout > 1024) begin
                    fail("compliant AXIS source timed out waiting for TREADY");
                    break;
                end
            end while (!s_axis_tready);
            @(negedge s_axis_aclk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata <= '0;
        end
    endtask

    task automatic send_words_compliant(input int base, input int count);
        int i;
        begin
            for (i = 0; i < count; i++)
                send_word_compliant(32'(base + i));
        end
    endtask

    task automatic hold_compliant_valid(input logic [31:0] data, input int cycles);
        begin
            @(negedge s_axis_aclk);
            s_axis_tdata <= data;
            s_axis_tvalid <= 1'b1;
            wait_s_axis(cycles);
            @(negedge s_axis_aclk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata <= '0;
        end
    endtask

    task automatic wait_completed_writes(input int expected);
        int timeout;
        begin
            timeout = 0;
            while (completed_count < expected) begin
                @(posedge m_axi_aclk);
                timeout++;
                if (timeout > 5000) begin
                    fail("timeout waiting for completed AXI writes");
                    break;
                end
            end
        end
    endtask

    function automatic logic [255:0] pack8(input int base);
        logic [255:0] result;
        int i;
        begin
            result = '0;
            for (i = 0; i < LANES; i++)
                result[i*32 +: 32] = 32'(base + i);
            return result;
        end
    endfunction

    function automatic logic [255:0] pack_partial_zero(input int base, input int n_valid);
        logic [255:0] result;
        int i;
        begin
            result = '0;
            for (i = 0; i < n_valid; i++)
                result[i*32 +: 32] = 32'(base + i);
            return result;
        end
    endfunction

    function automatic logic [255:0] pack_partial_decim(input int base, input int sample_decim, input int first_sample, input int n_valid);
        logic [255:0] result;
        int i;
        begin
            result = '0;
            for (i = 0; i < n_valid; i++)
                result[i*32 +: 32] = 32'(base + (first_sample + i) * sample_decim);
            return result;
        end
    endfunction

    task automatic expect_write(input int idx, input logic [31:0] addr, input logic [255:0] data);
        string msg;
        begin
            $sformat(msg, "write %0d exists", idx);
            check(completed_count > idx, msg);
            if (completed_count > idx) begin
                $sformat(msg, "write %0d address", idx);
                check(completed_addr[idx] == addr, msg);
                $sformat(msg, "write %0d data", idx);
                check(completed_data[idx] == data, msg);
                $sformat(msg, "write %0d strobe", idx);
                check(completed_strb[idx] == 32'hFFFF_FFFF, msg);
            end
        end
    endtask

    task automatic set_axi_write_stalls(input int aw_cycles, input int w_cycles, input int b_cycles);
        begin
            @(negedge m_axi_aclk);
            aw_stall_count <= aw_cycles;
            w_stall_count <= w_cycles;
            b_delay_cycles <= b_cycles;
        end
    endtask

    task automatic wait_response_delay_active();
        int timeout;
        begin
            timeout = 0;
            while (!(resp_pending && (resp_delay_count > 0))) begin
                @(posedge m_axi_aclk);
                timeout++;
                if (timeout > 1000) begin
                    fail("timeout waiting for delayed B response state");
                    break;
                end
            end
        end
    endtask

    task automatic run_capture(
        input logic [31:0] waddr,
        input int nsamp,
        input int ntrig,
        input logic [31:0] stride,
        input int sample_base
    );
        begin
            arm_capture(waddr, nsamp, ntrig, stride);
            pulse_trigger();
            send_words_compliant(sample_base, nsamp);
        end
    endtask

    task automatic check_single_event_data(
        input int first_write,
        input logic [31:0] event_base_addr,
        input int sample_base,
        input int nsamp
    );
        int words;
        int word_idx;
        int remaining;
        int n_valid;
        logic [255:0] expected;
        begin
            words = (nsamp + LANES - 1) / LANES;
            for (word_idx = 0; word_idx < words; word_idx++) begin
                remaining = nsamp - (word_idx * LANES);
                n_valid = (remaining >= LANES) ? LANES : remaining;
                expected = pack_partial_zero(sample_base + word_idx * LANES, n_valid);
                expect_write(first_write + word_idx,
                             event_base_addr + 32'(word_idx * AXI_WORD_BYTES),
                             expected);
            end
        end
    endtask

    task automatic check_single_event_decim_data(
        input int first_write,
        input logic [31:0] event_base_addr,
        input int sample_base,
        input int nsamp,
        input int sample_decim
    );
        int words;
        int word_idx;
        int remaining;
        int n_valid;
        logic [255:0] expected;
        begin
            words = (nsamp + LANES - 1) / LANES;
            for (word_idx = 0; word_idx < words; word_idx++) begin
                remaining = nsamp - (word_idx * LANES);
                n_valid = (remaining >= LANES) ? LANES : remaining;
                expected = pack_partial_decim(sample_base, sample_decim, word_idx * LANES, n_valid);
                expect_write(first_write + word_idx,
                             event_base_addr + 32'(word_idx * AXI_WORD_BYTES),
                             expected);
            end
        end
    endtask

    task automatic test_reset_default_state();
        logic [31:0] status;
        logic [31:0] trigger_delay;
        begin
            $display("TEST 0: reset/default state");
            reset_dut();
            axi_read32(REG_STATUS, status);
            axi_read32(REG_TRIGGER_DELAY, trigger_delay);
            check(status[STATUS_BUSY] == 1'b0, "reset status busy clear");
            check(status[STATUS_DONE] == 1'b0, "reset status done clear");
            check(status[STATUS_OVERFLOW] == 1'b0, "reset status overflow clear");
            check(status[STATUS_ARMED] == 1'b0, "reset status armed clear");
            check(
                trigger_delay == 32'd281970,
                "default trigger delay is 281970 source-clock cycles"
            );
            check(s_axis_tready == 1'b1, "idle/drop mode keeps s_axis_tready high");
            check(completed_count == 0, "no writes after reset");
        end
    endtask

    task automatic test_pre_arm_drop();
        begin
            $display("TEST 1: pre-arm drop");
            clear_scoreboard();
            send_words_compliant(32'h1000, 16);
            wait_m_axi(30);
            check(completed_count == 0, "pre-arm samples produce no AXI writes");
        end
    endtask

    task automatic test_single_trigger_full_word();
        begin
            $display("TEST 2: single trigger full word");
            run_capture(32'h0000_0000, 8, 1, 32'd0, 100);
            wait_completed_writes(1);
            wait_done();
            check(completed_count == 1, "full word produces one write");
            expect_write(0, 32'h0000_0000, pack8(100));
        end
    endtask

    task automatic test_single_trigger_partial_final_word();
        begin
            $display("TEST 3: single trigger partial final word");
            run_capture(32'h0000_0100, 10, 1, 32'd0, 200);
            wait_completed_writes(2);
            wait_done();
            check(completed_count == 2, "partial capture produces two writes");
            expect_write(0, 32'h0000_0100, pack8(200));
            expect_write(1, 32'h0000_0120, pack_partial_zero(208, 2));
        end
    endtask

    task automatic test_multi_trigger_explicit_stride();
        begin
            $display("TEST 4: multi-trigger explicit stride");
            arm_capture(32'h0000_0000, 10, 2, 32'd64);
            pulse_trigger();
            send_words_compliant(300, 10);
            wait_completed_writes(2);
            pulse_trigger();
            send_words_compliant(400, 10);
            wait_completed_writes(4);
            wait_done();
            check(completed_count == 4, "two events produce four writes");
            check_single_event_data(0, 32'h0000_0000, 300, 10);
            check_single_event_data(2, 32'h0000_0040, 400, 10);
        end
    endtask

    task automatic test_multi_trigger_auto_stride();
        begin
            $display("TEST 5: multi-trigger automatic stride");
            arm_capture(32'h0000_0200, 10, 3, 32'd0);
            pulse_trigger();
            send_words_compliant(500, 10);
            wait_completed_writes(2);
            pulse_trigger();
            send_words_compliant(600, 10);
            wait_completed_writes(4);
            pulse_trigger();
            send_words_compliant(700, 10);
            wait_completed_writes(6);
            wait_done();
            check(completed_count == 6, "three events produce six writes");
            check_single_event_data(0, 32'h0000_0200, 500, 10);
            check_single_event_data(2, 32'h0000_0240, 600, 10);
            check_single_event_data(4, 32'h0000_0280, 700, 10);
        end
    endtask

    task automatic test_trigger_ignored_after_done();
        int before_count;
        begin
            $display("TEST 6: trigger ignored while not armed");
            before_count = completed_count;
            pulse_trigger();
            send_words_compliant(800, 8);
            wait_m_axi(80);
            check(completed_count == before_count, "trigger after done produces no more writes");
        end
    endtask

    task automatic test_rearm_after_done();
        begin
            $display("TEST 7: re-arm after done");
            run_capture(32'h0000_0400, 1, 1, 32'd0, 900);
            wait_completed_writes(1);
            wait_done();
            check(completed_count == 1, "rearm nsamp=1 produces one write");
            expect_write(0, 32'h0000_0400, pack_partial_zero(900, 1));
        end
    endtask

    task automatic test_trigger_during_active_capture();
        logic [31:0] status;
        begin
            $display("TEST 8: trigger during active capture remains pending");
            arm_capture(32'h0000_0500, 20, 2, 32'd96);
            pulse_trigger();
            send_words_compliant(1000, 4);
            pulse_trigger();
            send_words_compliant(1004, 36);
            wait_completed_writes(6);
            wait_done();
            read_status(status);
            check(
                status[STATUS_OVERFLOW] == 1'b0,
                "trigger maturing during capture does not set overflow"
            );
            check(completed_count == 6, "two pending 20-sample events complete");
            check_single_event_data(0, 32'h0000_0500, 1000, 20);
            check_single_event_data(3, 32'h0000_0560, 1020, 20);
        end
    endtask

    task automatic test_awready_stall();
        begin
            $display("TEST 9: AWREADY stall");
            set_axi_write_stalls(6, 0, 0);
            run_capture(32'h0000_0600, 8, 1, 32'd0, 1100);
            wait_completed_writes(1);
            wait_done();
            expect_write(0, 32'h0000_0600, pack8(1100));
        end
    endtask

    task automatic test_wready_stall();
        begin
            $display("TEST 10: WREADY stall");
            set_axi_write_stalls(0, 6, 0);
            run_capture(32'h0000_0700, 8, 1, 32'd0, 1200);
            wait_completed_writes(1);
            wait_done();
            expect_write(0, 32'h0000_0700, pack8(1200));
        end
    endtask

    task automatic test_delayed_b_response();
        logic [31:0] status;
        begin
            $display("TEST 11: delayed B response");
            set_axi_write_stalls(0, 0, 120);
            arm_capture(32'h0000_0800, 8, 1, 32'd0);
            pulse_trigger();
            send_words_compliant(1300, 8);
            wait_response_delay_active();
            axi_read32(REG_STATUS, status);
            check(status[STATUS_DONE] == 1'b0, "done must not set before delayed B response");
            wait_completed_writes(1);
            wait_done();
            expect_write(0, 32'h0000_0800, pack8(1300));
        end
    endtask

    task automatic test_nsamp_one();
        begin
            $display("TEST 12: nsamp=1");
            run_capture(32'h0000_0900, 1, 1, 32'd0, 1400);
            wait_completed_writes(1);
            wait_done();
            expect_write(0, 32'h0000_0900, pack_partial_zero(1400, 1));
        end
    endtask

    task automatic test_nsamp_sixteen();
        begin
            $display("TEST 13: nsamp=16");
            run_capture(32'h0000_0A00, 16, 1, 32'd0, 1500);
            wait_completed_writes(2);
            wait_done();
            check(completed_count == 2, "nsamp=16 produces two full writes");
            expect_write(0, 32'h0000_0A00, pack8(1500));
            expect_write(1, 32'h0000_0A20, pack8(1508));
        end
    endtask

    task automatic test_invalid_configuration();
        logic [31:0] status;
        begin
            $display("TEST 14: invalid configuration");
            arm_capture(32'h0000_0B00, 0, 1, 32'd0);
            wait_done();
            read_status(status);
            check(status[STATUS_OVERFLOW] == 1'b1, "nsamp=0 reports overflow/error");
            check(completed_count == 0, "nsamp=0 produces no writes");

            arm_capture(32'h0000_0B00, 8, 0, 32'd0);
            wait_done();
            read_status(status);
            check(status[STATUS_OVERFLOW] == 1'b1, "ntrig=0 reports overflow/error");
            check(completed_count == 0, "ntrig=0 produces no writes");

            arm_capture(32'h0000_0B04, 8, 1, 32'd0);
            wait_done();
            read_status(status);
            check(status[STATUS_OVERFLOW] == 1'b1, "unaligned waddr reports overflow/error");
            check(completed_count == 0, "unaligned waddr produces no writes");

            arm_capture(32'h0000_0B00, 8, 1, 32'd36);
            wait_done();
            read_status(status);
            check(status[STATUS_OVERFLOW] == 1'b1, "unaligned stride reports overflow/error");
            check(completed_count == 0, "unaligned stride produces no writes");
        end
    endtask

    task automatic test_compliant_backpressure_overflow();
        logic [31:0] status;
        int timeout;
        begin
            $display("TEST 15: compliant source under DDR backpressure");
            set_axi_write_stalls(1000, 1000, 0);
            arm_capture(32'h0000_0C00, 64, 1, 32'd0);
            pulse_trigger();
            @(negedge s_axis_aclk);
            s_axis_tdata <= 32'hCAFE_0000;
            s_axis_tvalid <= 1'b1;
            wait_s_axis(180);
            read_status(status);
            check(status[STATUS_OVERFLOW] == 1'b1, "FIFO backpressure with stable TVALID reports overflow");
            @(negedge m_axi_aclk);
            aw_stall_count <= 0;
            w_stall_count <= 0;
            timeout = 0;
            while (!s_axis_tready) begin
                @(posedge s_axis_aclk);
                timeout++;
                if (timeout > 2000) begin
                    fail("timeout waiting for TREADY after releasing DDR backpressure");
                    break;
                end
            end
            @(posedge s_axis_aclk);
            @(negedge s_axis_aclk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata <= '0;
            soft_reset_capture();
        end
    endtask

    task automatic test_programmable_trigger_delay();
        logic [31:0] trigger_delay_rb;
        begin
            $display("TEST 19: programmable trigger delay register and pending request");
            arm_capture_delay(32'h0000_1000, 4, 1, 32'd0, 32'd3);
            axi_read32(REG_TRIGGER_DELAY, trigger_delay_rb);
            check(trigger_delay_rb == 32'd3, "trigger delay register readback");
            pulse_trigger();
            send_words_compliant(100, 7);
            wait_done();
            wait_completed_writes(1);
            expect_write(0, 32'h0000_1000, pack_partial_zero(100, 4));
        end
    endtask

    task automatic test_trigger_timestamp_queue();
        localparam int QUEUED_TRIGGERS = 8;
        localparam int DELAY_CYCLES = 300;
        int cycle_index;
        int trigger_index;
        logic [31:0] status;
        logic [31:0] trigger_count;
        begin
            $display("TEST 20: timestamp queue carries multiple long-delay triggers");
            check(
                dut.TRIGGER_QUEUE_DEPTH == QUEUED_TRIGGERS,
                "test instance has an eight-entry timestamp queue"
            );

            arm_capture_delay(
                32'h0000_2000,
                1,
                QUEUED_TRIGGERS,
                32'd32,
                DELAY_CYCLES
            );

            delay_accept_count = 0;
            delay_start_count = 0;
            delay_monitor_enable = 1'b1;

            // Keep TVALID high while eight trigger pulses enter four source
            // clocks apart. The 300-cycle delay exceeds the former 128-cycle
            // shift-line limit, and all eight due timestamps coexist.
            @(negedge s_axis_aclk);
            s_axis_tvalid <= 1'b1;
            s_axis_tdata <= 32'd5000;
            trigger <= 1'b0;
            for (cycle_index = 0; cycle_index < 380; cycle_index++) begin
                @(negedge s_axis_aclk);
                if (s_axis_tready)
                    s_axis_tdata <= s_axis_tdata + 1'b1;
                if ((cycle_index >= 2) &&
                    (cycle_index < (2 + 4 * QUEUED_TRIGGERS)))
                    trigger <= (((cycle_index - 2) % 4) < 2);
                else
                    trigger <= 1'b0;
            end
            s_axis_tvalid <= 1'b0;
            trigger <= 1'b0;
            delay_monitor_enable = 1'b0;

            wait_completed_writes(QUEUED_TRIGGERS);
            wait_done();

            read_status(status);
            axi_read32(REG_TRIGGER_COUNT, trigger_count);
            check(
                status[STATUS_OVERFLOW] == 1'b0,
                "timestamp-queued triggers complete without overflow"
            );
            check(
                trigger_count == QUEUED_TRIGGERS,
                "all timestamp-queued triggers complete"
            );
            check(
                delay_accept_count == QUEUED_TRIGGERS,
                "all trigger edges enter the timestamp queue"
            );
            check(
                delay_start_count == QUEUED_TRIGGERS,
                "all delayed trigger pulses start a capture"
            );
            for (trigger_index = 0;
                 trigger_index < QUEUED_TRIGGERS;
                 trigger_index++) begin
                check(
                    (delay_start_cycle[trigger_index] -
                     delay_accept_cycle[trigger_index]) == DELAY_CYCLES,
                    $sformatf(
                        "trigger %0d delay is exactly %0d source clocks",
                        trigger_index,
                        DELAY_CYCLES
                    )
                );
                expect_write(
                    trigger_index,
                    32'h0000_2000 + 32'(trigger_index * AXI_WORD_BYTES),
                    pack_partial_zero(delay_start_data[trigger_index], 1)
                );
            end
        end
    endtask

    task automatic test_timestamp_wraparound();
        localparam int DELAY_CYCLES = 12;
        int cycle_index;
        logic [31:0] status;
        begin
            $display("TEST 21: 32-bit due timestamp crosses wraparound");
            arm_capture_delay(
                32'h0000_2400,
                1,
                1,
                32'd0,
                DELAY_CYCLES
            );

            @(negedge s_axis_aclk);
            force dut.trigger_timestamp_s = 32'hFFFF_FFF8;
            release dut.trigger_timestamp_s;

            delay_accept_count = 0;
            delay_start_count = 0;
            delay_monitor_enable = 1'b1;
            s_axis_tvalid <= 1'b1;
            s_axis_tdata <= 32'd6000;
            trigger <= 1'b0;

            for (cycle_index = 0; cycle_index < 40; cycle_index++) begin
                @(negedge s_axis_aclk);
                if (s_axis_tready)
                    s_axis_tdata <= s_axis_tdata + 1'b1;
                trigger <= (cycle_index == 2) || (cycle_index == 3);
            end
            s_axis_tvalid <= 1'b0;
            trigger <= 1'b0;
            delay_monitor_enable = 1'b0;

            wait_completed_writes(1);
            wait_done();
            read_status(status);
            check(
                status[STATUS_OVERFLOW] == 1'b0,
                "timestamp wraparound completes without overflow"
            );
            check(delay_accept_count == 1, "wraparound trigger is accepted");
            check(delay_start_count == 1, "wraparound trigger starts capture");
            check(
                (delay_start_cycle[0] - delay_accept_cycle[0]) ==
                    DELAY_CYCLES,
                "wrapped due timestamp preserves the programmed delay"
            );
            check(
                dut.trigger_timestamp_s < 32'd128,
                "free-running timestamp crossed from 0xffffffff to zero"
            );
            expect_write(
                0,
                32'h0000_2400,
                pack_partial_zero(delay_start_data[0], 1)
            );
        end
    endtask

    task automatic test_timestamp_queue_overflow();
        localparam int REQUESTED_TRIGGERS = 9;
        localparam int DELAY_CYCLES = 100;
        int cycle_index;
        logic [31:0] status;
        begin
            $display("TEST 22: timestamp queue full sets sticky overflow");
            arm_capture_delay(
                32'h0000_2800,
                1,
                REQUESTED_TRIGGERS,
                32'd32,
                DELAY_CYCLES
            );

            @(negedge s_axis_aclk);
            trigger <= 1'b0;
            for (cycle_index = 0;
                 cycle_index < (4 * REQUESTED_TRIGGERS + 8);
                 cycle_index++) begin
                @(negedge s_axis_aclk);
                if ((cycle_index >= 2) &&
                    (cycle_index < (2 + 4 * REQUESTED_TRIGGERS)))
                    trigger <= (((cycle_index - 2) % 4) < 2);
                else
                    trigger <= 1'b0;
            end
            trigger <= 1'b0;
            wait_axi(12);
            read_status(status);
            check(
                status[STATUS_OVERFLOW] == 1'b1,
                "ninth outstanding trigger sets queue overflow"
            );
            check(
                dut.accepted_trigger_count_s == dut.TRIGGER_QUEUE_DEPTH,
                "full queue accepts exactly its configured depth"
            );
            check(
                dut.trigger_queue_count_s == dut.TRIGGER_QUEUE_DEPTH,
                "all accepted future timestamps remain queued"
            );
            soft_reset_capture();
        end
    endtask

    task automatic test_sample_decimation_single_trigger();
        logic [31:0] decim_rb;
        begin
            $display("TEST 16: sample decimation single trigger");
            arm_capture_decim(32'h0000_0D00, 8, 1, 32'd0, 32'd4);
            axi_read32(REG_SAMPLE_DECIM, decim_rb);
            check(decim_rb == 32'd4, "sample decimation register readback");
            pulse_trigger();
            send_words_compliant(2000, 29);
            wait_completed_writes(1);
            wait_done();
            check(completed_count == 1, "decim=4 nsamp=8 produces one write");
            check_single_event_decim_data(0, 32'h0000_0D00, 2000, 8, 4);
        end
    endtask

    task automatic test_sample_decimation_trigger_alignment();
        begin
            $display("TEST 17: sample decimation trigger alignment");
            arm_capture_decim(32'h0000_0E00, 4, 2, 32'd32, 32'd3);
            pulse_trigger();
            send_words_compliant(3000, 10);
            wait_completed_writes(1);
            pulse_trigger();
            send_words_compliant(4000, 10);
            wait_completed_writes(2);
            wait_done();
            check(completed_count == 2, "two decimated trigger events produce two writes");
            check_single_event_decim_data(0, 32'h0000_0E00, 3000, 4, 3);
            check_single_event_decim_data(1, 32'h0000_0E20, 4000, 4, 3);
        end
    endtask

    task automatic test_sample_decimation_zero_is_one();
        begin
            $display("TEST 18: sample decimation zero means one");
            arm_capture_decim(32'h0000_0F00, 8, 1, 32'd0, 32'd0);
            pulse_trigger();
            send_words_compliant(5000, 8);
            wait_completed_writes(1);
            wait_done();
            check(completed_count == 1, "decim=0 behaves as decim=1");
            expect_write(0, 32'h0000_0F00, pack8(5000));
        end
    endtask

    function automatic int next_index(input int value);
        begin
            next_index = (value + 1) % MAX_PENDING;
        end
    endfunction

    task automatic push_aw(input logic [31:0] addr);
        begin
            check(aw_count < MAX_PENDING, "AW pending queue overflow");
            aw_addr_q[aw_tail] = addr;
            aw_tail = next_index(aw_tail);
            aw_count++;
        end
    endtask

    task automatic push_w(input logic [255:0] data, input logic [31:0] strb);
        begin
            check(w_count < MAX_PENDING, "W pending queue overflow");
            w_data_q[w_tail] = data;
            w_strb_q[w_tail] = strb;
            w_tail = next_index(w_tail);
            w_count++;
        end
    endtask

    task automatic pop_complete_pair();
        begin
            check((aw_count > 0) && (w_count > 0), "internal AXI model pair pop requires AW and W");
            resp_addr = aw_addr_q[aw_head];
            resp_data = w_data_q[w_head];
            resp_strb = w_strb_q[w_head];
            aw_head = next_index(aw_head);
            w_head = next_index(w_head);
            aw_count--;
            w_count--;
            resp_pending = 1'b1;
            resp_delay_count = b_delay_cycles;
        end
    endtask

    task automatic complete_response();
        begin
            check(completed_count < MAX_WRITES, "completed write scoreboard overflow");
            completed_addr[completed_count] = resp_addr;
            completed_data[completed_count] = resp_data;
            completed_strb[completed_count] = resp_strb;
            completed_count++;
            resp_pending = 1'b0;
        end
    endtask

    always_ff @(posedge m_axi_aclk) begin
        if (!m_axi_aresetn) begin
            m_axi_awready <= 1'b0;
            m_axi_wready <= 1'b0;
            m_axi_bvalid <= 1'b0;
            m_axi_bresp <= 2'b00;
            m_axi_bid <= '0;
            aw_prev_backpressured <= 1'b0;
            w_prev_backpressured <= 1'b0;
        end else begin
            if (m_axi_awvalid) begin
                check(!$isunknown(m_axi_awaddr), "AWADDR has X/Z when AWVALID");
                check(!$isunknown(m_axi_awlen), "AWLEN has X/Z when AWVALID");
                check(!$isunknown(m_axi_awsize), "AWSIZE has X/Z when AWVALID");
                check(!$isunknown(m_axi_awburst), "AWBURST has X/Z when AWVALID");
                check(m_axi_awlen == 8'd0, "AWLEN must be zero for single-beat writes");
                check(m_axi_awsize == 3'b101, "AWSIZE must be 32 bytes");
                check(m_axi_awburst == 2'b01, "AWBURST must be INCR");
                check(m_axi_awlock == 1'b0, "AWLOCK must be zero");
            end

            if (m_axi_wvalid) begin
                check(!$isunknown(m_axi_wdata), "WDATA has X/Z when WVALID");
                check(!$isunknown(m_axi_wstrb), "WSTRB has X/Z when WVALID");
                check(!$isunknown(m_axi_wlast), "WLAST has X/Z when WVALID");
                check(m_axi_wlast == 1'b1, "WLAST must be asserted for every write");
                check(m_axi_wstrb == 32'hFFFF_FFFF, "WSTRB must be all ones");
            end

            if (aw_prev_backpressured) begin
                check(m_axi_awvalid == 1'b1, "AWVALID dropped while AWREADY was low");
                check(m_axi_awaddr == aw_prev_addr, "AWADDR changed while AWREADY was low");
                check(m_axi_awlen == aw_prev_len, "AWLEN changed while AWREADY was low");
                check(m_axi_awsize == aw_prev_size, "AWSIZE changed while AWREADY was low");
                check(m_axi_awburst == aw_prev_burst, "AWBURST changed while AWREADY was low");
            end

            if (w_prev_backpressured) begin
                check(m_axi_wvalid == 1'b1, "WVALID dropped while WREADY was low");
                check(m_axi_wdata == w_prev_data, "WDATA changed while WREADY was low");
                check(m_axi_wstrb == w_prev_strb, "WSTRB changed while WREADY was low");
                check(m_axi_wlast == w_prev_last, "WLAST changed while WREADY was low");
            end

            if (m_axi_awvalid && m_axi_awready)
                push_aw(m_axi_awaddr);
            if (m_axi_wvalid && m_axi_wready)
                push_w(m_axi_wdata, m_axi_wstrb);

            if (m_axi_bvalid && m_axi_bready) begin
                complete_response();
                m_axi_bvalid <= 1'b0;
            end

            if (!m_axi_bvalid && !resp_pending && (aw_count > 0) && (w_count > 0))
                pop_complete_pair();

            if (resp_pending && !m_axi_bvalid) begin
                if (resp_delay_count > 0) begin
                    resp_delay_count = resp_delay_count - 1;
                end else begin
                    m_axi_bvalid <= 1'b1;
                    m_axi_bresp <= 2'b00;
                    m_axi_bid <= '0;
                end
            end

            if (aw_stall_count > 0) begin
                m_axi_awready <= 1'b0;
                if (m_axi_awvalid)
                    aw_stall_count <= aw_stall_count - 1;
            end else begin
                m_axi_awready <= (aw_count < MAX_PENDING-1);
            end

            if (w_stall_count > 0) begin
                m_axi_wready <= 1'b0;
                if (m_axi_wvalid)
                    w_stall_count <= w_stall_count - 1;
            end else begin
                m_axi_wready <= (w_count < MAX_PENDING-1);
            end

            aw_prev_backpressured <= m_axi_awvalid && !m_axi_awready;
            aw_prev_addr <= m_axi_awaddr;
            aw_prev_len <= m_axi_awlen;
            aw_prev_size <= m_axi_awsize;
            aw_prev_burst <= m_axi_awburst;

            w_prev_backpressured <= m_axi_wvalid && !m_axi_wready;
            w_prev_data <= m_axi_wdata;
            w_prev_strb <= m_axi_wstrb;
            w_prev_last <= m_axi_wlast;
        end
    end

    always_ff @(posedge s_axis_aclk) begin
        if (!s_axis_aresetn) begin
            s_prev_backpressured <= 1'b0;
            s_prev_data <= '0;
        end else begin
            if (s_axis_tvalid) begin
                check(!$isunknown(s_axis_tdata), "S_AXIS_TDATA has X/Z when TVALID");
                check(!$isunknown(s_axis_tvalid), "S_AXIS_TVALID has X/Z");
            end

            if (s_prev_backpressured) begin
                check(s_axis_tvalid == 1'b1, "compliant source dropped TVALID while TREADY was low");
                check(s_axis_tdata == s_prev_data, "compliant source changed TDATA while TREADY was low");
            end

            s_prev_backpressured <= s_axis_tvalid && !s_axis_tready;
            s_prev_data <= s_axis_tdata;
        end
    end

    initial if (RUN_REGRESSION) begin
        test_reset_default_state();
        test_pre_arm_drop();
        test_single_trigger_full_word();
        test_single_trigger_partial_final_word();
        test_multi_trigger_explicit_stride();
        test_multi_trigger_auto_stride();
        test_trigger_ignored_after_done();
        test_rearm_after_done();
        test_trigger_during_active_capture();
        test_awready_stall();
        test_wready_stall();
        test_delayed_b_response();
        test_nsamp_one();
        test_nsamp_sixteen();
        test_invalid_configuration();
        test_compliant_backpressure_overflow();
        test_sample_decimation_single_trigger();
        test_sample_decimation_trigger_alignment();
        test_sample_decimation_zero_is_one();
        test_programmable_trigger_delay();
        test_trigger_timestamp_queue();
        test_timestamp_wraparound();
        test_timestamp_queue_overflow();

        wait_axi(20);
        if (errors == 0) begin
            $display("PASS: axis_buffer_ddr_sample_v2");
        end else begin
            $fatal(1, "FAIL: axis_buffer_ddr_sample_v2 had %0d errors", errors);
        end
        $finish;
    end

endmodule

`default_nettype wire
