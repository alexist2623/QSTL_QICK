"""Tests for canonical measurement units and automatic plot scaling.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import numpy as np

from measurement_display import measurement_display_scale, scale_iq_for_display


def test_current_scale_uses_nanoamps_for_nanoamp_data():
    scale = measurement_display_scale(
        np.asarray((-2.5e-9, 1.0e-9)),
        "A",
    )

    assert scale.factor == 1.0e9
    assert scale.unit == "nA"
    assert scale.base_unit == "A"


def test_voltage_scale_uses_millivolts_and_preserves_common_iq_factor():
    i_values, q_values, scale = scale_iq_for_display(
        np.asarray((1.0e-3, -2.0e-3)),
        np.asarray((0.5e-3, 3.0e-3)),
        "V",
    )

    assert scale.factor == 1.0e3
    assert scale.unit == "mV"
    np.testing.assert_allclose(i_values, (1.0, -2.0))
    np.testing.assert_allclose(q_values, (0.5, 3.0))


def test_adc_units_are_never_rescaled():
    i_values, q_values, scale = scale_iq_for_display(
        np.asarray((1.0, 2.0)),
        np.asarray((-3.0, 4.0)),
        "ADC units",
    )

    assert scale.factor == 1.0
    assert scale.unit == "ADC units"
    np.testing.assert_allclose(i_values, (1.0, 2.0))
    np.testing.assert_allclose(q_values, (-3.0, 4.0))
