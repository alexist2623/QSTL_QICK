"""Explicit both-disabled checks, retaining three initialization reset commands."""
import sys
from run_case import generate,arguments,EVIDENCE

if __name__=='__main__':
    _original,text=generate('compensation_off')
    for old,new in (
        ('assert program.sequence.rc_compensation is not None','assert program.sequence.rc_compensation is None'),
        ("assert len(rc_resets)==len(awg_channels)*(shots+1), 'Missing per-shot RC reset'",
         "assert len(rc_resets)==len(awg_channels), 'OFF must only have initialization resets'"),
        ('rc_compensation=vars(program.sequence.rc_compensation)','rc_compensation=None'),
    ):
        assert text.count(old)==1; text=text.replace(old,new)
    target=EVIDENCE/'verify_compensation_off_retry2.py'
    if target.exists():assert target.read_text(encoding='utf8')==text
    else:target.write_text(text,encoding='utf8')
    sys.argv=[str(target)]+arguments('compensation_off')+['--run-tag','v4virt_20261014_compensation_off_retry2']+sys.argv[1:]
    exec(compile(text,str(target),'exec'),{'__name__':'__main__','__file__':str(target)})
