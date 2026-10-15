"""Create validation-only copies. Never edit original tests or production RTL."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ORIGINAL=ROOT/'qick/firmware/ip/rc_precomp_validation/verify_gui_rtl.py'
EXACT=ROOT/'analysis_results/awg_tuning_v4/full_regression_20261014'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    provenance=[]
    for name,source in [('general',ORIGINAL),('hold1',EXACT/'verify_hold1_generated.py'),('hold2',EXACT/'verify_hold2_generated.py')]:
        text=source.read_text()
        text=text.replace("HERE=Path(__file__).resolve().parent",f"HERE=Path({str(ORIGINAL.parent)!r})")
        text=text.replace('import gui_rtl_extension as sum_validation','import extension_v5 as sum_validation')
        text=text.replace("rtl.append(HERE.parent/'axis_output_sum_v1/src/axis_output_sum_v1.sv')","rtl.append(HERE.parent/'axis_output_sum_v2/src/axis_output_sum_v2.sv')")
        # Physical traces and assertions are version-aware in the local adapter.
        text=text.replace('from hold10us_support import extra_monitor','from extension_v5 import extra_monitor')
        text=text.replace('from hold10us_support import analyze','from extension_v5 import analyze_hold')
        text=text.replace('summary[\'output_sum\']=analyze(out,result,model,offset,shots,','summary[\'output_sum\']=analyze_hold(out,result,model,offset,shots,')
        if name.startswith('hold'):
            text=text.replace('delay_us=0.,duration_us=10.','delay_us=args.sum_rf_delay_us,duration_us=10.-args.sum_rf_delay_us')
            text=text.replace('rf_duration_start=rf_duration_stop=10.','rf_duration_start=rf_duration_stop=10.-args.sum_rf_delay_us')
            text=text.replace(')),3000.)',')),round((10.-args.sum_rf_delay_us)*300))')
        else:
            anchor='top=sum_validation.monitor(top, shots, program, out, args)'
            assert anchor in text
            text=text.replace(anchor,anchor+'\n        top=sum_validation.extra_monitor(top)')
        path=HERE/f'verify_{name}.py'
        path.write_text(text)
        provenance.append(dict(source=str(source),source_sha256=sha(source),adapter=str(path),adapter_sha256=sha(path)))
    (HERE/'adapter_provenance.json').write_text(json.dumps(provenance,indent=2))

if __name__=='__main__':main()
