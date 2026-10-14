"""Report the selected 48-bit production design without rerunning width selection."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[5]
    state = json.loads((a.build/'status.json').read_text())
    assert set(state) == {'48'}, 'This report accepts one 48-bit run only'
    assert state['48']['state'] == 'passed' and state['48']['exit_code'] == 0
    hashes = json.loads((a.build/'source_hashes.json').read_text())
    records = []
    for name, expected in hashes.items():
        source = Path(name)
        assert sha(source) == expected, f'Stale source: {source}'
        records.append(dict(path=source.relative_to(repo).as_posix(), sha256=expected))
    rows = list(csv.DictReader((a.build/'48/width_sweep.csv').read_text().splitlines()))
    assert len(rows) == 200
    assert {(int(r['mode']), int(r['point'])) for r in rows} == {(m, p) for m in (0, 1) for p in range(100)}
    assert all(int(r['width']) == 48 and int(r['overflow']) == 0 and int(r['completed']) == 1 for r in rows)
    residual = [int(r['residual_area']) for r in rows]
    collection = [int(r['hardware_area_before_dc'])-int(r['target_area']) for r in rows]
    assert not any(residual) and not any(collection), 'DC sample-area arithmetic mismatch'
    cumulative = []
    total = 0
    for value in residual:
        total += value
        cumulative.append(total)
    max_rc = [float(r['max_rc_error_mv']) for r in rows]
    end_rc = [float(r['end_rc_mv']) for r in rows]
    assert max(max_rc) < 800/8192, 'Independent RC error exceeds an effective DAC LSB'
    a.out.mkdir(parents=True, exist_ok=True)
    saved = a.out/'width_48.csv'
    shutil.copyfile(a.build/'48/width_sweep.csv', saved)
    result = dict(complete=True, points_finished=200, completed_shots=200, overflow_points=0,
                  max_residual_effective_code_samples=max(map(abs, residual)),
                  max_cumulative_effective_code_samples=max(map(abs, cumulative)),
                  max_collection_error_without_overflow=max(map(abs, collection)),
                  final_cumulative_effective_code_samples=total,
                  max_rc_error_mv=max(max_rc), max_end_rc_mv=max(map(abs, end_rc)), csv_sha256=sha(saved))
    summary = dict(complete=True, selected_width=48, comparison_performed=False,
                   build=str(a.build), widths={'48': result}, analog_capacitor_reset_between_shots=False)
    (a.out/'width_results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (a.out/'rtl_source_manifest.json').write_text(json.dumps(dict(repository_sources=records), indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False})
    shot = list(range(1, 201))
    scale = 800/8192/4800
    fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    for axis, values, label in zip(ax, (residual, cumulative), ('shot 잔여 면적', '누적 잔여 면적')):
        axis.plot(shot, [v*scale for v in values], color='#176aa6')
        axis.set_ylabel(label+' (mV·µs)')
        axis.set_ylim(-scale, scale)
        axis.text(.5, .7, '200 shots 모두 정확히 0', transform=axis.transAxes, ha='center')
        axis.axvline(100.5, color='gray', ls='--'); axis.grid(alpha=.25)
    ax[-1].set_xlabel('1–100: 고정전압 / 101–200: 고정시간')
    fig.suptitle('선택된 48비트 DC 보상 — 실제 RTL 잔여 면적과 누적 오차')
    fig.savefig(a.out/'accumulated_error_48.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    ax[0].plot(shot, max_rc, label='shot 최대 |RC 오차|')
    ax[0].axhline(800/8192, color='gray', ls=':', label='유효 DAC 1 LSB')
    ax[0].set_ylabel('최대 전압 오차 (mV)'); ax[0].legend()
    ax[1].plot(shot, [v*1000 for v in end_rc], color='#8059aa')
    ax[1].set_ylabel('shot 종료 RC 잔류 (µV)')
    ax[1].set_xlabel('1–100: 고정전압 / 101–200: 고정시간')
    for axis in ax:
        axis.axvline(100.5, color='gray', ls='--'); axis.grid(alpha=.25)
    fig.suptitle('48비트 실제 IIR RTL + 독립 RC 모델 — 커패시터 상태를 shot 사이에 유지')
    fig.savefig(a.out/'rc_error_48.png', dpi=160); plt.close(fig)
    report = f'''# 선택된 48비트 DC 보상 검증

현재 생산 RTL로 100점 전압 sweep × DC 2모드 = 200 shots를 완료했습니다.
32/64비트 폭 선택 비교는 다시 실행하지 않았습니다. 과거 비교와 그림은 ../width_comparison에 보존합니다.

- overflow 0, 완료 shots 200, 실제 샘플 면적 수집 오차 0.
- 모든 shot의 디지털 잔여 면적 0, 누적 잔여 면적 0.
- 독립 RC 모델 최대 전압 오차 {result['max_rc_error_mv']:.12g} mV.
- shot 종료 RC 잔류 최대 {result['max_end_rc_mv']:.12g} mV.
- 실제 입력: A 100µs (−614+12p), B 10µs (−205+4p), C 400µs (−1229+24p) effective DAC codes, p=0..99.
- 고정전압 200mV, 고정시간 200µs, ±800mV, 4.8GSPS, τ=300µs.
- RC 커패시터의 상태는 shot 사이에 유지됩니다. 디지털 면적과 RC 잔류 전압은 다른 지표입니다.
- 기존 정수 SET sweep의 이상 목표 전압 양자화 오차를 고친 시험이 아닙니다.
- GUI→RTL의 RF/DDR 정합, 실제 보드 측정, 전체 FPGA timing은 이 단독 시험과 별개입니다.

![누적 오차](accumulated_error_48.png)

![RC 오차](rc_error_48.png)
'''
    (a.out/'REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
