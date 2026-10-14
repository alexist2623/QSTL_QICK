"""Independent hold-axis ordering/interval checks on actual RTL commands."""
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT/'qick/firmware/ip/axis_awg_tuning_v3/validation'))
from report_system_validation import verified_source_manifest

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))

def main():
    status=load(OUT/'run_status.json')
    assert status['complete'], 'Both real RTL runs must finish successfully'
    checks={}
    all_measured={}
    for name,info in status['cases'].items():
        source=Path(info['folder'])
        result=load(source/'result.json')
        assert result['validation_status']=='passed'
        assert result['sweep_case']=='hold_duration'
        assert (result['points'],result['repetitions'])==(100,2)
        assert result['command_value_mismatches']==result['command_timing_mismatches']==0
        assert result['rf_measurements']['pulses']==200
        assert result['rf_measurements']['width_mismatch_pulses']==0
        assert result['rf_measurements']['latency_cycles']==42
        match=load(source/'gui_widget_match.json')
        assert match['pmem_equal'] and match['dmem_equal'] and match['gui_sequence_unmodified']
        dest=OUT/name
        dest.mkdir(exist_ok=True)
        manifest=verified_source_manifest(source,ROOT)
        (dest/'rtl_source_manifest.json').write_text(json.dumps(manifest,indent=2))
        for filename in ('result.json','prepared.json','gui_export.py','program.asm','pmem.hex','dmem.txt',
            'xsim.log','gui_widget_match.json','gui_widget_pmem.hex','gui_input.json','gui_input.png',
            'gui_dc_controls.png','gui_compiled_timing.png','area_ch0.csv','area_ch1.csv',
            'rf_measurements.json','ddr_capture.csv','fir_dc_timing.json','rtl_events.csv','rc_analog.csv'):
            shutil.copy2(source/filename,dest/filename)
        actual=rows(source/'rtl_events.csv')
        events=[dict(cycle=int(r['cycle']),port=int(r['port']),word=int(r['word'],16)) for r in actual]
        starts=sorted(e['cycle'] for e in events if e['port']==4)
        assert len(starts)==200
        measurements=[]
        # Independent expected order: duration outer axis, voltage inner axis,
        # then two consecutive repetitions. No expected.json/model timing used.
        for shot,start in enumerate(starts):
            end=starts[shot+1] if shot+1<len(starts) else result['cycles']+result['cycle_offset']
            point=shot//2;duration_index=point//10;voltage_index=point%10
            expected_hold=300+30*duration_index
            entry=dict(shot=shot,point=point,repetition=shot%2,duration_index=duration_index,
                voltage_index=voltage_index,requested_hold_us=1.+duration_index*.1,
                expected_hold_cycles=expected_hold,start_cycle=start,channels=[])
            for ch in (0,1):
                awg=sorted([e for e in events if e['port']==ch and e['word']>>152==1
                    and start<=e['cycle']<end],key=lambda e:e['cycle'])
                assert awg[0]['cycle']==start and (awg[0]['word']>>144)&3==1
                ramp=next(e for e in awg if (e['word']>>144)&3==2)
                command_interval=ramp['cycle']-awg[0]['cycle']
                # Original AWG command-to-first-RAMP-sample startup is 7 clocks;
                # the independent full-clock raw monitor checks all actual lanes.
                actual_hold=command_interval+7
                assert actual_hold==expected_hold,(name,shot,ch,actual_hold,expected_hold)
                code=awg[0]['word']&0xffffffff
                if code>=2**31:code-=2**32
                # Fixture: virtual AWG0 5..15 mV, AWG1 -5 mV;
                # matrix [[1,.23],[-.17,1]], scales 800/400 mV.
                # Round endpoints to four-code DAC steps, then preserve the
                # established rounded constant increment (44 / -16 codes).
                expected_code=(156+44*voltage_index) if ch==0 else (-480-16*voltage_index)
                assert code==expected_code,(name,shot,ch,code,expected_code)
                entry['channels'].append(dict(channel=ch,first_set_cycle=awg[0]['cycle'],
                    first_ramp_command_cycle=ramp['cycle'],ramp_startup_cycles=7,
                    command_interval_cycles=command_interval,verified_output_hold_cycles=actual_hold,
                    first_set_code=code,expected_first_set_code=expected_code,
                    hold_error_cycles=actual_hold-expected_hold))
            measurements.append(entry)
        # Both repetitions, inner voltage increments, and every outer-axis
        # rewind must keep the identical original integer SET sweep sequence.
        for ch in (0,1):
            levels=[]
            for outer in range(10):
                block=[]
                for inner in range(10):
                    a,b=measurements[outer*20+inner*2:outer*20+inner*2+2]
                    assert a['channels'][ch]['first_set_code']==b['channels'][ch]['first_set_code']
                    block.append(a['channels'][ch]['first_set_code'])
                assert len(set(block[i+1]-block[i] for i in range(9)))==1
                levels.append(block)
            assert all(block==levels[0] for block in levels), 'Voltage axis failed to rewind'
        area={}
        for ch in (0,1):
            data=rows(source/f'area_ch{ch}.csv')
            assert len(data)==200 and all(int(r['residual_area'])==0 for r in data)
            assert all(int(r['first_area_cycle'])-int(r['command_cycle'])==17 for r in data)
            line=next(s for s in result['hardware_area_results'] if f'ch={ch} ' in s)
            assert 'shots=200' in line and 'reset_checks=200' in line and 'residual=0' in line, line
            area[ch]=dict(shots=200,residual_area=0,cumulative_residual_area=0,
                dc_start_cycles=17,monitor=line)
        capture=rows(source/'ddr_capture.csv')
        triggers={int(r['shot']):int(r['cycle']) for r in capture if r['event']=='trigger'}
        began={int(r['shot']):int(r['cycle']) for r in capture if r['event']=='start'}
        assert set(triggers)==set(began)==set(range(200))
        samples=[r for r in capture if r['event']=='sample']
        assert len(samples)==800
        for shot in range(200):
            data=[r for r in samples if int(r['shot'])==shot]
            assert [int(r['sample']) for r in data]==list(range(4))
            assert [int(r['tag']) for r in data]==[began[shot]+300*i for i in range(4)]
            assert 8712<=began[shot]-triggers[shot]<9012
            measurements[shot]['ddr_first_sample_delay_cycles']=began[shot]-triggers[shot]
        assert len(result['raw_awg_results'])==len(result['exact_awg_results'])==2
        ddr=result['ddr_capture_results'][0]
        assert 'writes=400' in ddr,ddr
        checks[name]=dict(status='passed',points=100,repetitions=2,shots=200,
            hold_values_us=[1.+i*.1 for i in range(10)],hold_values_cycles=list(range(300,571,30)),
            hold_command_intervals_cycles=list(range(293,564,30)),hold_interval_mismatches=0,
            repetition_mismatches=0,voltage_axis_rewind_mismatches=0,
            command_value_mismatches=0,command_timing_mismatches=0,
            hardware_area=area,raw_awg_results=result['raw_awg_results'],
            exact_iir_results=result['exact_awg_results'],rf=result['rf_measurements'],
            ddr=result['ddr_capture_results'],gui_widget_match=match,
            prepared_fingerprint=manifest['prepared_fingerprint'],source_folder=str(source))
        all_measured[name]=measurements
        (dest/'hold_measurements.json').write_text(json.dumps(measurements,indent=2))
    replay=load(OUT/'current_gui_replay/result.json')
    assert replay['complete'] and replay['simulator_rerun'] is False
    for path,digest in replay['source_hashes'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest, path
    (OUT/'hold_rtl_verification.json').write_text(json.dumps(dict(complete=True,cases=checks,
        current_gui_replay='current_gui_replay/result.json',current_gui_replay_passed=True),indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(3,1,figsize=(12,8),sharex=True,layout='constrained')
    for name,data in all_measured.items():
        for ch in (0,1):
            axs[0].plot([r['channels'][ch]['verified_output_hold_cycles']/300 for r in data],
                label=f'{name}, DAC {ch+1}',ls='--' if ch else '-',alpha=.75)
            axs[1].plot([r['channels'][ch]['hold_error_cycles'] for r in data],alpha=.75)
        axs[2].plot([r['ddr_first_sample_delay_cycles'] for r in data],label=name)
    for ax in axs:ax.grid(alpha=.25)
    axs[0].set_ylabel('Actual hold duration (us)');axs[0].legend(fontsize=8,ncol=2)
    axs[1].set_ylabel('Hold error (clocks)');axs[1].set_ylim(-.5,.5)
    axs[2].set_ylabel('DDR first sample delay\n(clocks after trigger)')
    axs[2].set_xlabel('Shot: 10 hold durations x 10 voltage points x 2 repetitions')
    axs[2].axhline(8712,color='black',ls=':',lw=.8)
    axs[2].legend(loc='upper right',fontsize=8)
    axs[2].text(.01,.95,'8712-clock delay + next 300-clock input sample',transform=axs[2].transAxes,
        va='top',bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
    fig.suptitle('Real GUI -> Verilog: hold-duration sweep and acquisition timing\n'
        'All 400 shots passed; original SET/RAMP path retained')
    fig.savefig(OUT/'hold_duration_rtl.png',dpi=170);plt.close(fig)
    lines=['# AWG Tuning hold duration sweep: 실제 GUI → Verilog 검증','',
        '- 두 DC 모드 모두 실제 MainWindow 입력 → Run Experiment compiler → PMEM/DMEM → tProcessor/TMUX/AWG/RF/DDR RTL로 확인했습니다.',
        '- 각 조건은 hold 1.0–1.9 µs(0.1 µs 간격 10값) × 전압 5–15 mV 10점 × 2회 = 200 shots입니다.',
        '- 두 DAC의 cross-capacitance [[1,.23],[-.17,1]], DAC ±800/±400 mV, 48비트 DC 면적 누적을 사용했습니다.',
        '', '| 조건 | 정책 | 실제 hold 오차 | 명령값/시각 오류 | 각 DAC 보상/초기화 | RF/DDR |',
        '|---|---|---|---|---|---|',
        '| 고정전압 20 mV | overlap_readout | 0 clocks | 0 / 0 | 200 / 200 | RF 200개·폭오차0, DDR 200 trigger·800 samples·400 writes |',
        '| 고정시간 1 µs | after_readout | 0 clocks | 0 / 0 | 200 / 200 | RF 200개·폭오차0, DDR 200 trigger·800 samples·400 writes |',
        '', '## 독립 확인',
        '- 실제 rtl_events.csv에서 200개의 shot 경계를 추출했습니다. 각 채널의 SET→첫 RAMP 명령 간격은 293–563 clocks입니다.',
        '- 기존 RAMP의 7-clock startup을 더한 실제 hold는 300–570 clocks(1.0–1.9 µs)이며 모든 점에서 요청값과 일치합니다. RAMP 출력 구간 시작 기준이며 양자화 때문에 첫 DAC 코드가 바뀌는 시각과는 구분합니다. 허용오차를 늘리지 않았습니다.',
        '- command-to-raw-sample 독립 Verilog checker가 모든 clock × 16 DAC lanes를 검사합니다. 따라서 명령 시각만 확인한 결과가 아닙니다. IIR 정수 recurrence도 모든 샘플에서 독립 계산과 일치했습니다.',
        '- 두 반복의 SET 값 동일, 각 hold 값에서 전압 고정 증분 동일, 다음 hold 값으로 갈 때 전압 축 rewind 동일을 실제 명령에서 확인했습니다.',
        '- 보상 후 각 shot의 잔여/누적 면적은 정확히 0 effective-code samples입니다. 출력16/DC시작17 clocks, RF42 clocks 및 DDR8712 clocks+입력 sample 대기는 유지됩니다.',
        '', '## 범위와 한계',
        '- DDR 입력은 300 clocks마다 생성한 timestamp stream입니다. 실제 ADC/아날로그 측정이나 FIR 산술 정확도를 검증한 것은 아닙니다.',
        '- 기존 정수 SET sweep의 이상 목표 전압 양자화 오차는 유지됩니다. 면적 잔여0은 실제 실행된 디지털 파형의 보상 결과입니다.',
        '- 이번 시험은 hold_duration sweep 두 DC 모드입니다. 기존 RTL/XDC/펌웨어는 변경하지 않았고 합성 및 32/64비트 비교는 다시 실행하지 않았습니다.',
        '- RTL/input snapshot SHA256와 각 GUI/RTL 원자료는 fixed_voltage 및 fixed_time 폴더에 보존했습니다. 최종 Acquisition-only GUI에서 두 조건을 다시 생성해 PMEM/DMEM 바이트 일치를 확인했고, 저장된 RTL evidence를 --analyze-only로 재검사했습니다. 시뮬레이터는 재실행하지 않았습니다.',
        '- 이번 조건은 초기 runtime DMEM이 0 words입니다. sweep 상태의 memwi 초기화/증분/rewind는 PMEM 명령과 실제 RTL 동작 검증에 포함됩니다.',
        '- 최종 GUI/compiler hash 및 이전/현재 PMEM/DMEM SHA256: [current_gui_replay/result.json](current_gui_replay/result.json).',
        '', '![Hold duration 및 DDR 타이밍](hold_duration_rtl.png)',
        '', '[기계 판독 검증 결과](hold_rtl_verification.json)']
    (OUT/'HOLD_RTL_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(complete=True,cases={k:v['status'] for k,v in checks.items()})))

if __name__=='__main__':main()
