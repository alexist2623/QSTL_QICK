
// Program

  regwi 0, $22, 0;                              //freq = 0
  regwi 0, $23, 0;                              //phase = 0
  regwi 0, $25, 0;                              //gain = 0
  regwi 0, $26, 589827;                         //phrst| stdysel | mode | | outsel = 0b01001 | length = 3 
  regwi 0, $27, 100;                            //t = 100
  set 0, 0, $22, $23, $0, $25, $26, $27;        //ch = 0, pulse @t = $27
  regwi 1, $16, 0;                              //freq = 0
  regwi 1, $17, 0;                              //phase = 0
  regwi 1, $19, 0;                              //gain = 0
  regwi 1, $20, 589827;                         //phrst| stdysel | mode | | outsel = 0b01001 | length = 3 
  regwi 1, $21, 104;                            //t = 104
  set 1, 1, $16, $17, $0, $19, $20, $21;        //ch = 2, pulse @t = $21
  waiti 0, 200;
  end ;