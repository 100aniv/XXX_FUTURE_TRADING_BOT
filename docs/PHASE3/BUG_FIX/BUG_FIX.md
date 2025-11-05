# 현재 플로우(실제 코드 기준)
mermaid
flowchart LR
    A[main.py] -->|모드별 주입| B[feed: Historical/Live]
    A --> C[broker: Sim/Paper/Live]
    A --> D[clock: Sim/Live]
    B --> E[execution/engine.run()]
    E --> F[signals: 전략 호출 + SignalGenerator.validate]
    F -->|save_signal_to_db| G[(monitoring.signals)]
    G --> H[strategies/ensemble.py\nDB기반 통합]
    H -->|결정| I[decision]
    I --> J[execution/position_sizer.py]
    J --> K[execution/risk_manager.py]
    K -->|허용| L[broker.execute(...)]
    L --> M[(trading.trades / backtest SQLite)]
    L --> N[포트폴리오/포지션 업데이트]
    N --> O[레포팅(reports/...)]
핵심: “전략 → 시그널(검증/DB) → 앙상블(통합/결정) → 사이징 → 리스크 → 주문/체결 → 포트폴리오 업데이트 → 리포팅”
모드별로 달라지는 것은 feed/broker/clock 세 개뿐이며, 루프는 동일합니다.
# 모듈 정리
[main/루프 진입]
main.py
: 모드(backtest/paper/live) 결정 → 심볼 관리(SymbolManager) → feed/broker/clock 주입 → 
engine.run()
[수집/피드]
collectors/historical_collector.py
, 
collectors/multi_historical_collector.py
, 
collectors/websocket_collector.py
: feed.stream() 공급자
[시그널/전략]
signals/signal_generator.py
: 버퍼/지표/쿨다운/MTF/레짐 필터 보조, 
process_candle
, 
validate_signal
strategies/*.py: signal_logic(df, config)로 신호 생성
strategies/ensemble.py
: DB 신호 집계 → 가중치/점수 → trading.decisions 저장
[실행/리스크/사이징]
execution/engine.py
: 공통 루프, 사이징/리스크 체크, broker.execute, DB 저장
execution/position_sizer.py
: RPT/품질가중치/한도/청산가 여유 검증
execution/risk_manager.py
: 일일 손실, 동시 포지션, 노출, Flash Guard, 연속손실 쿨다운
[실행기/브로커]
execution/executors/simulation.py
: 백테스트 체결(슬리피지/수수료)
execution/executors/paper.py
: 가상 체결
execution/executors/live.py
: Binance SDK 체결
[DB]
common/database.py
: PostgreSQL + 백테스트 SQLite(trades)
save_signal_to_db
, 
save_backtest_trade
, 
close_backtest_trade
, 
init_backtest_db
[지표]
indicators/
: add_indicators(df)
# 핵심 문제점(코드-문서 불일치 및 버그)
[1] ensemble 인터페이스 불일치
execution/engine.py
는 
ensemble_module.combine_signals(signals, conn, config)
를 호출하지만
strategies/ensemble.py
에는 
combine_signals
가 없습니다. 제공되는 것은 
process_pending_signals(conn)
 중심입니다.
결과: 예외 발생 시 첫 신호 fallback(의도하지 않은 동작).
[2] save_signal_to_db 호출 인자 불일치
common/database.py::save_signal_to_db(...)
는 timeframe, candle_closed_at, direction, confidence 등 필수 인자를 요구합니다.
현재 
engine.run()
에서는 side, timestamp 등으로 잘못 전달하고 있어 DB 저장이 실패하거나 잘못 저장될 수 있습니다.
참고: 
main.py
(실시간 경로)에서는 올바른 인자로 저장하고 있습니다.
[3] Broker/Clock 어댑터 경로 불일치
main.py
는 execution.adapters의 SimBroker/PaperBroker/LiveBroker, SimClock/LiveClock을 기대하지만
현재 레포 내 execution/adapters/ 폴더가 보이지 않습니다. 대신 execution/executors/*.py가 존재.
engine.run()
은 
broker.execute(decision, qty)
 시그니처를 기대하는데, executors/*는 
execute(side, price, qty)
 형태입니다.
이 간극을 메우는 BrokerAdapter 또는 executor_wrapper가 필요합니다. (경로/존재 확인 필요)
[4] 포트폴리오/포지션 매니저 누락
engine.run()
이 execution.portfolio_manager.PortfolioManager, execution.position_tracker.PositionTracker를 import하는데
현재 레포에는 해당 파일이 보이지 않습니다. (문서에는 존재) → 런타임 import 에러 예상.
[5] 시그널 생성 전략 세트 불일치
signals/signal_generator.py
는 import에 scalping/daytrade/swing만 직접 명시.
실제 운용은 
engine.run()
에서 
strategies
 dict로 주입하므로 동작에는 문제 없지만, 기본값 전략 세트 갱신 필요.
[6] 이중 실행 경로 혼재
execution/engine.run()
은 내부에서 바로 주문을 실행하는 “직접형”이고,
문서 기준의 execution/manager.py + executor_wrapper.py는 “DB pull형(결정→실행)”입니다.
두 경로 중 하나로 일원화해야 합니다. (권장: 공통 루프 직결형 유지)
[7] 중복/불필요 파일
core/trading_pipeline.py
(실험 잔재), 
common/trading_flow.py
(새로 추가된 중복 파일) 등
실제 실행과 무관한 파일이 존재. 혼동 유발.
# 권장 최종 구조(요청하신 추천 구조와 현 레포 매핑)
text
common/
  clock.py          ← SimClock/LiveClock (현재 엔진에서 사용, 실제 파일 필요)
  types.py          ← DTO(Candle/Order/Fill/Decision 등)
  performance.py    ← 이미 존재(common/performance.py)
collectors/
  feeds.py          ← HistoricalFeed/LiveFeed 래핑 (현재 collectors/*를 인터페이스 통일)
indicators/         ← 그대로
signals/            ← 유지. SignalGenerator/validate_signal 사용
strategies/
  *.py              ← trend, reversion, breakout, scalping, daytrade, swing
  ensemble.py       ← EnsembleStrategy (DB 기반 + 메모리 모드 보강)
trading/ (= execution/)
  risk.py           ← risk_manager.py
  portfolio.py      ← portfolio_manager.py (필요)
  broker.py         ← BrokerAdapter (Sim/Paper/Live executor를 감싼 execute(decision, qty))
  executor.py       ← executors/* 사용
  loop.py           ← engine.run() (공통 루프)
reports/
  trading_reporter.py, performance_reporter.py
현재 코드 기준으로는 
execution/engine.py
(loop), 
execution/risk_manager.py
, 
execution/position_sizer.py
, execution/executors/*를 재사용하고,
누락된 portfolio_manager.py, broker_adapter.py(또는 executor_wrapper.py), clock.py를 채우면 완성됩니다.
# 개선 사항(우선순위별)
[필수-버그] ensemble 호출 정합성
strategies/ensemble.py
에 
combine_signals(signals, config)
 메모리 모드를 추가하거나,
engine.run()
에서 DB 기반 루틴을 사용하도록 바꾸되 인터페이스를 일치시키세요.
권장: 메모리 모드 추가
입력: signals: List[Dict]
출력: { side, entry, sl, tp, confidence, score, strategy: 'ensemble' }
현재 문서 로직(
calculate_weights
,
calculate_ensemble_score
,
apply_bonuses
) 재사용 가능
[필수-버그] save_signal_to_db 인자 수정
execution/engine.py
에서 
save_signal_to_db()
를 아래와 같이 맞추세요.
timeframe: config['timeframe']
candle_closed_at: datetime.fromtimestamp(ts/1000)
direction: signal['side']
confidence: signal.get('confidence', 0.75)
atr/leverage/features: 존재 시 전달
[필수-구조] BrokerAdapter/Clock 구현
broker.execute(decision, qty)
를 만족하는 어댑터를 추가해 executors/*와 시그니처를 맞추세요.
clock.update(ts)를 제공하는 SimClock/LiveClock을 common/clock.py 등으로 표준화하고 실제 파일 추가.
[필수-구조] 포트폴리오/포지션 매니저 파일 추가
execution/portfolio_manager.py, execution/position_tracker.py 최소 기능 버전 작성(엔진 현재 호출부 충족).
최소 스펙:
PortfolioManager: get_equity(), 
update_equity()
, 
add_position()
, 
remove_position()
, can_open_position(...)
PositionTracker: check_tpsl_with_partial(...), tp_manager.calculate_tp_levels(...)
[정리] 실행 경로 일원화
execution/manager.py + executor_wrapper.py vs 
engine.run()
 중 하나만 사용.
권장: 
engine.run()
 공통 루프 유지. 
manager.py
는 리포팅/헬퍼로 최소화.
[정리] 중복/불필요 파일 삭제
삭제 후보:
core/trading_pipeline.py
 (실험 잔재)
common/trading_flow.py
 (중복 개념, 실제 경로에 연결 안 됨)
오래된 스크립트(원하시면 목록화)
“삭제 전 목록-승인-삭제” 절차로 진행 권장.
[정합성] SignalGenerator 기본 전략 세트 보강
import의 기본 전략 세트에 trend/reversion/breakout 추가 또는 완전히 주입 기반으로만 유지(기본값 제거).
# 모듈 간 관계 플로우차트
mermaid
flowchart TD
    subgraph Adapters[모드별 어댑터]
      FEED[Feed\nHistoricalFeed/LiveFeed]
      BROKER[BrokerAdapter\nSim/Paper/Live]
      CLOCK[Clock\nSimClock/LiveClock]
    end

    MAIN[main.py] --> FEED
    MAIN --> BROKER
    MAIN --> CLOCK

    FEED --> LOOP[execution/engine.run()]
    CLOCK --> LOOP

    subgraph Strategies[전략/시그널]
      STRATS[strategies/*.py\nsignal_logic(df, cfg)]
      SG[signals/SignalGenerator\nvalidate_signal()]
    end

    LOOP -->|df+config| STRATS
    STRATS -->|raw_signal| SG
    SG -->|ok| SIGDB[(monitoring.signals)]

    subgraph Ensemble[앙상블]
      ESM[strategies/ensemble.py\n(process_pending_signals)\n+ combine_signals(mem)]
    end

    SIGDB --> ESM
    ESM --> DEC[final decision]

    subgraph Execution[실행 단계]
      SIZER[execution/position_sizer.py]
      RISK[execution/risk_manager.py]
      PF[execution/portfolio_manager.py]
      PT[execution/position_tracker.py]
    end

    DEC --> SIZER --> RISK -->|allowed| BROKER --> TRADES[(trading.trades/SQLite)]
    BROKER --> PF
    BROKER --> PT
# 삭제 후보 목록(제안)
[중복/실험 파일]
core/trading_pipeline.py
common/trading_flow.py
 ← 제가 추가한 파일, 제거 권장
[구조 혼동 야기]
오래된 create_*, 
apply_docker.py
, 
backup_docker.py
, 
swap_main.py
 등은 “운영상 필요 여부” 확인 후 정리
승인 주시면 안전하게 백업 → 제거 진행하겠습니다.
# 실행에 영향 주는 구체적 버그 포인트
execution/engine.py
save_signal_to_db(...)
 매개변수 틀림 → DB 쿼리 실패 가능
ensemble_module.combine_signals(...)
 없음 → fallback 동작으로 정확도 저하
PortfolioManager, PositionTracker import 실패 가능
broker.execute(decision, qty)
 인터페이스 가정 vs 실제 executors/*의 
execute(side, price, qty)
 차이
이 4가지는 “바로 수정” 대상입니다.

# 제안 작업 순서(짧고 안전하게)
엔진-DB 시그널 저장 인자 수정
engine.run()
의 
save_signal_to_db()
 호출부를 
common/database.py
 시그니처에 맞게 수정
Ensemble 메모리 모드 추가 또는 엔진에서 DB 방식 호출 교정
strategies/ensemble.py
에 
combine_signals(signals, config)
 추가
또는 
engine.run()
에서 
process_pending_signals(conn)
로 호출 패턴 변경
BrokerAdapter/Clock 파일 추가
execution/broker_adapter.py(또는 기존 
executor_wrapper.py
 위치 확정)
common/clock.py 또는 execution/adapters/clocks.py 정식화
PortfolioManager/PositionTracker 최소 구현 파일 추가
엔진이 import/호출하는 최소 API만 제공
중복 파일 정리
core/trading_pipeline.py
, 
common/trading_flow.py
 삭제(승인 후)
README 되돌림/정합화
실제 구조 반영해 간결하게 정리(요청 주신 방향으로)
# 요청사항
[승인 필요] 삭제 후보
core/trading_pipeline.py
, 
common/trading_flow.py
 삭제 승인 여부?
[선호도] Ensemble 처리 방식
엔진 내 “메모리 모드 
combine_signals(signals)
”로 일원화 vs
주기 프로세서(
process_pending_signals
) DB 방식 유지(엔진은 decisions poll) 중 선택?
[확인] Broker/Clock 경로
execution.adapters 경로가 없어 executor_wrapper 또는 broker_adapter로 맞추겠습니다. 기존 파일이 다른 경로에 있으면 알려주세요.
# 작업 상태 요약
분석: 코드/문서 교차검증 완료. 현재 공통 루프는 존재하며, 시그널 모듈/앙상블/사이징/리스크의 역할은 분리되어 있습니다.
문제점: ensemble 인터페이스/DB 저장 인자/어댑터/누락 파일/중복 파일.
개선안: 6개 항목 제시(인터페이스 정합화, 어댑터/매니저 구현, 파일 정리, README 정리).
필요한 결정: 삭제 승인(2건), 앙상블 처리 방식 선택, 어댑터 경로 확인.
원하시면 바로 1~2번(엔진-DB 인자/ensemble 인터페이스)부터 수정 패치를 올리겠습니다.

---

# 2025-10-23 실제 코드 검증 결과 (BUG_FIX.md 분석 재검증)

## ✅ BUG_FIX.md의 오류 정정

### 실제 파일 존재 확인:
- ✅ `execution/portfolio_manager.py` 존재 (290줄, 완벽 구현)
- ✅ `execution/position_tracker.py` 존재 (207줄, TP 분할 지원)
- ✅ `execution/adapters/` 디렉토리 존재
- ✅ `execution/adapters/brokers.py` 존재 (SimBroker/PaperBroker/LiveBroker)
- ✅ `execution/adapters/clocks.py` 존재 (SimClock/LiveClock)
- ✅ `strategies/ensemble.py` combine_signals() 메서드 존재 (라인 559-608)

### BUG_FIX.md의 잘못된 지적:
1. ❌ "포트폴리오/포지션 매니저 누락" → 실제로는 **존재함**
2. ❌ "Broker/Clock 어댑터 경로 불일치" → 실제로는 **execution/adapters/에 모두 존재**
3. ❌ "ensemble.combine_signals 없음" → 실제로는 **존재함** (라인 559)

---

## 🔴 실제 발견된 치명적 버그

### Bug #1: engine.py save_signal_to_db() 호출 오류 (치명적!)

**위치:** `execution/engine.py` 라인 280-290

**문제:**
```python
# ❌ 잘못된 코드 (기존)
save_signal_to_db(
    signal_id=str(uuid4()),
    strategy_id=strategy_id,
    symbol=candle_symbol,
    side=signal.get('side'),          # ❌ 매개변수 이름 틀림
    entry_price=signal.get('entry'),
    sl_price=signal.get('sl'),
    tp_price=signal.get('tp'),
    timestamp=ts                       # ❌ 타입 틀림 (int → datetime 필요)
)
```

**database.py의 실제 시그니처:**
```python
def save_signal_to_db(
    signal_id: str,
    strategy_id: str,
    symbol: str,
    timeframe: str,              # ❌ 누락!
    candle_closed_at: datetime,  # ❌ timestamp 대신 candle_closed_at
    direction: str,              # ❌ side 대신 direction
    confidence: float,           # ❌ 누락!
    entry_price: Optional[float] = None,
    sl_price: Optional[float] = None,
    tp_price: Optional[float] = None,
    atr: Optional[float] = None,
    leverage: Optional[int] = None,
    features: Optional[Dict[str, Any]] = None
)
```

**수정 완료 (2025-10-23):**
```python
# ✅ 수정된 코드
from datetime import datetime
save_signal_to_db(
    signal_id=str(uuid4()),
    strategy_id=strategy_id,
    symbol=candle_symbol,
    timeframe=config.get('timeframe', '5m'),  # ✅ 추가
    candle_closed_at=datetime.fromtimestamp(ts/1000),  # ✅ int → datetime
    direction=signal.get('side'),  # ✅ side → direction
    confidence=signal.get('confidence', 0.75),  # ✅ 추가
    entry_price=signal.get('entry'),
    sl_price=signal.get('sl'),
    tp_price=signal.get('tp'),
    atr=signal.get('atr'),  # ✅ 추가
    leverage=signal.get('lev')  # ✅ 추가
)
```

**영향:**
- 신호가 DB에 저장되지 않음 → ensemble이 신호를 읽을 수 없음
- 단일 전략 모드에서는 영향 없음 (메모리 신호만 사용)
- **앙상블 모드에서 치명적**

---

### Bug #2: portfolio_manager.py 과도한 거래 차단

**위치:** `execution/portfolio_manager.py` 라인 50

**문제:**
```python
self.max_correlated_positions = 2  # BTC/ETH 등 메이저 코인
```

**로그 증거:**
```
⛔ 포트폴리오 거부: 상관성 높은 포지션 초과 (2/2)
```

**영향:**
- BTC/ETH/BNB 등 메이저 코인은 동시에 2개까지만 진입 가능
- **3,111건 → 실제 체결 훨씬 적음**

**수정 완료 (2025-10-23):**
```yaml
# config.yml
portfolio:
  max_correlated_positions: 5  # 2→5 완화
```

---

### Bug #3: risk_manager.py 연속 손실 쿨다운

**위치:** `execution/risk_manager.py` 라인 64

**문제:**
```python
self.max_consecutive_losses = config.get('risk', {}).get('max_consecutive_losses', 4)
```

**로그 증거:**
```
⛔ 리스크 체크 실패: 연속 손실 쿨다운 (6회)
진입 거래: 3111건 → 12건
```

**수정 완료 (config.yml에서 이미 999로 설정됨):**
```yaml
risk:
  max_consecutive_losses: 999  # ✅ 이미 완화됨
```

---

## 📊 근본 원인 요약

### 왜 "검증된 조건"(RSI<30 + BB하단)인데도 실패했나?

1. **신호 저장 실패 (Bug #1):**
   - save_signal_to_db() 호출 오류 → DB에 신호 안 쌓임
   - 앙상블 모드 사용 시 치명적

2. **과도한 리스크 차단 (Bug #2, #3):**
   - 포트폴리오 매니저: 상관성 포지션 2개 제한
   - 리스크 매니저: 연속 손실 쿨다운
   - **3,111건 신호 → 12건 체결**

3. **데이터 플로우 단절:**
   - 캔들 → 신호 생성 (✅ 정상)
   - 신호 → DB 저장 (❌ 실패)
   - DB → 앙상블 (❌ 신호 없음)
   - 앙상블 → 체결 (❌ 결정 없음)

---

## ✅ 수정 완료 항목 (2025-10-23)

1. ✅ **engine.py save_signal_to_db() 호출 수정**
   - timeframe, candle_closed_at, direction, confidence 추가
   - int → datetime 변환 추가
   - atr, leverage 추가

2. ✅ **config.yml 리스크 파라미터 완화**
   - portfolio.max_correlated_positions: 2 → 5
   - risk.max_consecutive_losses: 이미 999 (완화됨)

3. ✅ **백테스트 DB 실행 단위 초기화 (누적 방지)**
   - 파일: `common/database.py`
   - 위치: `init_backtest_db()`
   - 변경: 테이블 생성 후 `DELETE FROM trades` 실행하여 이전 실행 결과 누적 제거
   - 영향: TUNING_VIBLE 리포트가 현재 실행의 거래만 집계 (총 거래 수/ROI/MDD 왜곡 제거)

4. ✅ **지표 파라미터 주입(문서/YAML과 코드 정합)**
   - 파일: `execution/engine.py`
   - 위치: DataFrame 생성 직후 `add_indicators(...)`
   - 변경: `config.yml.indicators.*` 값을 `add_indicators()`에 전달(EMA/RSI/MACD/BB/ATR/Volume)
   - 영향: 전략 로직이 문서/설정대로 동작(기본값으로 고정되던 문제 해소)

5. ✅ **타임프레임 일관화(선택 전략 TF → 리스크/DB 기록 동기화)**
   - 파일: `execution/engine.py`
   - 위치: SignalGenerator 초기화 직후
   - 변경: 선택된 전략의 `timeframe`을 `effective_timeframe`으로 결정하여
     - `risk.config['timeframe']` 동기화 (Flash-Guard/쿨다운 윈도우 정합)
     - `save_signal_to_db(... timeframe=effective_timeframe ...)`로 저장
   - 영향: 전략 TF와 리스크/DB 기록의 불일치 해소 (검증/분석 혼선 제거)

6. ✅ **전략 필터 설정을 SignalGenerator로 정확히 반영**
   - 파일: `execution/engine.py`
   - 위치: `signal_gen_config` 구성 시
   - 변경: 선택 전략의 `filters.{mtf_confirm, volume_spike, regime}`를 `enable_mtf_confirm`, `require_htf_aligned`, `enable_vol_spike_filter`, `enable_regime_filter`로 반영
   - 영향: `SignalGenerator.validate_signal()`이 전략 필터를 정확히 사용(비활성화/누락 상태 방지)

> Note: Feed 생성 시점의 `timeframe`은 `main.py`의 Top-level 설정을 따르며, 현재 실행에서는 `backtest.data_file`이 우선 사용되어 CSV 자체의 해상도(예: 15m)가 유지됩니다. Feed TF 동기화는 다음 사이클에서 별도 이슈로 다룹니다(한 번에 하나씩 원칙).

---

## 📋 다음 단계

1. **불필요한 파일 archived로 이동**
   - cleanup/ 디렉토리의 오래된 로그
   - 사용하지 않는 실험 코드

2. **테스트 재실행**
   - TEST_SCENARIO.md 준수
   - BACKTEST_PERIODS.md 기준 데이터
   - TEST_CHECKLIST.md 업데이트

3. **문서 업데이트**
   - 수정 사항 반영
   - 실제 구조와 일치하도록 정리