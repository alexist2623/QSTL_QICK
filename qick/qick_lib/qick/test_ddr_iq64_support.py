"""Integer-format, physical DDR layout and legacy compatibility regression."""
import types
import unittest
from pathlib import Path
import numpy as np
from qick.test_ddr_triggered_pack_support import _install_pynq_stub, load_hwh_metadata
from qick.drivers.readout import AxisBufferDdrSampleV3


def make_ddr(words=4096, **parameters):
    ddr = object.__new__(AxisBufferDdrSampleV3)
    object.__setattr__(ddr, '_cfg', {})
    params = dict(TARGET_SLAVE_BASE_ADDR='0x0', ID_WIDTH='1',
                  S_AXIS_DATA_WIDTH='128', M_AXI_DATA_WIDTH='256',
                  IQ_COMPONENT_BITS='64', IQ_SCALE_LOG2='46', FORMAT_VERSION='1',
                  DEFAULT_TRIGGER_DELAY_CYCLES='8712', TRIGGER_QUEUE_ADDR_WIDTH='6')
    params.update(parameters)
    ddr._init_config({'parameters': params})
    registers = np.zeros(14, dtype=np.uint32)
    registers[10:14] = [0x5149434b, 1, 64, 46]
    object.__setattr__(ddr, 'mmio', types.SimpleNamespace(array=registers))
    object.__setattr__(ddr, 'ddr4_array', np.zeros(words, dtype=np.uint32))
    ddr.cfg['maxlen'] = words
    ddr._init_firmware()
    return ddr


class TestDdrIq64(unittest.TestCase):
    def test_exact_signed_raw_packing_and_stride(self):
        for samples in [1, 2, 13, 16]:
            for stride in [None, 512]:
                with self.subTest(samples=samples, stride=stride):
                    ddr = make_ddr()
                    expected = np.array([(2**62+3-k, -2**62-7+k)
                                         for k in range(samples*3)], dtype=np.int64)
                    reserved = ddr.arm_samples(samples, 3, address=32, stride_bytes=stride)
                    words = ((samples+1)//2)*8
                    self.assertEqual(reserved, words*3)
                    self.assertEqual(int(ddr.nsamp_reg), samples)
                    for k in range(3):
                        start = 8+k*(words if stride is None else stride//4)
                        ddr.ddr4_array[start:start+samples*4] = expected[k*samples:(k+1)*samples].ravel().view(np.uint32)
                    result = ddr.get_mem_samples(samples, 3, start=8, stride_bytes=stride)
                    self.assertEqual(result.dtype, np.dtype('int64'))
                    np.testing.assert_array_equal(result, expected)
                    result[:] = 0
                    self.assertTrue(np.any(ddr.ddr4_array))

    def test_format_validation_before_writes_and_reads(self):
        for index in [10, 11, 12, 13]:
            ddr = make_ddr()
            ddr.mmio.array[index] = 99
            with self.assertRaisesRegex(RuntimeError, 'format mismatch'):
                ddr.arm_samples(13)
            self.assertEqual(int(ddr.control_reg), 0)
            with self.assertRaisesRegex(RuntimeError, 'format mismatch'):
                ddr.get_mem_samples(13)
        for key in ['IQ_COMPONENT_BITS', 'IQ_SCALE_LOG2', 'FORMAT_VERSION']:
            with self.assertRaisesRegex(RuntimeError, 'Unsupported'):
                make_ddr(**{key: '99'})

    def test_memory_capacity_and_alignment(self):
        ddr = make_ddr(words=16)
        self.assertEqual(ddr.arm_samples(3), 16)
        with self.assertRaises(RuntimeError): ddr.arm_samples(5)
        with self.assertRaises(RuntimeError): ddr.get_mem_samples(5)
        with self.assertRaises(ValueError): ddr.get_mem_samples(1, start=1)
        with self.assertRaises(ValueError): ddr.get_mem_samples(1, stride_bytes=36)
        with self.assertRaises(ValueError): ddr.arm_samples(2**32)
        with self.assertRaises(ValueError): ddr.arm_samples(2**29, force_overwrite=True)

    def test_pipeline_delay_and_upstream_width_metadata(self):
        ddr = make_ddr()
        params = dict(OUTPUT_SCALE_LOG2=46, M_AXIS_DATA_WIDTH=128, PIPELINE_LATENCY_CYCLES=35)
        metadata = types.SimpleNamespace(
            get_param=lambda block, name: params[name], get_fclk=lambda *a: 300,
            trace_sig=lambda *a: [('zero', 'dout')], mod2type=lambda *a: 'xlconstant')
        params['CONST_VAL'] = 0
        ddr._configure_1msps_fir_path(types.SimpleNamespace(metadata=metadata), 'fir', 'm_axis')
        self.assertEqual(ddr.cfg['fir_pipeline_latency_cycles'], 35)
        self.assertAlmostEqual(ddr.cfg['fir_full_path_nominal_delay_us'], 29.04)
        self.assertEqual(ddr.cfg['fir_sample_rate_hz'], 1_000_000)
        self.assertFalse(ddr.cfg['fir_trigger_aligned'])
        params['OUTPUT_SCALE_LOG2'] = 0
        with self.assertRaisesRegex(RuntimeError, 'metadata mismatch'):
            ddr._configure_1msps_fir_path(types.SimpleNamespace(metadata=metadata), 'fir', 'm_axis')


if __name__ == '__main__':
    unittest.main()
