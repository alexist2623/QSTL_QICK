param([ValidateSet('zero','suite','fine-prepare','fine-run')][string]$Stage)
$ErrorActionPreference='Stop'
$repo='C:/GIT_Workspace/QSTL_QICK'
Set-Location -LiteralPath $repo
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH="$PSScriptRoot;C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI;C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps;C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps;$repo/qick/qick_lib"
$env:PATH='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+$env:PATH
$python='C:/Users/Measurement2/.conda/envs/qcodes2/python.exe'
switch($Stage){
 'zero' {& $python -X utf8 "$PSScriptRoot/zero_offset_probe.py"}
 'suite' {& $python -X utf8 "$PSScriptRoot/run_suite.py"}
 'fine-prepare' {
  $env:QICK_FINE_SCENARIO='v5'
  $env:QICK_FINE_GUI='C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI'
  $env:QICK_FINE_RTL_BUILD='F:/Vivado_Output/a5post_fine_rtl1'
  & $python -X utf8 "$PSScriptRoot/fine/prepare.py"
  if($LASTEXITCODE){exit $LASTEXITCODE}
  & $python -X utf8 "$PSScriptRoot/raw_same_timestamp.py" "$PSScriptRoot/fine/prepared.json"
 }
 'fine-run' {& $python -X utf8 "$PSScriptRoot/fine/run.py"}
}
exit $LASTEXITCODE
