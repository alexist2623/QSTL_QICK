"""Own the desktop Qt lifecycle; never open board connections."""
from pathlib import Path
import sys
from qick.sim import QickSim
import pytest
from run_case import EVIDENCE

if __name__=='__main__':
    raise SystemExit(pytest.main([str(Path(__file__).with_name('test_coverage.py')),
        '-q','-p','no:cacheprovider','--junitxml',str(EVIDENCE/'software_detailed.xml')]))
