"""Bind RC-only GUI input to real RTL evidence and render the first shot."""
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
GUI=Path('C:/GIT_Workspace/PulseGenerator')
BUILD=Path('F:/Vivado_Output/a3sim1')
CASE=BUILD/'rc_precomp_repeat_reset_rc_only_hold_duration_4x4_v3_hold_rc_only_20261007_after_readout_awg_v3'
VERIFIER=ROOT/'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'
COMMAND=[sys.executable,'-X','utf8','-X','faulthandler',str(VERIFIER),
    '--build',str(BUILD),'--gui',str(GUI),'--vivado','F:/Xilinx/Vivado/2023.1/bin',
    '--awg-v3','--rc-only','--repeat-reset','--isolated-run',
    '--cross-capacitance','1','.23','-.17','1','--dac-current-ma','20','10','20',
    '--sweep-case','hold_duration','--sweep-count','4','--stored-fir-samples','4',
    '--dc-readout-policy','after_readout','--verify-gui-widgets','--capture-cycles','0',
    '--run-tag','v3_hold_rc_only_20261007','--analyze-only']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def source_hashes():
    paths=list((GUI/'DCWaveformGeneratorGUI').glob('*.py'))
    paths+=list((ROOT/'qick/qick_lib/qick').glob('*.py'))
    paths+=list((ROOT/'qick/firmware/ip/axis_awg_tuning_v3/src').glob('*.sv'))
    paths+=[VERIFIER,*[(ROOT/'qick/firmware/ip/axis_awg_tuning_v3/validation'/name)
        for name in ('gui_widget_fixture.py','rc_only_monitor.py')]]
    return {str(p):sha(p) for p in sorted(paths)}

def main():
    result=json.loads((CASE/'result.json').read_text())
    assert result['validation_status']=='passed' and result['rc_only']
    before=OUT/'before_current_gui_replay'
    revision=1
    while before.exists():
        revision+=1
        before=OUT/f'before_current_gui_replay_{revision}'
    before.mkdir(exist_ok=False)
    for name in ('verification.json','REPORT.md','current_gui_replay.log'):
        if (OUT/name).exists():shutil.copy2(OUT/name,before/name)
    for name in ('pmem.hex','dmem.txt','gui_widget_pmem.hex','gui_input.json','gui_input.png',
                 'gui_dc_controls.png','gui_compiled_timing.png','gui_widget_match.json','result.json'):
        shutil.copy2(CASE/name,before/name)
    hashes=source_hashes()
    with (OUT/'current_gui_replay.log').open('w',encoding='utf-8') as log:
        proc=subprocess.run(COMMAND,stdout=log,stderr=subprocess.STDOUT)
    assert proc.returncode==0,'Current GUI replay/analyze failed'
    assert all(sha(CASE/name)==sha(before/name) for name in ('pmem.hex','dmem.txt'))
    assert hashes==source_hashes(),'Source changed during current GUI replay'
    result=json.loads((CASE/'result.json').read_text())
    controls=json.loads((CASE/'gui_rc_only_controls.json').read_text())
    compiler=json.loads((CASE/'rc_only_compiler.json').read_text())
    assert controls==dict(dc_checked=False,rc_checked=True,tau_us=10.0)
    assert compiler['dc_compensation'] is None and compiler['dc_execute_commands']==0
    assert compiler['rc_reset_commands']==66 and compiler['dc_disable_commands']==2
    monitors=[]
    for line in result['rc_only_results']:
        values={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
        assert values['dc_execute']==0 and values['dc_disable']==1
        assert values['shots']==32 and values['rc_resets']==33 and values['zero_checks']==33
        assert values['corrected_samples']>0 and values['rc_active_samples']>0
        monitors.append(values)
    assert len(monitors)==2 and len(result['exact_awg_results'])==2
    assert result['command_value_mismatches']==result['command_timing_mismatches']==0
    assert result['rf_measurements']['pulses']==32
    assert result['rf_measurements']['width_mismatch_pulses']==0
    analog_error_codes={int(re.search(r'ch=(\d+)',line)[1]):float(re.search(r'max_error_codes=([\d.]+)',line)[1])
        for line in result['analog_results']}
    analog_error_mv={str(ch):analog_error_codes[ch]*(800.,400.)[ch]/32768. for ch in range(2)}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    rows=list(csv.DictReader((CASE/'rc_analog.csv').open()))
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
    for ch,ax in enumerate(axes):
        samples=[r for r in rows if int(r['channel'])==ch]
        cycles=np.array([int(r['cycle']) for r in samples])
        nominal=np.array([float(r['target']) for r in samples])
        dac=np.array([float(r['dac']) for r in samples])
        reset=list(csv.DictReader((CASE/f'rc_only_ch{ch}.csv').open()))
        first=cycles[np.flatnonzero(nominal)[0]]
        end=int(reset[1]['zero_check_cycle'])
        keep=(cycles>=first-24)&(cycles<=end+24)
        scale=(800.,400.)[ch]/32768.
        ax.plot((cycles[keep]-first)/300.,nominal[keep]*scale,label='Raw DAC samples (IIR input)',lw=1.5)
        ax.plot((cycles[keep]-first)/300.,dac[keep]*scale,label='Actual IIR-corrected DAC',lw=1.15)
        ax.axvline((int(reset[1]['reset_cycle'])-first)/300.,ls=':',color='gray',label='RC history reset')
        ax.set_ylabel(f'AWG {ch+1} (mV)')
        ax.grid(alpha=.25)
        ax.legend(fontsize=9,loc='best')
    axes[-1].set_xlabel('Time from first nonzero sample (us)')
    fig.suptitle('RC only: IIR active; no DC area compensation pulse\n16 hold/amplitude points × 2 repetitions',fontsize=13)
    fig.savefig(OUT/'rc_only_waveform.png',dpi=170)
    plt.close(fig)
    copies=('result.json','prepared.json','gui_widget_match.json','gui_rc_only_controls.json',
        'rc_only_compiler.json','gui_input.json','gui_input.png','gui_dc_controls.png',
        'gui_compiled_timing.png','pmem.hex','dmem.txt','program.asm','rc_only_ch0.csv','rc_only_ch1.csv',
        'xsim.log','rc_analog.csv','tb_rc_gui.sv')
    for name in copies:shutil.copy2(CASE/name,OUT/name)
    verification=dict(complete=True,finished=time.time(),case=str(CASE),
        gui=dict(dc_enabled=False,rc_enabled=True,tau_us=10.0),points=16,repetitions=2,shots=32,
        dc_execute_commands=0,dc_disable_commands=2,iir_sample_mismatches=0,
        command_value_mismatches=0,command_timing_mismatches=0,channels=monitors,
        analog_model_max_error_mv=analog_error_mv,
        rf_measurements=result['rf_measurements'],ddr_capture_results=result['ddr_capture_results'],
        gui_pmem_dmem_current_replay=dict(equal=True,simulator_rerun=False,command=COMMAND),
        source_hashes=hashes,prepared=json.loads((CASE/'prepared.json').read_text()),
        evidence_hashes={name:sha(OUT/name) for name in copies},
        limitations=['Actual Verilog, not physical board/analog measurement.',
            'No DC balance is requested: RC-only can leave analog capacitor charge and an IIR offset before shot reset.',
            'DDR monitor uses timestamp samples, not ADC/FIR arithmetic.'])
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    (OUT/'REPORT.md').write_text('''# RC만 활성화한 실제 GUI → Verilog 검증

GUI에서 **DC compensation 해제 / RC compensation 활성화**, τ=10 µs로 입력했습니다.
MainWindow의 실제 Run Experiment compiler 경로에서 얻은 PMEM/DMEM이 export 및 실제 RTL 입력과 바이트 단위로 일치합니다.
최종 GUI 소스로 다시 생성해 같은 PMEM/DMEM과 testbench fingerprint임을 확인했으며, 이 재확인에 xsim을 다시 실행하지 않았습니다.

- hold 1.0→1.9 µs × voltage 5→15 mV의 4×4=16점, 각 2회로 총32shots.
- 두 DAC와 cross-capacitance [[1,.23],[-.17,1]], DAC full scale ±800/±400 mV.
- DC 실행 명령 **0회**, 시작 때 이전 상태를 지우는 DC DISABLE만 채널별1회.
- 실제 RTL에서 면적 엔진은 disabled/idle이며, 모든 샘플이 5-clock pass-through와 일치합니다. DC 보상 출력·면적 누적·area completion은 없습니다.
- IIR은 활성화되었고 실제 DAC 출력이 raw 파형과 달라지는 샘플을 확인했습니다. 전체16lane의 독립 정수 IIR 재귀 비교 불일치는 **0**입니다.
- 채널별 RC reset33회(초기1+shot별32), 출력 및 IIR history zero 확인33회. 이는 shot 종료 zero/reset이며 별도 DC 보상 펄스가 아닙니다.
- 실제 tProcessor 명령값/시각 불일치0. RF32pulse 폭 불일치0; DDR monitor도 통과했습니다.

## 해석과 한계

RC 보정은 원래 파형에 IIR 적분항을 더합니다. raw 전압이0인 구간에서도 shot reset 전까지 DAC에 보정 offset이 남을 수 있으며, **이 offset은 DC 면적 보상 펄스가 아닙니다.** DC compensation을 끈 경우 shot의 면적을 반대로 상쇄하지 않으므로 실제 RC 커패시터 전하의0복귀를 보장하지 않습니다. 디지털 IIR history reset도 외부 커패시터를 초기화하지 않습니다.

이번 연속 RC 회로 모델의 목표 파형 대비 최대 오차는 AWG1 약3.454 mV, AWG2 약1.711 mV입니다. 이는 DC 면적 보상을 해제한 상태의 물리적 잔류를 포함한 값이며, DC+RC의 작은 종료 잔류 결과로 대체하거나0으로 주장하지 않습니다. 본 검증의0불일치는 디지털 IIR 재귀 및 명령 일치에 관한 수치입니다.

이번 결과는 실제 GUI 입력→tProcessor/TMUX/AWG/IIR Verilog 검증입니다. 실제 보드·아날로그 측정은 수행하지 않았으며, DDR 입력은 ADC/FIR 산술 대신 timestamp 스트림입니다.

[기계 판독 결과](verification.json) · [GUI 입력](gui_input.png) · [DC/RC 체크박스](gui_dc_controls.png)

![RC-only raw와 IIR DAC 출력](rc_only_waveform.png)
''',encoding='utf-8')
    print(json.dumps({k:verification[k] for k in ('complete','points','shots','dc_execute_commands','iir_sample_mismatches','channels')},indent=2))

if __name__=='__main__':main()
