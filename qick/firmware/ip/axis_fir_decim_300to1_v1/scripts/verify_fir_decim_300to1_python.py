# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""Python-level validation for axis_fir_decim_300to1_v1."""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np

from fir_decim_300to1_model import (
    REPORT_DIR,
    cascade_decim_300to1_fixed,
    frequency_response_metrics,
    load_quantized_coefficients,
    design_float_coefficients,
)


FS_IN = 300e6
FS_OUT = 1e6


def tone(freq_hz: float, n: int, amp: float = 12000.0) -> np.ndarray:
    t = np.arange(n) / FS_IN
    return amp * np.sin(2 * np.pi * freq_hz * t)


def estimate_tone_amplitude(samples: np.ndarray, freq_hz: float, fs_hz: float) -> float:
    n = len(samples)
    t = np.arange(n) / fs_hz
    ref_s = np.sin(2 * np.pi * freq_hz * t)
    ref_c = np.cos(2 * np.pi * freq_hz * t)
    a = 2.0 * np.dot(samples, ref_s) / n
    b = 2.0 * np.dot(samples, ref_c) / n
    return float(np.sqrt(a * a + b * b))


def snr_db(signal: np.ndarray, reference: np.ndarray) -> float:
    err = np.asarray(signal) - np.asarray(reference)
    p_sig = np.mean(np.asarray(reference, dtype=np.float64) ** 2)
    p_err = np.mean(err.astype(np.float64) ** 2)
    return float(10 * np.log10((p_sig + 1e-18) / (p_err + 1e-18)))


def main() -> None:
    coeffs_q = load_quantized_coefficients()
    coeffs_f = design_float_coefficients()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    n = 300_000
    rng = np.random.default_rng(20260708)

    results: dict[str, float | int | dict] = {}
    freq_metrics = frequency_response_metrics(coeffs_f)
    results["frequency_response"] = freq_metrics

    # Impulse.
    impulse = np.zeros(60_000, dtype=np.int64)
    impulse[0] = 12000
    imp0, imp1 = cascade_decim_300to1_fixed(impulse, -impulse, coeffs_q)
    results["impulse_output_count"] = int(len(imp0))
    results["impulse_peak_lane0"] = int(np.max(np.abs(imp0)))

    # Passband tones.
    tone100 = np.rint(tone(100e3, n)).astype(np.int64)
    out100, _ = cascade_decim_300to1_fixed(tone100, tone100, coeffs_q)
    out100_ss = out100[len(out100) // 2 :]
    amp100 = estimate_tone_amplitude(out100_ss, 100e3, FS_OUT)
    results["tone_100khz_amp_db"] = float(20 * np.log10((amp100 / 12000.0) + 1e-18))

    tone400 = np.rint(tone(400e3, n)).astype(np.int64)
    out400, _ = cascade_decim_300to1_fixed(tone400, tone400, coeffs_q)
    out400_ss = out400[len(out400) // 2 :]
    amp400 = estimate_tone_amplitude(out400_ss, 400e3, FS_OUT)
    results["tone_400khz_amp_db"] = float(20 * np.log10((amp400 / 12000.0) + 1e-18))

    tone2m = np.rint(tone(2e6, n)).astype(np.int64)
    out2m, _ = cascade_decim_300to1_fixed(tone2m, tone2m, coeffs_q)
    out2m_ss = out2m[len(out2m) // 2 :]
    amp2m = np.sqrt(2.0) * np.sqrt(np.mean(out2m_ss.astype(np.float64) ** 2))
    results["tone_2mhz_atten_db"] = float(-20 * np.log10((amp2m / 12000.0) + 1e-18))

    # Mixed signal with deterministic out-of-band tones and high-frequency noise.
    t = np.arange(n) / FS_IN
    desired = 9000.0 * np.sin(2 * np.pi * 100e3 * t)
    interferers = (
        4500.0 * np.sin(2 * np.pi * 2.0e6 * t + 0.2)
        + 3500.0 * np.sin(2 * np.pi * 5.0e6 * t + 1.1)
        + 2500.0 * np.sin(2 * np.pi * 80.0e6 * t + 0.7)
    )
    noise = rng.normal(0.0, 1800.0, n)
    mixed = np.clip(np.rint(desired + interferers + noise), -32768, 32767).astype(np.int64)
    clean = np.rint(desired).astype(np.int64)

    fir_mixed, _ = cascade_decim_300to1_fixed(mixed, mixed, coeffs_q)
    fir_clean, _ = cascade_decim_300to1_fixed(clean, clean, coeffs_q)
    naive_mixed = mixed[299::300]
    naive_clean = clean[299::300]
    min_len = min(len(fir_mixed), len(naive_mixed), len(fir_clean), len(naive_clean))
    fir_mixed = fir_mixed[-min_len:]
    fir_clean = fir_clean[-min_len:]
    naive_mixed = naive_mixed[-min_len:]
    naive_clean = naive_clean[-min_len:]

    fir_snr = snr_db(fir_mixed, fir_clean)
    naive_snr = snr_db(naive_mixed, naive_clean)
    results["mixed_fir_snr_db"] = fir_snr
    results["mixed_naive_snr_db"] = naive_snr
    results["mixed_fir_snr_improvement_db"] = fir_snr - naive_snr
    results["mixed_output_count"] = int(len(fir_mixed))

    thresholds = {
        "100 kHz amplitude error <= 0.5 dB": abs(results["tone_100khz_amp_db"]) <= 0.5,
        "400 kHz amplitude error <= 0.5 dB": abs(results["tone_400khz_amp_db"]) <= 0.5,
        "passband ripple <= 1.0 dB": float(freq_metrics["passband_ripple_db"]) <= 1.0,
        "2 MHz attenuation >= 50 dB": results["tone_2mhz_atten_db"] >= 50.0,
        "FIR SNR improvement over naive >= 15 dB": results["mixed_fir_snr_improvement_db"] >= 15.0,
    }
    results["thresholds"] = thresholds

    with (REPORT_DIR / "python_noise_validation.json").open("w", encoding="ascii") as f:
        json.dump(results, f, indent=2)

    fig, ax = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
    count = min(300, min_len)
    x = np.arange(count) / FS_OUT * 1e6
    ax[0].plot(x, naive_mixed[:count], label="naive sample drop", alpha=0.8)
    ax[0].plot(x, fir_mixed[:count], label="FIR decimation", alpha=0.8)
    ax[0].plot(x, fir_clean[:count], label="clean expected", linewidth=1.0)
    ax[0].set_xlabel("time (us)")
    ax[0].set_ylabel("sample")
    ax[0].grid(True)
    ax[0].legend()
    ax[1].bar(["naive", "FIR"], [naive_snr, fir_snr])
    ax[1].set_ylabel("SNR (dB)")
    ax[1].grid(True, axis="y")
    fig.savefig(REPORT_DIR / "python_noise_validation.png", dpi=160)
    plt.close(fig)

    with (REPORT_DIR / "python_validation_summary.txt").open("w", encoding="ascii") as f:
        f.write("axis_fir_decim_300to1_v1 Python validation\n")
        f.write("============================================\n\n")
        for key, value in results.items():
            if key != "thresholds":
                f.write(f"{key}: {value}\n")
        f.write("\nThresholds\n----------\n")
        for key, value in thresholds.items():
            f.write(f"{key}: {'PASS' if value else 'FAIL'}\n")

    failed = [name for name, ok in thresholds.items() if not ok]
    if failed:
        raise SystemExit("Python validation failed: " + "; ".join(failed))

    print("PASS: Python FIR validation")


if __name__ == "__main__":
    main()
