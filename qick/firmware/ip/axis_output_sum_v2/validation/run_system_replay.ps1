param([Parameter(Mandatory=$true)][string]$CasePath,[Parameter(Mandatory=$true)][string]$Build)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../../../../..").Path.Replace('\','/')
$CasePath=(Resolve-Path -LiteralPath $CasePath).Path.Replace('\','/')
$Build=[IO.Path]::GetFullPath($Build).Replace('\','/')
$shared='F:/Vivado_Output/a3sim1/qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
$vivado='F:/Xilinx/Vivado/2023.1/bin'
if(Test-Path -LiteralPath $Build){throw "Fresh output required: $Build"}
New-Item -ItemType Directory -Path $Build,"$Build/xsim.dir" | Out-Null
# Reuse unchanged vendor/library compilation, but freshly compile the current
# AWG, Square, v5 sum, BD and all testbench checks. Never reuse a simulation PASS.
Copy-Item -LiteralPath "$shared/xsim.dir/xil_defaultlib" -Destination "$Build/xsim.dir/xil_defaultlib" -Recurse
Copy-Item -LiteralPath "$shared/xsim.ini" -Destination "$Build/xsim.ini"
foreach($file in Get-ChildItem -LiteralPath $CasePath -File){
 if($file.Extension -eq '.hex' -or $file.Name -in @('dmem.txt','program.asm','expected.json','rc_wrapper.v')){
  Copy-Item -LiteralPath $file.FullName -Destination "$Build/$($file.Name)"
 }
}
$bd=(Get-Content "$CasePath/rc_bd.v" -Raw).Replace('axis_output_sum_v1','axis_output_sum_v2')
[IO.File]::WriteAllText("$Build/rc_bd.v",$bd)
$tb=(Get-Content "$CasePath/tb_rc_gui.sv" -Raw).Replace("`r`n","`n").Replace($CasePath,$Build)
foreach($suffix in 4,5,6){
 $old="logic [255:0] sum_expected_$suffix=0;"
 if(!$tb.Contains($old)){throw "Missing sum oracle $suffix"}
 $tb=$tb.Replace($old,$old+"`nlogic [255:0] history_$suffix [0:12];`nlogic [12:0] history_valid_$suffix=0;")
 $tb=$tb.Replace("if(!resetn) sum_expected_$suffix=0;","if(!resetn) begin sum_expected_$suffix=0; history_valid_$suffix=0; end")
 $tb=$tb.Replace("dut.sim_bd_i.sum_$suffix.s0_axis_tvalid ? `$signed(dut.sim_bd_i.sum_$suffix.s0_axis_tdata[lane*16+:16])", "history_valid_$suffix[12] ? `$signed(history_$suffix[12][lane*16+:16])")
 $anchor="  #0.003;`n  if(cycle>20 && dut.sim_bd_i.sum_$suffix.m_axis_tdata!==sum_expected_$suffix)"
 # Source fixtures are LF; use LF explicitly for the independent FIFO oracle.
 if(!$tb.Contains($anchor)){throw "Missing oracle update anchor $suffix"}
 $update="  for(integer h=12;h>0;h=h-1) history_$suffix[h]=history_$suffix[h-1];`n  history_$suffix[0]=dut.sim_bd_i.sum_$suffix.s0_axis_tdata;`n  history_valid_$suffix={history_valid_$suffix[11:0],dut.sim_bd_i.sum_$suffix.s0_axis_tvalid};`n"
 $tb=$tb.Replace($anchor,$update+$anchor).Replace("v4 SUM mismatch suffix=$suffix","v5 SUM mismatch suffix=$suffix")
}
[IO.File]::WriteAllText("$Build/tb_rc_gui.sv",$tb)
$prj=(Get-Content "$CasePath/sources.prj" -Raw).Replace($CasePath,$Build).Replace('axis_output_sum_v1/src/axis_output_sum_v1.sv','axis_output_sum_v2/src/axis_output_sum_v2.sv')
[IO.File]::WriteAllText("$Build/sources.prj",$prj)
$hashes=[ordered]@{}
foreach($match in [regex]::Matches($prj,'"([^"]+)"')){
 $path=$match.Groups[1].Value;$hashes[$path]=(Get-FileHash -LiteralPath $path).Hash
}
foreach($name in 'pmem.hex','dmem.txt'){
 if((Get-FileHash "$Build/$name").Hash -ne (Get-FileHash "$CasePath/$name").Hash){throw "Changed fixture $name"}
 $hashes["$Build/$name"]=(Get-FileHash "$Build/$name").Hash
}
$hashes | ConvertTo-Json | Set-Content "$Build/source_hashes.json" -Encoding UTF8
$prepared=Get-Content "$CasePath/prepared.json" -Raw | ConvertFrom-Json
[ordered]@{source_case=$CasePath;input_policy='unchanged recorded GUI PMEM/DMEM; v4 RF advance retained';fresh_v5_simulation=$true;shots=$prepared.shots;cycles=$prepared.cycles} | ConvertTo-Json | Set-Content "$Build/fixture.json" -Encoding UTF8
$libs=@([regex]::Matches((Get-Content "$shared/elaborate.bat" -Raw),'-L (\w+)') | ForEach-Object {$_.Groups[1].Value} | Select-Object -Unique)
$libargs=@();foreach($lib in $libs){$libargs+=@('-L',$lib)}
Push-Location -LiteralPath $Build
try {
 & "$vivado/xvlog.bat" --relax -prj sources.prj *> compile_console.log
 if($LASTEXITCODE){throw 'xvlog failed'}
 & "$vivado/xelab.bat" --O2 --debug off --relax --mt 4 @libargs --snapshot v5_system xil_defaultlib.tb_rc_gui xil_defaultlib.glbl *> elaborate_console.log
 if($LASTEXITCODE){throw 'xelab failed'}
 @('v5_system','-runall',"-testplusarg `"CASE=$Build`"","-testplusarg `"OUT=$Build`"","-testplusarg `"CYCLES=$($prepared.cycles)`"") | Set-Content options.txt -Encoding ascii
 & "$vivado/xsim.bat" -f options.txt *> run_console.log
 $code=$LASTEXITCODE;$log=Get-Content run_console.log -Raw
 $pass=($code -eq 0 -and $log.Contains('RTL COMPLETE') -and $log -notmatch 'Fatal:|ERROR:' -and [regex]::Matches($log,'OUTPUT_SUM_RESULT').Count -eq 3)
 [ordered]@{passed=$pass;exit_code=$code;build=$Build;source_case=$CasePath;shots=$prepared.shots;finished=(Get-Date -Format o)} | ConvertTo-Json | Set-Content result.json -Encoding UTF8
 if(!$pass){throw 'System replay failed; see run_console.log'}
 $log -split "`n" | Where-Object {$_ -match 'RESULT|RTL COMPLETE'}
} finally {Pop-Location}
