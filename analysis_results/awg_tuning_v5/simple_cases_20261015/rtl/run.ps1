param([ValidateSet('coarse','fine')][string]$Stage='coarse')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath 'C:/GIT_Workspace/QSTL_QICK'
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH='C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI;C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps;C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps;C:/GIT_Workspace/QSTL_QICK/qick/qick_lib'
$env:PATH='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+$env:PATH
if ($Stage -eq 'coarse') {
    & 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 -u "$PSScriptRoot/run_coarse.py"
    exit $LASTEXITCODE
}
& 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 -u "$PSScriptRoot/fine/prepare.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 -u "$PSScriptRoot/fine/run.py" --prepared "$PSScriptRoot/fine/prepared.json" --state "$PSScriptRoot/fine/status.json"
exit $LASTEXITCODE
