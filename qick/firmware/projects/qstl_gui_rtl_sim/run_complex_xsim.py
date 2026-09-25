"""Compile/run the real two-AWG DUT, or the 78-IP full-DUT cross-check."""
import argparse
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('build',type=Path)
    p.add_argument('--case',default='gui_complex_10x10')
    p.add_argument('--full',action='store_true');p.add_argument('--cycles',type=int)
    p.add_argument('--reuse',action='store_true');p.add_argument('--compile-only',action='store_true')
    a=p.parse_args();run=a.build/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    generated=a.build/'complex_awg';d=HERE/a.case
    variant='full' if a.full else 'focus';top='tb_complex_'+variant;snapshot='complex_'+variant
    dest=d/variant;dest.mkdir(exist_ok=True)
    vivado=Path('C:/Xilinx/Vivado/2023.1/bin')
    def execute(tool,params):
        print(tool,variant,flush=True)
        r=subprocess.run([str(vivado/(tool+'.bat')),*params],cwd=run,
                         stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        (dest/(tool+'_console.log')).write_text(r.stdout)
        if r.returncode or re.search(r'^ERROR:|^Fatal:',r.stdout,re.M):
            print(r.stdout[-8000:]);raise SystemExit(r.returncode or 1)
        return r.stdout
    if not a.reuse:
        files=[] if a.full else [generated/'focus_bd.v',generated/'focus_bd_wrapper.v']
        files.append(generated/(top+'.sv'))
        prj=generated/(top+'.prj')
        prj.write_text(''.join(f'sv xil_defaultlib "{f.as_posix()}"\n' for f in files)+'nosort\n')
        execute('xvlog',['--incr','--relax','-prj',str(prj),'-i',str(generated)])
        libs=list(dict.fromkeys(re.findall(r'-L (\w+)',(run/'elaborate.bat').read_text())))
        execute('xelab',['--incr','--O2','--debug','off','--relax','--mt','4',
                        *[v for lib in libs for v in ('-L',lib)],'--snapshot',snapshot,
                        'xil_defaultlib.'+top,'xil_defaultlib.glbl'])
    if a.compile_only:return
    meta=json.loads((d/'expected.json').read_text());cycles=a.cycles or meta['stop_cycle']
    opts=generated/(snapshot+'_options.txt');tcl=generated/(snapshot+'_run.tcl')
    tcl.write_text('run all\nquit\n')
    options=[snapshot,f'-tclbatch "{tcl.as_posix()}"',f'-log "{(dest/"xsim.log").as_posix()}"']
    options += [f'-testplusarg "{arg}"' for arg in (f'CASE={d.as_posix()}',f'OUT={dest.as_posix()}',
                 f'CYCLES={cycles}',f'REQUIRE_END={int(cycles>=meta["stop_cycle"])}')]
    opts.write_text('\n'.join(options)+'\n')
    checks=dest/'rtl_checks.txt';checks.unlink(missing_ok=True)
    output=execute('xsim',['-f',str(opts)])
    if 'RTL COMPLETE' not in output or not checks.is_file():raise SystemExit('Simulation did not complete')
    print(checks.read_text(),flush=True)


if __name__=='__main__':main()
