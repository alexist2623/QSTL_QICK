`timescale 1ns/1ps
module tb_axis_fir_decim_300to1_v2;
    logic clk=0, resetn=0, valid=0;
    logic [31:0] data=0;
    wire ready, out_valid;
    wire [127:0] out_data;
    always #(5.0/3.0) clk=~clk;
    axis_fir_decim_300to1_v2 dut(
        .aclk(clk),.aresetn(resetn),.trigger(1'b0),.capture_trigger(),
        .s_axis_tdata(data),.s_axis_tvalid(valid),.s_axis_tready(ready),.s_axis_tlast(1'b0),
        .m_axis_tdata(out_data),.m_axis_tvalid(out_valid),.m_axis_tready(1'b1),.m_axis_tlast());
    logic [31:0] input_words[0:399999];
    logic [67:0] expected0[0:39999];
    logic [101:0] expected1[0:3999];
    logic [137:0] expected2[0:1332];
    logic [127:0] expected_out[0:1332];
    int n, n0, n1, n2, count0=0, count1=0, count2=0, count_out=0;
    int cycle=0, input_count=0, source_cycle[0:1332];
    string vector_dir, vector_path;
    int fd, scanned;
    always @(posedge clk) begin
        if (resetn) begin
            cycle++;
            if (valid) begin
                if (input_count%300==299) source_cycle[input_count/300]=cycle;
                input_count++;
            end
            #0.1;
            if (!ready) $fatal(1,"FAIL: source backpressure");
            if (dut.stage0_valid) begin
                if (dut.stage0_data !== expected0[count0]) $fatal(1,"FAIL: stage0 sample %0d",count0);
                count0++;
            end
            if (dut.stage1_valid) begin
                if (dut.stage1_data !== expected1[count1]) $fatal(1,"FAIL: stage1 sample %0d",count1);
                count1++;
            end
            if (dut.stage2_valid) begin
                if (dut.stage2_data !== expected2[count2]) $fatal(1,"FAIL: stage2 sample %0d",count2);
                count2++;
            end
            if (out_valid) begin
                if (out_data !== expected_out[count_out]) $fatal(1,"FAIL: int64 sample %0d: %032x != %032x",count_out,out_data,expected_out[count_out]);
                if (cycle-source_cycle[count_out]!=35) $fatal(1,"FAIL: latency %0d",cycle-source_cycle[count_out]);
                count_out++;
            end
        end
    end
    initial begin
        if (!$value$plusargs("VECTOR_DIR=%s",vector_dir)) $fatal(1,"Missing VECTOR_DIR");
        fd=$fopen({vector_dir,"/counts.txt"},"r");
        scanned=$fscanf(fd,"%d %d %d %d",n,n0,n1,n2); $fclose(fd);
        if(scanned!=4 || n>400000) $fatal(1,"Bad vector counts");
        vector_path=$sformatf("%s/input.hex",vector_dir);
        $readmemh(vector_path,input_words,0,n-1);
        vector_path=$sformatf("%s/stage0.hex",vector_dir);
        $readmemh(vector_path,expected0,0,n0-1);
        vector_path=$sformatf("%s/stage1.hex",vector_dir);
        $readmemh(vector_path,expected1,0,n1-1);
        vector_path=$sformatf("%s/stage2.hex",vector_dir);
        $readmemh(vector_path,expected2,0,n2-1);
        vector_path=$sformatf("%s/stored.hex",vector_dir);
        $readmemh(vector_path,expected_out,0,n2-1);
        for(int k=0;k<n;k++) if($isunknown(input_words[k])) $fatal(1,"FAIL: missing input vector %0d",k);
        for(int k=0;k<n0;k++) if($isunknown(expected0[k])) $fatal(1,"FAIL: missing stage0 vector %0d",k);
        for(int k=0;k<n1;k++) if($isunknown(expected1[k])) $fatal(1,"FAIL: missing stage1 vector %0d",k);
        for(int k=0;k<n2;k++) if($isunknown(expected2[k]) || $isunknown(expected_out[k])) $fatal(1,"FAIL: missing final vector %0d",k);
        // Repeat after reset with valid gaps to verify state clearing and
        // sample-count decimation independently of wall-clock spacing.
        for(int pass=0;pass<2;pass++) begin
            @(negedge clk); resetn=0; valid=0;
            repeat(16) @(negedge clk);
            count0=0;count1=0;count2=0;count_out=0;input_count=0;cycle=0;
            resetn=1;
            for(int k=0;k<n;k++) begin
                if(pass==1 && k%997==0) begin
                    valid=0; repeat(3) @(negedge clk);
                end
                valid=1; data=input_words[k]; @(negedge clk);
            end
            valid=0; repeat(100) @(negedge clk);
            if(count0!=n0 || count1!=n1 || count2!=n2 || count_out!=n2)
                $fatal(1,"FAIL: missing outputs %0d %0d %0d %0d",count0,count1,count2,count_out);
            $display("PASS: exact stage bits and int64 output, pass=%0d input=%0d output=%0d latency=35",pass,n,count_out);
        end
        $finish;
    end
endmodule
