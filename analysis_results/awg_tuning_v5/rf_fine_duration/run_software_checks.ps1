param(
    [Parameter(Mandatory=$true)][string]$Tag,
    [string]$Gui='F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI'
)
$ErrorActionPreference='Stop'
$repo='C:/GIT_Workspace/QSTL_QICK'
Set-Location -LiteralPath $repo
$evidence=Join-Path $PSScriptRoot $Tag
if(Test-Path -LiteralPath $evidence){throw 'Use a new evidence tag; never overwrite an earlier execution'}
New-Item -ItemType Directory -Path $evidence | Out-Null
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH="$Gui;C:/Users/Measurement2/AppData/Local/Temp/qick-v3-validation-deps;C:/Users/Measurement2/AppData/Local/Temp/qick-waveform-time-axis-deps;$repo/qick/qick_lib"
$env:PATH='C:/Users/Measurement2/.conda/envs/qcodes2/Library/bin;C:/Users/Measurement2/.conda/envs/qcodes2/DLLs;'+$env:PATH
$python='C:/Users/Measurement2/.conda/envs/qcodes2/python.exe'
$hashes=[ordered]@{}
Get-ChildItem -LiteralPath $Gui -Filter '*.py' -File | ForEach-Object {
    $hashes[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
}
$hashes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$evidence/source_hashes.json" -Encoding UTF8
$tests=@(
 'test_qick_fine_tune_sweep.py','test_qick_qcodes_experiment.py','test_output_sum_v4.py',
 'test_rf_duration_oneshot.py','test_dc_waveform_gui_rf.py','test_rf_delay_software_sweep.py',
 'test_rf_t2_delay_core.py','test_rf_t2_delay_editor.py','test_rf_t2_integration.py',
 'test_power_calibration.py','test_qick_power_calibration.py','test_qick_dc_area.py',
 'test_rc_precompensation.py','test_rf_fine_duration_compiler.py','test_rf_fine_duration_editor.py',
 'test_rf_fine_duration_runtime.py','test_acquisition_segment_timing.py'
) | ForEach-Object {Join-Path $Gui $_}
& $python -X utf8 "$repo/analysis_results/awg_tuning_v5/plot_annotation_fix/run_tests.py" @tests -q --tb=short "--junitxml=$evidence/affected.xml" *> "$evidence/affected.log"
if($LASTEXITCODE){throw "Affected software tests failed; see $evidence/affected.log"}
$env:QICK_FINE_GUI=$Gui
$env:QICK_FINE_BASELINE_BUILD="F:/Vivado_Output/a5fine_baseline_$Tag"
$env:QICK_FINE_BASELINE_EVIDENCE="$evidence/baseline"
& $python -X utf8 "$PSScriptRoot/recompile_baseline.py" *> "$evidence/baseline.log"
if($LASTEXITCODE){throw "Coarse input comparison failed; see $evidence/baseline.log"}
foreach($file in $hashes.Keys){
    if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $hashes[$file]){
        throw "Source changed during verification: $file"
    }
}
[xml]$xml=Get-Content -LiteralPath "$evidence/affected.xml" -Raw
$suite=$xml.testsuites.testsuite
if([int]$suite.failures -or [int]$suite.errors -or [int]$suite.skipped){throw 'Unexpected test failure, error or skip'}
if(!(Get-Content -LiteralPath "$evidence/affected.log" -Raw).Contains('QT_EXPLICIT_TEARDOWN_COMPLETE')){
    throw 'Qt process did not complete explicit teardown'
}
[ordered]@{passed=$true;finished=(Get-Date -Format o);tests=[int]$suite.tests;
    source_hashes=$hashes;coarse_cases=9;gui=$Gui;board_access=$false;production_modified=$false} |
    ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$evidence/result.json" -Encoding UTF8
Write-Output "SOFTWARE_PASS tests=$($suite.tests) coarse_cases=9 source_hashes_unchanged"
