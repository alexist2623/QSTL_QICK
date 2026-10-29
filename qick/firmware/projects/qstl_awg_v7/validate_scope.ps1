param([switch]$RequireFunctional,[string]$EvidenceRoot=$env:QICK_V7_EVIDENCE_ROOT)
$ErrorActionPreference='Stop'
if(!$EvidenceRoot){throw 'Set QICK_V7_EVIDENCE_ROOT to the fresh v7 verification evidence directory'}
$repo=(Resolve-Path "$PSScriptRoot/../../../..").Path
$branch=(& git -C $repo branch --show-current).Trim()
if($branch -ne 'awg_tuning_v7'){throw "Unexpected QICK branch: $branch"}
function Read-Json([string]$p){Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json}
function Hash([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Check-Hashes($map){
 if(!$map -or @($map.PSObject.Properties).Count -eq 0){throw 'Missing source/evidence hash map'}
 foreach($item in $map.PSObject.Properties){
 if(!(Test-Path -LiteralPath $item.Name -PathType Leaf) -or (Hash $item.Name) -ne $item.Value.ToLowerInvariant()){throw "Source/evidence changed: $($item.Name)"}
}}
$protected=Read-Json "$EvidenceRoot/protected_before.json"
Check-Hashes $protected.sha256
foreach($name in 'ios.xdc','timing.xdc'){
 if((Hash "$PSScriptRoot/$name") -ne (Hash "$PSScriptRoot/../qstl_awg_v6/$name")){throw "v7 changed existing constraints: $name"}
}
if(!$RequireFunctional){Write-Output 'V7_PROTECTED_SCOPE_PASS';exit 0}
$gate=Read-Json "$EvidenceRoot/functional_gate.json"
if(!$gate.passed -or !$gate.fresh_v7_rtl -or !$gate.actual_tprocessor_execution -or !$gate.all_lane_pairs -or !$gate.long_hold_overflow -or !$gate.set_ramp_rf_common_latency -or $gate.core_cycles -ne 11 -or $gate.final_awg_rf_cycles -ne 31){throw 'Fresh v7 functional checks incomplete'}
$expected=@('common_latency','extended_ramp','control_alignment','production_dc_rc','set_saturation','timing_tail','dc_area','dc_boundaries','dc_faults','full_cpu_legacy','full_cpu_extended','software')
foreach($name in $expected){
 $check=$gate.checks.$name
 if(!$check -or !$check.passed -or $check.exit_code -ne 0){throw "Missing or failed functional stage: $name"}
 Check-Hashes $check.evidence_hashes
}
Check-Hashes $gate.source_hashes
Write-Output 'V7_FUNCTIONAL_GATE_PASS'
