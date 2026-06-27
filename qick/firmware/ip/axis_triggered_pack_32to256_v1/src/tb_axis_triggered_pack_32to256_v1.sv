`timescale 1ns/1ps

module tb_axis_triggered_pack_32to256_v1;

    logic         aclk = 1'b0;
    logic         aresetn = 1'b0;
    logic         trigger = 1'b0;

    wire          s_axis_tready;
    logic         s_axis_tvalid = 1'b0;
    logic [31:0]  s_axis_tdata = '0;

    logic         m_axis_tready = 1'b1;
    wire          m_axis_tvalid;
    wire [255:0]  m_axis_tdata;
    wire [31:0]   m_axis_tstrb;
    wire          m_axis_tlast;

    int errors = 0;

    axis_triggered_pack_32to256_v1 dut (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .trigger       (trigger),
        .s_axis_tready (s_axis_tready),
        .s_axis_tvalid (s_axis_tvalid),
        .s_axis_tdata  (s_axis_tdata),
        .m_axis_tready (m_axis_tready),
        .m_axis_tvalid (m_axis_tvalid),
        .m_axis_tdata  (m_axis_tdata),
        .m_axis_tstrb  (m_axis_tstrb),
        .m_axis_tlast  (m_axis_tlast)
    );

    always #5 aclk = ~aclk;

    task automatic fail(input string msg);
        begin
            $display("FAIL: %s at time %0t", msg, $time);
            errors++;
        end
    endtask

    task automatic check(input bit cond, input string msg);
        begin
            if (!cond) fail(msg);
        end
    endtask

    task automatic wait_cycles(input int cycles);
        begin
            repeat (cycles) @(posedge aclk);
        end
    endtask

    task automatic send_word(input logic [31:0] data);
        int timeout;
        begin
            timeout = 0;
            @(negedge aclk);
            s_axis_tdata  <= data;
            s_axis_tvalid <= 1'b1;
            @(posedge aclk);
            while (!s_axis_tready) begin
                @(posedge aclk);
                timeout++;
                if (timeout > 32) fail("timeout waiting for s_axis_tready");
            end
            @(negedge aclk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata  <= '0;
        end
    endtask

    task automatic send_words(input int base, input int count);
        int i;
        begin
            for (i = 0; i < count; i++) begin
                send_word(32'(base + i));
            end
        end
    endtask

    function automatic logic [255:0] pack8(input int base);
        logic [255:0] result;
        int i;
        begin
            result = '0;
            for (i = 0; i < 8; i++) begin
                result[i*32 +: 32] = base + i;
            end
            return result;
        end
    endfunction

    task automatic wait_output(input logic [255:0] expected, input string tag);
        int timeout;
        begin
            timeout = 0;
            while (!m_axis_tvalid) begin
                @(posedge aclk);
                timeout++;
                if (timeout > 64) fail({tag, ": timeout waiting for output"});
            end
            check(m_axis_tdata === expected, {tag, ": packed data mismatch"});
            check(m_axis_tstrb === 32'hFFFF_FFFF, {tag, ": tstrb mismatch"});
            check(m_axis_tlast === 1'b0, {tag, ": tlast should be zero"});
            @(posedge aclk);
        end
    endtask

    initial begin
        aresetn = 1'b0;
        trigger = 1'b0;
        s_axis_tvalid = 1'b0;
        m_axis_tready = 1'b1;
        wait_cycles(5);
        aresetn = 1'b1;
        wait_cycles(5);

        // Data before trigger is accepted and dropped.
        send_words(100, 12);
        wait_cycles(4);
        check(m_axis_tvalid === 1'b0, "no output should be produced before trigger");

        // Trigger rising edge starts a fresh pack sequence.
        trigger <= 1'b1;
        wait_cycles(4);
        send_words(0, 8);
        wait_output(pack8(0), "first trigger full pack");

        // Hold output stable while downstream is not ready.
        m_axis_tready <= 1'b0;
        send_words(20, 8);
        wait_cycles(2);
        check(m_axis_tvalid === 1'b1, "output valid should stay high while stalled");
        check(m_axis_tdata === pack8(20), "output data should stay stable while stalled");
        wait_cycles(4);
        check(m_axis_tvalid === 1'b1, "output valid should remain high while stalled");
        check(m_axis_tdata === pack8(20), "output data should remain stable while stalled");
        m_axis_tready <= 1'b1;
        wait_cycles(2);

        // Falling trigger is not a capture stop condition. The partial pack
        // remains aligned and is completed by later input data.
        send_words(40, 3);
        trigger <= 1'b0;
        wait_cycles(4);
        check(m_axis_tvalid === 1'b0, "partial pack should not emit before it has 8 samples");
        send_words(43, 5);
        wait_output(pack8(40), "partial pack survives trigger fall");

        // A second trigger realigns the next pack sequence.
        send_words(200, 4);
        trigger <= 1'b1;
        wait_cycles(4);
        send_words(80, 8);
        wait_output(pack8(80), "second trigger full pack");

        if (errors == 0) begin
            $display("PASS: axis_triggered_pack_32to256_v1");
        end else begin
            $fatal(1, "FAIL: axis_triggered_pack_32to256_v1 had %0d errors", errors);
        end
        $finish;
    end

endmodule
