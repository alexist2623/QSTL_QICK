"""Check saved RTL evidence and recompile GUI programs after an interrupted host."""
import argparse
import hashlib
import json
from pathlib import Path
import py_compile
import re
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim
    from qick import QickConfig
    from PIL import Image
    here=Path(__file__).resolve().parent
    cfg=QickConfig(json.loads((here.parents[1]/'projects/qstl_gui_rtl_sim/soccfg.json').read_text()))
    for gen in cfg['gens']:
        if gen['type'] in ('axis_awg_tuning_v1','axis_square_pulse_v1'):
            gen.update(rc_precomp_version=1,output_latency_cycles=11)
        if gen['type']=='axis_square_pulse_v1': gen['command_latency_cycles']=15
        if gen['type']=='axis_awg_tuning_v1': gen.update(type='axis_awg_tuning_v2',frac=18,step_width=32)
    records=[]
    for folder in sorted(args.build.glob('*fir_dc4_*awg_v2')):
        prepared=json.loads((folder/'prepared.json').read_text())
        result=json.loads((folder/'result.json').read_text())
        assert result['validation_status']=='passed' and result['points']==9 and result['repetitions']==2
        files=[Path(p) for p in re.findall(r'^sv xil_defaultlib "([^"]+)"',
                                          (folder/'sources.prj').read_text(),re.M)]
        digest=hashlib.sha256(b''.join(p.read_bytes() for p in files+[folder/'pmem.hex',folder/'dmem.txt'])).hexdigest()
        assert digest==prepared['fingerprint'], f'Simulation source/input changed: {folder}'
        ns={}
        exec(compile((folder/'gui_export.py').read_text(),str(folder/'gui_export.py'),'exec'),ns)
        program=ns['build_program'](cfg)
        program.compile()
        saved=[int(line,16) for line in (folder/'pmem.hex').read_text().splitlines()]
        assert [int(w) for w in program.binprog]==saved, f'Current GUI PMEM differs: {folder}'
        dmem={int(a,16):int(w,16) for a,w in (line.split() for line in (folder/'dmem.txt').read_text().splitlines())}
        actual={program._runtime_dmem_base+i:int(w)&0xffffffff for i,w in enumerate(program._runtime_dmem_words)}
        assert actual==dmem, f'Current GUI DMEM differs: {folder}'
        records.append(dict(case=folder.name,fingerprint=digest,pmem_matches=True,dmem_matches=True))
    assert len(records)==8
    for name in ('DCWaveform_Generator.py','dc_waveform_core.py','qick_fine_tune_sweep.py',
                 'qick_qcodes_experiment.py','test_dc_readout_timing.py'):
        py_compile.compile(str(args.gui/'DCWaveformGeneratorGUI'/name),doraise=True)
    for path in args.out.glob('*.png'):
        with Image.open(path) as picture: picture.verify()
    for path in args.out.glob('*.json'):
        json.loads(path.read_text())
    (args.out/'recovery_integrity.json').write_text(json.dumps(dict(
        cases=records,python_compile='passed',png_decode='passed',json_parse='passed'),indent=2))
    print('PASS: 8 RTL fingerprints, current GUI PMEM/DMEM, Python files, report JSON/PNG')


if __name__=='__main__': main()
