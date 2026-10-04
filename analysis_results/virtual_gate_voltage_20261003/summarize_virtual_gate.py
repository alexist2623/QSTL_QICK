"""Collect completed RTL evidence and plot verified nominal SET targets."""
import json
import shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('C:/JeonghyunPark/Workspace/QSTL_QICK')
BUILD=ROOT.parent/'Vivado_Output/gui_rtl6'
OUT=ROOT/'analysis_results/virtual_gate_voltage_20261003'
PREFIX='rc_precomp_repeat_reset_no_aux_grid_20x20_virtual_gate_20261003_awg_v2'
results={}
for kind,suffix in [('awg',''),('stability','_stability')]:
    folder=BUILD/(PREFIX+suffix)
    result=json.loads((folder/'result.json').read_text())
    assert result['validation_status']=='passed'
    assert (result['points'],result['repetitions'])==(400,2)
    assert result['command_value_mismatches']==result['command_timing_mismatches']==0
    results[kind]=result
    for name in ('result.json','grid_axes.json','gui_export.py','program.asm','prepared.json'):
        shutil.copy2(folder/name,OUT/f'{kind}_{name}')
for name in ('check_virtual_gate_sweeps.py','test_virtual_gate_gui.py','summarize_virtual_gate.py'):
    shutil.copy2(ROOT/'tmp'/name,OUT/name)
report=dict(branch='awg_tuning_v2',qick_commit='587f46d7',gui_commit='3e78e0c',
    existing_regression_tests_passed=91,gui_virtual_gate_tests_passed=2,
    software=json.loads((OUT/'software_results.json').read_text()),rtl=results,
    limitations=['Digital RTL and instruction model; no physical board measurement.',
                 'Full-grid analog RC response is not simulated in these runs.',
                 'Coupled 200x200 hardware grids exceed 4096-word DMEM in both tested builders.'])
(OUT/'summary.json').write_text(json.dumps(report,indent=2))
axes=json.loads((OUT/'awg_grid_axes.json').read_text())
fig,axs=plt.subplots(2,2,figsize=(10.5,8),layout='constrained')
for ch,row in enumerate(axes):
    actual=np.array(row['executed_target_mv'])
    requested=np.array(row['requested_physical_mv'])
    half_lsb=(800,400)[ch]/16384
    for col,data in enumerate((actual,actual-requested)):
        ax=axs[ch,col]
        opts=dict(cmap='viridis') if col==0 else dict(cmap='RdBu_r',vmin=-half_lsb,vmax=half_lsb)
        im=ax.imshow(data.T,origin='lower',extent=(5,15,5,15),aspect='auto',**opts)
        fig.colorbar(im,ax=ax,label='mV')
        ax.set_xlabel('Virtual gate X (mV)');ax.set_ylabel('Virtual gate Y (mV)')
        ax.set_title(f'DAC {ch+1}: '+('RTL-verified SET target (before RC)' if col==0 else
                     f'Target rounding error (max {abs(data).max():.5f} mV)'))
fig.suptitle('Virtual gates + 20 x 20 hardware voltage sweep, 2 repeats\n'
             'V1 = X + 0.23 Y; V2 = -0.17 X + Y; full scales = +/-800, +/-400 mV')
fig.savefig(OUT/'virtual_gate_rtl.png',dpi=170)
print(json.dumps({k:{key:value for key,value in v.items() if key in
    ('points','repetitions','commands','dmem_words','grid_target_error_mv','reset_results','raw_awg_results')}
    for k,v in results.items()},indent=2))
