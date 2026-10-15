"""Preserve the validated sample-width oracle and adapt only v5 routing/sum."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=ROOT/'analysis_results/awg_tuning_v5/rf_fine_duration/rtl'
DEST=HERE/'fine'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    DEST.mkdir(exist_ok=False)
    provenance=[]
    for name in ('harness.py','prepare.py','run.py'):
        src=OLD/name;text=src.read_text()
        if name=='harness.py':
            text=text.replace('import shutil','import shutil\nimport sys\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]))\nfrom extension_v5 import delayed_oracle',1)
            anchor="        shutil.copy2(BASE / name, template / name)"
            assert anchor in text
            text=text.replace(anchor,anchor+"\n        if name=='rc_bd.v':\n            p=template/name;p.write_text(p.read_text().replace('axis_output_sum_v1 #','axis_output_sum_v2 #'))")
            anchor="    (template / 'tb_rc_gui.sv').write_text(top)"
            text=text.replace(anchor,"    top=delayed_oracle(top)\n"+anchor)
            anchor="    (template / 'sources.prj').write_text(project)"
            text=text.replace(anchor,"    project=project.replace('axis_output_sum_v1/src/axis_output_sum_v1.sv','axis_output_sum_v2/src/axis_output_sum_v2.sv')\n"+anchor)
            text=text.replace('existing v4 BD, SG-v6 vendor DDS, axis_output_sum_v1','unchanged routing, SG-v6 vendor DDS, candidate v5 axis_output_sum_v2')
        elif name=='prepare.py':
            text=text.replace("'F:/Vivado_Output/a5fine_sw/DCWaveformGeneratorGUI'",repr(str(ROOT.parent/'PulseGenerator/DCWaveformGeneratorGUI')))
            text=text.replace("'F:/Vivado_Output/a5fine_rtl1'","'F:/Vivado_Output/a5post_fine_rtl1'")
            text=text.replace('    import gui_rtl_extension','    sys.path.insert(0,str(HERE.parent))\n    import extension_v5 as gui_rtl_extension')
            anchor='    try:\n        for name, active, first, last, count, frequencies, gain in fixtures:'
            assert anchor in text
            text=text.replace(anchor,"    if os.environ.get('QICK_FINE_SCENARIO')=='v5':\n        fixtures=[f for f in fixtures if f[0].startswith(('remainders','short_1_to_31','short_carrier_1_to_31'))]\n"+anchor)
        else:
            text=text.replace("rtl_version='existing v4 SG-v6 plus sum-v1'","rtl_version='existing SG-v6 plus candidate v5 sum-v2'")
        dst=DEST/name;dst.write_text(text)
        provenance.append(dict(source=str(src),source_sha256=sha(src),adapter=str(dst),adapter_sha256=sha(dst)))
    (DEST/'adapter_provenance.json').write_text(json.dumps(provenance,indent=2))

if __name__=='__main__':main()
