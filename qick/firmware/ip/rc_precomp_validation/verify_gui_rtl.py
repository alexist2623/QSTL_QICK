"""GUI export -> PMEM -> real tProcessor/TMUX/AWG/Square RTL with analog RC.

Reuse the already generated production routing simulation libraries. Only the
AWG/Square module definitions are replaced by their current production source.
No RFDC or processor system is included in this digital output test.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]/'projects/qstl_gui_rtl_sim'


def calibration_fixture(path):
    """Synthetic power data read through the real GUI calibration database API."""
    if path.exists():
        return
    import math
    metadata=dict(schema='qstl-qick-output-power-calibration-v2',
        configuration=dict(nqz=1,output_filter_type='bypass',
            output_filter_cutoff_ghz=2.5,output_filter_bandwidth_ghz=1.),
        rf_settings_actual=dict(filter_type='bypass',filter_cutoff_ghz=2.5,filter_bandwidth_ghz=1.),
        simulation_fixture=True)
    with sqlite3.connect(path) as db:
        db.executescript('''
CREATE TABLE experiments (exp_id INTEGER PRIMARY KEY, name TEXT, sample_name TEXT);
CREATE TABLE runs (run_id INTEGER PRIMARY KEY, exp_id INTEGER, result_table_name TEXT,
    is_completed INTEGER, Attenuation TEXT, Calibration_Config TEXT);
CREATE TABLE layouts (layout_id INTEGER PRIMARY KEY, run_id INTEGER, parameter TEXT,
    label TEXT, unit TEXT, inferred_from TEXT);
CREATE TABLE "results-1-1" (id INTEGER PRIMARY KEY, gain REAL, freq REAL, pwr REAL);
INSERT INTO experiments VALUES (1, 'SIMULATION ONLY', 'RF_Out_RTL_fixture');
INSERT INTO layouts VALUES (1, 1, 'freq', 'freq', 'MHz', '');
''')
        db.execute('INSERT INTO runs VALUES (1,1,?,1,?,?)',
                   ('results-1-1',json.dumps(dict(att1=0,att2=0)),json.dumps(metadata)))
        for frequency in (180.,190.,200.,225.):
            for gain in (500,2000,8000):
                power=-20+20*math.log10(gain/2000)+.01*(frequency-190)
                db.execute('INSERT INTO "results-1-1" (gain,freq,pwr) VALUES (?,?,?)',
                           (gain,frequency,power))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--square-sweep',action='store_true')
    parser.add_argument('--repeat-reset',action='store_true',
                        help='Verify AWG history and DAC return to zero after every shot.')
    parser.add_argument('--no-aux',action='store_true',
                        help='Exercise AWG-only completion without SquarePulse or markers.')
    parser.add_argument('--sweep-case', choices=('ramp_rate', 'hold_duration', 'rf_duration',
        'rf_duration_fixed', 'rf_frequency', 'rf_power', 'rf_frequency_power'))
    parser.add_argument('--sweep-count', type=int, default=10)
    parser.add_argument('--run-tag', default='', help='Keep revised runs separate from prior evidence.')
    parser.add_argument('--dac-current-ma', type=float, nargs=3, default=(20.,20.,20.),
                        help='AWG1, AWG2, SquarePulse current for voltage scaling validation.')
    parser.add_argument('--dc-mode', choices=('fixed_time','fixed_voltage'), default='fixed_time')
    parser.add_argument('--dc-voltage-mv', type=float, default=20.)
    parser.add_argument('--rf-length-boundary', choices=('oneshot','periodic'),
                        help='Use a 2 x 2 zero-AWG fixture around the RF 16-bit length boundary.')
    parser.add_argument('--capture-cycles', type=int, default=12000,
                        help='Bound saved waveform size; all clocks are still checked.')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--reuse-snapshot', action='store_true')
    parser.add_argument('--isolated-run', action='store_true')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Recheck saved completed RTL evidence without rerunning the simulator.')
    parser.add_argument('--grid-count', type=int, default=0,
                        help='Run a compact two-DAC voltage grid with every RTL point checked.')
    parser.add_argument('--grid-zero-hold-ns', type=float, default=600.,
                        help='Final zero hold; 100 ns reproduces the dense-command throughput limit.')
    args=parser.parse_args()
    if args.analyze_only:
        args.reuse_snapshot=True
    if args.sweep_count < 2 or args.grid_count == 1 or args.grid_count < 0:
        parser.error('Sweep dimensions must contain at least two points.')
    if args.grid_count and args.sweep_case:
        parser.error('Choose either the two-DAC voltage grid or a mixed sweep case.')
    if args.run_tag and not re.fullmatch(r'[a-z0-9_]+',args.run_tag):
        parser.error('Run tag must contain only lowercase letters, digits and underscores.')
    if args.rf_length_boundary and (args.sweep_case!='rf_duration_fixed' or args.sweep_count!=2):
        parser.error('RF boundary fixture requires rf_duration_fixed with sweep-count 2.')
    case_name = 'rc_precomp_square_sweep' if args.square_sweep else 'rc_precomp'
    if args.repeat_reset:
        case_name += '_repeat_reset'
    if args.no_aux:
        case_name += '_no_aux'
    if args.sweep_case:
        case_name += '_' + args.sweep_case
        if args.sweep_count != 10:
            case_name += f'_{args.sweep_count}x{args.sweep_count}'
    if args.grid_count:
        case_name += f'_grid_{args.grid_count}x{args.grid_count}'
        if args.grid_zero_hold_ns != 600.:
            case_name += f'_zero{args.grid_zero_hold_ns:g}ns'
    if args.rf_length_boundary:
        case_name += '_boundary_' + args.rf_length_boundary
    if args.run_tag:
        case_name += '_' + args.run_tag
    out=args.build/case_name;out.mkdir(exist_ok=True)
    # Preserve the exact testbench generation used by saved evidence. New
    # simulations explicitly close every diagnostic stream before $finish.
    capture_version=2
    if args.reuse_snapshot:
        capture_version=json.loads((out/'prepared.json').read_text()).get('capture_version',1)
    run=args.build/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    sys.path.insert(0,str(args.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim
    from qick import QickConfig
    from qick.awg_tuning import TProcV1BehaviorModel
    from dc_waveform_core import (PulseSequence,QickSweepSpec,generate_qick_program_code,
        QickRampRateSweepSpec,QickHoldDurationSweepSpec,QickRfPulseSpec)
    import numpy as np

    cfg=QickConfig(json.loads((PROJECT/'soccfg.json').read_text()))
    for g in cfg['gens']:
        if g['type'] in ('axis_awg_tuning_v1','axis_square_pulse_v1'):
            g.update(rc_precomp_version=1,output_latency_cycles=11)
        if g['type']=='axis_square_pulse_v1':g['command_latency_cycles']=15
    pulses=[]
    for scale in (1.,-.5):
        p=PulseSequence()
        p.t=np.array([0,1000,1200,2200,2400,3400],dtype=float)
        p.v=np.array([10,10,-10,-10,0,0],dtype=float)*scale
        p.segment_names=['positive','negative','zero'];pulses.append(p)
    axes=[QickSweepSpec('set_0',f'awg_{i}',5/800,15/800,10) for i in range(2)]
    if args.grid_count:
        for p in pulses:
            # Leave a 600 ns zero hold for the dense dual-channel command
            # stream and nested-loop arithmetic to replenish queue lookahead.
            p.t=np.array([0,100,150,250,300,300+args.grid_zero_hold_ns],dtype=float)
        axes=[QickSweepSpec('set_0',f'awg_{i}',5/800,15/800,args.grid_count) for i in range(2)]
    square=dict(enabled=True,gen_ch=7,mute_on_finish=False,rc_enabled=True,rc_tau_us=10.,
        parameters=dict(frequency=dict(value=.002),amplitude=dict(value=10),phase=dict(value=0)))
    if args.square_sweep:
        axes=axes[:1]
        square['parameters']['amplitude'].update(sweep=True,start=5.,stop=15.,count=10)
    rf_specs = None
    if args.sweep_case:
        count=args.sweep_count
        ramp_stop=.1+(count-1)*5/300 if count==20 else .4
        hold_stop=1.+(count-1)*15/300 if count==20 else 1.9
        rf_duration_start=.1
        rf_duration_stop=ramp_stop
        axes = [QickSweepSpec('set_0', 'awg_0', 5/800, 15/800, count)]
        if args.rf_length_boundary:
            first=65534 if args.rf_length_boundary=='oneshot' else 65535
            rf_duration_start=first/300
            rf_duration_stop=(first+1)/300
            for pulse in pulses:
                pulse.t=np.array([0,230000,230200,231200,231400,232400],dtype=float)
                pulse.v[:]=0
            axes=[QickSweepSpec('set_0','awg_0',0.,0.,count)]
        if args.sweep_case == 'ramp_rate':
            axes.insert(0, QickRampRateSweepSpec('ramp_0_to_1', .1, ramp_stop, count))
        elif args.sweep_case == 'hold_duration':
            axes.insert(0, QickHoldDurationSweepSpec('set_0', 1., hold_stop, count))
        rf_kwargs = {}
        if args.sweep_case in ('rf_duration', 'rf_duration_fixed'):
            rf_kwargs.update(duration_sweep_enabled=True, duration_sweep_start_us=rf_duration_start,
                duration_sweep_stop_us=rf_duration_stop, duration_sweep_count=count,
                segment_length_mode='fixed' if args.sweep_case=='rf_duration_fixed' else 'extend_by_rf_duration')
        if args.sweep_case in ('rf_frequency', 'rf_frequency_power'):
            rf_kwargs.update(frequency_sweep_enabled=True, frequency_sweep_start_mhz=180.,
                frequency_sweep_stop_mhz=225., frequency_sweep_count=count)
        if args.sweep_case in ('rf_power', 'rf_frequency_power'):
            fixture=out/'synthetic_calibration.db'
            calibration_fixture(fixture)
            rf_kwargs.update(power_sweep_enabled=True,power_sweep_start_dbm=-26.,
                power_sweep_stop_dbm=-14.,power_sweep_count=count,power_calibration_enabled=True,
                power_calibration_database_path=str(fixture),power_calibration_run_id=1)
            if args.sweep_case=='rf_frequency_power':
                axes=[]
        rf_specs = [QickRfPulseSpec(0, 'set_0', 0., rf_duration_start, 190., 2000, 0., 0., **rf_kwargs)]
    code=generate_qick_program_code(pulses,awg_channels=(1,3),full_scale_mv=800.,
        output_full_scales_mv=tuple(current*40 for current in args.dac_current_ma[:2]),
        square_full_scale_mv=args.dac_current_ma[2]*40,
        fabric_mhz=300.,tproc_mhz=300.,repetitions_per_sweep=2,sweeps=axes,
        bias_t_compensation_enabled=True,bias_t_compensation_type='dc_rc',
        bias_t_compensation_mode=args.dc_mode,bias_t_compensation_voltage_mv=args.dc_voltage_mv,
        bias_t_compensation_duration_us=.1 if args.grid_count else 1.,bias_t_filter_tau_us=10.,
        rf_pulse_specs=rf_specs,
        square_pulse_settings=None if args.no_aux or args.sweep_case else square,
        output_trigger_settings=None if args.no_aux else dict(enabled=True,pin=0,scope='loop',edge='both',width_us=.1))
    if args.grid_count:
        code=code.replace('        ddr_readout=ddr_readout,\n',
                          '        ddr_readout=ddr_readout,\n        compile_validation_mode="boundary",\n')
    (out/'gui_export.py').write_text(code,encoding='utf-8')
    ns={};exec(compile(code,str(out/'gui_export.py'),'exec'),ns)
    program=ns['build_program'](cfg);program.compile()
    points=program.sequence.sweep_point_count
    shots=points*2
    (out/'program.asm').write_text(program.asm())
    (out/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
    dm={program._runtime_dmem_base+i:int(v)&0xffffffff for i,v in enumerate(program._runtime_dmem_words)}
    (out/'dmem.txt').write_text(''.join(f'{a:08x} {w:08x}\n' for a,w in dm.items()))
    model=TProcV1BehaviorModel(strict=True);program.load_runtime_dmem_into_model(model)
    model.run(program, max_steps=max(100000, shots*1000))
    assert not model.timing_conflicts
    expected=[dict(cycle=e.cycle,port=e.tproc_ch,word=f'{e.word:040x}') for e in model.output_events]
    expected += [dict(cycle=e['cycle'],port=e['port'],word=f'{e["word"]:040x}') for e in model.output_pin_events]
    if args.repeat_reset:
        resets = [e for e in model.output_events if e.word & (1 << 149) and e.word & (1 << 147)]
        assert len(resets) == 2*(shots+1)
    cycles=max(e['cycle'] for e in expected)+2000
    if not args.grid_count:
        (out/'expected.json').write_text(json.dumps(dict(events=expected,cycles=cycles),indent=2))
    # Large grids retain reproducible PMEM/DMEM and checked summaries instead
    # of duplicating millions of expected commands as a JSON waveform dump.
    print(f'PREPARED points={points} shots={shots} cycles={cycles} events={len(expected)}',flush=True)

    source=args.build/'qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/sim/sim_bd.v'
    text=source.read_text()
    keep={'axis_tproc64x32_x8_0','axis_tmux_v1_0','axis_tmux_v1_1','axis_tmux_v1_3',
          'axis_awg_tuning_v1_4','axis_awg_tuning_v1_5','axis_square_pulse_v1_0',
          'axis_register_slice_8','axis_register_slice_9','axis_register_slice_10',
          'axis_register_slice_21','axis_register_slice_12','axis_register_slice_23',
          'axis_set_reg_0','qick_vec2bit_0',*('xlconstant_'+str(i) for i in range(5))}
    if args.sweep_case:
        keep.update(('axis_signal_gen_v6_0', 'axis_register_slice_0', 'axis_register_slice_4'))
    pattern=re.compile(r'^  (sim_bd_\w+) (\w+)\s*\n.*?\);',re.M|re.S)
    found=list(pattern.finditer(text));assert keep<={m[2] for m in found}
    text=pattern.sub(lambda m:m[0] if m[2] in keep else '',text)
    text=text.replace('module sim_bd\n','module rc_bd\n',1)
    for i in (4,5):
        text=text.replace(f'sim_bd_axis_awg_tuning_v1_{i}_0 axis_awg',
                          'axis_awg_tuning_v1 #(.EXTRA_Y_PIPE_STAGES(3)) axis_awg')
    text=text.replace('sim_bd_axis_square_pulse_v1_0_0 axis_square','axis_square_pulse_v1 axis_square')
    ties=[f"assign axis_clk_cnvrt_avg_{i}_M_AXIS_TDATA=64'b0;\nassign axis_clk_cnvrt_avg_{i}_M_AXIS_TVALID=1'b0;" for i in range(4)]
    ties += [f"assign axis_tproc64x32_x8_0_m{i}_axis_TREADY=1'b1;" for i in (3,5,6,7)]
    if args.sweep_case:
        ties += ["assign axis_switch_gen_M00_AXIS_TDATA=32'b0; assign axis_switch_gen_M00_AXIS_TVALID=1'b0;"]
    text=text.replace('endmodule','\n'.join(ties)+'\nendmodule')
    (out/'rc_bd.v').write_text(text)
    wrapper=Path((args.build/'wrapper_path.txt').read_text().strip()).read_text()
    wrapper=wrapper.replace('module sim_bd_wrapper','module rc_wrapper',1).replace('sim_bd sim_bd_i','rc_bd sim_bd_i',1)
    (out/'rc_wrapper.v').write_text(wrapper)
    top=(PROJECT/'tb_gui.sv').read_text()
    top=top[:top.index('always @(posedge clk_300000000) if (resetn && dut.')]
    top=top.replace('module tb_gui;','module tb_rc_gui;').replace('sim_bd_wrapper dut','rc_wrapper dut')
    body=(PROJECT/'tb_complex_body.svh').read_text()
    body=body.replace('always @(posedge clk_300000000) if(resetn) begin', '''always @(posedge clk_300000000) if(resetn) begin
 if(dut.sim_bd_i.axis_tproc64x32_x8_0.m4_axis_tvalid)
  $fwrite(events_file,"%0d,%0d,3,%040h\\n",cycle,tproc_time,dut.sim_bd_i.axis_tproc64x32_x8_0.m4_axis_tdata);''',1)
    body=body.replace('integer cycle=0,','integer rc_file;\ninteger cycle=0,')
    body=body.replace('events_file=$fopen', 'rc_file=$fopen({output_dir,"/rc_analog.csv"},"w");\n $fwrite(rc_file,"cycle,channel,target,dac,after_rc\\n");\n events_file=$fopen',1)
    if args.capture_cycles:
        # Keep a small diagnostic trace; command/timestamp and sample oracles
        # still check every point. Avoid multi-gigabyte full waveform dumps.
        body=body.replace('if(awg1!==last_awg1 || awg3!==last_awg3 || cycle%128==0)',
                          f'if(cycle<cycle_at_start+{args.capture_cycles} && (awg1!==last_awg1 || awg3!==last_awg3 || cycle%128==0))')
        body=re.sub(r'  \$fwrite\(commands_file,[^\n]+',
                    f'  if(cycle<cycle_at_start+{args.capture_cycles}) '+r'\g<0>',body)
    if args.sweep_case:
        body=body.replace('integer rc_file;', 'integer rc_file,rf_file,rf_cmd_file;')
        body=body.replace('events_file=$fopen', '''rf_file=$fopen({output_dir,"/rf_samples.csv"},"w");
 $fwrite(rf_file,"cycle,word\\n");
 rf_cmd_file=$fopen({output_dir,"/rf_commands.csv"},"w");
 $fwrite(rf_cmd_file,"cycle,word\\n");
 events_file=$fopen''',1)
    if capture_version>=2:
        close_files='$fclose(rc_file);'
        if args.sweep_case:
            close_files+='$fclose(rf_file);$fclose(rf_cmd_file);'
        body=body.replace('$fclose(checks_file);',close_files+'$fclose(checks_file);',1)
    monitor=[]
    for ch,cell,raw in ((0,'axis_awg_tuning_v1_4','core_samples'),(1,'axis_awg_tuning_v1_5','core_samples'),(2,'axis_square_pulse_v1_0','raw_samples')):
        monitor.append(f'''
begin: MONITOR{ch}
 logic [255:0] nominal[0:10];
 real z=0,decay,max_error=0,error,y,target;
 integer sample;
 initial begin
  decay=$exp(-1.0/48000.0);
  for(integer i=0;i<11;i=i+1) nominal[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) nominal[i]=nominal[i-1];
  nominal[0]=dut.sim_bd_i.{cell}.{raw};
  #0.001;
  for(integer lane=0;lane<16;lane=lane+1) begin
   sample=$signed(dut.sim_bd_i.{cell}.m_axis_tdata[16*lane+:16]);
   target=$signed(nominal[10][16*lane+:16]);
   y=sample-z; error=y-target;if(error<0)error=-error;
   if(error>max_error)max_error=error;
   if(cycle>100 && error>4.2) $fatal(1,"GUI RC mismatch ch={ch} cycle=%0d error=%f",cycle,error);
   z=decay*z+(1.0-decay)*sample;
   if(lane==0 && cycle%4==0 && (0=={args.capture_cycles} || cycle<cycle_at_start+{args.capture_cycles}))$fwrite(rc_file,"%0d,{ch},%f,%0d,%f\\n",cycle,target,sample,y);
  end
 end
 final $display("GUI_RC_RESULT ch={ch} max_error_codes=%f",max_error);
end
''')
    if args.sweep_case or args.grid_count:
        # The 4.2-code bound belongs to the original fixed waveform. Swept
        # ramps have different DC area residuals; report their analog error
        # while checking the complete digital recurrence exactly below.
        monitor=[re.sub(r'   if\(cycle>100 && error>4.2\).*?\n', '', m) for m in monitor]
        if args.grid_count > 5:
            monitor=[]
        for ch,cell in enumerate(('axis_awg_tuning_v1_4','axis_awg_tuning_v1_5')):
            root=f'dut.sim_bd_i.{cell}'
            monitor.append(f'''
begin: EXACT_AWG{ch}
 logic signed [71:0] integral=0, qhistory[0:8], v, rounded;
 logic signed [15:0] previous_x=0;
 logic [255:0] expected[0:10];
 integer raw;
 longint samples=0;
 initial begin
  for(integer i=0;i<11;i=i+1) expected[i]=0;
  for(integer i=0;i<9;i=i+1) qhistory[i]=0;
 end
 always @(posedge clk_300000000) if(resetn) begin
  for(integer i=10;i>0;i=i-1) expected[i]=expected[i-1];
  for(integer i=8;i>0;i=i-1) qhistory[i]=qhistory[i-1];
  if({root}.rc_clear) begin integral=0;previous_x=0;end
  for(integer lane=0;lane<16;lane=lane+1) begin
   raw=$signed({root}.core_samples[16*lane+:16]);
   if({root}.rc_enabled && {root}.core_valid)
    integral=integral+72'(raw+previous_x)*$signed({{1'b0,{root}.rc_coefficient}});
   if({root}.core_valid)previous_x=raw;
   v=(72'(raw)<<<48)+integral;
   rounded=(v+(72'sd1<<49))>>>50;
   if(rounded>8191 || rounded< -8192) $fatal(1,"Unexpected AWG clipping ch={ch}");
   expected[0][16*lane+:16]={root}.rc_enabled ? 16'(rounded*4) : 16'(raw);
  end
  qhistory[0]=integral;
  #0.001;
  if(cycle>30) begin
   if({root}.m_axis_tdata!==expected[10] || {root}.GEN_RC.rc.integral!==qhistory[8])
    $fatal(1,"Exact AWG recurrence mismatch ch={ch} cycle=%0d",cycle);
   samples=samples+16;
  end
 end
 final $display("EXACT_AWG_RESULT ch={ch} samples=%0d",samples);
end
''')
    top+=body+'\ngenerate\n'+''.join(monitor)+'endgenerate\nendmodule\n'
    if args.sweep_case:
        rf_monitor = '''
begin: RF_MONITOR
 logic [255:0] previous_word=0;
 wire [255:0] word=ext_axis_register_slice_0_m_axis_tdata;
 always @(posedge clk_300000000) if(resetn) begin
  if(dut.sim_bd_i.axis_signal_gen_v6_0.s1_axis_tvalid)
   $fwrite(rf_cmd_file,"%0d,%040h\\n",cycle,dut.sim_bd_i.axis_signal_gen_v6_0.s1_axis_tdata);
  #0.002;
  if(cycle>100 && $isunknown(word)) $fatal(1,"Unknown RF output");
  if(cycle>100 && (word!=0 || previous_word!=0)) $fwrite(rf_file,"%0d,%064h\\n",cycle,word);
  previous_word=word;
 end
end
'''
        top=top.replace('endgenerate\nendmodule', rf_monitor+'endgenerate\nendmodule')
    if args.repeat_reset:
        reset_monitors = []
        for ch, cell in enumerate(('axis_awg_tuning_v1_4', 'axis_awg_tuning_v1_5')):
            root = f'dut.sim_bd_i.{cell}'
            reset_monitors.append(f'''
begin: REPEAT_RESET{ch}
 integer count=0, checks=0, check_at=-1;
 always @(posedge clk_300000000) if(resetn) begin
  if({root}.rc_clear && {root}.rc_enabled) begin
   count=count+1; check_at=cycle+12;
   if({root}.core_samples!==256'd0)
    $fatal(1,"RC reset ch={ch} was issued before nominal output returned to zero");
  end
  if(cycle==check_at) begin
   if({root}.GEN_RC.rc.integral!==72'd0 || {root}.m_axis_tdata!==256'd0)
    $fatal(1,"RC reset ch={ch} did not clear all DAC lanes and history");
   checks=checks+1;
   if({ch}==0 && checks%200==0) $display("GRID_PROGRESS shots=%0d cycle=%0d",checks-1,cycle);
  end
 end
 final begin
  if(count!={shots+1} || checks!={shots+1}) $fatal(1,"Expected {shots+1} reset checks ch={ch}, got %0d/%0d",count,checks);
  $display("REPEAT_RESET_RESULT ch={ch} resets=%0d zero_checks=%0d",count,checks);
 end
end
''')
        top=top.replace('endgenerate\nendmodule', ''.join(reset_monitors)+'endgenerate\nendmodule')
    (out/'tb_rc_gui.sv').write_text(top)
    rtl=[]
    for folder in ('axis_awg_tuning_v1','axis_square_pulse_v1'):
        rtl += [p for p in (HERE.parent/folder/'src').glob('*.sv') if not p.name.startswith('tb_')]
    files=rtl+[out/n for n in ('rc_bd.v','rc_wrapper.v','tb_rc_gui.sv')]
    (out/'sources.prj').write_text(''.join(f'sv xil_defaultlib "{f.as_posix()}"\n' for f in files)+'nosort\n')
    fingerprint=hashlib.sha256(b''.join(p.read_bytes() for p in files+[out/'pmem.hex',out/'dmem.txt'])).hexdigest()
    if args.reuse_snapshot:
        prepared=json.loads((out/'prepared.json').read_text())
        assert prepared['fingerprint']==fingerprint, 'Prepared snapshot/input mismatch'
    def execute(tool,params):
        print(tool,flush=True)
        r=subprocess.run([f'C:/Xilinx/Vivado/2023.1/bin/{tool}.bat',*params],cwd=run,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        (out/f'{tool}.log').write_text(r.stdout)
        if r.returncode or re.search(r'^ERROR:|^Fatal:',r.stdout,re.M):
            print(r.stdout[-8000:]);raise SystemExit(1)
        return r.stdout
    if not args.reuse_snapshot:
        execute('xvlog',['--incr','--relax','-prj',str(out/'sources.prj')])
        libs=list(dict.fromkeys(re.findall(r'-L (\w+)',(run/'elaborate.bat').read_text())))
        execute('xelab',['--incr','--O2','--debug','off','--relax','--mt','4',
            *[v for lib in libs for v in ('-L',lib)],'--snapshot','rc_gui','xil_defaultlib.tb_rc_gui','xil_defaultlib.glbl'])
    if args.isolated_run:
        isolated=out/'sim_run'
        if not args.reuse_snapshot:
            snapshot=isolated/'xsim.dir/rc_gui'
            snapshot.mkdir(parents=True,exist_ok=True)
            for path in (run/'xsim.dir/rc_gui').iterdir():
                if path.is_file():shutil.copy2(path,snapshot/path.name)
            shutil.copy2(run/'xsim.ini',isolated/'xsim.ini')
        run=isolated
    if args.prepare_only:
        (out/'prepared.json').write_text(json.dumps(dict(points=points,shots=shots,cycles=cycles,fingerprint=fingerprint,capture_version=capture_version)))
        return
    (out/'run.tcl').write_text('run all\nquit\n')
    options=['rc_gui',f'-tclbatch "{(out/"run.tcl").as_posix()}"',
             f'-log "{(out/"xsim_live.log").as_posix()}"']
    options += [f'-testplusarg "{v}"' for v in (f'CASE={out.as_posix()}',f'OUT={out.as_posix()}',f'CYCLES={cycles}')]
    (out/'options.txt').write_text('\n'.join(options)+'\n')
    result=(out/'xsim.log').read_text() if args.analyze_only else execute('xsim',['-f',str(out/'options.txt')])
    assert 'RTL COMPLETE' in result and 'Fatal:' not in result and 'ERROR:' not in result
    with (out/'rtl_events.csv').open() as f: actual=list(csv.DictReader(f))
    # Hardware pipeline has one fixed origin offset from the instruction model.
    expected.sort(key=lambda e:(e['cycle'],e['port']))
    actual.sort(key=lambda e:(int(e['cycle']),int(e['port'])))
    assert len(actual)==len(expected),(len(actual),len(expected))
    offset=int(actual[0]['cycle'])-expected[0]['cycle']
    for act,exp in zip(actual,expected):
        assert int(act['port'])==exp['port'] and int(act['word'],16)==int(exp['word'],16),(act,exp)
        assert int(act['cycle'])-exp['cycle']==offset,(act,exp,offset)
    summary=dict(points=points,repetitions=2,commands=len(actual),cycle_offset=offset,
        dac_current_ma=args.dac_current_ma,
        dc_mode=args.dc_mode,dc_voltage_mv=args.dc_voltage_mv,
        sweep_case=args.sweep_case,run_tag=args.run_tag,rf_length_boundary=args.rf_length_boundary,
        rc_range_corners=program.rc_output_range_validation,
        square_amplitude_sweep=args.square_sweep,
        rc_reset_each_repeat=args.repeat_reset,
        no_aux=args.no_aux,
        grid_count=args.grid_count,
        waveform_capture_cycles=args.capture_cycles,
        reset_results=re.findall(r'REPEAT_RESET_RESULT[^\n]+',result),
        cycles=cycles,analog_results=re.findall(r'GUI_RC_RESULT[^\n]+',result),
        exact_awg_results=re.findall(r'EXACT_AWG_RESULT[^\n]+',result),
        retained_cells=sorted(keep),pmem_words=len(program.binprog),dmem_words=len(dm))
    if args.grid_count:
        axes_report=[]
        for ch in range(2):
            events=[e for e in model.output_events if e.tproc_ch==ch]
            reset_positions=[i for i,e in enumerate(events) if e.word & (1<<149)]
            assert len(reset_positions)==shots+1
            first_codes=[]
            for shot in range(shots):
                e=events[reset_positions[shot]+1]
                code=e.word&0xffffffff
                first_codes.append(code if code<2**31 else code-2**32)
            values=np.array(first_codes).reshape(args.grid_count,args.grid_count,2)
            assert np.array_equal(values[:,:,0],values[:,:,1])
            axis=values[:,0,0] if ch==0 else values[0,:,0]
            expected_codes=np.broadcast_to(axis[:,None] if ch==0 else axis[None,:],values[:,:,0].shape)
            assert np.array_equal(values[:,:,0],expected_codes), 'Sweep axis failed to reset'
            requested=np.linspace(5.,15.,args.grid_count)
            measured=axis*(args.dac_current_ma[ch]*40)/32768
            axes_report.append(dict(channel=ch,requested_mv=requested.tolist(),
                executed_target_mv=measured.tolist(),target_codes=axis.tolist(),
                max_target_error_mv=float(max(abs(measured-requested))),
                repeat_mismatches=0,axis_reset_mismatches=0))
        (out/'grid_axes.json').write_text(json.dumps(axes_report,indent=2))
        summary['grid_target_error_mv']=[a['max_target_error_mv'] for a in axes_report]
        summary['compile_validation_mode']=program.compile_validation_mode
    if args.sweep_case:
        with (out/'rf_samples.csv').open() as f: rf_rows=list(csv.DictReader(f))
        pulses=[]; pulse=[]
        for row in rf_rows:
            cycle=int(row['cycle']); word=int(row['word'],16)
            if word:
                samples=[((word >> (16*k)) & 65535) for k in range(16)]
                samples=[v-65536 if v>=32768 else v for v in samples]
                pulse.append((cycle,samples))
            elif pulse:
                pulses.append((pulse,cycle));pulse=[]
        assert not pulse and len(pulses)==shots, len(pulses)
        rf_starts=[e for e in model.output_events if e.tproc_ch==0 and (e.word>>152)&255==0 and (e.word>>96)&0xffffffff]
        rf_stops=[e for e in model.output_events if e.tproc_ch==0 and (e.word>>152)&255==0 and not (e.word>>96)&0xffffffff]
        assert len(rf_starts)==shots
        periodic=[bool((e.word>>146)&1) for e in rf_starts]
        expected_periodic=(max(round(rf_duration_start*300),round(rf_duration_stop*300))>65535
                           if args.sweep_case in ('rf_duration','rf_duration_fixed') else False)
        assert all(mode==expected_periodic for mode in periodic), 'RF output mode differs from requested whole-axis length policy'
        assert len(rf_stops)==sum(periodic),(len(rf_stops),sum(periodic))
        stop_iter=iter(rf_stops)
        from qick_fine_tune_sweep import RfFrequencySweep, RfPowerSweep
        measurements=[]
        for shot,((wave,stop),event) in enumerate(zip(pulses,rf_starts)):
            values=np.array([v for _,word in wave for v in word])
            crossing=np.flatnonzero((values[:-1]<0)&(values[1:]>=0))
            crossing=crossing-values[crossing]/(values[crossing+1]-values[crossing])
            frequency=(len(crossing)-1)*4800/(crossing[-1]-crossing[0])
            expected_frequency=(event.word&0xffffffff)*4800/2**32
            peak=int(max(abs(values)))
            block_cycles=(event.word>>128)&65535
            expected_width=next(stop_iter).cycle-event.cycle if periodic[shot] else block_cycles
            # The existing RF controller reads queued updates only at the
            # periodic block boundary. Keep requested-width errors visible;
            # matching this architecture is not an exact-timing pass.
            architecture_width=((expected_width+block_cycles-1)//block_cycles)*block_cycles if periodic[shot] else expected_width
            requested_width=(rf_duration_start+(rf_duration_stop-rf_duration_start)*(shot//2%args.sweep_count)/(args.sweep_count-1))*300 if args.sweep_case in ('rf_duration','rf_duration_fixed') else 30.
            assert expected_width==round(requested_width),(shot,expected_width,requested_width)
            expected_gain=(event.word>>96)&0xffffffff
            # A finite sampled sine need not hit its continuous-time peak.
            # Recover its amplitude using all samples at the programmed FTW.
            phase=np.arange(len(values))*2*np.pi*(event.word&0xffffffff)/2**32
            basis=np.column_stack((np.cos(phase),np.sin(phase),np.ones(len(values))))
            fit=np.linalg.lstsq(basis,values,rcond=None)[0]
            amplitude=float(np.hypot(fit[0],fit[1]))
            fit_residual=float(max(abs(basis@fit-values)))
            coordinates=program.sequence.sweep_coordinate(shot//2)
            requested_frequency=190.
            requested_power=None
            for axis,coordinate in zip(program.sequence.sweep_axes,coordinates):
                if isinstance(axis,RfFrequencySweep):requested_frequency=float(coordinate)
                if isinstance(axis,RfPowerSweep):requested_power=float(coordinate)
            assert (event.word&0xffffffff)==int(cfg.freq2reg(requested_frequency,gen_ch=0))
            if requested_power is not None:
                fixture_gain=2000*10**((requested_power+20-.01*(requested_frequency-190))/20)
                assert abs(expected_gain-fixture_gain)<=1., (shot,expected_gain,fixture_gain)
            assert abs(frequency-expected_frequency)<.02, (shot,frequency,expected_frequency)
            assert abs(amplitude-expected_gain)<=1, (shot,amplitude,expected_gain)
            assert fit_residual<=4, (shot,fit_residual)
            assert stop-wave[0][0]==architecture_width, (shot,stop-wave[0][0],architecture_width)
            measurements.append(dict(shot=shot,frequency_mhz=frequency,expected_frequency_mhz=expected_frequency,
                peak_code=peak,expected_gain=expected_gain,width_cycles=stop-wave[0][0],
                fitted_amplitude_code=amplitude,fit_residual_max_codes=fit_residual,
                requested_frequency_mhz=requested_frequency,requested_power_dbm=requested_power,
                command_width_cycles=expected_width,architecture_width_cycles=architecture_width,
                width_error_cycles=stop-wave[0][0]-expected_width,
                requested_width_cycles=requested_width,latency_cycles=wave[0][0]-event.cycle-offset))
        command_triples=np.array([(e.word&0xffffffff,(e.word>>96)&0xffffffff,r['command_width_cycles'])
            for e,r in zip(rf_starts,measurements)],dtype=np.int64).reshape(points,2,3)
        assert np.array_equal(command_triples[:,0],command_triples[:,1]), 'Repetition changed RF command values'
        assert len({r['latency_cycles'] for r in measurements})==1
        (out/'rf_measurements.json').write_text(json.dumps(measurements,indent=2))
        summary['rf_measurements']=dict(pulses=len(measurements),
            periodic=expected_periodic,
            repetition_command_mismatches=0,
            frequency_error_max_mhz=max(abs(r['frequency_mhz']-r['expected_frequency_mhz']) for r in measurements),
            peak_error_max_codes=max(abs(r['peak_code']-r['expected_gain']) for r in measurements),
            amplitude_error_max_codes=max(abs(r['fitted_amplitude_code']-r['expected_gain']) for r in measurements),
            fit_residual_max_codes=max(r['fit_residual_max_codes'] for r in measurements),
            width_mismatch_pulses=sum(r['width_error_cycles']!=0 for r in measurements),
            width_error_max_cycles=max(abs(r['width_error_cycles']) for r in measurements),
            gain_codes=sorted({r['expected_gain'] for r in measurements}),
            requested_width_error_max_cycles=max(abs(r['width_cycles']-r['requested_width_cycles']) for r in measurements),
            widths_cycles=sorted({r['width_cycles'] for r in measurements}),
            latency_cycles=measurements[0]['latency_cycles'])
    summary['validation_status']='passed'
    if summary.get('rf_measurements',{}).get('width_mismatch_pulses',0):
        summary['validation_status']='completed_with_timing_findings'
        summary['findings']=['RF periodic block boundaries delay the output stop by up to two fabric clocks; requested duration is not exact.']
    (out/'result.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    if summary['validation_status']!='passed':
        raise SystemExit(2)


if __name__=='__main__':main()
