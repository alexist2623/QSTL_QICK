"""Lower circuit documents through the existing AWG/RF/FIR compiler.

This module adds no firmware commands. Unsupported exact schedules are rejected
before the existing experiment runner can configure or write the hardware.
Circuit time zero is a common, recorded origin after an AWG startup pre-roll.
"""
from __future__ import annotations

from dataclasses import dataclass, replace, asdict
from math import ceil, isclose, isfinite
from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
import inspect
import json
import uuid

try:
    from .quantum_circuit_model import validate_document, build_timeline
    from .dc_waveform_core import (QickRfPulseSpec, QickDdrReadoutSpec,
                                   QickRfCompositeItemSpec, QickRfFrequencyParameterSpec)
    from .qick_fine_tune_sweep import FineTuneSequence
    from .fir_ddr_profile import resolve_fir_ddr_profile
    from . import qick_qcodes_experiment as experiment
except ImportError:
    from quantum_circuit_model import validate_document, build_timeline
    from dc_waveform_core import (QickRfPulseSpec, QickDdrReadoutSpec,
                                  QickRfCompositeItemSpec, QickRfFrequencyParameterSpec)
    from qick_fine_tune_sweep import FineTuneSequence
    from fir_ddr_profile import resolve_fir_ddr_profile
    import qick_qcodes_experiment as experiment
try:
    from .quantum_circuit_loops import sweep_axis, point_document
except ImportError:
    from quantum_circuit_loops import sweep_axis, point_document

# Front-panel numbering, matching DCWaveform_Generator.DEFAULT_QSTL_*_CHANNELS.
DEFAULT_AWG_CHANNEL_MAP = (1, 3, 5, 7, 8, 9, 10, 11)
DEFAULT_RF_CHANNEL_MAP = (0, 2, 4, 6, 12, 13, 14, 15)
ANCHOR = "circuit_anchor"


@dataclass(frozen=True)
class CircuitExecution:
    document: dict
    sequence: FineTuneSequence
    awg_channels: tuple
    rf_specs: tuple
    readout_spec: QickDdrReadoutSpec
    repetitions_per_sweep: int
    program: object
    metadata: dict


def _ticks(value_us, mhz, label, *, positive=False):
    """Require representable timing instead of silently stretching a gate."""
    value = float(value_us) * float(mhz)
    if not isfinite(value) or value < 0 or (positive and value <= 0):
        raise ValueError(f"{label} must be {'positive' if positive else 'nonnegative'} and finite")
    nearest = round(value)
    if not isclose(value, nearest, rel_tol=0.0, abs_tol=1e-7):
        raise ValueError(f"{label} must be a multiple of {1000.0 / mhz:.9g} ns for the loaded clock")
    if positive and nearest < 1:
        raise ValueError(f"{label} is shorter than one loaded-clock cycle")
    return int(nearest)


def _mapped(channel, channels, label, gens):
    if channel < 1 or channel > len(channels):
        raise ValueError(f"{label} {channel} has no configured front-panel mapping")
    result = int(channels[channel - 1])
    if result < 0 or result >= len(gens):
        raise ValueError(f"{label} {channel} maps to generator {result}, absent from the loaded HWH")
    return result


def _configure_compensation(sequence, compensation, reference_mv, fabric_mhz):
    options = dict(compensation or {})
    allowed = {"bias_t_compensation_enabled", "bias_t_compensation_type",
               "bias_t_compensation_voltage_mv", "bias_t_compensation_mode",
               "bias_t_compensation_duration_us", "bias_t_filter_tau_us"}
    unknown = set(options) - allowed
    if unknown:
        raise ValueError(f"Unknown circuit compensation settings: {sorted(unknown)}")
    enabled = options.get("bias_t_compensation_enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("Compensation enabled must be a boolean")
    kind = options.get("bias_t_compensation_type", "dc")
    if kind not in ("dc", "filter", "dc_rc"):
        raise ValueError("Unsupported compensation type")
    if not enabled:
        return
    if kind in ("filter", "dc_rc"):
        sequence.set_rc_compensation(options.get("bias_t_filter_tau_us", 1000.0))
    if kind in ("dc", "dc_rc"):
        mv = options.get("bias_t_compensation_voltage_mv")
        mv = reference_mv * .1 if mv is None else float(mv)
        mode = options.get("bias_t_compensation_mode", "fixed_voltage")
        duration = None
        if mode == "fixed_time":
            duration = _ticks(options.get("bias_t_compensation_duration_us", 100.0),
                              fabric_mhz, "DC compensation duration", positive=True)
        sequence.set_bias_t_compensation(mv / reference_mv, mode=mode,
                                         fixed_duration_cycles=duration)


def _rf_template_map(templates):
    if templates is None:
        return {}
    if isinstance(templates, Mapping):
        result = dict(templates)
    else:
        result = {}
        for template in templates:
            if not isinstance(template, QickRfPulseSpec):
                raise TypeError("RF templates must be QickRfPulseSpec objects")
            if template.gen_ch in result:
                raise ValueError(f"More than one RF template configures generator {template.gen_ch}")
            result[template.gen_ch] = template
    if any(not isinstance(x, QickRfPulseSpec) for x in result.values()):
        raise TypeError("RF templates must be QickRfPulseSpec objects")
    if any(int(key) != value.gen_ch for key, value in result.items()):
        raise ValueError("RF template keys must match their generator channels")
    return result


def _rf_latencies(soccfg, awg_channels, timeline, rf_channel_map, explicit):
    """Select a verified digital-path profile, never infer an analog delay."""
    gens = soccfg["gens"]
    overrides = dict(explicit or {})
    result, profiles = {}, {}
    awg_profile = all(
        gens[ch].get("type") == "axis_awg_tuning_v3"
        and int(gens[ch].get("dc_area_version", 0)) == 1
        and int(gens[ch].get("dc_area_bits", 0)) == 48
        and int(gens[ch].get("output_latency_cycles", -1)) == 16
        for ch in awg_channels)
    for lane in timeline["rf"]:
        ch = _mapped(lane["channel"], rf_channel_map, "RF", gens)
        cfg = gens[ch]
        if ch in overrides:
            value = overrides[ch]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("Explicit RF output latency must be a nonnegative integer number of tProcessor clocks")
            result[ch], profiles[ch] = value, "caller_verified_digital_latency"
        elif (awg_profile and cfg.get("type") == "axis_signal_gen_v6"
              and int(cfg.get("revision", -1)) == 6
              and int(cfg.get("samps_per_clk", 0)) == 16
              and int(cfg.get("tmux_ch", -1)) == 0
              and float(cfg.get("f_fabric", 0)) == 300.0
              and float(soccfg["tprocs"][0]["f_time"]) == 300.0):
            result[ch] = 42
            profiles[ch] = "qstl_v3_rf_v6_300mhz_tmux_digital"
        else:
            raise ValueError(f"RF {lane['channel']} output latency is unknown for the loaded firmware profile; use the verified QSTL v3 profile or provide an explicitly verified digital latency")
    return result, profiles


def build_circuit_execution(document, soccfg, *, readout_template,
                            output_full_scales_mv, dac_current_settings=None,
                            awg_channel_map=DEFAULT_AWG_CHANNEL_MAP,
                            rf_channel_map=DEFAULT_RF_CHANNEL_MAP,
                            compensation=None, rf_templates=None,
                            rf_output_latency_tproc_cycles=None,
                            compile_validation_mode="boundary", cancel_check=None):
    """Validate and compile an isolated circuit without touching QICK hardware.

    The existing backend needs one FIR-DDR acquisition and an explicit AWG lane.
    Ramps on separate outputs may be simultaneous when their bounds match. A
    staggered/overlapping ramp or SET during another output's ramp is rejected:
    splitting it would add unwanted SET/RAMP pipeline transitions. Baselines and
    resolved absolute/relative targets come from the document, never the AWG
    editor's waveform. Its calibrated scales and compensation settings are reused.
    """
    if cancel_check:
        cancel_check()
    document = validate_document(document)
    for gate in document["gates"]:
        if (not gate["awg"] and not gate["rf"] and gate["acquisition"] is None
                and gate["name"].strip().casefold() not in ("wait", "idle", "delay")):
            raise ValueError(f"Gate {gate['name']!r} has no pulse or acquisition settings; configure it or name an intentional idle gate Wait/Idle/Delay")
    timeline = build_timeline(document)
    if len(timeline["acquisition"]) != 1:
        raise ValueError("Circuit QICK Run requires exactly one acquisition window; the existing DDR runner cannot execute zero or multiple windows per shot")
    if not isinstance(readout_template, QickDdrReadoutSpec):
        raise ValueError("Enable and configure RF Readout before running the circuit")
    if not timeline["awg"]:
        raise ValueError("Circuit QICK Run requires at least one explicit AWG setting or baseline")
    profile = resolve_fir_ddr_profile(soccfg, context="Quantum Circuit live HWH")
    gens = soccfg["gens"]
    channels = tuple(_mapped(row["channel"], awg_channel_map, "AWG", gens)
                     for row in timeline["awg"])
    if len(set(channels)) != len(channels):
        raise ValueError("AWG front-panel mappings must be unique")
    tproc_mhz = float(soccfg["tprocs"][0]["f_time"])
    if not isfinite(tproc_mhz) or tproc_mhz <= 0:
        raise ValueError("Loaded tProcessor clock is invalid")
    for ch in channels:
        cfg = gens[ch]
        if cfg.get("gen_type") != "awg_tuning" and not str(cfg.get("type", "")).startswith("axis_awg_tuning"):
            raise ValueError(f"Generator {ch} is not an AWG Tuning output in the loaded HWH")
        if not isclose(float(cfg["f_fabric"]), tproc_mhz, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Circuit execution currently requires matching AWG and tProcessor clocks")
    ports = [int(gens[ch]["tproc_ch"]) for ch in channels]
    if len(set(ports)) != len(ports):
        raise ValueError("Selected circuit AWGs share a tProcessor port; the existing compiler would skew their requested simultaneous timing")
    scales = [float(output_full_scales_mv[ch]) for ch in channels]
    if any(not isfinite(scale) or scale <= 0 for scale in scales):
        raise ValueError("Each circuit AWG needs its calibrated positive full-scale voltage")
    reference_mv = max(scales)
    duration_ticks = _ticks(timeline["duration_us"], tproc_mhz, "Circuit duration", positive=True)
    acq = timeline["acquisition"][0]
    acq_start = _ticks(acq["start_us"], tproc_mhz, "Acquisition start")
    sample_count = (acq["end_us"] - acq["start_us"]) * profile.sample_rate_hz / 1e6
    samples = round(sample_count)
    if samples <= 0 or not isclose(sample_count, samples, rel_tol=0, abs_tol=1e-7):
        raise ValueError(f"Acquisition duration must contain a positive whole number of samples at {profile.sample_rate_hz:g} samples/s ({profile.sample_period_us:g} us/sample)")
    register = readout_template.fpga_trigger_delay_samples
    if readout_template.fpga_trigger_delay_us is not None:
        register = profile.trigger_delay_value_for_us(readout_template.fpga_trigger_delay_us)
    if register is None:
        register = profile.selected_trigger_delay_value(None)
    fpga_delay_us = profile.trigger_delay_us_for(register)
    software_delay_ticks = (profile.software_trigger_delay_tproc_cycles(tproc_mhz)
                            if profile.software_warmup_compensation else 0)
    group_delay_us = ceil(profile.group_delay_input_samples) / profile.input_rate_mhz
    offset = (group_delay_us - fpga_delay_us) * tproc_mhz - software_delay_ticks
    if not isclose(offset, round(offset), rel_tol=0, abs_tol=1e-7):
        raise ValueError("Loaded FIR input-window offset is not representable on the tProcessor clock")
    offset = round(offset)
    startup = max(int(gens[ch].get("ramp_startup_latency_cycles", 5)) for ch in channels)
    guard_values = {int(gens[ch].get("ramp_guard_cycles", 1)) for ch in channels}
    if len(guard_values) != 1:
        raise ValueError("Circuit AWGs must have matching RAMP guard cycles")
    guard = guard_values.pop()
    pre_roll = max(startup + 6, -acq_start - offset + 3)
    rf_latencies, rf_profiles = _rf_latencies(
        soccfg, channels, timeline, rf_channel_map, rf_output_latency_tproc_cycles)
    for lane in timeline["rf"]:
        ch = _mapped(lane["channel"], rf_channel_map, "RF", gens)
        first_start = _ticks(lane["events"][0]["start_us"], tproc_mhz, "RF pulse start")
        pre_roll = max(pre_roll, rf_latencies[ch] - first_start + 3)

    # A group describes one simultaneous SET or RAMP operation. Its target is
    # resolved by the model from the preceding physical-channel voltage state.
    grouped = {}
    baseline = {r["channel"]: r["voltage_mv"] for r in document["awg_baselines"]}
    values = [float(baseline.get(row["channel"], 0.0)) for row in timeline["awg"]]
    for output, lane in enumerate(timeline["awg"]):
        for event in lane["events"]:
            start = _ticks(event["start_us"], tproc_mhz, "AWG transition start")
            ramp = _ticks(event["ramp_us"], tproc_mhz, "AWG ramp duration")
            grouped.setdefault((start, ramp), {})[output] = event["target_mv"]
    actions = sorted((start, ramp, targets) for (start, ramp), targets in grouped.items())
    for index, (start, ramp, _targets) in enumerate(actions):
        if index:
            previous_start, previous_ramp, _ = actions[index - 1]
            if start < previous_start + previous_ramp or start == previous_start:
                raise ValueError("AWG ramps must share the same start and end across outputs; staggered ramps or simultaneous SET/RAMP changes cannot be scheduled exactly by the existing compiler")

    sequence = FineTuneSequence(tuple(f"circuit_awg_{lane['channel']}" for lane in timeline["awg"]))
    sequence.set_voltage_scales(reference_mv, scales)
    sequence.output_full_scale_mv = reference_mv
    sequence.dac_current_settings = deepcopy(dict(dac_current_settings or {}))
    _configure_compensation(sequence, compensation, reference_mv, tproc_mhz)
    segment_starts = []
    logical_cursor = 0
    final_end = pre_roll + duration_ticks

    def add_hold(name, end):
        nonlocal logical_cursor
        length = end - logical_cursor
        if length < 3:
            raise ValueError("Circuit AWG SET interval is shorter than the 3-clock minimum, including the existing RAMP guard; separate the transitions")
        for output, mv in enumerate(values):
            if abs(mv) > scales[output]:
                raise ValueError(f"AWG {timeline['awg'][output]['channel']} target {mv:g} mV exceeds its calibrated full scale {scales[output]:g} mV")
        sequence.add_set(name, [mv / reference_mv for mv in values], length)
        segment_starts.append(logical_cursor)
        logical_cursor = end

    first = pre_roll + actions[0][0] if actions else final_end
    add_hold(ANCHOR, first)
    for index, (start, ramp, targets) in enumerate(actions):
        boundary = pre_roll + start
        if logical_cursor != boundary:
            raise RuntimeError("Circuit lowerer lost an AWG timing boundary")
        next_boundary = pre_roll + actions[index + 1][0] if index + 1 < len(actions) else final_end
        if ramp:
            # The backend holds the target throughout its guard clock. Remove
            # that guard from the following hold, never from the actual ramp.
            sequence.add_ramp(f"circuit_ramp_{index}", ramp)
            segment_starts.append(logical_cursor)
            logical_cursor += ramp + guard
        values = [float(targets.get(output, mv)) for output, mv in enumerate(values)]
        if index + 1 == len(actions):
            next_boundary = max(next_boundary, logical_cursor + 3)
        add_hold(f"circuit_set_{index}", next_boundary)

    templates = _rf_template_map(rf_templates)
    rf_specs = []
    used_rf_generators = set()
    for lane in timeline["rf"]:
        gen_ch = _mapped(lane["channel"], rf_channel_map, "RF", gens)
        if gen_ch in channels:
            raise ValueError("An output cannot be both a circuit AWG and RF channel")
        if gen_ch in used_rf_generators:
            raise ValueError("RF front-panel mappings must be unique")
        used_rf_generators.add(gen_ch)
        if gen_ch not in templates:
            raise ValueError(f"Configure RF {lane['channel']} in the existing RF panel to provide its attenuation/filter settings")
        if not isclose(float(gens[gen_ch]["f_fabric"]), tproc_mhz, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Circuit RF and tProcessor clocks must match for exact pulse timing")
        template = templates[gen_ch]
        items, frequencies, frequency_names = [], [], {}
        first_start = _ticks(lane["events"][0]["start_us"], tproc_mhz, "RF pulse start")
        cursor_us = first_start / tproc_mhz
        for index, event in enumerate(lane["events"]):
            start = _ticks(event["start_us"], tproc_mhz, "RF pulse start")
            duration = event["end_us"] - event["start_us"]
            rf_cycles = _ticks(duration, float(gens[gen_ch]["f_fabric"]), "RF pulse duration", positive=True)
            if rf_cycles < 3:
                raise ValueError("RF pulse duration must be at least 3 fabric clocks")
            # Existing generator uses 3-clock periodic words for long pulses;
            # stopping inside a word otherwise extends the RF pulse by 1-2 clocks.
            if rf_cycles > 65535 and rf_cycles % 3:
                raise ValueError("Long RF pulse duration must be a multiple of 3 fabric clocks to avoid periodic-word stop rounding")
            gap_us = start / tproc_mhz - cursor_us
            if gap_us > 1e-10:
                items.append(QickRfCompositeItemSpec(kind="delay", name=f"gap_{index}", duration_us=gap_us))
            frequency = event['frequency_mhz']
            if frequency not in frequency_names:
                frequency_names[frequency] = f'f{len(frequencies)}'
                frequencies.append(QickRfFrequencyParameterSpec(name=frequency_names[frequency], frequency_mhz=frequency))
            items.append(QickRfCompositeItemSpec(kind="pulse", name=f"{event['gate_id']}:RF{lane['channel']}:{index}",
                                                duration_us=duration, frequency_parameter=frequency_names[frequency],
                                                gain=event["gain"], phase_degrees=event["phase_deg"]))
            cursor_us = event["end_us"]
        rf_specs.append(QickRfPulseSpec(
            gen_ch=gen_ch, segment_name=ANCHOR,
            delay_us=(pre_roll + first_start - rf_latencies[gen_ch]) / tproc_mhz,
            duration_us=cursor_us - first_start / tproc_mhz,
            frequency_mhz=frequencies[0].frequency_mhz, gain=0,
            att1_db=template.att1_db, att2_db=template.att2_db, nqz=template.nqz,
            require_within_segment=False, filter_type=template.filter_type,
            filter_cutoff=template.filter_cutoff, filter_bandwidth=template.filter_bandwidth,
            output_board_type=template.output_board_type, pulse_mode="composite",
            frequency_parameters=tuple(frequencies), composite_items=tuple(items)))
    readout = replace(readout_template, segment_name=ANCHOR,
                      delay_us=(pre_roll + acq_start + offset) / tproc_mhz,
                      samples_per_trigger=int(samples),
                      fpga_trigger_delay_samples=register,
                      fpga_trigger_delay_us=None)
    sequence._validate()
    program = experiment.build_qick_program(
        soccfg, sequence, awg_channels=channels,
        repetitions_per_sweep=document["shots"], tproc_mhz=tproc_mhz,
        rf_specs=tuple(rf_specs), readout_spec=readout,
        compile_validation_mode=compile_validation_mode, cancel_check=cancel_check)
    program.compile()  # Enforce instruction/memory/register limits before I/O.
    capacity = int(soccfg['tprocs'][0].get('pmem_size', 0))
    if document.get('loops') and capacity <= 0:
        raise ValueError('Loop execution requires the loaded tProcessor PMEM capacity in HWH metadata.')
    if capacity > 0 and len(program.binprog) > capacity:
        raise ValueError(f'Circuit needs {len(program.binprog)} PMEM words, but loaded capacity is {capacity}; reduce loop n.')
    anchor_tick = program.timing["segment_starts"][0]
    origin_us = (anchor_tick + pre_roll) / tproc_mhz
    for requested, actual in zip(segment_starts, program.timing["segment_starts"]):
        if actual - anchor_tick != requested:
            raise ValueError("The loaded AWG compiler changed circuit segment timing")
    for entry in program.aux_timing.get("rf_pulses", ()):
        if entry["command_skew_tproc_cycles"] or entry["stop_skew_tproc_cycles"]:
            raise ValueError("A circuit RF pulse collides with another command on its shared output port; adjust its time")
    requested_rf = [event for lane in timeline["rf"] for event in lane["events"]]
    for entry, requested in zip(program.aux_timing.get("rf_pulses", ()), requested_rf):
        latency = rf_latencies[entry["gen_ch"]]
        for edge in ("start", "end"):
            actual = (entry[edge] + latency) / tproc_mhz - origin_us
            if not isclose(actual, requested[f"{edge}_us"], rel_tol=0, abs_tol=1e-8):
                raise ValueError("Compiled RF digital output timing does not match the circuit")
    # Unlike the backend's monotonic-order check, enforce the real SET dispatch
    # interval for all circuit event timestamps sharing a physical tProc port.
    by_port = {}
    for commands in program.compiled_points[0].segment_commands:
        for command in commands:
            when = program.timing["command_times"][program._timing_key(command)]
            by_port.setdefault(int(gens[command.gen_ch]["tproc_ch"]), []).append(when)
    for entry in program.aux_timing.get("rf_pulses", ()):
        times = by_port.setdefault(int(gens[entry["gen_ch"]]["tproc_ch"]), [])
        times.append(entry["start"])
        if entry["mode"] == "periodic_timed_stop":
            times.append(entry["end"])
    ro_port = int(soccfg["readouts"][readout.ro_ch]["tproc_ctrl"])
    by_port.setdefault(ro_port, []).append(program.aux_timing["ddr_readout_start"])
    for port, timestamps in by_port.items():
        timestamps.sort()
        if any(b - a < 3 for a, b in zip(timestamps, timestamps[1:])):
            raise ValueError(f"Circuit commands on tProcessor port {port} are less than 3 clocks apart; separate the transitions or use independent outputs")
    preview = program.fir_dc_timing_preview()
    for field, expected in (("group_delay_referenced_input_start_us", acq["start_us"]),
                            ("group_delay_referenced_input_end_us", acq["end_us"])):
        if not isclose(preview[field] - origin_us, expected, rel_tol=0, abs_tol=1e-8):
            raise ValueError("The compiled FIR acquisition does not match the circuit's input window")
    metadata = dict(version=1, circuit_origin_us=origin_us,
                    loops=deepcopy(timeline.get('loops', [])), expanded_gate_count=len(timeline['gates']),
                    startup_pre_roll_us=pre_roll / tproc_mhz,
                    circuit_duration_us=duration_ticks / tproc_mhz,
                    terminal_hold_extension_us=max(0, logical_cursor - final_end) / tproc_mhz,
                    tproc_mhz=tproc_mhz, awg_channels=list(channels),
                    rf_pulse_count=sum(len(spec.pulse_events) for spec in rf_specs), shots=document["shots"],
                    rf_output_latency_tproc_cycles=rf_latencies,
                    rf_output_latency_profiles=rf_profiles,
                    rf_latency_evidence="analysis_results/awg_tuning_v3/hold_acquisition_20261007/HOLD_RTL_REPORT.md; prior RF output latency 42 clocks",
                    rf_timing_scope="Profile-based RF digital-interface alignment; not a new hardware measurement, RFDC analog or cable-delay calibration.",
                    acquisition_samples=int(samples), sample_rate_hz=profile.sample_rate_hz,
                    acquisition_input_start_us=acq["start_us"], acquisition_input_end_us=acq["end_us"],
                    fir_timing=preview,
                    timing_note="FIR input bounds are group-delay referenced; continuous decimation can move a stored edge by one sample period. DAC/RF quantization is unchanged.",
                    compensation=deepcopy(dict(compensation or {})))
    return CircuitExecution(document, sequence, channels, tuple(rf_specs), readout,
                            document["shots"], program, metadata)


def _run_quantum_circuit_point(*, connection_config, run_config, document,
                                  gui_settings, readout_template,
                                  output_full_scales_mv, dac_current_settings=None,
                                  awg_channel_map=DEFAULT_AWG_CHANNEL_MAP,
                                  rf_channel_map=DEFAULT_RF_CHANNEL_MAP,
                                  compensation=None, rf_templates=None,
                                  rf_output_latency_tproc_cycles=None,
                                  compile_validation_mode="boundary",
                                  iq_storage_mode=experiment.DEFAULT_IQ_STORAGE_MODE, progress=False,
                                  connector=None, progress_callback=None,
                                  event_callback=None, cancel_check=None,
                                  _sweep_context=None, _expected_program_hash=None):
    """Connect once, preflight against live HWH, then use the existing runner."""
    if cancel_check:
        cancel_check()
    iq_storage_mode = experiment.normalize_iq_storage_mode(iq_storage_mode)
    if progress_callback:
        progress_callback(0, "Connecting and compiling Quantum Circuit")
    soc, soccfg = experiment.connect_qick(connection_config, connector=connector)
    execution = build_circuit_execution(
        document, soccfg, readout_template=readout_template,
        output_full_scales_mv=output_full_scales_mv,
        dac_current_settings=dac_current_settings, awg_channel_map=awg_channel_map,
        rf_channel_map=rf_channel_map, compensation=compensation,
        rf_templates=rf_templates,
        rf_output_latency_tproc_cycles=rf_output_latency_tproc_cycles,
        compile_validation_mode=compile_validation_mode,
        cancel_check=cancel_check)
    if _expected_program_hash is not None and _program_hash(execution) != _expected_program_hash:
        raise ValueError('Loop sweep program changed after preflight; execution stopped.')
    if _sweep_context is not None:
        execution.metadata['loop_count_sweep'] = deepcopy(_sweep_context)
    # Keep the editor snapshot for restoration, but never label its unrelated
    # waveforms, sweeps or SquarePulse settings as the executed experiment.
    snapshot = deepcopy(dict(gui_settings))
    settings = {"source": "quantum_circuit", "editor_snapshot": snapshot,
                "experiment": deepcopy(snapshot.get("experiment", {})),
                "qick": deepcopy(snapshot.get("qick", {})),
                "awg": {"outputs": build_timeline(execution.document)["awg"],
                        "sweeps": [],
                        "cross_capacitance": execution.sequence.cross_capacitance.tolist()},
                "rf_outputs": [asdict(spec) for spec in execution.rf_specs],
                "rf_readout": asdict(execution.readout_spec)}
    settings["quantum_circuit"] = execution.document
    settings["quantum_circuit_execution"] = execution.metadata
    # The connected HWH, not stale controls, supplies the compiler clock.
    settings["qick"] = dict(settings.get("qick", {}))
    settings["qick"].update(tproc_mhz=execution.metadata["tproc_mhz"],
                            fabric_mhz=execution.metadata["tproc_mhz"],
                            full_scale_mv=execution.sequence.output_full_scale_mv,
                            awg_channels=list(execution.awg_channels),
                            output_full_scales_mv=dict(zip(execution.awg_channels, execution.sequence.output_full_scales_mv)),
                            dac_current_settings=deepcopy(execution.sequence.dac_current_settings),
                            repetitions_per_sweep=execution.repetitions_per_sweep,
                            bias_t_compensation=deepcopy(dict(compensation or {})))
    if cancel_check:
        cancel_check()
    return experiment.run_qick_qcodes_experiment(
        connection_config=connection_config, run_config=run_config,
        sequence=execution.sequence, awg_channels=execution.awg_channels,
        repetitions_per_sweep=execution.repetitions_per_sweep,
        rf_specs=execution.rf_specs, readout_spec=execution.readout_spec,
        gui_settings=settings, iq_storage_mode=iq_storage_mode,
        compile_validation_mode=compile_validation_mode, progress=progress,
        connector=lambda **_kwargs: (soc, soccfg),
        progress_callback=progress_callback, event_callback=event_callback,
        cancel_check=cancel_check)


def _program_hash(execution):
    return sha256(experiment._json_text(execution.program.binprog).encode('utf-8')).hexdigest()


def run_quantum_circuit_experiment(**kwargs):
    """Run a fixed circuit or an ordered n sweep through the existing runner.

    Each n has one normal QCoDeS Run. A durable index connects every completed
    Run to its n value, including when a later point fails or is cancelled.
    All programs are preflighted before the first hardware acquisition.
    """
    inspect.signature(_run_quantum_circuit_point).bind(**kwargs)
    document = validate_document(kwargs['document'])
    loop_id, values = sweep_axis(document)
    if loop_id is None:
        return _run_quantum_circuit_point(**kwargs)
    experiment.normalize_iq_storage_mode(kwargs.get('iq_storage_mode', experiment.DEFAULT_IQ_STORAGE_MODE))
    cancel = kwargs.get('cancel_check')
    progress = kwargs.get('progress_callback')
    if cancel:
        cancel()
    soc, soccfg = experiment.connect_qick(kwargs['connection_config'], connector=kwargs.get('connector'))
    build_names = ('readout_template', 'output_full_scales_mv', 'dac_current_settings',
                   'awg_channel_map', 'rf_channel_map', 'compensation', 'rf_templates',
                   'rf_output_latency_tproc_cycles', 'compile_validation_mode', 'cancel_check')
    build_kwargs = {key: kwargs[key] for key in build_names if key in kwargs}
    hashes = []
    for index, n in enumerate(values):
        if cancel:
            cancel()
        if progress:
            progress(round(index / len(values) * 20), f'Preflight loop n={n} ({index + 1}/{len(values)})')
        execution = build_circuit_execution(point_document(document, index), soccfg, **build_kwargs)
        hashes.append(_program_hash(execution))
    del execution  # Do not retain every compiled program / waveform in memory.
    sweep_id = uuid.uuid4().hex
    database = kwargs['run_config'].resolved_database_path
    manifest_path = database.with_name(f'{database.stem}.circuit-sweep-{sweep_id}.json')
    manifest = dict(version=1, sweep_id=sweep_id, loop_id=loop_id, n_values=values,
                    shots_per_point=document['shots'], status='running', points=[],
                    circuit=document, preflight_program_sha256=hashes)

    def save_index():
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = manifest_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        temporary.replace(manifest_path)

    last_result = None
    save_index()
    try:
        for index, n in enumerate(values):
            if cancel:
                cancel()
            context = dict(sweep_id=sweep_id, loop_id=loop_id, index=index, n=n,
                           n_values=values, manifest_path=str(manifest_path))
            point_kwargs = dict(kwargs, document=point_document(document, index),
                                connector=lambda **_unused: (soc, soccfg),
                                _sweep_context=context, _expected_program_hash=hashes[index])
            if progress:
                point_kwargs['progress_callback'] = lambda percent, message, i=index, count=n: progress(
                    min(99, round(20 + 80 * (i + percent / 100) / len(values))),
                    f'n={count} ({i + 1}/{len(values)}) · {message}')
            last_result = _run_quantum_circuit_point(**point_kwargs)
            manifest['points'].append(dict(index=index, n=n, run_id=last_result.run_id,
                                           database_path=str(last_result.database_path)))
            save_index()
            last_result.detach_dataset()
        manifest['status'] = 'complete'
        save_index()
    except Exception as error:
        if last_result is not None:
            last_result.detach_dataset()
        manifest['status'] = 'cancelled' if isinstance(error, experiment.ExperimentCancelled) else 'failed'
        manifest['error'] = str(error)
        save_index()
        detail = f"Loop sweep {manifest['status']}: {len(manifest['points'])}/{len(values)} Runs saved. Index: {manifest_path}. {error}"
        if isinstance(error, experiment.ExperimentCancelled):
            raise experiment.ExperimentCancelled(detail) from error
        raise RuntimeError(detail) from error
    last_result.circuit_loop_sweep = dict(manifest, manifest_path=str(manifest_path))
    if progress:
        progress(100, f'Loop sweep complete: {len(values)} Runs saved')
    return last_result
