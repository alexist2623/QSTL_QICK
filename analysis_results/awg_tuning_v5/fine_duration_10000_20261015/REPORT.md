# Fine RF duration 단일 10,000점 sweep: 현재 컴파일 불가

2026-10-15 America/Vancouver. 사용자가 100×100 GUI→RTL 검증을 단일 RF duration 10,000점 가능 여부와 실제 어셈블리 확인으로 변경하여, 100×100 시뮬레이션은 시작하지 않았습니다.

현재 MainWindow에 비대각 3×3 virtual matrix를 로드하고 RF duration 위젯을 실제 QTest 입력으로 설정했습니다. `_experiment_run_arguments` → 생산 `runtime.build_qick_program` → `compile` 경로를 사용했습니다. 보드 연결 경계는 로컬 v5 HWH 기반 설정으로 대체했습니다. Run 버튼의 보드 acquisition은 호출하지 않았습니다.

## 결과

| 조건 | PMEM 명령 수 | Fine DMEM 표 | 결과 |
|---|---:|---:|---|
| 2점: 1, 100 sample | 234 | 12 words | 컴파일 성공 |
| 100점: 1..100 sample | 234 | 600 words | 컴파일 성공 |
| 10,000점: 1..10,000 sample | 생성 실패 | 60,000 words 필요 | DMEM 초과로 거부 |

현재 HWH의 `DMEM_N=12`로 tProcessor DMEM은 4,096 × 32bit = 16KiB입니다. 10,000점의 표만 240,000 bytes가 필요합니다. 원본 오류는 `runtime sweep tables do not fit tProcessor DMEM: low table ends at 60015, high state uses down through 4096`이며 [traceback](points_10000/compile_error.txt)을 보존했습니다. `results.json`의 passed는 이 용량 검사 실험이 기대대로 완료됐다는 의미이며, 10,000점 실행이 성공했다는 뜻이 아닙니다.

RF0만 duration을 sweep하고 RF2/RF4는 각각 97/31 sample 고정입니다. RF gain은 1000/2000/3000, frequency/phase는 0, RF 시작 offset은 100ns, HOLD는 10us, 각 점은 1회입니다. 세 AWG의 virtual matrix는 `[[1,.23,-.11],[-.17,1,.07],[.12,-.09,1]]`이며 RC/DC 보상은 이번 용량 확인에서 비활성화했습니다. 새 물리 파형 검증을 수행한 것은 아닙니다.

100점의 DMEM 표는 주소 16..615를 사용합니다. 완료 카운터 주소 1을 포함한 사용 주소 수는 601이며, 최고 사용 주소 기준 필요한 범위는 616 words입니다. RF 채널마다 16×128=2,048 I/Q samples(8KiB)의 패턴을 공유합니다. 점 수 증가가 waveform BRAM을 늘리지는 않습니다.

## 실제 어셈블리

- [전체 100점 ASM](points_100/program.asm), [행 번호 포함 ASM](points_100/program_numbered.asm), [PMEM](points_100/pmem.hex), [DMEM](points_100/dmem.txt).
- ASM 73행: 표 시작 주소 16을 포인터 `$1`에 저장. 74행: 반복 카운터 99(총 100점).
- 144..154행: `memr` 6개로 `[start, first_mode, envelope_address, tail_mode, tail_time, long_flag]`를 읽음. `mathi`로 각 열의 주소를 증가시키고 155행에서 포인터를 행 시작으로 되돌림.
- 159..161행: 짧은 파형은 gain을 2배로 조정해 product 모드의 스케일을 보정하고 `set` 1개로 시작. 긴 파형은 DDS plateau gain을 그대로 사용.
- 177..180행: `long_flag=0`이면 두 번째 명령을 건너뜀. 96 sample 이상이면 두 번째 `set`으로 DDS와 끝부분 envelope를 곱한 tail을 출력.
- 234..237행: `loopnz`로 다음 점을 선택하고 DMEM 포인터를 6 증가시킴. PMEM 본문은 점마다 복제하지 않음.

예를 들어 100 sample은 48 sample DDS plateau와 52 sample masked tail을 결합합니다. 1 sample은 패턴의 중간 주소에서 읽어 유효한 1 sample 다음을 0으로 만듭니다. 현재 300MHz×16 조건의 길이 단위는 0.208333…ns이며, 펄스 시작 시각은 fabric clock 단위입니다. [1/2/3/95/96/100 sample의 실제 표](points_100/selected_dmem_rows.json).

10,000점 하드웨어 sweep을 지원하려면 표 대신 길이/주소를 레지스터 연산으로 계산하는 등 컴파일러 변경이 필요합니다. 이번에는 기능 변경이나 자동 분할을 하지 않았습니다.

## 출력 합산 및 FIR

v5 HWH에서 AWG와 DDS의 합산 IP는 `axis_output_sum_v2`입니다. `s0_axis`는 AWG, `s1_axis`는 SG-v6 RF이며 `axis_output_sum_4/5/6` 뒤의 output register slice를 거쳐 DAC으로 연결됩니다. v4는 `axis_output_sum_v1`을 사용합니다.

v4/v5 HWH의 DDR 수집 경로에는 `ddr4_axis_fir_decim_300to1_v2_0`이 있습니다. 입력은 `axis_switch_ddr_M00_AXIS`, 출력은 `axis_buffer_ddr_sample_v3`이며 decimation은 10×10×3입니다. 이 FIR은 AWG+RF 출력 합산 IP와 별개입니다. 현재 보드에 로드된 bitstream은 접속하지 않아 확인하지 않았습니다. [HWH 설정과 SHA256](hardware_metadata.json).

## 범위와 보존

이번 작업은 실제 GUI→생산 컴파일러 용량 검사입니다. 10,000점은 RTL 입력 생성 전에 실패하므로 새 RTL 실행·실물 측정 결과가 없습니다. 100점도 ASM 생성 확인이며 새 RTL PASS로 표시하지 않습니다. 생산 Python, 사용자 JSON, 관련 RTL 및 v5 firmware 268파일의 해시는 변경되지 않았습니다. [보존 확인](preservation_audit.json), [전체 결과](results.json).
