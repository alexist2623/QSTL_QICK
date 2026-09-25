"""Write the report only from completed RTL runs and their checked results."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    cases = ['gui_sweep', 'gui_500us', 'gui_autonomy', 'gui_frequency',
             'gui_awg_repeat', 'gui_awg_capture_repeat']
    results = {case: json.loads((HERE/case/'comparison.json').read_text()) for case in cases}
    topology = json.loads((HERE/'topology_audit.json').read_text())
    if not topology['passed'] or not all(r['passed'] for r in results.values()):
        raise SystemExit('A required check has failed; do not publish a passing report.')
    provenance = {}
    for case in cases:
        provenance[case] = {name: hashlib.sha256((HERE/case/name).read_bytes()).hexdigest()
                            for name in ['gui_export.py', 'program.asm', 'pmem.hex', 'dmem.txt',
                                         'expected.json', 'comparison.json', 'rtl_checks.txt']}
        if (HERE/case/'gui_sources.json').is_file():
            provenance[case]['gui_sources.json'] = hashlib.sha256((HERE/case/'gui_sources.json').read_bytes()).hexdigest()
        if (HERE/case/'awg_point_timing.csv').is_file():
            provenance[case]['awg_point_timing.csv'] = hashlib.sha256((HERE/case/'awg_point_timing.csv').read_bytes()).hexdigest()
    (HERE/'result_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    rows = []
    for case, result in results.items():
        rows.append(f'| `{case}` | {result["gui_events"]} | {result["sample_checks"]:,} | '
                    f'{result["awg_sample_checks"]:,} | {result["captured_samples"]} | '
                    f'{result["ddr_beats"]} | PASS |')
    route = results['gui_sweep']['routing']
    latency = route['sqcmd']['latency_cycles'][0]
    periods = results['gui_500us']['initial_square_periods_us']
    theoretical_period = results['gui_500us']['initial_square_theoretical_period_us']
    delays = [c/300 for r in results.values() for c in r['trigger_to_first_sample_cycles']]
    first=results['gui_sweep']
    marker_to_square=(first['first_nonzero_dac_cycles']['dac']-first['first_marker_cycle'])/300*1000
    marker_to_awg=(first['first_nonzero_dac_cycles']['awg']-first['first_marker_cycle'])/300*1000
    text = f'''# GUI → 실제 tProcessor RTL 통합 시뮬레이션 결과

RFDC IP와 ARM CPU/Zynq PS를 제거한 별도 프로젝트에서 검증했다. GUI exporter의 Python을 실제 QICK assembler로 컴파일하여 PMEM/DMEM에 넣었고, 명령은 실제 tProcessor RTL이 실행했다. 생성기 입력에 명령을 대신 주입하지 않았다.

## 결과

| 시나리오 | GUI 명령 수 | SquarePulse 샘플 비교 | AWG 샘플 비교 | IQ64 샘플 | DDR AXI beat | 결과 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

SquarePulse는 모든 300 MHz 클록에서 16개 DAC lane을 독립적인 sample-by-sample 위상 누적 모델과 비교했다. DDS 코어와 DAC 경계의 10단 register slice를 각각 검사했다. AWG SET/RAMP/SET 출력도 기존 독립 동작 모델과 비교했다.

검증 조건은 다음과 같다. 실제 GUI 창의 현재 설정을 복원한 것이 아니라, 같은 exporter에 명시한 재현 가능한 입력이다.

- `gui_sweep`: 40/80 kHz × 20/40 mV × 0/90°의 8개 Cartesian hardware sweep. 진폭은 800 mV full-scale 설정에서 DAC code 820/1640이다.
- `gui_500us`: 고정 2 kHz, 20/40 mV hardware sweep, 270°. 두 loop의 첫 hold는 각각 325 µs이며, 한 주기 중간에 진폭이 바뀐다. 2 kHz FTW=1790의 이론 주기는 **{theoretical_period:.9f} µs**이고, RTL 양의 edge 간 측정값은 `{periods}` µs이다. 500 µs와의 차이는 32비트 frequency word 반올림에 따른 것이다.
- `gui_autonomy`: 별도 진단용 seed 프로그램으로 2 kHz SquarePulse를 켜고 END 도달을 확인했다. 100 µs 후 IP reset 없이 SquarePulse 명령이 없는 원본 GUI export를 실행했다. 그동안 누적 위상과 출력은 계속 진행하며 scalar 예상값과 일치했다.
- `gui_frequency`: 진폭 20 mV와 위상 0°를 유지하고 주파수만 40→80 kHz로 바꾸는 hardware sweep. Cartesian sweep 경계에서 다른 파라미터가 함께 바뀌는 효과를 분리하여 확인했다.
- `gui_awg_repeat`: AWG 전압 3값 × hold 2값 × ramp 2값을 각 3회 반복하는 36-shot hardware loop. 입력 설정에서 독립 계산한 모든 AWG DAC sample 및 절대 명령 시각과 비교했다. 이 빠른 테스트는 DDR capture를 요청하지 않는다.
- `gui_awg_capture_repeat`: AWG 전압 2값을 각 2회 반복하며 RF/readout/IQ64 capture를 함께 실행하는 4-shot hardware loop.
- 초기 네 시나리오는 `repetitions_per_sweep=1`이었다. 추가 두 시나리오는 실제 repeat 분기가 여러 번 실행된다. 상세 값·타이밍·양자화 분석과 파형은 [AWG_SWEEP_RESULTS.md](AWG_SWEEP_RESULTS.md)에 있다.
- 모든 경우에 실제 AWG SET/RAMP/SET과 190 MHz RF 출력을 함께 실행했다. `gui_awg_repeat`를 제외한 경우에는 190 MHz readout 및 IQ64 DDR 캡처도 실행했다. RF와 SquarePulse는 같은 tProcessor 출력의 실제 TMUX를 공유한다.

## 명령과 출력 시점

시간 기준은 300 MHz fabric clock이며 1 cycle = 3.333333 ns이다.

| 경계 | 측정/검증된 지연 |
| --- | --- |
| 프로그램의 예약 시각 → tProcessor AXIS transfer | +1 cycle: deadline 비교 후 transfer하는 실제 dispatcher 구조 |
| tProcessor transfer → SquarePulse IP command accept | {route['sqcmd']['latency_cycles']} cycles |
| tProcessor transfer → AWG IP command accept | {route['awgcmd']['latency_cycles']} cycles |
| tProcessor transfer → RF IP command accept | {route['rfcmd']['latency_cycles']} cycles |
| SquarePulse command accept → 새 파라미터가 반영된 core word | +4 cycles |
| SquarePulse core → DAC digital boundary | +10 cycles |
| 예약 시각 → SquarePulse DAC word | +{1+latency+14} cycles = {(1+latency+14)/300*1000:.6f} ns |
| 외부 marker 폭 | 111 cycles = 0.37 µs |
| DDR trigger accept → 보정 deadline | 8,712 cycles = 29.04 µs |
| DDR trigger accept → 첫 valid 1 MSPS sample | {min(delays):.6f}–{max(delays):.6f} µs |

주파수 업데이트는 누적기에 더하는 증가량을 바꾼다. 진폭 업데이트는 그 이후 출력 크기를 바꾸며, 위상 offset 업데이트는 누적 위상에 더하는 값을 바꾼다. 이번 sweep 명령에는 accumulator reset이 없다. 이 동작을 명령 이후 매 샘플의 예상값과 비교했다.

파라미터 반영 시점에 출력 부호가 반드시 바뀌는 것은 아니다. 주파수/위상 변경 후에도 누적 위상의 MSB가 같은 동안은 같은 레벨을 유지하며, 다음 경계에 도달했을 때 edge가 나타난다. 아래 단일 파라미터 그래프는 진폭·주파수·위상을 각각 독립적으로 바꾼 구간이다.

Marker는 지정된 loop/experiment 경계의 **디지털 트리거 시각**이다. 첫 loop에서 SquarePulse DAC 시작은 marker보다 **{marker_to_square:.6f} ns** 뒤이고, AWG DAC 시작은 **{marker_to_awg:.6f} ns** 뒤다. DAC 출력은 각 생성기와 register slice의 고정 지연을 거친다. 따라서 marker edge와 아날로그 DAC edge가 자동으로 같은 시각이라는 의미는 아니다.

`gui_sweep`의 RF 디지털 출력에서도 각 pulse가 1,500 clocks = 5 µs, peak code {first['rf_peak_code']}, zero-crossing으로 측정한 주파수 {first['rf_frequency_mhz']:.6f} MHz임을 확인했다. RF IP command accept에서 DAC 첫 word까지는 {first['rf_command_to_dac_cycles']} clocks였다. `gui_awg_repeat`의 RF pulse 길이는 별도로 설정한 150 clocks = 0.5 µs와 일치했다.

29.04 µs는 FPGA trigger queue의 보정 deadline이다. FIR의 1 MSPS valid 시점이 deadline과 일치하지 않으면 다음 valid sample에서 저장이 시작된다. DDR에 실제 기록한 모든 128-bit IQ word를 캡처 입력과 bit-for-bit 비교했고, 256-bit AXI packing 순서·주소·strobe도 확인했다.

일반 GUI export는 끝에서 SquarePulse **mute 명령을 직접 보낸다**. 따라서 일반 실험 종료 때 출력이 꺼지는 것은 그 명령의 결과다. `gui_autonomy`에서는 mute 없는 END/restart를 별도로 검증했다.

## 그래프

![Hardware sweep overview](gui_sweep/overview.png)

![Independent amplitude, frequency and phase updates](independent_updates.png)

![Marker and DAC boundary timing](gui_sweep/startup.png)

![500 us waveform](gui_500us/overview.png)

![Continuous output through END and restart](gui_autonomy/overview.png)

![Long-period and autonomous output comparison](long_runs.png)

![Trigger compensation and DDR capture](gui_sweep/capture.png)

## 프로젝트와 검증 범위

원본 HWH/Tcl과 비교하여 디지털 IP {topology['cells']}개, 공통 설정 {topology['parameters_checked']}개, 내부 AXIS 연결 {topology['retained_bus_nets']}개를 대조했다. 기능 설정 및 유지 대상 내부 연결 차이는 없다. PS interconnect 제거에 따라 host AXI 주소만 slave-relative로 바뀌었다.

- **제거:** RFDC, Zynq PS/ARM, PS AXI interconnect, host DMA, 외부 DDR controller/PHY.
- **유지:** 실제 tProcessor, 모든 DAC generator와 routing, GPIO, readout/average buffer, FIR, trigger 보정, IQ64 DDR writer RTL.
- **경계 모델:** AXI-Lite host BFM, PMEM 1-clock ROM, RF DAC→ADC digital loopback, DDR AXI memory sink. PMEM 주소/명령과 DMEM sweep table은 원본 Python에서 생성된다.
- RF DAC 4.8 GSPS의 짝수 sample을 ADC 2.4 GSPS 입력으로 전달하고 경계 register 한 단을 둔다. 다른 ADC 입력은 idle이다. 실제 RFDC의 아날로그 응답과 지연, 보드 전파 지연, 아날로그 calibration, post-route timing/SDF는 이 검증에 포함하지 않는다.
- 기존 QICK IP끼리 충돌하는 내부 HDL 이름은 시뮬레이션용 복사본에서만 namespace를 붙였다. RTL datapath/state-machine은 대체하지 않았다. `namespace_manifest.json`에 원본/복사본 hash와 변환 내역을 기록했다.

재현 방법은 [README.md](README.md), 개별 수치는 각 시나리오의 `comparison.json`, 명령별 시점은 `command_timing.csv`, GUI 소스 출처는 `gui_sources.json`, 결과 파일 hash는 `result_provenance.json`에 있다. `gui_export.py`, `program.asm`, `pmem.hex`, `dmem.txt`를 함께 보존했다.
'''
    (HERE/'RESULTS.md').write_text(text, encoding='utf-8')
    print(HERE/'RESULTS.md')


if __name__ == '__main__':
    main()
