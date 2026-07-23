# 60 Hz Harmonic IIR Notch Reference Model

This directory contains a Python `float64` reference model for removing 60 Hz
mains interference and its harmonics. It compares independently designed
filters at 10 kSPS and 100 kSPS. It is an analysis model only: it does not
contain HDL, coefficient quantization, fixed-point arithmetic, or an FPGA
implementation.

## Installation

Python 3.10 or newer is recommended. Create or activate an environment, then
install the local requirements:

```powershell
cd qick\tools\mains_notch_analysis
python -m pip install -r requirements.txt
```

## Running the analysis

The default command analyzes 10 kSPS and 100 kSPS, creates ten notches from
60 Hz through 600 Hz, and writes all reports and figures under `results/`:

```powershell
python notch_filter_analysis.py
```

The equivalent explicit command is:

```powershell
python notch_filter_analysis.py `
    --sample-rates 10000 100000 `
    --mains-frequency 60 `
    --harmonics 10 `
    --bandwidth 2 `
    --mode constant_bandwidth `
    --impulse-duration 2 `
    --output-dir results
```

Run the tests with:

```powershell
python -m pytest -q
```

## Filter structure

Every harmonic is implemented as one second-order notch produced by
`scipy.signal.iirnotch`. The rows are retained as an SOS cascade with the
format:

```text
[b0, b1, b2, a0, a1, a2]
```

The program never combines these rows into one high-order `b/a` polynomial.
This avoids the coefficient sensitivity and numerical instability associated
with evaluating a 20th-order transfer function as one polynomial.

For ten harmonics, the cascade has order 20. A conventional normalized SOS
implementation stores five independent coefficients and two state values per
section, and performs five multiplications per input sample per section. The
notch coefficients also satisfy `b0 = b2` and, to floating-point precision,
`b1 = a1`. A carefully derived implementation can exploit those identities,
but this reference model deliberately uses SciPy's standard SOS operations.

## Constant bandwidth and constant Q

`constant_bandwidth` is the default. Each section has an absolute 2 Hz
bandwidth, so its Q increases with harmonic number:

```text
Q_k = f_k / BW
```

The 60 Hz section therefore has Q=30 and the 600 Hz section has Q=300.

In `constant_q` mode every section uses the fundamental's Q:

```text
Q = mains_frequency / bandwidth_hz
```

Consequently, its absolute bandwidth increases with frequency. With the
defaults, all sections use Q=30 and the 600 Hz section has a 20 Hz bandwidth.

Harmonics at or above the actual Nyquist frequency are excluded with a clear
runtime warning. At least one valid harmonic is required.

## Impulse response and settling time

A narrow notch has a long, decaying sinusoidal ring-down even though it is only
second order. For an absolute notch bandwidth `BW`, the useful approximation is:

```text
tau ~= 1 / (pi * BW)
```

For 2 Hz, `tau` is about 0.159 s and the approximately 1% settling time is
`4.6*tau`, about 0.732 s. The number of samples in that interval is ten times
larger at 100 kSPS than at 10 kSPS, while the physical duration in seconds is
almost unchanged. The impulse figures use a real time axis and include at
least two seconds so that this ring-down is visible.

The synthetic test initializes the filter once with zero state. Its startup
subplot compares this output against `sosfilt_zi` initialization to make the
state-reset transient explicit.

## Digital Nyquist plot

The Nyquist figures in this tool are not pole-zero plots. They draw the complex
frequency response parametrically:

```text
x = Re{H(exp(j*omega))}
y = Im{H(exp(j*omega))}
```

The positive-frequency branch is colored by frequency and the
negative-frequency branch is drawn separately. Because all coefficients are
real, the two branches must satisfy conjugate symmetry. The program computes
and validates the maximum numerical symmetry error. The origin, DC response,
Nyquist response, and responses at all notch centers are marked.

Pole-zero data are saved in a separate figure. Pole stability is checked per
SOS without constructing a high-order polynomial.

## Group delay at a notch zero

Group delay is the negative frequency derivative of phase. At an exact notch
center, `H(exp(j*omega))` is zero, so its phase is undefined. The corresponding
group delay is therefore mathematically undefined and numerically unstable.
This program reports `NaN` at those exact frequencies instead of presenting a
large floating-point artifact as a physical delay. Group delay away from the
zeros is calculated by summing the group delay of the individual SOS rows.

## Outputs

Each sampling-rate directory contains:

- `coefficients.csv`: all SOS coefficients, poles, zeros, Q, and pole radii
- `validation.txt`: human-readable numerical results and PASS/WARNING checks
- `metrics.json`: machine-readable metrics
- full-band and low-frequency response figures
- a dense response figure around every harmonic
- phase and group-delay figures
- impulse response, digital Nyquist, pole-zero, and synthetic-test figures

`results/comparison_10k_100k.png` compares the impulse responses on a common
time axis. `results/comparison_validation.txt` compares time constants across
the two sampling rates.

All calculations use NumPy/SciPy `float64`. Passing these tests does not imply
that a later FPGA fixed-point realization will have the same notch depth,
stability margin, state growth, or settling behavior. Those properties require
a separate quantized model and HDL verification.
