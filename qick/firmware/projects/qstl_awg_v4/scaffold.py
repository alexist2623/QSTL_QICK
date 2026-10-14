"""Create v4 build scripts from immutable v3; never copy BIT/XSA/build folders."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
V3=HERE.parent/'qstl_awg_v3'
OUT=ROOT/'analysis_results/awg_tuning_v4'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((ROOT/'analysis_results/awg_tuning_v3/scope_correction/legacy_logic_baseline.json').read_text())['sources']
    for p in (ROOT/'qick/firmware/ip/axis_awg_tuning_v3/src').glob('*.sv'):
        frozen[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ('bd_2023-1.tcl','timing.xdc','ios.xdc','build_vivado_2023_1.tcl'):
        p=V3/name
        frozen[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=OUT/'protected_v3_sources.json'
    if manifest.exists():
        assert json.loads(manifest.read_text())==frozen,'v3 baseline changed'
    else: manifest.write_text(json.dumps(frozen,indent=2))
    for name in ('bd_2023-1.tcl','timing.xdc','ios.xdc'):
        dest=HERE/name
        if dest.exists(): assert dest.read_bytes()==(V3/name).read_bytes()
        else:dest.write_bytes((V3/name).read_bytes())
    script=(V3/'build_vivado_2023_1.tcl').read_text()
    script=script.replace('qstl_awg_v3','qstl_awg_v4').replace('Vivado_Output awg3','Vivado_Output awg4')
    script=script.replace('create_project $project_name $output_dir',
        'source [file join $script_dir package_sum.tcl]\n\ncreate_project $project_name $output_dir',1)
    script=script.replace('set_property ip_repo_paths [file join $repo_dir qick firmware ip] $sources_obj',
        'set_property ip_repo_paths [list [file join $repo_dir qick firmware ip] [file join $output_dir ip_repo]] $sources_obj')
    script=script.replace('source [file join $script_dir bd_2023-1.tcl]',
        'source [file join $script_dir bd_2023-1.tcl]\nsource [file join $script_dir connect_output_sum.tcl]')
    guard='''
if {$argc > 1 && [lindex $argv 1] eq "prepare"} {
    generate_target all $bd_file
    puts "V4_PREPARE_COMPLETE=$output_dir"
    close_project
    exit 0
}
set gate [file join $repo_dir analysis_results awg_tuning_v4 prebuild_gate.json]
if {![file exists $gate]} {error "v4 functional prebuild gate is not ready"}
exec C:/Users/Measurement2/.conda/envs/qcodes2/python.exe -X utf8 [file join $script_dir validate_scope.py] --require-functional
'''
    script=script.replace('launch_runs synth_1 -jobs $jobs',guard+'\nlaunch_runs synth_1 -jobs $jobs',1)
    # Refuse replacement if a running build could be depending on this script.
    target=HERE/'build_vivado_2023_1.tcl'
    if target.exists(): assert target.read_text()==script
    else:target.write_bytes(script.replace('\n','\r\n').encode())
    print('Created v4 source project; preserved',len(frozen),'v3 source hashes')

if __name__=='__main__':main()
