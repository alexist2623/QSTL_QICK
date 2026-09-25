
// Program

  regwi 3, $14, 1790;                           //freq = 1790
  regwi 3, $15, 0;                              //phase = 0
  regwi 3, $16, 1228;                           //gain = 1228
  regwi 3, $17, 0;                              //reserved = 0
  regwi 3, $18, 16777217;                       //control = 16777217
  synci 256;
  regwi 3, $19, 0;                              //t = 0
  set 3, 3, $14, $15, $16, $17, $18, $19;       //ch = 7, pulse @t = $19
  waiti 0, 300;
  end ;