"""Check routed-path changes in isolation before replacing production sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,required=True)
p.add_argument('--candidate-dir',type=Path)
p.add_argument('--vivado',type=Path,default=Path('F:/Xilinx/Vivado/2023.1'))
a=p.parse_args()
a.build.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent
ip=here.parent.parent
ctrl=(a.candidate_dir/'v3_awg_tuning_ctrl.sv' if a.candidate_dir else here.parent/'src/v3_awg_tuning_ctrl.sv')
square=(a.candidate_dir/'square_rc_precomp.sv' if a.candidate_dir else ip/'axis_square_pulse_v1/src/square_rc_precomp.sv')
sources=[ctrl,square,ip/'axis_awg_tuning_v2/validation/awg_v2_raw_checker.sv',here/'tb_timing_tail.sv',a.vivado/'data/verilog/src/glbl.v']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
(a.build/'sources.json').write_text(json.dumps(hashes,indent=2))
with (a.build/'run.log').open('w') as log:
    for tool,options in [('xvlog',['-sv',*map(str,sources)]),('xelab',['--relax','--timescale','1ns/1ps','-L','unisims_ver','tb_timing_tail','glbl','-s','tail']),('xsim',['tail','-runall'])]:
        result=subprocess.run([str(a.vivado/'bin'/f'{tool}.bat'),*options],cwd=a.build,stdout=log,stderr=subprocess.STDOUT)
        log.flush()
        if result.returncode:raise SystemExit(result.returncode)
text=(a.build/'run.log').read_text(errors='replace')
passed='PASS TIMING TAIL:' in text and 'Fatal:' not in text and 'ERROR:' not in text
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
(a.build/'result.json').write_text(json.dumps({'passed':passed,'sources':hashes},indent=2))
print('\n'.join(s for s in text.splitlines() if any(k in s for k in ('PASS','Fatal:','ERROR:','RESULT'))))
raise SystemExit(0 if passed else 1)
