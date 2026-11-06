"""Run generated output-only programs on the real CPU/TMUX/AWG/DDS RTL."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys


def run(build, gui_root, vivado):
    repo = Path(__file__).resolve().parents[3]
    sys.path[:0] = [str(gui_root), str(gui_root/'test'), str(repo/'qick/qick_lib')]
    from test_v8_controls import v8_config, pulse
    from test_output_forever import StopModel
    from dc_waveform_core import build_qick_sequence
    from qick_fine_tune_sweep import FineTuneSequence, RfPulseConfig
    build.mkdir(parents=True, exist_ok=False)
    records = []
    for case in range(10):
        dc, rc = bool(case & 1), bool(case & 2)
        cfg = v8_config()
        if case < 4:
            sequence = build_qick_sequence((pulse(),))
            shots = 3
        elif case < 8:
            sequence = FineTuneSequence(('a',))
            sequence.add_set('start', (0.0,), 30)
            sequence.add_ramp('ramp', 16)
            sequence.add_set('hold', (.2,), 30)
            sequence.add_amplitude_sweep('hold','a',.1,.3,3)
            shots = 13
        else:
            from test_qick_square_dds import configuration
            from qick_square_dds import SquarePulseConfig, OutputTriggerConfig, attach_square_settings
            dc = rc = case == 9
            cfg['gens'].append(configuration()['gens'][1])
            cfg['gens'][-1]['rc_precomp_version']=1
            cfg['tprocs'][0]['output_pins']=[('output',7,6,'SPARE1_1V8')]
            sequence=FineTuneSequence(('a',)).add_set('hold',(.1,),300)
            sequence.set_rc_compensation(200,enabled=rc)
            attach_square_settings(sequence,SquarePulseConfig(2,mute_on_finish=False),(),
                                   OutputTriggerConfig(True,0,'loop','both',1), follow_experiment_rc=True)
            shots=3
        sequence.set_bias_t_compensation(.1, enabled=dc, mode='fixed_time', fixed_duration_cycles=300)
        sequence.set_rc_compensation(200, enabled=rc)
        program = sequence.make_program(cfg,(1,),repetitions_per_sweep=2,
                                         execution_mode='output_forever',
                                         rf_pulse=(None if case < 4 or case >= 8 else RfPulseConfig(0,'hold',5,1000,delay_tproc_cycles=1,freq_mhz=0)))
        program.compile()
        model=StopModel(shots);program.load_runtime_dmem_into_model(model);model.run(program)
        prefix=build/f'case{case}'
        def save(suffix, values, digits):
            Path(str(prefix)+suffix).write_text(''.join(f'{int(v):0{digits}x}\n' for v in values),encoding='ascii')
        save('_pmem.hex',program.binprog,16)
        memory=[0]*4096
        for offset,value in enumerate(program._runtime_dmem_words):
            memory[program._runtime_dmem_base+offset]=value & 0xffffffff
        save('_dmem.hex',memory,8)
        save('_expected.hex',[(e.cycle<<160)|e.word for e in model.output_events],52)
        save('_pins.hex',[(e['cycle']<<32)|e['word'] for e in model.output_pin_events],20)
        save('_meta.hex',[len(model.output_events),len(program.binprog),0,shots,len(model.output_pin_events)],8)
        Path(str(prefix)+'.asm').write_text(program.asm(),encoding='utf-8')
        records.append(dict(case=case,dc=dc,rc=rc,shots=shots,commands=len(model.output_events)))
    tp=repo/'qick/firmware/ip/axis_tproc64x32_x8_v2/src'
    vhd=[tp/p for p in ('fifo/bram_simple_dp.vhd','fifo/fifo.vhd','alu/math.vhd','alu/bitw.vhd',
                        'regfile/regfile.vhd','regfile/regfile_8p.vhd','cond.vhd','s_axis_read.vhd',
                        'stack.vhd','synchronizer_n.vhd','timed_ictrl.vhd')]
    sv=[tp/'tproc64x32_x8.v',tp/'ctrl.sv',tp/'alu/alu.v']
    sv += [repo/'qick/firmware/ip/axis_tmux_v1/src'/p for p in ('tmux.sv','axis_tmux_v1.sv')]
    import re
    dds=sorted(p for p in Path('F:/Vivado_Output/a3sim1/namespaced').iterdir()
               if re.match(r'^0(4[1-9]|5[0-2])_',p.name))
    assert len(dds)==12
    vhd += [p for p in dds if p.suffix=='.vhd']
    sv += [p for p in dds if p.suffix!='.vhd']
    sv += [repo/'qick/firmware/ip/axis_square_pulse_v1/src'/p for p in ('axis_square_pulse_v1.sv','square_dds.sv','square_rc_precomp.sv')]
    sv += sorted((repo/'qick/firmware/ip/axis_awg_tuning_v8/src').glob('*.sv'))
    sv += [repo/'qick/firmware/ip/axis_output_sum_v7/src/axis_output_sum_v7.sv',
           repo/'qick/firmware/projects/qstl_awg_v8/test/cpu_native_pair.sv',
           Path(__file__).with_name('tb_output_forever.sv'), vivado/'data/verilog/src/glbl.v']
    sources = vhd+sv+[Path(__file__),gui_root/'qick_fine_tune_sweep.py']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (build/'sources.json').write_text(json.dumps(hashes,indent=2))
    for name,kind,files in (('vhdl','vhdl',vhd),('verilog','sv',sv)):
        (build/f'{name}.prj').write_text('\n'.join(f'{kind} xil_defaultlib "{p.as_posix()}"' for p in files)+'\nnosort\n')
    result=dict(passed=False,cases=records,scope='Full CPU/TMUX/AWG v8/DDS/sum; synchronous host memory model')
    try:
        for tool,args in [
            ('xvhdl',['--relax','-prj','vhdl.prj']),
            ('xvlog',['--relax','-prj','verilog.prj']),
            ('xelab',['--relax','--O2','--mt','2','-L','xil_defaultlib','-L','dds_compiler_v6_0_22',
                      '-L','unisims_ver','-L','unimacro_ver','-L','secureip',
                      'xil_defaultlib.tb_output_forever','xil_defaultlib.glbl','--snapshot','forever']),
            ('xsim',['forever','-runall'])]:
            with (build/f'{tool}_console.log').open('w') as log:
                subprocess.run([str(vivado/'bin'/f'{tool}.bat')]+args,cwd=build,stdout=log,
                               stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(build/'xsim_console.log').read_text()
        assert 'OUTPUT_FOREVER_RTL_PASS cases=10' in log and 'Fatal:' not in log
        assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        result['passed']=True
    finally:
        (build/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--gui-root',type=Path,default=Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI'))
    parser.add_argument('--vivado',type=Path,default=Path('F:/Xilinx/Vivado/2023.1'))
    args=parser.parse_args();run(args.build,args.gui_root,args.vivado)
