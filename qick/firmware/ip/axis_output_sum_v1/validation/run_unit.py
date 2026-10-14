"""Run the isolated, full-lane saturating sum/bypass xsim test."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--vivado',type=Path,default=Path('F:/Xilinx/Vivado/2023.1'))
    args=p.parse_args()
    args.build.mkdir(parents=True,exist_ok=False)
    here=Path(__file__).resolve().parent
    sources=[here.parent/'src/axis_output_sum_v1.sv',here/'tb_output_sum.sv']
    (args.build/'source_hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2))
    stages=[('xvlog',['-sv',*map(str,sources)]),
            ('xelab',['tb_output_sum','-s','output_sum']),('xsim',['output_sum','-runall'])]
    passed=True
    with (args.build/'run.log').open('w') as log:
        for stage,argv in stages:
            r=subprocess.run([str(args.vivado/'bin'/f'{stage}.bat'),*argv],cwd=args.build,stdout=log,stderr=subprocess.STDOUT)
            log.flush()
            if r.returncode: passed=False;break
    text=(args.build/'run.log').read_text(errors='replace')
    passed=passed and 'OUTPUT_SUM_PASS' in text and not any(x in text for x in ('Fatal:','ERROR:'))
    summary=dict(passed=passed,stage=stage,exit_code=r.returncode)
    m=re.search(r'OUTPUT_SUM_PASS (.*)',text)
    if m: summary.update({k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])})
    (args.build/'result.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
