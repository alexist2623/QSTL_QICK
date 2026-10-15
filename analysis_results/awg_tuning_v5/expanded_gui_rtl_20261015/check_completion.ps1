$ErrorActionPreference = 'Stop'
$out = Join-Path $PSScriptRoot 'controller_process_check.json'
if (Test-Path -LiteralPath $out) { throw 'Preserve previous completion evidence' }
$observed = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and (
        ($_.Name -match '^(python|pythonw|powershell|pwsh|cmd|xsim|xsimk)\.exe$' -and
         $_.CommandLine -match 'expanded_gui_rtl_20261015[\\/](matrix21|composite7|compiler17)[\\/]') -or
        ($_.Name -match '^(xsim|xsimk)\.exe$' -and
         $_.CommandLine -match 'a5(matrix1|composite1|compiler1|compiler2)')
    )
} | Select-Object ProcessId, ParentProcessId, Name, CommandLine, CreationDate)
$allXsim = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(xsim|xsimk)\.exe$'
} | Select-Object ProcessId, ParentProcessId, Name, CommandLine, CreationDate)
$branches = [ordered]@{}
foreach ($repo in @('C:/GIT_Workspace/QSTL_QICK', 'C:/GIT_Workspace/PulseGenerator')) {
    $branches[$repo] = (& git -C $repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Git branch inspection failed' }
}
$automations = [ordered]@{}
foreach ($id in @('awg-v3', 'awg-v4-timing', 'awg-v5-rtl')) {
    $path = "C:/Users/Measurement2/.codex/automations/$id/automation.toml"
    $content = Get-Content -LiteralPath $path -Raw
    $match = [regex]::Match($content, '(?m)^status\s*=\s*"([^"]+)"')
    if (-not $match.Success) { throw "Missing automation status: $id" }
    $automations[$id] = $match.Groups[1].Value
}
$result = [ordered]@{
    checked_at = (Get-Date).ToString('o')
    scope = 'Matrix21, composite7, compiler17 controllers and their xsim processes; identity uses name, command line, and creation time.'
    known_controller_pids_at_launch = @(63668, 88956, 104060)
    active_relevant_processes = $observed
    all_xsim_processes = $allXsim
    all_relevant_controllers_and_xsim_ended = ($observed.Count -eq 0 -and $allXsim.Count -eq 0)
    branches = $branches
    automation_status = $automations
}
if (-not $result.all_relevant_controllers_and_xsim_ended) { throw 'A relevant controller or simulator is still active' }
if (@($branches.Values | Where-Object { $_ -ne 'awg_tuning_v4' }).Count -ne 0) { throw 'Unexpected branch' }
if (@($automations.Values | Where-Object { $_ -ne 'PAUSED' }).Count -ne 0) { throw 'Unexpected automation state' }
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding UTF8
$result | ConvertTo-Json -Depth 8
