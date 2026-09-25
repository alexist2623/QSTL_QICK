# SquarePulse GUI mute 선택 및 포트 선택 검증

2026-09-23. GUI 변경은 `PulseGenerator-qick`의 `codex/square-pulse-dds-gui`에 적용했다. 제품 FPGA RTL과 bitstream 변경은 필요하지 않다.

## 동작

- **AWG Tuning → SquarePulse:** `Mute SquarePulse when experiment finishes`를 추가했다. 기본값은 체크다. 체크하면 정상 종료 시 mute하고, 해제하면 최종 주파수·진폭·위상 offset을 유지하면서 출력이 계속된다. 생성 assembly와 Python 종료 처리 모두 같은 선택을 따른다. 중단·오류 시에는 mute한다.
- **QICK Square Wave:** 전용 SquarePulse IP만 사용할 수 있다. 두 사각파 패널 모두 AWG Tuning과 같은 실제 DAC 포트 선택 창을 사용한다. 일반 AWG/RF 포트는 선택할 수 없고, 해당 IP가 없는 펌웨어는 실행이 비활성화된다. Start 직전 연결된 펌웨어의 IP 종류도 다시 검사한다.
- 별도 탭은 주파수(Hz), peak amplitude(mV), phase offset(deg), 최대 출력 전압을 설정한다. 해당 IP의 duty는 50%이며 DC offset은 지원하지 않는다.
- Start는 전용 IP에 한 번 설정을 보내고 tProcessor가 END에 도달하는 프로그램을 사용한다. GUI worker가 끝난 뒤 다른 실험을 실행할 수 있다. 출력은 계속 유지된다. 다시 Start하면 위상 누적기를 reset하지 않고 설정을 갱신한다.
- Stop은 `soc.stop_square_pulse()`로 선택한 IP를 mute한다. 이 탭에서 시작한 출력뿐 아니라, mute를 해제한 AWG 실험이 남겨 놓은 출력도 끌 수 있다. tProcessor END나 GUI 창 닫기 자체는 mute 명령이 아니다.
- mute 설정과 포트·파형 설정은 JSON에 저장된다. 기존 설정 파일에서 mute 항목이 없으면 기존대로 정상 종료 시 mute한다.

## Python / GUI

관련 10개 테스트 파일에서 **175 tests PASS**. 이후 포트 안내/주파수 입력 범위 조정에 대해서도 관련 테스트를 재실행했다.

검증 범위: 포트 선택과 일반 AWG 포트 차단, 다른 탭으로 돌아갔을 때 선택 제한 복구, 펌웨어별 generator 번호 변경, 구형 펌웨어, 설정 저장/복원, 생성 Python 실행, 정상 종료·취소·예외 처리, Start/Stop 연결 처리, 기존 AWG/RF/trigger 및 저장 동작.

## 실제 Verilog / VHDL 실행

Vivado/XSim 2023.1에서 실제 tProcessor + TMUX + command slice + SquarePulse IP + DAC output slice와 AWG 경로를 실행했다. 실제 생산 설계의 instance/연결을 그대로 유지한 14개 IP 설계이며, RFDC/ARM은 포함하지 않는다. 유지된 instance 텍스트와 원본 hash는 `square_controls_provenance.json`에 기록했다. behavioral DDS를 DUT로 대체하지 않았다.

AWG 실험은 실제 GUI export를 assembler로 컴파일한 PMEM/DMEM을 실행했다. 별도 탭은 실제 `build_square_wave_program()` 결과를 실행했다. 설정은 주기 500 µs(2 kHz 요청), 위상 offset 45°이며 실험에서는 진폭 10→20 mV를 2점 hardware sweep했다. 별도 탭은 20 mV를 사용했다. 디지털 전압 환산 full scale은 800 mV다.

| 실제 실행 | END 이후 확인 | IP core scalar samples | DAC scalar samples | 판정 |
|---|---|---:|---:|---|
| GUI mute ON | 출력 0 유지 | 5,283,392 | 5,283,392 | PASS |
| GUI mute OFF | 약 1.079 ms 동안 ±820 codes 출력 지속 | 5,283,392 | 5,283,392 | PASS |
| 별도 탭 Start | 약 1.099 ms 동안 ±820 codes 출력 지속 | 5,282,336 | 5,282,336 | PASS |

세 경우 모두 tProcessor END 도달을 assertion으로 확인했다. tProcessor 명령 word/시각, SquarePulse 입력 word/전달 지연, 위상 reset flag 부재를 확인했다. 모든 fabric clock의 16 lanes를 독립 scalar phase-accumulation reference와 비교했다. 총 **31,698,240 core/DAC sample comparisons, 불일치 0**이다.

계속 출력되는 구간을 확인한 뒤 각 경우에서 AXI-Lite mute 쓰기를 보냈다. CDC·출력 파이프라인이 지난 후 DAC 버스가 32 clocks 연속 0인지도 assertion으로 확인했으며 **세 경우 모두 PASS**다. Python 테스트에서는 Stop이 선택한 generator 번호로 `soc.stop_square_pulse()`를 호출하는지 별도로 확인했다.

![실제 RTL 출력](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/square_controls_rtl.png)

[기계 판독 결과](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/square_controls_results.json), [재현 스크립트](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/verify_square_gui_controls.py).

아날로그 DAC 출력의 전압·edge 실측은 이번 검증 범위에 포함하지 않았다.

## 실제 GUI 위젯 화면

아래는 새 코드를 실행해 Qt 위젯을 캡처한 화면이다. routing은 저장된 생산 펌웨어의 HWH 기반 구성이고, daughter-card 표시는 DC 카드 테스트 설정이다. 실제 보드에 접속해 얻은 화면은 아니다.

![별도 사각파 출력 탭](C:/JeonghyunPark/Workspace/PulseGenerator-qick/output/square_output_controls/square_wave_tab.png)

![AWG SquarePulse 탭의 mute 선택](C:/JeonghyunPark/Workspace/PulseGenerator-qick/output/square_output_controls/awg_squarepulse_tab.png)

![물리 포트 선택 창](C:/JeonghyunPark/Workspace/PulseGenerator-qick/output/square_output_controls/port_selector.png)

## 재현

기존 simulation project의 native RTL library가 준비된 상태에서:

```text
python SIM/verify_square_gui_controls.py BUILD --gui PATH_TO_PulseGenerator-qick
python SIM/plot_square_controls.py
python SIM/capture_square_controls.py --gui PATH_TO_PulseGenerator-qick
```

`SIM`은 이 문서의 디렉터리이며, 이번 `BUILD`는 `C:/JeonghyunPark/Workspace/Vivado_Output/gui_rtl6`이다. GUI 캡처에는 Qt offscreen backend와 Windows 글꼴을 사용했다.
