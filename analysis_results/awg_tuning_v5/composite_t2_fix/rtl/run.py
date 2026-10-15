"""Isolated existing-v4 RTL replay and independent T2 RF-window checks."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
STATE = HERE / 'status.json'
VIVADO = Path('F:/Xilinx/Vivado/2023.1/bin')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(case):
    out = Path(case['folder'])
    log = (out / 'run_console.log').read_text(errors='replace')
    assert 'RTL COMPLETE' in log and not re.search(r'Fatal:|ERROR:', log), log[-2000:]
    assert log.count('OUTPUT_SUM_RESULT') == 3
    assert len(re.findall(r'AREA_V3_RESULT.*residual=0', log)) == 3
    expected = json.loads((out / 'expected.json').read_text())['events']
    with (out / 'rtl_events.csv').open() as stream:
        actual = list(csv.DictReader(stream))
    expected.sort(key=lambda e: (e['cycle'], e['port']))
    actual.sort(key=lambda e: (int(e['cycle']), int(e['port'])))
    assert len(expected) == len(actual), (len(expected), len(actual))
    offset = int(actual[0]['cycle']) - expected[0]['cycle']
    for wanted, found in zip(expected, actual):
        assert int(found['port']) == wanted['port'] and int(found['word'], 16) == int(wanted['word'], 16)
        assert int(found['cycle']) - wanted['cycle'] == offset
    rf_checks = []
    for suffix, events in zip((4, 5, 6), case['rf_events']):
        blocks = []
        start = None
        with (out / f'physical_{suffix}.csv').open() as stream:
            for row in csv.DictReader(stream):
                cycle = int(row['cycle'])
                active = bool(int(row['rf'], 16))
                if active and start is None:
                    start = cycle
                if not active and start is not None:
                    blocks.append((start, cycle))
                    start = None
        assert start is None, 'RF remained active at simulation end'
        assert len(blocks) == 2 * len(events), (suffix, blocks)
        for repetition in range(2):
            shot = blocks[repetition * len(events):(repetition + 1) * len(events)]
            origin = shot[0][0] - round(events[0]['delay_us'] * 300)
            for (begin, end), event in zip(shot, events):
                assert end - begin == round(event['duration_us'] * 300), (suffix, event, begin, end)
                assert begin - origin == round(event['delay_us'] * 300), (suffix, event, begin, origin)
        rf_checks.append(dict(suffix=suffix, blocks=blocks,
            width_cycles=[end-start for start, end in blocks],
            expected_events=events, width_errors=0, relative_timing_errors=0))
    result = dict(passed=True, case=case['folder'], tau_us=case['tau_us'], pi_us=case['pi_us'],
        command_count=len(actual), command_value_mismatches=0, command_timing_mismatches=0,
        command_origin_offset_cycles=offset, rf_checks=rf_checks,
        sum_oracle='all three stages, every lane, zero mismatches',
        area_checks=re.findall(r'AREA_V3_RESULT[^\n]+', log),
        evidence_hashes={str(path): sha(path) for path in out.iterdir() if path.is_file()})
    (out / 'result.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    prepared = json.loads((HERE / 'prepared.json').read_text())
    build = Path(prepared['build'])
    sim = build / 'sim'
    state = dict(complete=False, stage='compile', build=str(build), cases=[])
    if STATE.exists():
        raise RuntimeError('Existing execution evidence; do not duplicate/retry automatically')
    def save():
        state['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        STATE.write_text(json.dumps(state, indent=2))
    def run(tool, args, log):
        with log.open('w') as stream:
            result = subprocess.run([str(VIVADO / (tool + '.bat')), *args], cwd=sim,
                                    stdout=stream, stderr=subprocess.STDOUT)
        assert result.returncode == 0, (tool, result.returncode, str(log))
    try:
        save()
        run('xvlog', ['--relax', '-prj', str(build / 'template/sources.prj')], build / 'compile_console.log')
        state['stage'] = 'elaborate'
        save()
        libraries = [arg for lib in prepared['libraries'] for arg in ('-L', lib)]
        run('xelab', ['--O2', '--debug', 'off', '--relax', '--mt', '4', *libraries,
                     '--snapshot', 't2_gui', 'xil_defaultlib.tb_rc_gui', 'xil_defaultlib.glbl'],
            build / 'elaborate_console.log')
        for case in prepared['cases']:
            state['stage'] = 'simulate'
            state['active_case'] = case['folder']
            save()
            out = Path(case['folder'])
            options = out / 'options.txt'
            options.write_text('\n'.join(['t2_gui', '-runall', '-testplusarg "CASE=' + out.as_posix() + '"',
                '-testplusarg "OUT=' + out.as_posix() + '"', '-testplusarg "CYCLES=' + str(case['cycles']) + '"',
                '-log "' + (out / 'xsim.log').as_posix() + '"']))
            run('xsim', ['-f', str(options)], out / 'run_console.log')
            result = check(case)
            state['cases'].append(result)
            print(f"PASS tau={case['tau_us']} us pi={case['pi_us']} us, three summed pairs, 2 repeats", flush=True)
            save()
        state['complete'] = True
        state['stage'] = 'passed'
        state['helper_sha256'] = sha(__file__)
        save()
    except BaseException as exc:
        state['stage'] = 'failed'
        state['error'] = repr(exc)
        save()
        raise


if __name__ == '__main__':
    main()
