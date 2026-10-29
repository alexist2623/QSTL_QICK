param(
 [Parameter(Mandatory=$true)][string]$Build,
 [Parameter(Mandatory=$true)][string]$Fixture,
 [string]$VivadoRoot='F:/Xilinx/Vivado/2023.1'
)
$ErrorActionPreference='Stop'
$repo=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../..'))
$buildPath=[System.IO.Path]::GetFullPath($Build)
$fixturePath=(Resolve-Path -LiteralPath $Fixture).Path.Replace('\','/')
if(-not $buildPath.StartsWith('F:\Vivado_Output\a7',[System.StringComparison]::OrdinalIgnoreCase)){
 throw 'Use a fresh F:/Vivado_Output/a7* build directory.'
}
if(Test-Path -LiteralPath $buildPath){throw 'Build directory exists; preserve previous evidence.'}
New-Item -ItemType Directory -Path $buildPath | Out-Null
$tp="$repo/qick/firmware/ip/axis_tproc64x32_x8_v2/src"
$vhdlFiles=@(
 "$tp/fifo/bram_simple_dp.vhd", "$tp/fifo/fifo.vhd", "$tp/alu/math.vhd", "$tp/alu/bitw.vhd",
 "$tp/regfile/regfile.vhd", "$tp/regfile/regfile_8p.vhd", "$tp/cond.vhd", "$tp/s_axis_read.vhd",
 "$tp/stack.vhd", "$tp/synchronizer_n.vhd", "$tp/timed_ictrl.vhd"
)
$vlogFiles=@("$tp/tproc64x32_x8.v","$tp/ctrl.sv","$tp/alu/alu.v",
 "$repo/qick/firmware/ip/axis_tmux_v1/src/tmux.sv","$repo/qick/firmware/ip/axis_tmux_v1/src/axis_tmux_v1.sv")
$namespaced='F:/Vivado_Output/a3sim1/namespaced'
$ddsFiles=@(Get-ChildItem -LiteralPath $namespaced -File | Where-Object Name -Match '^0(4[1-9]|5[0-2])_' | Sort-Object Name)
if($ddsFiles.Count -ne 12){throw 'Expected all 12 namespaced production SGv6/vendor DDS sources.'}
foreach($file in $ddsFiles){
 if($file.Extension -eq '.vhd'){$vhdlFiles+=$file.FullName}else{$vlogFiles+=$file.FullName}
}
$vlogFiles+=@(Get-ChildItem "$repo/qick/firmware/ip/axis_awg_tuning_v7/src" -Filter '*.sv' | Sort-Object Name | ForEach-Object FullName)
$vlogFiles+=@("$repo/qick/firmware/ip/axis_output_sum_v7/src/axis_output_sum_v7.sv",
 "$PSScriptRoot/cpu_native_pair.sv","$PSScriptRoot/tb_cpu_tmux_v7.sv","$VivadoRoot/data/verilog/src/glbl.v")
$sources=@($vhdlFiles+$vlogFiles+@("$PSScriptRoot/run_cpu_tmux.ps1","$PSScriptRoot/prepare_cpu_fixture.py","$PSScriptRoot/plot_required_waveforms.py"))
$sources+=@(Get-ChildItem -LiteralPath $fixturePath -File | ForEach-Object FullName)
foreach($name in @('fixture_meta.hex','pmem.hex','dmem.hex','expected_events.hex')){
 Copy-Item -LiteralPath "$fixturePath/$name" -Destination "$buildPath/$name"
 if((Get-FileHash -LiteralPath "$fixturePath/$name").Hash -ne (Get-FileHash -LiteralPath "$buildPath/$name").Hash){throw "Fixture copy hash mismatch: $name"}
 $sources+="$buildPath/$name"
}
function Get-SourceHashes {
 return @($sources | ForEach-Object { [pscustomobject]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLower()} })
}
$before=Get-SourceHashes
$before | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$buildPath/source_before.json" -Encoding UTF8
@($vhdlFiles | ForEach-Object {'vhdl xil_defaultlib "'+$_.Replace('\','/')+'"'})+@('nosort') | Set-Content -LiteralPath "$buildPath/sources_vhdl.prj" -Encoding ascii
@($vlogFiles | ForEach-Object {'sv xil_defaultlib "'+$_.Replace('\','/')+'"'})+@('nosort') | Set-Content -LiteralPath "$buildPath/sources_vlog.prj" -Encoding ascii
$result=[ordered]@{complete=$false;passed=$false;build=$buildPath;fixture=$fixturePath;scope='Full tProcessor CPU core, PMEM/DMEM, TMUX, production AWG/DDS/sum; AXI host wrapper excluded';error=$null}
function Invoke-SimTool([string]$Name,[string[]]$Arguments,[string]$Log){
 & "$VivadoRoot/bin/$Name.bat" @Arguments *> "$buildPath/$Log"
 if($LASTEXITCODE -ne 0){throw "$Name failed with exit $LASTEXITCODE; see $Log"}
}
Push-Location -LiteralPath $buildPath
try {
 Invoke-SimTool 'xvhdl' @('--relax','-prj','sources_vhdl.prj') 'compile_vhdl.log'
 Invoke-SimTool 'xvlog' @('--relax','-prj','sources_vlog.prj') 'compile_verilog.log'
 Invoke-SimTool 'xelab' @('--relax','--O2','--mt','4','-L','xil_defaultlib','-L','dds_compiler_v6_0_22','-L','unisims_ver','-L','unimacro_ver','-L','secureip','xil_defaultlib.tb_cpu_tmux_v7','xil_defaultlib.glbl','--snapshot','cpu_tmux_v7') 'elaborate.log'
 Invoke-SimTool 'xsim' @('cpu_tmux_v7','-runall') 'run_console.log'
 $log=[System.IO.File]::ReadAllText("$buildPath/run_console.log")
 if($log -notmatch 'V7_CPU_TMUX_PASS cases=49 pair_cases=147 commands=762 rf_cases=9' -or $log -match 'Fatal:|ERROR:'){throw 'Simulation did not meet full CPU coverage gates.'}
 $required=@('rise1_hold1_fall1','rise1_hold2_fall1','rise2_hold1_fall2')
 foreach($name in $required){if(-not $log.Contains("V7_REQUIRED_CASE_PASS $name pairs=3 scalar_assertions=pass")){throw "Required case missing: $name"}}
 $after=Get-SourceHashes
 $after | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$buildPath/source_after.json" -Encoding UTF8
 if(($before | ConvertTo-Json -Compress) -cne ($after | ConvertTo-Json -Compress)){throw 'Source or fixture changed during simulation.'}
 $result.required_cases=$required;$result.pair_cases=147;$result.commands=762;$result.ordinary_rf_cases=9
 $result.passed=$true;$result.complete=$true
} catch {
 $result.error=$_.Exception.Message
 throw
} finally {
 $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$buildPath/result.json" -Encoding UTF8
 Pop-Location
}
$result | ConvertTo-Json -Depth 6
