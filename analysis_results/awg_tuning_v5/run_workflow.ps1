# One-way v5 workflow. No publication, retry, board access or source repair.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../..").Path
$project="$repo/qick/firmware/projects/qstl_awg_v5"
$build='F:/Vivado_Output/a5full1'
if(Test-Path "$PSScriptRoot/workflow_status.json"){throw 'Existing v5 workflow; do not launch twice'}
$state=[ordered]@{complete=$false;stage='waiting_validation';pid=$PID;started=(Get-Date -Format o);build=$build;no_board_actions=$true;no_publish=$true;no_retry=$true}
function Save-State {
 $state.updated=Get-Date -Format o
 $state|ConvertTo-Json -Depth 7|Set-Content "$PSScriptRoot/workflow_status.tmp" -Encoding UTF8
 Move-Item -LiteralPath "$PSScriptRoot/workflow_status.tmp" -Destination "$PSScriptRoot/workflow_status.json" -Force
}
Save-State
try {
 while($true){
  $replay=Get-Content "$PSScriptRoot/replays_status.json" -Raw|ConvertFrom-Json
  if($replay.stage -eq 'failed'){throw 'System validation failed; synthesis is blocked'}
  if($replay.complete){break}
  $controller=Get-CimInstance Win32_Process -Filter "ProcessId=$($replay.pid)"
  if(!$controller -or $controller.Name -ne 'powershell.exe' -or $controller.CommandLine -notmatch 'awg_tuning_v5[\\/]run_replays.ps1'){
   throw 'Replay controller ended before completion; no synthesis started'
  }
  Start-Sleep -Seconds 15
 }
 $state.stage='functional_gate';Save-State
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$project/validate_scope.ps1" -RequireFunctional *> "$PSScriptRoot/prebuild_gate.log"
 if($LASTEXITCODE){throw 'Functional gate failed; no synthesis started'}
 if(Test-Path -LiteralPath $build){throw 'Build already exists; no restart permitted'}
 $state.stage='full_build';$state.build_started=Get-Date -Format o;Save-State
 Push-Location 'F:/Vivado_Output'
 try {
  & F:/Xilinx/Vivado/2023.1/bin/vivado.bat -mode batch -source "$project/build_vivado_2023_1.tcl" -log F:/Vivado_Output/a5full1_vivado.log -journal F:/Vivado_Output/a5full1_vivado.jou -tclargs $build *> F:/Vivado_Output/a5full1_build.log
  $state.build_exit_code=$LASTEXITCODE
 } finally {Pop-Location}
 $state.build_finished=Get-Date -Format o;Save-State
 if($state.build_exit_code -ne 0){throw "Vivado failed (exit $($state.build_exit_code)); no repair/retry/publication"}
 $result=@{}
 foreach($line in Get-Content "$build/build_result.txt"){$key,$value=$line -split '=',2;$result[$key]=$value}
 $state.build_result=$result
 if($result.timing_closed -ne 'YES'){throw 'Final routed setup/hold failed'}
 $timing=Get-Content "$build/timing_summary_postroute.rpt" -Raw
 $summary=[regex]::Match($timing,'(?m)^\s*WNS\(ns\)[^\r\n]*\r?\n[^\r\n]*\r?\n([^\r\n]+)')
 if(!$summary.Success){throw 'Missing final timing summary'}
 $values=$summary.Groups[1].Value.Trim() -split '\s+'
 if($values.Count -ne 12 -or [double]$values[1] -ne 0 -or [int]$values[2] -ne 0 -or [double]$values[5] -ne 0 -or [int]$values[6] -ne 0 -or [double]$values[9] -ne 0 -or [int]$values[10] -ne 0){throw 'Final timing endpoints fail signoff'}
 $skew=Get-Content "$build/bus_skew_postroute.rpt" -Raw
 $state.bus_skew_met=[regex]::Matches($skew,'Slack \(MET\)').Count
 if($state.bus_skew_met -ne 14 -or $skew -match 'VIOLATED'){throw 'Final bus-skew signoff failed'}
 $route=Get-Content "$build/route_status_postroute.rpt" -Raw
 if($route -notmatch '# of nets with routing errors\.+\s*:\s*0\s*:'){throw 'Final routing errors/missing report'}
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$project/validate_scope.ps1" -RequireFunctional *> "$PSScriptRoot/postbuild_gate.log"
 if($LASTEXITCODE){throw 'Post-build source/evidence gate failed'}
 $state.artifacts=[ordered]@{}
 foreach($name in 'bitstream.bit','bitstream.hwh','bitstream.xsa'){
  $file=Get-Item "$build/$name"
  $state.artifacts[$name]=[ordered]@{path=$file.FullName;bytes=$file.Length;sha256=(Get-FileHash $file.FullName).Hash}
 }
 $state.complete=$true;$state.stage='timing_passed_candidate_not_deployed';Save-State
} catch {
 $state.stage='stopped_failure';$state.error=$_.Exception.Message;Save-State
 Write-Error $_
 exit 1
}
