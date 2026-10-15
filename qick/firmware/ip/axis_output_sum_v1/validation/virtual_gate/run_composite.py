"""A concrete point of the actual GUI's N/tau sweep, or a named RF axis."""
import argparse
import hashlib
import json
import sys
from cases import CASES
from run_case import EVIDENCE,generate,arguments

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=2);p.add_argument('--tau',type=float,default=.2)
    p.add_argument('--named',choices=('frequency','duration'))
    args,extra=p.parse_known_args()
    name='cpmg_'+('named_'+args.named if args.named else f'n{args.n}_tau{round(args.tau*1000)}ns')
    CASES[name]=dict(sweep='hold_duration',n=args.n,tau=args.tau,named=args.named)
    base,text=generate(name)
    text=text.replace('from support import configure_inputs, build_from_widgets, matrix_oracle, extra_monitors, finish',
        'from composite_support import configure_inputs, build_from_widgets, matrix_oracle, extra_monitors, finish, analyze_rf, analyze_sum')
    start=text.index("    if args.sweep_case:\n        with (out/'rf_samples.csv').open()")
    end=text.index("    summary['validation_status']='passed'",start)
    text=text[:start]+"    summary['rf_measurements']=analyze_rf(out,model,offset,shots,args,program)\n"+text[end:]
    old="summary['output_sum']=sum_validation.analyze(out,result,model,offset,shots,args.sum_rf_delay_us)"
    assert text.count(old)==1
    text=text.replace(old,"summary['output_sum']=analyze_sum(out,result,model,offset,shots,args,program)")
    target=EVIDENCE/('verify_extended_'+name+'.py')
    if target.exists():assert target.read_text(encoding='utf8')==text
    else:target.write_text(text,encoding='utf8')
    sys.argv=[str(target)]+arguments(name)+extra
    exec(compile(text,str(target),'exec'),{'__name__':'__main__','__file__':str(target)})
