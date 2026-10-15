"""Opt-in RF sample-width compiler using the existing SGv6 envelope memory.

Sixteen reusable ending patterns are uploaded once. Hardware sweep pointers
select command words and exact timestamps, never a host loop or PMEM unroll.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import ceil, isclose
from numbers import Integral

import numpy as np

SAMPLES_PER_CLOCK = 16
PATTERN_SAMPLES = 128
MAX_FINE_GAIN = 16383


def samples_from_us(duration_us, fabric_mhz):
    rate = float(fabric_mhz) * SAMPLES_PER_CLOCK
    value = float(duration_us) * rate
    if not np.isfinite(value) or value <= 0:
        raise ValueError("fine RF duration must be finite and positive")
    nearest = round(value)
    # GUI values use nine decimals in microseconds. Preserve an intended
    # sample-grid point across that decimal serialization (half one display
    # unit), plus a few floating-point ULPs. Other values still round upward.
    tolerance = rate*0.5e-9 + 8*abs(float(np.spacing(value)))
    return max(1, int(nearest if abs(value-nearest) <= tolerance else ceil(value)))


@dataclass(frozen=True)
class FineDurationPlan:
    samples: int
    remainder: int
    address_offset_words: int
    start_length: int
    tail_offset: int
    tail_length: int
    busy_cycles: int
    periodic_plateau: bool = False

    @property
    def long(self):
        return self.tail_offset > 0


def plan_duration(samples):
    if isinstance(samples, bool) or not isinstance(samples, Integral) or samples < 1:
        raise ValueError("duration_samples must be a positive integer")
    samples = int(samples)
    q, r = divmod(samples, SAMPLES_PER_CLOCK)
    if q < 6:
        length = max(3, (samples + 15) // 16)
        return FineDurationPlan(samples, r, 5-q, length, 0, 3, length)
    plateau = q-3
    periodic = plateau > 65535
    if periodic:
        # A periodic word can be interrupted only at its own word boundary.
        plateau = 3*(plateau//3)
    tail_words = q-plateau
    return FineDurationPlan(samples, r, 5-tail_words, 3 if periodic else plateau,
                            plateau, tail_words + int(r > 0), (samples+15)//16, periodic)


def ending_patterns(maxv=32766):
    """Five full words, one fractional word, and two zero padding words."""
    result = []
    for remainder in range(16):
        data = np.zeros(PATTERN_SAMPLES, dtype=np.int16)
        data[:80+remainder] = int(maxv)
        result.append(data)
    return tuple(result)


class FineRfDurationProgramMixin:
    def _configure_rf_pulse(self, rf_index, rf):
        if not rf.fine_duration:
            return super()._configure_rf_pulse(rf_index, rf)
        cfg = self.soccfg['gens'][rf.gen_ch]
        if (cfg.get('type') != 'axis_signal_gen_v6' or cfg.get('samps_per_clk') != 16
                or not isclose(float(cfg['f_fabric']), self.tproc_mhz, rel_tol=1e-12)):
            raise ValueError("fine RF requires axis_signal_gen_v6, 16 samples/clock, and matching generator/tProcessor clocks")
        if cfg.get('has_dds') is not True:
            raise ValueError("fine RF requires a generator with has_dds=True")
        if rf.gen_ch in self.awg_channels:
            raise ValueError("fine RF requires a normal RF generator, not an AWG tuning channel")
        if rf.stdysel != 'zero':
            raise ValueError("fine RF requires stdysel='zero'")
        if int(cfg.get('maxv', 0)) != 32766:
            raise ValueError("fine RF requires the standard SGv6 envelope maximum 32766")
        gains = (int(rf.gain), *tuple(int(v) for v in rf.sweep_gain_codes))
        if any(abs(gain) > MAX_FINE_GAIN for gain in gains):
            raise ValueError("fine RF requires abs(gain) <= 16383, including every calibrated sweep gain")
        self._segment_index(rf.at_segment, require_set=True)
        if rf.gen_ch not in self._declared_rf_channels:
            self.declare_gen(ch=rf.gen_ch, nqz=rf.nqz)
            self._declared_rf_channels.add(rf.gen_ch)
        banks = getattr(self, '_fine_rf_pattern_banks', {})
        if rf.gen_ch not in banks:
            if self.envelopes[rf.gen_ch]['next_addr'] + 16*PATTERN_SAMPLES > int(cfg['maxlen']):
                raise ValueError("fine RF ending patterns do not fit the channel envelope memory")
            names = []
            for index, values in enumerate(ending_patterns(cfg['maxv'])):
                name = f'__fine_rf_end_{index}'
                if name in self.envelopes[rf.gen_ch]['envs']:
                    raise ValueError("reserved fine RF envelope name already exists")
                self.add_envelope(rf.gen_ch, name, idata=values)
                names.append(name)
            banks[rf.gen_ch] = tuple(names)
            self._fine_rf_pattern_banks = banks
        axis = self._rf_duration_axis(rf)
        samples = (tuple(samples_from_us(value, cfg['f_fabric']) for value in axis.points)
                   if axis is not None else (int(rf.duration_samples),))
        plans = tuple(plan_duration(value) for value in samples)
        frequency_axis = self._rf_frequency_axis(rf)
        frequency = rf.freq_mhz if frequency_axis is None else frequency_axis.points[0]
        self._rf_runtime[rf_index] = dict(
            fine=True, plans=plans, duration_axis=axis, frequency_axis=frequency_axis,
            power_axis=self._rf_power_axis(rf.gen_ch),
            freq=self._rf_frequency_word(rf, frequency), phase=self.deg2reg(rf.phase_degrees, gen_ch=rf.gen_ch),
            gain=int(rf.sweep_gain_codes[0] if rf.sweep_gain_codes else rf.gain),
            base_length_cycles=plans[0].busy_cycles, periodic=True,
        )
        # Each emitted event initializes every pulse register immediately
        # before use. Emitting these writes here again would make startup
        # latency grow with the number of composite pulses, delaying the
        # pre-existing fixed-time AWG/area-engine reset commands.

    def _build_aux_timing(self):
        fine = {index: runtime for index, runtime in self._rf_runtime.items() if runtime.get('fine')}
        # The inherited path validates the padded busy endpoint. Tail is an
        # internal continuation, not the legacy periodic stop at that endpoint.
        for runtime in fine.values():
            runtime['periodic'] = False
        try:
            super()._build_aux_timing()
        finally:
            for runtime in fine.values():
                runtime['periodic'] = True
        for index, runtime in fine.items():
            plan = runtime['plans'][0]
            start = self.aux_timing[f'rf_{index}_start']
            self.aux_timing[f'rf_{index}_fine_busy_end'] = start + plan.busy_cycles
            self.aux_timing[f'rf_{index}_end'] = start + (plan.tail_offset or 3)
            self.aux_timing[f'rf_{index}_mode'] = 'fine_envelope'

    def _build_event_timing_models(self):
        models = list(super()._build_event_timing_models())
        fine = [i for i, rf in enumerate(self.rf_pulse_configs) if rf.fine_duration]
        if not fine:
            return tuple(models)
        axes = tuple(self.sequence.sweep_axes)
        # AWG extension uses its pre-existing affine coarse-clock model. A
        # fractional carry must not silently alter that model's physical time.
        fine_axis_ids = {id(self._rf_duration_axis(self.rf_pulse_configs[i])) for i in fine}
        for axis in axes:
            if id(axis) in fine_axis_ids and getattr(axis, 'segment_length_mode', 'fixed') != 'fixed':
                raise ValueError("fine RF hardware duration sweep requires fixed segment length; extend the HOLD explicitly")
        for other in self.rf_pulse_configs:
            if other.fine_duration:
                continue
            if any(id(self._rf_duration_axis(other.gen_ch, name)) in fine_axis_ids
                   for name in other.preceding_duration_parameters):
                raise ValueError("a pulse following a fine swept duration must also enable fine RF timing")
        self._fine_rf_rows = {}
        for index in fine:
            rf = self.rf_pulse_configs[index]
            runtime = self._rf_runtime[index]
            own_axis = runtime['duration_axis']
            segment = self._segment_index(rf.at_segment)
            extension = tuple(self._extension_axis_deltas(segment, include_current=False))
            preceding = [self._rf_duration_axis(rf.gen_ch, name) for name in rf.preceding_duration_parameters]
            preceding = [axis for axis in preceding if axis is not None]
            relevant = sorted({i for i, delta in enumerate(extension) if delta and axes[i].count > 1}
                              | {axes.index(axis) for axis in preceding if axis.count > 1}
                              | ({axes.index(own_axis)} if own_axis is not None and own_axis.count > 1 else set()))
            shape = tuple(int(axes[i].count) for i in relevant)
            base = int(self.aux_timing[f'rf_{index}_start'])
            rows, details = [], []
            manager = self._gen_mgrs[rf.gen_ch]
            for selected in product(*(range(count) for count in shape)):
                coordinate = dict(zip(relevant, selected))
                point = coordinate.get(axes.index(own_axis), 0) if own_axis is not None else 0
                plan = runtime['plans'][point]
                start = base + sum(coordinate.get(i, 0)*int(delta) for i, delta in enumerate(extension))
                for axis in preceding:
                    values = tuple((samples_from_us(v, self.tproc_mhz)+15)//16 for v in axis.points)
                    start += values[coordinate.get(axes.index(axis), 0)] - values[0]
                name = self._fine_rf_pattern_banks[rf.gen_ch][plan.remainder]
                address = self.envelopes[rf.gen_ch]['envs'][name]['addr']//16 + plan.address_offset_words
                first_mode = manager.get_mode_code(length=plan.start_length,
                    mode='periodic' if plan.periodic_plateau else 'oneshot',
                    outsel='dds' if plan.long else 'product', stdysel='zero', phrst=0)
                tail_mode = manager.get_mode_code(length=plan.tail_length,
                    mode='oneshot', outsel='product', stdysel='zero', phrst=0)
                rows.append((int(start), int(first_mode), int(address), int(tail_mode),
                             int(start+plan.tail_offset), int(plan.long)))
                details.append(dict(start=int(start), tail=int(start+plan.tail_offset), active_tail=plan.long,
                                    busy_end=int(start+plan.busy_cycles), samples=plan.samples))
                latency = int(self.aux_timing.get(f'rf_{index}_output_latency', 0))
                end_deltas = self._extension_axis_deltas(segment, include_current=True)
                segment_end = int(self.timing['segment_ends'][segment]) + sum(
                    coordinate.get(i, 0)*int(delta) for i, delta in enumerate(end_deltas))
                if rf.require_within_segment and start+plan.busy_cycles+latency > segment_end:
                    raise ValueError("fine RF padded waveform exceeds its HOLD segment at a hardware sweep point")
            self._fine_rf_rows[index] = dict(axis_indices=tuple(relevant), axis_shape=shape,
                                            rows=tuple(rows), details=tuple(details))
            self._dynamic_point_end = max(getattr(self, '_dynamic_point_end', self.timing['point_end']),
                max(item['busy_end'] for item in details)+int(self.aux_timing.get(f'rf_{index}_output_latency', 0)))
            for kind, column in (('rf_start', 'start'), ('rf_stop', 'tail')):
                models.append(dict(key=('event_time', kind, index), register_name='event_time',
                    base=int(details[0][column] if kind == 'rf_start' or details[0]['active_tail'] else base+3),
                    axis_deltas=tuple(0 for _ in axes), timing_only=True, fine_event=(index, column)))
        return tuple(models)

    def _build_rf_point_table_models(self, sweep_axes):
        result = super()._build_rf_point_table_models(sweep_axes)
        for index, info in getattr(self, '_fine_rf_rows', {}).items():
            if not info['axis_indices']:
                continue
            rf = self.rf_pulse_configs[index]
            page, register = self._gen_regmap[(rf.gen_ch, 't')]
            result.append(dict(key=('rf_point_table', index, 'fine_duration'), register_name='rf_fine_duration',
                fine_row=True, row_width=6, gen_ch=rf.gen_ch, event_indices=(index,), page=int(page),
                command_register=int(register), axis_indices=info['axis_indices'], axis_shape=info['axis_shape'],
                values=tuple(value for row in info['rows'] for value in row)))
        return result

    def _build_capture_compensation_models(self, event_models):
        fields = list(super()._build_capture_compensation_models(event_models))
        fine = getattr(self, '_fine_rf_rows', {})
        if not fine or not self._overlap_dc_readout():
            return tuple(fields)
        models = list(self._capture_compensation_models)
        for index, info in fine.items():
            key = ('capture_compensation', f'rf_end_{index}')
            # Fine rf_stop is the start of its masked tail, not output end.
            # Waiting for the largest padded endpoint is conservative across
            # all hardware coordinates and also covers pulses outside HOLD.
            end = max(item['busy_end'] for item in info['details'])
            end += int(self.aux_timing.get(f'rf_{index}_output_latency', 0))
            for model in models:
                if model['key'] == key:
                    model.update(base=end, axis_deltas=tuple(0 for _ in self.sequence.sweep_axes))
            fields = [field for field in fields if field['key'] != key]
        self._capture_compensation_models = tuple(models)
        return tuple(fields)

    def _build_sweep_register_plan(self):
        super()._build_sweep_register_plan()
        for table in self._rf_point_tables:
            if table.get('fine_row'):
                table['axis_strides'] = {axis: stride*6 for axis, stride in table['axis_strides'].items()}

    def _fine_details_at(self, index, coordinates):
        info = self._fine_rf_rows[index]
        flat = 0
        for axis, size in zip(info['axis_indices'], info['axis_shape']):
            flat = flat*size+coordinates[axis]
        return info['details'][flat]

    def _validate_dynamic_event_order(self):
        if not getattr(self, '_fine_rf_rows', {}):
            return super()._validate_dynamic_event_order()
        # Legacy validation has affine timing only. Validate its unchanged
        # events first; then check every dependent coordinate with exact rows.
        for index in self._fine_rf_rows:
            self._rf_runtime[index]['periodic'] = False
        try:
            super()._validate_dynamic_event_order()
        finally:
            for index in self._fine_rf_rows:
                self._rf_runtime[index]['periodic'] = True
        models = {model['key']: model for model in self._event_timing_models}
        events = []
        for commands in self.compiled_points[0].segment_commands:
            for command in commands:
                key = ('event_time', 'awg', *self._command_key(command))
                events.append((int(self.timing['command_times'][self._timing_key(command)]), 10,
                               command.gen_ch, key, None))
        for index, rf in enumerate(self.rf_pulse_configs):
            events.append((int(self.aux_timing[f'rf_{index}_start']), 10, rf.gen_ch,
                           ('event_time', 'rf_start', index), index))
            if self._rf_runtime[index]['periodic']:
                events.append((int(self.aux_timing[f'rf_{index}_end']), 15, rf.gen_ch,
                               ('event_time', 'rf_stop', index), index))
        if self.ddr_readout_config is not None:
            ro = self.soccfg['readouts'][self.ddr_readout_config.ro_ch]
            ro_port = int(ro['tproc_ctrl'])
            representative = next((ch for ch, cfg in enumerate(self.soccfg['gens'])
                                   if int(cfg['tproc_ch']) == ro_port), None)
            if representative is not None:
                events.append((int(self.aux_timing['ddr_readout_start']), 0, representative,
                               ('event_time', 'ddr_readout'), None))
        if self.readout_config is not None:
            readout = self.readout_config
            ro_port = int(self.soccfg['readouts'][readout.ro_ch]['tproc_ctrl'])
            representative = next((ch for ch, cfg in enumerate(self.soccfg['gens'])
                                   if int(cfg['tproc_ch']) == ro_port), None)
            if representative is not None:
                when = int(self.timing['point_end'])
                if readout.at_segment is not None:
                    segment = self._segment_index(readout.at_segment)
                    reference = ('segment_starts' if readout.timing_reference == 'segment_start'
                                 else 'segment_ends')
                    when = int(self.timing[reference][segment])
                events.append((when + readout.measure_delay_tproc_cycles, 0, representative,
                               ('event_time', 'readout'), None))
        if self.sequence.bias_t_compensation is not None or self.sequence.rc_compensation is not None:
            pulse_end = int(self.timing['segment_ends'][-1]) - self.awg_output_latency_tproc
            for output, channel in enumerate(self.awg_channels):
                events.append((pulse_end + int(self._channel_slots[channel]), 30, channel,
                               ('event_time', 'bias_pre_zero', output), None))
        events.sort(key=lambda event: event[:2])
        axes = self.sequence.sweep_axes
        relevant = set(i for info in self._fine_rf_rows.values() for i in info['axis_indices'])
        relevant.update(i for model in models.values() for i, delta in enumerate(model['axis_deltas']) if delta)
        selected_axes = tuple(sorted(relevant))
        count = int(np.prod([axes[i].count for i in selected_axes], dtype=np.int64))
        if count > 1_000_000:
            raise ValueError("fine RF exact timing validation exceeds one million dependent coordinates")
        for selected in product(*(range(axes[i].count) for i in selected_axes)):
            coordinates = [0]*len(axes)
            for axis, value in zip(selected_axes, selected):
                coordinates[axis] = value
            previous = {}
            busy_by_gen = {}
            for base, _priority, channel, key, index in events:
                port = int(self.soccfg['gens'][channel]['tproc_ch'])
                if index in self._fine_rf_rows:
                    detail = self._fine_details_at(index, coordinates)
                    if key[1] == 'rf_stop' and not detail['active_tail']:
                        continue
                    timestamp = detail['start' if key[1] == 'rf_start' else 'tail']
                    if key[1] == 'rf_start':
                        if timestamp < busy_by_gen.get(channel, -1):
                            raise ValueError("fine RF padded waveform overlaps the next pulse on its generator")
                        busy_by_gen[channel] = detail['busy_end']
                else:
                    model = models.get(key)
                    timestamp = base if model is None else int(model['base']) + sum(
                        value*int(delta) for value, delta in zip(coordinates, model['axis_deltas']))
                    if index is not None and key[1] == 'rf_start':
                        if timestamp < busy_by_gen.get(channel, -1):
                            raise ValueError("fine RF padded waveform overlaps the next RF pulse")
                        rf = self.rf_pulse_configs[index]
                        duration_axis = self._rf_duration_axis(rf)
                        length = self._rf_runtime[index]['base_length_cycles']
                        if duration_axis is not None:
                            length = self._rf_duration_fabric_cycles(rf, duration_axis.points[
                                coordinates[axes.index(duration_axis)]])
                        busy_by_gen[channel] = timestamp + self._fabric_to_tproc(channel, length)
                previous_event = previous.get(port)
                if previous_event is not None:
                    old_time, old_key = previous_event
                    spacing = 3 if (key[1].startswith('rf_') or old_key[1].startswith('rf_')) else 0
                    if timestamp-old_time < spacing:
                        raise ValueError("fine RF sweep changes shared-port command order or requires commands less than 3 clocks apart")
                previous[port] = (timestamp, key)

    def _fine_load_row(self, index, rf):
        names = ('t', 'mode', 'addr', 'mode2', 'addr2', 'mode3')
        page = int(self._gen_regmap[(rf.gen_ch, 't')][0])
        table = next((table for table in self._rf_point_tables_by_event[index] if table.get('fine_row')), None)
        if table is None:
            for name, value in zip(names[:3], self._fine_rf_rows[index]['rows'][0][:3]):
                self.safe_regwi(page, self._gen_regmap[(rf.gen_ch, name)][1], value, f'fine RF {name}')
        else:
            pointer = int(table['pointer_register'])
            for column, name in enumerate(names):
                if column:
                    self.mathi(page, pointer, pointer, '+', 1)
                self.memr(page, self._gen_regmap[(rf.gen_ch, name)][1], pointer, f'load fine RF {name}')
            self.mathi(page, pointer, pointer, '+', -5, 'restore fine RF row pointer')
        return page

    def _fine_configure_event(self, index, rf):
        runtime = self._rf_runtime[index]
        page = self._fine_load_row(index, rf)
        tables = [table for table in self._rf_point_tables_by_event.get(index, ())
                  if not table.get('fine_row')]
        loaded = {int(table['command_register']) for table in tables}
        for name in ('freq', 'phase', 'gain'):
            register = int(self._gen_regmap[(rf.gen_ch, name)][1])
            if register not in loaded:
                self.safe_regwi(page, register, runtime[name], f'fine RF {name}')
        for table in tables:
            self.memr(int(table['page']), int(table['command_register']), int(table['pointer_register']),
                      f"load fine RF swept {table['register_name']}")
        return page

    def _fine_set(self, rf, page, comment, *, tail_registers=False):
        registers = [int(self._gen_regmap[(rf.gen_ch, name)][1])
                     for name in ('freq', 'phase', 'addr', 'gain',
                                  'mode2' if tail_registers else 'mode',
                                  'addr2' if tail_registers else 't')]
        self.set(int(self.soccfg['gens'][rf.gen_ch]['tproc_ch']), page, *registers, comment)

    def _emit_rf_start(self, rf_index, rf, tproc_time):
        owners = getattr(self, '_fine_register_owner', {})
        owners[rf.gen_ch] = rf_index
        self._fine_register_owner = owners
        if not rf.fine_duration:
            return super()._emit_rf_start(rf_index, rf, tproc_time)
        page = self._fine_configure_event(rf_index, rf)
        register = lambda name: int(self._gen_regmap[(rf.gen_ch, name)][1])
        kinds = {plan.long for plan in self._rf_runtime[rf_index]['plans']}
        if False in kinds:
            label = f'FINE_RF_{rf_index}_START_GAIN_READY'
            if True in kinds:
                self.condj(page, register('mode3'), '!=', 0, label, 'DDS plateau keeps original gain')
            self.bitwi(page, register('gain'), register('gain'), '<<', 1, 'compensate product envelope scaling')
            if True in kinds:
                self.label(label)
        self._fine_set(rf, page, 'fine RF start')

    def _emit_rf_stop(self, rf_index, rf, tproc_time):
        if not rf.fine_duration:
            getattr(self, '_fine_register_owner', {}).pop(rf.gen_ch, None)
            return super()._emit_rf_stop(rf_index, rf, tproc_time)
        kinds = {plan.long for plan in self._rf_runtime[rf_index]['plans']}
        if True not in kinds:
            return
        if getattr(self, '_fine_register_owner', {}).get(rf.gen_ch) != rf_index:
            raise ValueError("fine RF tail register state was overwritten by another pulse on its generator")
        page = int(self._gen_regmap[(rf.gen_ch, 't')][0])
        register = lambda name: int(self._gen_regmap[(rf.gen_ch, name)][1])
        label = f'FINE_RF_{rf_index}_TAIL_DONE'
        if False in kinds:
            self.condj(page, register('mode3'), '==', 0, label, 'short fine RF has no second command')
        # Same-generator overlap is rejected before code emission; other
        # generators/readouts use distinct reserved registers. Therefore the
        # start's carrier, gain, and ending-pattern address remain available.
        self.bitwi(page, register('gain'), register('gain'), '<<', 1, 'compensate product envelope scaling')
        dynamic = bool(self._fine_rf_rows[rf_index]['axis_indices'])
        if not dynamic:
            row = self._fine_rf_rows[rf_index]['rows'][0]
            self.safe_regwi(page, register('mode'), row[3], 'fine RF tail mode')
            self.safe_regwi(page, register('t'), row[4], 'fine RF tail time')
        self._fine_set(rf, page, 'fine RF ending pattern', tail_registers=dynamic)
        if False in kinds:
            self.label(label)
            self.mathi(page, register('mode3'), register('mode3'), '+', 0, 'fine RF tail complete')

    def summary(self):
        result = super().summary()
        fine = []
        for index, rf in enumerate(self.rf_pulse_configs):
            if not rf.fine_duration:
                continue
            runtime = self._rf_runtime[index]
            rate = float(self.soccfg['gens'][rf.gen_ch]['f_fabric'])*16
            fine.append(dict(event_id=rf.event_id, gen_ch=rf.gen_ch, duration_parameter=rf.duration_parameter,
                duration_samples=tuple(plan.samples for plan in runtime['plans']),
                actual_duration_us=tuple(plan.samples/rate for plan in runtime['plans']),
                sample_period_ns=1000/rate, samples_per_clock=16,
                busy_cycles=tuple(plan.busy_cycles for plan in runtime['plans']),
                pattern_count=16, pattern_samples=128, envelope_samples_per_channel=2048,
                hardware_sweep=True, pmem_unrolled=False, maximum_absolute_gain=MAX_FINE_GAIN,
                amplitude_scaling='DDS plateau gain; product ending pattern uses twice gain with integer truncation',
                timing_scope='sample-granular width; starts remain generator-fabric-clock aligned',
                duration_quantization='ceil to sample; snap grid points within half 1e-9 us display precision plus floating-point ULPs',
                row_axis_indices=self._fine_rf_rows[index]['axis_indices']))
        if fine:
            result['rf_fine_duration'] = tuple(fine)
        return result
