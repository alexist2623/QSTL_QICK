# 보상 파형 기대값: 읽기 검토와 검증 전용 compact 모델

현재 요청은 두 출력 −300..+300mV 각각 100점, HOLD10µs, RC τ10/20/30µs입니다. 각 τ에서 DC fixed_voltage300mV와 fixed_time10/20/30µs, 총12조건입니다. 이 문서와 helper는 계측기를 접근하지 않았습니다. 실제 새 bipolar 전점 또는 물리 측정의 PASS를 주장하지 않습니다.

## 세 가지 비교 대상을 구분합니다

- GUI requested ideal: 요청 전압·시간·DC/RC 설정에 따른 이상적 직접-DAC preemphasis 파형. 사용자 전압 정확도 판정의 기본 참조입니다.
- Exact compiled: 실제160-bit 명령·정수 RAMP·DC area·Q48 RC·14-bit 반올림으로 계산한 DAC 파형. 구현/양자화 원인 분리용 보조 참조이며 primary requested 값을 바꾸지 않습니다.
- External RC: 실제 외부 RC망 뒤 출력이라면 그 물리망의 τ·초기 capacitor 상태·연결을 추가로 알아야 합니다. 디지털 reset이 실제 capacitor를 reset한다고 가정하지 않습니다.

현재 helper는 두 번째 exact compiled 직접-DAC 기대값만 계산합니다. 실제 DAC scope를 평평한 요청 전압과 바로 비교하면 의도한 RC preemphasis 자체가 오차로 분류됩니다. 또한 RC 이전 목표 면적이 정확히0이어도 RC 이후 DAC의 전압 적분은 일반적으로0이 아닙니다. DAC 적분0을 DC보상 PASS 조건으로 사용하면 안 됩니다.

## 생산 소스의 모델과 초기화

- `qick/qick_lib/qick/precompensation.py:15`: scalar DAC rate를 사용한 `C=round(2^48/(2*τ_us*Fs_MHz))`. Fs=4800MHz일 때 τ10/20/30의 C는2932031007/1466015504/977343669입니다.
- `qick/firmware/ip/axis_awg_tuning_v3/src/v3_awg_rc_precomp.sv:67`: lane0부터 연속 scalar sample에 trapezoidal integral을 누적합니다. transport code를 x라 하면 `I[n]=I[n−1]+C*(x[n]+x[n−1])`, Q48이며 보정값은 `x[n]*2^48+I[n]`입니다.
- 같은 파일 `:35`: effective DAC4 transport-code 단위로 nearest rounding, tie는+∞ 방향, 최종−32768..32764 포화입니다. 음수에서 단순 truncation이나 대칭round를 쓰면 다릅니다.
- `v3_awg_tuning_ctrl.sv:286`, `:355`, `:420`: RAMP step은 bits127:96, 현재 transport값에서 signed fixed-point FRAC18로 증가하며 출력은 floor/saturation·마지막 sample 강제target입니다. RAMP의 native7 fabric-cycle startup을 유지합니다.
- `v3_awg_dc_area.sv:179`: RC 이전 effective14-bit code×모든scalar sample을48-bit area로 누적합니다. `:198`에서 마지막 emitted word까지 포함한 area를 snapshot합니다.
- `qick/qick_lib/qick/dc_area.py:64`: fixed_voltage는 지정크기 sample열+최대1partial sample+word zero padding, fixed_time은 N=16*words에 area를 q/q+1로 분배합니다. 양·음 area에 반대 polarity를 사용하며 두 모드 모두 정수area잔여0입니다.
- `v3_awg_dc_area.sv:251`: compensation첫area출력은command+17cycles입니다. normalarea5단계를 건너뛰고 RC11+v5AWG13+sum2를 거쳐, native31 metadata 기준 DAC는command+43cycles입니다. runtime `qick_fine_tune_sweep.py:7681`도17+31−5를 사용합니다.
- `v3_awg_dc_area.sv:278`: ZERO_EDGE가 마지막nonzero→0 trapezoid를 먼저 통과시키고 RESET_SHOT이area와RC history를 clear합니다. DC완료 후샷마다 디지털 상태는초기화되지만 외부capacitor상태는유지됩니다.
- `axis_awg_tuning_v3.sv:108`: RC command가enable/reset을따로설정합니다. AXIS SET0 자체는history를clear하지않습니다. `:112`의softwarezerooverride만abort/RCdisable+clear입니다.
- `PulseGenerator/DCWaveformGeneratorGUI/qick_fine_tune_sweep.py:2851`: 시작RC설정후SET0드레인→DCARM/disable드레인. `:2887` hardwareDC모드에서는IP완료barrier가RCclear까지보장하므로추가software-per-shotreset을생략합니다.
- `qick_dc_area.py:37`: command/register-add 기반 compact waveform ledger가exactfloor sum으로area를구합니다. `:210`은전체sweep최대DC완료시간을reserve하여shot간격은fixed-voltage실제pulse길이와같지않습니다.

## 배열 없이 계산하는 방법과 API

`compact_expectation.Run`은 constant 또는 fixed-point RAMP를 저장합니다. `prefix(k)`는앞k개의effective code합을 정수floor-sum으로계산합니다. `Waveform`은몇개구간의prefix만저장합니다.

처음 raw/history가0인shot에서 u[n]을effective code라하면:

`I[n] = 4*C*(u[n] + 2*sum(u[0:n]))`

따라서기록의scope sample시각에해당하는정수n만골라정확RC값을구할수있습니다. 전체4.8GHzscalar배열은필요없습니다. intermediate72-bit accumulator overflow는helper가거부하며포화이력경로를부정확하게추정하지않습니다. RC DAC최종포화여부는별도진단필드로반환합니다.

```python
from command_expectation import load_expected, output_model
expected = load_expected('expected_points.json.gz')  # plain JSON도지원
model = output_model(expected['points'][point]['outputs'][axis])
value = model.at_program_us(scope_time_us - single_scope_offset_us)
value['expected_direct_dac_mv']     # exact compiled 보조기준
value['unclipped_direct_dac_mv']
value['rtl_clipped_at_sample']
```

Command timestamp를변경하거나point별fit하지않습니다. native31, RAMP7, DC43은명시적기본인자입니다. helper는원본160-bitword에서step을직접읽고exporteddecoded값과다르면`metadata_step_mismatches`에남깁니다. 기존초기unipolarτ100fixture의step_signed가bits63:32를읽던metadata오류를발견하여원본을보존하고담당자에게전달했습니다. 신규bundle에서는이불일치가없어야합니다.

`compact_model_selfcheck.json`:120random signed조건,600prefix검사,2,132,090scalar RC recurrence비교,240exactDC면적검사PASS입니다. `signed_and_adapter_checks.json`:τ10/20/30×양/음×2DC모드12조건28,440scalar검사,기존실제command12출력의compact값과별도scalarrecurrence비교PASS입니다. 후자의실제commandfixture는초기0..400mV·τ100사전준비본이며최신bipolar실험검증을대체하지않습니다.

## 물리분석에서 유의할 점

100개의대칭−300..300mV값에는정확0target이없습니다. 고정offset은알려진전후idle또는DC완료·RCclear후zero gap에서한번만구합니다. mainwaveform의SET0/pre-DC gap에는RC integral이남으므로baseline으로사용하면안됩니다. 각조건마다scope시각정렬은단일offset으로고정하고,requested-ideal 참조와compiled-diagnostic 참조의오차를따로보존합니다.

τ10,20,30에서1µsramp뒤10µsHOLD의이상적DAC는각각약1.05V→2.05V,1.025V→1.525V,1.0167V→1.35V로변합니다(V=해당요청plateau값). V≈±300mV이면가장큰mainHOLD피크는약±615mV입니다. actual endpoint/register-step drift와DC구간까지포함한production rangegate를통과해야실물실행가능하며이근사치는range승인을대체하지않습니다.

1µsramp+10µsHOLD+1µsramp의목표area는약11V mV·µs입니다. fixed300mV tail은최대약11µs, fixed10/20/30µs tail전압크기는대략330/165/110mV입니다. body32µs에tail·명령barrier를합쳐1조건10,000점은약0.44~0.64초범위로예상되며정확한길이는새TProc모델이확정합니다.

0.6초의4800MHzsample을int16으로직접저장하면채널당약5.76GB가필요합니다. 반면scope2,000,000samples×2채널은rawcode8MB/조건,12조건96MB이며gzip으로무손실압축할수있습니다. compactmodel은구간·area만저장하고실제scope시각에서평가하므로이대규모scalar배열을만들지않습니다. scope전체기록이실험종료와zero를덮는지,dt및각ROI유효sample수를새acquisition별로확인해야합니다.
