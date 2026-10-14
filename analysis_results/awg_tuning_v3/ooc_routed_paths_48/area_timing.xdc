
create_clock -name fabric -period 3.333 [get_ports clk]
set data_inputs [get_ports -filter {DIRECTION == IN && NAME != clk && NAME != rstn}]
set_input_delay -clock fabric 0.0 $data_inputs
set_output_delay -clock fabric 0.0 [all_outputs]
# rstn is a reset control, not a fabric-cycle data input in this arithmetic test.
set_false_path -from [get_ports rstn]

