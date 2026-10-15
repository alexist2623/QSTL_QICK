$ErrorActionPreference='Stop'
Set-Location -LiteralPath 'C:/GIT_Workspace/QSTL_QICK'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI;C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps;C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps;C:/GIT_Workspace/QSTL_QICK/qick/qick_lib'
$controllerEvidence=Join-Path $PSScriptRoot 'controller_status.json'
if(Test-Path -LiteralPath $controllerEvidence){throw 'Preserve existing controller evidence'}
$controllerState=@{complete=$false;stage='Quantum0_UDD4';started=(Get-Date -Format o);controller_pid=$PID}
$controllerState | ConvertTo-Json | Set-Content -LiteralPath $controllerEvidence
& 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 "$PSScriptRoot/run_rtl_exec.py" --skip-compile *> "$PSScriptRoot/rtl_controller.log"
$firstExit=$LASTEXITCODE
$controllerState['quantum_udd_exit']=$firstExit
if($firstExit -eq 0){
    $controllerState['stage']='CPMG4'
    $controllerState | ConvertTo-Json | Set-Content -LiteralPath $controllerEvidence
    & 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 "$PSScriptRoot/run_cpmg_rtl_exec.py" --skip-compile *> "$PSScriptRoot/cpmg_controller.log"
    $secondExit=$LASTEXITCODE
    $controllerState['cpmg_exit']=$secondExit
}else{$secondExit=-1}
if($firstExit -eq 0 -and $secondExit -eq 0){
    & 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 "$PSScriptRoot/final_audit.py" after *> "$PSScriptRoot/final_audit_console.log"
    $integrityExit=$LASTEXITCODE
}else{$integrityExit=-1}
$controllerState['final_integrity_exit']=$integrityExit
& 'C:/Users/Measurement2/.conda/envs/qcodes2/python.exe' -X utf8 "$PSScriptRoot/report.py" *> "$PSScriptRoot/report_console.log"
$reportExit=$LASTEXITCODE
$controllerState['report_exit']=$reportExit
$controllerState['complete']=($firstExit -eq 0 -and $secondExit -eq 0 -and $reportExit -eq 0 -and $integrityExit -eq 0)
$controllerState['stage']=if($controllerState['complete']){'completed'}else{'failed'}
$controllerState['finished']=(Get-Date -Format o)
$controllerState | ConvertTo-Json | Set-Content -LiteralPath $controllerEvidence
if(-not $controllerState['complete']){exit 1}
exit 0
