"""Per-converter RFDC current control exposed through the QICK RPC server."""
import math


def _dc_generator(gen):
    return (str(gen.get('type', '')).startswith(('axis_awg_tuning', 'axis_square_pulse'))
            or gen.get('gen_type') in ('awg_tuning', 'square_pulse'))


def _summed_awg_output(generators):
    """Recognize only two consistently versioned HWH-linked AWG/RF inputs."""
    if len(generators) != 2:
        return False
    by_role = {g.get('output_sum_role'): g for _, g in generators}
    if set(by_role) != {'awg', 'rf'}:
        return False
    awg, rf = by_role['awg'], by_role['rf']
    return (_dc_generator(awg) and rf.get('type') == 'axis_signal_gen_v6'
            and bool(awg.get('output_sum_block'))
            and awg.get('output_sum_version') in (1, 2, 3, 7)
            and all(g.get('output_sum_version') == awg['output_sum_version']
                    and g.get('output_sum_bypass') is False
                    and g.get('output_sum_block') == awg['output_sum_block']
                    and g.get('output_sum_awg') == awg.get('fullpath')
                    and g.get('output_sum_rf') == rf.get('fullpath')
                    for g in (awg, rf)))


class DacCurrentControl:
    def get_dac_current_settings(self):
        """Read current for DC outputs, including an HWH-verified AWG/RF sum."""
        grouped = {}
        for channel, gen in enumerate(self['gens']):
            dac = str(gen['dac'])
            grouped.setdefault(dac, []).append((channel, gen))
        result = {}
        for dac, generators in grouped.items():
            dc = all(_dc_generator(g) for _, g in generators) or _summed_awg_output(generators)
            record = dict(converter_id=dac, channels=[ch for ch, _ in generators],
                          dc_output=dc, adjustable=False, current_ua=None,
                          min_current_ua=6425, max_current_ua=32000, reason='')
            try:
                tile, block = map(int, dac)
                hardware = self.rf.dac_tiles[tile].blocks[block]
                if int(self.rf.cfg.get('ip_type', -1)) < 2:
                    raise RuntimeError('Current control requires a Gen 3/DFE RFDC')
                try:
                    current = hardware.OutputCurr
                except TypeError:
                    # Older PYNQ declares an int pointer for a u32 C API.
                    import xrfdc
                    value = xrfdc._ffi.new('u32 *')
                    hardware._call_function_implicit('GetOutputCurr', value)
                    current = value[0]
                record['current_ua'] = int(current)
                record['full_scale_mv'] = float(current) * 800.0 / 20000.0
                if not dc:
                    record['reason'] = 'RF or shared RF generator: current is read-only'
                elif int(hardware.DACCompMode) != 0:
                    record['reason'] = 'VOP disabled (legacy DAC mode); VOP requires DAC_AVTT = 3.0 V'
                else:
                    record['adjustable'] = callable(getattr(hardware, 'SetDACVOP', None))
                    if not record['adjustable']:
                        record['reason'] = 'The board xrfdc driver does not provide SetDACVOP'
            except Exception as exc:
                record['reason'] = str(exc)
            result[dac] = record
        return result

    def set_dac_current(self, converter_id, current_ua):
        """Set one DC DAC and return actual quantized hardware readback.

        Never enable compatibility/VOP mode or change the board supply here.
        """
        dac = str(converter_id)
        value = float(current_ua)
        if not math.isfinite(value) or value != int(value):
            raise ValueError('DAC current must be an integer number of microamps')
        records = self.get_dac_current_settings()
        if dac not in records:
            raise ValueError('Unmapped DAC converter')
        record = records[dac]
        if not record['adjustable']:
            raise ValueError(record['reason'] or 'DAC current is read-only')
        if not record['min_current_ua'] <= value <= record['max_current_ua']:
            raise ValueError('DC DAC current must be between 6425 and 32000 uA')
        tile, block = map(int, dac)
        self.rf.dac_tiles[tile].blocks[block].SetDACVOP(int(value))
        return self.get_dac_current_settings()
