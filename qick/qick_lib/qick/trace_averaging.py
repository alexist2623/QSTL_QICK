"""Bounded-memory repetition averaging without reducing the trace time axis."""

from numbers import Integral

import numpy as np

FIR_AVERAGE_API_VERSION = 1


def positive_int(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 1:
        raise ValueError('%s must be a positive integer' % name)
    return int(value)


def average_repetition_traces(read, n_points, repetitions, trace_shape,
                              raw_dtype, scale_log2=0, max_chunk_bytes=8*1024*1024,
                              reduce_samples=False):
    """Read point-major, repetition-minor traces and return float64 means.

    ``read(first_trigger, count)`` returns ``(count, *trace_shape)`` raw samples.
    Real traces and I/Q traces are both supported. By default only repetitions
    are reduced; reduce_samples=True also reduces the first trace dimension.
    Integer data is converted before summation, including fixed-point IQ64.
    Temporary raw + float arrays are bounded by max_chunk_bytes, except that
    one complete trace must always fit. The returned mean array is additional.
    """
    n_points = positive_int(n_points, 'n_points')
    repetitions = positive_int(repetitions, 'repetitions')
    trace_shape = tuple(positive_int(n, 'trace_shape') for n in trace_shape)
    if not trace_shape:
        raise ValueError('trace_shape must contain a sample dimension')
    max_chunk_bytes = positive_int(max_chunk_bytes, 'max_chunk_bytes')
    raw_dtype = np.dtype(raw_dtype)
    elements = int(np.prod(trace_shape))
    chunk_reps = max(1, max_chunk_bytes // (elements * (raw_dtype.itemsize + 8)))
    output_shape = (1,) + trace_shape[1:] if reduce_samples else trace_shape
    means = np.empty((n_points,) + output_shape, dtype=np.float64)
    for point in range(n_points):
        total = np.zeros(trace_shape, dtype=np.float64)
        for first in range(0, repetitions, chunk_reps):
            count = min(chunk_reps, repetitions - first)
            raw = np.asarray(read(point * repetitions + first, count))
            if raw.shape != (count,) + trace_shape or raw.dtype != raw_dtype:
                raise RuntimeError('Unexpected raw trace shape or dtype during repetition averaging')
            values = raw.astype(np.float64)
            np.ldexp(values, -int(scale_log2), out=values)
            total += values.sum(axis=0, dtype=np.float64)
            del raw, values
        means[point] = (total.mean(axis=0, keepdims=True) if reduce_samples else total) / repetitions
    return means
