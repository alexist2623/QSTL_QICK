"""Compare implementation cost only after completed 32/48/64-bit RTL evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--comparison', required=True, type=Path)
parser.add_argument('--build', required=True, type=Path)
parser.add_argument('--widths', nargs='+', type=int, choices=(32, 48, 64), default=[48])
parser.add_argument('--vivado', type=Path, default=Path('F:/Xilinx/Vivado/2023.1'))
args = parser.parse_args()
comparison = json.loads(args.comparison.read_text())
if not comparison['complete'] or not comparison['identical_48_64_results']:
    raise SystemExit('Completed and matching 48/64-bit RTL results are required first')
for w in ('48', '64'):
    result = comparison['widths'][w]
    if result['overflow_points'] or result['max_residual_effective_code_samples'] or result['max_rc_error_mv'] > 800/8192:
        raise SystemExit(f'{w}-bit comparison failed; do not synthesize')
args.build.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
source = root/'src/v3_awg_dc_area.sv'
(args.build/'source_snapshot.sv').write_bytes(source.read_bytes())
status = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'widths': {}}
def save():
    (args.build/'status.json').write_text(json.dumps(status, indent=2))
for width in args.widths:
    start = time.time()
    status['widths'][str(width)] = {'state': 'running'}
    save()
    print(f'Starting {width}-bit arithmetic-engine OOC comparison', flush=True)
    # Tool working directory is a short ASCII path. Each width has independent
    # logs/checkpoints; no published firmware or current project is overwritten.
    with (args.build/f'width_{width}.log').open('w') as log:
        result = subprocess.run([
            str(args.vivado/'bin/vivado.bat'), '-mode', 'batch', '-notrace', '-nojournal', '-nolog',
            '-source', str(root/'validation/synth_area_width.tcl'),
            '-tclargs', str(width), str(args.build/str(width)),
        ], cwd=args.build, stdout=log, stderr=subprocess.STDOUT)
    path = args.build/str(width)/'result.txt'
    entry = status['widths'][str(width)]
    entry.update(exit_code=result.returncode, elapsed_s=time.time()-start)
    if result.returncode or not path.exists():
        entry['state'] = 'tool_failed'; save()
        raise SystemExit(f'{width}-bit OOC failed: {args.build}/width_{width}.log')
    values = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
    entry.update(values)
    entry['state'] = 'timing_met' if float(values['wns_ns']) >= 0 and float(values['whs_ns']) >= 0 else 'timing_failed'
    # OOC has virtual input ports with zero external delay and no routed net.
    # Preserve these boundary violations, but separately record the measured
    # internal register paths. Only the complete FPGA proves interface timing.
    if entry['state'] == 'timing_failed' and all(float(values[k]) >= 0 for k in ('internal_wns_ns', 'internal_whs_ns')):
        entry['state'] = 'internal_timing_met_boundary_pending'
    save()
    print(json.dumps(entry), flush=True)
print('OOC comparison finished. Full-design timing closure is still required.', flush=True)
