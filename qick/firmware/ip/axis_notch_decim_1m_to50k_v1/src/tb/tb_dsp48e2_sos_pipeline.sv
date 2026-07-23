// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
`timescale 1ns/1ps

module tb_dsp48e2_sos_pipeline;

    localparam real CLK_HALF_NS = 1.6666667;

    logic clk = 1'b0;
    logic rstn = 1'b0;

    logic mul_valid_i = 1'b0;
    logic signed [31:0] mul_a_i = '0;
    logic signed [31:0] mul_b_i = '0;
    wire mul_valid_o;
    wire signed [67:0] mul_product_o;

    logic add_valid_i = 1'b0;
    logic [67:0] add_a_i = '0;
    logic [67:0] add_b_i = '0;
    logic add_carry_i = 1'b0;
    wire add_valid_o;
    wire [67:0] add_sum_o;

    int errors = 0;

    always #(CLK_HALF_NS) clk = ~clk;

    dsp48e2_mul32x32_pipe mul_dut (
        .clk(clk),
        .rstn(rstn),
        .valid_i(mul_valid_i),
        .a_i(mul_a_i),
        .b_i(mul_b_i),
        .valid_o(mul_valid_o),
        .product_o(mul_product_o)
    );

    dsp48e2_add68_chunked_pipe add_dut (
        .clk(clk),
        .rstn(rstn),
        .valid_i(add_valid_i),
        .a_i(add_a_i),
        .b_i(add_b_i),
        .carry_i(add_carry_i),
        .valid_o(add_valid_o),
        .sum_o(add_sum_o)
    );

    task automatic check_mul(
        input logic signed [31:0] a,
        input logic signed [31:0] b,
        input string tag
    );
        logic signed [63:0] expected_64;
        logic signed [67:0] expected_68;
        int timeout;
        begin
            expected_64 = a * b;
            expected_68 = {{4{expected_64[63]}}, expected_64};
            @(negedge clk);
            mul_a_i <= a;
            mul_b_i <= b;
            mul_valid_i <= 1'b1;
            @(negedge clk);
            mul_valid_i <= 1'b0;

            timeout = 0;
            while (!mul_valid_o && timeout < 30) begin
                @(negedge clk);
                timeout++;
            end
            if (!mul_valid_o) begin
                $error("multiply timeout: %s", tag);
                errors++;
            end else if (mul_product_o !== expected_68) begin
                $error("multiply mismatch %s: %0d * %0d = %0d, expected %0d",
                       tag, a, b, mul_product_o, expected_68);
                errors++;
            end
            @(negedge clk);
        end
    endtask

    task automatic check_add(
        input logic [67:0] a,
        input logic [67:0] b,
        input logic carry,
        input string tag
    );
        logic [68:0] expected_wide;
        logic [67:0] expected;
        int timeout;
        begin
            expected_wide = {1'b0, a} + {1'b0, b} + carry;
            expected = expected_wide[67:0];
            @(negedge clk);
            add_a_i <= a;
            add_b_i <= b;
            add_carry_i <= carry;
            add_valid_i <= 1'b1;
            @(negedge clk);
            add_valid_i <= 1'b0;

            timeout = 0;
            while (!add_valid_o && timeout < 12) begin
                @(negedge clk);
                timeout++;
            end
            if (!add_valid_o) begin
                $error("add timeout: %s", tag);
                errors++;
            end else if (add_sum_o !== expected) begin
                $error("add mismatch %s: actual=%h expected=%h", tag, add_sum_o, expected);
                errors++;
            end
            @(negedge clk);
        end
    endtask

    initial begin
        repeat (8) @(negedge clk);
        rstn <= 1'b1;
        // The UNISIM glbl model holds GSR for 100 ns independently of rstn.
        // Start vectors only after both resets have been released.
        repeat (40) @(negedge clk);

        check_mul(32'sd0, 32'sd0, "zero");
        check_mul(32'sd1, -32'sd1, "one-negative-one");
        check_mul(32'sh7fff_ffff, 32'sh7fff_ffff, "positive-full-scale");
        check_mul(32'sh8000_0000, 32'sd1, "negative-full-scale");
        check_mul(32'sh8000_0000, 32'sh8000_0000, "negative-full-scale-squared");
        check_mul(32'sd65537, -32'sd1073741823, "cross-partial-sign");
        check_mul(-32'sd123456789, 32'sd987654321, "mixed-sign");

        check_add(68'd0, 68'd0, 1'b0, "zero");
        check_add({68{1'b1}}, 68'd0, 1'b1, "modulo-overflow");
        check_add((68'd1 << 47) - 1, 68'd1, 1'b0, "low-to-high-carry");
        check_add((68'd1 << 67) - 1, (68'd1 << 47) + 7, 1'b0, "wide-positive");
        check_add(68'h0_1234_5678_9abc_def0, ~68'h0_0000_0000_0001_2345,
                  1'b1, "twos-complement-subtract");

        if (errors == 0)
            $display("PASS: explicit DSP48E2 multiply and chunked 68-bit add/sub matched all directed vectors");
        else
            $fatal(1, "FAIL: %0d DSP pipeline mismatches", errors);
        $finish;
    end

    initial begin
        #100000;
        $fatal(1, "FAIL: DSP pipeline simulation timeout");
    end

endmodule
