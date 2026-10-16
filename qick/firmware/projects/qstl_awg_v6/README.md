# qstl_awg_v6

V6 aligns SET and RAMP at the hardware command interface, then aligns the common AWG sample path with DDS at the output combiner. It also uses the version 2 timed dispatcher for consecutive prequeued commands on one fabric-clock grid. Firmware artifacts are not valid until the new RTL regression and routed timing gates pass.

- AWG: `axis_awg_tuning_v4`, seven-clock common SET/RAMP pipeline at EXTRA=3; DC/RC control commands follow that epoch.
- Sum: `axis_output_sum_v3`, AWG delay six clocks plus two sum stages. Target native command-to-sum latency: SET/RAMP/DDS 31 clocks (excluding common external route/slice latency).
- tProcessor: `QICK:QICK:axis_tproc64x32_x8:2.0`; prequeued consecutive timestamps supported. A single port still cannot transmit two payloads in one cycle.
- Seven AWGs, three DDS pairs, unchanged 48-bit DC accumulator and unchanged XDC from v5.
- Functional gate includes actual PMEM-executing tProcessor/TMUX tests of rise/HOLD/fall lengths 1/1/1, 1/2/1, and 2/1/2 clocks. At 300 MHz each clock is exactly 10/3 ns; every 16-sample output word is checked, not only direct-command injection.
- Existing v5 firmware and previous IP revisions remain separate. Build work directories and private verification evidence stay outside Git. The released BIT/HWH/XSA package is stored in this project.

Set `QICK_V6_EVIDENCE_ROOT` to the private evidence folder containing a successful fresh `functional_gate.json`, then run Vivado 2023.1 with `build_vivado_2023_1.tcl` and a new empty external output directory. The gate checks source/evidence hashes before synthesis and after the build. The builder stops on routed setup/hold/pulse-width/bus-skew failures before bitstream generation.

Software timing integration and copying the matching BIT/HWH into this project follow successful routed signoff. Do not use the current v5 compiler timing profile as proof of v6 GUI compatibility. No board deployment is performed by the builder.

## Current integration status

The included firmware passed routed setup and hold timing (WNS +0.017997 ns, WHS +0.009598 ns). Python/GUI support is implemented, but integration is not fully validated: a grouped sweep with fixed-voltage DC compensation and RC compensation issued one SET-zero command five fabric clocks late. Do not treat this package as passing that case. The preceding falling RAMP was on time; the late command alone does not establish a delayed analog falling edge. No board deployment has been performed.
