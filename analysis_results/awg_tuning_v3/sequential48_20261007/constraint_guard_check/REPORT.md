# Synthetic offline constraint guard checks

**These checks do not run Vivado or xsim and do not establish FPGA timing closure.**

Passed: 32/32; complete: True.

The actual previous Vivado 2023.1 XPR was read only to verify XML attribute shape.
Acceptance/rejection fixtures and modified constraint copies exist only under `F:/Vivado_Output/a3_guard_check`.
No implementation source, original XDC, or real build evidence was edited.

| Check | Result |
|---|---|
| actual_Vivado_2023_1_XPR_attribute_shape | PASS |
| Tcl_reject_qick_root | PASS |
| Tcl_reject_qick_child | PASS |
| Tcl_reject_gui_root | PASS |
| Tcl_reject_gui_child | PASS |
| Tcl_reject_mixed_case_gui | PASS |
| Tcl_accept_path_external | PASS |
| Tcl_accept_path_sibling_name_boundary | PASS |
| actual_certutil_sha256_timing.xdc | PASS |
| actual_certutil_sha256_ios.xdc | PASS |
| parser_localized_header_uppercase_spaced_digest | PASS |
| parser_reject_missing_digest | PASS |
| parser_reject_two_digests | PASS |
| publisher_accept_absolute | PASS |
| publisher_accept_project_variable | PASS |
| publisher_accept_relative | PASS |
| publisher_reject_old_wrong_timing | PASS |
| publisher_reject_corrupted_ios | PASS |
| publisher_reject_wrong_source_hash | PASS |
| publisher_reject_wrong_snapshot_hash | PASS |
| publisher_reject_wrong_source_record_path | PASS |
| publisher_reject_wrong_snapshot_record_path | PASS |
| publisher_reject_project_uses_repository_XDC | PASS |
| publisher_reject_wrong_project_snapshot_path | PASS |
| publisher_reject_project_unresolved_variable | PASS |
| publisher_reject_missing_UsedIn_synthesis | PASS |
| publisher_reject_missing_UsedIn_implementation | PASS |
| publisher_reject_missing_ios_project_reference | PASS |
| publisher_reject_wrong_self_consistent_fixed_baseline | PASS |
| Tcl_snapshot_guard_accepts_correct_copy | PASS |
| Tcl_snapshot_guard_rejects_archived_wrong_XDC | PASS |
| source_and_real_constraints_unchanged | PASS |
