"""Compare area-accumulator domains using actual LTspice R/C transients.

Analysis only: no FPGA or production GUI code is modified. PWL voltage sources
represent the ideal continuous inverse; physical coupling is a capacitor and
resistor integrated by LTspice, with analog state retained across repetitions.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


BODY = ((100e-6, .030), (10e-6, .010), (400e-6, .060))
LABELS = {
    'pre': 'Area before IIR; compensation before IIR',
    'post_pre': 'Area after IIR; compensation before IIR',
    'post_post': 'Area after IIR; compensation after IIR',
}


def body_metrics(tau):
    area = drive_area = 0.
    for duration, level in BODY:
        drive_area += level*duration + area*duration/tau + level*duration**2/(2*tau)
        area += level*duration
    return area, drive_area


def make_case(kind, mode, tau):
    area, drive_area = body_metrics(tau)
    history = area/tau
    amplitude = .020
    duration = 200e-6
    if mode == 'fixed_voltage':
        if kind == 'pre': duration = area/amplitude
        elif kind == 'post_post': duration = drive_area/amplitude
        else:
            # The actual filtered DAC area keeps changing during compensation.
            # Solve A_u + (H-A)*T - A*T*T/(2*tau) = 0.
            b = history-amplitude
            duration = tau/amplitude*(b+math.sqrt(b*b+2*amplitude*drive_area/tau))
    else:
        if kind == 'pre': amplitude = area/duration
        elif kind == 'post_post': amplitude = drive_area/duration
        else: amplitude = (drive_area+history*duration)/(duration+duration**2/(2*tau))
    leftover = history-amplitude*duration/tau if kind != 'post_post' else None
    return dict(kind=kind, mode=mode, tau_s=tau, compensation_duration_s=duration,
                compensation_amplitude_v=amplitude, body_area_vs=area,
                body_dac_area_vs=drive_area, iir_state_before_reset_v=leftover)


def sources(case, repeats, period, end):
    """PWL knots of requested x and inverse drive u, with 1 ns SET edges."""
    tau = case['tau_s']
    rise = 1e-9
    start = 5e-6
    tx, vx, tu, vu = [0.], [0.], [0.], [0.]
    ends = []
    def put(t, x, u):
        tx.append(t); vx.append(x); tu.append(t); vu.append(u)
    for rep in range(repeats):
        t = rep*period+start
        put(t-rise, 0., 0.)
        integral = 0.
        for duration, level in BODY:
            put(t, level, level+integral/tau)
            integral += level*duration
            t += duration
            put(t-rise, level, level+integral/tau)
        amplitude = case['compensation_amplitude_v']
        duration = case['compensation_duration_s']
        corrected = case['kind'] != 'post_post'
        put(t, -amplitude, -amplitude+integral/tau if corrected else -amplitude)
        integral -= amplitude*duration
        t += duration
        put(t-rise, -amplitude, -amplitude+integral/tau if corrected else -amplitude)
        put(t, 0., integral/tau if corrected else 0.)
        # Match the GUI's explicit per-repeat digital-history reset. The real
        # capacitor is deliberately NOT reset; any error survives in the RC.
        put(t+20e-9, 0., integral/tau if corrected else 0.)
        put(t+21e-9, 0., 0.)
        ends.append(t)
    put(end, 0., 0.)
    return (np.array(tx), np.array(vx)), (np.array(tu), np.array(vu)), ends


def read_ascii_raw(path):
    data = path.read_bytes()
    encoding = 'utf-16' if data[:2] in (b'\xff\xfe', b'T\0') else 'utf-8'
    text = data.decode(encoding if data[:2] != b'T\0' else 'utf-16-le')
    head, raw = text.split('Values:', 1)
    variables = [line.split()[1] for line in head.rsplit('Variables:', 1)[1].splitlines() if line.strip()]
    tokens = raw.split()
    count = len(variables)
    array = np.asarray([float(v) for i,v in enumerate(tokens) if i%(count+1)], dtype=float).reshape(-1,count)
    return {name.lower(): array[:, i] for i,name in enumerate(variables)}


def simulate(out, executable, mode, tau, repeats):
    tag = f'{mode}_tau{tau*1e6:g}us'
    cases = [make_case(kind, mode, tau) for kind in LABELS]
    period = 5e-6+sum(t for t,_ in BODY)+max(c['compensation_duration_s'] for c in cases)+100e-6
    stop = period*repeats+5*tau
    lines = [f'Area domain comparison: {tag}', '* Analysis only, ideal DAC and linear AC coupling.',
             '.options plotwinsize=0 reltol=1e-7 abstol=1e-12 vntol=1e-10',
             f'.tran 0 {stop:.16g} 0 {min(tau/300, 1e-6):.16g}', '.save V(xpre) V(xpost_pre) V(xpost_post) V(upre) V(upost_pre) V(upost_post) V(ypre) V(ypost_pre) V(ypost_post)']
    for case in cases:
        kind = case['kind']
        x, u, ends = sources(case, repeats, period, stop)
        case.update(period_s=period, compensation_end_s=ends)
        for prefix, source in (('x',x), ('u',u)):
            path = out/f'{tag}_{prefix}{kind}.pwl'
            np.savetxt(path, np.column_stack(source), fmt='%.16g')
            lines.append(f'V{prefix}{kind} {prefix}{kind} 0 PWL FILE="{path.as_posix()}"')
        lines.extend((f'C{kind} u{kind} y{kind} {tau/1000:.16g}', f'R{kind} y{kind} 0 1000'))
    lines.append('.end')
    net = out/f'{tag}.cir'; net.write_text('\n'.join(lines)+'\n', encoding='ascii')
    process = subprocess.run([str(executable), '-b', '-ascii', str(net)], cwd=out,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=120)
    log = net.with_suffix('.log').read_text(errors='replace')
    assert process.returncode == 0 and net.with_suffix('.raw').exists(), (process.returncode,log)
    assert 'Fatal' not in log and 'aborted' not in log.lower(), log
    raw = read_ascii_raw(net.with_suffix('.raw')); t = raw['time']
    fig, axes = plt.subplots(3, 2, figsize=(13, 9), constrained_layout=True)
    for row, case in enumerate(cases):
        kind = case['kind']; x = raw[f'v(x{kind})']; u = raw[f'v(u{kind})']; y = raw[f'v(y{kind})']
        last = (repeats-1)*period
        sel = (t>=last)&(t<=last+period)
        local = (t[sel]-last)*1e6
        axes[row,0].plot(local,x[sel]*1000,label='Target before IIR')
        axes[row,0].plot(local,u[sel]*1000,label='DAC drive',alpha=.8)
        axes[row,0].plot(local,y[sel]*1000,label='LTspice after RC',ls='--')
        axes[row,0].set_title(LABELS[kind],fontsize=10)
        ends=case['compensation_end_s']
        tail_t = t[(t>=ends[-1]-20e-6)&(t<=ends[-1]+100e-6)]
        axes[row,1].plot((tail_t-ends[-1])*1e6,np.interp(tail_t,t,y)*1000)
        axes[row,1].axvline(.021,color='gray',ls=':',label='IIR reset')
        axes[row,1].set_title('After compensation: RC tail at last repetition',fontsize=10)
        sample_times = np.asarray(ends)+.1e-6
        tails = np.interp(sample_times,t,y)*1000
        case['post_reset_rc_residual_mv'] = tails.tolist()
        body_errors=[]
        for rep in range(repeats):
            cursor=rep*period+5e-6
            for duration,level in BODY:
                times=np.linspace(cursor+.2e-6,cursor+duration-.2e-6,50)
                body_errors.extend((np.interp(times,t,y)-level)*1000)
                cursor+=duration
        case['max_body_error_mv'] = float(np.max(np.abs(body_errors)))
        case['last_repeat_dac_area_v_s'] = float(np.trapezoid(u[sel],t[sel]))
        case['last_repeat_rc_area_v_s'] = float(np.trapezoid(y[sel],t[sel]))
        case['max_abs_dac_mv'] = float(np.max(np.abs(u))*1000)
        for ax in axes[row]:
            ax.set_xlabel('Time (us)'); ax.set_ylabel('Voltage (mV)'); ax.grid(alpha=.25)
    axes[0,0].legend(fontsize=8); axes[0,1].legend(fontsize=8)
    fig.suptitle(f'Actual LTspice RC transient | tau={tau*1e6:g} us | {mode} | {repeats} repeats\n'
                'Target: 30 mV / 100 us, 10 mV / 10 us, 60 mV / 400 us; ideal inverse and DAC')
    fig.savefig(out/f'{tag}.png',dpi=160); plt.close(fig)
    assert cases[0]['max_body_error_mv'] < .01, cases[0]
    assert max(abs(v) for v in cases[0]['post_reset_rc_residual_mv']) < .01, cases[0]
    return cases


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--ltspice',type=Path,default=Path('C:/Program Files/ADI/LTspice/LTspice.exe'))
    args=parser.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    results=[]
    for tau in (300e-6, 1000e-6):
        for mode in ('fixed_voltage','fixed_time'):
            results.extend(simulate(out,args.ltspice,mode,tau,5))
            (out/'result.json').write_text(json.dumps(results,indent=2))
            print(f'PASS: LTspice tau={tau} mode={mode}',flush=True)


if __name__=='__main__': main()
