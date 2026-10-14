"""Prepare isolated v4 snapshots serially, then run the approved RTL cases."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
GUI=ROOT.parent/'PulseGenerator'
OUT=ROOT/'analysis_results/awg_tuning_v4'
CASES={
 'hold_fixed_time':dict(sweep='hold_duration',count=10,mode='fixed_time',policy='after_readout',delay=0.),
 'hold_fixed_voltage_offset':dict(sweep='hold_duration',count=10,mode='fixed_voltage',policy='overlap_readout',delay=.1),
 'rf_duration_extend':dict(sweep='rf_duration',count=2,mode='fixed_voltage',policy='overlap_readout',delay=0.),
 'rf_duration_fixed':dict(sweep='rf_duration_fixed',count=2,mode='fixed_time',policy='after_readout',delay=.1),
 'rc_only':dict(sweep='hold_duration',count=4,mode='fixed_time',policy='after_readout',delay=0.,rc_only=True),
}


def arguments(build,name,cfg,tag):
    return [sys.executable,'-X','utf8',str(ROOT/'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'),
        '--build',str(build),'--gui',str(GUI),'--vivado','F:/Xilinx/Vivado/2023.1/bin',
        '--awg-v3','--output-sum','--repeat-reset','--isolated-run','--verify-gui-widgets',
        '--sweep-case',cfg['sweep'],'--sweep-count',str(cfg['count']),
        '--dc-mode',cfg['mode'],'--dc-readout-policy',cfg['policy'],'--stored-fir-samples','4',
        '--sum-rf-delay-us',str(cfg['delay']),'--run-tag',tag+'_'+name,
        *(['--rc-only'] if cfg.get('rc_only') else [])]


def folder(build,name,cfg,tag):
    value='rc_precomp_repeat_reset'+('_rc_only' if cfg.get('rc_only') else '')+'_'+cfg['sweep']
    if cfg['count']!=10:value+=f"_{cfg['count']}x{cfg['count']}"
    return build/(value+'_'+tag+'_'+name+'_output_sum_'+cfg['policy']+'_awg_v3')


def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True)
    p.add_argument('--tag',default='v4_final1');p.add_argument('--workers',type=int,default=3)
    p.add_argument('--prepare-only',action='store_true');p.add_argument('--reuse',action='store_true')
    a=p.parse_args();OUT.mkdir(exist_ok=True)
    status_path=OUT/(a.tag+'_status.json')
    if status_path.exists() and not a.reuse:raise RuntimeError('Existing batch: use a new tag')
    state={'complete':False,'tag':a.tag,'started_utc':datetime.now(timezone.utc).isoformat(),'cases':{}}
    def save():status_path.write_text(json.dumps(state,indent=2))
    def execute(name,cfg,prepare):
        destination=folder(a.build,name,cfg,a.tag);destination.mkdir(exist_ok=True)
        log=destination/('prepare_driver.log' if prepare else 'run_driver.log')
        with log.open('w',encoding='utf8') as stream:
            code=subprocess.call(arguments(a.build,name,cfg,a.tag)+(['--prepare-only'] if prepare else ['--reuse-snapshot']),
                                 cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        return code
    for name,cfg in CASES.items():
        dest=folder(a.build,name,cfg,a.tag)
        state['cases'][name]=dict(state='preparing',folder=str(dest),points=cfg['count']**2)
        save()
        code=0 if a.reuse else execute(name,cfg,True)
        if code:
            state['cases'][name].update(state='failed_prepare',exit_code=code);save();raise SystemExit(code)
        state['cases'][name]['state']='prepared';save()
    if a.prepare_only:return
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures={pool.submit(execute,n,c,False):n for n,c in CASES.items()}
        for n in CASES:state['cases'][n]['state']='running_or_queued'
        save()
        for future in as_completed(futures):
            name=futures[future];code=future.result()
            state['cases'][name].update(state='passed' if code==0 else 'failed',exit_code=code)
            save()
    state['complete']=all(c['state']=='passed' for c in state['cases'].values());save()
    if not state['complete']:raise SystemExit(1)


if __name__=='__main__':main()
