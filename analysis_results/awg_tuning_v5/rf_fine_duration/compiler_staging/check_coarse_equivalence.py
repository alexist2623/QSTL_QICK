"""Compare staged opt-in compiler's disabled path to unchanged production."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import qick.sim
import qick_fine_tune_sweep as staged
from test_qick_fine_tune_sweep import _shared_tmux_soccfg

HERE=Path(__file__).resolve().parent
BASE=Path('C:/GIT_Workspace/PulseGenerator/DCWaveformGeneratorGUI/qick_fine_tune_sweep.py')
spec=importlib.util.spec_from_file_location('coarse_production_reference',BASE)
original=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=original
spec.loader.exec_module(original)


def compile_case(module,length,start,stop,count,outer):
    cfg=_shared_tmux_soccfg()
    sequence=module.FineTuneSequence(('awg_0',)).add_set('hold',.01,400000)
    if outer>1:
        sequence.add_amplitude_sweep('hold','awg_0',.01,.03,outer)
    if start is not None:
        sequence.add_rf_duration_sweep('hold',0,start/300.,stop/300.,count,
                                       sequence_fabric_mhz=300.)
    rf=module.RfPulseConfig(0,'hold',length,2000,freq_mhz=190.,phase_degrees=45.,delay_tproc_cycles=30)
    program=sequence.make_program(cfg,awg_channels=(1,),rf_pulse=rf,
                                  repetitions_per_sweep=2,compile_validation_mode='boundary')
    program.compile()
    return program


results=[]
for args in ((3,None,None,1,1),(35,None,None,1,1),(65535,None,None,1,1),
             (65536,None,None,1,1),(30,30,125,20,20),(125,125,30,20,20),
             (35,35,65536,2,2)):
    before=compile_case(original,*args)
    after=compile_case(staged,*args)
    assert before.asm()==after.asm(),args
    assert np.array_equal(before.binprog,after.binprog),args
    assert before._runtime_dmem_words==after._runtime_dmem_words,args
    assert before.aux_timing==after.aux_timing,args
    results.append(dict(arguments=args,passed=True,
        pmem_sha256=hashlib.sha256(np.array(after.binprog,dtype=np.uint64).tobytes()).hexdigest(),
        asm_sha256=hashlib.sha256(after.asm().encode()).hexdigest(),
        dmem_sha256=hashlib.sha256(json.dumps(after._runtime_dmem_words).encode()).hexdigest()))
result=dict(passed=True,cases=results,source_hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (BASE,Path(staged.__file__),Path(staged.__file__).with_name('qick_rf_fine_duration.py'))})
(HERE/'coarse_equivalence.json').write_text(json.dumps(result,indent=2))
print('PASS 7 disabled-feature programs: PMEM/ASM/DMEM/timing byte-identical to unchanged production')
