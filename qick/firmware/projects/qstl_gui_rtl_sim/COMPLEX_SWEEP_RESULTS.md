# 복잡한 2채널 AWG 파형: 10 × 10 hardware sweep RTL 검증

검증일: 2026-09-23. **100점 실행은 완료했지만, 요청한 전압 및 marker 타이밍에 대한 전체 판정은 FAIL이다.** 두 AWG의 명령·출력은 현재 컴파일러의 정수 sweep 계산과 bit 단위로 일치한다. 그러나 그 계산 자체의 누적 전압 오차, ramp 끝의 overshoot/undershoot, loop 시작 marker 지연이 관찰됐다. GUI와 제품 RTL은 이번 검증에서 수정하지 않았다.

## 입력 조건

첨부 이미지의 두 AWG 표를 아래와 같이 입력하고, 실제 QICK GUI의 `generate_qick_program_code()`로 Python을 생성한 뒤 실제 QICK assembler로 컴파일했다. Python에서 각 점을 다시 실행하지 않고, tProcessor의 중첩 `loopnz`가 100점을 순회한다. 각 점의 repetition은 1이다.

| Segment | 진입 ramp (µs) | Flat (µs) | Gen 3 (mV) | Gen 1 (mV) |
|---|---:|---:|---:|---:|
| set_0 | 0 | 5 | 0 | 0 |
| set_1 | 1 | 5 | 0 | 300 |
| set_2 | 1 | 5 | −300 | 0 |
| set_3 | 0.05 | 0.1 | 125 | −75 |
| set_4 | 0.1 | 40 | 0 | 0 |

이미지에는 sweep 축과 범위가 표시되지 않아 다음을 **테스트 조건으로 가정**했다. 첫 점은 이미지의 원래 파형이다.

- 바깥 축: gen 3의 set_3 전압, **125 → 215 mV, 10점**.
- 안쪽 축: gen 1의 set_3 전압, **−75 → 15 mV, 10점**.
- 전압 환산: GUI `FULL_SCALE_MV=800`, cross-capacitance는 단위행렬, bias-T 보상 비활성.
- 클록: tProcessor와 AWG fabric 모두 300 MHz, 출력은 클록당 16 samples.
- 추가 진단 조건: 각 loop의 시작/끝에 폭 0.37 µs인 외부 marker.
- 이미지 하단 RF pulse의 설정은 전부 보이지 않아 이 사례에서는 RF/SquarePulse/readout 명령을 추가하지 않았다. 이 결과는 두 AWG 표와 marker에 대한 검증이다.

이 문서의 mV는 위 full-scale 설정으로 DAC 코드를 환산한 값이다. 아날로그 출력 실측이나 calibration 검증은 아니다.

## 실행 범위와 방법

실제 tProcessor, TMUX, command register slice, 두 `axis_awg_tuning_v1`, DAC 출력 register slice, trigger IP를 포함한 16개 instance로 100점을 끝까지 실행했다. GUI export는 175개 PMEM 명령과 0개 DMEM table word로 컴파일됐다. 테스트벤치는 실제 tProcessor가 END 명령에 도달했는지도 확인했다.

축소 설계는 기존 78-IP 시뮬레이션 설계에서 사용하지 않는 경로를 제거한 것이다. 유지된 instance의 연결·parameter 텍스트는 원본과 동일하며, 실제 RTL을 behavioral waveform generator로 대체하지 않았다. 제거한 readout 입력은 idle, 사용하지 않는 출력 포트는 ready로 고정했다. 원본·축소 설계의 instance hash는 `complex_topology_audit.json`에 남겼다.

동일한 100점 PMEM을 **78-IP 전체 디지털 설계에서도 앞 36,000 실행 클록** 동안 실행해 교차 검증했다. 이는 2점 전체와 3번째 점의 초반에 해당한다. 그 구간의 두 DAC 출력, 모든 AWG 명령, tProcessor 출력, GPIO trace는 축소 설계와 완전히 같았다. 전체 설계에서 100점을 모두 재실행한 것은 아니다. 두 설계 모두 RFDC와 ARM/PS를 포함하지 않는다.

독립 비교기는 입력 표에서 SET 값, 정수 ramp step, sweep 순서와 절대 시각을 계산한다. 관측한 AWG 명령을 그대로 expected waveform으로 사용하지 않는다. GUI의 현재 정수 sweep 계산과 일치하는지, 원래 요청값을 각 점별로 반올림한 결과와 일치하는지는 별도로 판정했다.

| 확인 항목 | 결과 |
|---|---|
| 10 × 10 hardware sweep, 실제 END 도달 | 완료 |
| AWG 명령 수 | 채널당 900개, 합계 1,800개; 누락 없음 |
| 모든 16 lanes의 DAC 값 비교 | 채널당 27,728,016 samples; 합계 **55,456,032 samples, 불일치 0** |
| 두 채널 command 및 waveform 시각 | 독립 정수 모델과 일치, 채널 간 skew 없음 |
| reset 이후 미정의 AWG 출력 | 0 |
| 78-IP / 16-IP 교차 검증 | 채널당 578,336 samples와 명령/GPIO 모두 일치 |
| 요청 전압을 각 점별로 반올림한 SET 값 | **불일치**, 최대 16 raw DAC codes |
| Ramp가 양 끝점 범위를 벗어나는지 | **벗어남**, 최대 16 raw DAC codes |
| 시작/끝 marker의 요청 시각·폭 | **불일치**, 아래 설명 |

Trace는 매 300 MHz 클록에서 16 lanes를 관찰한다. CSV는 값이 변하지 않는 구간을 생략하고 주기적인 checkpoint를 추가한 lossless 압축이며, 비교할 때 모든 클록을 복원한다.

## 실제 파형과 시간

검은 실선은 현재 정수 sweep 규칙에 대한 독립 예측, 색 점선은 실제 RTL 출력이다. 아래는 이미지와 동일한 첫 점과 50 ns ramp/100 ns flat 주변 확대다.

![첫 점 전체 및 짧은 구간 비교](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/waveform_comparison.png)

- 50 ns ramp: 15 fabric clocks, 240 scalar samples.
- 100 ns ramp: 30 fabric clocks, 480 scalar samples.
- 표의 시간 합계는 57.25 µs이다. 현재 GUI는 4개 ramp 뒤에 각각 1 fabric clock의 guard를 삽입해 예정 파형 길이는 **57.263333 µs**다. Ramp 목표값을 guard 동안 유지한다.
- recovery와 loop-end marker 구간까지 포함한 point 간격은 **17,311 clocks = 57.703333 µs**다.
- SET은 논리적 예정 시각으로부터 14 clocks 뒤에 관측 DAC 버스에 나타난다. tProcessor dispatch 1 clock, TMUX/command slice 3 clocks, 출력 slice 10 clocks를 포함한다. Ramp는 자체 startup 7 clocks를 보상하도록 command를 7 clocks 먼저 보낸다. 이 지연은 두 채널 모두 동일하며 비교기에 명시적으로 반영했다.

## 발견 1: sweep 전압의 누적 오차

현재 구현은 hardware register에 일정한 정수 증분을 더한다. 요청한 10 mV는 409.6 raw DAC codes지만, 유효 DAC code 간격 4에 맞추면 sweep 증분은 **408 codes = 9.9609375 mV**가 된다.

| 채널 | 첫 점 | 요청한 마지막 점 | 실제 마지막 SET code | 실제 마지막 점 | 요청 대비 오차 |
|---|---:|---:|---:|---:|---:|
| Gen 3 | 125 mV | 215 mV | 8792 | 214.6484375 mV | −0.3515625 mV |
| Gen 1 | −75 mV | 15 mV | 600 | 14.6484375 mV | −0.3515625 mV |

각 점을 독립적으로 가장 가까운 유효 DAC code로 반올림할 경우 마지막 점은 각각 8808, 616이다. 현재 hardware sweep 결과와는 16 raw codes 차이가 난다. 따라서 이것은 단순히 개별 전압의 불가피한 DAC 반올림 오차만으로 설명할 수 없다. 고정된 정수 증분의 오차가 누적된다.

실제 관측 SET code로 만든 100점 오차 지도:

![100점 SET 전압 오차](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/sweep_voltage_error.png)

관련 구현: [정수 sweep register 계획](C:/JeonghyunPark/Workspace/PulseGenerator-qick/DCWaveformGeneratorGUI/qick_fine_tune_sweep.py:3954), [axis 증분 계산](C:/JeonghyunPark/Workspace/PulseGenerator-qick/DCWaveformGeneratorGUI/qick_fine_tune_sweep.py:4110).

## 발견 2: ramp 끝의 작은 overshoot/undershoot

SET target과 ramp step을 서로 다른 정밀도로 따로 sweep하므로, 누적된 실제 시작·목표 전압과 ramp 기울기가 정확히 맞지 않을 수 있다. 실제 RTL에서 양 끝점 구간을 최대 **16 raw codes = 0.390625 mV** 벗어났다. 이는 14-bit 유효 DAC step으로 4칸이다.

예를 들어 point `(0,9)`의 gen 1은 마지막 0.1 µs ramp에서 0으로 내려갈 때 **−16 codes까지 내려갔다가 마지막 sample에서 0으로 고정**된다. 아래 그림은 실제 RTL sample을 전부 표시한다. 현재 ramp 수식과 bit 단위로 일치하더라도, 요청한 단조 ramp와는 차이가 있다.

![마지막 ramp undershoot](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/ramp_endpoint_detail.png)

관련 구현은 SET target을 4-code 단위, step을 1 단위로 별도 모델링하는 [field 설정](C:/JeonghyunPark/Workspace/PulseGenerator-qick/DCWaveformGeneratorGUI/qick_fine_tune_sweep.py:3993)이다.

## 발견 3: loop 경계의 marker 지연

첫 시작 marker와 100개 끝 marker는 요청한 폭 **111 clocks = 370 ns**를 유지했다. 그러나 2번째부터 100번째까지의 **99개 시작 marker는 2 clocks = 6.666667 ns 늦게 올라갔고**, 내려가는 시각은 유지돼 폭이 **109 clocks = 363.333333 ns**로 줄었다. AWG 자체의 예정 출력 시각은 변하지 않았다.

원인은 loop-end marker를 내린 뒤 다음 loop-start marker를 올리기까지 1 clock만 예약하기 때문이다. 실제 tProcessor의 해당 출력 상태기는 최소 3-clock 간격이 필요하다. 기존 SquarePulse 동시 실행 사례에서는 그 업데이트용 간격이 추가돼 이 조건이 드러나지 않았다. 이번에는 SquarePulse를 사용하지 않아 재현됐다.

![marker 요청과 실제 시각](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/marker_timing_error.png)

관련 구현: [marker 뒤 width+1 진행](C:/JeonghyunPark/Workspace/PulseGenerator-qick/DCWaveformGeneratorGUI/qick_output_triggers.py:59), [실제 timed output 상태기](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/ip/axis_tproc64x32_x8_v1/src/timed_ictrl.vhd:99).

## 결과 파일과 재현

- [실제 GUI 생성 Python](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/gui_export.py)
- [실제 assembly](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/program.asm)
- [100점 판정 JSON](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/focus/comparison.json)
- [각 점의 요청/실제 전압 CSV](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/focus/point_values.csv)
- [78-IP 교차 검증 JSON](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/gui_complex_10x10/full_focus_equivalence.json)
- [SystemVerilog 테스트벤치 본문](C:/JeonghyunPark/Workspace/QSTL_QICK/qick/firmware/projects/qstl_gui_rtl_sim/tb_complex_body.svh)

GUI checkout: `C:/JeonghyunPark/Workspace/PulseGenerator-qick`, branch `codex/square-pulse-dds-gui`. QICK checkout branch: `codex/1msps-square-pulse-dds`. GUI source hashes는 case의 `gui_sources.json`에 기록했다. XSim 2023.1을 사용했다.

기존 README의 simulation build 및 native RTL library 준비가 완료된 상태에서 다음을 실행한다. `SIM`은 이 문서의 디렉터리, `BUILD`는 기존 Vivado simulation build 경로다. 이번 실행의 BUILD는 `C:/JeonghyunPark/Workspace/Vivado_Output/gui_rtl6`이다.

```text
python SIM/build_complex_program.py --gui PATH_TO_PulseGenerator-qick
python SIM/build_complex_tb.py BUILD
python SIM/run_complex_xsim.py BUILD
python SIM/run_complex_xsim.py BUILD --full --cycles 36000
python SIM/analyze_complex.py
python SIM/analyze_complex.py --full
python SIM/plot_complex.py
```

두 `analyze_complex.py` 실행은 현재 발견한 문제 때문에 **exit code 1을 반환하는 것이 저장된 결과와 일치**한다. 파형 생성 시뮬레이터가 끝까지 실행됐다는 사실과 요청값 검증에 통과했다는 것은 별개다. `full_focus_equivalence.json`의 PASS는 두 실제 RTL 설계가 같은 결과를 냈다는 판정이다.
