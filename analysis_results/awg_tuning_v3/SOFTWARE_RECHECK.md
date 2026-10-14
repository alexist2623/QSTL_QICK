# 최종 소프트웨어 변경과 기존 RTL 증거의 일치 확인

2026-10-07, `awg_tuning_v3`. FPGA 배치·배선은 이 검사와 별도로 진행 중입니다.

## 긴 ramp의 포화 면적

SET 목표 전압이 허용 범위 안에 있어도, 기존 정수 고정 sweep 증분으로 갱신한
RAMP 증분과 다음 SET 값은 별도로 양자화됩니다. 긴 ramp에서는 그 사이의
일부 샘플이 DAC 한계를 넘어서 포화될 수 있습니다.

RTL 면적 누적기는 이미 포화된 실제 14-bit DAC 샘플을 합산합니다. Python의
면적 예측도 이에 맞추어 `clipped_floor_sum`을 사용하도록 수정했습니다.
점별 Cartesian 파형 표를 생성하지 않으며, 기존 add/rewind 방식도 유지합니다.
완료 대기와 overflow 사전 검사에는 경계에서 구한 보수적인 포화 면적 한계를
적용합니다. 이 변경으로 FPGA 데이터 경로나 지연은 바뀌지 않습니다.

- QICK: 34개 검사 통과 (`qick_software_final.log`). 무작위 포화 ramp 1,000개를
  독립 샘플 계산과 비교하는 검사를 포함합니다.
- GUI DC/RC/readout timing: 89개 검사 통과 (`gui_timing_final.log`). 100점의
  DAC 한계 근처 sweep 및 마지막 ramp의 독립 샘플 합산 검사를 포함합니다.

## 실제 GUI와 완료된 Verilog 실행 재대조

위 수정 후 기존 세 시스템 조건을 `verify_gui_rtl.py --reuse-snapshot
--prepare-only`로 다시 생성했습니다. 두 RF 조건은 `--verify-gui-widgets`를
사용하여 실제 Qt MainWindow 설정 → Run Experiment의 프로그램 생성 경로도
다시 실행했습니다.

| 조건 | 프로그램 생성 | 기존 RTL 소스·PMEM·DMEM fingerprint |
|---|---|---|
| RF duration × voltage, fixed voltage, overlap readout | GUI 입력 후 시험용 축 순서 반전 | 일치 |
| RF duration × voltage, fixed time, after readout | 실제 GUI 입력 | 일치 |
| Stability 10×10, fixed time, 역방향/축반전 | Stability builder | 일치 |

세 실행 모두 exit 0입니다. 따라서 이 세 조건은 최근 소프트웨어로도 완료된
RTL 실행과 동일한 입력/소스이며, 시뮬레이터를 중복 실행하지 않았습니다.
고정전압의 GUI 프로그램을 **변경 없이** 검증하기 위한 추가 100점×2회 실제
RTL도 별도로 실행하여 통과했습니다 (`v3_100_voltage_gui`, 세션56876 exit0).
각 DAC200회 보상/초기화/잔여0, 명령값·시각불일치0, RF200개/폭오차0,
DDR200trigger/800sample/400AXI write를 확인했습니다. 위 축 반전 조건은 추가
compiler/RTL 스트레스 시험으로 구분합니다. 최종 system 보고서는 이 추가
경우까지 총 네 경우가 모두 끝났으며 complete=true입니다.

새 포화 경계 사례 자체는 독립 소프트웨어 샘플 검사입니다. 그 사례를 새로
전체 GUI→tProcessor RTL로 실행했다고 주장하지 않습니다.

로그: `replay_voltage_final.log`, `replay_time_final.log`,
`replay_stability_final.log`. 실제 GUI와 PMEM/DMEM 일치 증거 및 프로그램은
`system_validation/`의 각 조건 폴더에 보관했습니다.

전체 디지털 시스템 결과는 [REPORT.md](system_validation/REPORT.md)를 참고하십시오.
BIT/HWH 배포는 전체 FPGA 타이밍 통과 이후에만 수행합니다.
