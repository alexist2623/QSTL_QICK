"""Finish the report after the preserved postprocessing-only auditor failure."""
from pathlib import Path
import datetime
import hashlib
import json
import shlex
import subprocess
import sys

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
    completion_path = HERE / "postprocessing_completion.json"
    assert not completion_path.exists()
    integrity = read(HERE / "rtl_integrity_after.json")
    assert integrity["passed"] and integrity["case_count"] == 9
    assert integrity["file_count"] == 327 and integrity["snapshot_file_count"] == 18
    assert integrity["prepared_expected_hash_checks"] == 295
    assert all(sha(p) == h for p, h in integrity["files"].items())
    assert all(sha(p) == h for p, h in integrity["final_evidence_hashes"].items())

    # Exact files only. Existing input files must remain unchanged above.
    metadata = []
    wrapper_checks = []
    for prep_name in ("prepared.json", "prepared_cpmg.json"):
        prep = read(HERE / prep_name)
        case = prep["cases"][-1]
        folder = Path(case["folder"])
        snapshot = Path(prep["build"]) / "sim/xsim.dir/compiler17"
        options = shlex.split((folder / "options.txt").read_text())
        case_path = folder.as_posix()
        for value in ("compiler17", "-runall", "CASE=" + case_path,
                      "OUT=" + case_path, "CYCLES=" + str(case["cycles"])):
            assert value in options, (value, options)
        expected_script = ("xsim {compiler17} -testplusarg CASE=" + case_path
            + " -testplusarg OUT=" + case_path + " -testplusarg CYCLES=" + str(case["cycles"])
            + " -autoloadwcfg -runall")
        assert (snapshot / "xsim_script.tcl").read_text().strip() == expected_script
        wrapper_checks.append(dict(case=case["name"], options_path=str(folder / "options.txt"),
            options_sha256=sha(folder / "options.txt"), expected_wrapper=expected_script,
            exact_match=True, generation="Vivado xsim generated runtime wrapper from supplied options.txt"))
        for name in ("xsimSettings.ini", "xsim_script.tcl", "xsimcrash.log", "xsimkernel.log"):
            path = snapshot / name
            assert str(path) in integrity["separately_recorded_new_runtime_outputs"]
            stat = path.stat()
            metadata.append(dict(path=str(path), sha256=sha(path), size_bytes=stat.st_size,
                creation_time=datetime.datetime.fromtimestamp(stat.st_ctime).astimezone().isoformat(),
                last_write_time=datetime.datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
                content=path.read_text(), original_baseline_file=False))
    assert len(metadata) == 8
    assert {row["path"] for row in metadata} == set(integrity["separately_recorded_new_runtime_outputs"])
    runtime_path = HERE / "runtime_output_metadata.json"
    assert not runtime_path.exists()
    runtime_path.write_text(json.dumps(dict(passed=True, files=metadata,
        wrapper_checks=wrapper_checks, wildcard_exception=False), indent=2), encoding="utf-8")

    process_command = "$found = @(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -eq 104060 -or ($_.ExecutablePath -match 'a5compiler[12]' -and $_.Name -match 'xsim') -or ($_.Name -match 'xsim' -and $_.CommandLine -match 'a5compiler[12]')} | Select-Object ProcessId,Name,CreationDate,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $found -Depth 4"
    process = subprocess.run(["powershell.exe", "-NoProfile", "-Command", process_command],
        capture_output=True, text=True, check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    active_processes = json.loads(process.stdout)
    assert active_processes == [], active_processes
    report_log = HERE / "postprocessing_report.log"
    assert not report_log.exists()
    with report_log.open("w", encoding="utf-8") as log:
        report_process = subprocess.run([sys.executable, "-X", "utf8", str(HERE / "report.py")],
            stdout=log, stderr=subprocess.STDOUT)
    assert report_process.returncode == 0, report_log.read_text()
    results = read(HERE / "results.json")
    assert results["verification_complete"] and not results["all_original_requests_rtl_passed"]
    assert results["original_accepted_rtl_pass"] == 1
    assert results["separately_labelled_rf100ns_variant_passes"] == 8
    evidence = {str(p): sha(p) for p in HERE.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != completion_path}
    complete = dict(complete=True, stage="completed_with_documented_limitations",
        checked=datetime.datetime.now().astimezone().isoformat(),
        original_controller_exit_code=1, original_controller_status_preserved=True,
        postprocessing_audit_v2_exit_code=0, postprocessing_report_exit_code=report_process.returncode,
        actual_rtl_case_count=9, actual_xsim_exit_codes=[c["exit_code"] for c in integrity["xsim_exit_codes"]],
        active_controller_or_compiler_xsim_processes=active_processes, evidence_hashes=evidence,
        runtime_metadata_path=str(runtime_path), runtime_metadata_sha256=sha(runtime_path),
        existing_file_hash_differences=[], production_edits=False, rtl_rerun=False, board_access=False)
    completion_path.write_text(json.dumps(complete, indent=2), encoding="utf-8")
    print(json.dumps({k: complete[k] for k in ("complete", "stage", "original_controller_exit_code",
        "postprocessing_audit_v2_exit_code", "postprocessing_report_exit_code", "actual_rtl_case_count")}))


if __name__ == "__main__":
    main()
