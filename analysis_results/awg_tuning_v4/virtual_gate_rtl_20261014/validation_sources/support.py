"""Independent virtual-voltage oracles and real Qt input, for validation only."""
from dataclasses import replace
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
import numpy as np
from cases import MATRIX

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
V3=ROOT/'qick/firmware/ip/axis_awg_tuning_v3/validation'

def configure_inputs(args,pulses,axes,rf_specs,square):
    from dc_waveform_core import QickSweepSpec
    c=args.virtual_case
    if c['two_voltage']:
        axes=[QickSweepSpec('set_0','awg_0',5/800,15/800,c['count']),
              QickSweepSpec('set_0','awg_1',-9/800,7/800,c['count'])]
    if c['square']:
        axes=[a for a in axes if a.axis_kind=='amplitude']
        square.update(mute_on_finish=True)
        square['parameters']['frequency']['value']=.2
        lo,hi={'frequency':(.2,.4),'amplitude':(5.,15.),'phase':(0.,135.)}[c['square']]
        square['parameters'][c['square']].update(sweep=True,start=lo,stop=hi,count=c['count'])
    if c['descending']: axes=[replace(a,start=a.stop,stop=a.start) for a in axes]
    if c['swap']: axes.reverse()  # Input order, before GUI or export compilation.
    # One independent RF frequency axis; every RF/AWG pair still outputs.
    rf_specs=[replace(s,frequency_sweep_enabled=s.frequency_sweep_enabled and s.gen_ch==0) for s in rf_specs]
    if c['compensation']=='off':
        sys.path.insert(0,str(V3))
        import rc_only_monitor
        rc_only_monitor.rc_only_monitor=off_monitor
    args.virtual_square=square
    return axes,rf_specs,square

def input_widgets(window,app,axes,options,out):
    from PyQt5 import QtCore,QtTest,QtWidgets
    import DCWaveform_Generator as gui
    errors=[];entered=[]
    def modal(action,editor):
        def apply():
            dialog=app.activeModalWidget()
            try:
                editor(dialog)
                dialog.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok).click()
            except Exception as exc:
                errors.append(repr(exc));dialog.reject()
        QtCore.QTimer.singleShot(50,apply)
        action()
        assert not errors,errors
    def value(widget,number):
        widget.setFocus();widget.selectAll()
        QtTest.QTest.keyClicks(widget,format(number,'.12g'))
        QtTest.QTest.keyClick(widget,QtCore.Qt.Key_Tab)
        assert abs(widget.value()-number)<1e-8,(widget.value(),number)
    def matrix(dialog):
        assert isinstance(dialog,gui.CrossCapacitanceDialog)
        for row in range(3):
            for col in range(3):
                if row!=col:value(dialog._editors[row][col],MATRIX[row][col])
        np.testing.assert_array_equal(dialog.matrix(),MATRIX)
        app.processEvents();assert dialog.grab().save(str(out/'matrix_input.png'))
    modal(window._configure_cross_capacitance,matrix)
    np.testing.assert_array_equal(window._cross_capacitance,MATRIX)
    for axis in axes:
        kind=axis.axis_kind
        if kind=='amplitude':
            action=lambda a=axis:window._configure_segment_sweep(int(a.output_name.split('_')[-1]),0)
            scale=800.
        elif kind=='ramp_duration':
            action=lambda:window._configure_ramp_rate_sweep(0,1);scale=1.
        elif kind=='hold_duration':
            action=lambda:window._configure_hold_duration_sweep(0,0);scale=1.
        else: raise AssertionError(kind)
        def sweep(dialog,a=axis,multiplier=scale):
            value(dialog.start,a.start*multiplier);value(dialog.stop,a.stop*multiplier);value(dialog.count,a.count)
            app.processEvents()
            assert dialog.grab().save(str(out/f'sweep_input_{len(entered)}.png'))
        modal(action,sweep)
        entered.append(dict(kind=kind,output=axis.output_name,start=axis.start,stop=axis.stop,count=axis.count))
    assert window._sweep_specs==axes,(window._sweep_specs,axes)
    (out/'gui_direct_input.json').write_text(json.dumps(dict(matrix=MATRIX,axes=entered,
        method='QTest keyboard -> actual modal OK -> MainWindow Run Experiment arguments',
        no_sequence_mutation=True),indent=2),encoding='utf8')

def build_from_widgets(cfg,pulses,axes,rf_specs,options,out):
    # Retain the reviewed fixture's connection setup and Qt lifecycle. Replace
    # JSON injection of matrix/axes with actual modal keyboard input.
    original=V3/'gui_widget_fixture.py'
    source=original.read_text(encoding='utf8')
    start=source.index("    data['awg']['cross_capacitance']")
    end=source.index("    data['qick'].update",start)
    source=source[:start]+"    data['awg']['cross_capacitance']=np.eye(3).tolist()\n    data['awg']['sweeps']=[]\n"+source[end:]
    source=source.replace("data['qick']['bias_t_compensation']=dict(enabled=True,type='filter' if rc_only else 'dc_rc',mode=options.dc_mode,",
        "data['qick']['bias_t_compensation']=dict(enabled=options.virtual_case['compensation']!='off',type=options.virtual_case['compensation'] if options.virtual_case['compensation']!='off' else 'dc',mode=options.dc_mode,")
    source=source.replace("    data['square_pulse']['enabled']=False", "    data['square_pulse']=options.virtual_square if options.virtual_case['square'] else dict(enabled=False)")
    start=source.index('    # Explicit widget values')
    end=source.index('    runtime=window._experiment_run_arguments',start)
    source=source[:start]+"    input_widgets(window,app,axes,options,out)\n    (out/'gui_input.json').write_text(json.dumps(window._settings_to_dict(),indent=2),encoding='utf8')\n"+source[end:]
    namespace=dict(np=np,input_widgets=input_widgets)
    exec(compile(source,str(original)+'[direct-input adapter]','exec'),namespace)
    (out/'gui_fixture_adapter.py').write_text(source,encoding='utf8')
    return namespace['build_from_widgets'](cfg,pulses,axes,rf_specs,options,out)

def matrix_oracle(program,pulses,axes,matrix,scales,out):
    """C@V in mV plus the existing integer add/rewind policy, independently.

    Compare every Cartesian point to compiler targets. The original harness
    then checks every command against real tProcessor RTL, and all raw lanes.
    This does not claim ideal-voltage quantization error has been eliminated.
    """
    actual_axes=program.sequence.sweep_axes
    counts=[a.count for a in actual_axes]
    base_virtual=np.array([p.v[0] for p in pulses])
    for a in actual_axes:
        if a.axis_kind=='amplitude':base_virtual[int(a.output_name.split('_')[-1])]=a.start*800
    physical=matrix@base_virtual
    base=np.rint(physical/np.asarray(scales)*8192).astype(int)*4
    deltas=[]
    for a in actual_axes:
        end_virtual=base_virtual.copy()
        if a.axis_kind=='amplitude':end_virtual[int(a.output_name.split('_')[-1])]=a.stop*800
        endpoint=np.rint((matrix@end_virtual)/np.asarray(scales)*8192).astype(int)*4
        change=[]
        for b,e in zip(base,endpoint):
            f=Fraction(int(e-b),max(1,a.count-1)*4)
            change.append((1 if f>=0 else -1)*int(abs(f)+Fraction(1,2))*4)
        deltas.append(change)
    rows=[]
    for point,indices in enumerate(itertools.product(*(range(n) for n in counts))):
        codes=base+sum((i*np.array(d) for i,d in zip(indices,deltas)),start=np.zeros(3,dtype=int))
        for ch in range(3):
            field=program._sweep_models[(0,ch,0,'target')]
            actual=program._sweep_model_value(field,point)
            assert actual==int(codes[ch]),(point,ch,actual,int(codes[ch]))
        rows.append(dict(point=point,indices=indices,target_codes=codes.tolist()))
    assert len(rows)==program.sequence.sweep_point_count
    (out/'independent_matrix_oracle.json').write_text(json.dumps(dict(matrix=matrix.tolist(),
        scales_mv=scales,base_virtual_mv=base_virtual.tolist(),base_physical_mv=physical.tolist(),
        base_codes=base.tolist(),axis_deltas=deltas,points=rows,
        policy='constant_quantized_increment; independent C@V and tie-away increment rounding',passed=True),indent=2))

def off_monitor(channel,root,shots):
    return f'''
begin: OFF_CHECK_{channel}
 logic [255:0] history[5];
 longint samples=0,disable_commands=0;
 initial for(integer i=0;i<5;i=i+1) history[i]=0;
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=4;i>0;i=i-1)history[i]=history[i-1];
  history[0]={root}.core_samples;
  if({root}.s_axis_tvalid && {root}.s_axis_tdata[150] && !{root}.s_axis_tdata[149]) begin
   if({root}.s_axis_tdata[147:144]!=4'b1111) $fatal(1,"OFF emitted DC ARM/EXEC");
   disable_commands=disable_commands+1;
  end
  #0.002;
  if({root}.rc_enabled || {root}.area_enabled || {root}.area_busy || {root}.area_done ||
     {root}.area_sum!==0 || {root}.area_completed_shots!==0 || {root}.area_fault || {root}.rc_clipped)
   $fatal(1,"OFF enabled compensation ch={channel}");
  if({root}.area_valid) begin
   if({root}.area_samples!==history[4]) $fatal(1,"OFF area bypass ch={channel}");
   samples=samples+16;
  end
 end
 final begin
  if(disable_commands!=1 || samples==0) $fatal(1,"Missing OFF checks");
  $display("RC_ONLY_RESULT ch={channel} mode=OFF bypass_samples=%0d dc_execute=0 rc_enable=0",samples);
 end
end
'''

def extra_monitors(top,args,program,out):
    if not args.virtual_case['square']:return top
    return top.replace('endmodule',(HERE/'square_oracle.svh').read_text()+'\nendmodule')

def finish(summary,args,program,out,log):
    assert len(summary['exact_awg_results'])==3
    summary['virtual_case']=args.virtual_case
    summary['matrix_direct_gui_input']=True
    summary['independent_matrix_oracle']='independent_matrix_oracle.json'
    if args.virtual_case['square']:
        match=re.findall(r'VIRTUAL_SQUARE_RESULT[^\n]+',log)
        assert len(match)==1,'Missing all-lane Square output oracle'
        summary['square_oracle']=match
    summary['test_source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()}
