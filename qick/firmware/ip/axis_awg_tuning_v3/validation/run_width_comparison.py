"""Run actual RTL at 32/48/64 bits with identical waveform and RC model.

Use a new build directory: existing evidence is never silently overwritten.
Each run stores its tool log and streaming point CSV, and status.json records
the actual subprocess stage/exit code. No full-waveform dump is generated.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--vivado', type=Path, default=Path('F:/Xilinx/Vivado/2023.1'))
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--width', type=int, choices=(32, 48, 64),
                        help='Validate one selected width without running other widths.')
    args = parser.parse_args()
    args.build.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    sources = [root/'src/v3_awg_dc_area.sv', root/'src/v3_awg_rc_precomp.sv',
               root/'validation/tb_dc_width.sv']
    (args.build/'source_hashes.json').write_text(json.dumps(
        {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2))
    statuses = {}
    lock = threading.Lock()

    def status(key, **values):
        with lock:
            statuses.setdefault(key, {}).update(values)
            (args.build/'status.json').write_text(json.dumps(statuses, indent=2))

    def run(width):
        key = 'smoke' if args.smoke else str(width)
        top = 'tb_width_smoke' if args.smoke else f'tb_width{width}'
        folder = args.build/key
        folder.mkdir()
        commands = [
            ('xvlog', ['-sv', *map(str, sources)]),
            ('xelab', ['--relax', '--timescale', '1ns/1ps', top, '-s', top]),
            ('xsim', [top, '-runall']),
        ]
        start = time.time()
        with (folder/'run.log').open('w') as log:
            for stage, options in commands:
                status(key, width=width, stage=stage, state='running')
                result = subprocess.run([str(args.vivado/'bin'/f'{stage}.bat'), *options],
                                        cwd=folder, stdout=log, stderr=subprocess.STDOUT)
                log.flush()
                if result.returncode:
                    status(key, state='failed', exit_code=result.returncode, elapsed_s=time.time()-start)
                    return False
        content = (folder/'run.log').read_text(errors='replace')
        passed = f'PASS WIDTH {width}:' in content and 'Fatal:' not in content
        status(key, state='passed' if passed else 'failed', exit_code=0 if passed else 1,
               elapsed_s=time.time()-start)
        return passed

    if args.width is not None or args.smoke:
        ok = [run(48 if args.smoke else args.width)]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            ok = list(pool.map(run, [32, 48, 64]))
    print(json.dumps(statuses, indent=2))
    raise SystemExit(0 if all(ok) else 1)


if __name__ == '__main__':
    main()
