param([switch]$RequireFunctional,[string]$EvidenceRoot=$env:QICK_V6_EVIDENCE_ROOT)
$ErrorActionPreference='Stop'
if(!$EvidenceRoot){throw 'Set QICK_V6_EVIDENCE_ROOT to the fresh v6 verification evidence directory'}
$repo=(Resolve-Path "$PSScriptRoot/../../../..").Path
$gui=Join-Path (Split-Path $repo) 'PulseGenerator'
foreach($path in $repo,$gui){
 $branch=(& git -C $path branch --show-current).Trim()
 if($branch -ne 'awg_tuning_v4'){throw "Unexpected branch: $path $branch"}
}
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
 if((Hash "$PSScriptRoot/$name") -ne (Hash "$PSScriptRoot/../qstl_awg_v5/$name")){throw "v6 changed existing constraints: $name"}
}
if(!$RequireFunctional){Write-Output 'V6_PROTECTED_SCOPE_PASS';exit 0}
$gate=Read-Json "$EvidenceRoot/functional_gate.json"
if(!$gate.passed -or !$gate.fresh_v6_rtl -or !$gate.actual_tprocessor_execution -or !$gate.one_cycle_rise_hold_fall -or !$gate.one_cycle_rise_two_hold_fall -or !$gate.two_cycle_rise_one_hold_fall -or !$gate.set_ramp_rf_common_latency){throw 'Fresh v6 functional checks incomplete'}
$expected=@('sum','awg_core','tproc_dispatcher','native_alignment','full_cpu_chain','dc_area','dc_boundaries','dc_faults','production_dc_rc','set_saturation','legacy_outputs','software_baseline')
foreach($name in $expected){
 $check=$gate.checks.$name
 if(!$check -or !$check.passed -or $check.exit_code -ne 0){throw "Missing or failed functional stage: $name"}
 Check-Hashes $check.evidence_hashes
}
Check-Hashes $gate.source_hashes
Write-Output 'V6_FUNCTIONAL_GATE_PASS'
