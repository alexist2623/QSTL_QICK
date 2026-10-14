# Waveform Plot acquisition 표시

## 구현 범위

Waveform Plot 아래에 제목 **Acquisition**과 입력 측정 구간 막대 하나만 표시합니다. 사용자의 최종 요청에 따라 DDR write, trigger, Input 축 라벨, readout 번호, sample 수/rate와 설명 문구는 화면에 표시하지 않습니다. Fit 범위도 실제 표시하는 측정 구간만 포함합니다.

Waveform과 acquisition의 시간축은 연결되어 있어 막대의 위치와 길이로 측정 시각/시간을 확인할 수 있습니다. 확대 범위에 따라 acquisition 시간축은 ns/us/ms/s 단위가 바뀝니다. 시작·종료·길이는 짧은 tooltip으로만 추가 제공하며, RF의 기존 단위 선택 동작은 유지합니다.

공통 Sweep point 선택은 virtual/physical/RC와 함께 RF 및 acquisition에도 적용됩니다. 앞쪽 hold-duration sweep이 늘어나면 뒤 segment에 연결된 RF와 acquisition 시작 시각이 같은 만큼 이동합니다. acquisition이 연결된 segment 자체의 hold 시간 변경은 해당 segment 시작에 걸린 trigger를 이동시키지 않습니다. RF duration/frequency sweep의 선택 좌표도 display-only RF 이벤트에 적용합니다. 실제 RF 명령, acquisition 명령, compiler 및 RTL은 수정하지 않았습니다.

## 시간의 의미

- 입력 측정 길이: `N / FIR sample rate`. 첫 sample과 마지막 sample 사이의 간격은 `(N - 1) / rate`입니다.
- 입력 시작 시각: 선택한 SET의 시작 + 사용자 trigger delay + 필요한 legacy software delay + HWH FPGA capture delay - FIR group delay.
- 사용자 trigger delay는 기존 `cycles_from_us`, FPGA override는 기존 `FirDdrProfile.trigger_delay_value_for_us`를 사용합니다. 기존 compiler와 같이 FIR group delay의 입력 sample 수를 올림합니다.
- DDR storage 시각은 입력 window 계산과 compiler 결과 비교에만 내부적으로 사용합니다. 화면에는 출력하지 않습니다.
- FIR margin과 post-run DDR read delay를 측정 길이에 더하지 않습니다.
- 이 표시는 현재 Waveform Plot과 같은 **이상적인 AWG 파형의 첫 edge를 0으로 놓은 nominal 입력 구간**입니다. full compiler의 명령 스케줄/출력 pipeline 절대시각은 포함하지 않습니다. FIR group-delay 기준이며 impulse-response 전체 support와 같지는 않습니다. 연속 decimation sample phase 때문에 최대 한 stored-sample period의 경계 차이가 있을 수 있습니다. 사용자의 간단한 표시 요청에 따라 이 기술 설명은 이 문서에만 남깁니다.
- HWH rate/delay metadata가 없거나 다른 연결로 Setup을 바꾸면 임의 rate를 가정하지 않고 이전 측정 막대를 지웁니다. `Identify QICK` 안내는 tooltip에만 표시하며 제목은 `Acquisition`으로 유지합니다.

## 변경 파일

모두 `C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI` 아래에 있습니다.

- `DCWaveform_Generator.py`: 표시 lane 연결, 선택 point/settings/profile 변경 시 refresh, RF point 동기화, Fit.
- `dc_waveform_widgets.py`: acquisition 측정 막대 하나, 가변 시간 단위, 간단한 제목/tooltip.
- `qick_front_panel.py`: 기존에 해석한 HWH `FirDdrProfile`을 선택적 표시 metadata로 전달. 기존 호출은 `None` 기본값 유지.
- `acquisition_preview.py`: 기존 sequence/FIR profile을 읽는 display-only timing 계산.
- `test_acquisition_preview.py`: 19개 추가 회귀 검사.

기존 dirty 변경과 사용자 설정 JSON은 보존했습니다. commit/push, compiler/RTL/XDC/펌웨어 변경은 이 표시 작업에 포함하지 않았습니다.

## 검증

- 기존 waveform-compensation/GUI-RF/front-panel + acquisition-segment-timing + 신규 표시 검사를 묶어 **153개 PASS**, exit 0. [JUnit](acquisition_tests_final.xml)
- 이후 사용자의 최종 `Acquisition` 제목/측정 막대만 표시 요청까지 반영한 뒤, 영향받는 **신규 19개 다시 PASS**, exit 0 (8.50초). [최종 JUnit](acquisition_new_tests_final.xml)
- 두 수치는 일부 중복 검사이며 172개 고유 검사라는 의미가 아닙니다.
- legacy 1 MSPS, source-clock-delay 및 valid-sample-delay profile에 대해 기존 `fir_dc_timing_preview`의 시각을 첫 AWG edge 기준으로 정렬하여 helper 결과와 비교했습니다.
- hold sweep의 downstream RF/acquisition 동시 이동, own-anchor 불변, delay override, N/rate, readout disable, 누락/변경된 HWH, settings restore, negative input start와 Fit, ns/ms zoom, 표시 동작의 run-settings/sequence 비변경을 확인했습니다.
- 최종 화면은 실제 Qt MainWindow로 만들어 1250px/600px 및 ns zoom을 각각 열어 확인했습니다. Qt offscreen capture에만 Windows Arial font를 명시적으로 로드했으며 production font 설정은 변경하지 않았습니다.

[전체 화면](acquisition_waveform.png) · [600px dock](acquisition_narrow.png) · [ns 확대](acquisition_zoom.png)

hold-duration 실제 GUI→Verilog 및 추가 RC-only 검증은 부모 작업의 별도 보고서에 기록합니다. 표시 테스트 통과만으로 해당 RTL 검증 완료를 주장하지 않습니다.
