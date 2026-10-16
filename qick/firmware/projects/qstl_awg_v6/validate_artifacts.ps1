param([Parameter(Mandatory=$true)][string]$Build)
$ErrorActionPreference='Stop'
function File-Hash([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
[xml]$hwh=Get-Content -LiteralPath "$Build/bitstream.hwh" -Raw
$modules=@($hwh.SelectNodes('//MODULE[@MODTYPE="axis_output_sum_v3"]'))
if($modules.Count -ne 7 -or $hwh.SelectNodes('//MODULE[@MODTYPE="axis_output_sum_v1" or @MODTYPE="axis_output_sum_v2"]').Count -ne 0){throw 'Expected seven v6 output-delay blocks'}
function Parameter($module,[string]$name){$module.SelectSingleNode("PARAMETERS/PARAMETER[@NAME='$name']").VALUE}
function Check-Link($module,[string]$port,[string]$instance,[string]$targetPort){
 $links=@($module.SelectNodes("PORTS/PORT[@NAME='$port']/CONNECTIONS/CONNECTION"))
 if($links.Count -ne 1 -or $links[0].INSTANCE -ne $instance -or $links[0].PORT -ne $targetPort){throw "Unexpected HWH connection: $($module.INSTANCE) $port"}
}
$awgs=@($hwh.SelectNodes('//MODULE[@MODTYPE="axis_awg_tuning_v4"]'))
if($awgs.Count -ne 7 -or $hwh.SelectNodes('//MODULE[@MODTYPE="axis_awg_tuning_v3"]').Count -ne 0){throw 'Expected seven common-latency AWG v4 blocks'}
$tprocs=@($hwh.SelectNodes('//MODULE[@MODTYPE="axis_tproc64x32_x8"]'))
if($tprocs.Count -ne 1 -or $tprocs[0].VLNV -ne 'QICK:QICK:axis_tproc64x32_x8:2.0'){throw 'Expected queued single-cycle tProcessor version 2.0'}
$pairs=@(@(4,8,0),@(5,10,1),@(6,11,3),@(8,13,-1),@(9,14,-1),@(10,15,-1),@(11,16,-1))
foreach($pair in $pairs){
 $awg=$pair[0];$slice=$pair[1];$rf=$pair[2]
 $sum=$hwh.SelectSingleNode("//MODULE[@INSTANCE='axis_output_sum_$awg']")
 if(!$sum -or $sum.MODTYPE -ne 'axis_output_sum_v3' -or
    (Parameter $sum 'N_PTS') -ne '16' -or
    (Parameter $sum 'PIPELINE_CYCLES') -ne '2' -or
    (Parameter $sum 'AWG_DELAY_CYCLES') -ne '6' -or
    [int](Parameter $sum 'BYPASS') -ne [int]($rf -lt 0)){throw "Unexpected v6 sum parameters: AWG $awg"}
 $generator=$hwh.SelectSingleNode("//MODULE[@INSTANCE='axis_awg_tuning_v4_$awg']")
 if(!$generator -or (Parameter $generator 'DC_AREA_BITS') -ne '48' -or (Parameter $generator 'EXTRA_Y_PIPE_STAGES') -ne '3' -or (Parameter $generator 'N_PTS') -ne '16' -or (Parameter $generator 'RC_PRECOMP_VERSION') -ne '1' -or (Parameter $generator 'DC_AREA_VERSION') -ne '1'){throw "Unexpected AWG area width: $awg"}
 $clock=$sum.SelectSingleNode("PORTS/PORT[@NAME='aclk']")
 if($clock.CLKFREQUENCY -ne '300000000' -or
    $clock.SIGNAME -ne $generator.SelectSingleNode("PORTS/PORT[@NAME='aclk']").SIGNAME){throw "Unexpected AWG/sum clock: $awg"}
 Check-Link $sum 's0_axis_tdata' "axis_awg_tuning_v4_$awg" 'm_axis_tdata'
 Check-Link $sum 'm_axis_tdata' "axis_register_slice_$slice" 's_axis_tdata'
 if($rf -ge 0){Check-Link $sum 's1_axis_tdata' "axis_signal_gen_v6_$rf" 'm_axis_tdata'}
 else {Check-Link $sum 's1_axis_tdata' 'sum_zero_word' 'dout'}
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive=[IO.Compression.ZipFile]::OpenRead("$Build/bitstream.xsa")
$embedded=[ordered]@{}
try {
 foreach($pair in @(@('bitstream.bit','bitstream.bit'),@('bitstream.hwh','d_1.hwh'))){
  $entries=@($archive.Entries|Where-Object {$_.Name -eq $pair[1]})
  if($entries.Count -ne 1){throw "Missing/ambiguous XSA member: $($pair[1])"}
  $stream=$entries[0].Open();$sha=[Security.Cryptography.SHA256]::Create()
  try {$digest=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','')}
  finally {$stream.Dispose();$sha.Dispose()}
  if($digest -ne (File-Hash "$Build/$($pair[0])")){throw "XSA/file mismatch: $($pair[0])"}
  $embedded[$pair[0]]=$digest
 }
} finally {$archive.Dispose()}
$artifacts=[ordered]@{}
foreach($file in 'bitstream.bit','bitstream.hwh','bitstream.xsa'){
 $item=Get-Item -LiteralPath "$Build/$file"
 $artifacts[$file]=[ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(File-Hash $item.FullName)}
}
[ordered]@{passed=$true;checked=(Get-Date -Format o);output_sum_blocks=7;awg_blocks=7;tproc_vlnv='QICK:QICK:axis_tproc64x32_x8:2.0';set_ramp_common_cycles=7;awg_delay_cycles=6;pipeline_cycles=2;clock_hz=300000000;embedded_matches=$embedded;artifacts=$artifacts;deployed=$false;python_v6_timing_profile=$false} | ConvertTo-Json -Depth 6 | Set-Content "$Build/candidate_manifest.json" -Encoding UTF8
Write-Output 'V6_CANDIDATE_ARTIFACTS_PASS_NOT_DEPLOYED'
