# v6 CPU to output integration validation

This fixture runs the production `tproc64x32_x8` CPU from the v2 IP package,
including instruction fetch/decode, register files, ALU, DMEM reads/writes,
per-port timed FIFOs, and the new timed dispatcher. Behavioral synchronous
PMEM and DMEM model host-loaded memories. The AXI host wrapper is excluded.
No timed FIFO contents or generator commands are injected around the CPU.

Three CPU ports each drive the production `axis_tmux_v1` (RF output 0, AWG
output 1), AWG v4, the production namespaced signal-generator v6/vendor DDS,
and output-sum v3. Each pair has a combined path, an AWG-only BYPASS path,
and an RF-only observation path. ADC/FIR/DDR and analog hardware are excluded.

The fixture uses integer 300 MHz clock counts and 16 samples per word.
Rise/fall durations `{1,2,3,4,7,8,10}` cross HOLD durations of the same set:
49 cases on three pairs. The required `1/1/1`, `1/2/1`, and `2/1/2` cases
also have separate completion markers and representative scalar-sample CSV.
All ordinary DDS tests use frequency/phase zero, widths 8/16/31 words,
and an explicit one-clock same-port AWG/RF issue offset. Fine RF memory
endpoints are not covered by this fixture.

The reference integer ramp model is independent of DUT internals. The fixed
contracts are AWG native 23, DDS native 29, and final native 31 clocks;
the sum adds six AWG clocks plus two pipeline clocks. CPU downstream sampling
must occur at programmed timestamp + 1 and TMUX transport adds two clocks.
These are independently asserted, not fitted to measured edges. The common
seven-clock AWG core latency is also covered by the separate AWG v4 unit TB.
There are no Python timing compensations in these emitted command words.

Preparation and simulation require fresh private directories:

```powershell
python prepare_cpu_fixture.py --out F:/QICK_Private_Analysis/awg_tuning_v6/cpu_tmux_fixture_01
powershell -File run_cpu_tmux.ps1 -Build F:/Vivado_Output/a6cpu_tmux01 -Fixture F:/QICK_Private_Analysis/awg_tuning_v6/cpu_tmux_fixture_01
python plot_required_waveforms.py --build F:/Vivado_Output/a6cpu_tmux01
```

The runner preserves source/input SHA256 before and after simulation and
requires all three case flags before reporting success. Existing evidence is
never overwritten. Do not treat this assembler-driven digital fixture as a
GUI/worker regression or physical measurement.
