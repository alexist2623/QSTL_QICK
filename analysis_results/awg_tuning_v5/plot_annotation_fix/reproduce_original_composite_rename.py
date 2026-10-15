"""Check RF rename callback against the original, unmodified plot widgets."""

from pathlib import Path
import importlib.util
import sys

from qick.sim import QickSim  # Desktop bootstrap only; no board connection.

backup = Path(__file__).with_name("dc_waveform_widgets.before.py")
spec = importlib.util.spec_from_file_location("dc_waveform_widgets", backup)
module = importlib.util.module_from_spec(spec)
sys.modules["dc_waveform_widgets"] = module
spec.loader.exec_module(module)
print("ORIGINAL_WIDGET_MODULE:", module.__file__, flush=True)

import run_tests
print("OWNED_QT_RUNNER_IMPORTED", flush=True)

if __name__ == "__main__":
    raise SystemExit(run_tests.main())
