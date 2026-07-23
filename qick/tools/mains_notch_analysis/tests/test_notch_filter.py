"""Tests for the float64 mains-harmonic SOS notch reference model."""

from __future__ import annotations

from pathlib import Path
import sys
import warnings

import numpy as np
import pytest
from scipy import signal

TOOL_ROOT = Path(__file__).resolve().parents[1]
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from notch_filter_analysis import (
    _design_notch_details,
    build_frequency_grid,
    compute_digital_nyquist,
    compute_frequency_response,
    compute_group_delay,
    compute_impulse_response,
    design_notch_sos,
    direct_section_cascade,
    run_synthetic_test,
)


@pytest.mark.parametrize("fs", [10_000.0, 100_000.0])
def test_default_design_is_float64_sos_with_expected_q(fs):
    sos = design_notch_sos(fs)
    design = _design_notch_details(fs)
    assert sos.shape == (10, 6)
    assert sos.dtype == np.float64
    np.testing.assert_allclose(sos, design.sos, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(
        [section.q for section in design.sections],
        np.arange(1, 11, dtype=float) * 30.0,
    )
    np.testing.assert_allclose(
        [section.bandwidth_hz for section in design.sections], 2.0
    )
    assert all(section.pole_radius < 1.0 for section in design.sections)


def test_constant_q_uses_fundamental_q_for_all_harmonics():
    design = _design_notch_details(10_000.0, mode="constant_q")
    np.testing.assert_allclose([section.q for section in design.sections], 30.0)
    np.testing.assert_allclose(
        [section.bandwidth_hz for section in design.sections],
        np.arange(1, 11, dtype=float) * 2.0,
    )


def test_harmonics_at_or_above_nyquist_are_excluded():
    with pytest.warns(RuntimeWarning):
        design = _design_notch_details(500.0, n_harmonics=10)
    np.testing.assert_allclose(design.notch_frequencies_hz, [60.0, 120.0, 180.0, 240.0])
    assert design.sos.shape == (4, 6)
    assert design.excluded_harmonics[0] == (5, 300.0)


def test_design_rejects_configuration_with_no_valid_harmonic():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match="no requested harmonic"):
            design_notch_sos(100.0)


def test_frequency_grid_contains_centers_and_bandwidth_edges_exactly():
    frequencies = np.asarray([60.0, 120.0, 180.0])
    grid = build_frequency_grid(10_000.0, frequencies, 2.0)
    assert np.all(np.diff(grid) > 0.0)
    assert grid[0] == 0.0
    assert grid[-1] == 5_000.0
    for f0 in frequencies:
        assert f0 - 1.0 in grid
        assert f0 in grid
        assert f0 + 1.0 in grid


@pytest.mark.parametrize("fs", [10_000.0, 100_000.0])
def test_frequency_response_meets_dc_notch_and_bandwidth_requirements(fs):
    design = _design_notch_details(fs)
    probe = np.unique(
        np.concatenate(
            (
                np.asarray([0.0]),
                design.notch_frequencies_hz,
                design.notch_frequencies_hz - 1.0,
                design.notch_frequencies_hz + 1.0,
            )
        )
    )
    response = compute_frequency_response(
        design.sos,
        fs,
        probe,
        notch_frequencies_hz=design.notch_frequencies_hz,
        bandwidth_hz=design.bandwidths_hz,
    )
    assert np.all(np.isfinite(response["cascade_magnitude_db"]))
    dc_index = int(np.flatnonzero(probe == 0.0)[0])
    assert response["cascade_magnitude"][dc_index] == pytest.approx(1.0, abs=1e-12)
    for section_index, section in enumerate(design.sections):
        center_index = int(np.flatnonzero(probe == section.f0_hz)[0])
        assert response["cascade_magnitude_db"][center_index] <= -80.0
        edge_frequencies = [section.f0_hz - 1.0, section.f0_hz + 1.0]
        _, edge_response = signal.sosfreqz(
            design.sos[section_index : section_index + 1],
            worN=edge_frequencies,
            fs=fs,
        )
        edge_db = 20.0 * np.log10(np.abs(edge_response))
        np.testing.assert_allclose(edge_db, -3.01029995664, atol=0.20, rtol=0.0)


@pytest.mark.parametrize("fs", [10_000.0, 100_000.0])
def test_impulse_sosfilt_matches_direct_section_cascade(fs):
    design = _design_notch_details(fs)
    impulse = compute_impulse_response(design.sos, fs, duration_seconds=2.0)
    direct = direct_section_cascade(design.sos, impulse["input"])
    np.testing.assert_allclose(impulse["cascade"], direct, rtol=1e-13, atol=1e-14)
    assert impulse["time_seconds"][0] == 0.0
    assert impulse["duration_seconds"] == pytest.approx(2.0)
    assert np.all(np.isfinite(impulse["cascade"]))


def test_impulse_duration_is_never_shorter_than_two_seconds():
    design = _design_notch_details(10_000.0)
    impulse = compute_impulse_response(design.sos, design.fs, duration_seconds=0.25)
    assert impulse["duration_seconds"] == pytest.approx(2.0)


@pytest.mark.parametrize("fs", [10_000.0, 100_000.0])
def test_group_delay_is_nan_at_notch_center_and_finite_away_from_it(fs):
    design = _design_notch_details(fs)
    frequencies = np.asarray([0.0, 10.0, 59.5, 60.0, 60.5, 100.0])
    result = compute_group_delay(
        design.sos,
        design.fs,
        frequencies,
        report_frequencies_hz=frequencies,
    )
    delay = np.asarray(result["samples"])
    assert np.isnan(delay[3])
    assert np.all(np.isfinite(np.delete(delay, 3)))
    assert np.all(np.delete(delay, 3) >= 0.0)
    assert result["reports"][3]["defined"] is False


@pytest.mark.parametrize("fs", [10_000.0, 100_000.0])
def test_nyquist_response_has_conjugate_symmetry(fs):
    design = _design_notch_details(fs)
    frequencies = build_frequency_grid(
        fs,
        design.notch_frequencies_hz,
        design.bandwidths_hz,
        coarse_points=4097,
        dense_points_per_notch=201,
    )
    result = compute_digital_nyquist(design.sos, fs, frequencies)
    assert result["conjugate_symmetry_max_error"] < 1e-12
    np.testing.assert_allclose(
        result["negative"], np.conj(result["positive"]), rtol=1e-12, atol=1e-12
    )


def test_seconds_time_constant_is_rate_independent_while_samples_scale():
    designs = [_design_notch_details(fs) for fs in (10_000.0, 100_000.0)]
    theoretical_tau = 1.0 / (np.pi * 2.0)
    sample_taus = [theoretical_tau * design.fs for design in designs]
    assert sample_taus[1] / sample_taus[0] == pytest.approx(10.0)
    pole_taus = [
        -1.0 / (design.fs * np.log(design.sections[0].pole_radius))
        for design in designs
    ]
    assert pole_taus[0] == pytest.approx(theoretical_tau, rel=2e-4)
    assert pole_taus[1] == pytest.approx(theoretical_tau, rel=2e-4)
    assert pole_taus[0] == pytest.approx(pole_taus[1], rel=2e-4)


def test_synthetic_test_is_finite_and_reduces_every_harmonic():
    design = _design_notch_details(10_000.0)
    result = run_synthetic_test(
        design.sos,
        design.fs,
        design.notch_frequencies_hz,
        duration_seconds=2.0,
    )
    assert np.all(np.isfinite(result["output"]))
    assert len(result["harmonic_metrics"]) == 10
    assert all(
        metric["after_amplitude"] < metric["before_amplitude"]
        for metric in result["harmonic_metrics"]
    )
