"""Pure v7 RAMP encoder; no hardware access and no floating time rounding.

Indices are DAC sample positions relative to the first output word. An edge
includes both endpoints: an edge from index 2 to 7 has FIVE intervals.
Legacy RAMPs keep their existing 23-bit sample-count/32-bit Q18 ABI.
"""
from numbers import Integral

FRAC = 18
NO_FALL = 0b11111
MAX_SAMPLES = (1 << 23) - 1


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    value = int(value)
    if not low <= value <= high:
        raise ValueError(f"{name} must be in [{low}, {high}]")
    return value


def code(value, name):
    value = integer(value, name, -32768, 32764)
    if value % 4:
        raise ValueError(f"{name} must be an effective DAC code (multiple of 4)")
    return value


def edge_step(start, target, intervals):
    """Round away from zero; bound to target in RTL, never add an end jump."""
    if intervals == 0:
        if start != target:
            raise ValueError("A nonzero edge needs at least one sample interval")
        return 0
    delta = (target - start) << FRAC
    return (1 if delta >= 0 else -1) * ((abs(delta) + intervals - 1) // intervals)


def ramp_packet(*, start, target, rise_start, rise_end, fall_start=None,
                fall_end=None, end_target=None, tmux=0):
    """Return packet and reservation for one two-edge or one-edge RAMP.

    rise_start is a lane (0..15). fall_start is a complete sample index;
    it is split into a coarse word and fine lane. None encodes 11111 and
    ignores the second slope. This avoids treating lane 15 as a sentinel.
    Falling may cross any number of words until fall_end (up to ABI limit).
    An inverted/negative pulse is supported: direction follows its targets.
    """
    start, target = code(start, "start"), code(target, "target")
    r0 = integer(rise_start, "rise_start", 0, 15)
    r1 = integer(rise_end, "rise_end", r0, MAX_SAMPLES - 1)
    tmux = integer(tmux, "tmux", 0, 255)
    up = edge_step(start, target, r1 - r0)
    if fall_start is None:
        if fall_end is not None or end_target is not None:
            raise ValueError("No falling edge: omit fall_end and end_target")
        lane, coarse, down, endpoint, last = NO_FALL, 0, 0, target, r1
    else:
        f0 = integer(fall_start, "fall_start", r1, (1 << 14) - 1)
        f1 = integer(fall_end, "fall_end", f0, MAX_SAMPLES - 1)
        endpoint = code(end_target, "end_target")
        lane, coarse = f0 % 16, f0 // 16
        down = edge_step(target, endpoint, f1 - f0)
        last = f1
    for name, step in (("rise_step", up), ("fall_step", down)):
        integer(step, name, -(1 << 34), (1 << 34) - 1)
    duration = last + 1
    word = ((target & 0xffff) | ((endpoint & 0xffff) << 16)
            | ((up & ((1 << 35) - 1)) << 32)
            | ((down & ((1 << 35) - 1)) << 67)
            | (r0 << 102) | (lane << 106) | (duration << 111)
            | (coarse << 134) | (2 << 144) | (1 << 151) | (tmux << 152))
    return dict(word=word, words=[(word >> (32*i)) & 0xffffffff for i in range(5)],
                duration_samples=duration, reservation_cycles=(duration+15)//16,
                rise_step=up, fall_step=down, terminal=endpoint,
                rise_start=r0, rise_end=r1, fall_start=fall_start, fall_end=fall_end)
