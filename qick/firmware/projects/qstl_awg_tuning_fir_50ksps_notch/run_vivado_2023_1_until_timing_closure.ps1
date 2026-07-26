# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
#
# Run independent Vivado 2023.1 clean builds until timing closes or the
# requested attempt limit is reached. Each attempt starts from synthesis.

[CmdletBinding()]
param(
    [ValidateRange(1, 10)]
    [int]$MaxAttempts = 10,

    [ValidateRange(1, 10)]
    [int]$StartAttempt = 1,

    [string]$OutputRoot = "C:\JeonghyunPark\Workspace\Vivado_Output",

    [ValidatePattern("^[A-Za-z0-9_-]+$")]
    [string]$OutputPrefix = "q50tc",

    [string]$VivadoBat = "C:\Xilinx\Vivado\2023.1\bin\vivado.bat"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectDir = $PSScriptRoot
$buildTcl = Join-Path $projectDir "build_vivado_2023_1_run5.tcl"
$retryTcl = Join-Path $projectDir "resume_vivado_2023_1_impl_run5.tcl"
$scratchDir = "C:\VivadoTemp"
$summaryCsv = Join-Path $OutputRoot "$($OutputPrefix)_summary.csv"
$summaryMarkdown = Join-Path $OutputRoot "$($OutputPrefix)_summary.md"
$projectName = "qstl_awg_tuning_fir_50ksps_notch"

foreach ($requiredPath in @($VivadoBat, $buildTcl, $retryTcl)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file was not found: $requiredPath"
    }
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
New-Item -ItemType Directory -Force -Path $scratchDir | Out-Null
$env:TEMP = $scratchDir
$env:TMP = $scratchDir

# Existing directories are never deleted or reused. Refusing them guarantees
# that every reported attempt is a clean synthesis and implementation.
$attemptDirectories = for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    Join-Path $OutputRoot ("{0}{1:d2}" -f $OutputPrefix, $attempt)
}
if ($StartAttempt -gt $MaxAttempts) {
    throw "StartAttempt ($StartAttempt) cannot be greater than MaxAttempts ($MaxAttempts)."
}

foreach ($attemptDirectory in $attemptDirectories[($StartAttempt - 1)..($MaxAttempts - 1)]) {
    if (Test-Path -LiteralPath $attemptDirectory) {
        throw "Clean-build directory already exists; refusing to reuse it: $attemptDirectory"
    }
}

function Invoke-VivadoBatch {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceTcl,

        [Parameter(Mandatory = $true)]
        [string]$OutputDirectory,

        [Parameter(Mandatory = $true)]
        [string]$LogPath,

        [Parameter(Mandatory = $true)]
        [string]$JournalPath
    )

    & $VivadoBat `
        -mode batch `
        -notrace `
        -log $LogPath `
        -journal $JournalPath `
        -source $SourceTcl `
        -tclargs $OutputDirectory 2>&1 |
        ForEach-Object { Write-Host $_ }
    $vivadoExitCode = $LASTEXITCODE
    return $vivadoExitCode
}

function Read-KeyValueFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $separator = $line.IndexOf("=")
        if ($separator -gt 0) {
            $key = $line.Substring(0, $separator)
            $value = $line.Substring($separator + 1)
            $values[$key] = $value
        }
    }
    return $values
}

function Get-ValueOrDefault {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Values,

        [Parameter(Mandatory = $true)]
        [string]$Key,

        [string]$Default = ""
    )

    if ($Values.ContainsKey($Key)) {
        return [string]$Values[$Key]
    }
    return $Default
}

function Write-AttemptSummary {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.Generic.List[object]]$Rows
    )

    $Rows | Export-Csv -LiteralPath $summaryCsv -NoTypeInformation -Encoding UTF8

    $markdown = [System.Collections.Generic.List[string]]::new()
    $markdown.Add("# Vivado 2023.1 clean-build timing attempts")
    $markdown.Add("")
    $markdown.Add("- Project: ``$projectName``")
    $markdown.Add("- Vivado: 2023.1")
    $markdown.Add("- Jobs and ``general.maxThreads``: 5")
    $markdown.Add("- Synthesis strategy: Vivado Synthesis Defaults")
    $markdown.Add("- Implementation strategy: Vivado Implementation Defaults")
    $markdown.Add("- Manual placement/routing: disabled")
    $markdown.Add("- Git commit: ``$(git -C (Resolve-Path (Join-Path $projectDir '..\..\..\..')) rev-parse HEAD)``")
    $markdown.Add("")
    $markdown.Add("| Attempt | Full build | Impl retry | Setup WNS (ns) | Setup TNS (ns) | Hold WHS (ns) | Hold THS (ns) | Closed |")
    $markdown.Add("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |")
    foreach ($row in $Rows) {
        $markdown.Add(
            "| $($row.attempt) | $($row.full_build_exit_code) | $($row.impl_retry_exit_code) | " +
            "$($row.setup_wns_ns) | $($row.setup_tns_ns) | $($row.hold_whs_ns) | " +
            "$($row.hold_ths_ns) | $($row.timing_closed) |"
        )
    }
    $markdown.Add("")
    $markdown.Add("Each output directory is independent and begins with synthesis.")
    $markdown | Set-Content -LiteralPath $summaryMarkdown -Encoding UTF8
}

$rows = [System.Collections.Generic.List[object]]::new()
$timingClosed = $false

for ($attempt = 1; $attempt -lt $StartAttempt; $attempt++) {
    $outputDirectory = $attemptDirectories[$attempt - 1]
    $result = Read-KeyValueFile (Join-Path $outputDirectory "build_result.txt")
    if ($result.Count -eq 0) {
        throw "Cannot resume: completed result is missing for attempt $attempt at $outputDirectory"
    }
    $rows.Add([pscustomobject]@{
        attempt = $attempt
        output_directory = $outputDirectory
        full_build_exit_code = "completed"
        impl_retry_exit_code = ""
        synthesis_status = Get-ValueOrDefault $result "synthesis_status" "NO_RESULT"
        implementation_status = Get-ValueOrDefault $result "implementation_status" "NO_RESULT"
        setup_wns_ns = Get-ValueOrDefault $result "setup_wns_ns" ""
        setup_tns_ns = Get-ValueOrDefault $result "setup_tns_ns" ""
        hold_whs_ns = Get-ValueOrDefault $result "hold_whs_ns" ""
        hold_ths_ns = Get-ValueOrDefault $result "hold_ths_ns" ""
        timing_closed = Get-ValueOrDefault $result "timing_closed" "UNKNOWN"
    })
}
Write-AttemptSummary -Rows $rows

for ($attempt = $StartAttempt; $attempt -le $MaxAttempts; $attempt++) {
    $outputDirectory = $attemptDirectories[$attempt - 1]
    $attemptTag = "{0}{1:d2}" -f $OutputPrefix, $attempt
    $fullLog = Join-Path $OutputRoot "$($attemptTag)_vivado.log"
    $fullJournal = Join-Path $OutputRoot "$($attemptTag)_vivado.jou"
    $retryLog = Join-Path $OutputRoot "$($attemptTag)_impl_retry.log"
    $retryJournal = Join-Path $OutputRoot "$($attemptTag)_impl_retry.jou"

    Write-Host ""
    Write-Host "===== CLEAN BUILD ATTEMPT $attempt OF ${MaxAttempts}: $outputDirectory ====="
    $fullExitCode = Invoke-VivadoBatch `
        -SourceTcl $buildTcl `
        -OutputDirectory $outputDirectory `
        -LogPath $fullLog `
        -JournalPath $fullJournal

    $retryExitCode = ""
    if ($fullExitCode -eq 3) {
        $projectFile = Join-Path $outputDirectory "$projectName.xpr"
        if (Test-Path -LiteralPath $projectFile) {
            Write-Host "Implementation stopped; retrying impl_1 without reusing placement or routing."
            $retryExitCode = Invoke-VivadoBatch `
                -SourceTcl $retryTcl `
                -OutputDirectory $outputDirectory `
                -LogPath $retryLog `
                -JournalPath $retryJournal
        }
    }

    $result = Read-KeyValueFile (Join-Path $outputDirectory "build_result.txt")
    $closed = Get-ValueOrDefault $result "timing_closed" "UNKNOWN"
    $row = [pscustomobject]@{
        attempt = $attempt
        output_directory = $outputDirectory
        full_build_exit_code = $fullExitCode
        impl_retry_exit_code = $retryExitCode
        synthesis_status = Get-ValueOrDefault $result "synthesis_status" "NO_RESULT"
        implementation_status = Get-ValueOrDefault $result "implementation_status" "NO_RESULT"
        setup_wns_ns = Get-ValueOrDefault $result "setup_wns_ns" ""
        setup_tns_ns = Get-ValueOrDefault $result "setup_tns_ns" ""
        hold_whs_ns = Get-ValueOrDefault $result "hold_whs_ns" ""
        hold_ths_ns = Get-ValueOrDefault $result "hold_ths_ns" ""
        timing_closed = $closed
    }
    $rows.Add($row)
    Write-AttemptSummary -Rows $rows

    Write-Host (
        "ATTEMPT_RESULT attempt={0} full_exit={1} retry_exit={2} WNS={3} TNS={4} WHS={5} THS={6} closed={7}" -f `
            $attempt,
            $fullExitCode,
            $retryExitCode,
            $row.setup_wns_ns,
            $row.setup_tns_ns,
            $row.hold_whs_ns,
            $row.hold_ths_ns,
            $closed
    )

    if ($closed -eq "YES") {
        $timingClosed = $true
        Write-Host "TIMING_CLOSURE_ACHIEVED=$outputDirectory"
        break
    }
}

if (-not $timingClosed) {
    Write-Host "TIMING_CLOSURE_NOT_ACHIEVED_AFTER=$($rows.Count)"
}
Write-Host "SUMMARY_CSV=$summaryCsv"
Write-Host "SUMMARY_MARKDOWN=$summaryMarkdown"
