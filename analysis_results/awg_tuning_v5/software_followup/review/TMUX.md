# 공유 tProcessor 포트와 TMUX의 시간 처리: RTL 읽기 검토

검토 범위는 현재 v5 빌드에 사용된 생산 RTL의 정적 구조이다. 소스 수정이나 새 시뮬레이션은 수행하지 않았다. 아래 최단 간격은 FSM에서 도출한 구조적 설명이며, 별도로 진행할 raw diagnostic의 측정 결과를 대신하지 않는다.

## 1. 같은 DAC의 AWG/RF는 하나의 timed dispatcher를 공유한다

`qick/firmware/projects/qstl_awg_v5/bd_2023-1.tcl`:

- 2595–2597: tProcessor m1/m2/m3 각각이 TMUX 0/1/2의 단일 s_axis에 연결된다.
- 2578–2583: 각 TMUX의 m0은 RF register slice, m1은 AWG register slice이다.
- 2543–2557: 해당 slice 출력이 RF 0/1/3 및 AWG 4/5/6의 명령 입력으로 연결된다.

`qick/firmware/ip/axis_tproc64x32_x8_v1/src/tproc64x32_x8.v` 496–553은 **tProcessor 물리 출력 채널마다 FIFO와 timed_ictrl 하나**를 생성한다. 528의 FIFO 선택은 `channel_i == i`이다. 명령 payload의 TMUX 번호별로 별도 timed FIFO를 생성하지 않는다.

따라서 명령 두 개를 미리 프로그램에 넣는 것과, 두 개의 독립 출력 스케줄러에 넣는 것은 다르다. 다른 TMUX 번호를 사용해도 같은 tProcessor 물리 채널의 FIFO 순서를 공유한다.

## 2. 3클록 guard는 timed dispatcher의 FSM에 근거한다

`qick/firmware/ip/axis_tproc64x32_x8_v1/src/timed_ictrl.vhd`:

- 99–102: READ_ST에서 FIFO가 비어 있지 않으면 WAIT_ST로 이동한다.
- 104–120: WAIT_ST에서 `t_inst <= t_cnt`이면 SET_ST로 이동한다.
- 146–147: SET_ST 다음에는 READ_ST로 돌아간다.
- 167–168: FIFO read enable은 READ_ST에서 켜진다.
- 183–185: 160비트 SET 출력의 valid는 SET_ST에서 켜진다.

두 명령이 충분히 미리 큐에 있고 두 번째 timestamp도 이미 도래한 최단 경우의 **출력 상태**는 다음과 같다.

| 상대 클록 | dispatcher 상태 | 출력 valid |
|---:|---|---:|
| 0 | SET_ST, 첫 명령 | 1 |
| 1 | READ_ST, 다음 FIFO 명령 읽기 | 0 |
| 2 | WAIT_ST, 다음 명령 timestamp 검사 | 0 |
| 3 | SET_ST, 둘째 명령 | 1 |

즉 SET 출력 valid의 최단 간격은 구조상 3 tProcessor 클록이다. timestamp를 같게 쓰거나 1클록 차이로 써도 FSM의 READ/WAIT 단계가 없어지지 않는다. 실제 release 시각의 기준 클록과 출력 도착 차이는 raw diagnostic에서 별도로 확인해야 한다. 큐 공급이 늦거나 blocking/ready 조건이 있으면 간격은 더 길어질 수 있다.

컴파일러의 `abs(rf_start - occupied_time) < 3` 및 sweep `minimum < 3` 거부는 이 조건을 보존한다. 서로 다른 tProcessor 물리 포트에는 별도 dispatcher가 있으므로 이 설명을 모든 출력 쌍에 일반화하면 안 된다.

## 3. TMUX 자체에는 출력별 timestamp FIFO가 없다

`qick/firmware/ip/axis_tmux_v1/src/tmux.sv`:

- 47–52, 81–92: data/valid의 공통 2단 파이프라인이다.
- 67–75: payload 상위 8비트의 하위 3비트로 출력 하나를 선택하고, 선택된 출력만 valid를 낸다.
- 117: 입력 ready는 항상 1이다.

TMUX는 입력 stream을 목적지로 분배한다. 출력별 FIFO, timestamp 비교기, 공통 시각까지 대기하는 독립 scheduler는 없다. TMUX 자체는 연속 입력을 파이프라인할 수 있지만 앞단 timed dispatcher의 3클록 처리율을 높여주지 않는다.

timestamp 자체도 TMUX까지 전달되지 않는다. `timed_ictrl.vhd` 79는 FIFO의 [207:160]에서 timestamp를 읽지만, 198–199의 출력은 p4..p0의 **160비트 payload만**이다. 후단 TMUX가 원래 timestamp를 해석해서 두 명령을 재정렬하거나 동시에 내보낼 수 없다.

주의: **RF generator에는 자체 명령 FIFO가 있다.** `axis_signal_gen_v6/src/signal_gen_top.v` 92–119가 그것이다. 이것을 TMUX별 독립 timestamp FIFO와 혼동하면 안 된다. `ctrl_sg_v6.sv` 294–305, 430–438은 길이/모드/주파수/위상/주소 등의 160비트 명령을 재생하며, tProcessor의 48비트 timestamp를 비교하지 않는다. 이 FIFO는 이미 늦게 도착한 명령을 원래 절대 시각으로 되돌릴 수 없다.

## 4. native latency가 같아도 명령 도착 차이는 남는다

v5는 AWG 출력에 13클록을 더하여, 검증된 일반 명령 기준 native latency를 AWG 31 / RF 31로 맞춘다. 해당 기준에서:

`RF 물리 시작 - AWG 물리 시작 = RF 명령 도착 - AWG 명령 도착`

동일한 31을 양쪽에 더해도 앞단의 명령 도착 차이는 없어지지 않는다. 따라서 현재 공유 포트와 기존 SET/HOLD + RF 명령 형식에서는, 같은 timestamp 두 개가 곧 같은 물리 출력 시각이라는 주장을 할 수 없다. RAMP의 기존 추가 시작 지연 7클록은 별도 의미이며 이 식의 일반 SET/HOLD 기준과 혼동하지 않는다.

현재 소프트웨어는 이를 숨기려고 요청 timestamp를 이동하거나 guard를 완화하지 않는다. RF offset 0의 같은 HOLD 경계 요청에 대한 실제 동작은 진행 중인 raw diagnostic과 GUI→RTL 검증 증거로 최종 보고해야 한다.

## 빌드 소스 일치 확인

`timed_ictrl.vhd` 저장소 원본과 `F:/Vivado_Output/a5full1/qstl_awg_v5.gen/sources_1/bd/d_1/ipshared/ffa8/src/timed_ictrl.vhd`의 SHA256은 모두 다음과 같다.

`cac24b18f1e0b98dff48b826d8917e0f094c4402935caf6545030d18a9c5a0e8`

본 문서는 읽기 검토이며 raw diagnostic의 출력 CSV/파형/수치를 포함하지 않는다.
