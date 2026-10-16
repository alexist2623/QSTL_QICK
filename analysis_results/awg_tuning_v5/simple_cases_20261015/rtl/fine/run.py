"""Explicit isolated actual RTL execution and sample-resolution checks."""
import argparse
from contextlib import contextmanager
import csv
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from harness import SHARED, sha

HERE = Path(__file__).resolve().parent
VIVADO = Path('F:/Xilinx/Vivado/2023.1/bin')
LOADED_HELPER_SHA256 = sha(__file__)


def memory_headroom():
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong),
                    *[(name,ctypes.c_ulonglong) for name in
                      ('total_phys','available_phys','total_commit','available_commit',
                       'total_virtual','available_virtual','extended')]]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    return memory.available_phys/2**30, memory.available_commit/2**30


@contextmanager
def analysis_lock(path):
    if path is None:
        yield
        return
    import msvcrt
    with path.open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0'); stream.flush()
        while True:
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                break
            except OSError:
                time.sleep(.5)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)


def read_samples(path):
    import numpy as np
    cycles, values = [], []
    with path.open() as stream:
        for row in csv.DictReader(stream):
            cycles.append(int(row['cycle']))
            word = int(row['rf'], 16)
            values.extend((((word >> (16*lane))&65535)+32768)%65536-32768 for lane in range(16))
    assert cycles and all(b == a+1 for a,b in zip(cycles,cycles[1:])), 'Trace must contain every fabric word'
    return cycles[0]*16, np.asarray(values, dtype=np.int16)


def check(case):
    if case.get('raw_same_timestamp'):
        from raw_report_v2 import check as check_raw
        return check_raw(case)
    import numpy as np
    out = Path(case['folder'])
    log = (out/'run_console.log').read_text(errors='replace')
    assert 'RTL COMPLETE' in log and not re.search(r'Fatal:|ERROR:', log), log[-4000:]
    assert log.count('OUTPUT_SUM_RESULT') == 3, log[-2000:]
    assert log.count('ENVELOPE_LOAD') == 3
    expected = json.loads((out/'expected.json').read_text())
    with (out/'rtl_events.csv').open() as stream:
        actual = list(csv.DictReader(stream))
    wanted = sorted(expected['events'], key=lambda e:(e['cycle'],e['port']))
    actual.sort(key=lambda e:(int(e['cycle']),int(e['port'])))
    assert len(actual) == len(wanted), (len(actual),len(wanted))
    command_offset = int(actual[0]['cycle'])-wanted[0]['cycle']
    for e,a in zip(wanted,actual):
        assert int(a['port']) == e['port'] and int(a['word'],16) == int(e['word'],16), (e,a)
        assert int(a['cycle'])-e['cycle'] == command_offset, (e,a)
    checks = []
    for channel in (0,2,4):
        bursts = expected['bursts'][str(channel)]
        origin, data = read_samples(out/f'fine_{channel}.csv')
        nonzero = np.flatnonzero(data)
        assert nonzero.size
        # Every fixture starts at freq=0 with a nonzero gain. Consequently the
        # first observed nonzero sample unambiguously establishes pipeline delay.
        assert bursts[0]['frequency_mhz'] == 0. and bursts[0]['gain'] != 0
        sample_offset = int(nonzero[0])+origin-16*bursts[0]['command_cycle']
        # The unchanged shared-TMUX/register-slice/SG-v6 path has a separately
        # established 32-fabric-clock command-to-sum-input latency.
        assert sample_offset-16*command_offset == 32*16, (channel,sample_offset,command_offset)
        mask = np.zeros(data.size, dtype=bool)
        results = []
        carrier_references = {}
        for burst in bursts:
            start = 16*burst['command_cycle']+sample_offset-origin
            stop = start+burst['samples']
            assert 0 <= start < stop <= data.size
            assert not np.any(mask[start:stop]), 'Requested windows overlap'
            mask[start:stop] = True
            values = data[start:stop].astype(float)
            item = dict(**burst, first_sample=start+origin, last_sample_exclusive=stop+origin)
            gain = burst['gain']
            frequency = burst['frequency_register']*4800./2**32
            if burst['frequency_mhz'] == 0.:
                assert np.all(values != 0), (channel,burst,'zero inside active window')
                assert np.max(np.abs(values-gain)) <= 3., (channel,burst,values.min(),values.max())
                item['exact_active_sample_count'] = len(values)
                item['maximum_amplitude_error_codes'] = float(np.max(np.abs(values-gain)))
            else:
                time_us = np.arange(len(values))/4800.
                if case['name'].startswith('short_carrier_1_to_31') and len(values) < 48:
                    # One or two samples cannot determine sinusoid amplitude or
                    # phase. Predict them from the independently measured long
                    # carrier at the same FTW, preserving absolute sample time.
                    reference = carrier_references[burst['frequency_register']]
                    assert reference['samples'] >= 4801 and reference['gain'] == gain
                    theta = (2*np.pi*frequency*(time_us+(start+origin-reference['first_sample'])/4800.)
                             +np.deg2rad(burst['phase_degrees']-reference['phase_degrees']))
                    a,b,dc = reference['coefficients']
                    predicted = a*np.sin(theta)+b*np.cos(theta)+dc
                    errors = predicted-values
                    assert np.max(np.abs(errors)) < 5., (channel,burst,errors)
                    item.update(reference_prediction_max_error_codes=float(np.max(np.abs(errors))),
                                reference_prediction_rms_codes=float(np.sqrt(np.mean(errors**2))),
                                reference_first_sample=reference['first_sample'],
                                reference_samples=reference['samples'],
                                first_sample_code=int(values[0]),last_sample_code=int(values[-1]))
                    results.append(item)
                    continue
                basis = np.column_stack([np.sin(2*np.pi*frequency*time_us),
                                         np.cos(2*np.pi*frequency*time_us),np.ones(len(values))])
                coefficients = np.linalg.lstsq(basis,values,rcond=None)[0]
                amplitude = float(np.hypot(*coefficients[:2]))
                errors = basis@coefficients-values
                rms = float(np.sqrt(np.mean(errors**2)))
                assert abs(amplitude-abs(gain)) < 3., (channel,burst,amplitude)
                assert rms < 1.5 and np.max(np.abs(errors)) < 5., (channel,burst,rms)
                phase = float(np.degrees(np.arctan2(coefficients[1],coefficients[0]))
                              -360*frequency*(start+origin)/4800.)
                item.update(fitted_amplitude=amplitude, rms_codes=rms,
                            max_fit_error_codes=float(np.max(np.abs(errors))),
                            time_referenced_phase_degrees=phase)
                carrier_references.setdefault(burst['frequency_register'],dict(
                    coefficients=coefficients,first_sample=start+origin,samples=len(values),
                    gain=gain,phase_degrees=burst['phase_degrees']))
            results.append(item)
        assert not np.any(data[~mask]), (channel,'nonzero outside exact requested sample windows')
        carrier = [item for item in results if 'time_referenced_phase_degrees' in item]
        for item in carrier:
            reference = next(r for r in carrier if r['frequency_register'] == item['frequency_register'])
            delta = (item['time_referenced_phase_degrees']-reference['time_referenced_phase_degrees']
                     -item['phase_degrees']+reference['phase_degrees']+180.)%360.-180.
            assert abs(delta) < .1, (channel,item,delta)
            item['phase_error_degrees'] = delta
        checks.append(dict(channel=channel, sample_offset=sample_offset,
            pipeline_after_tproc_samples=sample_offset-16*command_offset,
            bursts=results, unexpected_nonzero_samples=0, csv_sha256=sha(out/f'fine_{channel}.csv')))
    result = dict(passed=True,name=case['name'],folder=str(out),checks=checks,
                  commands=len(actual),command_value_errors=0,command_timing_errors=0,
                  command_offset_cycles=command_offset,sum_lane_oracle_errors=0,
                  helper_sha256=LOADED_HELPER_SHA256,rtl_version='existing SG-v6 plus candidate v5 sum-v2',
                  analog_measurement=False,board_access=False)
    from extension_v5 import physical_oracle, physical_rows
    result['final_dac_lane_checks'] = {str(s): physical_oracle(physical_rows(out,s),s) for s in (4,5,6)}
    (out/'result.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepared',type=Path,default=HERE/'prepared.json')
    parser.add_argument('--name',action='append',default=[])
    parser.add_argument('--skip-compile',action='store_true')
    parser.add_argument('--sim-build',type=Path)
    parser.add_argument('--execution-dir',type=Path)
    parser.add_argument('--analysis-lock',type=Path)
    parser.add_argument('--min-free-gib',type=float,default=3.)
    parser.add_argument('--min-commit-gib',type=float,default=2.)
    parser.add_argument('--state',type=Path,default=HERE/'status.json')
    args = parser.parse_args()
    prepared = json.loads(args.prepared.read_text())
    build = Path(prepared['build'])
    sim_build = args.sim_build or build
    if args.sim_build:
        assert args.skip_compile, 'A reused snapshot must not be recompiled implicitly'
        for name in ('rc_bd.v','rc_wrapper.v','tb_rc_gui.sv'):
            assert sha(build/'template'/name) == sha(sim_build/'template'/name), (name,'snapshot source mismatch')
    sim = sim_build/'sim'
    snapshot_sources = {}
    if args.execution_dir:
        assert args.skip_compile, 'An isolated runtime directory requires an already compiled snapshot'
        assert not args.execution_dir.exists(), 'Use a new runtime directory to preserve prior evidence'
        snapshot = sim/'xsim.dir/fine_gui'
        snapshot_sources = {str(path.relative_to(snapshot)):sha(path)
                            for path in snapshot.rglob('*') if path.is_file()}
        shutil.copytree(snapshot,args.execution_dir/'xsim.dir/fine_gui')
        shutil.copy2(sim/'xsim.ini',args.execution_dir/'xsim.ini')
        sim = args.execution_dir
    cases = [case for case in prepared['cases'] if not args.name or case['name'] in args.name]
    assert cases
    if args.state.exists():
        raise RuntimeError('Execution evidence already exists; use a new explicit --state path')
    state = dict(complete=False,stage='compile',build=str(build),sim_build=str(sim_build),
                 execution_dir=str(sim),snapshot_sources=snapshot_sources,
                 helper_sha256=LOADED_HELPER_SHA256,cases=[])
    def save():
        state['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        args.state.write_text(json.dumps(state,indent=2))
    def execute(tool,arguments,path):
        with path.open('w') as stream:
            result = subprocess.run([str(VIVADO/(tool+'.bat')),*arguments],cwd=sim,
                                    stdout=stream,stderr=subprocess.STDOUT)
        assert result.returncode == 0, (tool,result.returncode,str(path))
    try:
        save()
        if not sim.exists():
            (sim/'xsim.dir').mkdir(parents=True)
            shutil.copytree(SHARED/'xsim.dir/xil_defaultlib',sim/'xsim.dir/xil_defaultlib')
            shutil.copy2(SHARED/'xsim.ini',sim/'xsim.ini')
        if not args.skip_compile:
            execute('xvlog',['--relax','-prj',str(build/'template/sources.prj')],build/'compile_console.log')
            state['stage']='elaborate';save()
            libraries = [arg for lib in prepared['libraries'] for arg in ('-L',lib)]
            execute('xelab',['--O2','--debug','off','--relax','--mt','off',*libraries,
                '--snapshot','fine_gui','xil_defaultlib.tb_rc_gui','xil_defaultlib.glbl'],build/'elaborate_console.log')
        for case in cases:
            while True:
                physical,commit = memory_headroom()
                if physical >= args.min_free_gib and commit >= args.min_commit_gib:
                    break
                state['stage']='wait_memory';state['memory_headroom_gib']=[physical,commit];save()
                print(f'WAIT memory: physical={physical:.2f} GiB, commit={commit:.2f} GiB',flush=True)
                time.sleep(30)
            state['stage']='simulate';state['active_case']=case['name'];save()
            out = Path(case['folder'])
            options = out/'options.txt'
            options.write_text('\n'.join(['fine_gui','-runall',f'-testplusarg "CASE={out.as_posix()}"',
                f'-testplusarg "OUT={out.as_posix()}"',f'-testplusarg "CYCLES={case["cycles"]}"',
                f'-log "{(out/"xsim.log").as_posix()}"']))
            execute('xsim',['-f',str(options)],out/'run_console.log')
            state['stage']='analyze';save()
            with analysis_lock(args.analysis_lock):
                state['cases'].append(check(case));save()
            print(f'PASS {case["name"]}',flush=True)
        state['complete']=True;state['stage']='passed';save()
    except BaseException as error:
        state['stage']='failed';state['error']=repr(error);save()
        raise


if __name__ == '__main__':
    main()
