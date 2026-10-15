$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$rows=Import-Csv 'F:/Vivado_Output/a5ramp2/ramp_hold.csv'
$bmp=New-Object Drawing.Bitmap 1440,1050
$g=[Drawing.Graphics]::FromImage($bmp);$g.SmoothingMode='AntiAlias';$g.Clear([Drawing.Color]::White)
$font=New-Object Drawing.Font 'Segoe UI',12
$title=New-Object Drawing.Font 'Segoe UI',19,([Drawing.FontStyle]::Bold)
$small=New-Object Drawing.Font 'Segoe UI',10
$black=[Drawing.Brushes]::Black;$gray=New-Object Drawing.Pen ([Drawing.Color]::LightGray),1
$axis=New-Object Drawing.Pen ([Drawing.Color]::Gray),1
$g.DrawString('v5 actual RTL: AWG / RF latency matched at 31 clocks',$title,$black,35,20)
$g.DrawString('300 MHz | 10 us RAMP / HOLD / RAMP / HOLD | RF exactly spans the selected HOLD | pair 1, lane 0',$font,$black,35,60)
$g.DrawString('Direct generator commands; original 7-clock RAMP startup accounted for. No board measurement.',$small,$black,35,89)
$series=@(@('awg','AWG output',-500,4600,[Drawing.Color]::RoyalBlue),@('rf','RF output',-2500,2500,[Drawing.Color]::SeaGreen),@('sum','Saturated sum',-2500,7000,[Drawing.Color]::Firebrick))
for($col=0;$col -lt 2;$col++){
 $hold=$col+1;$data=@($rows|Where-Object hold -eq "$hold")
 $g.DrawString("RF on HOLD $hold",$title,$black,110+$col*700,126)
 for($r=0;$r -lt 3;$r++){
  $item=$series[$r];$left=100+$col*700;$top=185+$r*260;$w=590;$height=190
  $lo=[double]$item[2];$hi=[double]$item[3]
  $shade=New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(35,255,190,0))
  $shadeStart=if($hold -eq 1){10}else{30}
  $shadeX=$left+$shadeStart/40*$w
  $g.FillRectangle($shade,[single]$shadeX,[single]$top,[single]($w/4),[single]$height);$shade.Dispose()
  for($x=0;$x -le 40;$x+=10){$px=$left+$x/40*$w;$g.DrawLine($gray,[single]$px,[single]$top,[single]$px,[single]($top+$height));$g.DrawString("$x",$small,$black,[single]($px-8),[single]($top+$height+6))}
  $zero=$top+$hi/($hi-$lo)*$height
  $g.DrawLine($axis,[single]$left,[single]$zero,[single]($left+$w),[single]$zero)
  $g.DrawRectangle($axis,$left,$top,$w,$height)
  $g.DrawString($item[1]+' (DAC codes)',$font,$black,$left,$top-28)
  $g.DrawString("$hi",$small,$black,$left-55,$top-5);$g.DrawString('0',$small,$black,$left-25,[single]($zero-7));$g.DrawString("$lo",$small,$black,$left-55,$top+$height-10)
  $points=New-Object 'System.Collections.Generic.List[System.Drawing.PointF]'
  foreach($row in $data){
   $t=([int]$row.cycle-[int]$row.start-31)/300.0
   if($t -lt 0 -or $t -gt 40){continue}
   $hex=$row.($item[0]);$code=[Convert]::ToInt32($hex.Substring($hex.Length-4),16);if($code -ge 32768){$code-=65536}
   $points.Add([Drawing.PointF]::new([single]($left+$t/40*$w),[single]($top+($hi-$code)/($hi-$lo)*$height)))
  }
  $pen=New-Object Drawing.Pen $item[4],1.2
  $g.DrawLines($pen,$points.ToArray());$pen.Dispose()
  $g.DrawString('Time from RAMP start (us)',$small,$black,$left+190,$top+$height+29)
 }
}
$g.DrawString('PASS: 3 physical pairs; 2 selected HOLD cases; 288,000 flat-HOLD scalar checks; RF width = 3,000 clocks = 10 us.',$font,$black,35,1000)
$bmp.Save("$PSScriptRoot/native_ramp_hold.png",[Drawing.Imaging.ImageFormat]::Png)
$g.Dispose();$bmp.Dispose();$font.Dispose();$title.Dispose();$small.Dispose();$gray.Dispose();$axis.Dispose()
