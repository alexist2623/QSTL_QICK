"""Run v8 RTL with the installed Vivado simulator; keep generated files outside Git."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--build',type=Path,required=True)
parser.add_argument('--bench',required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[5]
ip=repo/'qick/firmware/ip'
vivado=Path('F:/Xilinx/Vivado/2023.1')
if args.bench in ('tb_abort','tb_axis_buffer_ddr_sample_v4'):
    sources=list((ip/'axis_buffer_ddr_sample_v4/src').glob('*.sv'))
    if args.bench=='tb_abort': sources += [ip/'axis_buffer_ddr_sample_v4/test/tb_abort.sv']
else:
    sources=list((ip/'axis_awg_tuning_v8/src').glob('*.sv'))
    sources += [ip/'axis_awg_tuning_v8/test/awg_v8_raw_checker.sv',ip/f'axis_awg_tuning_v8/test/{args.bench}.sv',vivado/'data/verilog/src/glbl.v']
    if args.bench=='tb_timing_tail': sources += [ip/'axis_square_pulse_v1/src/square_rc_precomp.sv']
args.build.mkdir(parents=True,exist_ok=False)
if args.bench=='tb_ramp_edges':
    import sys
    sys.path.insert(0,str(ip/'axis_awg_tuning_v8/test'))
    from generate_ramp_vectors import generate
    generate(args.build)
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
commands=[('xvlog',['-sv',*map(str,sources)]),('xelab',['--relax','--timescale','1ns/1ps','-L','unisims_ver',args.bench,*(['glbl'] if 'glbl.v' in [p.name for p in sources] else []),'-s','unit']),('xsim',['unit','-runall'])]
code=0
with (args.build/'run.log').open('w') as log:
    for stage,params in commands:
        r=subprocess.run([str(vivado/'bin'/f'{stage}.bat'),*params],cwd=args.build,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        log.flush()
        code=r.returncode
        if code: break
text=(args.build/'run.log').read_text(errors='replace')
passed=code==0 and 'PASS' in text and 'Fatal:' not in text and 'ERROR:' not in text
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
(args.build/'result.json').write_text(json.dumps(dict(passed=passed,exit_code=code,bench=args.bench,sources=hashes),indent=2))
print('\n'.join(line for line in text.splitlines() if any(w in line for w in ('PASS','ERROR:','Fatal:'))))
raise SystemExit(0 if passed else 1)
