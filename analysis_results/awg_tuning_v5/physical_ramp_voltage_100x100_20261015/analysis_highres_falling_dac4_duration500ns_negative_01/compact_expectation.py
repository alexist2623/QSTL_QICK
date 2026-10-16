"""Verification-only compact DAC expectation, no board/production imports.

The input is the actual pre-RC effective-14-bit scalar stream represented as
constant runs and fixed-point ramps. Timing/commands are supplied externally;
this module does not infer or shift command timestamps. One Waveform is one
digital reset epoch. RC state is NOT an external physical capacitor state.
"""
from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random

FRAC_RC = 48
LOWER = -8192
UPPER = 8191


def clamp(code):
    return min(UPPER, max(LOWER, int(code)))


def floor_sum(n, m, a, b):
    """Exact sum floor((a*k+b)/m), k=0..n-1; signed a/b allowed."""
    if n < 0 or m <= 0:
        raise ValueError('Invalid floor-sum range')
    answer = 0
    while True:
        qa, a = divmod(a, m)
        qb, b = divmod(b, m)
        answer += qa * n * (n - 1) // 2 + qb * n
        top = a * n + b
        if top < m:
            return answer
        n, b = divmod(top, m)
        a, m = m, a


def clipped_floor_sum(n, m, a, b):
    """Exact saturated effective-code sum, no per-sample allocation."""
    if n <= 0:
        return 0
    if a < 0:
        b += a * (n - 1)
        a = -a
    if not a:
        return n * clamp(b // m)

    def first_at_least(code):
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if (a * mid + b) // m >= code:
                hi = mid
            else:
                lo = mid + 1
        return lo

    lo = first_at_least(LOWER)
    hi = first_at_least(UPPER + 1)
    return lo * LOWER + floor_sum(hi - lo, m, a, b + lo * a) + (n - hi) * UPPER


@dataclass(frozen=True)
class Run:
    count: int
    kind: str = 'constant'
    code: int = 0
    start_transport: int = 0
    target_transport: int = 0
    step: int = 0
    frac: int = 18

    def __post_init__(self):
        if self.count < 1 or self.kind not in ('constant', 'ramp'):
            raise ValueError('A run needs a positive count and a known kind')
        if self.kind == 'constant' and self.code != clamp(self.code):
            raise ValueError('Constant input must already be a valid effective DAC code')

    def at(self, index):
        if not 0 <= index < self.count:
            raise IndexError(index)
        if self.kind == 'constant':
            return self.code
        # The core forces the final sample to its target; padding is separate.
        if index == self.count - 1:
            return clamp(self.target_transport >> 2)
        return clamp(((self.start_transport << self.frac) + self.step * index) >> (self.frac + 2))

    def prefix(self, count):
        """Sum of the first count samples (exclusive endpoint)."""
        if not 0 <= count <= self.count:
            raise IndexError(count)
        if self.kind == 'constant':
            return self.code * count
        n = min(count, self.count - 1)
        result = clipped_floor_sum(n, 1 << (self.frac + 2), self.step,
                                   self.start_transport << self.frac)
        if count == self.count:
            result += clamp(self.target_transport >> 2)
        return result


class Waveform:
    """A compact exact pre-RC stream within one reset epoch, initial zero."""
    def __init__(self, runs):
        self.runs = tuple(runs)
        self.ends = []
        self.areas = [0]
        samples = 0
        for run in self.runs:
            samples += run.count
            self.ends.append(samples)
            self.areas.append(self.areas[-1] + run.prefix(run.count))
        self.samples = samples
        self.area = self.areas[-1]

    def raw_at(self, index):
        if index < 0 or index >= self.samples:
            return 0
        r = bisect_right(self.ends, index)
        start = self.ends[r - 1] if r else 0
        return self.runs[r].at(index - start)

    def prefix(self, count):
        if count <= 0:
            return 0
        if count >= self.samples:
            return self.area
        r = bisect_right(self.ends, count)
        start = self.ends[r - 1] if r else 0
        return self.areas[r] + self.runs[r].prefix(count - start)

    def rc_effective_at(self, index, coefficient):
        """Exact RC quantization at one scalar sample; initial raw/history zero.

        Let u be effective codes (transport x=4u). The trapezoidal integral
        at n is 4*C*(u[n]+2*sum(u[0:n])). No global 4.8 GHz array is needed.
        The helper rejects accumulator overflow instead of approximating its
        path-dependent saturation. This campaign is bounded far below it.
        """
        if index < 0:
            return 0
        u = self.raw_at(index)
        transport_integral_q48 = 4 * coefficient * (u + 2 * self.prefix(index))
        if not -(1 << 71) <= transport_integral_q48 < (1 << 71):
            raise OverflowError('RC integral saturation requires a sequential model')
        corrected_q48 = (4 * u << FRAC_RC) + transport_integral_q48
        if not -(1 << 71) <= corrected_q48 < (1 << 71):
            raise OverflowError('RC corrected saturation requires a sequential model')
        # Effective-code nearest rounding, exact half ties toward +infinity.
        return clamp((corrected_q48 + (1 << 49)) >> 50)


def compensation_runs(area, *, amplitude_transport=None, words=None):
    """Independent exact integer-area tail construction, before the RC filter."""
    if (amplitude_transport is None) == (words is None):
        raise ValueError('Choose one compensation mode')
    sign = -1 if area > 0 else 1
    magnitude = abs(int(area))
    if words is not None:
        if words < 1:
            raise ValueError('Positive fixed word count required')
        count = 16 * words
        q, r = divmod(magnitude, count)
        values = [(r, sign * (q + 1)), (count - r, sign * q)]
    else:
        if not 4 <= amplitude_transport <= 32764 or amplitude_transport % 4:
            raise ValueError('Aligned positive transport amplitude required')
        amplitude = amplitude_transport // 4
        q, r = divmod(magnitude, amplitude)
        count = q + bool(r)
        words = max(1, (count + 15) // 16)
        values = [(q, sign * amplitude), (int(bool(r)), sign * r), (words * 16 - count, 0)]
    runs = [Run(n, code=value) for n, value in values if n]
    assert area + sum(r.prefix(r.count) for r in runs) == 0
    return runs


def self_check():
    """Short scalar recurrence crosscheck; no hardware or production imports."""
    rng = random.Random(20261015)
    coefficient = round(2**48 / (2 * 100 * 4800))
    prefixes = 0
    outputs = 0
    ledgers = 0
    for case in range(120):
        count = rng.randrange(1, 800)
        run = Run(count, kind='ramp', start_transport=rng.randrange(-40000, 40000),
                  target_transport=rng.randrange(-40000, 40000), step=rng.randrange(-2**28, 2**28))
        scalar = [run.at(i) for i in range(count)]
        for n in (0, 1, count // 2, max(0, count - 1), count):
            assert run.prefix(n) == sum(scalar[:n])
            prefixes += 1
        runs = [Run(16, code=0), run, Run(27, code=rng.randrange(-1000, 1000)), Run(16, code=0)]
        wave = Waveform(runs)
        for mode in ('voltage', 'time'):
            tail = compensation_runs(wave.area, **({'amplitude_transport': 12000} if mode == 'voltage' else {'words': 1000}))
            balanced = Waveform(runs + tail + [Run(32)])
            assert balanced.area == 0
            ledgers += 1
            previous = integral = 0
            for i in range(balanced.samples):
                raw = 4 * balanced.raw_at(i)
                integral += coefficient * (raw + previous)
                previous = raw
                expected = clamp(((raw << 48) + integral + (1 << 49)) >> 50)
                assert balanced.rc_effective_at(i, coefficient) == expected
                outputs += 1
            assert integral == 0
    return dict(passed=True, cases=120, prefix_checks=prefixes, sample_output_checks=outputs,
                exact_area_balancing_checks=ledgers, tau_us=100, scalar_mhz=4800,
                coefficient=coefficient, physical_instrument_access=False,
                limitation='Arithmetic helper only; command timing, full physical waveform and external RC network are not validated here.')


if __name__ == '__main__':
    result = self_check()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    target = Path(__file__).with_name('compact_model_selfcheck.json')
    if target.exists():
        raise FileExistsError('Preserve the original selfcheck result')
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result, indent=2))
