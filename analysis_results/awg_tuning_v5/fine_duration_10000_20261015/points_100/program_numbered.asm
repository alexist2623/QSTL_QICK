   1  
   2  // Program
   3  
   4                              synci 200;
   5                              regwi 1, $10, 0;    //target = 0x00000000
   6                              regwi 1, $11, 0;    //reserved_start = 0x00000000
   7                              regwi 1, $12, 0;    //duration = 0x00000000
   8                              regwi 1, $13, 0;    //step = 0x00000000
   9                              regwi 1, $14, 19595264;//control = 0x012b0000
  10                              regwi 1, $15, 0;    //t = 0
  11                              set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
  12                              regwi 1, $26, 0;    //target = 0x00000000
  13                              regwi 1, $27, 0;    //reserved_start = 0x00000000
  14                              regwi 1, $28, 0;    //duration = 0x00000000
  15                              regwi 1, $29, 0;    //step = 0x00000000
  16                              regwi 1, $30, 19595264;//control = 0x012b0000
  17                              regwi 1, $31, 0;    //t = 0
  18                              set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
  19                              regwi 2, $16, 0;    //target = 0x00000000
  20                              regwi 2, $17, 0;    //reserved_start = 0x00000000
  21                              regwi 2, $18, 0;    //duration = 0x00000000
  22                              regwi 2, $19, 0;    //step = 0x00000000
  23                              regwi 2, $20, 19595264;//control = 0x012b0000
  24                              regwi 2, $21, 0;    //t = 0
  25                              set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
  26                              synci 100;
  27                              synci 384;
  28                              regwi 1, $10, 0;    //target = 0x00000000
  29                              regwi 1, $11, 0;    //reserved_start = 0x00000000
  30                              regwi 1, $12, 0;    //duration = 0x00000000
  31                              regwi 1, $13, 0;    //step = 0x00000000
  32                              regwi 1, $14, 16842752;//control = 0x01010000
  33                              regwi 1, $15, 0;    //t = 0
  34                              set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
  35                              regwi 1, $26, 0;    //target = 0x00000000
  36                              regwi 1, $27, 0;    //reserved_start = 0x00000000
  37                              regwi 1, $28, 0;    //duration = 0x00000000
  38                              regwi 1, $29, 0;    //step = 0x00000000
  39                              regwi 1, $30, 16842752;//control = 0x01010000
  40                              regwi 1, $31, 0;    //t = 0
  41                              set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
  42                              regwi 2, $16, 0;    //target = 0x00000000
  43                              regwi 2, $17, 0;    //reserved_start = 0x00000000
  44                              regwi 2, $18, 0;    //duration = 0x00000000
  45                              regwi 2, $19, 0;    //step = 0x00000000
  46                              regwi 2, $20, 16842752;//control = 0x01010000
  47                              regwi 2, $21, 0;    //t = 0
  48                              set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
  49                              synci 384;
  50                              regwi 1, $10, 0;    //target = 0x00000000
  51                              regwi 1, $11, 0;    //reserved_start = 0x00000000
  52                              regwi 1, $12, 0;    //duration = 0x00000000
  53                              regwi 1, $13, 0;    //step = 0x00000000
  54                              regwi 1, $14, 21954560;//control = 0x014f0000
  55                              regwi 1, $15, 0;    //t = 0
  56                              set 0, 1, $10, $11, $12, $13, $14, $15;//ch = 1, pulse @t = $15
  57                              regwi 1, $26, 0;    //target = 0x00000000
  58                              regwi 1, $27, 0;    //reserved_start = 0x00000000
  59                              regwi 1, $28, 0;    //duration = 0x00000000
  60                              regwi 1, $29, 0;    //step = 0x00000000
  61                              regwi 1, $30, 21954560;//control = 0x014f0000
  62                              regwi 1, $31, 0;    //t = 0
  63                              set 1, 1, $26, $27, $28, $29, $30, $31;//ch = 3, pulse @t = $31
  64                              regwi 2, $16, 0;    //target = 0x00000000
  65                              regwi 2, $17, 0;    //reserved_start = 0x00000000
  66                              regwi 2, $18, 0;    //duration = 0x00000000
  67                              regwi 2, $19, 0;    //step = 0x00000000
  68                              regwi 2, $20, 21954560;//control = 0x014f0000
  69                              regwi 2, $21, 0;    //t = 0
  70                              set 2, 2, $16, $17, $18, $19, $20, $21;//ch = 5, pulse @t = $21
  71                              synci 384;
  72                              regwi 0, $13, 0;
  73                              regwi 0, $1, 16;    //initialize ('rf_point_table', 0, 'fine_duration') DMEM pointer
  74                              regwi 0, $2, 99;    //initialize sweep axis 0 counter
  75                              synci 128;
  76  FINE_TUNE_POINT:            regwi 0, $15, 0;
  77  FINE_TUNE_REP:              regwi 1, $10, 0;    //awg_0:set_0:target
  78                              regwi 1, $11, 0;    //awg_0:set_0:reserved_start
  79                              regwi 1, $12, 0;    //awg_0:set_0:duration
  80                              regwi 1, $13, 0;    //awg_0:set_0:step
  81                              regwi 1, $14, 16842752;//awg_0:set_0:control
  82                              regwi 1, $15, 0;    //set_0 t
  83                              set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_0
  84                              regwi 1, $26, 0;    //awg_1:set_0:target
  85                              regwi 1, $27, 0;    //awg_1:set_0:reserved_start
  86                              regwi 1, $28, 0;    //awg_1:set_0:duration
  87                              regwi 1, $29, 0;    //awg_1:set_0:step
  88                              regwi 1, $30, 16842752;//awg_1:set_0:control
  89                              regwi 1, $31, 0;    //set_0 t
  90                              set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_0
  91                              regwi 2, $16, 0;    //awg_2:set_0:target
  92                              regwi 2, $17, 0;    //awg_2:set_0:reserved_start
  93                              regwi 2, $18, 0;    //awg_2:set_0:duration
  94                              regwi 2, $19, 0;    //awg_2:set_0:step
  95                              regwi 2, $20, 16842752;//awg_2:set_0:control
  96                              regwi 2, $21, 0;    //set_0 t
  97                              set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_0
  98                              regwi 1, $10, 352;  //awg_0:ramp_0_to_1:target
  99                              regwi 1, $11, 0;    //awg_0:ramp_0_to_1:reserved_start
 100                              regwi 1, $12, 480;  //awg_0:ramp_0_to_1:duration
 101                              regwi 1, $13, 192640;//awg_0:ramp_0_to_1:step
 102                              regwi 1, $14, 16908288;//awg_0:ramp_0_to_1:control
 103                              regwi 1, $15, 23;   //ramp_0_to_1 t
 104                              set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_0_to_1
 105                              regwi 1, $26, 1073741757;//awg_1:ramp_0_to_1:target
 106                              bitwi 1, $26, $26 << 2;
 107                              regwi 1, $27, 0;    //awg_1:ramp_0_to_1:reserved_start
 108                              regwi 1, $28, 480;  //awg_1:ramp_0_to_1:duration
 109                              regwi 1, $29, 1073705156;//awg_1:ramp_0_to_1:step
 110                              bitwi 1, $29, $29 << 2;
 111                              mathi 1, $29, $29 + 3;
 112                              regwi 1, $30, 16908288;//awg_1:ramp_0_to_1:control
 113                              regwi 1, $31, 23;   //ramp_0_to_1 t
 114                              set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_0_to_1
 115                              regwi 2, $16, 168;  //awg_2:ramp_0_to_1:target
 116                              regwi 2, $17, 0;    //awg_2:ramp_0_to_1:reserved_start
 117                              regwi 2, $18, 480;  //awg_2:ramp_0_to_1:duration
 118                              regwi 2, $19, 91941;//awg_2:ramp_0_to_1:step
 119                              regwi 2, $20, 16908288;//awg_2:ramp_0_to_1:control
 120                              regwi 2, $21, 23;   //ramp_0_to_1 t
 121                              set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_0_to_1
 122                              regwi 1, $10, 352;  //awg_0:set_1:target
 123                              regwi 1, $11, 0;    //awg_0:set_1:reserved_start
 124                              regwi 1, $12, 0;    //awg_0:set_1:duration
 125                              regwi 1, $13, 0;    //awg_0:set_1:step
 126                              regwi 1, $14, 16842752;//awg_0:set_1:control
 127                              regwi 1, $15, 61;   //set_1 t
 128                              set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_1
 129                              regwi 1, $26, 1073741757;//awg_1:set_1:target
 130                              bitwi 1, $26, $26 << 2;
 131                              regwi 1, $27, 0;    //awg_1:set_1:reserved_start
 132                              regwi 1, $28, 0;    //awg_1:set_1:duration
 133                              regwi 1, $29, 0;    //awg_1:set_1:step
 134                              regwi 1, $30, 16842752;//awg_1:set_1:control
 135                              regwi 1, $31, 61;   //set_1 t
 136                              set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_1
 137                              regwi 2, $16, 168;  //awg_2:set_1:target
 138                              regwi 2, $17, 0;    //awg_2:set_1:reserved_start
 139                              regwi 2, $18, 0;    //awg_2:set_1:duration
 140                              regwi 2, $19, 0;    //awg_2:set_1:step
 141                              regwi 2, $20, 16842752;//awg_2:set_1:control
 142                              regwi 2, $21, 61;   //set_1 t
 143                              set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_1
 144                              memr 0, $27, $1;    //load fine RF t
 145                              mathi 0, $1, $1 + 1;
 146                              memr 0, $26, $1;    //load fine RF mode
 147                              mathi 0, $1, $1 + 1;
 148                              memr 0, $24, $1;    //load fine RF addr
 149                              mathi 0, $1, $1 + 1;
 150                              memr 0, $30, $1;    //load fine RF mode2
 151                              mathi 0, $1, $1 + 1;
 152                              memr 0, $28, $1;    //load fine RF addr2
 153                              mathi 0, $1, $1 + 1;
 154                              memr 0, $31, $1;    //load fine RF mode3
 155                              mathi 0, $1, $1 + -5;//restore fine RF row pointer
 156                              regwi 0, $22, 0;    //fine RF freq
 157                              regwi 0, $23, 0;    //fine RF phase
 158                              regwi 0, $25, 1000; //fine RF gain
 159                              condj 0, $31, !=, $0, @FINE_RF_0_START_GAIN_READY;//DDS plateau keeps original gain
 160                              bitwi 0, $25, $25 << 1;//compensate product envelope scaling
 161  FINE_RF_0_START_GAIN_READY: set 0, 0, $22, $23, $24, $25, $26, $27;//fine RF start
 162                              regwi 1, $21, 91;   //fine RF t
 163                              regwi 1, $20, 589827;//fine RF mode
 164                              regwi 1, $18, 10;   //fine RF addr
 165                              regwi 1, $16, 0;    //fine RF freq
 166                              regwi 1, $17, 0;    //fine RF phase
 167                              regwi 1, $19, 2000; //fine RF gain
 168                              set 1, 1, $16, $17, $18, $19, $20, $21;//fine RF start
 169                              regwi 2, $11, 91;   //fine RF t
 170                              regwi 2, $10, 524291;//fine RF mode
 171                              regwi 2, $8, 124;   //fine RF addr
 172                              regwi 2, $6, 0;     //fine RF freq
 173                              regwi 2, $7, 0;     //fine RF phase
 174                              regwi 2, $9, 3000;  //fine RF gain
 175                              bitwi 2, $9, $9 << 1;//compensate product envelope scaling
 176                              set 2, 2, $6, $7, $8, $9, $10, $11;//fine RF start
 177                              condj 0, $31, ==, $0, @FINE_RF_0_TAIL_DONE;//short fine RF has no second command
 178                              bitwi 0, $25, $25 << 1;//compensate product envelope scaling
 179                              set 0, 0, $22, $23, $24, $25, $30, $28;//fine RF ending pattern
 180  FINE_RF_0_TAIL_DONE:        mathi 0, $31, $31 + 0;//fine RF tail complete
 181                              bitwi 1, $19, $19 << 1;//compensate product envelope scaling
 182                              regwi 1, $20, 524292;//fine RF tail mode
 183                              regwi 1, $21, 94;   //fine RF tail time
 184                              set 1, 1, $16, $17, $18, $19, $20, $21;//fine RF ending pattern
 185                              regwi 1, $10, 0;    //awg_0:ramp_1_to_2:target
 186                              regwi 1, $11, 0;    //awg_0:ramp_1_to_2:reserved_start
 187                              regwi 1, $12, 480;  //awg_0:ramp_1_to_2:duration
 188                              regwi 1, $13, 1073693664;//awg_0:ramp_1_to_2:step
 189                              bitwi 1, $13, $13 << 2;
 190                              regwi 1, $14, 16908288;//awg_0:ramp_1_to_2:control
 191                              regwi 1, $15, 3054; //ramp_1_to_2 t
 192                              set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:ramp_1_to_2
 193                              regwi 1, $26, 0;    //awg_1:ramp_1_to_2:target
 194                              regwi 1, $27, 0;    //awg_1:ramp_1_to_2:reserved_start
 195                              regwi 1, $28, 480;  //awg_1:ramp_1_to_2:duration
 196                              regwi 1, $29, 146669;//awg_1:ramp_1_to_2:step
 197                              regwi 1, $30, 16908288;//awg_1:ramp_1_to_2:control
 198                              regwi 1, $31, 3054; //ramp_1_to_2 t
 199                              set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:ramp_1_to_2
 200                              regwi 2, $16, 0;    //awg_2:ramp_1_to_2:target
 201                              regwi 2, $17, 0;    //awg_2:ramp_1_to_2:reserved_start
 202                              regwi 2, $18, 480;  //awg_2:ramp_1_to_2:duration
 203                              regwi 2, $19, 1073718838;//awg_2:ramp_1_to_2:step
 204                              bitwi 2, $19, $19 << 2;
 205                              mathi 2, $19, $19 + 3;
 206                              regwi 2, $20, 16908288;//awg_2:ramp_1_to_2:control
 207                              regwi 2, $21, 3054; //ramp_1_to_2 t
 208                              set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:ramp_1_to_2
 209                              regwi 1, $10, 0;    //awg_0:set_2:target
 210                              regwi 1, $11, 0;    //awg_0:set_2:reserved_start
 211                              regwi 1, $12, 0;    //awg_0:set_2:duration
 212                              regwi 1, $13, 0;    //awg_0:set_2:step
 213                              regwi 1, $14, 16842752;//awg_0:set_2:control
 214                              regwi 1, $15, 3092; //set_2 t
 215                              set 0, 1, $10, $11, $12, $13, $14, $15;//awg_0:set_2
 216                              regwi 1, $26, 0;    //awg_1:set_2:target
 217                              regwi 1, $27, 0;    //awg_1:set_2:reserved_start
 218                              regwi 1, $28, 0;    //awg_1:set_2:duration
 219                              regwi 1, $29, 0;    //awg_1:set_2:step
 220                              regwi 1, $30, 16842752;//awg_1:set_2:control
 221                              regwi 1, $31, 3092; //set_2 t
 222                              set 1, 1, $26, $27, $28, $29, $30, $31;//awg_1:set_2
 223                              regwi 2, $16, 0;    //awg_2:set_2:target
 224                              regwi 2, $17, 0;    //awg_2:set_2:reserved_start
 225                              regwi 2, $18, 0;    //awg_2:set_2:duration
 226                              regwi 2, $19, 0;    //awg_2:set_2:step
 227                              regwi 2, $20, 16842752;//awg_2:set_2:control
 228                              regwi 2, $21, 3092; //set_2 t
 229                              set 2, 2, $16, $17, $18, $19, $20, $21;//awg_2:set_2
 230                              synci 3173;
 231                              mathi 0, $13, $13 + 1;
 232                              memwi 0, $13, 1;
 233                              loopnz 0, $15, @FINE_TUNE_REP;
 234                              loopnz 0, $2, @FINE_TUNE_ADVANCE_0;
 235                              end ;
 236  FINE_TUNE_ADVANCE_0:        mathi 0, $1, $1 + 6;//advance axis 0 ('rf_point_table', 0, 'fine_duration') pointer
 237                              condj 0, $0, ==, $0, @FINE_TUNE_POINT;
