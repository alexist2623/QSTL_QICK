
// Program

  synci 128;
  regwi 3, $14, 1790;                           //freq = 1790
  regwi 3, $15, 536870912;                      //phase = 536870912
  regwi 3, $16, 820;                            //gain = 820
  regwi 3, $17, 0;                              //reserved = 0
  regwi 3, $18, 16777217;                       //control = 16777217
  regwi 3, $19, 0;                              //t = 0
  set 3, 3, $14, $15, $16, $17, $18, $19;       //ch = 7, pulse @t = $19
  waiti 3, 32;
  end ;