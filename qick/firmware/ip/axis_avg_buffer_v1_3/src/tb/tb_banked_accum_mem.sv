`timescale 1ns/1ps

// Self-checking unit test for ramb36e2_accum_mem.
//
// Uses N=12 so NUM_BANKS = 4. For B=16, each bank has four 36-bit RAMB36E2
// width slices and stores one 128-bit word per local address:
//   {Q_accum[63:0], I_accum[63:0]}.
//
// The bank update path has a four-cycle read/DSP/writeback latency after the
// bank input command reaches the selected bank. Same-address updates are
// intentionally spaced here because the RTL flags back-to-back same-address
// hazards in simulation.

module tb_banked_accum_mem;

    localparam int N = 12;
    localparam int B = 16;
    localparam int ACC_CH_WIDTH = 4 * B;
    localparam int ACC_WORD_WIDTH = 8 * B;
    localparam int NUM_ADDRS = 9;

    localparam logic [1:0] OP_CLEAR  = 2'd0;
    localparam logic [1:0] OP_UPDATE = 2'd1;
    localparam logic [1:0] OP_READ   = 2'd2;

    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic rstn;
    logic valid;
    logic [1:0] op;
    logic [N-1:0] addr;
    logic [ACC_WORD_WIDTH-1:0] delta;
    wire read_valid;
    wire [N-1:0] read_addr;
    wire [ACC_WORD_WIDTH-1:0] read_data;

    int unsigned test_addrs [0:NUM_ADDRS-1] = '{
        0, 1, 1023, 1024, 1025, 2047, 2048, 3071, 4095
    };
    longint signed exp_i [0:NUM_ADDRS-1];
    longint signed exp_q [0:NUM_ADDRS-1];

    ramb36e2_accum_mem #(
        .N (N),
        .B (B)
    ) dut (
        .clk          (clk),
        .rstn         (rstn),
        .valid_i      (valid),
        .op_i         (op),
        .addr_i       (addr),
        .delta_i      (delta),
        .read_valid_o (read_valid),
        .read_addr_o  (read_addr),
        .read_data_o  (read_data)
    );

    function automatic logic [ACC_WORD_WIDTH-1:0] pack_iq64(
        input longint signed i,
        input longint signed q
    );
        pack_iq64 = {q[63:0], i[63:0]};
    endfunction

    task automatic reset_dut;
        begin
            rstn  = 1'b0;
            valid = 1'b0;
            op    = OP_CLEAR;
            addr  = '0;
            delta = '0;
            repeat (8) @(posedge clk);
            rstn = 1'b1;
            repeat (4) @(posedge clk);
        end
    endtask

    task automatic issue_cmd(
        input logic [1:0] cmd_op,
        input int unsigned cmd_addr,
        input logic [ACC_WORD_WIDTH-1:0] cmd_delta
    );
        begin
            @(negedge clk);
            valid <= 1'b1;
            op    <= cmd_op;
            addr  <= cmd_addr[N-1:0];
            delta <= cmd_delta;
            @(negedge clk);
            valid <= 1'b0;
            op    <= OP_CLEAR;
            addr  <= '0;
            delta <= '0;
        end
    endtask

    task automatic clear_addr(input int unsigned a);
        begin
            issue_cmd(OP_CLEAR, a, '0);
        end
    endtask

    task automatic update_addr(
        input int unsigned a,
        input longint signed i_delta,
        input longint signed q_delta
    );
        begin
            issue_cmd(OP_UPDATE, a, pack_iq64(i_delta, q_delta));
        end
    endtask

    task automatic update_addr_and_wait(
        input int unsigned a,
        input longint signed i_delta,
        input longint signed q_delta
    );
        begin
            update_addr(a, i_delta, q_delta);
            repeat (8) @(posedge clk);
        end
    endtask

    task automatic read_and_check(
        input int unsigned a,
        input longint signed exp_i_val,
        input longint signed exp_q_val,
        input string tag
    );
        int guard;
        longint signed act_i;
        longint signed act_q;
        begin
            issue_cmd(OP_READ, a, '0);
            guard = 0;
            do begin
                @(posedge clk);
                #1;
                guard++;
                if (guard > 80)
                    $fatal(1, "%s: timeout waiting for read addr %0d", tag, a);
            end while (!read_valid);

            act_i = $signed(read_data[ACC_CH_WIDTH-1:0]);
            act_q = $signed(read_data[ACC_WORD_WIDTH-1:ACC_CH_WIDTH]);

            if (read_addr != a[N-1:0])
                $fatal(1, "%s: read address mismatch expected %0d got %0d", tag, a, read_addr);
            if (act_i != exp_i_val || act_q != exp_q_val) begin
                $fatal(1,
                    "%s: addr=%0d expected I=%0d Q=%0d got I=%0d Q=%0d word=%h",
                    tag, a, exp_i_val, exp_q_val, act_i, act_q, read_data);
            end
        end
    endtask

    initial begin
        reset_dut();

        for (int idx = 0; idx < NUM_ADDRS; idx++) begin
            exp_i[idx] = 0;
            exp_q[idx] = 0;
            clear_addr(test_addrs[idx]);
        end
        repeat (16) @(posedge clk);

        for (int idx = 0; idx < NUM_ADDRS; idx++)
            read_and_check(test_addrs[idx], 0, 0, "clear-check");

        for (int idx = 0; idx < NUM_ADDRS; idx++) begin
            longint signed di;
            longint signed dq;
            di = 64'sd1000 + longint'(test_addrs[idx]);
            dq = -64'sd2000 - longint'(test_addrs[idx]);
            if (test_addrs[idx] == 2048) begin
                di = 64'sd5_000_000_000;
                dq = -64'sd5_000_000_123;
            end
            exp_i[idx] += di;
            exp_q[idx] += dq;
            update_addr(test_addrs[idx], di, dq);
        end
        repeat (16) @(posedge clk);

        for (int idx = 0; idx < NUM_ADDRS; idx++)
            read_and_check(test_addrs[idx], exp_i[idx], exp_q[idx], "first-update");

        update_addr(1024, 64'sd77, -64'sd88);
        exp_i[3] += 64'sd77;
        exp_q[3] += -64'sd88;
        update_addr(2048, -64'sd12, 64'sd34);
        exp_i[6] += -64'sd12;
        exp_q[6] += 64'sd34;
        repeat (16) @(posedge clk);

        read_and_check(1024, exp_i[3], exp_q[3], "second-update-bank1");
        read_and_check(2048, exp_i[6], exp_q[6], "second-update-bank2");
        read_and_check(4095, exp_i[8], exp_q[8], "bank3-retained");

        clear_addr(77);
        repeat (8) @(posedge clk);
        update_addr_and_wait(77, 64'sd123, -64'sd456);
        read_and_check(77, 64'sd123, -64'sd456, "single-update-read");

        clear_addr(78);
        repeat (8) @(posedge clk);
        update_addr_and_wait(78, -64'sd5, 64'sd7);
        update_addr_and_wait(78, 64'sd2, -64'sd11);
        update_addr_and_wait(78, 64'sd9, 64'sd4);
        read_and_check(78, 64'sd6, 64'sd0, "spaced-same-address-signed");

        clear_addr(79);
        repeat (8) @(posedge clk);
        update_addr_and_wait(
            79,
            64'sh0000_0000_ffff_ffff,
            64'sh0000_0001_ffff_ffff
        );
        update_addr_and_wait(
            79,
            64'sh0000_0000_0000_0001,
            64'sh0000_0002_0000_0001
        );
        read_and_check(
            79,
            64'sh0000_0001_0000_0000,
            64'sh0000_0004_0000_0000,
            "lower-carry-and-high-carry"
        );

        clear_addr(80);
        repeat (8) @(posedge clk);
        update_addr_and_wait(80, 64'shffff_ffff_ffff_ffff, -64'sd3);
        update_addr_and_wait(80, 64'sh0000_0000_0000_0001, 64'sd8);
        read_and_check(80, 64'sd0, 64'sd5, "negative-wraparound");

        $display("PASS: tb_banked_accum_mem verified 4-bank 128-bit accumulated storage");
        $finish;
    end

endmodule
