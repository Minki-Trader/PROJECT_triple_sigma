# STEP02. 5분봉 마감 기반 OnNewBar 트리거 + Bid/Ask 데이터 수집 + 64-bar 버퍼

- 목적: Contract의 X(time axis 과거→현재, 64 bars)를 만들기 위한 **바 확정 감지 + 데이터 수집**을 안정적으로 구현한다.

---

## 1) 범위
- 새 5분봉 “확정(마감)”을 정확히 1회만 감지
- Bid OHLC 수집(Contract 고정)
- Ask-Bid spread 수집(게이트/비용 분석용)
- 64-bar 링버퍼 관리 및 윈도우 생성(과거→현재)

---

## 2) 입력 / 출력

### 입력
- MT5 시계열(Bid OHLC, Ask/Bid)
- timeframe=5m

### 출력
- `bars[64]`: 과거→현재 정렬된 64개 바(각 바는 O/H/L/C, time, spread 포함)
- `window_ready` 플래그(64 bars 채워졌는지)
- (로그) 누락/역순/중복 감지 정보

---

## 3) 고정 규칙(Invariants)
- price_basis: Bid
- time axis: X[0,0] oldest, X[0,63] latest (과거→현재)
- 새 바 확정은 1회만(중복 의사결정 금지)
- 데이터 누락/불연속 감지 시: 해당 바는 PASS-only로 안전 처리(상위 STEP의 fail-safe 원칙)

---

## 4) 설계(결정 사항)

### 4.1 OnNewBar 감지 방식(권장)
- Pattern C(Hybrid): **OnTick + OnTimer** 조합
  - OnTick: 마지막 Bid/Ask 스냅샷 갱신(스프레드/가격 계산 보조)
  - OnTimer: 1초~2초 주기로 “새로 마감된 5분봉” 검사
- 감지 키:
  - `last_closed_bar_time`를 저장하고, 새로 닫힌 바의 time이 바뀌면 1회 처리

### 4.2 데이터 수집(권장)
- Bid OHLC:
  - `CopyRates` 또는 `iClose/iOpen/...`를 사용하되 “확정 바”만 사용
- spread:
  - 기본: bar close 시점의 Ask-Bid
  - 구현상 close 순간 정확한 tick이 없을 수 있으므로,
    - “바 마감 직후 첫 tick”의 Ask/Bid를 close spread 근사로 기록(로그에 근사 방식 명시 권장)

### 4.3 링버퍼 / 윈도우
- 고정 길이 64
- 내부 저장은 “최신이 뒤”가 되도록 관리(디버깅 단순화)
- 윈도우 생성 시:
  - 항상 64개인지 검사
  - time이 단조 증가인지 검사
  - 실패 시 PASS-only + reason 로그

---

## 5) 로깅(권장)
bar_log(또는 별도 debug)에 아래를 남기면 역순/누락 버그를 빨리 잡는다.
- `bar_time_t`
- `window_first_time`, `window_last_time`
- `missing_bars_count`(time gap으로 추정)
- `newbar_detect_source`(tick/timer)
- `spread_price_t`, `spread_points_t`

---

## 6) 테스트/검증(Acceptance)
- [A1] 동일 바에 대해 의사결정이 2번 이상 발생하지 않음
- [A2] 64-bar 윈도우가 항상 과거→현재 정렬임(시간 단조 증가)
- [A3] 특정 구간(주말/서버 점검) 이후 재시작해도 “바 누락 감지 + PASS-only”가 동작

---

## 7) 구현 메모
- MT5에서 시계열 인덱스(0=현재 바) 함정이 많음 → 윈도우 생성 시 항상 역순을 검사하는 “가드 테스트”를 둔다.
