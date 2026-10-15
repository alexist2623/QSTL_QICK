# Exercise the report gate only. This never launches Vivado or changes reports.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/../..").Path
$gate="$repo/qick/firmware/projects/qstl_awg_v5/validate_routed.ps1"
$root='F:/Vivado_Output/a5gatecases2'
if(Test-Path $root){throw 'Fresh parser-test evidence required'}
New-Item -ItemType Directory $root|Out-Null
$cases=@('known_v4_pass','negative_setup','negative_hold','negative_tns','negative_ths','pulse_width','bus_skew','missing_skew','route_error')
$results=@()
foreach($name in $cases){
 $folder=Join-Path $root $name
 New-Item -ItemType Directory $folder|Out-Null
 foreach($file in 'build_result.txt','timing_summary_postroute.rpt','bus_skew_postroute.rpt','route_status_postroute.rpt'){
  Copy-Item -LiteralPath "F:/Vivado_Output/a4full2/$file" -Destination "$folder/$file"
 }
 $target="$folder/build_result.txt"
 $text=Get-Content $target -Raw
 switch($name){
  negative_setup {$text=[regex]::Replace($text,'(?m)^setup_wns_ns=.*$','setup_wns_ns=-0.000001')}
  negative_hold {$text=[regex]::Replace($text,'(?m)^hold_whs_ns=.*$','hold_whs_ns=-0.000001')}
  negative_tns {$text=[regex]::Replace($text,'(?m)^setup_tns_ns=.*$','setup_tns_ns=-0.001')}
  negative_ths {$text=[regex]::Replace($text,'(?m)^hold_ths_ns=.*$','hold_ths_ns=-0.001')}
  pulse_width {
   $target="$folder/timing_summary_postroute.rpt";$text=Get-Content $target -Raw
   $pattern='(?m)^\s*WNS\(ns\)[^\r\n]*\r?\n[^\r\n]*\r?\n([^\r\n]+)'
   $match=[regex]::Match($text,$pattern);$columns=$match.Groups[1].Value.Trim() -split '\s+'
   $columns[8]='-0.001';$columns[9]='-0.001';$columns[10]='1'
   $g=$match.Groups[1];$text=$text.Substring(0,$g.Index)+($columns -join ' ')+$text.Substring($g.Index+$g.Length)
  }
  bus_skew {$target="$folder/bus_skew_postroute.rpt";$text=(Get-Content $target -Raw).Replace('Slack (MET)','Slack (VIOLATED)')}
  missing_skew {$target="$folder/bus_skew_postroute.rpt";$text='No paths reported'}
  route_error {$target="$folder/route_status_postroute.rpt";$text=[regex]::Replace((Get-Content $target -Raw),'(# of nets with routing errors\.+\s*:)\s*0\s*:','$1 1 :')}
 }
 [IO.File]::WriteAllText($target,$text)
 $child=Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$gate,'-Build',$folder) -WorkingDirectory $repo -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$folder/gate.log" -RedirectStandardError "$folder/gate.stderr.log"
 $code=$child.ExitCode;$expected=($name -eq 'known_v4_pass')
 if(($code -eq 0) -ne $expected){throw "Incorrect routed-gate decision: $name exit=$code"}
 $results+= [ordered]@{case=$name;exit_code=$code;expected_pass=$expected;correct=$true;log="$folder/gate.log"}
}
[ordered]@{passed=$true;scope='Parser/gate tests using copied v4 reports; not v5 timing signoff';cases=$results;gate_sha256=(Get-FileHash $gate).Hash} | ConvertTo-Json -Depth 6 | Set-Content "$PSScriptRoot/routed_gate_tests.json" -Encoding UTF8
Write-Output 'ROUTED_GATE_TESTS_PASS 9/9'
