"""Record this display change and completed hold-sweep evidence separately."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
GUI = Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rtl = load(OUT / 'hold_rtl_verification.json')
    replay = load(OUT / 'current_gui_replay/result.json')
    rc_only = load(OUT / 'rc_only/verification.json')
    assert rtl['complete'] and replay['complete']
    assert rc_only['complete']
    assert rc_only['gui']['dc_enabled'] is False and rc_only['gui']['rc_enabled'] is True
    assert rc_only['dc_execute_commands'] == rc_only['iir_sample_mismatches'] == 0
    assert rc_only['command_value_mismatches'] == rc_only['command_timing_mismatches'] == 0
    assert all(c['rc_resets'] == c['zero_checks'] == rc_only['shots'] + 1
               and c['corrected_samples'] > 0 for c in rc_only['channels'])
    assert not replay['simulator_rerun']
    assert all(c['status'] == 'passed' for c in rtl['cases'].values())
    assert all(c['exit_code'] == 0 and c['old_sha256'] == c['new_sha256']
               for c in replay['cases'].values())
    suites = ET.parse(OUT / 'acquisition_tests_final.xml').getroot().iter('testsuite')
    counts = {name: 0 for name in ('tests', 'failures', 'errors', 'skipped')}
    for suite in suites:
        for name in counts:
            counts[name] += int(suite.attrib.get(name, 0))
    assert counts['tests'] >= 153 and counts['failures'] == counts['errors'] == counts['skipped'] == 0, counts
    latest_suites = ET.parse(OUT / 'acquisition_new_tests_final.xml').getroot().iter('testsuite')
    latest_counts = {name: 0 for name in counts}
    for suite in latest_suites:
        for name in latest_counts:
            latest_counts[name] += int(suite.attrib.get(name, 0))
    assert latest_counts['tests'] >= 19
    assert latest_counts['failures'] == latest_counts['errors'] == latest_counts['skipped'] == 0
    baseline = load(OUT / 'before_change_hashes.json')['files']
    changed = {}
    for name, before in baseline.items():
        path = Path(name)
        assert path.is_file(), name
        after = digest(path)
        if before != after:
            changed[name] = {'before': before, 'after': after}
    allowed = {str(GUI / name) for name in (
        'DCWaveform_Generator.py', 'dc_waveform_widgets.py', 'qick_front_panel.py')}
    assert set(changed) <= allowed, changed
    sources = {str(GUI / name): digest(GUI / name) for name in (
        'DCWaveform_Generator.py', 'dc_waveform_widgets.py', 'qick_front_panel.py',
        'acquisition_preview.py', 'test_acquisition_preview.py')}
    for name, sha in replay['source_hashes'].items():
        assert digest(Path(name)) == sha, f'Source changed after GUI replay: {name}'
    for name, sha in rc_only['source_hashes'].items():
        assert digest(Path(name)) == sha, f'Source changed after RC-only replay: {name}'
    figures = ['acquisition_waveform.png', 'acquisition_zoom.png', 'hold_duration_rtl.png']
    assert all((OUT / name).is_file() for name in figures)
    result = dict(complete=True, finished=datetime.now().astimezone().isoformat(),
                  software_tests=counts, final_display_rechecks=latest_counts,
                  rtl_cases=list(rtl['cases']), rc_only_verification=rc_only,
                  changed_existing_sources=changed, current_feature_sources=sources,
                  unchanged_baseline_files=len(baseline)-len(changed),
                  firmware_rtl_compiler_constraints_unchanged=True,
                  current_gui_pmem_dmem_equal=True,
                  figures={name: digest(OUT / name) for name in figures})
    (OUT / 'completion.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    report = f'''# Acquisition 표시 및 hold duration sweep 검증

2026-10-07 후속 GUI 작업. 두 저장소 `awg_tuning_v3` 유지. 코드 구현과 아래 범위의 검증을 완료했습니다.

## Waveform Plot

- Acquisition을 RF처럼 같은 시간축의 별도 패널에 표시합니다. 최종 사용자 요청에 따라 제목은 **Acquisition**, 그래프는 청록색 측정 구간 막대 하나만 남겼습니다. DDR write, trigger, 채널·표본율·샘플 수 및 기술 설명은 화면에 표시하지 않습니다. Hover에는 시작·종료와 길이만 표시합니다.
- HWH 표본율과 FIR 지연을 이용한 내부 계산은 유지합니다. `N / Fs`가 측정 길이이며 마지막 샘플 시각은 시작에서 `(N-1) / Fs`만큼 떨어집니다. 이 계산 설명은 보고서에만 남깁니다.
- 선택한 sweep point의 hold/RF duration을 반영합니다. RF 미리보기도 동일 지점을 따르며, 확대·축소 시 시간 단위가 바뀝니다. Fit은 파형 이후의 측정 구간까지 포함합니다.
- Acquisition 비활성화, 잘못된 입력, HWH 없음 및 장비 연결 변경 시 이전 측정 구간을 재사용하지 않습니다. HWH의 FIR 표본율과 지연을 모르면 숫자를 추정하지 않습니다.
- 표시는 요청 파형 기준의 nominal 미리보기입니다. FIR group delay를 기준으로 입력 구간을 표시하며 전체 FIR 응답 지지 구간을 뜻하지 않습니다. 연속 decimation 위상에 따라 경계가 한 표본 주기 이내로 달라질 수 있습니다. 실제 명령·pipeline 시각은 기존 compiled FIR/DC timing 보기에서 확인합니다. 이 기술 설명을 그래프에는 추가하지 않았습니다.

## 검증 결과

- GUI 및 관련 회귀 검사 **{counts['tests']}개 통과**, 실패·오류·skip 0. 기존 waveform/RF/front-panel 검사와 새 acquisition 검사 포함. 마지막 표시 수정 후 관련 **{latest_counts['tests']}개를 재검사**했으며 모두 통과했습니다. 재검사는 중복 항목이므로 고유 테스트 수에 더하지 않습니다.
- 실제 GUI 입력→Verilog: 고정전압/고정시간 DC 보상 **2조건, 각각 100점×2회**, 총 **400 shots** 통과.
- Hold 1.0–1.9 µs의 10값 × 전압 5–15 mV의 10값. 두 DAC 모두 실제 hold 길이 오차 **0 clocks**, 명령값·시각 불일치 **0**. 반복 및 전압 축 rewind도 확인했습니다.
- 각 조건에서 DAC별 보상/reset 200회, 잔여·누적 면적 0. RF 200펄스 폭오차 0, DDR 200 trigger/800 samples/400 AXI writes. 기존 출력16/DC시작17/RF42클록 및 DDR8712클록 지연을 유지합니다.
- 최종 수정된 GUI로 두 조건의 PMEM/DMEM을 다시 생성했고, 완료된 RTL이 실행한 입력과 바이트 단위로 일치했습니다. 이 단계에서 xsim을 재실행하지 않았습니다.
- 추가 요청인 **DC 끔 / RC 켬**은 별도 실제 GUI→Verilog 조건에서 검증했습니다. RC IIR 보정 활성과 DC 보상 명령·펄스 미생성을 함께 확인한 상세 수치와 범위는 [RC-only 보고서](rc_only/REPORT.md)에 보존했습니다. 종료 시 zero/reset이나 RC 적분 상태에 의한 DAC offset은 별도의 DC 면적 보상 펄스와 구분합니다.
- DDR 검증 입력은 300클록 timestamp stream입니다. 보드·ADC 아날로그 실측 또는 FIR 산술 전체 검증으로 해석하지 않습니다. 기존 SET sweep 이상 목표 전압 양자화 오차는 그대로입니다.

## 변경 범위와 산출물

표시 관련 기존 Python 3파일과 새 `acquisition_preview.py` 및 회귀 테스트를 추가/수정했습니다. 컴파일러, QICK Python 라이브러리, RTL, XDC와 기존 BIT/HWH/XSA는 작업 전 해시와 동일합니다. 새 합성·펌웨어 교체·32/64비트 비교·commit/push는 수행하지 않았습니다. 기존 배포 보고서는 당시 소스의 기록으로 보존합니다.

- [화면 캡처](acquisition_waveform.png) · [ns 확대 캡처](acquisition_zoom.png)
- [Hold sweep 실제 RTL 그래프](hold_duration_rtl.png) · [상세 RTL 보고서](HOLD_RTL_REPORT.md)
- [RC-only 검증](rc_only/REPORT.md) · [RC-only 수치](rc_only/verification.json)
- [소프트웨어 검사 XML](acquisition_tests_final.xml) · [마지막 표시 재검사](acquisition_new_tests_final.xml) · [현재 GUI 재생성 결과](current_gui_replay/result.json)
- [최종 해시·완료 확인](completion.json) · [RTL 검증 수치](hold_rtl_verification.json)

![Acquisition 표시](acquisition_waveform.png)

![Hold duration sweep 검증](hold_duration_rtl.png)
'''
    (OUT / 'REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
