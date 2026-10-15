"""Fast RC DAC headroom checks; never expand scalar samples or sweep grids."""
from itertools import product
import math

import numpy as np


def sweep_corners(sequence):
    """Return only the Cartesian endpoints (four points for a 2-D sweep)."""
    shape = tuple(int(axis.count) for axis in sequence.sweep_axes)
    if not shape:
        return (0,)
    return tuple(int(np.ravel_multi_index(index, shape)) for index in product(
        *((0,) if count == 1 else (0, count - 1) for count in shape)))


def interval_extrema(intervals, inverse_tau):
    """Bound x + integral(x)/tau for piecewise-linear normalized intervals.

    Each entry is (start, end, duration_us, input_error_bound). The error
    envelope also integrates, so quantization cannot silently consume headroom.
    A RAMP may have an interior extremum even when its endpoints are safe.
    History starts at zero, matching the reset at every hardware repetition.
    """
    history = error_history = 0.0
    low = high = 0.0
    for start, end, duration, error in intervals:
        if duration < 0 or not all(math.isfinite(v) for v in
                                   (start, end, duration, error)):
            raise ValueError("Invalid RC output prediction interval")
        slope = (end - start) / duration if duration else 0.0
        candidates = [0.0, duration]
        if slope and inverse_tau:
            for sign in (-1, 1):
                stationary = -(slope + (start + sign * error) * inverse_tau) / (slope * inverse_tau)
                if 0 < stationary < duration:
                    candidates.append(stationary)
        for time in candidates:
            value = start + slope * time + history + inverse_tau * (
                start * time + 0.5 * slope * time * time)
            uncertainty = error + error_history + inverse_tau * error * time
            low = min(low, value - uncertainty)
            high = max(high, value + uncertainty)
        history += 0.5 * (start + end) * duration * inverse_tau
        error_history += error * duration * inverse_tau
    # Include the zero-input gap before the digital reset and the reset itself.
    return min(low, history - error_history), max(high, history + error_history)


def check_limits(bounds, *, name, point, limits, full_scale_mv=None):
    low, high = bounds
    if low >= limits[0] and high <= limits[1]:
        return
    scale = 1.0 if full_scale_mv is None else float(full_scale_mv)
    unit = "full scale" if full_scale_mv is None else "mV"
    raise ValueError(
        f"RC-compensated DAC output exceeds range: {name}, sweep corner {point}. "
        f"Predicted bounds [{low * scale:+.6g}, {high * scale:+.6g}] {unit}; "
        f"allowed [{limits[0] * scale:+.6g}, {limits[1] * scale:+.6g}] {unit}. "
        "Includes DC compensation and the zero-input hold before IIR reset. "
        "Reduce voltage/duration or increase RC tau.")


def validate_channel_voltage_ranges(sequence):
    """Check nominal and DC compensation voltages at sweep endpoints only."""
    if sequence.output_full_scales_mv is None:
        return
    for point in sweep_corners(sequence):
        for index in range(len(sequence.segments)):
            sequence.amplitudes_at(point, index)
        for comp in sequence.bias_t_compensation_preview(point):
            if abs(comp.target_amplitude) > 1:
                scale = sequence.output_full_scales_mv[comp.output_index]
                raise ValueError(f'DC compensation for {comp.output_name} exceeds +/-{scale:g} mV')


def validate_sequence_rc_range(sequence, fabric_mhz, full_scale_mv):
    """GUI preflight in physical coordinates, before connecting to hardware."""
    if sequence.rc_compensation is None:
        return ()
    inverse_tau = 1.0 / sequence.rc_compensation.tau_us
    results = []
    for point in sweep_corners(sequence):
        times, values, _ = sequence.compensated_waveform_vertices(point)
        for name in sequence.output_names:
            scale_mv = (sequence.output_full_scales_mv[sequence.output_names.index(name)]
                        if sequence.output_full_scales_mv else full_scale_mv)
            wave = values[name]
            intervals = [(float(a), float(b), float(dt) / fabric_mhz, 0.0)
                         for a, b, dt in zip(wave[:-1], wave[1:], np.diff(times))]
            # A single zero-duration SET still has an output value.
            intervals.append((float(wave[-1]), float(wave[-1]), 0.0, 0.0))
            bounds = interval_extrema(intervals, inverse_tau)
            check_limits(bounds, name=name, point=point, limits=(-1.0, 1.0),
                         full_scale_mv=scale_mv)
            results.append(dict(point_index=point, output_name=name,
                                minimum_mv=bounds[0] * scale_mv,
                                maximum_mv=bounds[1] * scale_mv))
    return tuple(results)


def validate_program_rc_range(program):
    """Recheck compiler endpoint words, DC fields and quantization margins.

    This uses the *executed* endpoint commands after register-step rounding,
    not the ideal sweep stop. Conservative RAMP bounds cover step error and
    sample quantization. Runtime is O(corners * outputs * segments).
    """
    sequence = program.sequence
    if sequence.rc_compensation is None:
        return ()
    from qick.precompensation import rc_coefficient

    if getattr(program, '_hardware_dc_area', False) and sequence.bias_t_compensation is not None:
        from qick_dc_area import validate_rc
        return validate_rc(program)

    results = []
    rows = {index: row for row, index in enumerate(program._compile_validation_point_indices)}
    fields = {int(f['output_index']): f for f in program._bias_t_fields}
    for point_index in sweep_corners(sequence):
        program._check_cancel()
        point = (program.compiled_points[point_index]
                 if program._compiled_point_by_index is None
                 else program._compiled_point_by_index[point_index])
        for output, channel in enumerate(program.awg_channels):
            gen = program.soccfg['gens'][channel]
            fabric = float(gen['f_fabric'])
            rate = fabric * int(gen['n_pts'])
            coef = rc_coefficient(sequence.rc_compensation.tau_us, rate)
            inverse_tau = 2 * coef * rate / 2**48
            quantum = 2**int(gen.get('dac_invalid_lsb', 2)) / 32768.0
            current = 0.0
            intervals = []
            for seg_index, commands in enumerate(point.segment_commands):
                command = next((c for c in commands if c.output_index == output), None)
                duration = sequence.segment_duration_cycles_at(point_index, seg_index) / fabric
                target = current if command is None else command.target_code / 32768.0
                if sequence.segments[seg_index].kind == 'set':
                    intervals.append((target, target, duration, 0.0))
                else:
                    error = quantum
                    if command is not None:
                        # The final scalar sample is forced to target by RTL.
                        stepped_end = current + command.step * max(0, command.duration_samples - 1) / (2**int(gen['frac']) * 32768.0)
                        error += abs(stepped_end - target)
                    intervals.append((current, target, duration, error))
                current = target
            # User pulse returns to zero before DC compensation and RC reset.
            intervals.append((0.0, 0.0, 0.0, 0.0))
            if sequence.bias_t_compensation is not None:
                row = rows[point_index]
                field = fields[output]
                if sequence.bias_t_compensation.mode == 'fixed_time':
                    target = float(program._bias_t_target_code_actual[row, output]) / 32768.0
                    duration = int(field['fixed_duration_tproc_cycles']) / program.tproc_mhz
                else:
                    signed_duration = int(program._bias_t_duration_q_actual[row, output])
                    bits = int(field['duration_frac_bits'])
                    duration = ((abs(signed_duration) + (1 << (bits - 1))) >> bits) / program.tproc_mhz
                    target = int(field['negative_code'] if signed_duration > 0 else field['positive_code']) / 32768.0
                if duration:
                    intervals.append((target, target, duration, 0.0))
                intervals.append((0.0, 0.0, 0.0, 0.0))
            low, high = interval_extrema(intervals, inverse_tau)
            # Reserve half an output LSB, trapezoidal sample-edge error, and
            # two fabric clocks per transition for command/clock quantization.
            peak = max(abs(v) for interval in intervals for v in interval[:2])
            margin = quantum / 2 + peak * inverse_tau * (len(intervals) * 2 / fabric + 1 / rate)
            bounds = low - margin, high + margin
            limits = int(gen.get('minv', -32768)) / 32768.0, int(gen.get('maxv', 32764)) / 32768.0
            check_limits(bounds, name=f"{sequence.output_names[output]} (gen {channel})",
                         point=point_index, limits=limits,
                         full_scale_mv=(sequence.output_full_scales_mv[output] if sequence.output_full_scales_mv else getattr(sequence, 'output_full_scale_mv', None)))
            results.append(dict(point_index=point_index, gen_ch=channel,
                                minimum_normalized=bounds[0], maximum_normalized=bounds[1]))
    return tuple(results)
