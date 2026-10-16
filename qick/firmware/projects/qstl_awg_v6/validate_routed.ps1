param([Parameter(Mandatory=$true)][string]$Build)
$ErrorActionPreference='Stop'
$result=@{}
foreach($line in Get-Content -LiteralPath "$Build/build_result.txt"){
 $key,$value=$line -split '=',2;$result[$key]=$value
}
foreach($key in 'setup_wns_ns','hold_whs_ns'){
 if(!$result.ContainsKey($key) -or $result[$key] -eq '' -or [double]$result[$key] -lt 0){throw "Final routed $key failed or missing"}
}
foreach($key in 'setup_tns_ns','hold_ths_ns'){
 if(!$result.ContainsKey($key) -or $result[$key] -eq '' -or [double]$result[$key] -ne 0){throw "Final routed $key failed or missing"}
}
$timing=Get-Content -LiteralPath "$Build/timing_summary_postroute.rpt" -Raw
$summary=[regex]::Match($timing,'(?m)^\s*WNS\(ns\)[^\r\n]*\r?\n[^\r\n]*\r?\n([^\r\n]+)')
if(!$summary.Success){throw 'Final routed timing summary missing'}
$values=$summary.Groups[1].Value.Trim() -split '\s+'
if($values.Count -ne 12){throw 'Unexpected timing summary columns'}
foreach($i in 0,4,8){if([double]$values[$i] -lt 0){throw 'Negative setup/hold/pulse-width slack'}}
foreach($i in 1,2,5,6,9,10){if([double]$values[$i] -ne 0){throw 'Final timing failures remain'}}
$skew=Get-Content -LiteralPath "$Build/bus_skew_postroute.rpt" -Raw
if([regex]::Matches($skew,'Slack \(MET\)').Count -ne 14 -or $skew -match 'VIOLATED'){throw 'Final bus-skew failure or missing paths'}
$route=Get-Content -LiteralPath "$Build/route_status_postroute.rpt" -Raw
if($route -notmatch '# of nets with routing errors\.+\s*:\s*0\s*:'){throw 'Routing errors or missing route report'}
Write-Output 'V6_ROUTED_GATE_PASS'
