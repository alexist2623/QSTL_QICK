# Runtime-only check: creates no project and runs no synthesis or simulation.
puts "VIVADO_PYTHONHOME=$::env(PYTHONHOME)"
set validator C:/GIT_Workspace/QSTL_QICK/qick/firmware/projects/qstl_awg_v4/validate_scope.py
set output [exec C:/Users/Measurement2/.conda/envs/qcodes2/python.exe -E -X utf8 $validator --require-functional]
puts "EXTERNAL_PYTHON_VALIDATOR=$output"
puts "PYTHON_ENVIRONMENT_CHECK=PASS"
exit 0
