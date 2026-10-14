"""Preserve measured RTL residuals and their cumulative error as plots + CSV.

Only a finished 100-point x 2-mode run is accepted as a completed comparison.
--allow-partial produces explicitly watermarked progress evidence.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    states = json.loads((args.build/'status.json').read_text())
    repo = Path(__file__).resolve().parents[5]
    source_hashes = json.loads((args.build/'source_hashes.json').read_text())
    source_records = []
    for name, expected in source_hashes.items():
        source = Path(name)
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Width comparison sources changed since simulation: {source}')
        source_records.append(dict(path=source.resolve().relative_to(repo).as_posix(), sha256=expected))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'rtl_source_manifest.json').write_text(json.dumps(
        dict(repository_sources=source_records), indent=2)+'\n')
    data = {}
    summaries = {}
    complete = True
    for width in (32, 48, 64):
        path = args.build/str(width)/'width_sweep.csv'
        # Copy first, then parse the preserved bytes; never report a changing CSV.
        saved = args.out/f'width_{width}.csv'
        shutil.copyfile(path, saved)
        rows = list(csv.DictReader(saved.read_text().splitlines()))
        rows = [r for r in rows if None not in r.values()]
        if not rows:
            raise RuntimeError(f'No complete point for {width} bits yet')
        fields = {key: np.array([float(r[key]) for r in rows]) for key in rows[0]}
        data[width] = fields
        passed = states[str(width)]['state'] == 'passed'
        coverage = {(int(r['mode']), int(r['point'])) for r in rows}
        full = passed and len(rows) == 200 and coverage == {(m, p) for m in (0, 1) for p in range(100)}
        complete &= full
        good = fields['overflow'] == 0
        residual_int = [int(r['residual_area']) for r in rows]
        cumulative_int = []
        total = 0
        for value in residual_int:
            total += value
            cumulative_int.append(total)
        fields['cumulative_area'] = np.array(cumulative_int, dtype=np.float64)
        summaries[str(width)] = {
            'complete': full, 'points_finished': len(rows),
            'overflow_points': int(np.count_nonzero(~good)),
            'completed_shots': int(fields['completed'].sum()),
            'max_residual_effective_code_samples': max(map(abs, residual_int)),
            'max_cumulative_effective_code_samples': max(map(abs, cumulative_int)),
            'final_cumulative_effective_code_samples': total,
            'max_residual_without_overflow': float(np.max(np.abs(fields['residual_area'][good]))) if good.any() else None,
            'max_collection_error_without_overflow': float(np.max(np.abs((fields['hardware_area_before_dc']-fields['target_area'])[good]))) if good.any() else None,
            'max_rc_error_mv': float(fields['max_rc_error_mv'].max()),
            'max_end_rc_mv': float(np.abs(fields['end_rc_mv']).max()),
            'full_scale_unipolar_limit_s': (2**(width-1)-1)/(8192*4.8e9),
            'csv_sha256': hashlib.sha256(saved.read_bytes()).hexdigest(),
        }
        if width > 32 and (np.any(~good) or any(residual_int) or np.any(fields['completed'] != 1)):
            raise RuntimeError(f'{width}-bit DC compensation has an unexpected failure')
    if not complete and not args.allow_partial:
        raise RuntimeError('Width comparison is still incomplete; final report refused')

    # One effective DAC code = 800/8192 mV; one scalar sample = 1/4800 us.
    area_to_mv_us = 800.0/8192.0/4800.0
    colors = {32: '#bb302d', 48: '#1465aa', 64: '#148456'}
    plt.rcParams.update({'font.family': 'Malgun Gothic', 'font.size': 10, 'axes.unicode_minus': False})
    title_prefix = '' if complete else '진행 중 — '
    fig, axes = plt.subplots(3, 3, figsize=(16, 10), constrained_layout=True)
    for col, width in enumerate((32, 48, 64)):
        d = data[width]
        shot = d['mode']*100+d['point']+1
        bad = d['overflow'] != 0
        axes[0, col].set_title(f'{width} bit: {len(shot)}/200 shots, overflow {np.count_nonzero(bad)}')
        for row, key in enumerate(('residual_area', 'cumulative_area')):
            values = d[key]*area_to_mv_us
            axes[row, col].plot(shot, values, color=colors[width], lw=1.4)
            if bad.any():
                axes[row, col].scatter(shot[bad], values[bad], color='#bb302d', marker='x', s=16, label='overflow')
            if np.all(values == 0):
                axes[row, col].set_ylim(-area_to_mv_us, area_to_mv_us)
                axes[row, col].text(.5, .65, '디지털 잔여 면적 = 정확히 0', ha='center', transform=axes[row, col].transAxes)
            axes[row, col].ticklabel_format(axis='y', style='sci', scilimits=(-3, 4))
        axes[2, col].plot(shot, d['max_rc_error_mv'], color=colors[width], label='shot 최대 |RC 오차|')
        axes[2, col].plot(shot, np.abs(d['end_rc_mv']), color='#8059aa', lw=1, label='shot 종료 |RC 잔류|')
        axes[2, col].axhline(800/8192, color='gray', ls=':', label='유효 DAC 1 LSB')
        axes[2, col].set_xlabel('shot 순서: 1–100 고정전압 / 101–200 고정시간')
        axes[2, col].legend(fontsize=8)
        for row in range(3):
            axes[row, col].axvline(100.5, color='gray', ls='--', lw=.7)
            axes[row, col].grid(alpha=.25)
            axes[row, col].set_xlim(1, 200)
    for ax, label in zip(axes[:, 0], ('각 shot 보상 후 잔여 면적 (mV·µs)', '잔여 면적 누적합 (mV·µs)', '독립 RC 모델 전압 오차 (mV)')):
        ax.set_ylabel(label)
    fig.suptitle(title_prefix+'면적 누적기 32 / 48 / 64 bit 실제 RTL 비교\n'
                 '동일한 정수 증분 100점 sweep × DC 2모드, 4.8 GSPS, ±800 mV, τ=300 µs\n'
                 '물리 RC 상태는 shot 사이에 유지. 32 bit overflow 뒤 전압 오차에는 이전 shot 잔류도 포함.', fontsize=13)
    fig.savefig(args.out/'accumulated_error_by_width.png', dpi=170)
    plt.close(fig)

    # Keep a second wide-register plot so failed 32-bit data cannot hide their scale.
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    for width in (48, 64):
        d = data[width]; shot = d['mode']*100+d['point']+1
        style = '-' if width == 48 else '--'
        axes[0].plot(shot, d['cumulative_area']*area_to_mv_us, style, color=colors[width], label=f'{width} bit')
        axes[1].plot(shot, d['end_rc_mv']*1000, style, color=colors[width], label=f'{width} bit')
    axes[0].set_ylabel('DC 잔여 면적 누적합 (mV·µs)')
    axes[0].set_ylim(-area_to_mv_us, area_to_mv_us)
    axes[0].ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
    axes[1].set_ylabel('shot 종료 RC 잔류 전압 (µV)')
    axes[1].set_xlabel('shot 순서: 1–100 고정전압 / 101–200 고정시간')
    for ax in axes:
        ax.grid(alpha=.25); ax.legend(); ax.set_xlim(1, 200)
        ax.axvline(100.5, color='gray', ls='--', lw=.7)
    fig.suptitle(title_prefix+'48 / 64 bit 누적 오차 확대 비교\n디지털 면적과 아날로그 RC 잔류 전압은 서로 다른 지표입니다.')
    fig.savefig(args.out/'wide_accumulator_error_detail.png', dpi=170)
    plt.close(fig)
    common = min(len(data[48]['point']), len(data[64]['point']))
    same_wide_results = all(np.array_equal(data[48][key][:common], data[64][key][:common])
                            for key in data[48] if key != 'width')
    summary = {'complete': complete, 'build': str(args.build), 'widths': summaries,
               'identical_48_64_results': same_wide_results, 'compared_48_64_shots': common,
               'area_unit': 'effective DAC code * scalar sample', 'area_to_mv_us': area_to_mv_us,
               'analog_capacitor_reset_between_shots': False}
    (args.out/'width_results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    shutil.copyfile(args.build/'source_hashes.json', args.out/'source_hashes.json')
    lines = ['# 32/48/64-bit 누적 오차 비교', '',
             '**'+('전체 600 shots의 RTL 비교 완료.' if complete else '진행 중 결과입니다. 최종 통과 보고가 아닙니다.')+'**', '',
             '각 폭에서 동일한 100점 전압 sweep을 고정전압/고정시간 보상으로 실행합니다. 총 200 shots/폭입니다.',
             '원하는 SET sweep 전압의 반올림 방식을 바꾸지 않고, 실제 IIR 입력 샘플의 면적을 합산한 보상 결과입니다.', '',
             '| 폭 | 완료 shots | overflow | 최대 shot 잔여 면적 (code·sample) | 최대 누적 잔여 면적 (code·sample) | 최대 RC 오차 (mV) |',
             '|---|---:|---:|---:|---:|---:|']
    for w, s in summaries.items():
        lines.append(f"| {w} | {s['points_finished']}/200 | {s['overflow_points']} | {s['max_residual_effective_code_samples']} | {s['max_cumulative_effective_code_samples']} | {s['max_rc_error_mv']:.9g} |")
    lines += ['', f'48/64-bit 공통 {common} shots의 모든 수치 열(폭 식별자 제외) 동일 여부: **{same_wide_results}**.', '',
              '## 동일 입력 조건', '',
              'p=0..99이며, 아래 코드는 effective DAC code입니다. 1 code = 800/8192 mV입니다.', '',
              '| 구간 | 시간 | 각 지점의 실제 입력 코드 |',
              '|---|---:|---|',
              '| A | 100 µs | −614 + 12p |',
              '| B | 10 µs | −205 + 4p |',
              '| C | 400 µs | −1229 + 24p |', '',
              '고정전압 보상 크기는 200 mV(2048 code), 고정시간 보상은 200 µs(60,000 fabric clocks)입니다. 보상 부호는 IP가 누적 면적에서 결정합니다.',
              '위 정수 코드열 자체에 대한 면적 정확도 시험이며, 임의의 사용자 시작/끝 전압을 정확한 linspace로 만드는 시험이 아닙니다. 기존 SET sweep 증분의 양자화 정책은 별개로 유지됩니다.', '',
              '## 해석과 검증 범위', '',
              '- 32-bit의 overflow는 성공한 DC 보상이 아닙니다. 테스트벤치가 예상한 overflow 검출 자체에 PASS를 출력하더라도, 해당 입력 범위에서 사용 가능하다는 의미가 아닙니다.',
              '- overflow가 없다면 면적은 유효 DAC 코드의 정수 합이므로 별도의 소수 비트 반올림 오차가 없습니다. 48/64 bit 차이는 우선 누적 가능한 범위입니다.',
              '- 그림의 누적 오차는 실제 출력 잔여 면적의 signed 합입니다. 각 shot 오차도 별도 표시하므로 양/음 오차 상쇄로 실패를 숨기지 않습니다.',
              '- RC 모델은 모든 DAC scalar sample을 처리하고 물리 커패시터 상태를 shot 사이에 초기화하지 않습니다. 따라서 32-bit overflow 이후의 정상 범위 shot에도 아날로그 잔류가 전달됩니다.',
              '- τ=300 µs 단일 pole 회로 모델이며 실제 보드의 측정 오차를 보장하지 않습니다. IIR Q48/72-bit와 reciprocal Q64는 세 폭 모두 동일합니다.',
              '- 이번 그림은 실제 면적 엔진과 기존 IIR RTL을 사용한 폭 비교입니다. 전체 tProcessor/RF/DDR 시간 정렬, Vivado timing closure 및 bitstream 검증은 후속 검증 대상입니다.', '',
              '![누적 오차](accumulated_error_by_width.png)', '',
              '![48/64 bit 확대](wide_accumulator_error_detail.png)', '']
    (args.out/'WIDTH_COMPARISON.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
