"""Summarize only completed RTL evidence; retain honest progress for active runs."""
import argparse
import json
from pathlib import Path
import re


CASES = (
    'rc_precomp_repeat_reset_no_aux_grid_200x200_todo_increment_20261004_awg_v2',
    'rc_precomp_repeat_reset_no_aux_grid_200x200_todo_increment_20261004_awg_v2_stability',
    'rc_precomp_repeat_reset_rf_duration_20x20_todo_fixed_time_20261004_awg_v2',
    'rc_precomp_repeat_reset_rf_duration_20x20_todo_fixed_voltage_minset_20261004_awg_v2',
    'rc_precomp_repeat_reset_rf_duration_fixed_20x20_todo_fixed_time_20261004_awg_v2',
    'rc_precomp_repeat_reset_rf_duration_fixed_20x20_todo_fixed_voltage_minset_20261004_awg_v2',
)


def complete_cycle(path):
    if not path.exists():return 0
    with path.open('rb') as f:
        f.seek(0,2);size=f.tell();f.seek(max(0,size-8192));tail=f.read().splitlines()
    # Last row can be partially buffered while xsim is writing.
    for line in reversed(tail[:-1]):
        fields=line.decode(errors='replace').split(',')
        if len(fields)==4 and fields[0].isdigit() and len(fields[3])==40:
            return int(fields[0])
    return 0


def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    statuses=[]
    for name in CASES:
        folder=args.build/name
        prepared=json.loads((folder/'prepared.json').read_text()) if (folder/'prepared.json').exists() else {}
        result=json.loads((folder/'result.json').read_text()) if (folder/'result.json').exists() else None
        row=dict(case=name,prepared=prepared,completed=result is not None,
                 last_complete_event_cycle=complete_cycle(folder/'rtl_events.csv'),
                 disk_mib=sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())/2**20)
        if result:
            assert result['validation_status']=='passed'
            assert result['points']==(40000 if 'grid_200x200' in name else 400)
            assert result['repetitions']==2
            assert result['command_value_mismatches']==result['command_timing_mismatches']==0
            resets=result['points']*2+1
            assert len(result['reset_results'])==2
            assert all(f'resets={resets} zero_checks={resets}' in line for line in result['reset_results'])
            if 'grid_200x200' not in name:
                assert result['rf_measurements']['pulses']==800
                assert result['rf_measurements']['width_mismatch_pulses']==0
            row['result']=result
        statuses.append(row)
    (args.out/'rtl_status.json').write_text(json.dumps(statuses,indent=2))
    software=args.out/('software_final' if (args.out/'software_final/exit_codes.json').exists() else 'software')
    tests=json.loads((software/'exit_codes.json').read_text(encoding='utf-8-sig'))
    lines=['# TODO 검증 현황','','실제 RTL 완료는 각 실행의 `result.json`과 명령 값·시각 비교 통과로 판단한다.',
           '소프트웨어 명령 모델을 실제 RTL 완료로 대체하지 않는다.','',
           '| 경우 | 지점 × 반복 | 실제 RTL | 마지막 기록 clock / 전체 clock | 용량 MiB |',
           '|---|---:|---|---:|---:|']
    for row in statuses:
        pre=row['prepared']
        lines.append(f"| {row['case']} | {pre.get('points','?')} × {pre.get('shots',0)//max(1,pre.get('points',0))} | "
                     f"{'통과' if row['completed'] else '미완료'} | {row['last_complete_event_cycle']} / {pre.get('cycles','?')} | {row['disk_mib']:.1f} |")
    lines+=['','## 검증 범위','',
        '- 두 DAC virtual gate: AWG Tuning 200×200×2 정방향, Stability 200×200×2 역방향 및 축 순서 반전.',
        '- 행렬 `[[1, 0.23], [-0.17, 1]]`, DAC full-scale ±800/±400 mV. X 5→15 mV, Y −9→7 mV.',
        '- RF duration × voltage: fixed/extend_by_rf_duration × DC fixed_time/fixed_voltage 네 조합. 각 20×20×2 actual RTL, 두 AWG+RF DDS+실제 tProcessor/TMUX/RC.',
        '- 고정전압 보상 20 mV의 최초 두 RTL 실행은 1~2클록 보상이 3클록으로 늘어나는 실패를 검출했다. 해당 rev2 기록을 통과로 세지 않는다. 현재 소프트웨어는 이런 조건을 실행 전에 거부한다.',
        '- 지원 범위 RTL 재검증은 fixed_voltage에서 extend=0.5 mV, fixed=2 mV의 별도 조건이다. 사용자 설정을 자동 변경한 것이 아니다. 자세한 실패 및 검출 근거는 SHORT_DC_FINDING.md 참조.',
        '- RF 200×200의 양방향·축 순서·두 DC 모드는 별도 소프트웨어 검사다. RF 전체 200×200 RTL이라고 부르지 않는다.',
        '- 대규모 grid에는 매 clock raw AWG 및 RC 정수 연산 검사가 있다. analog RC 통과 오차와 SET 명령의 이상 목표 전압 오차는 별개다.',
        '- 실제 ADC/RFDC, ARM, 보드에서의 아날로그 측정을 포함하지 않는다. RF DDS의 디지털 파형을 검사한다.',
        '- 이전 FIR/DC 실행 순서 기능은 기존 8종 실제 RTL 증거와 이번 소프트웨어 회귀 검사로 확인한다.',
        '- 추가 면적 누적 IP와 bitstream 변경은 하지 않았다. LTspice 비교는 별도 보고서 참조.','',
        '## 소프트웨어 프로세스 종료 코드','']
    for item in tests:
        log=(software/f"{item['module']}.log").read_text(errors='replace')
        counts=re.findall(r'\d+ passed[^\r\n]*',log)
        lines.append(f"- `{item['module']}`: exit={item['exit_code']}, {counts[-1] if counts else '통과 개수 미확인'}")
    lines+=['','## 남는 정수 증분 오차','',
        '사용자의 2026-10-04 요청에 따라 점별 nearest-DAC 전압표를 제거하고 기존 고정 증분/add/rewind 방식을 유지했다.',
        '32-bit Q18 확장은 RAMP step에만 적용되며 SET의 DAC 코드 간격은 바뀌지 않는다.',
        '따라서 명령 값·시각 RTL 검사 통과를 이상적인 요청 전압과 정확히 일치한다는 뜻으로 해석하면 안 된다.',
        '상세 수치는 `increment_errors.json`, 파형 비교는 `virtual_grid_fixed_time.png` 및 `LTSPICE_REPORT.md`에 있다.',
        '특히 fixed_time DC 전압 증분도 누적 양자화 오차를 가지며, 기존 방식에서는 정확한 면적 상쇄를 일반적으로 보장하지 않는다.',
        '증분 누적 결과가 DAC/보상 레지스터 범위를 넘으면 RC 옵션과 무관하게 실행 전에 오류를 낸다.','']
    (args.out/'RTL_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps([dict(case=r['case'],completed=r['completed'],cycle=r['last_complete_event_cycle'],
                           cycles=r['prepared'].get('cycles'),mib=round(r['disk_mib'],1)) for r in statuses],indent=2))


if __name__=='__main__':main()
