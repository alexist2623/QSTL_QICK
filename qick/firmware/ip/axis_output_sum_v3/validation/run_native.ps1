param([Parameter(Mandatory=$true)][string]$Build,
      [ValidateSet('tb_native_alignment')][string]$Top='tb_native_alignment')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../../../../..").Path
$vivado='F:/Xilinx/Vivado/2023.1/bin'
if(Test-Path -LiteralPath $Build){throw "Fresh build required: $Build"}
New-Item -ItemType Directory -Path $Build | Out-Null
$namespaced='F:/Vivado_Output/a3sim1/namespaced'
$files=@(Get-ChildItem $namespaced -File | Where-Object Name -Match '^0(4[1-9]|5[0-2])_')
$vlog=@();$vhdl=@();$hashes=[ordered]@{}
foreach($file in $files){
 $hashes[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName).Hash
 if($file.Extension -eq '.vhd'){$vhdl+='vhdl xil_defaultlib "'+$file.FullName.Replace('\','/')+'"'}
 else{$vlog+='sv xil_defaultlib "'+$file.FullName.Replace('\','/')+'"'}
}
$rtl=@(Get-ChildItem "$repo/qick/firmware/ip/axis_awg_tuning_v4/src" -Filter '*.sv')
$rtl+=Get-Item "$PSScriptRoot/../src/axis_output_sum_v3.sv","$PSScriptRoot/tb_native_alignment.sv",'F:/Xilinx/Vivado/2023.1/data/verilog/src/glbl.v'
foreach($file in $rtl){
 $hashes[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName).Hash
 $vlog+='sv xil_defaultlib "'+$file.FullName.Replace('\','/')+'"'
}
($vlog+@('nosort')) | Set-Content "$Build/sources_vlog.prj" -Encoding ascii
($vhdl+@('nosort')) | Set-Content "$Build/sources_vhdl.prj" -Encoding ascii
$hashes | ConvertTo-Json | Set-Content "$Build/source_hashes.json" -Encoding UTF8
Push-Location -LiteralPath $Build
try {
 & "$vivado/xvlog.bat" --relax -prj sources_vlog.prj *> compile_console.log
 if($LASTEXITCODE){throw 'xvlog failed'}
 & "$vivado/xvhdl.bat" --relax -prj sources_vhdl.prj *> vhdl_console.log
 if($LASTEXITCODE){throw 'xvhdl failed'}
 & "$vivado/xelab.bat" --relax --O2 --mt 4 -L xil_defaultlib -L dds_compiler_v6_0_22 -L unisims_ver -L unimacro_ver -L secureip "xil_defaultlib.$Top" xil_defaultlib.glbl --snapshot native *> elaborate_console.log
 if($LASTEXITCODE){throw 'xelab failed'}
 & "$vivado/xsim.bat" native -runall *> run_console.log
 $code=$LASTEXITCODE
 $log=Get-Content run_console.log -Raw
 $marker='V6_NATIVE_ALIGNMENT_PASS'
 $pass=($code -eq 0 -and $log.Contains($marker) -and $log -notmatch 'Fatal:|ERROR:')
 [ordered]@{passed=$pass;exit_code=$code;build=$Build;top=$Top;finished=(Get-Date -Format o)} | ConvertTo-Json | Set-Content result.json -Encoding UTF8
 if(!$pass){throw 'Native alignment failed; see run_console.log'}
 $log -split "`n" | Where-Object {$_ -match $marker}
} finally {Pop-Location}
