"""Source paths for desktop tests; no instrument or network initialization."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for relative in ('qick_lib', 'test/qick_lib/qick', 'test/qick_lib/qick/sim',
                 'tools/mains_notch_analysis',
                 'firmware/ip/axis_output_sum_v1/validation/virtual_gate'):
    sys.path.insert(0, str(ROOT / relative))
