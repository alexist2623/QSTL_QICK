// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

module tb_axis_notch_decim_1m_to50k_v1;

    localparam int INPUT_COUNT = 2400;
    localparam int OUTPUT_COUNT = 120;
    localparam real CLK_HALF_NS = 1.6666667;

    logic aclk = 1'b0;
    logic aresetn = 1'b0;
    logic [31:0] s_axis_tdata = '0;
    logic s_axis_tvalid = 1'b0;
    wire s_axis_tready;
    logic s_axis_tlast = 1'b0;
    wire [31:0] m_axis_tdata;
    wire m_axis_tvalid;
    logic m_axis_tready = 1'b1;
    wire m_axis_tlast;

    logic [31:0] input_words [0:INPUT_COUNT-1];
    logic [31:0] expected_words [0:OUTPUT_COUNT-1];
    int output_index = 0;
    int errors = 0;

    axis_notch_decim_1m_to50k_v1 dut (
        .aclk(aclk),
        .aresetn(aresetn),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready),
        .s_axis_tlast(s_axis_tlast),
        .m_axis_tdata(m_axis_tdata),
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tready(m_axis_tready),
        .m_axis_tlast(m_axis_tlast)
    );

    always #(CLK_HALF_NS) aclk = ~aclk;

    always @(negedge aclk) begin
        if (aresetn && m_axis_tvalid) begin
            if (output_index >= OUTPUT_COUNT) begin
                $error("unexpected extra output %08x", m_axis_tdata);
                errors++;
            end else if (m_axis_tdata !== expected_words[output_index]) begin
                $error("output %0d mismatch: actual=%08x expected=%08x",
                       output_index, m_axis_tdata, expected_words[output_index]);
                errors++;
            end
            output_index++;
        end
    end

    task automatic drive_word(input logic [31:0] word);
        begin
            while (!s_axis_tready)
                @(negedge aclk);
            s_axis_tdata  <= word;
            s_axis_tvalid <= 1'b1;
            @(negedge aclk);
            s_axis_tvalid <= 1'b0;
            s_axis_tdata  <= '0;
            // Preserve the real 1 MSPS spacing at the 300 MHz fabric clock.
            // The deeply pipelined 40-section engine completes within this
            // 300-cycle interval for every accepted 50 kSPS sample.
            repeat (300) @(negedge aclk);
        end
    endtask

    initial begin
        $readmemh("input.hex", input_words);
        $readmemh("expected.hex", expected_words);

        repeat (10) @(negedge aclk);
        aresetn <= 1'b1;
        repeat (5) @(negedge aclk);

        fork
            begin
                for (int index = 0; index < INPUT_COUNT; index++)
                    drive_word(input_words[index]);
            end
            begin
                // The output path intentionally has no backpressure. Toggling
                // ready must not change any result or decimation phase.
                forever begin
                    repeat (37) @(negedge aclk);
                    m_axis_tready <= ~m_axis_tready;
                end
            end
        join_none

        wait (output_index == OUTPUT_COUNT);
        repeat (100) @(negedge aclk);
        if (m_axis_tlast !== 1'b0) begin
            $error("m_axis_tlast must remain low");
            errors++;
        end

        if (errors == 0)
            $display("PASS: continuous 1 MSPS to 50 kSPS filtering matched %0d bit-accurate outputs", OUTPUT_COUNT);
        else
            $fatal(1, "FAIL: %0d mismatches", errors);
        $finish;
    end

    initial begin
        #100000000;
        $fatal(1, "FAIL: simulation timeout");
    end

endmodule
