"""Display-only readout/RF windows on the selected, ideal AWG time axis."""
from dataclasses import replace
from math import ceil, isfinite

try:
    from .qick_fine_tune_sweep import cycles_from_us
except ImportError:
    from qick_fine_tune_sweep import cycles_from_us


def selected_segment_bounds_us(sequence, point_index, segment_name, fabric_mhz):
    """Use the same point-specific durations as the waveform preview."""
    if not isfinite(fabric_mhz) or fabric_mhz <= 0:
        raise ValueError("AWG fabric clock must be positive and finite")
    start = 0
    for index, segment in enumerate(sequence.segments):
        duration = sequence.segment_duration_cycles_at(point_index, index)
        if segment.name == segment_name and segment.kind == "set":
            return start / fabric_mhz, (start + duration) / fabric_mhz
        start += duration
    raise ValueError(f"unknown acquisition/RF SET segment {segment_name!r}")


def acquisition_window(sequence, point_index, spec, profile, fabric_mhz, tproc_mhz):
    """Nominal FIR input coverage and DDR writes, relative to the first AWG edge.

    This is the lightweight equivalent of ``fir_dc_timing_preview``'s FIR
    offsets, placed on the *ideal waveform* axis. It does not compile a program
    or include AWG command scheduling/pipeline offsets. Continuous decimation
    adds up to one sample period of phase uncertainty. The input interval is
    group-delay referenced, not the complete FIR impulse-response support.
    """
    start, _end = selected_segment_bounds_us(
        sequence, point_index, spec.segment_name, fabric_mhz)
    if not isfinite(tproc_mhz) or tproc_mhz <= 0:
        raise ValueError("tProcessor clock must be positive and finite")
    if profile is None:
        raise ValueError("Identify QICK to load the HWH FIR rate and delay; acquisition duration is unavailable")
    user_delay = (cycles_from_us(spec.delay_us, tproc_mhz) / tproc_mhz
                  if spec.delay_us > 0 else 0.0)
    trigger = start + user_delay
    if profile.software_warmup_compensation:
        trigger += profile.software_trigger_delay_tproc_cycles(tproc_mhz) / tproc_mhz
    register = spec.fpga_trigger_delay_samples
    if register is None:
        register = profile.selected_trigger_delay_value(spec.fpga_trigger_delay_us)
    storage_start = trigger + profile.trigger_delay_us_for(register)
    group_delay = ceil(profile.group_delay_input_samples) / profile.input_rate_mhz
    span = spec.samples_per_trigger * profile.sample_period_us
    return dict(
        point_index=point_index, ro_ch=spec.ro_ch, segment_name=spec.segment_name,
        samples=spec.samples_per_trigger, sample_rate_hz=profile.sample_rate_hz,
        sample_period_us=profile.sample_period_us, trigger_us=trigger,
        input_start_us=storage_start - group_delay,
        input_end_us=storage_start - group_delay + span,
        storage_start_us=storage_start, storage_end_us=storage_start + span,
        duration_us=span,
    )


def selected_rf_events(sequence, point_index, spec, fabric_mhz, *, software_values=None):
    """Resolve RF display timing onto the same selected AWG sweep point."""
    # Software coordinates are resolved before looking up pulse events, just as
    # execution recompiles one concrete RF sequence per host coordinate. The
    # caller supplies the corresponding concrete AWG sequence for SET extension.
    if software_values:
        predefined = {}
        if ("rf_template_n", "N") in software_values:
            predefined["n_pulses"] = int(round(software_values[("rf_template_n", "N")]))
        if ("rf_template_tau", "tau") in software_values:
            predefined["tau_us"] = float(software_values[("rf_template_tau", "tau")])
        if predefined:
            spec = spec.with_predefined_parameters(**predefined)
        delays = {name: float(value) for (kind, name), value in software_values.items()
                  if kind == "rf_delay"}
        if delays:
            spec = spec.with_delay_parameters(delays)
        durations = {name: float(value) for (kind, name), value in software_values.items()
                     if kind == "rf_t2_duration"}
        if durations:
            spec = spec.with_duration_parameters(durations)
        amplitudes = {name: float(value) for (kind, name), value in software_values.items()
                      if kind == "rf_amplitude"}
        if amplitudes:
            spec = spec.with_amplitude_parameters(amplitudes)
        phases = {name: float(value) for (kind, name), value in software_values.items()
                  if kind == "rf_phase"}
        if phases:
            spec = spec.with_phase_parameters(phases)
    start, end = selected_segment_bounds_us(
        sequence, point_index, spec.segment_name, fabric_mhz)
    values = {
        (axis.axis_kind, getattr(axis, "parameter_name", "")): value
        for axis, value in zip(sequence.sweep_axes, sequence.sweep_coordinate(point_index))
        if getattr(axis, "gen_ch", None) == spec.gen_ch
        and axis.segment_name == spec.segment_name
    }
    resolved = []
    duration_deltas = {}
    for event in spec.pulse_events:
        duration = values.get(("rf_duration", event.duration_parameter), event.duration_us)
        duration_deltas[event.duration_parameter] = duration - event.duration_us
        delay = event.delay_us + sum(duration_deltas.get(name, 0.0)
                                     for name in event.preceding_duration_parameters)
        event = replace(event, duration_us=duration, delay_us=delay,
                        frequency_mhz=values.get(("rf_frequency", event.frequency_parameter),
                                                 event.frequency_mhz))
        event_start, event_end = start + delay, start + delay + duration
        if spec.require_within_segment and event_end > end + 1e-12:
            raise ValueError(f"RF pulse {event.name!r} extends beyond {spec.segment_name}")
        resolved.append((event, event_start, event_end))
    return tuple(resolved)


def calibrated_rf_preview_events(spec, events):
    """Map selected RF-event gains for display using the execution calibration.

    ``events`` contains ``(event, start_us, end_us)`` tuples returned by
    ``selected_rf_events``. Calibration is read-only; target power and source
    metadata remain attached to each event. Invalid calibration raises instead
    of displaying a stale manual gain as the calibrated output.
    """
    try:
        from .power_calibration import CalibrationDatabase
    except ImportError:
        from power_calibration import CalibrationDatabase
    import numpy as np
    parameters = {parameter.name: parameter for parameter in spec.frequency_parameters}
    resolved = []
    for event, start, end in events:
        if event.power_calibration_enabled:
            try:
                parameter = parameters.get(event.frequency_parameter)
                if parameter is not None and parameter.sweep_enabled:
                    frequencies = np.linspace(parameter.sweep_start_mhz, parameter.sweep_stop_mhz,
                                              parameter.sweep_count, dtype=np.float64)
                elif not event.frequency_parameter and spec.frequency_sweep_enabled:
                    frequencies = np.linspace(spec.frequency_sweep_start_mhz, spec.frequency_sweep_stop_mhz,
                                              spec.frequency_sweep_count, dtype=np.float64)
                else:
                    frequencies = np.asarray([event.frequency_mhz], dtype=np.float64)
                selected = int(np.argmin(np.abs(frequencies - event.frequency_mhz)))
                if abs(float(frequencies[selected]) - event.frequency_mhz) > 1e-5:
                    raise ValueError('selected RF frequency is outside the configured sweep coordinates')
                calibration = CalibrationDatabase(event.power_calibration_database_path).output_calibration(
                    spec.output_board_type, frequencies,
                    run_id=event.power_calibration_run_id or None, nqz=int(spec.nqz),
                    output_filter_type=str(spec.filter_type),
                    output_filter_cutoff_ghz=float(spec.filter_cutoff),
                    output_filter_bandwidth_ghz=float(spec.filter_bandwidth))
                schedule = calibration.build_gain_schedule(
                    frequencies, event.target_output_power_dbm,
                    output_att1_db=float(spec.effective_att1_db),
                    output_att2_db=float(spec.effective_att2_db), max_entries=len(frequencies))
                event = replace(event, gain=int(schedule.gain_codes[selected]))
            except Exception as exc:
                raise ValueError(f"RF preview calibration failed for {event.name!r}: {exc}") from exc
        resolved.append((event, start, end))
    return tuple(resolved)
