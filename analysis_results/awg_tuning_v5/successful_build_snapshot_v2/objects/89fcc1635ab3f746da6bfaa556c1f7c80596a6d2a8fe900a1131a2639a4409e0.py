"""Bounded-size, ideal DAC precompensation previews (not an RTL simulation)."""
import numpy as np


def rc_precompensated_vertices(time_ns, values_mv, tau_us, points_per_ramp=33):
    """Evaluate x + integral(x)/tau exactly on each linear input interval.

    Duplicate timestamps are SET edges, with no added area. The integrator
    starts at zero, as it does for each hardware repetition. DC epilogues and
    zero-input gaps must be supplied in the input vertices. Flat intervals
    become straight lines; ramps become quadratic curves. No scalar-sample
    expansion is needed, even for long pulses.
    """
    times = np.asarray(time_ns, dtype=float)
    values = np.asarray(values_mv, dtype=float)
    if (times.ndim != 1 or not times.size or values.ndim != 2
            or values.shape[1] != times.size or not np.all(np.isfinite(times))
            or not np.all(np.isfinite(values)) or np.any(np.diff(times) < 0)):
        raise ValueError("RC preview requires finite, ordered waveform vertices")
    tau_ns = float(tau_us) * 1000.0
    if not np.isfinite(tau_ns) or tau_ns <= 0:
        raise ValueError("RC tau must be positive and finite")
    if int(points_per_ramp) < 2:
        raise ValueError("points_per_ramp must be at least 2")
    history = np.zeros(values.shape[0])
    out_times = [times[0]]
    out_values = [values[:, 0].copy()]
    for index, duration in enumerate(np.diff(times)):
        start, end = values[:, index], values[:, index + 1]
        if duration == 0:
            out_times.append(times[index + 1])
            out_values.append(end + history)
            continue
        slope = (end - start) / duration
        count = int(points_per_ramp) if np.any(slope) else 2
        offsets = list(np.linspace(0, duration, count)[1:])
        # Include interior extrema, so auto-fit does not miss an overshoot.
        for a, b in zip(start, slope):
            if b:
                stationary = -tau_ns - a / b
                if 0 < stationary < duration:
                    offsets.append(stationary)
        for offset in sorted(set(offsets)):
            out_times.append(times[index] + offset)
            out_values.append(start + slope * offset + history
                              + (start * offset + .5 * slope * offset**2) / tau_ns)
        history += (start + end) * .5 * duration / tau_ns
    return np.asarray(out_times), np.asarray(out_values).T
