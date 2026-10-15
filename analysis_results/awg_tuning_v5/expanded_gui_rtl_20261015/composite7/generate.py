"""Verification-only adapter: fresh production GUI input to candidate v5 RTL."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
OLD = ROOT / 'analysis_results/awg_tuning_v5/composite_t2_fix/rtl'
V5 = ROOT / 'analysis_results/awg_tuning_v5/software_followup/gui_rtl'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    source = OLD / 'prepare.py'
    text = source.read_text()
    text = text.replace('New GUI host coordinates -> real v4 RTL inputs',
                        'Fresh current GUI host coordinates -> real candidate v5 RTL inputs')
    text = text.replace("    import gui_rtl_extension\n",
        f"    sys.path.insert(0, {str(V5)!r})\n    import extension_v5 as gui_rtl_extension\n")
    anchor = '    gui_rtl_extension.configure(cfg)\n'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + "    (BUILD / 'candidate_soccfg.json').write_text(json.dumps(cfg._cfg, indent=2))\n")
    anchor = "        (template / name).write_text(text)"
    assert text.count(anchor) == 1
    text = text.replace(anchor, """        if name == 'rc_bd.v':
            assert text.count('axis_output_sum_v1 #') == 3
            text = text.replace('axis_output_sum_v1 #', 'axis_output_sum_v2 #')
        elif name == 'sources.prj':
            assert text.count('axis_output_sum_v1/src/axis_output_sum_v1.sv') == 1
            text = text.replace('axis_output_sum_v1/src/axis_output_sum_v1.sv',
                                'axis_output_sum_v2/src/axis_output_sum_v2.sv')
        elif name == 'tb_rc_gui.sv':
            text = gui_rtl_extension.delayed_oracle(text)
        (template / name).write_text(text)""")
    text = text.replace("rtl_version='existing v4'", "rtl_version='candidate v5, axis_output_sum_v2, AWG delay13, native31/31'")
    path = HERE / 'prepare_v5.py'
    path.write_text(text)
    (HERE / 'adapter_provenance.json').write_text(json.dumps(dict(
        original=str(source), original_sha256=sha(source), adapter=str(path), adapter_sha256=sha(path),
        reused_v5_oracle=str(V5/'extension_v5.py'), oracle_sha256=sha(V5/'extension_v5.py'),
        candidate_hwh='F:/Vivado_Output/a5full1/bitstream.hwh',
        candidate_hwh_sha256=sha('F:/Vivado_Output/a5full1/bitstream.hwh'),
        changes=['production HWH metadata v2 native31/31', 'fresh v2 sum elaboration',
                 'independent 13-clock AWG delay oracle; original waveform and sweep parameters unchanged']), indent=2))

if __name__ == '__main__':
    main()
