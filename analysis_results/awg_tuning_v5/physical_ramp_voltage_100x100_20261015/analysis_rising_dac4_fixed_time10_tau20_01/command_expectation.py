"""Verification-only actual-command -> compact RC-DAC expectation adapter.

API: model = output_model(expected_point['outputs'][axis]); then
model.at_program_us(sample_time_us - one_global_scope_offset_us).
No per-point shifts/fits and no instrument calls. A model is a digital shot,
not a fresh physical capacitor. This predicts direct DAC voltage only.
"""
from dataclasses import dataclass
import gzip
import json
import math
from pathlib import Path

from compact_expectation import Run, Waveform, clamp, compensation_runs


def load_expected(path):
    """Load the one retained JSON or lossless gzip JSON evidence artifact."""
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf8') as stream:
        return json.load(stream)


def signed32(value):
    value &= (1 << 32) - 1
    return value - (1 << 32) if value >= (1 << 31) else value


@dataclass(frozen=True)
class OutputModel:
    waveform: Waveform
    origin_scalar: int
    scalar_mhz: float
    full_scale_mv: float
    coefficient: int
    pre_dc_area: int
    dc_start_scalar: int
    dc_end_scalar: int
    metadata_step_mismatches: tuple

    def at_program_us(self, time_us):
        # The caller supplies one globally aligned program time. Native scalar
        # samples are zero-order held; no interpolation of the command stream.
        index = math.floor(float(time_us) * self.scalar_mhz) - self.origin_scalar
        raw = self.waveform.raw_at(index)
        corrected = self.waveform.rc_effective_at(index, self.coefficient)
        corrected_q48 = ((4 * raw << 48)
                         + 4 * self.coefficient * (raw + 2 * self.waveform.prefix(index)))
        return dict(program_time_us=float(time_us), relative_scalar_index=index,
                    nominal_code=raw, rc_dac_code=corrected,
                    nominal_mv=raw * self.full_scale_mv / 8192,
                    expected_direct_dac_mv=corrected * self.full_scale_mv / 8192,
                    unclipped_direct_dac_mv=corrected_q48 * self.full_scale_mv / (32768 * (1 << 48)),
                    rtl_clipped_at_sample=((corrected_q48 >> 48) > 32764
                                           or (corrected_q48 >> 48) < -32768))


def output_model(output, *, native_latency_cycles=31, ramp_startup_cycles=7,
                 fabric_mhz=300., samples_per_clock=16, frac=18):
    """Build from actual 160-bit command words, verify exported exact area.

    The original command word is authoritative; decoded helper metadata is
    audited and mismatches are returned explicitly. No mismatch is silently
    converted into evidence that the metadata or physical execution passed.
    """
    if fabric_mhz != 300. or samples_per_clock != 16:
        raise ValueError('This adapter is scoped to the verified v5 300 MHz / 16 lanes')
    commands = output['commands']
    origin = (int(commands[0]['cycle']) + native_latency_cycles) * samples_per_clock
    cursor = origin
    current_transport = 0
    runs = []
    mismatches = []

    def hold_until(end):
        nonlocal cursor
        if end < cursor:
            raise ValueError('Actual command ordering overlaps an active RAMP')
        if end > cursor:
            runs.append(Run(end - cursor, code=clamp(current_transport >> 2)))
        cursor = end

    for i, command in enumerate(commands):
        word = int(command['word'], 16)
        opcode = (word >> 144) & 3
        target = signed32(word)
        step = signed32(word >> 96)
        count = (word >> 64) & ((1 << 23) - 1)
        assert opcode == command['opcode']
        assert target == command['transport_target']
        assert count == command['duration_samples']
        if int(command.get('step_signed', step)) != step:
            mismatches.append(dict(command=i, metadata_step=command['step_signed'], actual_word_step=step))
        start = (int(command['cycle']) + native_latency_cycles) * samples_per_clock
        if opcode == 1:
            hold_until(start)
            # This campaign uses persistent SET, never one-word hold_zero.
            if (word >> 146) & 1:
                raise ValueError('Unexpected hold_zero SET requires separate timing model')
            current_transport = target
        elif opcode == 2:
            start += ramp_startup_cycles * samples_per_clock
            hold_until(start)
            count = max(1, count)
            runs.append(Run(count, kind='ramp', start_transport=current_transport,
                            target_transport=target, step=step, frac=frac))
            cursor += count
            current_transport = target
            padding = (-count) % samples_per_clock
            hold_until(cursor + padding)
        else:
            raise ValueError('Only SET/RAMP commands belong in the body stream')

    assert current_transport == 0, 'Compiler must return raw output to zero before DC'
    dc_word = int(output['dc_command_word'], 16)
    assert (dc_word >> 150) & 1 and not ((dc_word >> 149) & 1)
    assert (dc_word >> 144) & 3 == 3
    action = (dc_word >> 146) & 3
    dc_latency = 17 + native_latency_cycles - 5
    dc_start = (int(output['dc_command_cycle']) + dc_latency) * samples_per_clock
    hold_until(dc_start)
    body = Waveform(runs)
    assert body.area == int(output['pre_dc_area_effective_code_samples']), (
        body.area, output['pre_dc_area_effective_code_samples'])
    if action == 1:
        dc_runs = compensation_runs(body.area, amplitude_transport=dc_word & 0xffffffff)
    elif action == 2:
        words = (dc_word >> 64) & 0xffffffff
        assert dc_word & ((1 << 64) - 1) == (1 << 64) // (samples_per_clock * words)
        dc_runs = compensation_runs(body.area, words=words)
    else:
        raise ValueError('Unknown DC compensation command')
    assert [(r.count, r.code) for r in dc_runs] == [tuple(r) for r in output['dc_runs_effective14']]
    words = sum(r.count for r in dc_runs) // samples_per_clock
    assert words == output['dc_duration_cycles']
    dc_end = dc_start + words * samples_per_clock
    scalar_mhz = fabric_mhz * samples_per_clock
    assert math.isclose(dc_start / scalar_mhz, output['dc_start_digital_output_us'], abs_tol=1e-8)
    assert math.isclose(dc_end / scalar_mhz, output['dc_end_digital_output_us'], abs_tol=1e-8)
    balanced = Waveform(runs + dc_runs + [Run(32)])
    assert balanced.area == 0
    assert balanced.rc_effective_at(balanced.samples - 1, output['rc_coefficient']) == 0
    return OutputModel(balanced, origin, scalar_mhz, float(output['full_scale_mv']),
                       int(output['rc_coefficient']), body.area, dc_start, dc_end, tuple(mismatches))
