# XDC 복원 및 추가 변경 대조 — 2026-10-07

사용자 지시에 따라 a3full5 및 하위 실행 프로세스를 종료한 뒤, 성공한 v2의 timing.xdc를 v3로 바이트 그대로 복사했다. 원래 v3 XDC와 중단 로그는 이 폴더에 보존했다. 성공 v2 manifest의 SHA256과 복원 파일 SHA256은 모두 9f9d68f0d1d9e69d9c236606d65781e5c1f5eed4b1672a24daebfb670e0bacfb이다.

- 새 전체 빌드: F:/Vivado_Output/a3full6, 세션51524. 로그: F:/Vivado_Output/a3full6_build.log.
- timing.xdc / ios.xdc: 성공 v2와 바이트 동일.
- BD: 7개 AWG IP/인스턴스의 v2→v3 및 DC_AREA_VERSION=1/DC_AREA_BITS=48 추가 외의 변경 없음. RF/DDR/FIR 설정·클록배선·주소는 동일.
- build Tcl: 프로젝트명/기본출력폴더 및 jobs5→3 차이. 현재 jobs/maxThreads=3/3은 이번 교정에서 변경하지 않았다. 이전 성공 v2는5/5이므로 전체 빌드조건이 같다고 주장하지 않는다.
- proj.tcl: 프로젝트명/기본출력폴더 차이.
- 기존 주요 RTL·생성기 53파일: 보존 baseline 해시 검사 PASS.
- GUI/QICK 라이브러리에는 새 v3 IP 인식·DC 명령·지연 정합·검증 연동 변경이 남아 있다. 전체 저장소가 무변경이라고 주장하지 않는다. 사용자 GUI 설정 JSON은 변경하지 않았다.
- 이번 교정에서 변경한 production 파일은 v3 timing.xdc 하나다. RTL은 바꾸지 않았으므로 현재 scoped1 GUI→RTL 및 scope1 폭 비교를 중복 실행하지 않는다.
- 검증/전체 timing 통과 전 BIT/HWH/XSA 배포 금지. 자동화 PAUSED 유지.

각 파일의 실제 차이는 같은 폴더의 *.diff, 해시는 restored_build_audit.json 참조.
