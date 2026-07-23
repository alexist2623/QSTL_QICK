"""Float64 reference analysis for cascaded mains-harmonic IIR notch filters.

The design intentionally remains in second-order-section (SOS) form.  No
high-order numerator/denominator polynomial is formed anywhere in this module.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from scipy import signal


DB_FLOOR = -300.0
DEFAULT_GROUP_DELAY_FREQUENCIES = (
    0.0,
    10.0,
    30.0,
    50.0,
    59.0,
    59.5,
    60.0,
    60.5,
    61.0,
    100.0,
)


@dataclass(frozen=True)
class NotchSection:
    """Design data for one harmonic notch biquad."""

    harmonic: int
    f0_hz: float
    bandwidth_hz: float
    q: float
    b: np.ndarray
    a: np.ndarray
    zeros: np.ndarray
    poles: np.ndarray
    pole_radius: float


@dataclass(frozen=True)
class NotchDesign:
    """SOS design and the metadata required by analysis and reporting."""

    fs: float
    mains_frequency: float
    requested_harmonics: int
    requested_bandwidth_hz: float
    mode: str
    sos: np.ndarray
    sections: tuple[NotchSection, ...]
    excluded_harmonics: tuple[tuple[int, float], ...]

    @property
    def notch_frequencies_hz(self) -> np.ndarray:
        return np.asarray([section.f0_hz for section in self.sections], dtype=np.float64)

    @property
    def bandwidths_hz(self) -> np.ndarray:
        return np.asarray(
            [section.bandwidth_hz for section in self.sections], dtype=np.float64
        )

    @property
    def order(self) -> int:
        return 2 * len(self.sections)


def _positive_float(value: float, name: str) -> float:
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or int(value) != value or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _magnitude_db(values: np.ndarray) -> np.ndarray:
    magnitude = np.abs(np.asarray(values))
    return np.maximum(20.0 * np.log10(np.maximum(magnitude, np.finfo(float).tiny)), DB_FLOOR)


def _design_notch_details(
    fs: float,
    mains_frequency: float = 60.0,
    n_harmonics: int = 10,
    bandwidth_hz: float = 2.0,
    mode: str = "constant_bandwidth",
) -> NotchDesign:
    fs = _positive_float(fs, "fs")
    mains_frequency = _positive_float(mains_frequency, "mains_frequency")
    n_harmonics = _positive_int(n_harmonics, "n_harmonics")
    bandwidth_hz = _positive_float(bandwidth_hz, "bandwidth_hz")
    mode = str(mode).lower()
    if mode not in {"constant_bandwidth", "constant_q"}:
        raise ValueError("mode must be 'constant_bandwidth' or 'constant_q'")

    nyquist = fs / 2.0
    constant_q = mains_frequency / bandwidth_hz
    rows: list[np.ndarray] = []
    sections: list[NotchSection] = []
    excluded: list[tuple[int, float]] = []

    for harmonic in range(1, n_harmonics + 1):
        f0 = mains_frequency * harmonic
        if f0 >= nyquist:
            excluded.append((harmonic, f0))
            warnings.warn(
                f"excluding harmonic {harmonic} at {f0:g} Hz because it is not "
                f"below Nyquist ({nyquist:g} Hz)",
                RuntimeWarning,
                stacklevel=2,
            )
            continue

        if mode == "constant_bandwidth":
            q = f0 / bandwidth_hz
            effective_bandwidth = bandwidth_hz
        else:
            q = constant_q
            effective_bandwidth = f0 / q

        b, a = signal.iirnotch(f0, q, fs=fs)
        b = np.asarray(b, dtype=np.float64)
        a = np.asarray(a, dtype=np.float64)
        if a[0] == 0.0:
            raise RuntimeError("scipy.signal.iirnotch returned a zero a0 coefficient")
        b = b / a[0]
        a = a / a[0]
        row = np.concatenate((b, a)).astype(np.float64, copy=False)
        zeros = np.roots(b).astype(np.complex128)
        poles = np.roots(a).astype(np.complex128)
        pole_radius = float(np.max(np.abs(poles)))
        rows.append(row)
        sections.append(
            NotchSection(
                harmonic=harmonic,
                f0_hz=float(f0),
                bandwidth_hz=float(effective_bandwidth),
                q=float(q),
                b=b,
                a=a,
                zeros=zeros,
                poles=poles,
                pole_radius=pole_radius,
            )
        )

    if not rows:
        raise ValueError(
            "no requested harmonic lies below Nyquist; increase fs or reduce harmonics"
        )

    sos = np.vstack(rows).astype(np.float64, copy=False)
    return NotchDesign(
        fs=fs,
        mains_frequency=mains_frequency,
        requested_harmonics=n_harmonics,
        requested_bandwidth_hz=bandwidth_hz,
        mode=mode,
        sos=sos,
        sections=tuple(sections),
        excluded_harmonics=tuple(excluded),
    )


def design_notch_sos(
    fs,
    mains_frequency=60.0,
    n_harmonics=10,
    bandwidth_hz=2.0,
    mode="constant_bandwidth",
):
    """Design a float64 cascade of harmonic notch biquads.

    ``constant_bandwidth`` uses ``Q_k = f_k / bandwidth_hz``.  In
    ``constant_q`` mode, every section uses the fundamental's Q,
    ``mains_frequency / bandwidth_hz``.  Harmonics at or above Nyquist are
    excluded with a warning.  The returned matrix has one row per valid
    harmonic in ``[b0, b1, b2, a0, a1, a2]`` order.
    """

    return _design_notch_details(
        fs,
        mains_frequency,
        n_harmonics,
        bandwidth_hz,
        mode,
    ).sos.copy()


def build_frequency_grid(
    fs: float,
    notch_frequencies_hz: Sequence[float],
    bandwidth_hz: float | Sequence[float] = 2.0,
    *,
    coarse_points: int = 32_769,
    dense_points_per_notch: int = 4_001,
    dense_half_width_bandwidths: float = 5.0,
) -> np.ndarray:
    """Combine a full-band grid with dense, exact grids around each notch."""

    fs = _positive_float(fs, "fs")
    coarse_points = _positive_int(coarse_points, "coarse_points")
    dense_points_per_notch = _positive_int(
        dense_points_per_notch, "dense_points_per_notch"
    )
    dense_half_width_bandwidths = _positive_float(
        dense_half_width_bandwidths, "dense_half_width_bandwidths"
    )
    frequencies = np.asarray(notch_frequencies_hz, dtype=np.float64)
    if frequencies.ndim != 1:
        raise ValueError("notch_frequencies_hz must be one-dimensional")
    if np.isscalar(bandwidth_hz):
        bandwidths = np.full(frequencies.shape, _positive_float(bandwidth_hz, "bandwidth_hz"))
    else:
        bandwidths = np.asarray(bandwidth_hz, dtype=np.float64)
        if bandwidths.shape != frequencies.shape:
            raise ValueError("bandwidth_hz must be scalar or match notch frequencies")
        if np.any(~np.isfinite(bandwidths)) or np.any(bandwidths <= 0.0):
            raise ValueError("all bandwidths must be finite and positive")

    nyquist = fs / 2.0
    grids: list[np.ndarray] = [
        np.linspace(0.0, nyquist, coarse_points, dtype=np.float64)
    ]
    for f0, width in zip(frequencies, bandwidths):
        if not 0.0 < f0 < nyquist:
            raise ValueError(f"notch frequency {f0:g} Hz is outside (0, Nyquist)")
        low = max(0.0, f0 - dense_half_width_bandwidths * width)
        high = min(nyquist, f0 + dense_half_width_bandwidths * width)
        dense = np.linspace(low, high, dense_points_per_notch, dtype=np.float64)
        exact = np.asarray([f0 - width / 2.0, f0, f0 + width / 2.0])
        exact = exact[(exact >= 0.0) & (exact <= nyquist)]
        grids.extend((dense, exact))
    return np.unique(np.concatenate(grids)).astype(np.float64, copy=False)


def compute_frequency_response(
    sos: np.ndarray,
    fs: float,
    frequencies_hz: np.ndarray | None = None,
    *,
    notch_frequencies_hz: Sequence[float] = (60.0,),
    bandwidth_hz: float | Sequence[float] = 2.0,
) -> dict[str, np.ndarray]:
    """Compute single-fundamental and full-cascade responses with sosfreqz."""

    sos = np.asarray(sos, dtype=np.float64)
    if sos.ndim != 2 or sos.shape[1] != 6 or sos.shape[0] < 1:
        raise ValueError("sos must have shape (n_sections, 6)")
    if frequencies_hz is None:
        frequencies_hz = build_frequency_grid(
            fs, notch_frequencies_hz, bandwidth_hz
        )
    frequencies_hz = np.asarray(frequencies_hz, dtype=np.float64)
    _, cascade = signal.sosfreqz(sos, worN=frequencies_hz, fs=fs)
    _, single = signal.sosfreqz(sos[:1], worN=frequencies_hz, fs=fs)

    result: dict[str, np.ndarray] = {"frequency_hz": frequencies_hz}
    for name, response in (("single", single), ("cascade", cascade)):
        magnitude = np.abs(response)
        result[f"{name}_complex"] = response
        result[f"{name}_magnitude"] = magnitude
        result[f"{name}_magnitude_db"] = _magnitude_db(response)
        result[f"{name}_wrapped_phase_rad"] = np.angle(response)
        result[f"{name}_unwrapped_phase_rad"] = np.unwrap(np.angle(response))
    return result


def compute_impulse_response(
    sos: np.ndarray,
    fs: float,
    duration_seconds: float = 2.0,
) -> dict[str, np.ndarray | float]:
    """Return float64 single-section and cascade impulse responses."""

    fs = _positive_float(fs, "fs")
    duration_seconds = max(
        2.0, _positive_float(duration_seconds, "duration_seconds")
    )
    n_samples = max(2, int(math.ceil(duration_seconds * fs)))
    impulse = np.zeros(n_samples, dtype=np.float64)
    impulse[0] = 1.0
    single = signal.sosfilt(np.asarray(sos[:1], dtype=np.float64), impulse)
    cascade = signal.sosfilt(np.asarray(sos, dtype=np.float64), impulse)
    return {
        "sample_index": np.arange(n_samples, dtype=np.int64),
        "time_seconds": np.arange(n_samples, dtype=np.float64) / fs,
        "input": impulse,
        "single": single,
        "cascade": cascade,
        "duration_seconds": float(n_samples / fs),
    }


def _summed_sos_group_delay(
    sos: np.ndarray,
    fs: float,
    frequencies_hz: np.ndarray,
) -> np.ndarray:
    frequencies_hz = np.asarray(frequencies_hz, dtype=np.float64)
    omega = 2.0 * np.pi * frequencies_hz / fs
    total = np.zeros_like(omega)
    # Evaluate section group delay from pole/zero factors. For a root
    # root=r*exp(j*theta), Re{root*exp(-jw)/(1-root*exp(-jw))} equals
    # (r*cos(theta-w)-r^2)/(1-2*r*cos(theta-w)+r^2). Denominator roots add
    # this term and numerator roots subtract it. Unit-circle numerator roots
    # contribute exactly +1/2 sample away from their phase singularity; using
    # that identity avoids catastrophic cancellation next to a deep notch.
    for row in np.asarray(sos, dtype=np.float64):
        for roots, sign in ((np.roots(row[:3]), -1.0), (np.roots(row[3:]), 1.0)):
            for root in roots:
                radius = float(abs(root))
                if sign < 0.0 and abs(radius - 1.0) <= 1.0e-10:
                    total += 0.5
                    continue
                delta = float(np.angle(root)) - omega
                denominator = (
                    1.0
                    - 2.0 * radius * np.cos(delta)
                    + radius * radius
                )
                numerator = radius * np.cos(delta) - radius * radius
                total += sign * numerator / denominator
    _, response = signal.sosfreqz(sos, worN=frequencies_hz, fs=fs)
    total[np.abs(response) < 1.0e-10] = np.nan
    # At a notch zero the phase, and therefore group delay, is undefined.
    # Magnitude-only masking is insufficient at high fs because round-off may
    # leave a tiny but finite residual above the threshold. Recover each notch
    # frequency from its numerator zeros and mask the exact center explicitly.
    center_tolerance_hz = max(1.0e-9, fs * 1.0e-12)
    for row in np.asarray(sos, dtype=np.float64):
        zero_angles = np.abs(np.angle(np.roots(row[:3])))
        center_hz = float(np.mean(zero_angles) * fs / (2.0 * np.pi))
        total[
            np.isclose(
                frequencies_hz,
                center_hz,
                rtol=0.0,
                atol=center_tolerance_hz,
            )
        ] = np.nan
    total[~np.isfinite(total)] = np.nan
    return total


def compute_group_delay(
    sos: np.ndarray,
    fs: float,
    frequencies_hz: np.ndarray | None = None,
    *,
    report_frequencies_hz: Sequence[float] = DEFAULT_GROUP_DELAY_FREQUENCIES,
) -> dict[str, object]:
    """Compute SOS-summed group delay, explicitly masking notch singularities."""

    fs = _positive_float(fs, "fs")
    if frequencies_hz is None:
        frequencies_hz = np.linspace(0.0, fs / 2.0, 32_769)
    frequencies_hz = np.asarray(frequencies_hz, dtype=np.float64)
    samples = _summed_sos_group_delay(sos, fs, frequencies_hz)

    report_frequencies = np.asarray(report_frequencies_hz, dtype=np.float64)
    if np.any(report_frequencies < 0.0) or np.any(report_frequencies > fs / 2.0):
        raise ValueError("group-delay report frequencies must lie in [0, Nyquist]")
    report_samples = _summed_sos_group_delay(sos, fs, report_frequencies)
    reports = []
    for frequency, delay_samples in zip(report_frequencies, report_samples):
        reports.append(
            {
                "frequency_hz": float(frequency),
                "samples": float(delay_samples),
                "seconds": float(delay_samples / fs),
                "defined": bool(np.isfinite(delay_samples)),
            }
        )
    return {
        "frequency_hz": frequencies_hz,
        "samples": samples,
        "seconds": samples / fs,
        "reports": tuple(reports),
    }


def direct_section_cascade(sos: np.ndarray, samples: np.ndarray) -> np.ndarray:
    """Reference a SOS cascade by applying each biquad with lfilter."""

    output = np.asarray(samples, dtype=np.float64)
    for row in np.asarray(sos, dtype=np.float64):
        output = signal.lfilter(row[:3], row[3:], output)
    return output


def compute_digital_nyquist(
    sos: np.ndarray,
    fs: float,
    positive_frequencies_hz: np.ndarray | None = None,
) -> dict[str, np.ndarray | float]:
    """Evaluate H(exp(j*omega)) on both branches of the unit circle."""

    if positive_frequencies_hz is None:
        positive_frequencies_hz = np.linspace(0.0, fs / 2.0, 40_001)
    positive_frequencies_hz = np.asarray(positive_frequencies_hz, dtype=np.float64)
    omega_positive = 2.0 * np.pi * positive_frequencies_hz / fs
    omega_negative = -omega_positive
    _, positive = signal.sosfreqz(sos, worN=omega_positive)
    _, negative = signal.sosfreqz(sos, worN=omega_negative)
    symmetry_error = float(np.max(np.abs(negative - np.conj(positive))))
    return {
        "frequency_hz": positive_frequencies_hz,
        "omega_positive": omega_positive,
        "omega_negative": omega_negative,
        "positive": positive,
        "negative": negative,
        "conjugate_symmetry_max_error": symmetry_error,
    }


def _figure_title(design: NotchDesign, detail: str) -> str:
    first = design.sections[0]
    return (
        f"{detail} | fs={design.fs:g} S/s, f0={first.f0_hz:g} Hz, "
        f"BW={first.bandwidth_hz:g} Hz, Q={first.q:g}"
    )


def _save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _harmonic_lines(ax: plt.Axes, design: NotchDesign) -> None:
    for section in design.sections:
        ax.axvline(section.f0_hz, color="0.72", linewidth=0.65, linestyle=":")


def plot_frequency_response(
    design: NotchDesign,
    response: Mapping[str, np.ndarray],
    group_delay: Mapping[str, object],
    output_dir: Path,
) -> None:
    """Save full, zoomed, per-notch, phase, and group-delay figures."""

    output_dir = Path(output_dir)
    frequency = np.asarray(response["frequency_hz"])
    single_db = np.asarray(response["single_magnitude_db"])
    cascade_db = np.asarray(response["cascade_magnitude_db"])

    fig, ax = plt.subplots(figsize=(11, 5.6), constrained_layout=True)
    ax.plot(frequency, single_db, label="Single 60 Hz biquad", linewidth=1.0)
    ax.plot(frequency, cascade_db, label="10-notch SOS cascade", linewidth=1.0)
    _harmonic_lines(ax, design)
    ax.set(xlabel="Frequency [Hz]", ylabel="Magnitude [dB]", ylim=(-140, 3))
    ax.set_xlim(0.0, design.fs / 2.0)
    ax.set_title(_figure_title(design, "Full-band magnitude response"))
    ax.grid(True, which="both", alpha=0.35)
    ax.legend()
    _save_figure(fig, output_dir / "frequency_response_full.png")

    zoom = frequency <= min(700.0, design.fs / 2.0)
    fig, ax = plt.subplots(figsize=(11, 5.6), constrained_layout=True)
    ax.plot(frequency[zoom], single_db[zoom], label="Single 60 Hz biquad")
    ax.plot(frequency[zoom], cascade_db[zoom], label="Harmonic cascade")
    _harmonic_lines(ax, design)
    ax.set(xlabel="Frequency [Hz]", ylabel="Magnitude [dB]", ylim=(-140, 3))
    ax.set_xlim(0.0, min(700.0, design.fs / 2.0))
    ax.set_title(_figure_title(design, "Low-frequency magnitude response"))
    ax.grid(True, which="both", alpha=0.35)
    ax.legend()
    _save_figure(fig, output_dir / "frequency_response_zoom.png")

    ncols = 2
    nrows = int(math.ceil(len(design.sections) / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(12, 2.9 * nrows), constrained_layout=True, squeeze=False
    )
    for ax, section in zip(axes.flat, design.sections):
        half_span = 5.0 * section.bandwidth_hz
        mask = np.abs(frequency - section.f0_hz) <= half_span
        _, section_h = signal.sosfreqz(
            design.sos[section.harmonic - 1 : section.harmonic],
            worN=frequency[mask],
            fs=design.fs,
        )
        ax.plot(frequency[mask], _magnitude_db(section_h), label="This biquad")
        ax.plot(frequency[mask], cascade_db[mask], "--", label="Full cascade")
        ax.axvline(section.f0_hz, color="k", linewidth=0.8, linestyle=":")
        ax.axvline(
            section.f0_hz - section.bandwidth_hz / 2.0,
            color="0.5",
            linewidth=0.7,
        )
        ax.axvline(
            section.f0_hz + section.bandwidth_hz / 2.0,
            color="0.5",
            linewidth=0.7,
        )
        ax.set(
            title=f"{section.f0_hz:g} Hz, BW={section.bandwidth_hz:g} Hz, Q={section.q:g}",
            xlabel="Frequency [Hz]",
            ylabel="Magnitude [dB]",
            ylim=(-140, 3),
        )
        ax.grid(True, alpha=0.35)
        ax.legend(fontsize=8)
    for ax in axes.flat[len(design.sections) :]:
        ax.set_visible(False)
    fig.suptitle(_figure_title(design, "Dense response around every harmonic"))
    _save_figure(fig, output_dir / "frequency_response_harmonics.png")

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True, constrained_layout=True)
    mask = frequency <= min(700.0, design.fs / 2.0)
    axes[0].plot(frequency[mask], response["cascade_wrapped_phase_rad"][mask])
    axes[1].plot(frequency[mask], response["cascade_unwrapped_phase_rad"][mask])
    for ax in axes:
        _harmonic_lines(ax, design)
        ax.grid(True, alpha=0.35)
        ax.set_ylabel("Phase [rad]")
    axes[0].set_title(_figure_title(design, "Wrapped and unwrapped phase"))
    axes[0].set_ylabel("Wrapped phase [rad]")
    axes[1].set_ylabel("Unwrapped phase [rad]")
    axes[1].set_xlabel("Frequency [Hz]")
    _save_figure(fig, output_dir / "phase_response.png")

    gd_frequency = np.asarray(group_delay["frequency_hz"])
    gd_samples = np.asarray(group_delay["samples"])
    gd_seconds = np.asarray(group_delay["seconds"])
    mask = gd_frequency <= min(700.0, design.fs / 2.0)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True, constrained_layout=True)
    axes[0].plot(gd_frequency[mask], gd_samples[mask])
    axes[1].plot(gd_frequency[mask], 1e3 * gd_seconds[mask])
    for ax in axes:
        _harmonic_lines(ax, design)
        ax.grid(True, alpha=0.35)
    axes[0].set_title(
        _figure_title(design, "SOS-summed group delay (undefined at notch centers)")
    )
    axes[0].set_ylabel("Group delay [samples]")
    axes[1].set_ylabel("Group delay [ms]")
    axes[1].set_xlabel("Frequency [Hz]")
    _save_figure(fig, output_dir / "group_delay.png")


def plot_impulse_response(
    impulse_results: Mapping[float, Mapping[str, np.ndarray | float]],
    output_path: Path,
    *,
    title: str = "IIR notch impulse response comparison",
) -> None:
    """Plot impulse response views for one or more sampling rates."""

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    epsilon = np.finfo(np.float64).tiny
    for fs, result in sorted(impulse_results.items()):
        time = np.asarray(result["time_seconds"])
        single = np.asarray(result["single"])
        cascade = np.asarray(result["cascade"])
        label_prefix = f"fs={fs:g} S/s"
        axes[0, 0].plot(time, single, linewidth=0.8, label=f"{label_prefix}, 60 Hz")
        axes[0, 0].plot(time, cascade, linewidth=0.8, label=f"{label_prefix}, cascade")
        initial = time <= 0.050
        axes[0, 1].plot(time[initial] * 1e3, single[initial], linewidth=0.8, label=f"{label_prefix}, 60 Hz")
        axes[0, 1].plot(time[initial] * 1e3, cascade[initial], linewidth=0.8, label=f"{label_prefix}, cascade")
        ring = (np.arange(time.size) > 0) & (time <= min(0.5, time[-1]))
        axes[1, 0].plot(time[ring], single[ring], linewidth=0.8, label=f"{label_prefix}, 60 Hz")
        axes[1, 0].plot(time[ring], cascade[ring], linewidth=0.8, label=f"{label_prefix}, cascade")
        axes[1, 1].plot(
            time,
            20.0 * np.log10(np.abs(single) + epsilon),
            linewidth=0.75,
            label=f"{label_prefix}, 60 Hz",
        )
        axes[1, 1].plot(
            time,
            20.0 * np.log10(np.abs(cascade) + epsilon),
            linewidth=0.75,
            label=f"{label_prefix}, cascade",
        )

    axes[0, 0].set(title="Complete response", xlabel="Time [s]", ylabel="h(t)")
    axes[0, 1].set(title="Initial 50 ms", xlabel="Time [ms]", ylabel="h(t)")
    axes[1, 0].set(
        title="Ring-down with direct impulse n=0 excluded",
        xlabel="Time [s]",
        ylabel="h(t)",
    )
    axes[1, 1].set(
        title="Logarithmic absolute envelope",
        xlabel="Time [s]",
        ylabel="20 log10(|h| + epsilon) [dB]",
        ylim=(-300, 5),
    )
    for ax in axes.flat:
        ax.grid(True, alpha=0.35)
        ax.legend(fontsize=8)
    fig.suptitle(title)
    _save_figure(fig, Path(output_path))


def plot_digital_nyquist(
    design: NotchDesign,
    sos: np.ndarray,
    output_path: Path,
    *,
    title_label: str,
    notch_sections: Sequence[NotchSection],
) -> float:
    """Plot Re{H(exp(jw))} versus Im{H(exp(jw))}, not pole-zero data."""

    positive_grid = build_frequency_grid(
        design.fs,
        [section.f0_hz for section in notch_sections],
        [section.bandwidth_hz for section in notch_sections],
        coarse_points=40_001,
        dense_points_per_notch=2_001,
    )
    data = compute_digital_nyquist(sos, design.fs, positive_grid)
    positive = np.asarray(data["positive"])
    negative = np.asarray(data["negative"])
    points = np.column_stack((positive.real, positive.imag)).reshape(-1, 1, 2)
    segments = np.concatenate((points[:-1], points[1:]), axis=1)

    fig, ax = plt.subplots(figsize=(8.5, 8), constrained_layout=True)
    collection = LineCollection(segments, cmap="viridis", linewidth=1.35)
    collection.set_array(positive_grid[:-1])
    ax.add_collection(collection)
    ax.plot(
        negative.real,
        negative.imag,
        "--",
        color="0.45",
        linewidth=0.9,
        label="Negative-frequency branch",
    )
    ax.scatter([0.0], [0.0], marker="+", s=90, color="k", label="Origin")
    ax.scatter(
        [positive[0].real],
        [positive[0].imag],
        marker="o",
        s=50,
        color="tab:green",
        label="H(0)",
    )
    ax.scatter(
        [positive[-1].real],
        [positive[-1].imag],
        marker="s",
        s=45,
        color="tab:orange",
        label="H(Nyquist)",
    )
    for index, section in enumerate(notch_sections):
        _, notch_h = signal.sosfreqz(sos, worN=np.asarray([section.f0_hz]), fs=design.fs)
        ax.scatter(
            notch_h.real,
            notch_h.imag,
            marker="x",
            s=45,
            color="tab:red",
            label="H(notch centers)" if index == 0 else None,
        )
    colorbar = fig.colorbar(collection, ax=ax)
    colorbar.set_label("Positive frequency [Hz]")
    ax.set_xlabel("Re{H(exp(j omega))}")
    ax.set_ylabel("Im{H(exp(j omega))}")
    first = design.sections[0]
    ax.set_title(
        f"Digital Nyquist: {title_label}\n"
        f"fs={design.fs:g} S/s, f0={first.f0_hz:g} Hz, "
        f"BW={first.bandwidth_hz:g} Hz, Q={first.q:g}; "
        f"symmetry error={data['conjugate_symmetry_max_error']:.3e}"
    )
    ax.grid(True, alpha=0.35)
    ax.relim()
    ax.autoscale_view()
    ax.set_aspect("equal", adjustable="box")
    ax.legend(fontsize=8, loc="best")
    _save_figure(fig, Path(output_path))
    return float(data["conjugate_symmetry_max_error"])


def plot_pole_zero(design: NotchDesign, output_path: Path) -> None:
    """Plot every SOS pole and zero without forming a high-order polynomial."""

    fig, ax = plt.subplots(figsize=(8.5, 8), constrained_layout=True)
    angle = np.linspace(0.0, 2.0 * np.pi, 1000)
    ax.plot(np.cos(angle), np.sin(angle), color="k", linewidth=1.0, label="Unit circle")
    colors = plt.cm.turbo(np.linspace(0.05, 0.95, len(design.sections)))
    for section, color in zip(design.sections, colors):
        label = f"{section.f0_hz:g} Hz"
        ax.scatter(
            section.zeros.real,
            section.zeros.imag,
            marker="o",
            facecolors="none",
            edgecolors=[color],
            s=65,
            linewidth=1.3,
            label=f"Zeros {label}",
        )
        ax.scatter(
            section.poles.real,
            section.poles.imag,
            marker="x",
            color=[color],
            s=55,
            linewidth=1.4,
            label=f"Poles {label}",
        )
    ax.set_xlabel("Real(z)")
    ax.set_ylabel("Imag(z)")
    ax.set_title(_figure_title(design, "SOS poles and zeros"))
    ax.grid(True, alpha=0.35)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-1.08, 1.08)
    ax.set_ylim(-1.08, 1.08)
    ax.legend(fontsize=7, ncol=2, loc="lower left")
    _save_figure(fig, Path(output_path))


def _tone_amplitude(values: np.ndarray, fs: float, frequency_hz: float) -> float:
    index = np.arange(values.size, dtype=np.float64)
    phasor = np.exp(-2j * np.pi * frequency_hz * index / fs)
    return float(2.0 * np.abs(np.dot(values, phasor)) / values.size)


def run_synthetic_test(
    sos: np.ndarray,
    fs: float,
    notch_frequencies_hz: Sequence[float],
    *,
    duration_seconds: float = 5.0,
    seed: int = 0x5EED,
) -> dict[str, object]:
    """Filter a deterministic low-frequency signal plus mains harmonics/noise."""

    fs = _positive_float(fs, "fs")
    duration_seconds = _positive_float(duration_seconds, "duration_seconds")
    n_samples = int(math.ceil(duration_seconds * fs))
    if n_samples < int(2.0 * fs):
        raise ValueError("synthetic test duration must be at least 2 seconds")
    time = np.arange(n_samples, dtype=np.float64) / fs
    rng = np.random.default_rng(seed)
    desired = 0.35 * np.sin(2.0 * np.pi * 7.0 * time)
    desired += 0.20 * np.sin(2.0 * np.pi * 23.0 * time + 0.2)
    interference = np.zeros_like(time)
    for harmonic, frequency in enumerate(notch_frequencies_hz, start=1):
        interference += (0.30 / math.sqrt(harmonic)) * np.sin(
            2.0 * np.pi * frequency * time + 0.17 * harmonic
        )
    white_noise = 0.02 * rng.standard_normal(n_samples)
    input_signal = desired + interference + white_noise
    output_zero_state = signal.sosfilt(sos, input_signal)
    zi = signal.sosfilt_zi(sos) * input_signal[0]
    output_initialized, _ = signal.sosfilt(sos, input_signal, zi=zi)

    discard = min(n_samples // 2, max(int(fs), int(math.ceil(0.8 * fs))))
    settled_input = input_signal[discard:]
    settled_output = output_zero_state[discard:]
    nperseg = min(settled_input.size, max(8192, int(2.0 * fs)))
    frequencies_psd, input_psd = signal.welch(
        settled_input, fs=fs, nperseg=nperseg, scaling="density"
    )
    _, output_psd = signal.welch(
        settled_output, fs=fs, nperseg=nperseg, scaling="density"
    )

    harmonic_metrics = []
    for frequency in notch_frequencies_hz:
        before = _tone_amplitude(settled_input, fs, frequency)
        after = _tone_amplitude(settled_output, fs, frequency)
        attenuation_db = 20.0 * math.log10(max(before, np.finfo(float).tiny) / max(after, np.finfo(float).tiny))
        harmonic_metrics.append(
            {
                "frequency_hz": float(frequency),
                "before_amplitude": before,
                "after_amplitude": after,
                "attenuation_db": attenuation_db,
            }
        )

    passband_frequencies = np.asarray(
        [frequency for frequency in (5.0, 10.0, 30.0, 50.0, 75.0, 100.0, 250.0, 450.0, 700.0) if frequency < fs / 2.0]
    )
    _, passband_h = signal.sosfreqz(sos, worN=passband_frequencies, fs=fs)
    passband_metrics = tuple(
        {
            "frequency_hz": float(frequency),
            "gain_db": float(_magnitude_db(np.asarray([value]))[0]),
        }
        for frequency, value in zip(passband_frequencies, passband_h)
    )

    arrays_to_check = (
        time,
        input_signal,
        output_zero_state,
        output_initialized,
        frequencies_psd,
        input_psd,
        output_psd,
    )
    if any(np.any(~np.isfinite(values)) for values in arrays_to_check):
        raise RuntimeError("synthetic test produced NaN or inf")
    return {
        "time_seconds": time,
        "input": input_signal,
        "output": output_zero_state,
        "output_initialized": output_initialized,
        "psd_frequency_hz": frequencies_psd,
        "input_psd": input_psd,
        "output_psd": output_psd,
        "harmonic_metrics": tuple(harmonic_metrics),
        "passband_metrics": passband_metrics,
        "discard_samples": discard,
    }


def plot_synthetic_test(
    design: NotchDesign,
    synthetic: Mapping[str, object],
    output_path: Path,
) -> None:
    time = np.asarray(synthetic["time_seconds"])
    input_signal = np.asarray(synthetic["input"])
    output = np.asarray(synthetic["output"])
    initialized = np.asarray(synthetic["output_initialized"])
    psd_frequency = np.asarray(synthetic["psd_frequency_hz"])
    input_psd = np.asarray(synthetic["input_psd"])
    output_psd = np.asarray(synthetic["output_psd"])
    metrics = synthetic["harmonic_metrics"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    settled_start = min(time[-1] * 0.5, 1.0)
    trace = (time >= settled_start) & (time <= settled_start + 0.20)
    axes[0, 0].plot(time[trace], input_signal[trace], label="Before", linewidth=0.8)
    axes[0, 0].plot(time[trace], output[trace], label="After", linewidth=0.9)
    axes[0, 0].set(
        title="Settled time trace",
        xlabel="Time [s]",
        ylabel="Amplitude [a.u.]",
    )

    psd_mask = psd_frequency <= min(700.0, design.fs / 2.0)
    axes[0, 1].semilogy(psd_frequency[psd_mask], input_psd[psd_mask], label="Before")
    axes[0, 1].semilogy(psd_frequency[psd_mask], output_psd[psd_mask], label="After")
    _harmonic_lines(axes[0, 1], design)
    axes[0, 1].set(
        title="Welch power spectral density",
        xlabel="Frequency [Hz]",
        ylabel="PSD [a.u.^2/Hz]",
    )

    harmonic_frequency = [entry["frequency_hz"] for entry in metrics]
    attenuation = [entry["attenuation_db"] for entry in metrics]
    axes[1, 0].bar(harmonic_frequency, attenuation, width=35.0)
    axes[1, 0].set(
        title="Measured harmonic attenuation after transient",
        xlabel="Harmonic frequency [Hz]",
        ylabel="Attenuation [dB]",
    )

    transient = time <= min(0.25, time[-1])
    axes[1, 1].plot(
        time[transient] * 1e3,
        output[transient],
        label="Zero SOS state",
        linewidth=0.8,
    )
    axes[1, 1].plot(
        time[transient] * 1e3,
        initialized[transient],
        label="sosfilt_zi initialized",
        linewidth=0.8,
    )
    axes[1, 1].set(
        title="Startup transient caused by state reset",
        xlabel="Time [ms]",
        ylabel="Output [a.u.]",
    )
    for ax in axes.flat:
        ax.grid(True, which="both", alpha=0.35)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(fontsize=8)
    fig.suptitle(_figure_title(design, "Deterministic synthetic validation"))
    _save_figure(fig, Path(output_path))


def _complex_text(value: complex) -> str:
    return f"{value.real:.17g}{value.imag:+.17g}j"


def _json_safe(value):
    """Convert NumPy values and intentional NaNs into strict JSON values."""

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else None
    return value


def write_coefficients_csv(design: NotchDesign, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "harmonic",
                "f0_hz",
                "bandwidth_hz",
                "q",
                "b0",
                "b1",
                "b2",
                "a0",
                "a1",
                "a2",
                "zero_0",
                "zero_1",
                "pole_0",
                "pole_1",
                "pole_radius",
            ]
        )
        for section in design.sections:
            writer.writerow(
                [
                    section.harmonic,
                    f"{section.f0_hz:.17g}",
                    f"{section.bandwidth_hz:.17g}",
                    f"{section.q:.17g}",
                    *(f"{value:.17g}" for value in section.b),
                    *(f"{value:.17g}" for value in section.a),
                    *(_complex_text(value) for value in section.zeros),
                    *(_complex_text(value) for value in section.poles),
                    f"{section.pole_radius:.17g}",
                ]
            )


def validate_design(
    design: NotchDesign,
    response: Mapping[str, np.ndarray],
    impulse: Mapping[str, np.ndarray | float],
    group_delay: Mapping[str, object],
    synthetic: Mapping[str, object],
) -> tuple[dict[str, object], list[str]]:
    """Run numerical acceptance checks and return metrics plus report lines."""

    _, dc_h = signal.sosfreqz(design.sos, worN=np.asarray([0.0]), fs=design.fs)
    dc_gain = float(abs(dc_h[0]))
    all_poles = np.concatenate([section.poles for section in design.sections])
    max_pole_radius = float(np.max(np.abs(all_poles)))
    stable = bool(np.all(np.abs(all_poles) < 1.0))
    center_rows = []
    edge_rows = []
    for section in design.sections:
        _, center_h = signal.sosfreqz(
            design.sos, worN=np.asarray([section.f0_hz]), fs=design.fs
        )
        center_db = float(_magnitude_db(center_h)[0])
        edges = np.asarray(
            [
                section.f0_hz - section.bandwidth_hz / 2.0,
                section.f0_hz + section.bandwidth_hz / 2.0,
            ]
        )
        _, section_edge_h = signal.sosfreqz(
            design.sos[section.harmonic - 1 : section.harmonic],
            worN=edges,
            fs=design.fs,
        )
        edge_db = _magnitude_db(section_edge_h)
        center_rows.append(
            {
                "frequency_hz": section.f0_hz,
                "magnitude_db": center_db,
                "attenuation_db": -center_db,
                "passes_80_db": bool(center_db <= -80.0),
            }
        )
        edge_rows.append(
            {
                "frequency_hz": section.f0_hz,
                "lower_db": float(edge_db[0]),
                "upper_db": float(edge_db[1]),
                "approximately_minus_3_db": bool(
                    np.all(np.abs(edge_db + 3.01029995664) <= 0.20)
                ),
            }
        )

    rng = np.random.default_rng(12345)
    reference_input = rng.standard_normal(10_000).astype(np.float64)
    sos_output = signal.sosfilt(design.sos, reference_input)
    direct_output = direct_section_cascade(design.sos, reference_input)
    cascade_error = float(np.max(np.abs(sos_output - direct_output)))

    response_arrays = [
        value
        for key, value in response.items()
        if isinstance(value, np.ndarray) and "phase" not in key
    ]
    impulse_arrays = [
        value for value in impulse.values() if isinstance(value, np.ndarray)
    ]
    finite_without_group_singularities = bool(
        all(np.all(np.isfinite(value)) for value in response_arrays + impulse_arrays)
    )
    nyquist = compute_digital_nyquist(
        design.sos,
        design.fs,
        build_frequency_grid(
            design.fs,
            design.notch_frequencies_hz,
            design.bandwidths_hz,
            coarse_points=8_193,
            dense_points_per_notch=401,
        ),
    )
    tau_seconds = 1.0 / (np.pi * design.requested_bandwidth_hz)
    tau_samples = tau_seconds * design.fs
    settling_seconds = 4.6 * tau_seconds
    pole_tau_seconds = -1.0 / (design.fs * math.log(max_pole_radius))
    b0_b2_max_error = float(
        np.max(np.abs(design.sos[:, 0] - design.sos[:, 2]))
    )
    b1_a1_max_error = float(
        np.max(np.abs(design.sos[:, 1] - design.sos[:, 4]))
    )

    checks = {
        "dc_gain_close_to_one": bool(abs(dc_gain - 1.0) <= 1e-10),
        "all_notches_at_least_80_db": bool(
            all(row["passes_80_db"] for row in center_rows)
        ),
        "all_poles_stable": stable,
        "all_bandwidth_edges_near_minus_3_db": bool(
            all(row["approximately_minus_3_db"] for row in edge_rows)
        ),
        "sosfilt_matches_direct_cascade": bool(cascade_error <= 1e-10),
        "no_unexpected_nan_or_inf": finite_without_group_singularities,
        "nyquist_conjugate_symmetry": bool(
            nyquist["conjugate_symmetry_max_error"] <= 1e-12
        ),
        "notch_coefficient_identities": bool(
            b0_b2_max_error <= 1e-15 and b1_a1_max_error <= 1e-15
        ),
    }
    metrics: dict[str, object] = {
        "fs": design.fs,
        "sample_period_seconds": 1.0 / design.fs,
        "mode": design.mode,
        "sections": len(design.sections),
        "filter_order": design.order,
        "stored_coefficient_count": 6 * len(design.sections),
        "independent_normalized_coefficient_count": 5 * len(design.sections),
        "sos_state_count": 2 * len(design.sections),
        "standard_multiplications_per_sample": 5 * len(design.sections),
        "symmetry_optimized_multiplications_per_sample": 3 * len(design.sections),
        "dc_gain": dc_gain,
        "max_pole_radius": max_pole_radius,
        "tau_seconds": tau_seconds,
        "tau_samples": tau_samples,
        "settling_1_percent_seconds": settling_seconds,
        "settling_1_percent_samples": settling_seconds * design.fs,
        "pole_derived_tau_seconds": pole_tau_seconds,
        "b0_equals_b2_max_abs_error": b0_b2_max_error,
        "b1_equals_a1_max_abs_error": b1_a1_max_error,
        "center_response": center_rows,
        "bandwidth_edges": edge_rows,
        "group_delay": group_delay["reports"],
        "direct_cascade_max_abs_error": cascade_error,
        "nyquist_conjugate_symmetry_max_error": nyquist[
            "conjugate_symmetry_max_error"
        ],
        "synthetic_harmonic_attenuation": synthetic["harmonic_metrics"],
        "synthetic_passband_gain": synthetic["passband_metrics"],
        "checks": checks,
    }

    lines = [
        "Float64 harmonic IIR notch validation",
        "=" * 44,
        f"sampling rate: {design.fs:.9g} S/s",
        f"sample period: {1.0 / design.fs:.12g} s",
        f"mode: {design.mode}",
        f"valid SOS sections: {len(design.sections)}",
        f"total filter order: {design.order}",
        f"stored coefficients (including a0): {6 * len(design.sections)}",
        f"independent normalized coefficients: {5 * len(design.sections)}",
        f"SOS state values (DF-II transposed): {2 * len(design.sections)}",
        f"standard multiplications/sample: {5 * len(design.sections)}",
        f"possible b0=b2, b1=a1 optimized multiplications/sample: {3 * len(design.sections)}",
        f"max |b0-b2|: {b0_b2_max_error:.3e}",
        f"max |b1-a1|: {b1_a1_max_error:.3e}",
        f"DC gain: {dc_gain:.17g}",
        f"maximum pole radius: {max_pole_radius:.17g}",
        f"all poles inside unit circle: {stable}",
        f"theoretical tau = 1/(pi*BW): {tau_seconds:.12g} s = {tau_samples:.6f} samples",
        f"pole-derived slowest tau: {pole_tau_seconds:.12g} s",
        f"4.6*tau (about 1%): {settling_seconds:.12g} s = {settling_seconds * design.fs:.6f} samples",
        "",
        "SOS coefficients and poles",
        "-" * 44,
    ]
    for section in design.sections:
        lines.extend(
            [
                f"harmonic {section.harmonic}: f0={section.f0_hz:g} Hz, "
                f"BW={section.bandwidth_hz:g} Hz, Q={section.q:g}",
                "  SOS: " + ", ".join(f"{value:.17g}" for value in np.r_[section.b, section.a]),
                "  poles: " + ", ".join(_complex_text(value) for value in section.poles),
                f"  pole radius: {section.pole_radius:.17g}",
            ]
        )
    if design.excluded_harmonics:
        lines.append("")
        lines.append("Excluded harmonics (at or above Nyquist):")
        lines.extend(
            f"  harmonic {harmonic}: {frequency:g} Hz"
            for harmonic, frequency in design.excluded_harmonics
        )
    lines.extend(["", "Notch centers and -3 dB edges", "-" * 44])
    for center, edge in zip(center_rows, edge_rows):
        lines.append(
            f"{center['frequency_hz']:8.3f} Hz: center={center['magnitude_db']:10.4f} dB; "
            f"edges=({edge['lower_db']:.5f}, {edge['upper_db']:.5f}) dB"
        )
    lines.extend(["", "Group delay", "-" * 44])
    for report in group_delay["reports"]:
        if report["defined"]:
            lines.append(
                f"{report['frequency_hz']:8.3f} Hz: {report['samples']:.9g} samples, "
                f"{report['seconds']:.12g} s"
            )
        else:
            lines.append(
                f"{report['frequency_hz']:8.3f} Hz: NaN (undefined at a notch zero)"
            )
    lines.extend(["", "Synthetic harmonic attenuation", "-" * 44])
    for row in synthetic["harmonic_metrics"]:
        lines.append(
            f"{row['frequency_hz']:8.3f} Hz: before={row['before_amplitude']:.9g}, "
            f"after={row['after_amplitude']:.9g}, "
            f"attenuation={row['attenuation_db']:.6f} dB"
        )
    lines.extend(["", "Non-harmonic passband probes", "-" * 44])
    for row in synthetic["passband_metrics"]:
        lines.append(
            f"{row['frequency_hz']:8.3f} Hz: gain={row['gain_db']:.9f} dB"
        )
    lines.extend(["", "Validation checks", "-" * 44])
    for name, passed in checks.items():
        lines.append(f"{'PASS' if passed else 'WARNING'}: {name}")
    lines.append(f"direct cascade max absolute error: {cascade_error:.3e}")
    lines.append(
        "Nyquist conjugate-symmetry max error: "
        f"{nyquist['conjugate_symmetry_max_error']:.3e}"
    )
    if not checks["all_notches_at_least_80_db"]:
        warnings.warn("one or more notch centers did not reach 80 dB attenuation")
    return metrics, lines


def run_analysis_for_rate(
    fs: float,
    *,
    mains_frequency: float,
    n_harmonics: int,
    bandwidth_hz: float,
    mode: str,
    impulse_duration: float,
    synthetic_duration: float,
    output_dir: Path,
) -> dict[str, object]:
    design = _design_notch_details(
        fs,
        mains_frequency,
        n_harmonics,
        bandwidth_hz,
        mode,
    )
    rate_dir = output_dir / f"fs_{int(fs) if float(fs).is_integer() else fs:g}"
    rate_dir.mkdir(parents=True, exist_ok=True)
    grid = build_frequency_grid(
        fs,
        design.notch_frequencies_hz,
        design.bandwidths_hz,
    )
    response = compute_frequency_response(
        design.sos,
        fs,
        grid,
        notch_frequencies_hz=design.notch_frequencies_hz,
        bandwidth_hz=design.bandwidths_hz,
    )
    impulse = compute_impulse_response(design.sos, fs, impulse_duration)
    group_delay = compute_group_delay(design.sos, fs, grid)
    synthetic = run_synthetic_test(
        design.sos,
        fs,
        design.notch_frequencies_hz,
        duration_seconds=synthetic_duration,
    )

    write_coefficients_csv(design, rate_dir / "coefficients.csv")
    plot_frequency_response(design, response, group_delay, rate_dir)
    plot_impulse_response(
        {fs: impulse},
        rate_dir / "impulse_response.png",
        title=_figure_title(design, "Impulse response"),
    )
    symmetry_single = plot_digital_nyquist(
        design,
        design.sos[:1],
        rate_dir / "nyquist_single_60Hz.png",
        title_label="single 60 Hz notch",
        notch_sections=design.sections[:1],
    )
    symmetry_cascade = plot_digital_nyquist(
        design,
        design.sos,
        rate_dir / "nyquist_cascade.png",
        title_label="harmonic SOS cascade",
        notch_sections=design.sections,
    )
    plot_pole_zero(design, rate_dir / "pole_zero.png")
    plot_synthetic_test(design, synthetic, rate_dir / "synthetic_test.png")
    metrics, validation_lines = validate_design(
        design, response, impulse, group_delay, synthetic
    )
    metrics["nyquist_plot_single_symmetry_error"] = symmetry_single
    metrics["nyquist_plot_cascade_symmetry_error"] = symmetry_cascade
    (rate_dir / "validation.txt").write_text(
        "\n".join(validation_lines) + "\n", encoding="utf-8"
    )
    (rate_dir / "metrics.json").write_text(
        json.dumps(_json_safe(metrics), indent=2, allow_nan=False), encoding="utf-8"
    )
    return {
        "design": design,
        "response": response,
        "impulse": impulse,
        "group_delay": group_delay,
        "synthetic": synthetic,
        "metrics": metrics,
        "output_dir": rate_dir,
    }


def write_cross_rate_comparison(
    analyses: Mapping[float, Mapping[str, object]], output_dir: Path
) -> None:
    impulse_results = {
        fs: analysis["impulse"] for fs, analysis in analyses.items()
    }
    labels = ", ".join(f"{fs:g} S/s" for fs in sorted(analyses))
    plot_impulse_response(
        impulse_results,
        output_dir / "comparison_10k_100k.png",
        title=f"Time-axis impulse comparison: {labels}",
    )
    lines = ["Cross-sampling-rate time-constant comparison", "=" * 48]
    pole_taus = []
    theoretical_taus = []
    for fs, analysis in sorted(analyses.items()):
        metrics = analysis["metrics"]
        pole_taus.append(float(metrics["pole_derived_tau_seconds"]))
        theoretical_taus.append(float(metrics["tau_seconds"]))
        lines.append(
            f"fs={fs:g} S/s: theoretical tau={metrics['tau_seconds']:.12g} s, "
            f"tau={metrics['tau_samples']:.6f} samples, "
            f"pole-derived tau={metrics['pole_derived_tau_seconds']:.12g} s"
        )
    theoretical_spread = max(theoretical_taus) - min(theoretical_taus)
    pole_relative_spread = (
        (max(pole_taus) - min(pole_taus)) / np.mean(pole_taus)
        if len(pole_taus) > 1
        else 0.0
    )
    lines.extend(
        [
            f"theoretical seconds-domain tau spread: {theoretical_spread:.3e} s",
            f"pole-derived relative tau spread: {pole_relative_spread:.3e}",
            "PASS: seconds-domain theoretical tau is sampling-rate independent"
            if theoretical_spread <= 1e-15
            else "WARNING: seconds-domain theoretical tau differs",
            "PASS: pole-derived seconds-domain tau agrees across rates"
            if pole_relative_spread <= 1e-3
            else "WARNING: pole-derived seconds-domain tau differs by more than 0.1%",
        ]
    )
    (output_dir / "comparison_validation.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze float64 SOS IIR notches at mains harmonics."
    )
    parser.add_argument(
        "--sample-rates",
        nargs="+",
        type=float,
        default=[10_000.0, 100_000.0],
        help="sampling rates in samples/second",
    )
    parser.add_argument("--mains-frequency", type=float, default=60.0)
    parser.add_argument("--harmonics", type=int, default=10)
    parser.add_argument("--bandwidth", type=float, default=2.0)
    parser.add_argument(
        "--mode",
        choices=("constant_bandwidth", "constant_q"),
        default="constant_bandwidth",
    )
    parser.add_argument("--impulse-duration", type=float, default=2.0)
    parser.add_argument("--synthetic-duration", type=float, default=5.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    analyses: dict[float, dict[str, object]] = {}
    for fs in args.sample_rates:
        print(f"Analyzing fs={fs:g} S/s ...", flush=True)
        analysis = run_analysis_for_rate(
            fs,
            mains_frequency=args.mains_frequency,
            n_harmonics=args.harmonics,
            bandwidth_hz=args.bandwidth,
            mode=args.mode,
            impulse_duration=args.impulse_duration,
            synthetic_duration=args.synthetic_duration,
            output_dir=output_dir,
        )
        analyses[float(fs)] = analysis
        metrics = analysis["metrics"]
        print(
            f"  order={metrics['filter_order']}, DC gain={metrics['dc_gain']:.12g}, "
            f"max pole radius={metrics['max_pole_radius']:.12g}",
            flush=True,
        )
        for report in analysis["group_delay"]["reports"]:
            if report["defined"]:
                print(
                    f"  GD {report['frequency_hz']:6.1f} Hz: "
                    f"{report['samples']:12.6g} samples = {report['seconds']:.9g} s"
                )
            else:
                print(
                    f"  GD {report['frequency_hz']:6.1f} Hz: NaN "
                    "(undefined at notch center)"
                )
        print(f"  results: {analysis['output_dir']}", flush=True)
    write_cross_rate_comparison(analyses, output_dir)
    print(f"Completed float64 analysis in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
