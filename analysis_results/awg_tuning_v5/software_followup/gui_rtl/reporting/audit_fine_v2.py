"""Additional provenance and requested-parameter audit; original evidence stays intact."""
from dataclasses import asdict,replace
import gc
import hashlib
import json
from pathlib import Path
import sys
import traceback

HERE=Path(__file__).resolve().parent;EVIDENCE=HERE.parent;ROOT=EVIDENCE.parents[3]
GUI=ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI'
BUILD=Path('F:/Vivado_Output/a5post_fine_rtl1')
sys.path.insert(0,str(EVIDENCE));sys.path.insert(0,str(GUI))
from extension_v5 import configure

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def normalized(value):return json.loads(json.dumps(value))

def compare_spec(wanted,actual,expected):
    from dc_waveform_core import QickRfPulseSpec
    from qick_fine_tune_sweep import cycles_from_us
    raw={k:v for k,v in wanted.items() if k!='enabled'}
    request=QickRfPulseSpec(**raw)
    assert request.gen_ch==actual.gen_ch
    assert len(request.pulse_events)==len(actual.pulse_events)
    checked=[]
    for a,b in zip(request.pulse_events,actual.pulse_events):
        aa,bb=asdict(a),asdict(b)
        for key in aa:
            if key=='duration_us':assert round(aa[key]*4800)==round(bb[key]*4800),(key,aa[key],bb[key])
            elif key=='delay_us':
                assert abs(aa[key]-bb[key])<=(len(request.pulse_events)+1)*.5e-9+1e-12
                # Production starts use CEIL with integer-nearness tolerance, not round-to-nearest.
                # Preserve and expose any boundary-selection difference rather than hiding it.
            else:assert normalized(aa[key])==normalized(bb[key]),(key,aa[key],bb[key])
        wanted_cycles=cycles_from_us(a.delay_us,300) if a.delay_us else 0
        actual_cycles=cycles_from_us(b.delay_us,300) if b.delay_us else 0
        compiled=[item['command_cycle'] for item in expected[str(actual.gen_ch)] if item['name']==a.name]
        checked.append(dict(name=a.name,gen_ch=actual.gen_ch,requested=aa,actual=bb,
            requested_delay_cycles=wanted_cycles,gui_delay_cycles=actual_cycles,
            cycle_difference=actual_cycles-wanted_cycles,compiled_command_timestamps=compiled,
            gui_delay_precision_bound_us=(len(request.pulse_events)+1)*.5e-9+1e-12))
    assert len(request.sweep_axes)==len(actual.sweep_axes)
    for a,b in zip(request.sweep_axes,actual.sweep_axes):
        aa,bb=asdict(a),asdict(b)
        for key in aa:
            if a.axis_kind=='rf_duration' and key in ('start','stop'):assert round(aa[key]*4800)==round(bb[key]*4800)
            else:assert normalized(aa[key])==normalized(bb[key]),(key,aa[key],bb[key])
    # Static routing, board, calibration, amplitude mode and enabled controls.
    exclude={'frequency_parameters','duration_parameters','delay_parameters','phase_parameters','amplitude_parameters',
             'composite_items','t2_initial_phase_parameter','t2_final_phase_parameter','predefined_phase_parameter'}
    for key,value in asdict(request).items():
        if key in exclude:continue
        found=getattr(actual,key)
        if key=='duration_us':assert round(value*4800)==round(found*4800)
        else:assert normalized(value)==normalized(found),(key,value,found)
    return dict(events=checked,axis_fields_checked=[asdict(a) for a in actual.sweep_axes],
        gui_representation_normalization='GUI creates named phase/delay parameters from literal Custom values; resolved event fields are checked, not inferred from names.',
        duration_editor_rounding='9 decimal microseconds per duration/delay editor; each cumulative delay is bounded by the sum of editor half-units. Active duration maps to the same DAC sample count. Requested and GUI CEIL-to-fabric-cycle delays and any differences are reported explicitly.')

def main():
    import qick.sim
    from qick import QickConfig
    from PyQt5 import QtCore,QtGui,QtWidgets,sip
    import DCWaveform_Generator as gui
    from qick_front_panel import identify_qick_front_panel
    from qick_qcodes_experiment import build_qick_program
    prepared=json.loads((EVIDENCE/'fine/prepared.json').read_text())
    assert all(sha(p)==h for p,h in prepared['source_hashes'].items()),'Production source changed since actual preparation'
    base=ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json'
    cfg=QickConfig(json.loads(base.read_text()))
    for g in cfg['gens']:
        if g['type'] in ('axis_awg_tuning_v1','axis_square_pulse_v1'):g.update(rc_precomp_version=1,output_latency_cycles=11)
        if g['type']=='axis_square_pulse_v1':g['command_latency_cycles']=15
        if g['type']=='axis_awg_tuning_v1':g.update(type='axis_awg_tuning_v3',frac=18,step_width=32,dc_area_version=1,dc_area_bits=48,output_latency_cycles=16,dc_start_cycles=17)
    configure(cfg)
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(QtGui.QFont('Segoe UI',9))
    results=[];failure=None;qt_errors=[]
    def exception_hook(*args):
        message=''.join(traceback.format_exception(*args));qt_errors.append(message);print(message,flush=True)
    sys.excepthook=exception_hook
    try:
        for case in prepared['cases']:
            if case.get('raw_same_timestamp'):continue
            print('AUDIT_CASE',case['name'],flush=True)
            folder=Path(case['folder']);data=json.loads((folder/'gui_input.json').read_text())
            window=gui.MainWindow();window._on_qick_configuration_identified(replace(identify_qick_front_panel(cfg),dac_current_settings=data['qick']['dac_current_settings']))
            window._load_settings_json(folder/'gui_input.json');app.processEvents()
            assert not qt_errors,qt_errors
            args=window._experiment_run_arguments(require_readout=False,require_run_config=False)
            actual=args['rf_specs'];assert len(actual)==len(data['rf_outputs'])==3
            expected=json.loads((folder/'expected.json').read_text())['bursts']
            comparisons=[compare_spec(a,b,expected) for a,b in zip(data['rf_outputs'],actual)]
            assert normalized([asdict(s) for s in actual])==json.loads((folder/'gui_runtime_specs.json').read_text())
            p=build_qick_program(cfg,args['sequence'],awg_channels=args['awg_channels'],repetitions_per_sweep=2,
                rf_specs=actual,readout_spec=args['readout_spec'],tproc_mhz=300.,compile_validation_mode='boundary');p.compile()
            pmem=''.join(f'{int(w):016x}\n' for w in p.binprog)
            dmem=''.join(f'{p._runtime_dmem_base+i:08x} {int(w)&0xffffffff:08x}\n' for i,w in enumerate(p._runtime_dmem_words))
            assert pmem==(folder/'pmem.hex').read_text() and dmem==(folder/'dmem.txt').read_text()
            envelopes={}
            for channel in (0,2,4):
                envs=p.envelopes[channel]['envs'];count=max(e['addr']+len(e['data']) for e in envs.values());words=[0]*count
                for entry in envs.values():
                    for i,(iv,qv) in enumerate(entry['data']):words[entry['addr']+i]=(int(iv)&65535)|((int(qv)&65535)<<16)
                content=''.join(f'{w:08x}\n' for w in words);path=folder/f'envelope_{channel}.hex';assert content==path.read_text();envelopes[channel]=sha(path)
            results.append(dict(case=case['name'],passed=True,comparisons=comparisons,pmem_sha256=sha(folder/'pmem.hex'),dmem_sha256=sha(folder/'dmem.txt'),envelope_sha256=envelopes))
            window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();del window;gc.collect()
        sources=[base,Path(cfg['validation_candidate_hwh']),EVIDENCE/'extension_v5.py',EVIDENCE/'fine/harness.py',EVIDENCE/'fine/prepare.py',ROOT/'qick/firmware/ip/axis_output_sum_v2/src/axis_output_sum_v2.sv',Path(__file__)]
        quantization_differences=[dict(case=r['case'],**event) for r in results for comparison in r['comparisons'] for event in comparison['events'] if event['cycle_difference']]
        report=dict(passed=True,request_timing_preserved=not quantization_differences,quantization_differences=quantization_differences,cases=results,configured_soccfg=cfg._cfg,source_hashes={str(p):sha(p) for p in sources},
            original_production_source_hashes=prepared['source_hashes'],
            configured_soccfg_proof='Fresh real MainWindow recompilation with this full v5 config reproduces every saved PMEM/DMEM/envelope byte exactly; original prepared/results remain unchanged.',board_access=False)
        destination=HERE/'fine_input_provenance_audit.json';assert not destination.exists();destination.write_text(json.dumps(report,indent=2))
        print('FINE_INPUT_PROVENANCE_AUDIT_PASS',len(results))
    except BaseException as exc:
        traceback.print_exc();failure=repr(exc)
        (HERE/'fine_audit_v2_failure.json').write_text(json.dumps(dict(error=failure,qt_errors=qt_errors),indent=2))
    finally:
        for window in app.topLevelWidgets():window.close();window.deleteLater()
        app.sendPostedEvents(None,QtCore.QEvent.DeferredDelete);app.processEvents();QtCore.QTimer.singleShot(0,app.quit);app.exec_();sip.delete(app)
    if failure:raise RuntimeError(failure)

if __name__=='__main__':main()
