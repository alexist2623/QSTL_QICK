"""Preserve initial harness failures; retry corrected test setup in new folders."""
import argparse
import sys
from run_case import generate,arguments,EVIDENCE

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',required=True)
    args,extra=p.parse_known_args()
    original,text=generate(args.case)
    if args.case=='compensation_off':
        old='assert program.sequence.rc_compensation is not None'
        assert text.count(old)==1
        text=text.replace(old,'assert program.sequence.rc_compensation is None  # Explicit OFF fixture')
    target=EVIDENCE/f'verify_{args.case}_retry1.py'
    if target.exists():assert target.read_text(encoding='utf8')==text
    else:target.write_text(text,encoding='utf8')
    sys.argv=[str(target)]+arguments(args.case)+['--run-tag','v4virt_20261014_'+args.case+'_retry1']+extra
    exec(compile(text,str(target),'exec'),{'__name__':'__main__','__file__':str(target)})
