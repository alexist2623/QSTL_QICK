"""Check the v4 output stage in the AWG-only Stability baseline fixture."""
import csv
import json
import re


def analyze(out, log, model, offset, shots, delay_us):
    checked = re.findall(r'OUTPUT_SUM_RESULT suffix=(\d+) samples=(\d+)', log)
    assert {int(s) for s,n in checked} == {4,5,6}
    assert all(int(n)>0 for s,n in checked)
    pairs = []
    for port,suffix in enumerate((4,5,6)):
        events = [e for e in model.output_events if e.tproc_ch==port]
        # Type-zero DDS words must never appear in the AWG-only fixture.
        assert not [e for e in events if (e.word>>152)&255 == 0]
        with (out/f'sum_edges_{suffix}.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        assert not [r for r in rows if r['stream']=='rf'], 'Unexpected RF output'
        with (out/f'sum_alignment_{suffix}.csv').open() as stream:
            trace = list(csv.DictReader(stream))
        assert all(int(r['rf'],16)==0 for r in trace)
        area_index = (0,1,3)[port]
        with (out/f'area_ch{area_index}.csv').open() as stream:
            area = list(csv.DictReader(stream))
        assert len(area)==shots
        assert all(int(r['residual_area'])==0 for r in area)
        assert all(int(r['first_area_cycle'])-int(r['command_cycle'])==17 for r in area)
        pairs.append(dict(suffix=suffix,shots=shots,rf_pulses=0,residual_area=0))
    result = dict(sample_oracles=checked,pairs=pairs,combiner_pipeline_cycles=2,
                  stability_public_builder=True,rf_enabled=False,ddr_enabled=False)
    (out/'output_sum_result.json').write_text(json.dumps(result,indent=2))
    return result
