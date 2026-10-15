param([switch]$RequireFunctional)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../../../..").Path
$gui=Join-Path (Split-Path $repo) 'PulseGenerator'
$e=Join-Path $repo 'analysis_results/awg_tuning_v5'
function Read-Json([string]$path){Get-Content -LiteralPath $path -Raw|ConvertFrom-Json}
function Hash([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
function Assert-Hashes($hashes){foreach($item in $hashes.PSObject.Properties){
 if(!(Test-Path -LiteralPath $item.Name -PathType Leaf) -or (Hash $item.Name) -ne $item.Value){throw "Evidence source changed: $($item.Name)"}
}}
foreach($root in $repo,$gui){
 $branch=(& git -C $root branch --show-current).Trim()
 if($branch -ne 'awg_tuning_v4'){throw "Unexpected branch: $root $branch"}
}
$before=Read-Json "$e/protected_before.json"
$authorized=Read-Json "$e/authorized_gui_fix.json"
Assert-Hashes $authorized.files
$changed=@();$userSettings=@()
foreach($item in $before.PSObject.Properties){
 if(!(Test-Path -LiteralPath $item.Name -PathType Leaf)){throw "Protected file missing: $($item.Name)"}
 if((Hash $item.Name) -ne $item.Value){
  if($authorized.files.PSObject.Properties.Name -contains $item.Name){$changed+=$item.Name}
  elseif($item.Name.Replace('\','/').StartsWith($gui.Replace('\','/')+'/DCWaveformGeneratorGUI/') -and $item.Name.EndsWith('.json')){$userSettings+=$item.Name}
  else{throw "Unauthorized protected-source change: $($item.Name)"}
 }
}
foreach($name in 'timing.xdc','ios.xdc','bd_2023-1.tcl'){
 if((Hash "$PSScriptRoot/$name") -ne (Hash "$PSScriptRoot/../qstl_awg_v4/$name")){throw "v5 baseline differs: $name"}
}
$scope=[ordered]@{passed=$true;checked=(Get-Date -Format o);protected_files=@($before.PSObject.Properties).Count;authorized_gui_changes=$changed;user_settings_changed_externally=$userSettings;branch='awg_tuning_v4'}
$scope|ConvertTo-Json -Depth 5|Set-Content "$e/scope_current.json" -Encoding UTF8
if(!$RequireFunctional){Write-Output 'V5_SCOPE_PASS';exit 0}

$checks=[ordered]@{}
$routedGateTests=Read-Json "$e/routed_gate_tests.json"
if(!$routedGateTests.passed -or @($routedGateTests.cases).Count -ne 9 -or
   $routedGateTests.gate_sha256 -ne (Hash "$PSScriptRoot/validate_routed.ps1")){throw 'Routed signoff gate tests missing or stale'}
foreach($entry in @(@('sum','F:/Vivado_Output/a5sum2'),@('native','F:/Vivado_Output/a5native3'),@('ramp_hold','F:/Vivado_Output/a5ramp2'))){
 $result=Read-Json "$($entry[1])/result.json"
 if(!$result.passed -or $result.exit_code -ne 0){throw "Failed or incomplete test: $($entry[0])"}
 Assert-Hashes (Read-Json "$($entry[1])/source_hashes.json")
 $checks[$entry[0]]=$result
}
$regular=Read-Json 'F:/Vivado_Output/a5reg1/status.json'
if(!$regular.finished){throw 'Regular regression is still running'}
$retry=Read-Json "$e/desktop_retries.json"
$reviewed=@();$softwareTests=0;$softwareModules=0
foreach($stage in $regular.stages.PSObject.Properties){
 $log=Get-Content -LiteralPath $stage.Value.log -Raw
 if($stage.Name -match '^(gui|qick)_'){
  $softwareModules++
  if($stage.Value.state -eq 'passed'){
   $match=[regex]::Match($log,'(\d+) passed')
   if(!$match.Success){throw "Missing test count: $($stage.Name)"}
   $softwareTests+=[int]$match.Groups[1].Value
  }
 }
 if($stage.Value.state -eq 'passed'){continue}
 $name=$stage.Name -replace '^gui_DCWaveformGeneratorGUI_',''
 if($name -notin @('test_rc_precompensation','test_sparameter_phase_storage','test_trigger_output_panel')){throw "Unreviewed failure: $($stage.Name)"}
 $r=$retry.$name
 if(!$r -or $r.exit_code -ne 0 -or (Hash $r.source) -ne $r.sha256 -or (Hash $r.harness) -ne $r.harness_sha256){throw "Invalid retry: $name"}
 $retryLog=Get-Content -LiteralPath $r.log -Raw
 $m=[regex]::Match($retryLog,'(\d+) passed')
 if(!$m.Success -or !$retryLog.Contains('QT_EXPLICIT_TEARDOWN_COMPLETE') -or $retryLog -match 'QT_CALLBACK_ERRORS:|FAILED|fatal exception'){throw "Retry failed: $name"}
 if($name -ne 'test_trigger_output_panel' -and $log -notmatch 'passed.*[\s\S]*access violation'){throw "Unexpected initial failure: $name"}
 if($name -eq 'test_trigger_output_panel' -and !$log.Contains("No module named 'pynq'")){throw 'Unexpected trigger test failure'}
 $softwareTests+=[int]$m.Groups[1].Value;$reviewed+=$name
}
foreach($name in 'tb_dc_area','tb_dc_boundaries','tb_width_awg','tb_dc_faults','tb_set_saturation'){
 $result=Read-Json "F:/Vivado_Output/a5reg1/$name/result.json"
 if(!$result.passed){throw "Basic RTL failed: $name"}
 Assert-Hashes (Read-Json "F:/Vivado_Output/a5reg1/$name/sources.json")
}
foreach($path in $regular.changed_sources_or_user_settings){
 if($path.Replace('\','/') -notin @($changed+$userSettings)){throw "Unreviewed regular source change: $path"}
}
[xml]$guiTests=Get-Content "$e/gui_selection_tests.xml" -Raw
$suite=$guiTests.testsuites.testsuite
if([int]$suite.tests -ne 73 -or [int]$suite.failures -ne 0 -or [int]$suite.errors -ne 0){throw 'GUI selection regression failed'}
$replays=Read-Json "$e/replays_status.json"
if(!$replays.complete -or @($replays.cases.PSObject.Properties).Count -ne 9){throw 'System replay is incomplete'}
foreach($case in $replays.cases.PSObject.Properties){
 $result=Read-Json "$($case.Value.build)/result.json"
 if($case.Value.state -ne 'passed' -or !$result.passed -or $result.exit_code -ne 0){throw "System case failed: $($case.Name)"}
 Assert-Hashes (Read-Json "$($case.Value.build)/source_hashes.json")
}
$compiler=Read-Json "$e/compiler_equivalence.json"
if(!$compiler.complete -or @($compiler.cases).Count -ne 9 -or
   $compiler.harness_sha256 -ne (Hash "$e/recompile_inputs.py")){throw 'Current GUI compiler proof missing or stale'}
Assert-Hashes $compiler.source_hashes
foreach($case in $compiler.cases){
 if(!$case.passed -or (Hash $case.source) -ne $case.source_sha256){throw "Compiler fixture changed: $($case.case)"}
 Assert-Hashes $case.files
 foreach($entry in $case.files.PSObject.Properties){
  $name=Split-Path $entry.Name -Leaf
  if($name -in @('pmem.hex','dmem.txt') -and
     (Hash (Join-Path $replays.cases.($case.case).build $name)) -ne $entry.Value){throw "Current compiler and v5 RTL input differ: $($case.case) $name"}
 }
}
$rcState=Read-Json "$e/selected48_status.json"
if(!$rcState.complete -or $rcState.rtl_exit -ne 0 -or $rcState.report_exit -ne 0){throw 'Selected-48 continuous RC validation is incomplete or failed'}
Assert-Hashes (Read-Json 'F:/Vivado_Output/a5rc48/source_hashes.json')
$rc=Read-Json "$e/selected48/width_results.json"
$rc48=$rc.widths.'48'
if(!$rc.complete -or $rc.selected_width -ne 48 -or $rc.comparison_performed -or
   $rc48.completed_shots -ne 200 -or $rc48.overflow_points -ne 0 -or
   $rc48.max_residual_effective_code_samples -ne 0 -or
   $rc48.max_cumulative_effective_code_samples -ne 0 -or
   $rc48.max_collection_error_without_overflow -ne 0 -or
   $rc48.final_cumulative_effective_code_samples -ne 0 -or
   $rc48.max_rc_error_mv -ge (800/8192) -or
   (Hash "$e/selected48/width_48.csv") -ne $rc48.csv_sha256){throw 'Selected-48 RC signoff failed'}
$v5Hashes=[ordered]@{}
$files=@(Get-ChildItem "$repo/qick/firmware/ip/axis_output_sum_v2/src" -File)
$files+=@(Get-ChildItem $PSScriptRoot -File|Where-Object {$_.Extension -in @('.tcl','.xdc','.ps1')})
foreach($file in $files){$v5Hashes[$file.FullName]=Hash $file.FullName}
$gate=[ordered]@{passed=$true;verified=(Get-Date -Format o);scope=$scope;checks=$checks;software_modules=$softwareModules;software_tests=$softwareTests;gui_selection_tests=73;reviewed_initial_failures=$reviewed;system_cases=9;current_compiler_equivalent_cases=9;selected48=$rc;fresh_v5_rtl=$true;gui_input_policy='current GUI/compiler byte-equivalent to replayed PMEM/DMEM; Python v4 timing retained';v5_sources=$v5Hashes}
$gate|ConvertTo-Json -Depth 10|Set-Content "$e/prebuild_gate.json" -Encoding UTF8
Write-Output "V5_FUNCTIONAL_GATE_PASS software=$softwareTests modules=$softwareModules system_cases=9"
