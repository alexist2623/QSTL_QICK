# Physical two-axis voltage sweep — 2026-10-15

User requested a simple real oscilloscope test, with 400 mV voltage axes. After distinguishing generator numbers from panel connectors, the user clarified panel outputs **4 and 5**. The connection order is interpreted from the user's earlier statement as DAC4 → scope CH1, DAC5 → scope CH2.

- Live board: 192.168.2.99, existing `myqick` Pyro service, ZCU216, firmware timestamp Wed Oct 14 21:39:55 2026.
- Live routing: DAC4 = AWG generator 1 + RF generator 0; DAC5 = AWG generator 3 + RF generator 2. Both report output_sum_version=2 and native output latency 31 clocks.
- DAC current readback: 20,037 µA, GUI reference full scale 801.48 mV. Current will not be changed.
- Scope: AGILENT TECHNOLOGIES DSO-X 6004A, MY60101437, firmware 07.31.2020012834. Initial inputs CH1/CH2: DC coupling, 1 MΩ, probe factor 1. Inputs will retain these settings.
- Two independent voltage axes: 0, 200, 400 mV each, identity matrix, nine Cartesian points, one repetition. Axis 2 varies fastest.
- Waveform: zero wait → positive-duration ramp → 1 ms plateau → ramp to zero → zero wait. The finite hardware loop ends at zero.
- Use actual GUI input extraction and the production compiler, followed by the no-readout hardware execution path. This is **not** a full GUI Run-worker / ADC / FIR-DDR / QCoDeS acquisition test.
- Store both oscilloscope channels from one completed acquisition, raw words, preamble, voltage/time arrays, scope setup, GUI settings, assembly, PMEM/DMEM, expected coordinates, and measured plateau levels.
- Explicitly prepare AWG-specific zero-output cleanup. Any paired-RF zero program addresses only the two RF paths summed into these tested outputs. Do not reset unrelated generators.
- Preserve source, user JSON, existing firmware, existing success/failure evidence, and running unrelated processes. No firmware upload, server restart, or production edits.

## Acquisition preparation findings

`:RSTate?`, `:OPERation:CONDition?`, and `:ADER?` are unsupported on the actual scope firmware; their query failures are preserved. The supported state query is `:OPERegister:CONDition?`, with bit 3 indicating running. Initial value 4144 indicates stopped. `:AER?` and `:TER?` are supported.

The first setup query was truncated by newline termination at 75 bytes; it is preserved as failed evidence and must not be used for restore. A subsequent binary-safe read retrieved the complete 167,580-byte setup payload; SHA256 is recorded separately. No analog output or scope acquisition-setting changes occurred during these queries.

This simple check measures output levels and two-axis ordering. It does not certify calibrated amplitude accuracy, fine RF sample timing, nonidentity virtual matrix behavior, or ADC/FIR arithmetic.
