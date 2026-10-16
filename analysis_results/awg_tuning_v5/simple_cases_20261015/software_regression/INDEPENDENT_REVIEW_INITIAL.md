# Independent source review — initial pass

This review was read-only. The 110-test software regression remains unchanged.

## Fresh execution path

The coarse and fine RTL adapters reuse proven simulation infrastructure, but regenerate GUI input, compile the current production Python, and load fresh PMEM/DMEM/envelopes. The coarse path additionally compares actual GUI and export compiler bytes and checks the prepared input/source fingerprint. This is not a replay of previous inputs or PASS results.

Matrix arithmetic and fine active-sample counts have independent analytic checks. End-to-end absolute timing still has compiler/model-derived references, so the final report must retain that boundary. The offscreen GUI normal argument/compile path is not a live Run-worker/board/scope test.

## Findings sent to the GUI runner owner

1. Assert independently requested SET/RAMP structure before using production `sequence.segments` to interpret emitted commands; otherwise a missing RAMP could skip a ramp assertion.
2. Construct expected GUI timeline directly from case duration/ramp/hold constants; `pulse.t` is committed GUI state, not an independently calculated requested timing reference.
3. Validate known startup zero-SET commands explicitly rather than slicing the final expected number of AWG commands, which can hide extra commands.

These findings concern the new validation harness, not demonstrated production defects. Owner/root were notified before final suite interpretation. A later addendum will record resolution against the final helper hash.

See `independent_review_initial.json` for exact reviewed hashes, positive findings, and limitations.
