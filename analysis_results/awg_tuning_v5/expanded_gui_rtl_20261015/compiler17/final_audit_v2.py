"""Postprocess only: immutable compiled inputs plus exact new xsim runtime outputs.

The original final_audit.py and failed controller are retained unchanged.
No simulation, compilation, hardware access or production edits are performed.
"""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    destination = HERE / "rtl_integrity_after.json"
    assert not destination.exists(), "Preserve existing final evidence"
    before = read(HERE / "rtl_integrity_before.json")
    current = {p: sha(p) for p in before["files"]}
    differences = [p for p, h in before["files"].items() if current[p] != h]
    assert not differences, differences

    expected = {}
    cases = []
    snapshots = []
    additions = {}
    runtime_names = {"xsimSettings.ini", "xsim_script.tcl", "xsimcrash.log", "xsimkernel.log"}
    for prep_name in ("prepared.json", "prepared_cpmg.json"):
        prep = read(HERE / prep_name)
        build = Path(prep["build"])
        cases.extend(prep["cases"])
        for group in ("source_hashes", "helper_hashes", "template_sources"):
            for p, h in prep[group].items():
                if p in expected:
                    assert expected[p] == h, ("Conflicting expected source hashes", p)
                expected[p] = h
        for case in prep["cases"]:
            for name, h in case["inputs"].items():
                expected[str(Path(case["folder"]) / name)] = h

        snapshot = build / "sim/xsim.dir/compiler17"
        old = {p for p in before["snapshots"] if Path(p).parent == snapshot}
        now = {str(p) for p in snapshot.iterdir() if p.is_file()}
        assert old <= now, sorted(old - now)
        added = now - old
        assert {Path(p).name for p in added} == runtime_names, sorted(added)
        assert len(added) == 4
        assert (snapshot / "xsimcrash.log").stat().st_size == 0
        assert "Simulation completed" in (snapshot / "xsimkernel.log").read_text()
        script = (snapshot / "xsim_script.tcl").read_text()
        assert prep["cases"][-1]["name"] in script and "-runall" in script
        additions.update({p: sha(p) for p in sorted(added)})
        snapshots.extend(sorted(old))

    expected_differences = [p for p, h in expected.items() if sha(p) != h]
    assert not expected_differences, expected_differences
    exits = []
    evidence = {}
    results = []
    for status_name in ("rtl_status.json", "cpmg_rtl_status.json"):
        state = read(HERE / status_name)
        assert state["complete"] and state["stage"] == "passed"
        commands = state["command_exits"]
        assert len(commands) == len(state["cases"])
        assert all(c["tool"] == "xsim" and c["exit_code"] == 0 for c in commands)
        assert len({c["log"] for c in commands}) == len(commands)
        exits.extend(commands)
        evidence[str(HERE / status_name)] = sha(HERE / status_name)
    for case in cases:
        folder = Path(case["folder"])
        result = read(folder / "result.json")
        assert result["passed"] and result["xsim_exit_code"] == 0
        assert result["name"] == case["name"]
        assert len([c for c in exits if Path(c["log"]).parent == folder]) == 1
        results.append(result)
        for p in folder.iterdir():
            if p.is_file():
                evidence[str(p)] = sha(p)
    inventory = read(HERE / "inventory.json")
    assert inventory["complete"] and len(inventory["cases"]) == 17
    original_folders = [HERE / c["name"] for c in inventory["cases"]]
    for folder in [HERE / "semantic_audit", *original_folders]:
        for p in folder.rglob("*"):
            if p.is_file():
                evidence[str(p)] = sha(p)
    for name in ("inventory.json", "prepared.json", "prepared_cpmg.json",
                 "controller_status.json", "rtl_controller.log", "cpmg_controller.log",
                 "final_audit.py", "final_audit_v2.py", "final_audit_diagnostic.txt",
                 "rtl_integrity_before.json"):
        evidence[str(HERE / name)] = sha(HERE / name)
    evidence.update(additions)
    result = dict(
        passed=True, mode="after", checked=datetime.datetime.now().astimezone().isoformat(),
        files=current, file_count=len(current), snapshot_file_count=len(snapshots), snapshots=snapshots,
        prepared_expected_hash_checks=len(expected), differences=differences,
        expected_differences=expected_differences, case_count=len(cases), xsim_exit_codes=exits,
        final_evidence_hashes=evidence, original_case_evidence_count=len(original_folders),
        pmem_dmem_envelope_inputs_included=True, production_rtl_inputs_included=True,
        separately_recorded_new_runtime_outputs=additions, board_access=False,
        original_controller_exit_code=1, original_controller_failed_step="postprocessing final_audit.py",
        correction="Original immutable inputs are checked against the original baseline. Exactly four new Vivado runtime outputs per compiled snapshot are hashed separately; no old file changes, missing files or unrecognized additions are allowed.",
        original_auditor_preserved=True, simulation_rerun=False,
        physical_sample_checks=sum(r["physical_sample_checks"] for r in results),
        sum_lane_samples=sum(r["sum_lane_samples"] for r in results),
        rf_pulses=sum(c["pulses"] for r in results for c in r["rf_checks"]),
    )
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("passed", "file_count", "snapshot_file_count",
        "prepared_expected_hash_checks", "case_count", "original_case_evidence_count",
        "physical_sample_checks", "sum_lane_samples", "rf_pulses")}))


if __name__ == "__main__":
    main()
