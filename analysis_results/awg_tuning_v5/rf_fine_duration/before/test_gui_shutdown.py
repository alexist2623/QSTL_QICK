"""Check native process exit, not only Python assertions before teardown."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('restore_count', [0, 1, 5])
def test_application_shutdown_after_settings_restore(restore_count, tmp_path):
    script = '''
from pathlib import Path
from PyQt5 import QtCore
import DCWaveform_Generator as gui
original_show = gui.MainWindow.show
def show(window):
    original_show(window)
    path = Path(SETTINGS)
    window._save_settings_json(path)
    for _ in range(COUNT):
        window._load_settings_json(path)
    QtCore.QTimer.singleShot(30, window.close)
gui.MainWindow.show = show
assert gui.main() == 0
print('GUI_SHUTDOWN_OK', flush=True)
'''.replace('SETTINGS', repr(str(tmp_path/'settings.json'))).replace('COUNT', str(restore_count))
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    run = subprocess.run([sys.executable, '-u', '-X', 'faulthandler', '-c', script],
        cwd=Path(__file__).parent, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, (run.returncode, run.stdout, run.stderr)
    assert 'GUI_SHUTDOWN_OK' in run.stdout
