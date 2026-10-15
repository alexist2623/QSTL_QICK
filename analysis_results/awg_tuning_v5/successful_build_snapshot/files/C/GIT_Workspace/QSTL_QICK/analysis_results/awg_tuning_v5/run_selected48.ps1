$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../..").Path
$python='C:/Users/Measurement2/.conda/envs/qcodes2/python.exe'
$valid="$repo/qick/firmware/ip/axis_awg_tuning_v3/validation"
$build='F:/Vivado_Output/a5rc48'
if(Test-Path -LiteralPath $build){throw 'Fresh selected-48 run required'}
$env:PYTHONDONTWRITEBYTECODE='1'
$env:QT_QPA_PLATFORM='offscreen'
$env:PATH='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+$env:PATH
$state=[ordered]@{complete=$false;pid=$PID;started=(Get-Date -Format o);build=$build;selected_width=48;comparison_performed=$false}
function Save-State {$state|ConvertTo-Json|Set-Content "$PSScriptRoot/selected48_status.json" -Encoding UTF8}
Save-State
try {
 & $python -X utf8 "$valid/run_width_comparison.py" --width 48 --build $build *> "$PSScriptRoot/selected48_run.log"
 $state.rtl_exit=$LASTEXITCODE;Save-State
 if($LASTEXITCODE){throw 'Selected-48 RTL failed'}
 & $python -X utf8 "$valid/report_selected48.py" --build $build --out "$PSScriptRoot/selected48" *> "$PSScriptRoot/selected48_report.log"
 $state.report_exit=$LASTEXITCODE
 if($LASTEXITCODE){throw 'Selected-48 report verification failed'}
 $state.complete=$true;$state.finished=Get-Date -Format o;Save-State
} catch {$state.error=$_.Exception.Message;Save-State;Write-Error $_;exit 1}
