"""Original requests first, authorized explicit-offset variants second; one xsim."""
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from cases import CASES,case
from run_case import generate,arguments,ROOT,EVIDENCE,SIM,folder

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def initialize():
    source=Path('F:/Vivado_Output/a3sim1');SIM.mkdir(exist_ok=False)
    sub=Path('qstl_gui_rtl_sim.sim/sim_1/behav/xsim');src=source/sub;dst=SIM/sub
    (dst/'xsim.dir').mkdir(parents=True)
    shutil.copytree(src/'xsim.dir/xil_defaultlib',dst/'xsim.dir/xil_defaultlib')
    for n in ('xsim.ini','elaborate.bat'):shutil.copy2(src/n,dst/n)
    name=Path('qstl_gui_rtl_sim.gen/sources_1/bd/sim_bd/sim/sim_bd.v');(SIM/name).parent.mkdir(parents=True)
    shutil.copy2(source/name,SIM/name);shutil.copy2(source/'wrapper_path.txt',SIM/'wrapper_path.txt')

def main():
    status=EVIDENCE/'status.json';assert not status.exists(),'Do not duplicate controller'
    for name in CASES:generate(name)
    initialize()
    state=dict(complete=False,execution_complete=False,pid=os.getpid(),started_utc=now(),stage='running',max_xsim=1,cases={},
        source_scope='Current production GUI/driver, actual v5 HWH; validation-only adapters; original input preserved before any explicit offset variant')
    def save():state['updated_utc']=now();status.write_text(json.dumps(state,indent=2))
    def execute(name,kind,argv,phase):
        log=EVIDENCE/f'{name}.{kind}.{phase}.log';assert not log.exists()
        entry=state['cases'][name][kind];entry[phase]=dict(command=argv,log=str(log),started_utc=now());save()
        with log.open('w',encoding='utf-8') as stream:
            p=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);entry[phase]['pid']=p.pid;save();code=p.wait()
        entry[phase].update(exit_code=code,finished_utc=now());save();print(name,kind,phase,'exit',code,flush=True)
        return code
    save()
    for name in CASES:
        original=folder(name);argv=[sys.executable,'-X','utf8','-u',str(EVIDENCE/'run_case.py'),'--case',name]
        entry=state['cases'][name]=dict(original=dict(folder=str(original),rf_delay_us=case(name)['delay']),state='original_prepare');save()
        code=execute(name,'original',argv+['--prepare-only'],'prepare')
        selected='original';target=original;selected_argv=argv
        if code:
            rejection_path=original/'gui_rejection.json'
            rejection=json.loads(rejection_path.read_text()) if rejection_path.exists() else {}
            entry['original']['rejection']=rejection;entry['original']['state']='rejected' if rejection else 'failed_prepare'
            if 'shared tProcessor port' not in rejection.get('error','') or case(name)['delay']!=0:
                entry['state']='failed_prepare';save();continue
            selected='rf100ns';tag='v5matrix_20261015_'+name+'_rf100ns'
            target=original.with_name(original.name.replace(name+'_output_sum',name+'_rf100ns_output_sum'))
            selected_argv=argv+['--run-tag',tag,'--sum-rf-delay-us','.1']
            entry[selected]=dict(folder=str(target),rf_delay_us=.1,explicit_fixture_change='Only all three RF base delay_us: 0 -> 0.1 us; production source and guard unchanged.')
            entry['state']='variant_prepare';save()
            code=execute(name,selected,selected_argv+['--prepare-only'],'prepare')
            if code:entry['state']='failed_variant_prepare';save();continue
            # Audit the actual saved GUI settings: only base RF delay may differ.
            before=json.loads((original/'gui_input.json').read_text());after=json.loads((target/'gui_input.json').read_text())
            differences=[]
            for i,(a,b) in enumerate(zip(before['rf_outputs'],after['rf_outputs'])):
                assert a['delay_us']==0 and b['delay_us']==.1,(name,i,a['delay_us'],b['delay_us'])
                differences.append(dict(output=i,path=f'rf_outputs[{i}].delay_us',before=0,after=.1));a['delay_us']=.1
            assert before==after,('Unexpected GUI input change beyond explicitly authorized RF offset',name)
            entry[selected]['input_changes']=differences
        entry['selected']=selected;entry['state']='rtl_running';save()
        code=execute(name,selected,selected_argv+['--reuse-snapshot'],'rtl')
        result_path=target/'result.json';result=json.loads(result_path.read_text()) if result_path.exists() else {}
        entry['state']='passed' if code==0 and result.get('validation_status')=='passed' else 'rtl_failed';save()
    state['execution_complete']=True;state['complete']=all(c['state']=='passed' for c in state['cases'].values()) and len(state['cases'])==21
    state['stage']='passed_variants_separately_classified' if state['complete'] else 'finished_with_failures';state['finished_utc']=now();save()
    return 0 if state['complete'] else 1

if __name__=='__main__':raise SystemExit(main())
