param([switch]$RequireFunctional,[string]$EvidenceRoot=$env:QICK_V8_EVIDENCE_ROOT)
$ErrorActionPreference='Stop'
if(!$EvidenceRoot){throw 'Set QICK_V8_EVIDENCE_ROOT to the v8 verification evidence directory'}
$repo=(Resolve-Path "$PSScriptRoot/../../../..").Path
if((& git -C $repo branch --show-current).Trim() -ne 'awg_tuning_v8'){throw 'Expected awg_tuning_v8 branch'}
function Read-Json([string]$p){Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json}
function File-Hash([string]$p){
 $stream=[IO.File]::OpenRead($p);$hash=[Security.Cryptography.SHA256]::Create()
 try {return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
 finally {$stream.Dispose();$hash.Dispose()}
}
function Check-Hashes($map){
 if(!$map -or @($map.PSObject.Properties).Count -eq 0){throw 'Missing source/evidence hash map'}
 foreach($item in $map.PSObject.Properties){
  if(!(Test-Path -LiteralPath $item.Name -PathType Leaf) -or
     (File-Hash $item.Name) -ne $item.Value){throw "Changed file: $($item.Name)"}
 }
}
Check-Hashes (Read-Json "$EvidenceRoot/protected_before.json").sha256
if(!$RequireFunctional){Write-Output 'V8_PROTECTED_SCOPE_PASS';exit 0}
$gate=Read-Json "$EvidenceRoot/functional_gate.json"
if(!$gate.passed){throw 'Functional gate is incomplete'}
foreach($name in @('ddr_abort','ddr_capture','clipping','common_latency','control_alignment','set_saturation','timing_tail','dc_area','dc_faults','ramp_edges','dc_boundaries','cpu_legacy','cpu_edges')){
 $check=$gate.checks.$name
 if(!$check -or !$check.passed){throw "Failed/missing check: $name"}
 Check-Hashes $check.evidence_hashes
}
Check-Hashes $gate.source_hashes
Write-Output 'V8_FUNCTIONAL_GATE_PASS'
