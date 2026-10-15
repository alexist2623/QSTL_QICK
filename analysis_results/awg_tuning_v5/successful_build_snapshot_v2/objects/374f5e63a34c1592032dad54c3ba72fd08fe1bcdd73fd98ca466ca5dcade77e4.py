"""Shared DAC current state, independent of the selected experiment tab."""
from copy import deepcopy
import math
from PyQt5 import QtCore

REFERENCE_CURRENT_UA = 20000
REFERENCE_FULL_SCALE_MV = 800.0


def full_scale_mv(current_ua):
    current = float(current_ua)
    if not math.isfinite(current) or current <= 0:
        raise ValueError('DAC current must be positive and finite')
    return REFERENCE_FULL_SCALE_MV * current / REFERENCE_CURRENT_UA


def read_current_settings(soc):
    reader = getattr(soc, 'get_dac_current_settings', None)
    if not callable(reader):
        return {}
    return dict(reader())


def verify_current_settings(soc, settings):
    """Never execute codes compiled for a different hardware current."""
    if not settings:
        return
    actual = read_current_settings(soc)
    for dac, expected in settings.items():
        record = actual.get(str(dac), {})
        if record.get('current_ua') != expected['current_ua']:
            raise RuntimeError(f'DAC {dac} current changed or cannot be read. '
                               'Refresh the front panel and compile again.')
        if not record.get('dc_output'):
            raise RuntimeError(f'DAC {dac} is no longer connected exclusively to DC generator IPs')
        if sorted(record.get('channels', ())) != sorted(expected.get('channels', ())):
            raise RuntimeError(f'DAC {dac} generator routing changed; identify QICK and compile again')


class DacCurrentState(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = {}

    def update(self, records):
        self.records = deepcopy(dict(records))
        self.changed.emit()

    def for_channel(self, channel):
        return next((v for v in self.records.values()
                     if int(channel) in v.get('channels', ())), None)

    def scale(self, channel):
        record = self.for_channel(channel)
        if record and record.get('dc_output') and record.get('current_ua') is not None:
            return full_scale_mv(record['current_ua'])
        return REFERENCE_FULL_SCALE_MV

    def snapshot(self, channels):
        wanted = set(map(int, channels))
        for record in self.records.values():
            if wanted.intersection(record.get('channels', ())) and record.get('dc_output') and record.get('current_ua') is None:
                raise ValueError('DAC current could not be read; identify QICK again before output')
        return {dac: deepcopy(record) for dac, record in self.records.items()
                if wanted.intersection(record.get('channels', ()))
                and record.get('dc_output') and record.get('current_ua') is not None}
