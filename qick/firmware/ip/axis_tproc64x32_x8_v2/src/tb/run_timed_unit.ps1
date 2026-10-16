param(
    [Parameter(Mandatory=$true)][string]$BuildDir,
    [string]$VivadoRoot='F:/Xilinx/Vivado/2023.1'
)
$ErrorActionPreference='Stop'
$ipRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$v1Root=[System.IO.Path]::GetFullPath((Join-Path $ipRoot '../axis_tproc64x32_x8_v1'))
$resolvedBuild=[System.IO.Path]::GetFullPath($BuildDir)
if(-not $resolvedBuild.StartsWith('F:\Vivado_Output\a6',[System.StringComparison]::OrdinalIgnoreCase)){
    throw 'Use a fresh F:/Vivado_Output/a6* directory for isolated simulation.'
}
if(Test-Path -LiteralPath $resolvedBuild){throw 'Build directory already exists; preserve prior evidence and use a fresh directory.'}
New-Item -ItemType Directory -Path $resolvedBuild | Out-Null
$sourceFiles=@(
    "$ipRoot/src/fifo/bram_simple_dp.vhd", "$ipRoot/src/fifo/fifo.vhd",
    "$ipRoot/src/timed_ictrl.vhd", "$PSScriptRoot/tb_timed_ictrl_v2.sv",
    "$v1Root/src/timed_ictrl.vhd", "$PSScriptRoot/run_timed_unit.ps1"
)
$sourceBefore=@($sourceFiles | ForEach-Object {
    [pscustomobject]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLower()}
})
$sourceBefore | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$resolvedBuild/source_before.json" -Encoding UTF8
$reference=[System.IO.File]::ReadAllText("$v1Root/src/timed_ictrl.vhd").Replace('timed_ictrl','timed_ictrl_v1_reference')
[System.IO.File]::WriteAllText("$resolvedBuild/timed_ictrl_v1_reference.vhd",$reference,[System.Text.Encoding]::ASCII)
"run all`nquit" | Set-Content -LiteralPath "$resolvedBuild/run_all.tcl" -Encoding ASCII
function Invoke-XsimTool([string]$Name,[string[]]$ToolArguments,[string]$LogName){
    & "$VivadoRoot/bin/$Name.bat" @ToolArguments *> "$resolvedBuild/$LogName"
    if($LASTEXITCODE -ne 0){throw "$Name failed with exit $LASTEXITCODE; see $resolvedBuild/$LogName"}
}
$result=[ordered]@{complete=$false;passed=$false;build=$resolvedBuild;error=$null}
Push-Location -LiteralPath $resolvedBuild
try {
    Invoke-XsimTool 'xvhdl' @('--relax','-work','xil_defaultlib',"$ipRoot/src/fifo/bram_simple_dp.vhd","$ipRoot/src/fifo/fifo.vhd","$ipRoot/src/timed_ictrl.vhd","$resolvedBuild/timed_ictrl_v1_reference.vhd") 'compile_vhdl.log'
    Invoke-XsimTool 'xvlog' @('--sv','-work','xil_defaultlib',"$PSScriptRoot/tb_timed_ictrl_v2.sv") 'compile_sv.log'
    Invoke-XsimTool 'xelab' @('--debug','typical','--relax','--mt','2','xil_defaultlib.tb_timed_ictrl_v2','-s','timed_v2_unit') 'elaborate.log'
    Invoke-XsimTool 'xsim' @('timed_v2_unit','-tclbatch','run_all.tcl','-log','simulation.log') 'xsim_console.log'
    $simText=[System.IO.File]::ReadAllText("$resolvedBuild/simulation.log")
    if($simText -notmatch 'TIMED_V2_PASS scenarios=(\d+) outputs=(\d+) checked_cycles=(\d+)'){
        throw 'Simulation did not reach the required PASS marker.'
    }
    $result.scenarios=[int]$Matches[1];$result.outputs=[int]$Matches[2];$result.checked_cycles=[int]$Matches[3]
    $sourceAfter=@($sourceFiles | ForEach-Object {
        [pscustomobject]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLower()}
    })
    $sourceAfter | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$resolvedBuild/source_after.json" -Encoding UTF8
    if(($sourceBefore | ConvertTo-Json -Compress) -cne ($sourceAfter | ConvertTo-Json -Compress)){
        throw 'Simulation sources changed during the run.'
    }
    $result.passed=$true
    $result.complete=$true
} catch {
    $result.error=$_.Exception.Message
    throw
} finally {
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$resolvedBuild/result.json" -Encoding UTF8
    Pop-Location
}
$result | ConvertTo-Json -Depth 6
