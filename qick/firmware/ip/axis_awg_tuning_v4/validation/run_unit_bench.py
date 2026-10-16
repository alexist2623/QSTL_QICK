"""Reproducible xsim runner for v4 common-latency/arithmetic/production testbenches."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--build', required=True, type=Path)
parser.add_argument('--bench', choices=('tb_dc_area', 'tb_dc_boundaries', 'tb_width_awg', 'tb_dc_faults', 'tb_set_saturation', 'tb_timing_tail', 'tb_common_latency', 'tb_control_alignment'), required=True)
parser.add_argument('--vivado', default=Path('F:/Xilinx/Vivado/2023.1'), type=Path)
parser.add_argument('--width', type=int, choices=(48,), default=48,
                    help='Run only the selected production width; preserve original benches.')
args = parser.parse_args()
args.build.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
sources = sorted((root/'src').glob('*.sv'))
sources += [root/'validation/awg_v4_raw_checker.sv',
            root/'validation'/f'{args.bench}.sv', args.vivado/'data/verilog/src/glbl.v']
if args.bench == 'tb_timing_tail':
    sources.append(root.parent/'axis_square_pulse_v1/src/square_rc_precomp.sv')
if args.width == 48 and args.bench in ('tb_dc_boundaries', 'tb_width_awg'):
    original = root/'validation'/f'{args.bench}.sv'
    text = original.read_text()
    if args.bench == 'tb_dc_boundaries':
        text = text[:text.index('module tb_dc_boundaries;')] + '''module tb_dc_boundaries;
    wire done48;
    dc_boundary_case #(.WIDTH(48)) w48(done48);
    initial begin wait(done48); $finish; end
    initial begin #100000; $fatal(1,"watchdog"); end
endmodule
'''
    else:
        for width in (32, 64):
            old = f'    width_awg_case #(.WIDTH({width})) w{width}(clk,rstn,command_valid,rc_enabled,command,done{width});'
            assert text.count(old) == 1
            text = text.replace(old, f'    assign done{width}=done48; // One selected 48-bit DUT only.')
    selected = args.build/f'{args.bench}_selected48.sv'
    selected.write_text(text)
    sources[sources.index(original)] = selected
hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
(args.build/'sources.json').write_text(json.dumps(hashes, indent=2))
commands = [
    ('xvlog', ['-sv', *map(str, sources)]),
    ('xelab', ['--relax', '--timescale', '1ns/1ps', '-L', 'unisims_ver', args.bench, 'glbl', '-s', 'unit']),
    ('xsim', ['unit', '-runall']),
]
with (args.build/'run.log').open('w') as log:
    for stage, options in commands:
        r = subprocess.run([str(args.vivado/'bin'/f'{stage}.bat'), *options], cwd=args.build,
                           stdout=log, stderr=subprocess.STDOUT)
        log.flush()
        if r.returncode:
            print(f'{stage} failed: {args.build}/run.log')
            raise SystemExit(r.returncode)
text = (args.build/'run.log').read_text(errors='replace')
passed = 'PASS' in text and 'Fatal:' not in text and 'ERROR:' not in text
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in hashes.items()), 'Source changed during validation'
(args.build/'result.json').write_text(json.dumps({'bench': args.bench, 'passed': passed,
                                               'selected_width': args.width, 'sources': hashes}, indent=2))
print('\n'.join(line for line in text.splitlines() if any(word in line for word in ('PASS', 'Fatal:', 'ERROR:', 'RESULT'))))
raise SystemExit(0 if passed else 1)
