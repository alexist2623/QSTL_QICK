"""Compile the isolated production HDL and run one GUI machine-code image."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import shutil

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('project',type=Path)
    p.add_argument('case');p.add_argument('--reuse',action='store_true')
    p.add_argument('--snapshot', default='gui_isolated')
    p.add_argument('--optimization', choices=('2','3'), default='2')
    p.add_argument('--compile-only', action='store_true')
    p.add_argument('--isolated-run', action='store_true',
                   help='Copy the compiled snapshot into a case-specific run directory (requires --reuse).')
    p.add_argument('--vivado',type=Path,default=Path('C:/Xilinx/Vivado/2023.1/bin'))
    a=p.parse_args();run=a.project/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    if a.isolated_run:
        if not a.reuse:p.error('--isolated-run requires --reuse')
        source=run
        run=a.project/'case_runs'/a.case
        run.mkdir(parents=True,exist_ok=True)
        snapshot=run/'xsim.dir'/a.snapshot
        snapshot.mkdir(parents=True,exist_ok=True)
        for path in (source/'xsim.dir'/a.snapshot).iterdir():
            if path.is_file():shutil.copy2(path,snapshot/path.name)
        shutil.copy2(source/'xsim.ini',run/'xsim.ini')
    case=HERE/a.case;meta=json.loads((case/'expected.json').read_text())
    def command(tool,args):
        print(tool,flush=True)
        result=subprocess.run([str(a.vivado/(tool+'.bat')),*args],cwd=run,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        (case/(tool+'_console.log')).write_text(result.stdout)
        if result.returncode or re.search(r'^ERROR:|^Fatal:',result.stdout,re.M):
            print(result.stdout[-7000:]);raise SystemExit(result.returncode or 1)
        return result.stdout
    if not a.reuse:
        command('xvlog',['--incr','--relax','-prj','isolated_vlog.prj','-i',str(a.project/'namespaced'),'-log','isolated_xvlog.log'])
        command('xvhdl',['--incr','--relax','-prj','isolated_vhdl.prj','-log','isolated_xvhdl.log'])
        libs=list(dict.fromkeys(re.findall(r'-L (\w+)',(run/'elaborate.bat').read_text())))
        command('xelab',['--incr','--O'+a.optimization,'--debug','off','--relax','--mt','4',
            *[v for lib in libs for v in ('-L',lib)],'--snapshot',a.snapshot,
            'xil_defaultlib.tb_gui','xil_defaultlib.glbl','-log','isolated_elaborate.log'])
    if a.compile_only:return
    (run/'run_all.tcl').write_text('run all\nquit\n')
    ntrig=sum(bool(int(e['word'],16)&32) for e in meta['events'] if e['port']==7)
    options=[a.snapshot,'-tclbatch run_all.tcl',f'-log "{(case/"xsim.log").as_posix()}"']
    options += [f'-testplusarg "{arg}"' for arg in (
        'ROOT='+HERE.as_posix(),'CASE='+case.as_posix(),f'CYCLES={meta["stop_cycle"]}',
        f'NTRIG={ntrig}',f'SEED={int(a.case=="gui_autonomy")}')]
    # The vendor Windows batch wrapper splits unquoted NAME=value arguments.
    # A simulator options file preserves each plusarg without shell parsing.
    (run/'case_options.txt').write_text('\n'.join(options)+'\n')
    checks=case/'rtl_checks.txt'
    checks.unlink(missing_ok=True)
    output=command('xsim',['-f','case_options.txt'])
    if 'RTL COMPLETE' not in output or not checks.is_file():
        raise SystemExit('Simulator ended before the testbench completion marker.')
    print((case/'rtl_checks.txt').read_text(),flush=True)


if __name__=='__main__':main()
