"""Collect actual GUI -> tProcessor -> AWG/RF/DDR RTL evidence and figures."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

CASES = {
    'GUI RF duration + voltage / fixed voltage': 'rc_precomp_repeat_reset_rf_duration_v3_pipe4_voltage_gui_overlap_readout_awg_v3',
    'Reversed axes / fixed voltage': 'rc_precomp_repeat_reset_rf_duration_v3_pipe4_voltage_reverse_overlap_readout_awg_v3',
    'GUI RF duration + voltage / fixed time': 'rc_precomp_repeat_reset_rf_duration_fixed_v3_pipe4_time_gui_after_readout_awg_v3',
    'Stability / fixed time': 'rc_precomp_repeat_reset_no_aux_grid_10x10_v3_pipe4_stability_awg_v3_stability',
}


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def verified_source_manifest(source, repo):
    """Bind completed results to the exact explicit RTL/input snapshot."""
    files = [Path(name) for name in re.findall(
        r'^sv xil_defaultlib "([^"]+)"', (source/'sources.prj').read_text(), re.M)]
    assert files, 'No explicit simulator RTL sources found'
    inputs = files + [source/'pmem.hex', source/'dmem.txt']
    fingerprint = hashlib.sha256(b''.join(path.read_bytes() for path in inputs)).hexdigest()
    prepared = json.loads((source/'prepared.json').read_text())
    assert fingerprint == prepared['fingerprint'], 'Completed RTL snapshot differs from current sources/inputs'
    records = []
    for path in files:
        try:
            relative = path.resolve().relative_to(repo)
        except ValueError:
            continue  # Generated wrapper/bench are covered by the combined fingerprint.
        records.append(dict(path=relative.as_posix(),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return dict(prepared_fingerprint=fingerprint, repository_sources=records)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--allow-partial',action='store_true')
    args=p.parse_args()
    repo=Path(__file__).resolve().parents[5]
    args.out.mkdir(parents=True,exist_ok=True)
    results={}
    areas={}
    timings={}
    for name,folder in CASES.items():
        source=args.build/folder
        if not (source/'result.json').exists():
            results[name]=dict(state='pending',folder=str(source))
            continue
        result=json.loads((source/'result.json').read_text())
        assert result['validation_status']=='passed'
        assert (result['points'],result['repetitions'])==(100,2)
        assert result['command_value_mismatches']==result['command_timing_mismatches']==0
        assert len(result['hardware_area_results'])==2
        destination=args.out/folder
        destination.mkdir(exist_ok=True)
        manifest=verified_source_manifest(source, repo)
        (destination/'rtl_source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        for filename in ('result.json','prepared.json','gui_export.py','program.asm','pmem.hex','dmem.txt',
                         'xsim.log','gui_widget_match.json','gui_widget_pmem.hex','gui_input.json',
                         'gui_dc_controls.png','gui_compiled_timing.png','gui_input.png',
                         'area_ch0.csv','area_ch1.csv','rf_measurements.json','ddr_capture.csv',
                         'fir_dc_timing.json','rc_analog.csv'):
            path=source/filename
            if path.exists():shutil.copy2(path,destination/filename)
        for ch in range(2):
            data=rows(source/f'area_ch{ch}.csv')
            assert len(data)==200
            assert all(int(row['residual_area'])==0 for row in data)
            assert all(int(row['first_area_cycle'])-int(row['command_cycle'])==17 for row in data)
            areas[name,ch]=data
        if result['sweep_case']:
            assert result['rf_measurements']['pulses']==200
            assert result['rf_measurements']['width_mismatch_pulses']==0
            assert len(result['ddr_capture_results'])==1
            match=json.loads((source/'gui_widget_match.json').read_text())
            assert match['pmem_equal'] and match['dmem_equal']
            if name.startswith('GUI '):
                assert match['gui_sequence_unmodified'] and not match['sequence_mutations']
            else:
                assert not match['gui_sequence_unmodified']
            captures=rows(source/'ddr_capture.csv')
            accepted={int(r['shot']):int(r['cycle']) for r in captures if r['event']=='trigger'}
            started={int(r['shot']):int(r['cycle']) for r in captures if r['event']=='start'}
            assert set(accepted)==set(started)==set(range(200))
            sample_rows=[r for r in captures if r['event']=='sample']
            assert len(sample_rows)==800
            for shot in range(200):
                samples=[r for r in sample_rows if int(r['shot'])==shot]
                assert [int(r['sample']) for r in samples]==list(range(4))
                assert [int(r['tag']) for r in samples]==[started[shot]+300*i for i in range(4)]
            ddr_delays=[started[i]-accepted[i] for i in range(200)]
            assert all(8712<=delay<9012 for delay in ddr_delays)
            rf=json.loads((source/'rf_measurements.json').read_text())
            timings[name]=dict(ddr_first_sample_delay=ddr_delays,
                rf_command_latency=[r['latency_cycles'] for r in rf],
                rf_width_error=[r['width_error_cycles'] for r in rf])
        results[name]=dict(state='passed',folder=str(source),result=result)
    complete=all(r['state']=='passed' for r in results.values())
    (args.out/'status.json').write_text(json.dumps(dict(complete=complete,cases=results),indent=2))
    if not complete and not args.allow_partial:
        raise RuntimeError('Actual RTL results are not all complete')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    if areas:
        fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
        for (name,ch),data in areas.items():
            label=f'{name}, DAC {ch+1}'
            scale=results[name]['result']['dac_current_ma'][ch]*40/8192/4800
            values=np.array([int(r['input_area']) for r in data])*scale
            error=np.array([int(r['residual_area']) for r in data])*scale
            axes[0].plot(np.arange(200),values,label=label,lw=1)
            axes[1].plot(error,lw=1)
            axes[2].plot(np.cumsum(error),lw=1)
        for ax in axes:ax.grid(alpha=.2)
        axes[0].set_ylabel('Captured area (mV us)')
        axes[0].legend(fontsize=8,ncol=2,loc='lower center',bbox_to_anchor=(.5,1.02))
        axes[1].set_ylabel('Area after DC (mV us)')
        axes[2].set_ylabel('Cumulative residual (mV us)')
        axes[2].set_xlabel('Shot index (100 points x 2 repetitions)')
        axes[1].text(.02,.8,'Every completed shot: exactly 0 effective-code samples',transform=axes[1].transAxes)
        fig.suptitle('48-bit production RTL: all 16 DAC samples counted before IIR\n'
                     + ('All cases complete' if complete else 'PARTIAL: only completed cases shown'))
        fig.savefig(args.out/'system_accumulated_area.png',dpi=160)
        plt.close(fig)
    if timings:
        fig,axes=plt.subplots(4,1,figsize=(12,9),sharex=True,layout='constrained')
        for name,data in timings.items():
            area=areas[name,0]
            axes[0].plot([int(r['first_area_cycle'])-int(r['command_cycle']) for r in area],label=name)
            axes[1].plot(data['rf_command_latency'],label=name)
            axes[2].plot(data['rf_width_error'],label=name)
            axes[3].plot(data['ddr_first_sample_delay'],label=name)
        for ax in axes:ax.grid(alpha=.2)
        axes[0].set_ylabel('DC start latency\n(clocks, pre-IIR)')
        axes[0].legend(fontsize=8)
        axes[1].set_ylabel('RF start latency\n(clocks)')
        axes[2].set_ylabel('RF width error\n(clocks)')
        axes[3].set_ylabel('DDR first sample\n(clocks after trigger)')
        axes[3].axhline(8712,color='k',ls='--',lw=.8)
        axes[3].axhline(9012,color='k',ls='--',lw=.8)
        axes[3].text(.02,.88,'8712-clock delay + wait for next 300-clock FIR sample',
                     transform=axes[3].transAxes,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
        axes[3].set_xlabel('Shot index (100 points x 2 repetitions)')
        fig.suptitle('Actual RTL timing: GUI commands, hardware DC, RF DDS, DDR capture\n'
                     +('All cases complete' if complete else 'PARTIAL: only completed cases shown'))
        fig.savefig(args.out/'system_timing.png',dpi=160)
        plt.close(fig)
        (args.out/'timing_measurements.json').write_text(json.dumps(timings,indent=2))
    lines=['# GUI → 실제 RTL 검증','',f'- 전체 완료: {complete}',
        '- 두 AWG의 기존 정수 고정 전압 증분/add/rewind를 그대로 사용했습니다.',
        '- 보상 잔여 면적 0은 실행된 디지털 파형에 대한 결과입니다. 요청한 이상 전압과 SET sweep 누적 양자화 오차가 0이라는 의미가 아닙니다.',
        '- GUI RF 시험: 실제 GUI MainWindow 설정을 읽는 Run Experiment 경로의 프로그램을 변경 없이 사용하고 exported PMEM/DMEM과 바이트 일치를 확인했습니다.',
        '- Reversed axes 시험: GUI 값을 읽은 뒤 시험용으로 sweep 축 순서를 반전한 추가 compiler/RTL 스트레스 조건입니다. GUI를 변경 없이 실행한 조건과 구분합니다.',
        '- RTL: 실제 tProcessor/TMUX/AWG/RF DDS 및 DDR capture IP. DDR 입력은 300클록마다 나오는 합성 timestamp stream이며 ADC/아날로그 실측 또는 FIR 산술 검증은 아닙니다.',
        '- IIR 정수 recurrence는 전 클록/16 lanes에서 독립 계산과 일치해야 통과합니다. 아날로그 RC는 독립 수치 모델이며 capacitor state를 shot마다 강제로 초기화하지 않습니다.',
        '- Stability 시험은 실제 Stability builder의 10×10 전압 grid, 역방향/축반전, 보상 및 반복을 검증했습니다. 해당 경우 자체에는 RF/DDR가 포함되지 않습니다.',
        '', '| 조건 | 상태 | 명령/시각 불일치 | 각 DAC 보상/초기화 | RF 폭 오차 |',
        '|---|---|---|---|---|']
    details=[]
    for name,info in results.items():
        result=info.get('result',{})
        lines.append(f'| {name} | {info["state"]} | '+('0 / 0 | 200 / 200 | '+('0 clocks' if result.get('sweep_case') else '해당 없음') if result else '미완료 | 미완료 | 미완료')+' |')
        if result.get('sweep_case'):
            details.extend(['',f'### {name}',f'- DDR: {result["ddr_capture_results"][0]}',
                f'- RF 명령→실제 출력 지연: {result["rf_measurements"]["latency_cycles"]} clocks (기존 RF 경로)',
                '- 새 AWG 파이프라인 5클록은 GUI의 AWG segment/RF/DDR trigger 기준에 함께 반영됩니다. 설정된 DDR 8,712클록 지연 자체는 바뀌지 않습니다.'])
            for text in result['analog_results']:
                match=re.search(r'ch=(\d+) max_error_codes=([\d.]+)',text)
                if match and int(match[1])<2:
                    ch=int(match[1]); scale=result['dac_current_ma'][ch]*40/32768
                    details.append(f'- DAC {ch+1}: 독립 RC 모델 최대 오차 {float(match[2])*scale:.9f} mV '
                                   f'(한 effective DAC LSB {4*scale:.9f} mV).')
    lines.extend(details)
    lines.extend(['','![보상 누적 면적](system_accumulated_area.png)',
        '', '![실제 RTL 타이밍](system_timing.png)' if timings else 'RF/DDR 타이밍 그림: 실행 완료 대기 중.',
        '', '전체 FPGA setup/hold closure와 BIT/HWH 배포 여부는 별도 최종 빌드 보고서를 확인해야 합니다. 이 RTL 보고서만으로 펌웨어 배포 완료를 의미하지 않습니다.'])
    (args.out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(complete=complete,states={k:v['state'] for k,v in results.items()})))


if __name__=='__main__':main()
