"""Reject changes outside the user's pre-IIR DC-engine implementation scope."""
import hashlib
import json
from pathlib import Path


def validate(repo):
    manifest_path = repo/'analysis_results/awg_tuning_v3/scope_correction/legacy_logic_baseline.json'
    manifest = json.loads(manifest_path.read_text())
    required = {
        'qick/firmware/ip/axis_awg_tuning_v3/src/v3_awg_tuning_ctrl.sv',
        'qick/firmware/ip/axis_awg_tuning_v3/src/v3_awg_rc_precomp.sv',
        'qick/firmware/ip/axis_square_pulse_v1/src/square_rc_precomp.sv',
        'qick/firmware/ip/rc_precomp_validation/generate_rtl.py',
    }
    if not required.issubset(manifest['sources']):
        raise RuntimeError('Legacy scope baseline is incomplete')
    changed = [path for path, expected in manifest['sources'].items()
               if not (repo/path).is_file() or
               hashlib.sha256((repo/path).read_bytes()).hexdigest() != expected]
    if changed:
        raise RuntimeError('Protected existing logic was changed: '+', '.join(changed))
    return dict(passed=True, files=len(manifest['sources']),
                manifest=str(manifest_path),
                manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())


if __name__ == '__main__':
    print(json.dumps(validate(Path(__file__).resolve().parents[5]), indent=2))
