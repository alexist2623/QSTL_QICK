"""Create fresh validation-only small-case adapters; preserve prior evidence."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/GIT_Workspace/QSTL_QICK')
MATRIX = ROOT / 'analysis_results/awg_tuning_v5/expanded_gui_rtl_20261015/matrix21'
FINE = ROOT / 'analysis_results/awg_tuning_v5/software_followup/gui_rtl/fine'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    records = []
    def save(src, dest, text):
        assert not dest.exists(), dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding='utf-8')
        records.append(dict(source=str(src), source_sha256=sha(src), adapter=str(dest), adapter_sha256=sha(dest)))
    for name in ('support.py', 'extension_v5.py', 'square_oracle.svh'):
        save(MATRIX/name, HERE/name, (MATRIX/name).read_text())
    src = MATRIX/'run_case.py'
    text = src.read_text().replace('F:/Vivado_Output/a5matrix1', 'F:/Vivado_Output/a5simple1').replace('v5matrix_20261015_', 'v5simple_20261015_')
    save(src, HERE/'run_case.py', text)
    src = MATRIX/'cases.py'
    text = src.read_text()
    text += "\n# Fresh representative positive cases: RF +100ns is part of the request.\nCASES = {name: dict(CASES[name], count=2, delay=.1) for name in ('hold_fixed_time','ramp_fixed_time','rf_frequency')}\n"
    save(src, HERE/'cases.py', text)
    for name in ('prepare.py', 'harness.py', 'run.py'):
        src = FINE/name
        text = src.read_text()
        if name == 'prepare.py':
            text = text.replace('F:/Vivado_Output/a5post_fine_rtl1', 'F:/Vivado_Output/a5simple_fine1')
            before = '    try:\n        for name, active, first, last, count, frequencies, gain in fixtures:'
            assert before in text
            text = text.replace(before, "    fixtures = [('fine_duration94_97', 0, 94, 97, 4, (0.,), 4000)]\n" + before)
            before = '            args = window._experiment_run_arguments(require_readout=False, require_run_config=False)'
            ui = '''            # Commit duration sweep values again through actual Qt controls.
            from PyQt5 import QtTest
            panel = window._rf_ports_panel._panels[0]
            panel.set_time_unit('us')
            table = panel.duration_parameter_table
            for column, value in ((3, first/4800.), (4, last/4800.), (5, count)):
                widget = table.cellWidget(0, column)
                widget.setFocus(); widget.selectAll()
                QtTest.QTest.keyClicks(widget, format(value, '.12g'))
                QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Tab)
            table.cellWidget(0, 2).setChecked(True)
            panel.fine_duration.setChecked(True)
            app.processEvents()
            (output/'gui_committed.json').write_text(json.dumps(window._settings_to_dict(), indent=2))
            assert panel.grab().save(str(output/'fine_duration_input.png'))
'''
            assert before in text
            text = text.replace(before, ui + before)
            before = '                for e1, e2 in zip(wanted.pulse_events, found.pulse_events):'
            text = text.replace(before, "                for key in ('gen_ch','segment_name','delay_us','gain','phase_degrees','frequency_mhz','fine_duration','require_within_segment'):\n                    assert getattr(wanted,key)==getattr(found,key), (key,getattr(wanted,key),getattr(found,key))\n" + before)
            before = "                    assert round(e1.duration_us*4800.) == round(e2.duration_us*4800.), (e1,e2)"
            text = text.replace(before, before + "\n                    assert (e1.frequency_mhz,e1.gain,e1.phase_degrees)==(e2.frequency_mhz,e2.gain,e2.phase_degrees)")
            before = '            program.compile()'
            text = text.replace(before, before + "\n            (output/'configured_soccfg.json').write_text(json.dumps(cfg._cfg, indent=2))")
            before = '    app = QtWidgets.QApplication([])'
            text = text.replace(before, "    sources.update({str(p):sha(p) for p in (HERE/'prepare.py',HERE/'harness.py',HERE/'run.py',Path(gui_rtl_extension.__file__),gui_rtl_extension.HWH,ROOT/'qick/firmware/ip/axis_output_sum_v2/src/axis_output_sum_v2.sv',ROOT/'qick/firmware/projects/qstl_gui_rtl_sim/soccfg.json')})\n" + before)
        if name == 'harness.py':
            text = text.replace('from extension_v5 import delayed_oracle', 'from extension_v5 import delayed_oracle, extra_monitor')
            text = text.replace('    top=delayed_oracle(top)', '    top=extra_monitor(delayed_oracle(top))')
        if name == 'run.py':
            before = "    (out/'result.json').write_text(json.dumps(result,indent=2))"
            assert before in text
            text = text.replace(before, "    from extension_v5 import physical_oracle, physical_rows\n    result['final_dac_lane_checks'] = {str(s): physical_oracle(physical_rows(out,s),s) for s in (4,5,6)}\n" + before)
        save(src, HERE/'fine'/name, text)
    (HERE/'adapter_provenance.json').write_text(json.dumps(records, indent=2))

if __name__ == '__main__': main()
