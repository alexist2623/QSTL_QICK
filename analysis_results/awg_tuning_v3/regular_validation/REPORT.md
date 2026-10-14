# 기본 소프트웨어 / 선택48 RTL 검증

기존 소프트웨어 검사 986개 통과.
48비트 area/boundary/production/fault 및 기존 SET/RAMP/SquarePulse 출력·지연 검사를 완료했습니다.
기존 주요 RTL 53개 해시 검사 및 GUI 설정 JSON 보존 검사도 통과했습니다.
검사기 임시 상위 폴더 누락으로 실패했던 두 모듈은 폴더 복구 후 동일 검사로 통과했습니다. 초기 실패 로그는 보존합니다.
추가 재검사: 프로젝트 지정 plottr 0.15.0 의존성 공급, 기존 qick.sim desktop 초기화, QApplication 명시적 종료를 적용했습니다.
SquareWave 한 검사의 오래된 오류문구 정규식은 빌드 폴더의 테스트 복사본에서만 현재 문구로 정정했습니다. ValueError 및 수치 검사는 그대로이며 저장소 테스트/생산 소스는 변경하지 않았습니다.
14개 assertion 뒤 Qt 접근 위반이 발생했던 초기 실행은 실패로 보존하고, 명시적 종료 재검사가 exit0인 것을 확인했습니다.

| 검사 | 결과 |
|---|---|
| legacy_before | PASS |
| qick_sim_test_models | PASS |
| qick_sim_test_outputs | PASS |
| qick_sim_test_qick_sim | PASS |
| qick_sim_test_tproc_v1 | PASS |
| qick_qick_test_awg_tuning | PASS |
| qick_qick_test_awg_tuning_asmv1 | PASS |
| qick_qick_test_awg_tuning_sim | PASS |
| qick_qick_test_awg_tuning_v2 | PASS |
| qick_qick_test_dc_area | PASS |
| qick_qick_test_ddr_iq64_support | PASS |
| qick_qick_test_ddr_triggered_pack_support | PASS |
| qick_qick_test_precompensation | PASS |
| qick_qick_test_qstl_awg_tuning_project_sim | PASS |
| qick_qick_test_square_pulse | PASS |
| qick_qick_test_square_pulse_desktop | PASS |
| qick_qick_test_tproc_v1_sim | PASS |
| gui_DCWaveformGeneratorGUI_test_acquisition_electrode_selection | PASS |
| gui_DCWaveformGeneratorGUI_test_acquisition_segment_timing | PASS |
| gui_DCWaveformGeneratorGUI_test_awg_segment_sweep_structure | PASS |
| gui_DCWaveformGeneratorGUI_test_awg_sweep_map | PASS |
| gui_DCWaveformGeneratorGUI_test_awg_tuning_v2 | PASS |
| gui_DCWaveformGeneratorGUI_test_bias_control | PASS |
| gui_DCWaveformGeneratorGUI_test_bias_measurement | PASS |
| gui_DCWaveformGeneratorGUI_test_bias_t_set_spacing | PASS |
| gui_DCWaveformGeneratorGUI_test_dac_current | PASS |
| gui_DCWaveformGeneratorGUI_test_dc_readout_timing | PASS |
| gui_DCWaveformGeneratorGUI_test_dc_voltage_calibration | PASS |
| gui_DCWaveformGeneratorGUI_test_dc_waveform_gui_rf | PASS |
| gui_DCWaveformGeneratorGUI_test_ddr_memory_usage | PASS |
| gui_DCWaveformGeneratorGUI_test_fir_ddr_profile | PASS |
| gui_DCWaveformGeneratorGUI_test_fir_rate_gui | PASS |
| gui_DCWaveformGeneratorGUI_test_gui_shutdown | PASS |
| gui_DCWaveformGeneratorGUI_test_incremental_virtual_grid | PASS |
| gui_DCWaveformGeneratorGUI_test_input_power_estimate | PASS |
| gui_DCWaveformGeneratorGUI_test_iq64_format | PASS |
| gui_DCWaveformGeneratorGUI_test_measurement_display | PASS |
| gui_DCWaveformGeneratorGUI_test_noise_acquisition | PASS |
| gui_DCWaveformGeneratorGUI_test_noise_analysis | PASS |
| gui_DCWaveformGeneratorGUI_test_power_calibration | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_dc_area | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_fine_tune_sweep | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_front_panel | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_output_triggers | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_power_calibration | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_qcodes_experiment | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_rc_validation | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_sparameter_sweep | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_square_dds | PASS |
| gui_DCWaveformGeneratorGUI_test_qick_square_wave | PASS |
| gui_DCWaveformGeneratorGUI_test_rc_precompensation | PASS |
| gui_DCWaveformGeneratorGUI_test_rc_sweep_matrix | PASS |
| gui_DCWaveformGeneratorGUI_test_rf_duration_oneshot | PASS |
| gui_DCWaveformGeneratorGUI_test_sparameter_magnitude_display | PASS |
| gui_DCWaveformGeneratorGUI_test_sparameter_phase_storage | PASS |
| gui_DCWaveformGeneratorGUI_test_square_awg_exclusion | PASS |
| gui_DCWaveformGeneratorGUI_test_square_dds_cleanup | PASS |
| gui_DCWaveformGeneratorGUI_test_square_dds_gui | PASS |
| gui_DCWaveformGeneratorGUI_test_square_dds_storage | PASS |
| gui_DCWaveformGeneratorGUI_test_square_desktop_imports | PASS |
| gui_DCWaveformGeneratorGUI_test_square_multi_output | PASS |
| gui_DCWaveformGeneratorGUI_test_square_output_controls | PASS |
| gui_DCWaveformGeneratorGUI_test_stability_diagram | PASS |
| gui_DCWaveformGeneratorGUI_test_trace_plot_overlay | PASS |
| gui_DCWaveformGeneratorGUI_test_trigger_output_panel | PASS |
| gui_DCWaveformGeneratorGUI_test_waveform_compensation_display | PASS |
| tb_dc_area | PASS |
| tb_dc_boundaries | PASS |
| tb_width_awg | PASS |
| tb_dc_faults | PASS |
| tb_set_saturation | PASS |
| legacy_outputs | PASS |
| legacy_after | PASS |
