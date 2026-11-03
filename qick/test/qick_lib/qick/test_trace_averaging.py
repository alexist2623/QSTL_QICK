"""Board CPU averaging, real traces, IQ64 padding and the public RPC contract."""

from types import SimpleNamespace

import numpy as np
import pytest

from test_ddr_iq64_support import make_ddr
from qick.qick import QickSoc
from qick.trace_averaging import average_repetition_traces


@pytest.mark.parametrize('shape', [(13,), (13, 2)])
@pytest.mark.parametrize('reduce_samples', [False, True])
@pytest.mark.parametrize('repetitions', [1, 3, 300])
def test_real_and_iq_traces_keep_point_and_time_alignment(shape, reduce_samples, repetitions):
    raw = np.arange(3 * repetitions * np.prod(shape), dtype=np.int64).reshape(3, repetitions, *shape)
    raw = raw * 2**30 + 2**61  # Summing int64 would overflow for sufficiently many reps.
    calls = []
    def read(first, count):
        calls.append((first, count))
        return raw.reshape(-1, *shape)[first:first + count]
    mean = average_repetition_traces(read, 3, repetitions, shape, 'int64', 46,
                                    max_chunk_bytes=16*np.prod(shape)*2, reduce_samples=reduce_samples)
    expected = np.ldexp(raw.astype(np.float64), -46).mean(axis=1)
    if reduce_samples:
        expected = expected.mean(axis=1, keepdims=True)
    np.testing.assert_allclose(mean, expected, rtol=1e-14)
    assert all(count <= 2 for _, count in calls)
    assert mean.dtype == np.float64


@pytest.mark.parametrize('samples', [1, 2, 13, 16, 17])
@pytest.mark.parametrize('stride_bytes', [None, 512])
@pytest.mark.parametrize('reduce_samples', [False, True])
def test_qicksoc_mean_respects_padding_nonzero_start_and_raw_format(samples, stride_bytes, reduce_samples):
    ddr = make_ddr(words=8192)
    ddr.cfg.update(sample_capture=True, fir_enabled=True)
    raw = (np.arange(2 * 3 * samples * 2, dtype=np.int64).reshape(2, 3, samples, 2) - 50) * 2**46
    stride_words = ddr._physical_words_per_trigger(samples) if stride_bytes is None else stride_bytes // 4
    for trigger, values in enumerate(raw.reshape(6, samples, 2)):
        start = 8 + trigger * stride_words
        ddr.ddr4_array[start:start + samples * 4] = values.ravel().view(np.uint32)
    before = ddr.ddr4_array.copy()
    soc = SimpleNamespace(ddr4_buf=ddr)
    soc.get_ddr4_fir_samples = lambda *a, **kw: QickSoc.get_ddr4_fir_samples(soc, *a, **kw)
    reply = QickSoc.get_ddr4_fir_mean(soc, samples, 3, n_points=2, start=8,
                                     stride_bytes=stride_bytes, max_chunk_bytes=1,
                                     reduce_samples=reduce_samples)
    expected = np.ldexp(raw.astype(float), -46).mean(axis=1)
    if reduce_samples:
        expected = expected.mean(axis=1, keepdims=True)
    np.testing.assert_array_equal(reply['iq'], expected)
    assert reply['accumulation_repetitions'] == 3
    assert reply['source_samples_per_trace'] == samples
    assert reply['source_iq_scale_log2'] == 46 and reply['iq_scale_log2'] == 0
    np.testing.assert_array_equal(before, ddr.ddr4_array)
    np.testing.assert_array_equal(soc.get_ddr4_fir_samples(samples, 6, 8, stride_bytes), raw.reshape(-1, 2))


@pytest.mark.parametrize('kwargs', [dict(repetitions=0), dict(repetitions=True), dict(n_points=1.5),
                                   dict(n_points=10000), dict(start=1), dict(stride_bytes=36),
                                   dict(reduce_samples='yes')])
def test_bad_requests_are_rejected(kwargs):
    ddr = make_ddr(words=64)
    ddr.cfg.update(sample_capture=True, fir_enabled=True)
    soc = SimpleNamespace(ddr4_buf=ddr)
    soc.get_ddr4_fir_samples = lambda *a, **kw: QickSoc.get_ddr4_fir_samples(soc, *a, **kw)
    with pytest.raises((ValueError, RuntimeError)):
        QickSoc.get_ddr4_fir_mean(soc, **dict(dict(n_samples=3, repetitions=2), **kwargs))


def test_capability_handshake_does_not_access_hardware():
    assert QickSoc.get_fir_average_capabilities(object()) == dict(
        api_version=1, modes=['repetition_mean', 'point_mean'], units='input_code', dtype='float64')


def test_mean_reply_crosses_a_real_pyro_connection():
    """Exercise serialization with the same pickle protocol as the board server."""
    import threading
    import Pyro4

    ddr = make_ddr(words=256)
    ddr.cfg.update(sample_capture=True, fir_enabled=True)
    raw = (np.arange(2 * 3 * 3 * 2, dtype=np.int64).reshape(6, 3, 2) - 10) * 2**46
    for index, values in enumerate(raw):
        ddr.ddr4_array[index*16:index*16+12] = values.ravel().view(np.uint32)

    @Pyro4.expose
    class Server:
        def get_fir_average_capabilities(self):
            return QickSoc.get_fir_average_capabilities(self)
        def get_ddr4_fir_samples(self, *a, **kw):
            return QickSoc.get_ddr4_fir_samples(self, *a, **kw)
        def get_ddr4_fir_mean(self, *a, **kw):
            return QickSoc.get_ddr4_fir_mean(self, *a, **kw)

    server = Server()
    server.ddr4_buf = ddr
    accepted = Pyro4.config.SERIALIZERS_ACCEPTED
    Pyro4.config.SERIALIZERS_ACCEPTED = set(accepted) | {'pickle'}
    daemon = Pyro4.Daemon(host='127.0.0.1')
    thread = threading.Thread(target=daemon.requestLoop, daemon=True)
    try:
        uri = daemon.register(server)
        thread.start()
        with Pyro4.Proxy(uri) as proxy:
            proxy._pyroSerializer = 'pickle'
            proxy._pyroTimeout = 5
            assert proxy.get_fir_average_capabilities()['api_version'] == 1
            reply = proxy.get_ddr4_fir_mean(3, 3, n_points=2)
            np.testing.assert_array_equal(reply['iq'], np.ldexp(raw.astype(float), -46).reshape(2, 3, 3, 2).mean(axis=1))
            assert reply['iq'].dtype == np.float64
    finally:
        daemon.shutdown()
        thread.join(timeout=5)
        daemon.close()
        Pyro4.config.SERIALIZERS_ACCEPTED = accepted
