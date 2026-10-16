param([Parameter(Mandatory=$true)][string]$Build)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Build){throw "Fresh output required: $Build"}
New-Item -ItemType Directory -Path $Build | Out-Null
$source=(Resolve-Path "$PSScriptRoot/../src/axis_output_sum_v3.sv").Path
$bench=(Resolve-Path "$PSScriptRoot/tb_output_sum.sv").Path
$h=[ordered]@{};foreach($p in $source,$bench){$h[$p]=(Get-FileHash -LiteralPath $p).Hash}
$h | ConvertTo-Json | Set-Content "$Build/source_hashes.json" -Encoding UTF8
Push-Location -LiteralPath $Build
try {
 & F:/Xilinx/Vivado/2023.1/bin/xvlog.bat -sv $source $bench *> compile_console.log
 if($LASTEXITCODE){throw 'xvlog failed'}
 & F:/Xilinx/Vivado/2023.1/bin/xelab.bat tb_output_sum -s output_sum *> elaborate_console.log
 if($LASTEXITCODE){throw 'xelab failed'}
 & F:/Xilinx/Vivado/2023.1/bin/xsim.bat output_sum -runall *> run_console.log
 $code=$LASTEXITCODE;$log=Get-Content run_console.log -Raw
 $passed=($code -eq 0 -and $log.Contains('V6_OUTPUT_SUM_PASS') -and $log -notmatch 'Fatal:|ERROR:')
 [ordered]@{passed=$passed;exit_code=$code;build=$Build;finished=(Get-Date -Format o)} | ConvertTo-Json | Set-Content result.json -Encoding UTF8
 if(!$passed){throw 'v6 sum unit test failed'}
 $log -split "`n" | Where-Object {$_ -match 'V6_OUTPUT_SUM_PASS'}
} finally {Pop-Location}
