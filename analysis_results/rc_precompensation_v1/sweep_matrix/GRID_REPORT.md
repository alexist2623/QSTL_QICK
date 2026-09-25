# Completed two-DAC 20 x 20 RTL run

Points: 400; repetitions per point: 2.
All 14,402 command words and timestamps matched the instruction model.
Cycles: 384,793; PMEM: 206 words; DMEM table: 0 words.

EXACT_AWG_RESULT ch=0 samples=6158800
EXACT_AWG_RESULT ch=1 samples=6158800
REPEAT_RESET_RESULT ch=0 resets=801 zero_checks=801
REPEAT_RESET_RESULT ch=1 resets=801 zero_checks=801

Maximum nominal target error: [0.7421875, 0.7421875] mV.
This is the existing rounded integer sweep-step error, not a mismatched RTL recurrence.
Neither repetition nor inner-axis reset mismatches occurred.
The analog RC model was not run over this full large grid; see the smaller mixed-sweep analog validations.

Only the first 12,000 clocks of the waveform were stored. All clocks were checked in the RTL testbench.
