$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../..").Path
$old=Get-Content "$repo/analysis_results/awg_tuning_v4/full_regression_20261014/status.json" -Raw | ConvertFrom-Json
$runner="$repo/qick/firmware/ip/axis_output_sum_v2/validation/run_system_replay.ps1"
$state=[ordered]@{complete=$false;stage='system_replays';pid=$PID;started=(Get-Date -Format o);cases=[ordered]@{}}
if(Test-Path "$PSScriptRoot/replays_status.json"){throw 'Replay controller already has evidence'}
$state.cases.exact10us_hold1=[ordered]@{state='passed';build='F:/Vivado_Output/a5hold1r1';source=$old.cases.exact10us_hold1.folder}
$first=Get-Content 'F:/Vivado_Output/a5hold1r1/result.json' -Raw | ConvertFrom-Json
if(!$first.passed){throw 'First replay is not passed'}
function Save-State {
 $state.updated=Get-Date -Format o
 $state | ConvertTo-Json -Depth 7 | Set-Content "$PSScriptRoot/replays_status.tmp" -Encoding UTF8
 Move-Item -LiteralPath "$PSScriptRoot/replays_status.tmp" -Destination "$PSScriptRoot/replays_status.json" -Force
}
$keys=@('exact10us_hold2','rf_duration_extend','rf_duration_fixed','rc_only','hold_fixed_time','hold_fixed_voltage_offset','reversed_axes','stability')
$active=@();$next=0;$failed=$false
while($next -lt $keys.Count -or $active.Count){
 while(!$failed -and $next -lt $keys.Count -and $active.Count -lt 2){
  $key=$keys[$next];$build="F:/Vivado_Output/a5sys$next";$next++
  if(Test-Path $build){throw "Build already exists: $build"}
  $source=$old.cases.$key.folder.Replace('\','/')
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-CasePath',$source,'-Build',$build)
  $child=Start-Process powershell.exe -ArgumentList $args -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput "$PSScriptRoot/$key.console.log" -RedirectStandardError "$PSScriptRoot/$key.stderr.log"
  $state.cases[$key]=[ordered]@{state='running';build=$build;source=$source;pid=$child.Id;started=(Get-Date -Format o)}
  $active+=@{key=$key;process=$child};Save-State
 }
 $remaining=@()
 foreach($entry in $active){
  $child=$entry.process
  if(!$child.HasExited){$remaining+=$entry;continue}
  $child.WaitForExit();$key=$entry.key;$resultPath=Join-Path $state.cases[$key].build 'result.json'
  $ok=$false
  if(Test-Path $resultPath){$result=Get-Content $resultPath -Raw|ConvertFrom-Json;$ok=$result.passed -and $result.exit_code -eq 0}
  $state.cases[$key].state=if($ok){'passed'}else{'failed'}
  $state.cases[$key].finished=Get-Date -Format o
  if(!$ok){$failed=$true}
  Save-State
 }
 $active=$remaining
 if($failed -and !$active.Count){break}
 if($active.Count){Start-Sleep -Seconds 3}
}
$state.complete=(!$failed -and $state.cases.Count -eq 9)
$state.stage=if($state.complete){'passed'}else{'failed'}
Save-State
if(!$state.complete){exit 1}
