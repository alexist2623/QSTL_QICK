"""Summarize completed fresh suites without conflating refusals with RTL passes."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def artifact(path):
    path = Path(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def update_completion_documents(result):
    backups = HERE / "documentation_before"
    backups.mkdir(exist_ok=True)
    notes = (
        "## 2026-10-15 현재 v5 추가 GUI → RTL 검증 완료\n\n"
        f"새 실제 RTL {result['fresh_real_rtl_runs']}회·{result['fresh_shots']} shots가 통과했습니다. "
        "원본 거부 조건을 통과로 바꾸지 않고 별도 RF +100ns 변형과 분리했습니다. "
        "Virtual matrix×sweep 21조건은 원본 "
        f"{result['matrix21']['original_accepted_count']}개와 명시적 변형 "
        f"{result['matrix21']['explicit_offset_variant_passed_count']}개이며, composite 7조건은 원본 그대로 PASS입니다. "
        "별도 compiler 17조합은 Calibration 정상 거부 6개, Quantum N=0 원본 RTL PASS 1개, "
        "CPMG/UDD 명시적 +100ns 변형 RTL PASS 8개, Quantum N=1/3 v5 latency 미지원 거부 2개입니다. "
        "원본 45조건 전체 RTL PASS로 표시하지 않습니다.\n\n"
        "실제 MainWindow/생산 compiler 입력과 새 PMEM/DMEM을 실제 tProcessor/TMUX/AWG/DDS/v5 합산 "
        "RTL로 실행했습니다. 정확한 AWG/RF 동시 시작은 사용자 지시에 따라 수정하지 않았습니다. "
        "생산 소스·RTL/XDC·사용자 설정 및 기존 펌웨어는 보존했고, 이후 요청받은 로컬 v5 "
        "BIT/HWH/XSA/manifest 네 신규 파일만 추가했습니다. 보드 업로드와 새 합성은 없으며 "
        "자동화는 PAUSED 상태입니다.\n\n"
    )
    targets = [
        (HERE.parent / "RUNNING.md", "v5_RUNNING.md", "expanded_gui_rtl_20261015/REPORT.md"),
        (HERE.parent / "PLAN.md", "v5_PLAN.md", "expanded_gui_rtl_20261015/REPORT.md"),
        (HERE.parent / "REPORT.md", "v5_REPORT.md", "expanded_gui_rtl_20261015/REPORT.md"),
        (HERE.parent.parent / "awg_tuning_v4/VALIDATION_CHECKLIST.md",
         "v4_VALIDATION_CHECKLIST.md", "../awg_tuning_v5/expanded_gui_rtl_20261015/REPORT.md"),
    ]
    updates = []
    for path, backup_name, link in targets:
        raw = path.read_bytes()
        backup = backups / backup_name
        assert not backup.exists(), "Preserve earlier documentation snapshot"
        backup.write_bytes(raw)
        content = raw.decode("utf-8-sig")
        heading, separator, body = content.partition("\n")
        assert separator and heading.startswith("# ")
        insert = notes + f"[이번 최종 보고서와 케이스별 증거]({link}). "
        insert += "Show/Run 경로 비교 및 미재현 정체 진단은 해당 보고서의 별도 링크를 따릅니다.\n\n"
        insert += "아래 기존 기록은 각 버전·빌드·조사 당시 상태를 보존한 것입니다.\n\n---\n"
        path.write_text(heading.rstrip() + "\n\n" + insert + body, encoding="utf-8")
        updates.append({"before": artifact(backup), "after": artifact(path)})
    return updates


def main():
    destination = HERE / "results.json"
    assert not destination.exists(), "Preserve prior final evidence"
    matrix = read(HERE / "matrix21/reporting/result.json")
    matrix_completion = read(HERE / "matrix21/reporting/completion.json")
    composite = read(HERE / "composite7/result.json")
    compiler = read(HERE / "compiler17/results.json")
    compiler_completion = read(HERE / "compiler17/postprocessing_completion.json")
    preservation = read(HERE / "after.json")
    processes = read(HERE / "controller_process_check.json")
    for profile in ("v4", "v5"):
        comparison = read(HERE.parent / "show_program_freeze_20261015" / f"show_run_equal_{profile}.json")
        assert comparison["passed"] and comparison["assembly_equal"] and comparison["pmem_equal"]
        assert comparison["proof"]["instructions"] == 118 and comparison["rf_host_sweep_axes"] == 0
        assert comparison["proof"]["dmem_words"] == [] and comparison["proof"]["envelopes"] == {}
        assert not comparison["board_connected"] and not comparison["hardware_run"]
    probe = read(HERE.parent / "show_program_freeze_20261015/worker_wait_probe/reviewed_result.json")
    assert probe["passed"] and not probe["production_changes"] and not probe["board_access"]
    assert matrix["execution_complete"] and compiler["verification_complete"]
    assert matrix["all_selected_cases_passed"] and matrix["passed_case_count"] == 21
    assert matrix_completion["controller_exit_code"] == matrix_completion["aggregate_exit_code"] == 0
    assert matrix_completion["matching_matrix_processes"] == []
    assert all(artifact(item["path"])["sha256"] == item["sha256"] for item in matrix_completion["artifacts"])
    assert matrix["original_prepare_error_count"] == 0
    assert matrix["original_accepted_count"] + matrix["original_rejected_count"] == 21
    assert matrix["original_rejected_count"] == matrix["explicit_offset_variant_passed_count"]
    assert composite["passed"] and composite["fresh_real_rtl_runs"] == 7
    assert composite["source_and_input_match"] and composite["failures"] == 0
    assert len(compiler["rtl_results"]) == 9 and not compiler["pending_rtl"]
    assert all(r["passed"] and r["xsim_exit_code"] == 0 for r in compiler["rtl_results"])
    assert compiler["final_integrity"]["passed"] and not compiler["source_hash_differences"]
    assert compiler_completion["complete"] and compiler_completion["original_controller_exit_code"] == 1
    assert compiler_completion["postprocessing_audit_v2_exit_code"] == compiler_completion["postprocessing_report_exit_code"] == 0
    assert compiler_completion["actual_rtl_case_count"] == 9
    assert compiler_completion["actual_xsim_exit_codes"] == [0] * 9
    assert not compiler_completion["active_controller_or_compiler_xsim_processes"]
    assert not compiler_completion["existing_file_hash_differences"]
    assert all(artifact(path)["sha256"] == digest
               for path, digest in compiler_completion["evidence_hashes"].items())
    assert preservation["passed"] and not preservation["differences"]
    assert processes["all_relevant_controllers_and_xsim_ended"]
    assert len(matrix["originals"]) == 21 and compiler["original_case_count"] == 17
    assert compiler["expected_negative_guard_cases"] == 6
    assert compiler["shared_port_original_rejections"] == 8
    assert compiler["quantum_unsupported_original_cases"] == 2
    assert compiler["original_accepted_rtl_pass"] == 1
    assert compiler["separately_labelled_rf100ns_variant_passes"] == 8
    prepared_compiler = [case for name in ("prepared.json", "prepared_cpmg.json")
                         for case in read(HERE / "compiler17" / name)["cases"]]
    prepared_names = [case["name"] for case in prepared_compiler]
    result_names = [case["name"] for case in compiler["rtl_results"]]
    assert len(prepared_names) == len(set(prepared_names)) == 9
    assert len(result_names) == len(set(result_names)) == 9
    assert set(prepared_names) == set(result_names)
    compiler_shots = sum(case["shots"] for case in prepared_compiler)
    composite_shots = composite["fresh_gui_programs"] * composite["repetitions"]
    paths = [
        "before.json", "after.json", "controller_process_check.json", "check_completion.ps1", "PLAN.md", "audit.py",
        "matrix21/reporting/result.json", "matrix21/reporting/REPORT.md",
        "matrix21/reporting/completion.json",
        "matrix21/reporting/matrix_v5_actual_trace_v2.png",
        "matrix21/reporting/matrix_v5_actual_dialog.png", "matrix21/reporting/plot_provenance_v2.json",
        "matrix21/status.json", "composite7/result.json", "composite7/REPORT.md",
        "composite7/proof_hashes.json", "composite7/status.json",
        "composite7/composite7_actual_v5_rtl.png", "compiler17/results.json",
        "compiler17/REPORT.md", "compiler17/inventory.json",
        "compiler17/controller_status.json", "compiler17/rtl_integrity_after.json",
        "compiler17/postprocessing_completion.json", "compiler17/runtime_output_metadata.json",
        "compiler17/semantic_audit/result.json", "final_report.py",
        "../show_program_freeze_20261015/SHOW_RUN_PATHS.md",
        "../show_program_freeze_20261015/show_run_equal_v4.json",
        "../show_program_freeze_20261015/show_run_equal_v5.json",
        "../show_program_freeze_20261015/worker_wait_probe/reviewed_result.json",
    ]
    result = {
        "execution_complete": True,
        "status": "completed_with_documented_limitations",
        "checked_at": datetime.now().astimezone().isoformat(),
        "all_selected_real_rtl_executions_passed": True,
        "all_original_requests_rtl_passed": False,
        "fresh_real_rtl_runs": matrix["passed_case_count"] + composite["fresh_real_rtl_runs"] + len(compiler["rtl_results"]),
        "fresh_shots": matrix["shots"] + composite_shots + compiler_shots,
        "final_digital_sample_checks": matrix["physical_lane_checks"] + composite["final_physical_sample_checks"] + compiler["physical_sample_checks"],
        "matrix21": {key: matrix[key] for key in (
            "passed_case_count", "original_accepted_count", "original_rejected_count",
            "explicit_offset_variant_passed_count", "points", "shots", "commands",
            "physical_lane_checks", "sum_lane_checks", "executed_matrix_target_checks",
            "compiler_model_matrix_target_checks", "saved_gui_grid_coordinates_checked")},
        "composite7": composite,
        "compiler17": {key: compiler[key] for key in (
            "original_case_count", "expected_negative_guard_cases", "shared_port_original_rejections",
            "quantum_unsupported_original_cases", "original_accepted_rtl_pass",
            "separately_labelled_rf100ns_variant_passes", "physical_sample_checks", "sum_lane_samples")},
        "compiler_rtl_shots": compiler_shots,
        "compiler_final_audit_review": {
            "initial_controller_exit": 1,
            "rtl_runs_all_exit_zero": True,
            "cause": "Eight newly generated Vivado runtime outputs were initially counted as input changes.",
            "original_failure_preserved": True,
            "postprocessing_audit_passed": compiler["final_integrity"]["passed"],
            "rtl_rerun_for_audit": False,
        },
        "protected_file_count_before": read(HERE / "before.json")["file_count"],
        "protected_file_count_after": preservation["file_count"],
        "production_python_count": preservation["prior_verified_production_python_count"],
        "python_hash_scope_includes_related_test_sources": True,
        "authorized_new_local_firmware_files": preservation["authorized_new_local_firmware_files"],
        "production_changes": [],
        "board_access": False,
        "board_firmware_upload": False,
        "new_synthesis": False,
        "exact_simultaneous_start_tested_or_fixed": False,
        "adc_fir_arithmetic_validated": False,
        "show_program_freeze": {
            "status": "live_symptom_not_reproduced_cause_unconfirmed",
            "fixed": False,
            "settings": "awg_rf_test.json",
            "offline_show_run_instructions_equal_v4_and_v5": 118,
            "runtime_dmem_and_envelopes_both_empty": True,
            "simulated_worker_wait_keeps_qt_event_loop_responsive": True,
            "production_change": False,
        },
        "evidence": [artifact(HERE / path) for path in paths],
    }
    lines = [
        "# 현재 v5 GUI → 실제 RTL 추가 검증 결과", "",
        f"검증 종료: {result['checked_at']}. 새 실제 RTL 실행 {result['fresh_real_rtl_runs']}개, "
        f"{result['fresh_shots']}회, 최종 디지털 출력 샘플 {result['final_digital_sample_checks']:,}개 검사 PASS입니다.", "",
        "원본 GUI가 거부한 조건과 명시적인 RF +100 ns 변형은 별도로 기록했습니다. "
        "따라서 원본 45조건이 모두 RTL을 통과했다는 의미는 아닙니다. "
        "사용자가 제외한 AWG/RF 정확한 동시 시작 문제는 수정하지 않았습니다.", "",
        "| 요청 묶음 | 이번 새 실행 결과 |", "|---|---|",
        f"| Virtual matrix × sweep 21조건 | 실제 RTL 21/21 PASS. 원본 {matrix['original_accepted_count']}조건, "
        f"원본 공유 포트 거부 후 별도 RF +100 ns 변형 {matrix['explicit_offset_variant_passed_count']}조건. "
        f"{matrix['points']}점 × 2회. |",
        "| 별도 compiler 17조합 | 원본 전체를 실제 GUI/compiler로 확인. Calibration 정상 거부 6개, "
        "Quantum N=0 원본 RTL PASS 1개, CPMG/UDD 공유 포트 거부 8개는 별도 +100 ns 변형 RTL 8/8 PASS. "
        "Quantum N=1/3 두 조건은 v5 RF latency profile 미지원으로 실행 전 거부. |",
        "| Composite 7조건 | 기존 원본 설정으로 실제 RTL 7/7 PASS. τ×π 6조건과 Hahn→Custom 1조건, "
        "세 RF/AWG 쌍·두 반복·126 RF burst. |", "",
        "## GUI 입력과 실제 RTL의 연결", "",
        "실제 MainWindow/설정창 → Run Experiment의 생산 컴파일 경로 → 새 PMEM/DMEM → "
        "실제 tProcessor/TMUX/AWG/DDS/IIR/axis_output_sum_v2/최종 출력 slice를 실행했습니다. "
        "보드 I/O 경계만 로컬 컴파일로 대체했습니다. N/τ 및 Custom host parameter는 정상 software-coordinate "
        "해석을 거치며, hardware sweep은 프로그램 안에서 실행됩니다.", "",
        "Matrix는 비대칭 완전결합 3×3, 물리 출력 scale 800/400/800 mV와 독립 C@V·정수 증가량 oracle을 "
        "사용했습니다. 기존 SET 양자화 정책을 검증한 것이며 이상적 연속 전압 오차가 0이라는 뜻은 아닙니다. "
        "compiler17의 CPMG는 9점 HOLD×전압 grid이고 matrix21의 해당 N/τ는 2점 진폭 grid라 별도 실행했습니다.", "",
        f"저장된 GUI grid {matrix['saved_gui_grid_coordinates_checked']}좌표, compiler 모델 목표값 "
        f"{matrix['compiler_model_matrix_target_checks']}개, 별도의 실제 RTL SET payload "
        f"{matrix['executed_matrix_target_checks']}개가 독립 기대값과 일치했습니다.", "",
        "Matrix의 inherited analog_results/GUI_RC_RESULT는 일부 경로의 가상 RC 진단값입니다. "
        "세 AWG의 아날로그 오차 통과 결과로 해석하지 않습니다. 이번 통과 기준은 세 AWG의 디지털 "
        "IIR 점화식·면적/reset 또는 bypass와 최종 DAC oracle이며, 기존 연속 RC 200회 검증은 별도 기록입니다.", "",
        "+100 ns 변형은 외부 RF 시작 offset만 바꿨습니다. 내부 τ/π/phase, 생산 spacing guard, "
        "원본 실패 기록은 유지했습니다. Quantum N=0은 RF가 없는 Quantum 경로이며 AWG Tuning virtual matrix를 "
        "상속하지 않습니다. Quantum N=1/3은 별도 Quantum RF latency 탐색이 v5를 인식하지 못하는 제한입니다.", "",
        "## 보존 및 범위", "",
        f"기준 Python 소스(관련 검증 코드 포함) {result['production_python_count']}개와 검증 전 보호 파일 "
        f"{result['protected_file_count_before']}개의 해시를 유지했습니다. 사용자가 이후 요청한 로컬 v5 "
        "BIT/HWH/XSA/manifest 네 신규 파일만 정확한 해시로 추가를 허용하여 최종 "
        f"{result['protected_file_count_after']}개를 대조했습니다. 각 묶음의 새 RTL/입력/로그 증거도 재검사했습니다.", "",
        "Compiler17의 RTL 실행은 모두 exit0이었지만 최초 controller는 최종 파일 감사에서 exit1로 "
        "종료했습니다. Vivado가 실행 후 생성한 런타임 파일 8개를 입력 변경으로 집계한 감사기 오류였습니다. "
        "원본 실패를 보존하고 정확한 신규 출력 경로·해시를 별도 기록한 후처리 감사가 통과했습니다. "
        "기존 입력과 compiled snapshot 해시는 동일하며 RTL을 다시 실행하거나 허용 오차를 바꾸지 않았습니다.", "",
        "이번 검증에서 새 합성, 보드 접속·업로드·서버 재시작, 사용자 설정 변경, 생산 코드 변경은 없습니다. "
        "기존 자동화는 PAUSED 상태입니다. 로컬 firmware package의 additional_validation=running은 "
        "복사 시점 기록이며, 이후 완료 증거는 이 보고서와 연결된 최종 결과입니다.", "",
        "실물 아날로그 측정과 ADC/FIR 산술은 미수행입니다. AWG IIR 뒤 DDS 면적 및 clipping은 "
        "기존 AWG DC 면적 보상 범위 밖입니다.", "",
        "## 결과 파일", "",
        "- [전체 결과와 증거 SHA256](results.json)",
        "- [Matrix 21 상세](matrix21/reporting/REPORT.md) · [실제 최종 출력 파형](matrix21/reporting/matrix_v5_actual_trace_v2.png)",
        "- [Compiler 17 상세 및 거부 원인](compiler17/REPORT.md)",
        "- [Composite 7 상세](composite7/REPORT.md) · [실제 RTL 파형](composite7/composite7_actual_v5_rtl.png)",
        "- [검증 전 보존 감사](before.json) · [검증 후 보존 감사](after.json)",
        "- [로컬 v5 패키지](../local_firmware_package_20261015/REPORT.md)",
        "- [Show QICK Program / Run Experiment 코드 경로와 비교](../show_program_freeze_20261015/SHOW_RUN_PATHS.md)", "",
        "Show 응답 없음은 현재 재현되지 않아 원인을 확정하거나 해결로 표시하지 않았습니다. "
        "awg_rf_test.json의 로컬 v4/v5 검증에서는 Show와 Run 직전 ASM/PMEM/DMEM/RF envelope가 일치했습니다.",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result["report"] = artifact(HERE / "REPORT.md")
    result["updated_documents"] = update_completion_documents(result)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "status", "fresh_real_rtl_runs", "fresh_shots", "final_digital_sample_checks")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
