"""Collect the two completed real-RTL runs without altering earlier signoff."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lanes(value):
    word=int(value,16)
    a=np.array([(word>>(16*i))&65535 for i in range(16)],dtype=np.int32)
    return np.where(a>=32768,a-65536,a)


def main():
    previous=json.loads((HERE.parent/'final_integration_manifest.json').read_text())
    # Verify production code and published firmware still match final signoff.
    current_hashes=previous['current_source_hashes']
    for name,digest in current_hashes.items():
        assert sha(Path(name))==digest, ('production source changed',name)
    manifest_path=ROOT/'qick/firmware/projects/qstl_awg_v4/build_manifest.json'
    assert sha(manifest_path)==previous['build_manifest']['sha256']
    firmware=json.loads(manifest_path.read_text())
    for artifact in firmware['artifacts']:
        assert sha(Path(artifact['path']))==artifact['sha256']
    protected=json.loads((HERE.parent/'protected_v3_sources.json').read_text())
    for name,digest in protected.items():
        assert sha(ROOT/name)==digest, ('protected source changed',name)
    gate=json.loads((HERE.parent/'prebuild_gate.json').read_text())
    rtl_hashes={name:digest for name,digest in gate['source_hashes'].items()
                if name.lower().endswith(('.sv','.v','.vhd','.xdc','.tcl'))}
    for name,digest in rtl_hashes.items():
        assert sha(ROOT/name)==digest, ('RTL/constraint/build source changed',name)
    results={}
    evidence={}
    fig,axes=plt.subplots(3,2,figsize=(14,9),sharex=True,constrained_layout=True)
    for hold in (1,2):
        source=Path(f'F:/Vivado_Output/a3sim1/rc_precomp_repeat_reset_hold_duration_2x2_v4_exact10us_hold{hold}_output_sum_awg_v3')
        result=json.loads((source/'result.json').read_text())
        assert result['validation_status']=='passed'
        assert result['points']==1 and result['repetitions']==2
        assert result['command_value_mismatches']==result['command_timing_mismatches']==0
        assert len(result['hardware_area_results'])==3
        match=json.loads((source/'gui_widget_match.json').read_text())
        assert match['pmem_equal'] and match['dmem_equal'] and match['gui_sequence_unmodified']
        prepared=json.loads((source/'prepared.json').read_text())
        for name,digest in prepared['program_source_hashes'].items():
            assert sha(Path(name))==digest, ('simulation source changed',name)
        destination=HERE/f'hold{hold}'
        destination.mkdir(exist_ok=True)
        for name in ('result.json','output_sum_result.json','gui_widget_match.json','gui_widget_pmem.hex',
                     'gui_input.json','gui_input.png','gui_compiled_timing.png','compiled_timing.json',
                     'pmem.hex','dmem.txt','program.asm','gui_export.py','prepared.json','expected.json',
                     'tb_rc_gui.sv','sources.prj','rtl_events.csv','rf_measurements.json',
                     'xsim.log','xvlog.log','xelab.log','area_ch0.csv','area_ch1.csv','area_ch3.csv'):
            shutil.copy2(source/name,destination/name)
            evidence[str(destination/name)]=sha(destination/name)
        results[f'hold{hold}']=dict(build_folder=str(source),result=result,gui_match=match)
        for row_index,suffix in enumerate((4,5,6)):
            path=source/f'physical_{suffix}.csv'
            evidence[str(path)]=sha(path)
            with path.open() as stream:
                rows=list(csv.DictReader(stream))
            pair=result['output_sum']['pairs'][row_index]
            measured=pair['measurements'][0]
            origin=measured['first_ramp_sum_input_cycle']+12
            data={int(r['cycle']):r for r in rows}
            selected=[r for r in rows if -1.05 <= (int(r['cycle'])-origin)/300 <= 40.025]
            times=np.array([(int(r['cycle'])-origin)/300 for r in selected])
            awg=np.array([lanes(data[int(r['cycle'])-12]['awg']).mean() for r in selected])*800/32768
            nominal=np.array([lanes(data[int(r['cycle'])-28]['raw']).mean() for r in selected])*800/32768
            dac=np.array([lanes(r['dac']) for r in selected])*800/32768
            axis=axes[row_index,hold-1]
            axis.fill_between(times,dac.min(axis=1),dac.max(axis=1),color='#d17b20',alpha=.5,
                              label='Final summed DAC (16-lane envelope)')
            axis.plot(times,awg,color='#174f85',lw=1.4,label='AWG after RC compensation')
            axis.plot(times,nominal,color='#333333',lw=1.1,ls='--',label='Nominal AWG before RC')
            start=measured['start_relative_first_ramp_us'];stop=measured['stop_relative_first_ramp_us']
            axis.axvspan(start,stop,color='#5e35b1',alpha=.09,label='Measured RF active interval')
            axis.axhline(0,color='#666666',lw=.6)
            for x in (10,20,30,40):axis.axvline(x,color='#999999',lw=.6,ls=':')
            axis.set_xlim(-1,40.02)
            axis.set_title(f'AWG {row_index+1} + RF {row_index+1} / DAC {suffix} — RF on HOLD {hold}')
            axis.set_ylabel('Digital DAC equivalent (mV)')
            if row_index==2:axis.set_xlabel('Time from first RAMP start (us)')
            if row_index==0:axis.legend(fontsize=7,loc='upper left')
    fig.suptitle('Actual GUI → PMEM/DMEM → tProcessor / AWG / DDS / sum / output-slice RTL\n'
                 '10 us RAMP, 10 us HOLD, 10 us RAMP, 10 us HOLD; DC + RC enabled',fontsize=14)
    fig.savefig(HERE/'rtl_hold10us.png',dpi=170)
    plt.close(fig)
    evidence[str(HERE/'rtl_hold10us.png')]=sha(HERE/'rtl_hold10us.png')
    for path in HERE.glob('*.py'):evidence[str(path)]=sha(path)
    status=dict(complete=True,verified_utc=datetime.now(timezone.utc).isoformat(),
        cases=results,production_source_unchanged=True,published_manifest_unchanged=True,
        firmware_artifacts_unchanged=3,protected_files_unchanged=len(protected),
        rtl_constraint_build_sources_unchanged=len(rtl_hashes),
        previous_final_integration_manifest_sha256=sha(HERE.parent/'final_integration_manifest.json'),
        evidence_sha256=evidence,
        finding='Existing one-clock guard follows each RAMP; GUI ideal preview omits it. '
                'RF starts exactly at the compiled/RTL HOLD and lasts 3000 clocks.',
        reran_synthesis=False,board_analog_measured=False)
    (HERE/'status.json').write_text(json.dumps(status,indent=2),encoding='utf8')
    samples=sum(p['physical_sample_checks'] for r in results.values() for p in r['result']['output_sum']['pairs'])
    text=f'''# 10µs RAMP/HOLD GUI → RTL 추가 검증

실제 GUI MainWindow 설정 → Run Experiment 컴파일 경로 → PMEM/DMEM → 실제 tProcessor/TMUX/AWG/DDS/합산/최종 출력 지연 RTL을 실행했습니다. 두 조건 모두 PASS입니다. 보드에서 아날로그 출력을 측정한 결과는 아닙니다.

| 설정 | 검증 결과 |
|---|---|
| 공통 입력 | 초기 0V SET 1µs + RAMP 10µs → HOLD 10µs → RAMP 10µs → HOLD 10µs |
| AWG1 / AWG2 / AWG3 | 0 → +10 → 0mV / 0 → −5 → 0mV / 0 → +2.5 → 0mV |
| RF | 세 RF 모두 190MHz, gain 2000, delay 0, duration 10µs |
| 조건 1 | Anchor SET = 첫 HOLD (`set_1`) |
| 조건 2 | Anchor SET = 둘째 HOLD (`set_2`) |
| 반복 | 각 조건 1점 × 2회, 세 RF/AWG 쌍 모두 검사 |
| 보상 | DC fixed_time 1µs + RC τ=10µs 활성화 |
| 구간 길이 설정 | Keep AWG segment length fixed; Keep pulse inside anchor SET 활성화 |
| GUI 입력 일치 | 두 조건 모두 PMEM / DMEM 바이트 일치; GUI sequence 변경 없음 |
| 명령 값 / 명령 시각 | 불일치 0 / 0 |
| RF와 실제 HOLD 시작 차이 | 0클록 |
| RF 폭 | 모든 12개 펄스 3000클록 = 10µs; 폭 오차 0 |
| 예상 밖 RF 펄스 | 0; RAMP 구간에서 RF 꺼짐 |
| 최종 DAC 샘플 | {samples:,}개 독립 signed 합산/포화/반올림 비교 통과 |
| DC 면적/초기화 | 각 출력 각 조건 2회 보상/초기화 확인, 잔여 정수 면적 0 |

## 기존 RAMP guard와 실제 출력 시각

기존 v3부터 RAMP 뒤에 `ramp_guard_cycles=1`이 있습니다. RAMP 데이터 자체는 정확히 48000샘플(3000클록, 10µs)이지만 다음 HOLD 경계는 이 1클록(3.333ns) 뒤입니다. GUI의 이상적인 시간축에는 이 guard가 표시되지 않습니다. 이번 검증에서는 이를 오차 없이 10µs 간격이라고 처리하지 않았습니다.

첫 RAMP 시작을 0으로 잡으면:

| RF 선택 | 이상적인 GUI 표시 | 실제 RTL RF 시작–종료 | 실제 HOLD와 차이 |
|---|---|---|---|
| 첫 HOLD | 10–20µs | 10.003333–20.003333µs | 0클록 |
| 둘째 HOLD | 30–40µs | 30.006667–40.006667µs | 0클록 |

따라서 RF는 선택한 실제 HOLD 전체에 맞고 RAMP와 겹치지 않습니다. 다만 이상적인 40µs 타임라인과는 guard 두 개만큼 차이가 납니다. 기존 guard/RTL/GUI/드라이버/XDC/펌웨어는 변경하지 않았습니다. 최종 출력 검사에는 합산 2클록과 기존 출력 지연 10클록을 포함했습니다.

## 증거

파형에서 점선은 RC 이전의 실제 AWG 값이고 파란 선은 RC 보상이 적용된 값입니다. HOLD 중 파란 선이 기울어지는 것은 RC 보상 동작입니다.

- [실제 RTL 출력 파형](rtl_hold10us.png)
- [첫 HOLD GUI 설정](hold1/gui_input.png), [둘째 HOLD GUI 설정](hold2/gui_input.png)
- [첫 HOLD 결과](hold1/result.json), [둘째 HOLD 결과](hold2/result.json)
- [입력/소스/증거 해시 및 전체 결과](status.json)
- 전체 16-lane 샘플 CSV와 isolated simulator snapshot은 각 결과의 `build_folder`에 있습니다.

생성된 테스트 사본과 추가 모니터만 새 폴더에 만들었습니다. 기존 최종 검증 보고서/해시와 배포 펌웨어를 덮어쓰지 않았고, 합성도 다시 실행하지 않았습니다. 합산은 AWG IIR 뒤이므로 AWG DC 보상은 추가 RF 면적이나 최종 clipping을 보상하지 않습니다.

후처리 기록: 두 xsim 실행은 RTL COMPLETE와 모든 RTL monitor 통과로 종료했습니다. 첫 Python 후처리에서는 새 검사기의 출력 지연 가정이 잘못되어 실패했으며, 실제 IP 설정 `axis_register_slice_nb N=10`에 맞게 검사기를 정정했습니다. 같은 저장 CSV를 `--analyze-only`로 재검사하여 모든 샘플이 통과했습니다. RTL 또는 허용오차는 변경하지 않았으며 시뮬레이션도 반복하지 않았습니다. 최초 로그는 `hold1_run.log`, `hold2_run.log`, 최종 후처리 로그는 `hold1_analysis.log`, `hold2_analysis.log`로 보존했습니다.
'''
    (HERE/'REPORT.md').write_text(text,encoding='utf8')
    print(json.dumps(dict(complete=True,cases=2,pairs=6,rf_pulses=12,physical_samples=samples,
                         rf_hold_skew_cycles=0,rf_width_error_cycles=0,ramp_guard_cycles=1)))


if __name__=='__main__':main()
