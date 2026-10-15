"""Run an auditable test-only adaptation of the established RTL harness.

Every replacement is exact and saved alongside the generated source. No
production GUI, compiler, RTL, constraints, or previous evidence is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from cases import case, CASES, MATRIX

HERE = Path(__file__).resolve().parent
ROOT = Path('C:\\GIT_Workspace\\QSTL_QICK')
BASE = ROOT / 'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'
EVIDENCE = HERE
SIM = Path('F:/Vivado_Output/a5matrix1')

def arguments(name):
    c = case(name)
    args = ['--build',str(SIM),'--gui',str(ROOT.parent/'PulseGenerator'),
        '--vivado','F:/Xilinx/Vivado/2023.1/bin','--awg-v3','--output-sum',
        '--repeat-reset','--isolated-run','--verify-gui-widgets',
        '--sweep-case',c['sweep'],'--sweep-count',str(c['count']),
        '--dc-mode',c['mode'],'--sum-rf-delay-us',str(c['delay']),
        '--cross-capacitance',*[str(v) for row in MATRIX for v in row],
        '--run-tag','v5matrix_20261015_'+name,'--dac-current-ma','20','10','20']
    if c['compensation'] in ('filter','off'): args += ['--rc-only']
    return args

def folder(name):
    c=case(name)
    rc='_rc_only' if c['compensation'] in ('filter','off') else ''
    return SIM / f'rc_precomp_repeat_reset{rc}_{c["sweep"]}_{c["count"]}x{c["count"]}_v5matrix_20261015_{name}_output_sum_awg_v3'

def generate(name):
    text = BASE.read_text(encoding='utf8')
    edits=[]
    def replace(old,new):
        nonlocal text
        assert text.count(old)==1,(old,text.count(old))
        text=text.replace(old,new,1);edits.append(dict(old=old,new=new))
    replace('HERE=Path(__file__).resolve().parent',f'HERE=Path({str(BASE.parent)!r})')
    replace('type=float, nargs=4,','type=float, nargs=9,')
    replace("default=(1., 0., 0., 1.), metavar=('M00', 'M01', 'M10', 'M11'),", "default=(1.,0.,0.,0.,1.,0.,0.,0.,1.), metavar='M',")
    replace('    args=parser.parse_args()',f'    args=parser.parse_args()\n    from cases import case\n    from support import configure_inputs, build_from_widgets, matrix_oracle, extra_monitors, finish\n    args.virtual_case=case({name!r})')
    # Both summary and actual configuration must carry all nine coefficients.
    assert text.count('np.asarray(args.cross_capacitance).reshape(2,2)')==4
    text=text.replace('np.asarray(args.cross_capacitance).reshape(2,2)','np.asarray(args.cross_capacitance).reshape(3,3)')
    edits.append(dict(all_occurrences=4,old='reshape(2,2)',new='reshape(3,3) for args.cross_capacitance'))
    replace('        extended=np.eye(3);extended[:2,:2]=matrix;matrix=extended;scales=scales+(800.,)',
        '        scales=scales+(800.,)\n    axes,rf_specs,square=configure_inputs(args,pulses,axes,rf_specs,square)')
    replace("bias_t_compensation_enabled=args.v2_fixture!='fast',bias_t_compensation_type='filter' if args.rc_only else 'dc_rc',",
        "bias_t_compensation_enabled=args.virtual_case['compensation']!='off',bias_t_compensation_type=args.virtual_case['compensation'] if args.virtual_case['compensation']!='off' else 'dc',")
    replace('square_pulse_settings=None if args.no_aux or args.sweep_case else square,',
        "square_pulse_settings=square if args.virtual_case['square'] else None,")
    replace('        from gui_widget_fixture import build_from_widgets','        # support.build_from_widgets uses real matrix and sweep dialogs')
    replace('    points=program.sequence.sweep_point_count','    matrix_oracle(program,pulses,axes,matrix,scales,out)\n    points=program.sequence.sweep_point_count')
    replace("enumerate(('axis_awg_tuning_v1_4','axis_awg_tuning_v1_5')):\n            root=f'dut.sim_bd_i.{cell}'\n            monitor.append", "enumerate(('axis_awg_tuning_v1_4','axis_awg_tuning_v1_5','axis_awg_tuning_v1_6')):\n            root=f'dut.sim_bd_i.{cell}'\n            monitor.append")
    replace("for cell in [next((c for c in ('axis_awg_tuning_v1_4','axis_awg_tuning_v1_5') if c in m),'unused')]]", "for cell in [next((c for c in ('axis_awg_tuning_v1_4','axis_awg_tuning_v1_5','axis_awg_tuning_v1_6') if c in m),'unused')]]")
    replace("    (out/'tb_rc_gui.sv').write_text(top)","    top=extra_monitors(top,args,program,out)\n    (out/'tb_rc_gui.sv').write_text(top)")
    replace("    (out/'result.json').write_text(json.dumps(summary,indent=2))", "    finish(summary,args,program,out,result)\n    (out/'result.json').write_text(json.dumps(summary,indent=2))")
    # Current v5 metadata and independently delayed sum oracle; validation only.
    replace('import gui_rtl_extension as sum_validation','import extension_v5 as sum_validation')
    replace("rtl.append(HERE.parent/'axis_output_sum_v1/src/axis_output_sum_v1.sv')","rtl.append(HERE.parent/'axis_output_sum_v2/src/axis_output_sum_v2.sv')")
    replace('top=sum_validation.monitor(top, shots, program, out, args)','top=sum_validation.monitor(top, shots, program, out, args)\n        top=sum_validation.extra_monitor(top)')
    # Construct actual UI before export compile, preserving original GUI rejection.
    replace("    program=ns['build_program'](cfg);program.compile()", "    if args.verify_gui_widgets:\n        widget_program=build_from_widgets(cfg,pulses,axes,rf_specs,args,out)\n    program=ns['build_program'](cfg);program.compile()")
    replace('        widget_program=build_from_widgets(cfg,pulses,axes,rf_specs,args,out)\n        assert widget_program.binprog', '        assert widget_program.binprog')
    if name=='compensation_off':
        replace('assert program.sequence.rc_compensation is not None','assert program.sequence.rc_compensation is None')
        replace("assert len(rc_resets)==len(awg_channels)*(shots+1), 'Missing per-shot RC reset'", "assert len(rc_resets)==len(awg_channels), 'OFF must only have initialization resets'")
        replace('rc_compensation=vars(program.sequence.rc_compensation)','rc_compensation=None')
    if name.startswith('cpmg_'):
        replace('from support import configure_inputs, build_from_widgets, matrix_oracle, extra_monitors, finish','from composite_support import configure_inputs, build_from_widgets, matrix_oracle, extra_monitors, finish, analyze_rf')
        start=text.index("    if args.sweep_case:\n        with (out/'rf_samples.csv').open()")
        end=text.index("    summary['validation_status']='passed'",start)
        text=text[:start]+"    summary['rf_measurements']=analyze_rf(out,model,offset,shots,args,program)\n"+text[end:]
        replace("summary['output_sum']=sum_validation.analyze(out,result,model,offset,shots,args.sum_rf_delay_us)","summary['output_sum']=sum_validation.analyze_composite(out,result,model,offset,shots,args,program)")
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    generated=EVIDENCE/f'verify_{name}.py'
    if generated.exists(): assert generated.read_text(encoding='utf8')==text,'Do not mutate prepared harness'
    else:
        generated.write_text(text,encoding='utf8')
        (EVIDENCE/f'harness_{name}.json').write_text(json.dumps(dict(original=str(BASE),
            original_sha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),
            generated_sha256=hashlib.sha256(text.encode()).hexdigest(),edits=edits),indent=2),encoding='utf8')
    return generated,text

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',choices=CASES,required=True)
    opts,extra=parser.parse_known_args()
    generated,text=generate(opts.case)
    sys.argv=[str(generated)]+arguments(opts.case)+extra
    exec(compile(text,str(generated),'exec'),{'__name__':'__main__','__file__':str(generated)})
