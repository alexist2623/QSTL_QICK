"""Run real GUI mute/standalone programs on production tProcessor + DDS RTL."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CASES = ('gui_mute_on', 'gui_mute_off', 'gui_square_standalone')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('build', type=Path)
    p.add_argument('--gui', type=Path, required=True)
    p.add_argument('--analyze-only', action='store_true')
    a = p.parse_args()
    sys.path.insert(0, str(a.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim
    from qick import QickConfig
    from qick.awg_tuning import TProcV1BehaviorModel
    from dc_waveform_core import PulseSequence, generate_qick_program_code
    from qick_square_wave import SquareWaveConfig, build_square_wave_program
    import numpy as np
    cfg = QickConfig(json.loads((HERE/'soccfg.json').read_text()))
    out = a.build/'square_gui_controls'
    out.mkdir(exist_ok=True)
    run = a.build/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    if not a.analyze_only:
        for case in CASES:
            d = HERE/case
            d.mkdir(exist_ok=True)
            if case == 'gui_square_standalone':
                settings = SquareWaveConfig(gen_ch=7, frequency_hz=2000, amplitude_mv=20,
                                            zero_code=0, phase_deg=45)
                program = build_square_wave_program(cfg, settings, tproc_mhz=300)
                (d/'settings.json').write_text(json.dumps(settings.__dict__, indent=2)+'\n')
            else:
                pulse = PulseSequence()
                pulse.t = np.array([0., 10000.]); pulse.v = np.array([10., 10.])
                pulse.segment_names = ['hold']
                square = dict(enabled=True, gen_ch=7, mute_on_finish=case=='gui_mute_on',
                    parameters={'frequency':dict(value=.002), 'phase':dict(value=45),
                                'amplitude':dict(value=10, sweep=True, start=10, stop=20, count=2)})
                code = generate_qick_program_code([pulse], awg_channels=(1,),
                    full_scale_mv=800, fabric_mhz=300, tproc_mhz=300,
                    square_pulse_settings=square, repetitions_per_sweep=1)
                (d/'gui_export.py').write_text(code, encoding='utf-8')
                ns = {}; exec(compile(code, str(d/'gui_export.py'), 'exec'), ns)
                program = ns['build_program'](cfg)
            program.compile()
            (d/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in program.binprog))
            (d/'program.asm').write_text(program.asm())
            words = getattr(program, '_runtime_dmem_words', ())
            base = getattr(program, '_runtime_dmem_base', 0)
            (d/'dmem.txt').write_text(''.join(f'{base+i:08x} {int(w)&0xffffffff:08x}\n' for i,w in enumerate(words)))
            model = TProcV1BehaviorModel(strict=True)
            if words: program.load_runtime_dmem_into_model(model)
            model.run(program)
            events = [dict(cycle=e.cycle, port=e.tproc_ch, word=f'{e.word:040x}') for e in model.output_events]
            meta = dict(events=events, stop_cycle=330000, mute_on_finish=case=='gui_mute_on')
            (d/'expected.json').write_text(json.dumps(meta, indent=2)+'\n')

        # Retain the exact production instances and routing for both paths.
        source = a.build/'qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/sim/sim_bd.v'
        text = source.read_text()
        keep = {'axis_tproc64x32_x8_0', 'axis_tmux_v1_0', 'axis_tmux_v1_3',
                'axis_awg_tuning_v1_4', 'axis_square_pulse_v1_0',
                'axis_register_slice_8', 'axis_register_slice_9',
                'axis_register_slice_12', 'axis_register_slice_23',
                *('xlconstant_'+str(i) for i in range(5))}
        pattern = re.compile(r'^  (sim_bd_\w+) (\w+)\s*\n.*?\);', re.M|re.S)
        instances = list(pattern.finditer(text))
        assert len(instances)==78 and keep <= {m[2] for m in instances}
        text = pattern.sub(lambda m:m[0] if m[2] in keep else '', text)
        text = text.replace('module sim_bd\n', 'module square_controls_bd\n', 1)
        ties = [f"assign axis_clk_cnvrt_avg_{i}_M_AXIS_TDATA=64'b0;\nassign axis_clk_cnvrt_avg_{i}_M_AXIS_TVALID=1'b0;" for i in range(4)]
        ties += [f"assign axis_tproc64x32_x8_0_m{i}_axis_TREADY=1'b1;" for i in (2,3,5,6,7,8)]
        text = text.replace('endmodule', '\n'.join(ties)+'\nendmodule')
        copied = {m[2]:m[0] for m in pattern.finditer(text)}
        assert all(copied[m[2]]==m[0] for m in instances if m[2] in keep)
        (out/'square_controls_bd.v').write_text(text)
        wrapper = Path((a.build/'wrapper_path.txt').read_text().strip()).read_text()
        wrapper = wrapper.replace('module sim_bd_wrapper', 'module square_controls_wrapper', 1)
        wrapper = wrapper.replace('sim_bd sim_bd_i', 'square_controls_bd sim_bd_i', 1)
        (out/'square_controls_wrapper.v').write_text(wrapper)
        top = (HERE/'tb_gui.sv').read_text().replace('module tb_gui;', 'module tb_square_controls;', 1)
        top = top.replace('sim_bd_wrapper dut', 'square_controls_wrapper dut', 1)
        # Remove only the unused RF observation, not a tested datapath.
        top = re.sub(r'always @\(posedge clk_300000000\) if \(resetn && dut.sim_bd_i.axis_signal_gen_v6_2.*?;\n', '', top, flags=re.S)
        top = top.replace('`include "tb_body.svh"', '`include "square_controls_body.svh"')
        (out/'tb_square_controls.sv').write_text(top)
        body = (HERE/'tb_body.svh').read_text()
        body = re.sub(r'wire \[127:0\] fir_samples = .*?;', "wire [127:0] fir_samples = 128'b0;", body)
        body = re.sub(r'wire fir_valid = .*?;', "wire fir_valid = 1'b0;", body)
        body = body.replace('wire [255:0] rf_samples = ext_axis_register_slice_2_m_axis_tdata;', "wire [255:0] rf_samples = 256'b0;")
        body = re.sub(r'always @\(posedge clk_300000000\) if\(resetn\) begin\n if\(dut.sim_bd_i.ddr4_axis_buffer.*?end\n\n// Ordered', '// Ordered', body, flags=re.S)
        body = '\n'.join(line for line in body.splitlines() if not line.strip().startswith(('host_write(SWITCH', 'host_write(DDR')))+'\n'
        body = body.replace('checks_file=$fopen', '''if(dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.ir_r[63:56] !== 8'h3f)
   $fatal(1,"GUI program did not reach END");
 manual_mute=1;
 $fwrite(epoch_file,"%0d,manual_mute\\n",cycle);
 host_write(15,0,0);
 repeat(100) @(negedge clk_300000000);
 repeat(32) begin
  @(negedge clk_300000000);
  if(dac_samples !== 256'b0) $fatal(1,"AXI-Lite Stop did not mute the DAC");
 end
 $display("AXI-LITE MUTE PASS");
 checks_file=$fopen''')
        body = body.replace('if(cycle>16) begin', 'if(cycle>16 && !manual_mute) begin')
        body += '''
bit end_logged=0;
bit manual_mute=0;
always @(posedge clk_300000000) if(resetn && !end_logged &&
 dut.sim_bd_i.axis_tproc64x32_x8_0.inst.tproc_i.ir_r[63:56] === 8'h3f) begin
 end_logged=1;$fwrite(epoch_file,"%0d,end_confirmed\\n",cycle);
end
'''
        (out/'square_controls_body.svh').write_text(body)
        provenance = dict(retained_cells=sorted(keep), instances_identical=True,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            gui_sources={n:hashlib.sha256((a.gui/'DCWaveformGeneratorGUI'/n).read_bytes()).hexdigest()
                         for n in ('qick_square_dds.py','qick_square_wave.py','qick_fine_tune_sweep.py','dc_waveform_core.py')})
        (HERE/'square_controls_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        files=['square_controls_bd.v','square_controls_wrapper.v','tb_square_controls.sv']
        (out/'sources.prj').write_text(''.join(f'sv xil_defaultlib "{(out/n).as_posix()}"\n' for n in files)+'nosort\n')
        def execute(tool, args, log):
            print(tool, log, flush=True)
            r = subprocess.run([f'C:/Xilinx/Vivado/2023.1/bin/{tool}.bat', *args],cwd=run,
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
            log.write_text(r.stdout)
            if r.returncode or re.search(r'^ERROR:|^Fatal:',r.stdout,re.M):
                print(r.stdout[-6000:]); raise SystemExit(1)
            return r.stdout
        execute('xvlog',['--incr','--relax','-prj',str(out/'sources.prj'),'-i',str(out)],out/'xvlog.log')
        libs=list(dict.fromkeys(re.findall(r'-L (\w+)',(run/'elaborate.bat').read_text())))
        execute('xelab',['--incr','--O2','--debug','off','--relax','--mt','4',
            *[v for lib in libs for v in ('-L',lib)],'--snapshot','square_controls',
            'xil_defaultlib.tb_square_controls','xil_defaultlib.glbl'],out/'xelab.log')
        (out/'run.tcl').write_text('run all\nquit\n')
        for case in CASES:
            d=HERE/case
            options=['square_controls',f'-tclbatch "{(out/"run.tcl").as_posix()}"']
            options += [f'-testplusarg "{v}"' for v in (f'ROOT={HERE.as_posix()}',f'CASE={d.as_posix()}', 'CYCLES=330000','NTRIG=0')]
            (out/'options.txt').write_text('\n'.join(options)+'\n')
            result=execute('xsim',['-f',str(out/'options.txt')],d/'xsim.log')
            assert 'RTL COMPLETE' in result
    results={}
    for case in CASES:
        d=HERE/case
        def rows(name):
            with (d/name).open() as f:return list(csv.DictReader(f))
        checks=dict(line.split('=') for line in (d/'rtl_checks.txt').read_text().splitlines())
        assert int(checks['errors'])==0
        meta=json.loads((d/'expected.json').read_text())
        events=rows('rtl_events.csv'); commands=rows('rtl_commands.csv')
        assert len(events)==len(meta['events'])
        for actual,expected in zip(events,meta['events']):
            assert int(actual['tproc_time'])==expected['cycle']+1
            assert int(actual['port'])==expected['port'] and actual['word']==expected['word']
        sq=[r for r in commands if r['kind']=='sqcmd']
        origin={int(r['cycle'])-int(r['tproc_time']) for r in events}
        assert len(origin)==1
        origin=origin.pop()
        expected_sq=[e for e in meta['events'] if e['port']==cfg['gens'][7]['tproc_ch']
                     and int(e['word'],16)>>152==cfg['gens'][7]['tmux_ch']]
        assert len(sq)==len(expected_sq)
        for actual,expected in zip(sq,expected_sq):
            assert actual['word']==expected['word']
            assert int(actual['cycle'])==origin+expected['cycle']+4
        assert all(int(r['word'],16)&(1<<129)==0 for r in sq)
        assert bool(int(sq[-1]['word'],16)&(1<<128)) == (case!='gui_mute_on')
        end_cycle=next(int(r['cycle']) for r in rows('rtl_epochs.csv') if r['kind']=='end_confirmed')
        mute_cycle=next(int(r['cycle']) for r in rows('rtl_epochs.csv') if r['kind']=='manual_mute')
        trace=rows('rtl_samples.csv')
        tail=[r for r in trace if end_cycle+100<int(r['cycle'])<mute_cycle]
        codes=[int(r['dac'],16)&65535 for r in tail]
        codes=[v-65536 if v>=32768 else v for v in codes]
        if case=='gui_mute_on':assert set(codes)=={0}
        else:assert set(codes)=={-820,820}
        assert 'AXI-LITE MUTE PASS' in (d/'xsim.log').read_text()
        results[case]=dict(passed=True,core_samples=int(checks['samples']),
            dac_samples=int(checks['samples']),command_count=len(sq),end_cycle=end_cycle,
            cycles_after_end=mute_cycle-end_cycle,
            final_levels=sorted(set(codes)),phase_reset_commands=0,axi_lite_stop_passed=True,
            command_routing_passed=True)
    (HERE/'square_controls_results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
