"""Retry reviewed desktop test-environment failures without changing production sources."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

STEMS = ('test_iq64_format', 'test_qick_qcodes_experiment', 'test_qick_square_wave',
         'test_sparameter_phase_storage', 'test_trigger_output_panel')
OLD_MESSAGE = 'with pytest.raises(ValueError, match="axis_awg_tuning_v1"):'
NEW_MESSAGE = 'with pytest.raises(ValueError, match="Select an AWG tuning DAC generator"):'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(module, basetemp):
    # Existing QICK desktop simulation bootstrap, also used by the normal sweep tests.
    from qick.sim import QickSim  # noqa: F401
    import pytest
    app = None
    if module.stem == 'test_sparameter_phase_storage':
        from PyQt5 import QtCore, QtWidgets, sip
        assert QtWidgets.QApplication.instance() is None
        app = QtWidgets.QApplication([])
        app.setQuitOnLastWindowClosed(False)
    code = pytest.main([str(module), '-q', '-p', 'no:cacheprovider', '--basetemp', str(basetemp)])
    if app is not None:
        widgets = app.topLevelWidgets()
        for widget in widgets:
            widget.close()
            widget.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        app.processEvents()
        QtCore.QTimer.singleShot(0, app.quit)
        app.exec_()
        widgets.clear()
        if 'widget' in locals():
            del widget
        gc.collect()
        sip.delete(app)
        print('QT_EXPLICIT_TEARDOWN_COMPLETE', flush=True)
    return int(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--basetemp', type=Path)
    a = parser.parse_args()
    if a.worker:
        raise SystemExit(worker(a.worker, a.basetemp))
    state = json.loads((a.build/'status.json').read_text())
    results = {}
    reviewed = a.build/'reviewed_test_fixtures'
    reviewed.mkdir(exist_ok=False)
    for stem in STEMS:
        key = 'gui_DCWaveformGeneratorGUI_'+stem
        assert state['stages'][key]['state'] == 'failed'
        source = a.gui/'DCWaveformGeneratorGUI'/(stem+'.py')
        module = source
        reason = 'Use project-pinned plottr 0.15.0 from isolated validation dependencies.'
        if stem == 'test_qick_square_wave':
            text = source.read_text(encoding='utf-8')
            assert text.count(OLD_MESSAGE) == 1
            module = reviewed/source.name
            module.write_text(text.replace(OLD_MESSAGE, NEW_MESSAGE), encoding='utf-8')
            reason = ('One stale error-message regex in a build-local test copy. Production message has '
                      'been committed since 3e78e0cd; source test and production files remain unchanged.')
        elif stem == 'test_sparameter_phase_storage':
            reason = 'Own QApplication through pytest and explicitly destroy widgets/application before Python shutdown.'
        elif stem == 'test_trigger_output_panel':
            reason = 'Initialize existing qick.sim desktop support before importing the tProcessor behavior model.'
        command = [sys.executable, '-X', 'utf8', '-X', 'faulthandler', str(Path(__file__).resolve()),
                   '--build', str(a.build), '--gui', str(a.gui), '--worker', str(module),
                   '--basetemp', str(a.build/'pytest_temp'/(key+'_desktop_retry'))]
        log = a.build/(key+'.desktop_retry.log')
        item = dict(state='running', command=command, log=str(log), original_module=str(source),
                    original_sha256=digest(source), executed_module=str(module), executed_sha256=digest(module),
                    reason=reason, started=time.time(), harness_sha256=digest(Path(__file__)),
                    pythonpath=os.environ.get('PYTHONPATH', ''))
        results[key] = item
        (a.build/'desktop_retries.json').write_text(json.dumps(results, indent=2))
        with log.open('w', encoding='utf-8') as stream:
            code = subprocess.run(command, cwd=a.gui, stdout=stream, stderr=subprocess.STDOUT).returncode
        item.update(state='passed' if code == 0 else 'failed', exit_code=code,
                    elapsed_s=time.time()-item['started'])
        assert digest(source) == item['original_sha256']
        (a.build/'desktop_retries.json').write_text(json.dumps(results, indent=2))
        print(f'{key}: exit {code}', flush=True)
    raise SystemExit(0 if all(r['exit_code']==0 for r in results.values()) else 1)


if __name__ == '__main__':
    main()
