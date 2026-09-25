# Residual DAC offset audit

The original 100-point, two-repeat GUI program was replayed in actual tProcessor,
TMUX and production AWG RTL. Only diagnostic monitors were added; production
RTL, firmware and the GUI were not changed. The exported assembly is identical.
Every scalar sample entering each AWG RC compensator was summed, including DC
compensation pulses. The existing independent analog RC checks still pass.

| Quantity after 200 shots | AWG 1 | AWG 2 |
|---|---:|---:|
| Sum of precompensator input codes | -2261440 | 2039840 |
| Input area, mV us | -11.502278646 | 10.375162760 |
| Internal RC correction, mV | -1.150227864 | 1.037516276 |
| Quantized DAC output, mV | -1.171875 | 1.07421875 |

The 72-bit integral is **exactly** `2 * 2932031007 * sum(input_codes)` in
its internal fractional units at the final zero-input plateau. Thus the
integrator is retaining a real uncompensated input area, rather than suffering
arithmetic accumulation error. Scaling is 4.8 GSPS and 800/32768 mV/code.

The DC algorithm models ramps as ideal trapezoids, rounds fixed-time
compensation voltages to a legal DAC code, and approximates their hardware
sweep with a constant code increment. It does not close the exact actual
sample area or carry the remaining area into the next compensation pulse.

Equivalent final-offset contributions, before final DAC quantization:

| Contribution, mV | AWG 1 | AWG 2 |
|---|---:|---:|
| Per-point compensation voltage rounding | -0.097656250 | -0.097656250 |
| Constant-increment compensation sweep approximation | 0.390625000 | 1.562500000 |
| Actual RTL input sample area minus ideal trapezoid/flat model | -1.443196615 | -0.427327474 |
| Sum (using ideal tau = 10 us) | -1.150227865 | 1.037516276 |

The last contribution includes the actual AWG ramp quantization and sample
timing, rather than assuming an ideal continuous ramp. The reciprocal
coefficient rounding accounts for the sub-nanovolt difference from the
measured internal correction. This decomposition uses the actual command
target codes; waveform sweep target differences are not silently substituted.

For target `x`, correction state `q`, and DAC output `u`, the ideal equations
are `q' = x/tau` and `u = x + q`. Closing the input area returns `q` to its
initial value. It does not generally make the DAC area `integral(u)` zero.
If DC compensation requires zero **actual DAC** area, both the RC-induced
slopes and the held nonzero correction during nominal-zero intervals must
be included. A corrected design must distinguish input-area/state closure
from actual DAC-area closure and validate both requested conditions.

Evidence: [numeric results](result.json), [XSim log](xsim.log).
Diagnostic runner: `tmp/audit_rc_residual.py` in the QSTL_QICK checkout.
Detailed traces: `C:/JeonghyunPark/Workspace/Vivado_Output/gui_rtl6/rc_residual_audit`.
