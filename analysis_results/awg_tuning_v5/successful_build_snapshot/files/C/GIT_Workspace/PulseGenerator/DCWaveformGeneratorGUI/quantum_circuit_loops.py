"""Bounded circuit block repetition, shared by the preview and QICK lowerer."""
from copy import deepcopy
from hashlib import sha256
import math

MAX_LOOPS = 64
MAX_EXPANDED_GATES = 4096
MAX_EXPANDED_ACTIONS = 16384
MAX_SWEEP_POINTS = 1000


def _model():
    try:
        from . import quantum_circuit_model as model
    except ImportError:
        import quantum_circuit_model as model
    return model


def sweep_values(sweep):
    """An inclusive, exact integer range; no rounded or duplicated n values."""
    m = _model()
    row = m._object(sweep, 'Loop sweep', ('start', 'stop', 'step'))
    start = m._integer(row['start'], 'Sweep start n', 0, 1_000_000)
    stop = m._integer(row['stop'], 'Sweep stop n', 0, 1_000_000)
    step = m._integer(row['step'], 'Sweep step', -1_000_000, 1_000_000)
    if not step or (stop - start) * step < 0 or (stop - start) % step:
        raise ValueError('Loop sweep step must reach stop exactly in the selected direction.')
    size = (stop - start) // step + 1
    if size > MAX_SWEEP_POINTS:
        raise ValueError(f'Loop sweep supports at most {MAX_SWEEP_POINTS} points.')
    return list(range(start, stop + (1 if step > 0 else -1), step))


def normalize_loops(raw, gates):
    m = _model()
    by_id = {g['id']: g for g in gates}
    loops, ids, spans = [], set(), []
    for row in m._list(raw, 'Loops', MAX_LOOPS):
        row = m._object(row, 'Loop', ('id', 'name', 'gate_ids', 'count'), ('sweep',))
        identifier = m._text(row['id'], 'Loop ID')
        if identifier in ids:
            raise ValueError('Duplicate loop ID.')
        ids.add(identifier)
        selected = [m._text(x, 'Loop gate ID') for x in m._list(row['gate_ids'], 'Loop gates', m.MAX_GATES, 1)]
        if len(set(selected)) != len(selected) or not set(selected) <= by_id.keys():
            raise ValueError('Loop must refer to distinct existing gates.')
        start = min(by_id[x]['start_us'] for x in selected)
        end = max(by_id[x]['start_us'] + by_id[x]['duration_us'] for x in selected)
        # A loop repeats a global time interval, including all simultaneous gates.
        # Requiring the complete block avoids implicit changes to other qubits.
        for gate in gates:
            if (gate['id'] not in selected
                    and m._exceeds(end, gate['start_us'])
                    and m._exceeds(gate['start_us'] + gate['duration_us'], start)):
                raise ValueError('Select every gate in the loop time interval, including simultaneous gates.')
        count = m._integer(row['count'], 'Loop count n', 0, 1_000_000)
        sweep = row.get('sweep')
        if sweep is not None:
            sweep_values(sweep)
            sweep = dict(sweep)
        loops.append(dict(id=identifier, name=m._text(row['name'], 'Loop name'),
                          gate_ids=selected, count=count, sweep=sweep))
        spans.append((start, end, identifier))
    m._check_overlaps({'blocks': spans}, 'Loop')
    if sum(row['sweep'] is not None for row in loops) > 1:
        raise ValueError('Enable n sweep on one loop at a time.')
    # Bound the largest possible preview/program before allocating copies.
    for use_sweep_max in (False, True):
        gate_count, actions = len(gates), sum(len(g['awg']) + len(g['rf']) + (g['acquisition'] is not None) for g in gates)
        for row in loops:
            count = max(sweep_values(row['sweep'])) if use_sweep_max and row['sweep'] else row['count']
            gate_count += (count - 1) * len(row['gate_ids'])
            actions += (count - 1) * sum(len(by_id[x]['awg']) + len(by_id[x]['rf']) + (by_id[x]['acquisition'] is not None) for x in row['gate_ids'])
        if gate_count > MAX_EXPANDED_GATES or actions > MAX_EXPANDED_ACTIONS:
            raise ValueError(f'Expanded loop exceeds {MAX_EXPANDED_GATES} gates or {MAX_EXPANDED_ACTIONS} pulse settings; reduce n.')
    return loops


def _expand_validated(document):
    """Expand a normalized document; relative voltage values are left relative."""
    gates = document['gates']
    loops = document.get('loops', [])
    if not loops:
        return dict(gates=gates, origins={}, regions=[])
    by_id = {g['id']: g for g in gates}
    ordered = []
    for row in loops:
        selected = [by_id[x] for x in row['gate_ids']]
        start = min(g['start_us'] for g in selected)
        end = max(g['start_us'] + g['duration_us'] for g in selected)
        ordered.append((start, end, row, selected))
    ordered.sort(key=lambda item: item[0])
    expanded, origins, regions, member_ids = [], {}, [], set()
    shift = 0.
    for start, end, row, selected in ordered:
        period = end - start
        physical_start = start + shift
        physical_end = physical_start + period * row['count']
        if not math.isfinite(physical_end):
            raise ValueError('Expanded loop time is not finite.')
        regions.append(dict(id=row['id'], name=row['name'], count=row['count'],
                            start_us=physical_start, end_us=physical_end, period_us=period))
        member_ids.update(row['gate_ids'])
        for repetition in range(row['count']):
            for gate in selected:
                copy = deepcopy(gate)
                copy['id'] = 'loop:' + sha256(f"{row['id']}\0{repetition}\0{gate['id']}".encode()).hexdigest()[:32]
                copy['start_us'] = physical_start + repetition * period + (gate['start_us'] - start)
                origins[copy['id']] = gate['id']
                expanded.append(copy)
        shift += period * (row['count'] - 1)
    for gate in gates:
        if gate['id'] in member_ids:
            continue
        copy = deepcopy(gate)
        copy['start_us'] += sum((end - start) * (row['count'] - 1)
                                for start, end, row, _ in ordered
                                if not _model()._exceeds(end, gate['start_us']))
        expanded.append(copy)
    if len({g['id'] for g in expanded}) != len(expanded):
        raise ValueError('Expanded loop instance ID collides with a gate ID.')
    for gate in expanded:
        if gate['start_us'] < 0 or not math.isfinite(gate['start_us']):
            raise ValueError('Expanded gate start must be finite and nonnegative.')
        _model()._end(gate['start_us'], gate['duration_us'], 'Expanded gate')
    duration = max((g['start_us'] + g['duration_us'] for g in gates), default=0.) + shift
    if not math.isfinite(duration):
        raise ValueError('Expanded circuit duration is not finite.')
    return dict(gates=expanded, origins=origins, regions=regions, duration_us=duration)


def sweep_axis(document):
    for loop in document.get('loops', []):
        if loop.get('sweep') is not None:
            return loop['id'], sweep_values(loop['sweep'])
    return None, []


def point_document(document, index):
    doc = _model().validate_document(document)
    identifier, values = sweep_axis(doc)
    if identifier is None:
        if index != 0:
            raise ValueError('Circuit has no n sweep.')
        return doc
    _model()._integer(index, 'Sweep point index', 0, len(values) - 1)
    for row in doc['loops']:
        if row['id'] == identifier:
            row['count'] = values[index]
            row['sweep'] = None
    return _model().validate_document(doc)
