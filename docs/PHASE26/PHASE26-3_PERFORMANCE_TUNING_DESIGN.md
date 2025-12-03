# PHASE26-3: Multi-Symbol Performance Tuning & Top100 Scalability - Design Document

**작성일**: 2025-12-03  
**상태**: 🔄 IN PROGRESS  
**Model**: Claude 4.5 Thinking  
**목적**: Multi-Symbol Engine v1 (Sequential) 성능 최적화 및 Top100 심볼 실시간 처리 기반 확보

---

## 0. Executive Summary

### 0.1. PHASE26-3 목표

**Primary Goal**: Multi-Symbol Engine v1 (Sequential Processing)을 유지하면서, Top100 심볼까지 실시간 안정 처리 가능한 성능 기반 확보

**핵심 원칙**:
1. ✅ **Sequential Processing 유지**: 코루틴/비동기 변경 없음 (PHASE27 이후)
2. ✅ **DO-NOT-TOUCH 엄수**: execution/engine.py 코어 로직 미수정
3. ✅ **최적화는 Adapter/Indicator/Utils 레이어에서**: 엔진 외부에서만 개선
4. ✅ **PHASE26-1/2 100% 하위 호환**: 기존 기능 유지

**Target Performance**:
- Top100 심볼 30분 PAPER 실행
- 평균 Loop Latency ≤ 150ms
- P95 Loop Latency ≤ 250ms
- CPU 1코어 ≤ 70%
- Memory ≤ 800MB

**Out of Scope**:
- ❌ Coroutine 기반 비동기 처리 (PHASE27 이후)
- ❌ 전략/파라미터 튜닝
- ❌ Risk/Portfolio 구조 변경
- ❌ Universe Provider 변경

---

## 1. AS-IS 분석

### 1.1. 현재 Multi-Symbol Engine v1 구조

**파일**: `execution/engine.py`

**핵심 플로우** (PHASE26-1 기준):
```
┌──────────────────────────────────────────────────────────────┐
│ engine.run_v2()                                              │
│ ────────────────────────────────────────────────────────────│
│  1. Universe Provider 로딩 (PHASE26-0)                      │
│  2. symbols = provider.get_universe()                        │
│  3. adapters = create_adapters(symbols)                      │
│  4. run(feed, broker, clock, strategies, symbols)            │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ engine.run() - Main Loop (Sequential)                        │
│ ────────────────────────────────────────────────────────────│
│  for candle in feed.stream():                                │
│    ├─ candle_symbol = candle["symbol"]                       │
│    ├─ buffer_key = (candle_symbol, timeframe)                │
│    ├─ buffers[buffer_key].append(candle)                     │
│    ├─ df = pd.DataFrame(buffers[buffer_key])                 │
│    ├─ calculate_indicators(df)  ← ⚠️ Hot Path #1            │
│    ├─ generate_signal(df, strategy)  ← ⚠️ Hot Path #2       │
│    ├─ portfolio.can_open_position(symbol)                    │
│    ├─ risk.check_exposure(symbol)                            │
│    └─ broker.place_order()                                   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2. 성능 병목 지점 (AS-IS)

#### Hot Path #1: Indicator 계산
```python
# execution/engine.py (line ~800-900)
for candle in feed.stream():
    df = pd.DataFrame(buffers[buffer_key])  # ⚠️ 매번 DataFrame 생성
    
    # Indicator 계산 (indicators/core_indicators.py)
    df['rsi'] = ta.RSI(df['close'], timeperiod=14)  # ⚠️ 전체 재계산
    df['ema20'] = ta.EMA(df['close'], timeperiod=20)
    df['ema50'] = ta.EMA(df['close'], timeperiod=50)
    # ... 10+ indicators
```

**문제점**:
- 매 캔들마다 **전체 버퍼** 재계산
- Top10: 10 symbols × 10 indicators × 1000 rows = 100,000회/분
- Top100: **1,000,000회/분** → CPU 병목

**해결 방향**:
- Incremental calculation (최근 1-2개만 업데이트)
- Indicator Cache Layer 추가

#### Hot Path #2: DataFrame 슬라이싱
```python
# 현재 패턴 (여러 곳에서 반복)
last_candle = df.iloc[-1]  # ⚠️ 느린 iloc
last_close = df['close'].iloc[-1]
last_rsi = df['rsi'].iloc[-1]
```

**문제점**:
- `iloc[-1]`은 O(n) 복잡도 (pandas 내부 인덱싱)
- 심볼 수 증가 시 latency 누적

**해결 방향**:
- `.iloc[-1]` → `.tail(1).squeeze()` 또는 직접 버퍼 접근
- 캔들 처리 시 최신 값을 변수에 미리 저장

#### Hot Path #3: Logging Overhead
```python
# 현재 로깅 (Multi-Symbol 루프 내부)
logger.info(f"[{symbol}] 신호 생성: {signal}")  # ⚠️ 100회/분
logger.debug(f"[{symbol}] RSI={rsi:.2f}, EMA20={ema20:.2f}")  # ⚠️ 1000회/분
```

**문제점**:
- Top100에서 로그 문자열 format이 CPU 사용
- logger.info/debug 내부에서 format 및 파일 I/O

**해결 방향**:
- Multi-Symbol 루프에서 INFO 로그 최소화
- TRACE 레벨 분리 (개발용만)
- Lazy formatting (f-string 회피)

### 1.3. 기존 Profiling 인프라 (재사용 가능)

**파일**: `monitoring/telemetry_profiler.py`

**기능**:
- `TelemetryProfiler`: 이벤트 기반 프로파일링 (context manager)
- `PerformanceMonitor`: 함수 실행 시간/메모리 측정 (데코레이터)
- psutil 기반 CPU/메모리 모니터링

**재사용 가능 부분**:
- ✅ `TelemetryProfiler.profile(event_name)` → 루프 latency 측정
- ✅ `PerformanceMonitor.start_monitoring()` → 시스템 리소스 측정
- ✅ `export_performance()` → JSON/로그 출력

**추가 필요 부분**:
- Per-symbol indicator latency 측정
- Queue depth (feed 버퍼 크기) 측정
- 자동 프로파일 분석 (hot path 감지)

---

## 2. TO-BE 설계

### 2.1. Performance Profiling Layer (확장)

**파일**: `common/perf/perf_profiler.py` (신규)

**목적**: PHASE26-3 전용 프로파일러 (기존 telemetry_profiler 확장)

**추가 기능**:
1. **Per-Symbol Indicator Latency**:
   ```python
   profiler.log_indicator_latency(symbol, indicator_name, duration_ms)
   ```

2. **Loop Latency Per-Symbol**:
   ```python
   with profiler.profile_loop(symbol):
       # 캔들 처리
   ```

3. **Queue Depth Tracking**:
   ```python
   profiler.log_queue_depth(symbol, depth)
   ```

4. **Auto Analysis**:
   ```python
   hot_paths = profiler.analyze_hot_paths()
   # Returns: [(symbol, indicator, avg_ms, p95_ms), ...]
   ```

5. **Report Generation**:
   ```python
   profiler.export_report("phase26_3_top100_profile.json")
   ```

**구현 전략**:
```python
# common/perf/perf_profiler.py
from monitoring.telemetry_profiler import TelemetryProfiler, PerformanceMonitor

class MultiSymbolProfiler:
    """
    Multi-Symbol 전용 프로파일러 (PHASE26-3)
    
    기능:
    - Per-symbol indicator latency
    - Loop latency per symbol
    - Queue depth tracking
    - Hot path analysis
    """
    
    def __init__(self):
        self.telemetry = TelemetryProfiler()  # ⭐ 재사용
        self.perf = PerformanceMonitor()      # ⭐ 재사용
        
        # PHASE26-3 전용
        self.per_symbol_indicators = defaultdict(lambda: defaultdict(list))
        self.loop_latencies = defaultdict(list)
        self.queue_depths = defaultdict(list)
    
    def log_indicator_latency(self, symbol, indicator, duration_ms):
        self.per_symbol_indicators[symbol][indicator].append(duration_ms)
    
    def analyze_hot_paths(self):
        """Top 10 느린 indicator 반환"""
        hot_paths = []
        for symbol, indicators in self.per_symbol_indicators.items():
            for indicator, latencies in indicators.items():
                avg_ms = sum(latencies) / len(latencies)
                p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]
                hot_paths.append((symbol, indicator, avg_ms, p95_ms))
        
        return sorted(hot_paths, key=lambda x: x[3], reverse=True)[:10]
```

### 2.2. Indicator Cache Layer

**파일**: `common/indicators/indicator_cache.py` (신규)

**목적**: Incremental Indicator Calculation (전체 재계산 회피)

**핵심 아이디어**:
```python
# AS-IS: 매번 전체 재계산
df['rsi'] = ta.RSI(df['close'], timeperiod=14)  # 1000 rows 재계산

# TO-BE: 최근 1-2개만 계산
cache = IndicatorCache()
new_rsi = cache.update_rsi(symbol, new_close, period=14)  # O(1)
```

**구현 전략**:
```python
class IndicatorCache:
    """
    Incremental Indicator Calculation Cache
    
    목적:
    - 매 캔들마다 전체 재계산 회피
    - 최근 N개 데이터만 유지
    - pandas 연산 최소화
    """
    
    def __init__(self, max_history=1000):
        self.cache = {}  # {(symbol, indicator): deque}
        self.max_history = max_history
    
    def update_rsi(self, symbol, new_close, period=14):
        """
        RSI Incremental Update
        
        로직:
        1. 기존 cache에서 close 히스토리 조회
        2. new_close 추가
        3. 최근 period+1개만 사용해서 RSI 계산
        4. cache 업데이트
        """
        key = (symbol, 'close')
        if key not in self.cache:
            self.cache[key] = deque(maxlen=self.max_history)
        
        self.cache[key].append(new_close)
        
        # 최근 period+1개만 사용 (RSI 계산용)
        if len(self.cache[key]) >= period + 1:
            recent_closes = list(self.cache[key])[-period-1:]
            df_temp = pd.DataFrame({'close': recent_closes})
            rsi_series = ta.RSI(df_temp['close'], timeperiod=period)
            return rsi_series.iloc[-1]  # 최신 값만 반환
        else:
            return None  # 데이터 부족
    
    def update_ema(self, symbol, new_close, period=20):
        """EMA Incremental Update"""
        # Similar logic
    
    def get_latest(self, symbol, indicator):
        """캐시된 최신 indicator 값 조회"""
        key = (symbol, indicator)
        if key in self.cache and self.cache[key]:
            return self.cache[key][-1]
        return None
```

**제한사항**:
- **완전한 Incremental 계산은 복잡함** (EMA는 가능하지만 RSI는 어려움)
- **현실적 접근**: 최근 period+N개만 사용해서 계산 (100% incremental은 아니지만 충분히 빠름)

**적용 가능 Indicator**:
- ✅ EMA/SMA: 완전 incremental 가능
- ✅ RSI: 최근 30-50개만 사용 (충분히 정확)
- ✅ MACD: EMA 기반이므로 incremental 가능
- ✅ Bollinger Bands: 최근 period+20개만 사용

### 2.3. DataFrame 슬라이싱 최적화

**변경 범위**: `execution/engine.py`, `strategies/*.py`, `indicators/core_indicators.py`

**AS-IS → TO-BE**:
```python
# AS-IS (느림)
last_close = df['close'].iloc[-1]  # O(n)

# TO-BE Option 1: tail()
last_close = df['close'].tail(1).squeeze()  # O(1) in pandas >= 1.0

# TO-BE Option 2: 직접 버퍼 접근 (가장 빠름)
last_close = buffers[buffer_key][-1]['close']  # O(1)
```

**적용 위치**:
```python
# execution/engine.py (line ~850)
# AS-IS
last_rsi = df['rsi'].iloc[-1]
last_ema20 = df['ema20'].iloc[-1]

# TO-BE
latest_values = {
    'rsi': df['rsi'].tail(1).squeeze(),
    'ema20': df['ema20'].tail(1).squeeze(),
    'ema50': df['ema50'].tail(1).squeeze(),
    # ...
}
last_rsi = latest_values['rsi']
last_ema20 = latest_values['ema20']
```

**주의사항**:
- ❌ **DO-NOT-TOUCH 위반 회피**: engine.py 코어 로직은 수정하지 않음
- ✅ **Adapter/Indicator 레이어에서만** 최적화

### 2.4. Logging 비용 절감

**변경 범위**: `common/logger.py`, `execution/engine.py` (로그 호출부만)

**AS-IS → TO-BE**:
```python
# AS-IS (Multi-Symbol 루프 내부, INFO 레벨)
logger.info(f"[{symbol}] 신호 생성: {signal}")  # ⚠️ 100회/분

# TO-BE Option 1: DEBUG 레벨로 변경
logger.debug(f"[{symbol}] 신호 생성: {signal}")  # ✅ 프로덕션에서 꺼짐

# TO-BE Option 2: TRACE 레벨 추가 (개발용만)
logger.trace(f"[{symbol}] 신호 생성: {signal}")  # ✅ 기본적으로 비활성화

# TO-BE Option 3: Lazy formatting (f-string 회피)
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("[%s] 신호 생성: %s", symbol, signal)  # ✅ f-string 미사용
```

**TRACE 레벨 추가**:
```python
# common/logger.py
import logging

# TRACE 레벨 추가 (DEBUG보다 낮음)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

logging.Logger.trace = trace
```

### 2.5. Top100 Config & Runner

**파일**: `configs/paper/phase26_3_top100_paper_30m.yml`

**핵심 설정**:
```yaml
# Universe Provider (Top100)
universe:
  enabled: true
  provider:
    type: topn_volume
    top_n: 100  # ⭐ Top100
    cache_ttl_sec: 3600

# Paper 설정 (30분)
paper:
  duration_mode: "wall_clock"
  duration_hours: 0.5  # ⭐ 30분 (Acceptance 테스트용)

# 보수적 리스크 (Top100용)
position_sizing:
  default_risk_per_trade: 0.001  # ⭐ 0.1% RPT (Top10: 0.2% → Top100: 0.1%)

portfolio:
  max_open_positions: 20  # Top100 × 1포지션/5심볼 가정
  max_exposure_pct: 0.3   # ⭐ 30% (Top10: 50% → Top100: 30%)

risk:
  max_exposure_per_symbol: 0.05  # 심볼당 5% 한도
```

**파일**: `scripts/infra/phase26_3_run_top100_paper.py`

**핵심 기능**:
1. **단계별 실행 (Top10 → Top20 → Top50 → Top100)**:
   ```python
   def run_scaling_test(base_config_path):
       """
       Top10 → Top20 → Top50 → Top100 순차 실행
       
       각 단계별:
       - Universe top_n 변경
       - 30분 실행
       - 프로파일링 데이터 수집
       - 자동 분석 및 리포트 생성
       """
       for top_n in [10, 20, 50, 100]:
           config = load_config(base_config_path)
           config['universe']['provider']['top_n'] = top_n
           
           # 30분 실행
           profiler = MultiSymbolProfiler()
           run_paper_with_profiling(config, profiler, duration_minutes=30)
           
           # 분석
           hot_paths = profiler.analyze_hot_paths()
           save_report(f"phase26_3_top{top_n}_report.md", hot_paths)
   ```

2. **자동 프로파일링**:
   - Loop latency per symbol
   - Indicator latency per symbol
   - CPU/메모리 사용량
   - Trade activity

3. **자동 리포트 생성**:
   - MD 리포트 (템플릿 기반)
   - JSON 요약 (그래프용)

### 2.6. Acceptance Criteria (강화)

**필수 조건 (MUST PASS)**:

| Criteria | Target | 측정 방법 |
|----------|--------|-----------|
| **Top100 PAPER 실행** | 30분 이상 | wall_clock 모드 |
| **평균 Loop Latency** | ≤ 150ms | profiler.loop_latencies 평균 |
| **P95 Loop Latency** | ≤ 250ms | profiler.loop_latencies P95 |
| **CPU 사용률** | ≤ 70% | psutil.Process().cpu_percent() |
| **Memory 사용량** | ≤ 800MB | psutil.Process().memory_info().rss |
| **CRITICAL 오류** | 0건 | logs/application.log 파싱 |
| **Active Positions** | 0건 (종료 시) | DB 쿼리 |
| **Aggregate 평가** | ≥ 100건 | 로그 파싱 |
| **활성 Trade 심볼** | ≥ 3개 | DB 쿼리 (per-symbol trades) |

**권장 조건 (NICE TO HAVE)**:
- Top10/20/50 단계별 Latency 증가율 < 2배
- Hot Path Top 10에서 개선 가능 항목 식별
- Indicator Cache Hit 비율 > 80%

---

## 3. Implementation Plan

### 3.1. STEP 1: Performance Profiler 확장 (2H)

**파일**:
- `common/perf/__init__.py` (신규)
- `common/perf/perf_profiler.py` (신규)

**작업**:
1. `monitoring/telemetry_profiler.py` 임포트 및 확장
2. `MultiSymbolProfiler` 클래스 구현
3. Per-symbol indicator/loop latency 측정
4. Queue depth 측정
5. Auto analysis (`analyze_hot_paths()`)
6. Export report (JSON + MD template)

**테스트**:
- `tests/test_phase26_3_performance.py` 생성
- Profiler 동작 검증 (mock data)

### 3.2. STEP 2: Indicator Cache Layer (3H)

**파일**:
- `common/indicators/__init__.py` (확장)
- `common/indicators/indicator_cache.py` (신규)

**작업**:
1. `IndicatorCache` 클래스 구현
2. `update_rsi()`, `update_ema()`, `update_macd()` 구현
3. 최근 N개만 사용하는 로직
4. `get_latest()` 조회 함수

**적용**:
- `indicators/core_indicators.py`에서 캐시 사용 (optional)
- 기존 calculate_indicators() 100% 호환 유지

**테스트**:
- Cache hit/miss 비율 측정
- 계산 정확도 검증 (전체 재계산과 비교)

### 3.3. STEP 3: DataFrame/Logging 최적화 (1H)

**변경**:
- `execution/engine.py`: 로그 레벨 조정 (INFO → DEBUG)
- `common/logger.py`: TRACE 레벨 추가
- `strategies/scalping.py`: `.iloc[-1]` → `.tail(1).squeeze()`

**주의**:
- DO-NOT-TOUCH 위반 회피
- 최소 변경 원칙

### 3.4. STEP 4: Top100 Config + Runner (2H)

**파일**:
- `configs/paper/phase26_3_top100_paper_30m.yml` (신규)
- `scripts/infra/phase26_3_run_top100_paper.py` (신규)

**작업**:
1. Top100 Universe Config 생성
2. Runner 구현 (PHASE25-0 harness 재사용)
3. 단계별 실행 (Top10/20/50/100) 지원
4. 자동 프로파일링 통합
5. 자동 리포트 생성

### 3.5. STEP 5: 테스트 작성 (1H)

**파일**:
- `tests/test_phase26_3_performance.py` (신규)

**테스트 케이스**:
1. `test_profiler_log_indicator_latency()`
2. `test_profiler_analyze_hot_paths()`
3. `test_indicator_cache_update_rsi()`
4. `test_indicator_cache_hit_ratio()`
5. `test_top100_config_loading()`
6. `test_runner_wiring()`
7. `test_latency_mock()`

### 3.6. STEP 6: 문서 작성 (1H)

**파일**:
- `docs/PHASE26/PHASE26-3_PERFORMANCE_TUNING_DESIGN.md` (본 파일)
- `docs/PHASE26/PHASE26-3_PERFORMANCE_TEST_REPORT_TEMPLATE.md` (템플릿)
- `docs/PHASE26/PHASE26_ROADMAP_UPDATE.md` (업데이트)

### 3.7. STEP 7: Git Commit (0.5H)

**작업**:
- 변경 파일 확인
- 의미 있는 커밋 메시지
- Roadmap 업데이트

**총 예상 시간**: ~10.5H (실제 Top100 실행 제외)

---

## 4. Known Limitations & Future Work

### 4.1. PHASE26-3 제한사항

1. **Sequential Processing 유지**:
   - 심볼 수 증가 시 latency는 선형 증가
   - Top100 → Top200 확장 시 추가 최적화 필요
   - **해결**: PHASE27에서 coroutine 도입

2. **Indicator Cache 정확도**:
   - 최근 N개만 사용하므로 극히 드물게 오차 발생 가능
   - 대부분의 indicator는 최근 30-50개로 충분히 정확
   - **해결**: 필요 시 Cache 비활성화 옵션

3. **Top100 Trade Activity**:
   - 보수적 리스크 설정으로 실제 Trade 수는 제한적
   - **해결**: 향후 Per-symbol 리스크 조정 (PHASE29)

4. **No Real-Time Dashboard**:
   - 프로파일링 데이터는 사후 분석용
   - **해결**: PHASE28에서 실시간 모니터링 대시보드

### 4.2. Future Work (PHASE27+)

**PHASE27: Coroutine 기반 비동기 처리**:
- `async def stream()` Feed Adapter
- 심볼별 concurrent processing
- Top200+ 지원

**PHASE28: Real-Time Monitoring Dashboard**:
- Grafana/Prometheus 통합
- 실시간 latency/CPU/메모리 그래프
- Hot path 실시간 감지

**PHASE29: Per-Symbol Config Override**:
- 심볼별 리스크 파라미터
- 심볼별 전략 선택
- 심볼별 타임프레임

---

## 5. Risk Mitigation

### 5.1. 리스크 요소

1. **Indicator Cache 버그**:
   - **대응**: 기존 calculate_indicators() 100% fallback 지원
   - **테스트**: 정확도 검증 테스트 (전체 재계산과 비교)

2. **Profiling Overhead**:
   - **대응**: Profiler는 기본적으로 비활성화, 필요 시만 활성화
   - **측정**: Profiler ON/OFF Latency 비교

3. **Top100 Scalability**:
   - **대응**: 단계별 실행 (Top10/20/50/100)으로 병목 조기 발견
   - **Fallback**: Top50까지만 안정적이면 일단 PASS

4. **DO-NOT-TOUCH 위반**:
   - **대응**: Code Review 필수, engine.py 변경 최소화
   - **검증**: PHASE26-1/2 회귀 테스트 100% PASS

### 5.2. 회귀 방지

- ✅ PHASE26-0/1/2 테스트 재실행 (44 tests)
- ✅ 단일 심볼 모드 100% 호환 확인
- ✅ Top10 PAPER 회귀 테스트

---

## 6. Acceptance Criteria Summary

### 6.1. 구현 완료 체크리스트

- [ ] Performance Profiler 확장 (`common/perf/perf_profiler.py`)
- [ ] Indicator Cache Layer 구현 (`common/indicators/indicator_cache.py`)
- [ ] DataFrame/Logging 최적화
- [ ] Top100 Config 생성 (`configs/paper/phase26_3_top100_paper_30m.yml`)
- [ ] Top100 Runner 구현 (`scripts/infra/phase26_3_run_top100_paper.py`)
- [ ] 테스트 작성 (7+ tests, 100% PASS)
- [ ] 설계 문서 작성 (본 파일)
- [ ] 리포트 템플릿 작성
- [ ] PHASE26_ROADMAP 업데이트
- [ ] Git Commit

### 6.2. 실행 테스트 체크리스트 (향후)

- [ ] Top10 PAPER 30분 실행 (평균 Latency ≤ 150ms)
- [ ] Top20 PAPER 30분 실행 (평균 Latency ≤ 150ms)
- [ ] Top50 PAPER 30분 실행 (평균 Latency ≤ 150ms)
- [ ] **Top100 PAPER 30분 실행** (평균 Latency ≤ 150ms) ⭐
- [ ] CPU ≤ 70%, Memory ≤ 800MB
- [ ] CRITICAL 오류 0건
- [ ] 최소 100건 Aggregate 평가
- [ ] 최소 3개 심볼 Trade 발생

---

**작성자**: Cascade AI (Claude 4.5 Thinking)  
**작성일**: 2025-12-03  
**검토 대상**: PHASE26-2 완료 후 즉시 착수  
**핵심 원칙**: "Sequential 최적화 + DO-NOT-TOUCH 엄수 + Top100 Scalability"
