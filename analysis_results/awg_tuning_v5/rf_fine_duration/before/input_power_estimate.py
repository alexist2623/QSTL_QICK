"""Output-power regression and gain selection for ADC input calibration."""

from __future__ import annotations

import numpy as np

try:
    from .power_calibration import MAX_QICK_GAIN
except ImportError:
    from power_calibration import MAX_QICK_GAIN


class OutputGainRegression:
    """Fit dBm against log amplitude independently at each measured frequency.

    Use the same upper-gain region as the existing amplitude model to reduce
    noise-floor bias. Frequency interpolation stays inside measured coverage.
    Gain extrapolation is allowed throughout the hardware's positive range.
    """

    def __init__(self, calibration):
        self.calibration = calibration
        self.frequencies_mhz = calibration.frequencies_mhz.copy()
        self.curves = []
        self.fits = []
        for frequency in self.frequencies_mhz:
            gains, powers = calibration._curves[float(frequency)]
            valid = np.isfinite(gains) & np.isfinite(powers) & (gains > 0)
            valid &= gains <= MAX_QICK_GAIN
            gains, powers = gains[valid], powers[valid]
            unique = np.unique(gains)
            powers = np.array([np.mean(powers[gains == gain]) for gain in unique])
            gains = unique
            if gains.size < 2:
                raise ValueError(f"{frequency:g} MHz needs at least two measured gains for regression")
            selected = gains >= np.max(gains) / 8.0
            if np.count_nonzero(selected) < min(3, gains.size):
                selected = np.zeros(gains.size, dtype=bool)
                selected[-min(8, gains.size):] = True
            x = 20.0 * np.log10(gains[selected] / MAX_QICK_GAIN)
            y = powers[selected]
            slope, intercept = np.polyfit(x, y, 1)
            residual = y - (slope * x + intercept)
            total = np.sum((y - np.mean(y)) ** 2)
            if not np.isfinite(slope + intercept) or slope <= 0 or total <= 0:
                raise ValueError(f"{frequency:g} MHz has no increasing gain/power regression")
            self.curves.append((gains, powers, selected))
            self.fits.append({
                "frequency_mhz": float(frequency),
                "slope": float(slope), "intercept_dbm": float(intercept),
                "r_squared": float(1.0 - np.sum(residual ** 2) / total),
                "rmse_db": float(np.sqrt(np.mean(residual ** 2))),
                "fit_gain_min": float(gains[selected].min()),
                "fit_gain_max": float(gains[selected].max()),
                "point_count": int(np.count_nonzero(selected)),
            })

    def _values(self, frequencies, key):
        # Reuse the existing coverage tolerance, including DDS quantization.
        self.calibration.frequency_response_dbm(frequencies)
        return np.interp(frequencies, self.frequencies_mhz, [fit[key] for fit in self.fits])

    def _attenuation_delta(self, att1, att2):
        summary = self.calibration.summary
        return float(att1) + float(att2) - summary.calibration_att1_db - summary.calibration_att2_db

    def output_power_dbm(self, frequencies, gains, *, output_att1_db=0.0, output_att2_db=0.0):
        frequencies, gains = np.broadcast_arrays(np.asarray(frequencies, float), np.asarray(gains, float))
        if np.any(~np.isfinite(gains)) or np.any((gains < 1) | (gains > MAX_QICK_GAIN)):
            raise ValueError(f"DAC gain must be in 1..{MAX_QICK_GAIN}")
        return (self._values(frequencies, "slope") * 20.0 * np.log10(gains / MAX_QICK_GAIN)
                + self._values(frequencies, "intercept_dbm")
                - self._attenuation_delta(output_att1_db, output_att2_db))

    def gains_for_power(self, frequencies, powers_dbm, **attenuation):
        frequencies, powers = np.broadcast_arrays(np.asarray(frequencies, float), np.asarray(powers_dbm, float))
        minimum = self.output_power_dbm(frequencies, 1, **attenuation)
        maximum = self.output_power_dbm(frequencies, MAX_QICK_GAIN, **attenuation)
        invalid = ~np.isfinite(powers) | (powers < minimum) | (powers > maximum)
        if np.any(invalid):
            index = tuple(np.argwhere(invalid)[0])
            raise ValueError(
                f"Requested output power at {frequencies[index]:g} MHz is outside "
                f"the DAC gain range: {minimum[index]:.6g}..{maximum[index]:.6g} dBm"
            )
        exponent = (powers - maximum) / (20.0 * self._values(frequencies, "slope"))
        return np.clip(np.rint(MAX_QICK_GAIN * 10.0 ** exponent), 1, MAX_QICK_GAIN).astype(np.int64)

    def warnings(self, frequencies, gains):
        frequencies, gains = np.broadcast_arrays(np.asarray(frequencies, float), np.asarray(gains, float))
        messages = ["Output powers are regression estimates, not new power measurements."]
        # Use the intersection of neighboring fit intervals for conservative reporting.
        positions = np.searchsorted(self.frequencies_mhz, frequencies)
        right = np.clip(positions, 0, len(self.fits) - 1)
        left = np.clip(positions - 1, 0, len(self.fits) - 1)
        exact = np.isclose(frequencies, self.frequencies_mhz[right], atol=1e-5, rtol=0)
        left = np.where(exact, right, left)
        lows = np.array([fit["fit_gain_min"] for fit in self.fits])
        highs = np.array([fit["fit_gain_max"] for fit in self.fits])
        outside = (gains < np.maximum(lows[left], lows[right])) | (gains > np.minimum(highs[left], highs[right]))
        if np.any(outside):
            messages.append(f"{np.count_nonzero(outside)} selected point(s) extrapolate beyond the fitted gain range; calibration is allowed.")
        relevant = set(np.ravel(left)) | set(np.ravel(right))
        if any(self.fits[i]["r_squared"] < 0.98 for i in relevant):
            messages.append("Some fits have R² < 0.98; review the measured points and fit residuals.")
        if any(self.fits[i]["point_count"] == 2 for i in relevant):
            messages.append("Some fits have only two points; fit quality cannot be independently assessed.")
        return messages

    def metadata(self):
        return {
            "model": "gain_regression",
            "formula": "output_dbm = slope(f)*20*log10(gain/32767) + intercept_dbm(f) - attenuation_delta_db",
            "fit_selection": "gain >= max_measured_gain/8; fall back to up to eight highest gains if fewer than three",
            "fits": self.fits,
        }
