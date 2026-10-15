"""Board-independent command ABI and exact arithmetic for AWG v3 shot area.

Area is counted in effective 14-bit DAC codes times scalar samples, before
the RC inverse filter. These helpers never import a PYNQ hardware driver.
"""
from numbers import Integral

AREA_BITS = 48
AREA_PIPELINE_CYCLES = 5
DC_START_CYCLES = 17
DC_ZERO_RESET_CYCLES = 2
SAMPLES_PER_CLOCK = 16


def _integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, Integral) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return int(value)


def dc_area_words(action, *, amplitude=0, words=0, tmux_ch=None):
    """Return five u32 command words; fixed-voltage amplitude is transport code.

    ARM/DISABLE require the AWG raw path to be zero and drained. A compensation
    command snapshots the actual accumulated samples. Its completion clears
    the area and IIR history after the final zero edge has reached the IIR.
    """
    actions = {"arm": 0, "fixed_voltage": 1, "fixed_time": 2, "disable": 3}
    if action not in actions:
        raise ValueError(f"Unsupported DC area action: {action!r}")
    amplitude = _integer(amplitude, "amplitude", 0, 32764)
    words = _integer(words, "words", 0, 0xffffffff)
    low = high = 0
    if action == "fixed_voltage":
        if not amplitude or amplitude % 4 or words:
            raise ValueError("Fixed-voltage compensation requires an aligned positive amplitude and no word count")
        low = amplitude
    elif action == "fixed_time":
        if not words or amplitude:
            raise ValueError("Fixed-time compensation requires a positive word count and no amplitude")
        reciprocal = (1 << 64) // (SAMPLES_PER_CLOCK * words)
        low, high = reciprocal & 0xffffffff, reciprocal >> 32
    elif amplitude or words:
        raise ValueError("ARM/DISABLE do not take amplitude or word count")
    control = (1 << 22) | (3 << 16) | (actions[action] << 18)
    if tmux_ch is not None:
        control |= _integer(tmux_ch, "tmux_ch", 0, 255) << 24
    return low, high, words, 0, control


def validate_area_bounds(minimum, maximum, bits=AREA_BITS):
    """Check every-prefix bounds, not only a shot's possibly cancelling net area."""
    bits = _integer(bits, "bits", 32, 64)
    minimum = int(minimum)
    maximum = int(maximum)
    if minimum > maximum:
        raise ValueError("Invalid area interval")
    if minimum < -(1 << (bits-1)) or maximum >= (1 << (bits-1)):
        raise ValueError(f"AWG {bits}-bit DC area accumulator can overflow: "
                         f"prefix area [{minimum}, {maximum}] effective-code samples")


def compensation_plan(area, *, amplitude=None, words=None):
    """Exact digital compensation ledger, with no per-point voltage rounding.

    Returns compact scalar run lengths. Fixed time uses q and q+1 codes;
    fixed voltage uses full-amplitude samples and at most one partial sample.
    This matches the RTL tail construction and always cancels integer area.
    """
    area = int(area)
    validate_area_bounds(area, area)
    negative = area > 0
    sign = -1 if negative else 1
    magnitude = abs(area)
    if (amplitude is None) == (words is None):
        raise ValueError("Specify exactly one of amplitude or words")
    if words is not None:
        words = _integer(words, "words", 1, 0xffffffff)
        count = words * SAMPLES_PER_CLOCK
        quotient, remainder = divmod(magnitude, count)
        limit = 8192 if negative else 8191
        if quotient + bool(remainder) > limit:
            raise ValueError("Fixed-time DC compensation exceeds the DAC range")
        runs = ((remainder, sign * (quotient+1)), (count-remainder, sign*quotient))
    else:
        amplitude = _integer(amplitude, "amplitude", 4, 32764)
        if amplitude % 4:
            raise ValueError("Compensation amplitude must be aligned to the effective DAC code")
        full, partial = divmod(magnitude, amplitude//4)
        count = full + bool(partial)
        words = max(1, (count+15)//16)
        runs = ((full, sign*(amplitude//4)), (int(bool(partial)), sign*partial),
                (words*16-count, 0))
    return {"words": words, "runs": tuple((n, v) for n, v in runs if n),
            "residual": area + sum(n*v for n, v in runs)}


def floor_sum(count, divisor, slope, intercept):
    """Exact sum floor((slope*i+intercept)/divisor), O(log divisor)."""
    count, divisor, slope, intercept = map(int, (count, divisor, slope, intercept))
    if count < 0 or divisor <= 0:
        raise ValueError("count must be nonnegative and divisor positive")
    result = 0
    while True:
        q, slope = divmod(slope, divisor)
        result += q * count * (count-1)//2
        q, intercept = divmod(intercept, divisor)
        result += q * count
        top = slope*count + intercept
        if top < divisor:
            return result
        count, intercept = divmod(top, divisor)
        divisor, slope = slope, divisor


def clipped_floor_sum(count, divisor, slope, intercept, lower=-8192, upper=8191):
    """Sum a monotone fixed-point ramp after the production DAC saturation."""
    count, divisor, slope, intercept = map(int, (count, divisor, slope, intercept))
    if count < 0 or divisor <= 0 or lower > upper:
        raise ValueError('Invalid clipped ramp interval')
    if not count:
        return 0
    if slope < 0:
        intercept += slope * (count-1)
        slope = -slope
    if not slope:
        return count * min(upper, max(lower, intercept//divisor))
    def boundary(threshold):
        return min(count, max(0, -((intercept-threshold*divisor)//slope)))
    first, last = boundary(lower), boundary(upper+1)
    return (lower*first + floor_sum(last-first, divisor, slope, intercept+slope*first)
            + upper*(count-last))


def ramp_area(start_transport, target_transport, step, sample_count, frac=18):
    """Effective-code area of a production RAMP, including forced last target."""
    sample_count = _integer(sample_count, "sample_count", 1, (1 << 23)-1)
    return (clipped_floor_sum(sample_count-1, 1 << (frac+2), int(step), int(start_transport) << frac)
            + (int(target_transport) >> 2))
