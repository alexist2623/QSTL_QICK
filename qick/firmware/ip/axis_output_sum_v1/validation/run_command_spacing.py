"""Read-only production RTL diagnostic; simulation files stay outside Git."""
from pathlib import Path
import hashlib,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
BUILD=Path('F:/Vivado_Output/a4_command_spacing_20261014')
OUT=ROOT/'analysis_results/awg_tuning_v4/command_spacing_20261014'
VIVADO=Path('F:/Xilinx/Vivado/2023.1/bin')

def main():
    assert not BUILD.exists(), 'Preserve previous simulation evidence'
    BUILD.mkdir();OUT.mkdir(parents=True,exist_ok=True)
    src=ROOT/'qick/firmware/ip/axis_tproc64x32_x8_v1/src'
    vhdl=[src/'fifo/bram_simple_dp.vhd',src/'fifo/fifo.vhd',src/'timed_ictrl.vhd']
    sv=[ROOT/'qick/firmware/ip/axis_tmux_v1/src/tmux.sv',HERE/'tb_shared_command_spacing.sv']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in vhdl+sv}
    def run(tool,args):
        result=subprocess.run([str(VIVADO/(tool+'.bat')),*map(str,args)],cwd=BUILD,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        (OUT/(tool+'.log')).write_text(result.stdout,encoding='utf8')
        print(tool,result.returncode,flush=True)
        assert result.returncode==0,result.stdout[-4000:]
        return result.stdout
    run('xvhdl',vhdl)
    run('xvlog',['--sv',*sv])
    run('xelab',['xil_defaultlib.tb_shared_command_spacing','--snapshot','spacing','--debug','off'])
    log=run('xsim',['spacing','--runall'])
    assert 'SHARED_COMMAND_SPACING_PASS' in log and 'Fatal:' not in log
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    result=dict(passed=True,source_hashes=hashes,simulation_build=str(BUILD),
        direct_tmux_words=512,direct_tmux_interval=1,dispatcher_requested_intervals=[1,2,3,4],
        dispatcher_observed_intervals=[3,3,3,4],production_modified=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
