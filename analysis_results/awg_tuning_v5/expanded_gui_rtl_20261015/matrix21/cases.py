"""Small, orthogonal current-v4 GUI-to-RTL regressions (not exhaustive products)."""
MATRIX = [[1., .23, -.11], [-.17, 1., .07], [.12, -.09, 1.]]
CASES = {
    'hold_fixed_time': dict(sweep='hold_duration', count=3),
    'hold_fixed_voltage_descending': dict(sweep='hold_duration', count=3, mode='fixed_voltage', descending=True, delay=.1),
    'ramp_fixed_time': dict(sweep='ramp_rate'),
    'ramp_fixed_voltage_descending': dict(sweep='ramp_rate', mode='fixed_voltage', descending=True),
    'rf_duration_fixed': dict(sweep='rf_duration_fixed'),
    'rf_duration_extend': dict(sweep='rf_duration', mode='fixed_voltage'),
    'rf_frequency': dict(sweep='rf_frequency'),
    'two_voltage_axes': dict(sweep='hold_duration', count=3, two_voltage=True),
    'two_voltage_axes_reversed': dict(sweep='hold_duration', count=3, two_voltage=True, descending=True, swap=True),
    'rc_only': dict(sweep='hold_duration', compensation='filter'),
    'dc_only': dict(sweep='hold_duration', compensation='dc'),
    'compensation_off': dict(sweep='hold_duration', compensation='off'),
    'square_frequency': dict(sweep='hold_duration', square='frequency'),
    'square_amplitude': dict(sweep='hold_duration', square='amplitude'),
    'square_phase': dict(sweep='hold_duration', square='phase'),
}

def case(name):
    return dict(count=2, mode='fixed_time', compensation='dc_rc', descending=False,
                swap=False, delay=0., two_voltage=False, square=None) | CASES[name]

for _n in (1,2):
    for _tau in (.2,.4):
        CASES[f"cpmg_n{_n}_tau{round(_tau*1000)}ns"]=dict(sweep="hold_duration",n=_n,tau=_tau,named=None)
for _named in ("frequency","duration"):
    CASES["cpmg_named_"+_named]=dict(sweep="hold_duration",n=2,tau=.2,named=_named)
