"""Combine completed fine-duration evidence; never apply production changes."""
from datetime import datetime
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    software = read(HERE/'release/result.json')
    rtl = read(HERE/'rtl/result.json')
    equivalent = read(HERE/'rtl/final_recompile_equivalence.json')
    package = read(HERE/'release_package/manifest.json')
    baseline = read(HERE/'before_manifest.json')
    assert software['passed'] and software['tests'] == 680 and software['coarse_cases'] == 9
    assert rtl['passed'] and rtl['case_count'] == 9
    assert rtl['consecutive_short_samples'] == list(range(1,32))
    assert rtl['consecutive_short_bursts'] == rtl['short_carrier_prediction_bursts'] == 186
    assert equivalent['passed'] and equivalent['checked_cases'] == 8
    for path, digest in software['source_hashes'].items():
        assert sha(path) == digest.lower(), path
    for path, digest in baseline['source_hashes'].items():
        assert sha(path) == digest.lower(), f'Production source changed: {path}'
    for entry in package['files']:
        assert sha(entry['path']) == entry['sha256']
    for path, digest in rtl['statuses'].items():
        assert sha(path) == digest and read(path)['complete'] and read(path)['stage'] == 'passed'
    for path, digest in rtl['prepared_manifests'].items():
        assert sha(path) == digest
    result = dict(stage='validated_staged_await_v5_postbuild_gate',
        validation_complete=True, production_promoted=False,
        verified=datetime.now().astimezone().isoformat(), software_tests=680,
        coarse_gui_input_cases=9, actual_rtl_cases=9,
        implementation_files=package['files'],
        evidence={str(path):sha(path) for path in (
            HERE/'release/result.json', HERE/'release/baseline/baseline_equivalence.json',
            HERE/'rtl/result.json', HERE/'rtl/final_recompile_equivalence.json',
            HERE/'release_package/manifest.json')},
        minimum_active_samples=1, sample_period_ns=1/4.8,
        minimum_generator_busy_cycles=3, minimum_generator_busy_ns=10.,
        production_policy='After successful v5 postbuild gate, preserve that snapshot, promote the eight files with original-hash checks, recompile the nine baseline GUI cases, and refresh exact authorization hashes. Preserve v4 latency behavior; later v5 latency changes need separate GUI-to-v5 RTL validation.',
        board_access=False, firmware_changed=False, production_rtl_changed=False)
    (HERE/'results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    text = f'''# RF 샘플 단위 폭 제어 구현·검증 결과

검증본의 구현과 검증을 완료했습니다. 현재 사용하는 GUI 소스는 그대로이며,
진행 중인 v5 빌드의 최종 소스 해시 검사 통과 후 반영하도록 검증된 8개 파일을
`release_package/`에 보존했습니다. 보드 접속·업로드·펌웨어 교체·생산 RTL/XDC 변경은 하지 않았습니다.

## 최소 길이와 hardware sweep

현재 300 MHz × 16 samples/clock 설정의 정확한 간격은 **0.208333333 ns**입니다.
RF 활성 길이를 1–31샘플로 직접 설정할 수 있습니다. 1샘플은 0.208333 ns,
16샘플은 3.333333 ns, 31샘플은 6.458333 ns입니다.

짧은 펄스는 원하는 샘플만 출력하고 나머지를 0으로 채웁니다. 생성기가 차지하는
최소 재생 구간은 **3클록(10 ns)**이므로, 활성 길이와 다음 펄스를 예약할 수 있는
간격은 다릅니다. 시작 시각은 기존 300 MHz 클록 격자를 사용합니다.

16개 끝 패턴(각 128샘플, 채널당 총 2,048 complex samples)을 한 번 적재합니다.
Hardware sweep에서는 tProcessor의 DMEM 표로 주소·길이·시각을 선택하며,
각 점마다 PC에서 파형을 다시 업로드하지 않습니다.

## 새 실행 결과

| 검증 | 결과 |
|---|---|
| 관련 소프트웨어·GUI 회귀 | **680 PASS**, 정상 Qt 종료 |
| 기존 GUI 9조건 | PMEM/DMEM 바이트 동일 |
| 실제 GUI → tProcessor/TMUX → SG-v6/vendor DDS → v4 합산 RTL | **9조건 PASS** |
| 1–31샘플 전수 | 3경로 × 2회, **186펄스 PASS** |
| 190 MHz, 37°의 1–31샘플 | 긴 실제 RF 기준 파형과 비교, **186펄스 PASS** |
| Hardware duration × frequency | 경로별 32폭(81–112) × 2주파수 × 2회, 16개 끝 패턴과 경계 모두 PASS |
| 긴 펄스 | 10 µs+1샘플, 100 µs+1샘플 및 300 µs 부근의 3가지 반복 경계 PASS |
| 기타 | 음수/최대 허용 gain, 위상 차이, 명령 값·시각, 합산 lane 검사 PASS |

고정 gain의 실제 최대 오차는 {rtl['maximum_fixed_amplitude_error_codes']:.0f} DAC code,
190 MHz의 최대 RMS 오차는 {rtl['maximum_carrier_rms_codes']:.6f} code입니다.
1–31샘플 RF의 기준 파형 대비 최대 오차는
{rtl['maximum_short_carrier_prediction_error_codes']:.6f} code입니다.
요청 구간 밖의 예기치 않은 출력과 명령 시각/값 오류는 없습니다.

최종 DDS 지원 검사 및 점별 메타데이터 보완 후, 이미 실행한 8조건의 PMEM/DMEM,
envelope, 명령 예상값과 GUI 입력을 새로 생성해 바이트 동일성을 확인했습니다.
새 190 MHz 짧은 펄스 조건은 최종 코드로 직접 실행했습니다.

## 사용·저장 범위

- RF 설정의 기본 해제된 **Fine duration (DAC sample)** 옵션으로 사용합니다.
- 지원 구성은 DDS가 있는 SG-v6, 16 samples/clock 및 일치하는 generator/tProcessor clock입니다.
- 요청 manual gain 또는 보정으로 계산된 gain의 절댓값은 **16,383 이하**여야 합니다.
- Hardware duration sweep은 고정 길이 HOLD를 사용합니다. 메모리 부족, 출력 구간 겹침,
  공유 명령 포트 간격 부족이나 지원하지 않는 HOLD 연장은 명시적으로 거부합니다.
- 요청 시간과 실제 sample 수/길이를 구분해 저장합니다. T2 등 software sweep도
  모든 소프트웨어 좌표의 실제 폭을 저장하며 마지막 점 요약의 범위를 명시합니다.
- 기존 v4 지연 처리는 유지했습니다. 이 검증은 v5 지연 profile 연동이나 최종 routed
  timing 검증을 대체하지 않습니다. 보드 아날로그 상승/하강 시간은 측정하지 않았습니다.
- IIR 뒤 RF 합산 면적 및 clipping은 기존 AWG DC 면적 보상 대상이 아닙니다.

## 실패·수정 이력 보존

초기 xelab 병렬 옵션 오류, 초기화/펄스별 중복 register 쓰기로 명령이 늦어진 실제
RTL 실패를 보존했습니다. 불필요한 쓰기와 short-pulse tail 명령을 제거하고,
긴 tail에서 이미 준비된 register를 재사용했습니다. 오차 기준이나 명령 시각 검사는
완화하지 않았습니다. 최종 실행은 원래의 엄격한 검사로 통과했습니다.

## 증거

- [실제 RTL 상세 결과](rtl/REPORT.md), [기계 판독 결과](results.json)
- [실제 짧은 RF 파형](rtl/actual_short_rf_sample_width.png)
- [전체 폭 sweep 파형](rtl/actual_rf_sample_width.png)
- [소프트웨어 실행 결과](release/result.json), [소스 묶음](release_package/manifest.json)
- [점별 메타데이터 검증](software_point_metadata_fix/REPORT.md)

![1–31샘플 실제 RTL 파형](rtl/actual_short_rf_sample_width.png)
'''
    (HERE/'REPORT.md').write_text(text,encoding='utf8')
    print('FINE_DURATION_VALIDATION_PASS; production promotion waits for the original v5 postbuild gate')


if __name__ == '__main__':
    main()
