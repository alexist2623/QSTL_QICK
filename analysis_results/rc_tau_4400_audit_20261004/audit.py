"""Numerical audit, NOT RTL or live-board evidence.

Constant 100 mV target, initially relaxed RC, 4.8 GSPS, +/-800 mV DAC.
Use production coefficient conversion, closed-form integer trapezoidal
history, effective 14-bit DAC rounding, and independent exact ZOH analog RC.
No FIR/readout, analog bandwidth, unknown loading, clipping, or shot resets.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('rc_conversion', ROOT/'qick/qick_lib/qick/precompensation.py')
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)
FS_MHZ = 4800.
COUNT = 24_000_000  # 5 ms, using every scalar sample in the numerical model.
BLOCK = 48_000
GAIN = 4096  # 100 mV
MV_PER_CODE = 800./32768
cases = [(4400.,4400.), (3750.,4400.), (3750.,3750.)]
fig, ax = plt.subplots(figsize=(10,5), constrained_layout=True)
results = []
for programmed, analog in cases:
    coefficient = rc.rc_coefficient(programmed, FS_MHZ)
    previous_u = previous_y = 0.
    max_error = 0.
    trace_t, trace_y = [], []
    for start in range(0, COUNT, BLOCK):
        n = np.arange(start, min(start+BLOCK,COUNT), dtype=np.int64)
        # Initial previous target is zero; each later trapezoid adds 2*GAIN*C.
        fixed = (GAIN << 48) + GAIN*(2*n+1)*coefficient
        codes = ((fixed+(1<<49)) >> 50)*4
        assert codes.min() >= -32768 and codes.max() <= 32764
        u = codes.astype(float)*MV_PER_CODE
        difference = np.diff(u, prepend=previous_u)
        powers = np.exp(-np.arange(1,len(n)+1)/(FS_MHZ*analog))
        # Exact ZOH high-pass recurrence y[n] = a*y[n-1]+u[n]-u[n-1].
        y = powers*(previous_y+np.cumsum(difference/powers))
        max_error = max(max_error, float(np.max(np.abs(y-100))))
        trace_t.extend((n[::4800]/FS_MHZ/1000).tolist())
        trace_y.extend(y[::4800].tolist())
        previous_u, previous_y = float(u[-1]), float(y[-1])
    if programmed == analog:
        assert max_error <= .1, max_error
    effective = (1<<48)/(2*FS_MHZ*coefficient)
    results.append(dict(programmed_tau_us=programmed,analog_tau_us=analog,
                        coefficient=coefficient,effective_tau_us=effective,
                        final_mV=previous_y,max_abs_target_error_mV=max_error,
                        samples=COUNT))
    ax.plot(trace_t, trace_y, label=f'Set {programmed:g} us / analog {analog:g} us',alpha=.8)
ax.axhline(100,color='black',ls='--',lw=1,label='Target 100 mV')
ax.set(xlabel='Time (ms)',ylabel='After analog RC (mV)',
       title='Numerical model: quantized DAC + exact analog RC\nNot a new RTL run or physical measurement')
ax.grid(alpha=.2);ax.legend()
fig.savefig(OUT/'rc_tau_comparison.png',dpi=160)
(OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
