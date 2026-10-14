# Read-only installation capability query; does not create or modify a project.
puts "VIVADO_VERSION=[version -short]"
puts "TARGET_PART=[get_parts -quiet xczu49dr-ffvf1760-2-e]"
puts "TARGET_BOARD=[get_board_parts -quiet *zcu216*]"
exit
