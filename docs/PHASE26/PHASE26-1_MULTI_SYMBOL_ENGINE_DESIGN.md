# PHASE26-1: Multi-Symbol Engine v1 - Design Document

**작성일**: 2025-12-03  
**상태**: 🔄 IN PROGRESS  
**목적**: Universe Provider → Engine 통합 + Multi-Symbol 실행 플로우 v1

---

## 0. Executive Summary

### 0.1. AS-IS vs TO-BE 비교

| 항목 | AS-IS (PHASE26-0) | TO-BE (PHASE26-1) |
|------|-------------------|-------------------|
| **Universe 개념** | ❌ 없음 | ✅ UniverseProvider 통합 |
| **심볼 선정** | 단일 심볼 (`config['symbol']`) | 단일 또는 Universe (설정 기반) |
| **엔진 구조** | 단일 심볼만 처리 | Multi-Symbol 오케스트레이션 v1 |
| **Per-Symbol 상태** | N/A | 독립적 buffer/state 관리 |
| **Config 모드** | `universe.enabled=false` (기본) | `universe.enabled=true` 지원 |
| **하위 호환성** | 100% | 100% 유지 (enabled=false 시) |

### 0.2. PHASE26-1 범위

✅ **포함**:
- UniverseProvider → Engine 통합 (config.universe 연동)
- Multi-Symbol 실행 플로우 v1 (오케스트레이션)
- Per-Symbol 상태 관리 (buffer, portfolio, risk)
- 단일 심볼 모드 100% 호환성 보장

❌ **제외** (향후 PHASE):
- Advanced per-symbol coroutine (PHASE26-2+)
- Top10+ 성능 최적화 (PHASE27)
- DB 메트릭 기반 Universe (PHASE27+)
- Universe 자동 갱신 (PHASE28+)

---

## 1. AS-IS 구조 분석

### 1.1. 단일 심볼 실행 플로우 (engine.run_v2)

```
┌──────────────────────────────────────────────────────────────┐
│ scripts/run_v2.py                                            │
│ ────────────────────────────────────────────────────────────│
│  1. Config 로딩 (load_config_with_mode)                     │
│  2. engine.run_v2(mode, config, clean_state) 호출           │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ execution/engine.py::run_v2()                                │
│ ────────────────────────────────────────────────────────────│
│  1. symbol = config.get('symbol', 'BTCUSDT')  ← 단일 심볼    │
│  2. load_strategies(config) 호출                             │
│  3. create_adapters(mode, symbols=[symbol])                  │
│  4. run(feed, broker, clock, strategies, config) 호출        │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ execution/engine.py::run()                                   │
│ ────────────────────────────────────────────────────────────│
│  • symbol = config.get('symbol')  ← 단일 심볼 가정           │
│  • buffers: Dict[tuple, deque] = {}                          │
│    → key: (symbol, timeframe)                                │
│  • PortfolioManager(config) ← 이미 멀티 심볼 지원            │
│  • RiskManager(config, portfolio) ← 심볼별 exposure 지원     │
│  • SignalGenerator(config, strategies)                       │
│  • feed.start() → Main Loop                                  │
│    - 캔들 수신                                               │
│    - 버퍼 업데이트                                           │
│    - 신호 생성 (단일 심볼)                                   │
│    - 포지션 관리 (단일 심볼)                                 │
└──────────────────────────────────────────────────────────────┘
```

### 1.2. AS-IS 제한사항

1. **단일 심볼 하드코딩**:
   - `symbol = config.get('symbol', 'BTCUSDT')` (line 69, 149, 171, 319)
   - 엔진 전체가 단일 심볼만 처리하도록 설계됨

2. **Universe 미통합**:
   - UniverseProvider는 구현되었지만, 엔진에서 사용하지 않음
   - `config.universe` 섹션이 존재하지만 무시됨

3. **Per-Symbol 상태 부족**:
   - `buffers`는 이미 `(symbol, tf)` 키로 멀티 심볼 지원 가능
   - 하지만 실제로는 단일 심볼만 처리함

4. **Adapter 생성**:
   - `symbols=[symbol]`로 항상 단일 심볼만 전달

### 1.3. AS-IS 강점 (재사용 가능)

✅ **이미 멀티 심볼을 고려한 설계**:

1. **PortfolioManager**:
   - `self.positions: Dict[str, List[Dict]]` ← 심볼별 포지션 관리
   - `can_open_position(symbol, strategy, ...)` ← 심볼 인자 존재
   - 심볼별 exposure 추적 (`_get_symbol_exposure(symbol)`)

2. **RiskManager**:
   - `self.symbol_exposures: Dict[str, float]` ← 심볼별 노출도
   - `self.portfolio` 참조로 멀티 심볼 체크 가능

3. **Buffers**:
   - `buffers: Dict[tuple, deque] = {}` ← key: `(symbol, timeframe)`
   - 이미 멀티 심볼/TF 지원 가능

4. **Adapters**:
   - `create_adapters(mode, symbols=[...])` ← symbols는 리스트로 이미 정의됨
   - Feed/Broker는 멀티 심볼 처리 가능 (특히 Paper/Live)

---

## 2. PHASE26-1 설계: Multi-Symbol Engine v1

### 2.1. 핵심 설계 원칙

1. **단일 진입점 유지**: `engine.run_v2()` 중심 구조 유지
2. **기존 모듈 재사용**: Portfolio/Risk/Buffer 구조 최대한 활용
3. **최소 변경**: 새 클래스/파일 최소화, 기존 코드 확장
4. **100% 하위 호환**: `universe.enabled=false` 시 기존 동작 완벽 유지

### 2.2. TO-BE 실행 플로우

```
┌──────────────────────────────────────────────────────────────┐
│ scripts/run_v2.py                                            │
│ ────────────────────────────────────────────────────────────│
│  1. Config 로딩 (load_config_with_mode)                     │
│  2. engine.run_v2(mode, config, clean_state) 호출           │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ execution/engine.py::run_v2()  ← ⭐ PHASE26-1 수정 지점      │
│ ────────────────────────────────────────────────────────────│
│  1. universe_cfg = load_universe_config(config)  ← 신규      │
│  2. if universe_cfg:                                         │
│       provider = create_universe_provider(universe_cfg)      │
│       symbols = [s.symbol for s in await provider.get_universe()] │
│     else:                                                    │
│       symbols = [config.get('symbol', 'BTCUSDT')]  ← 기존    │
│  3. load_strategies(config)                                  │
│  4. create_adapters(mode, symbols=symbols)  ← symbols 전달   │
│  5. run(feed, broker, clock, strategies, config, symbols)    │
│     ↑ run() 함수 시그니처 변경 (symbols 인자 추가)          │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ execution/engine.py::run()  ← ⭐ PHASE26-1 수정 지점         │
│ ────────────────────────────────────────────────────────────│
│  Args:                                                       │
│    symbols: List[str]  ← 신규 인자 (기본값: None)           │
│                                                              │
│  • if symbols is None:  ← 하위 호환                         │
│      symbols = [config.get('symbol', 'BTCUSDT')]            │
│                                                              │
│  • Main Loop 수정:                                           │
│    for symbol in symbols:  ← Multi-Symbol 오케스트레이션     │
│      - buffers[(symbol, tf)] 관리                           │
│      - 캔들 수신 (per-symbol)                                │
│      - 신호 생성 (per-symbol)                                │
│      - 포지션 관리 (per-symbol)                              │
│      - Portfolio/Risk 체크 (symbol 인자 전달)                │
└──────────────────────────────────────────────────────────────┘
```

### 2.3. Multi-Symbol 오케스트레이션 v1 전략

#### Option A: Sequential (단순, 안정적) ← ⭐ PHASE26-1 채택

```python
# Pseudo code
for symbol in symbols:
    # 1. 캔들 수신 (symbol별)
    candle = feed.get_latest_candle(symbol, timeframe)
    
    # 2. 버퍼 업데이트
    buffer_key = (symbol, timeframe)
    buffers[buffer_key].append(candle)
    
    # 3. 신호 생성 (symbol 전달)
    df = pd.DataFrame(buffers[buffer_key])
    signal = signal_gen.generate_signal(df, symbol=symbol)
    
    # 4. 포지션 관리 (symbol 전달)
    if signal['side']:
        portfolio.can_open_position(symbol, strategy, ...)
        # ...
```

**장점**:
- 구현 단순, 검증 용이
- 기존 코드 재사용 극대화
- Debugging 쉬움

**단점**:
- 심볼 수 증가 시 latency 증가
- 실시간 처리 제약 (Top10+ 부하 시)

#### Option B: Coroutine (병렬, 복잡) ← PHASE26-2+로 연기

```python
async def process_symbol(symbol, ...):
    # per-symbol coroutine
    ...

tasks = [process_symbol(s, ...) for s in symbols]
await asyncio.gather(*tasks)
```

**장점**:
- 높은 처리량 (Top50+)
- 실시간 병렬 처리

**단점**:
- 구현 복잡도 높음
- 동시성 버그 리스크
- PHASE26-1 범위 초과

---

## 3. 세부 구현 설계

### 3.1. engine.run_v2() 변경

#### Before (AS-IS):
```python
def run_v2(mode: str, config: dict, clean_state: bool = False):
    # ...
    symbol = config.get('symbol', 'BTCUSDT')  # 단일 심볼
    
    # ...
    adapters = _create_paper_adapters(config, clean_state)
    
    run(feed, broker, clock, strategies, ensemble_module, config)
```

#### After (TO-BE):
```python
def run_v2(mode: str, config: dict, clean_state: bool = False):
    # ...
    
    # ⭐ PHASE26-1: Universe Provider 통합
    from common.config_loader import load_universe_config
    from common.universe_provider import create_universe_provider
    import asyncio
    
    universe_cfg = load_universe_config(config)
    
    if universe_cfg:
        logger.info(f"🌐 [PHASE26-1] Universe Provider 활성화: {universe_cfg.provider_type}")
        provider = create_universe_provider(universe_cfg)
        universe = asyncio.run(provider.get_universe())
        symbols = [s.symbol for s in universe]
        logger.info(f"✅ [PHASE26-1] Universe: {len(symbols)}개 심볼 - {symbols[:5]}...")
    else:
        # 기존 단일 심볼 모드 (하위 호환)
        symbol = config.get('symbol', 'BTCUSDT')
        symbols = [symbol]
        logger.info(f"📊 [PHASE26-1] 단일 심볼 모드: {symbol}")
    
    # Adapters 생성 (symbols 전달)
    adapters = _create_paper_adapters(config, clean_state, symbols)
    
    # run() 호출 (symbols 전달)
    run(feed, broker, clock, strategies, ensemble_module, config, symbols=symbols)
```

### 3.2. _create_*_adapters() 변경

#### Before:
```python
def _create_paper_adapters(config: dict, clean_state: bool) -> dict:
    from execution.adapters import create_adapters
    
    symbol = config.get('symbol', 'BTCUSDT')  # 단일 심볼
    
    feed, broker, clock = create_adapters(
        mode='paper',
        symbols=[symbol],  # 단일 리스트
        config=config,
        logger=logger
    )
    # ...
```

#### After:
```python
def _create_paper_adapters(config: dict, clean_state: bool, symbols: List[str]) -> dict:
    from execution.adapters import create_adapters
    
    # PHASE26-1: symbols 인자로 받음
    feed, broker, clock = create_adapters(
        mode='paper',
        symbols=symbols,  # Multi-Symbol 지원
        config=config,
        logger=logger
    )
    # ...
```

### 3.3. engine.run() 변경

#### Before (AS-IS):
```python
def run(feed, broker, clock, strategies: Dict, ensemble_module, config: Dict):
    # ...
    symbol = config.get("symbol", "BTCUSDT")  # 단일 심볼 가정
    
    buffers: Dict[tuple, deque] = {}  # {(symbol, timeframe): deque}
    
    # Main Loop
    while True:
        # 단일 심볼만 처리
        candle = feed.get_latest_candle()  # symbol 없음
        buffers[(symbol, timeframe)].append(candle)
        # ...
```

#### After (TO-BE):
```python
def run(feed, broker, clock, strategies: Dict, ensemble_module, config: Dict, symbols: List[str] = None):
    # ⭐ PHASE26-1: symbols 인자 추가
    if symbols is None:
        # 하위 호환: 단일 심볼 모드
        symbols = [config.get("symbol", "BTCUSDT")]
        logger.info(f"📊 [PHASE26-1] 단일 심볼 모드 (symbols 미전달): {symbols[0]}")
    else:
        logger.info(f"🌐 [PHASE26-1] Multi-Symbol 모드: {len(symbols)}개 심볼")
    
    buffers: Dict[tuple, deque] = {}  # {(symbol, timeframe): deque}
    
    # Per-Symbol 초기화
    for symbol in symbols:
        buffer_key = (symbol, timeframe)
        buffers[buffer_key] = deque(maxlen=lookback)
        logger.info(f"✅ [PHASE26-1] Buffer 초기화: {symbol} ({timeframe})")
    
    # Main Loop
    while True:
        # ⭐ PHASE26-1: Multi-Symbol Sequential Processing
        for symbol in symbols:
            # 1. 캔들 수신
            candle = feed.get_latest_candle(symbol, timeframe)  # ← Feed에 symbol 전달
            if candle is None:
                continue
            
            # 2. 버퍼 업데이트
            buffer_key = (symbol, timeframe)
            buffers[buffer_key].append(candle)
            
            # 3. 신호 생성 (symbol 전달)
            df = pd.DataFrame(buffers[buffer_key])
            signal = signal_gen.generate_signal(df, symbol=symbol)  # ← symbol 전달
            
            # 4. 포지션 관리 (symbol 인자 명시)
            if signal['side']:
                can_open, reason = portfolio.can_open_position(
                    symbol=symbol,  # ← 명시적 전달
                    strategy=strategy_id,
                    position_value=notional,
                    side=signal['side']
                )
                # ...
```

### 3.4. SignalGenerator 변경 (최소)

기존 `SignalGenerator.generate_signal(df)`는 symbol을 전달받지 않음.  
하지만 내부적으로 strategy 모듈에 df만 전달하므로, symbol은 필요 시 metadata로 전달.

#### Option 1: symbol 인자 추가 (최소 변경)
```python
def generate_signal(self, df, symbol=None):
    # symbol은 로깅용으로만 사용
    logger.debug(f"[SIGNAL] {symbol} - 신호 생성 중...")
    # 기존 로직 유지
    return strategy.compute_signal(df, config)
```

#### Option 2: 변경 없음 (더 안전)
- symbol은 엔진 레벨에서만 관리
- SignalGenerator는 df만 받고 symbol 무시
- **PHASE26-1에서는 Option 2 채택** (최소 변경 원칙)

### 3.5. Per-Symbol 상태 관리

#### 3.5.1. Buffers (이미 지원)
```python
buffers: Dict[tuple, deque] = {}  # {(symbol, timeframe): deque}
```
- 이미 멀티 심볼/TF 지원 가능
- 변경 불필요

#### 3.5.2. Portfolio/Risk (이미 지원)
```python
# PortfolioManager
portfolio.can_open_position(symbol="BTCUSDT", strategy="scalping", ...)

# RiskManager
risk.check_per_symbol_exposure(symbol="BTCUSDT", ...)
```
- 이미 symbol 인자 존재
- 변경 불필요

#### 3.5.3. Reject Cooldown (symbol 키 사용)
```python
reject_cooldown: Dict[str, float] = {}  # {f"{symbol}_{strategy}": last_reject_time}
```
- 이미 symbol을 포함한 키 사용
- 변경 불필요

---

## 4. Config 연동

### 4.1. universe 섹션 (PHASE26-0에서 이미 정의)

```yaml
# configs/base.yml
universe:
  enabled: false  # ⭐ PHASE26-1: true로 변경 시 멀티 심볼 활성화
  
  provider:
    type: topn_volume  # "topn_volume" | "static"
    top_n: 10
    cache_ttl_sec: 3600
    
    static_symbols:  # Static Provider용
      - BTCUSDT
      - ETHUSDT
    
  filters:
    quote_assets:
      - USDT
    exclude_symbols:
      - BTCDOWNUSDT
      - BTCUPUSDT
    min_24h_volume_usd: 10000000  # 10M USDT
    market_types:
      - PERPETUAL
    contract_status: TRADING

# 기존 symbol/symbols 구조는 하위 호환 유지
symbol: BTCUSDT  # universe.enabled=false 시 사용
symbols:
  mode: top100
  # ...
```

### 4.2. Config 로딩 플로우

```python
# 1. config 로딩
config = load_config_with_mode('paper')

# 2. Universe Provider 설정 로딩
universe_cfg = load_universe_config(config)  # ← PHASE26-0에서 구현됨

# 3. 분기
if universe_cfg:
    # Multi-Symbol 모드
    provider = create_universe_provider(universe_cfg)
    universe = await provider.get_universe()
    symbols = [s.symbol for s in universe]
else:
    # 단일 심볼 모드 (기존)
    symbols = [config.get('symbol', 'BTCUSDT')]
```

---

## 5. Backward Compatibility 전략

### 5.1. 하위 호환 보장 방법

1. **Default: universe.enabled=false**
   - 기존 config는 universe 섹션이 없거나 enabled=false
   - 이 경우 100% 기존 동작 유지

2. **run() 함수 시그니처**
   - `symbols: List[str] = None` ← 기본값 None
   - None이면 단일 심볼 모드로 fallback

3. **Adapter 생성**
   - `symbols` 인자가 없으면 `[config['symbol']]`로 fallback

4. **테스트**
   - 기존 테스트는 universe 설정 없이 실행 → 모두 PASS 유지

### 5.2. 하위 호환 검증 계획

```python
# tests/test_phase26_1_multi_symbol_engine.py

def test_backward_compatibility_single_symbol():
    """universe.enabled=false 시 기존 동작 유지"""
    config = {
        'symbol': 'BTCUSDT',
        'universe': {'enabled': False},  # 명시적 비활성화
        # ... (기존 config)
    }
    
    # run_v2 호출 시 단일 심볼 모드로 동작해야 함
    # symbols = ['BTCUSDT']
    # 기존 테스트와 동일한 결과
```

---

## 6. Acceptance Criteria (PHASE26-1 PASS 기준)

### 6.1. 필수 조건

| Criterion | 구현 방법 | 검증 방법 |
|-----------|-----------|-----------|
| ✅ UniverseProvider → Engine 통합 | `run_v2()`에서 `load_universe_config()` 호출 | Config enabled=true 시 Universe 조회 성공 |
| ✅ Multi-Symbol 실행 플로우 v1 | `run()` 함수 symbols 인자 추가 + Sequential processing | 최소 2개 심볼 처리 테스트 |
| ✅ Per-Symbol 상태 관리 | Buffers, Portfolio, Risk symbol 키 사용 | 심볼별 독립 포지션 생성 확인 |
| ✅ 단일 심볼 모드 100% 호환 | `universe.enabled=false` fallback 로직 | 기존 테스트 모두 PASS |
| ✅ 테스트 통과 | `test_phase26_1_multi_symbol_engine.py` | 핵심 시나리오 3개 PASS |
| ✅ 회귀 테스트 | PHASE25/26-0 테스트 유지 | 기존 테스트 PASS |
| ✅ 문서 완성 | 설계 + 리포트 | 문서 존재 확인 |
| ✅ PHASE_ROADMAP 업데이트 | PHASE26-1 상태 → COMPLETE | Roadmap 반영 |
| ✅ Git Commit | 의미 있는 커밋 메시지 | Working tree clean |

### 6.2. 성공 지표

- **단일 심볼 모드**: 기존 동작 100% 유지 (테스트로 검증)
- **Multi-Symbol 모드**: StaticUniverseProvider로 2~3개 심볼 처리 성공
- **Per-Symbol 독립성**: 각 심볼에 대해 독립적인 포지션/리스크 관리
- **회귀 없음**: PHASE25 튜닝 테스트 모두 PASS

---

## 7. Known Limitations (PHASE26-1)

### 7.1. 제한사항

1. **Sequential Processing Only**:
   - 심볼 수가 많아지면 latency 증가
   - Top10 이상에서는 실시간 처리 제약
   - → PHASE26-2에서 coroutine 구조로 개선

2. **No Universe Auto-Refresh**:
   - Universe는 프로세스 시작 시 1회만 조회
   - 실행 중 Universe 변경 불가
   - → PHASE28에서 hot-reload 지원

3. **No DB Metrics Integration**:
   - TopN은 Binance API 기반만 지원
   - DB 마켓 메트릭 미연동
   - → PHASE27에서 DBMetricsUniverseProvider 추가

4. **No Per-Symbol Config Override**:
   - 모든 심볼에 동일한 전략/리스크 적용
   - 심볼별 파라미터 조정 불가
   - → 향후 PHASE에서 지원

### 7.2. 알려진 이슈

- **Feed.get_latest_candle(symbol, tf)**: Feed adapter가 symbol 인자를 지원하는지 확인 필요
  - Backtest: HistoricalFeed는 symbol을 이미 지원 가능 (구조 확인 필요)
  - Paper/Live: WebSocket Feed는 multi-symbol 구독 지원 필요 (확인 필요)

---

## 8. 구현 순서 (Step-by-Step)

### Step 1: engine.run_v2() Universe 통합
- `load_universe_config()` 호출
- `create_universe_provider()` 호출
- symbols 리스트 생성
- Adapters에 symbols 전달

### Step 2: _create_*_adapters() 수정
- symbols 인자 추가
- create_adapters()에 symbols 전달

### Step 3: engine.run() Multi-Symbol 지원
- symbols 인자 추가 (기본값 None)
- Per-Symbol 초기화 (buffers)
- Main Loop 수정 (for symbol in symbols)
- symbol 전달 (Feed, Portfolio, Risk)

### Step 4: Feed Adapter 확인/수정
- get_latest_candle(symbol, tf) 지원 확인
- 필요 시 수정

### Step 5: 테스트 작성
- test_backward_compatibility_single_symbol
- test_static_universe_multi_symbol
- test_topn_universe_multi_symbol (선택)

### Step 6: 회귀 테스트
- PHASE25/26-0 테스트 실행
- 실패 시 수정

### Step 7: 문서 작성
- PHASE26-1_MULTI_SYMBOL_ENGINE_REPORT.md
- PHASE_ROADMAP.md 업데이트

### Step 8: Git Commit
- git status / git diff --stat
- 의미 있는 커밋 메시지

---

## 9. References

- **PHASE26-0 설계**: `docs/PHASE26/PHASE26-0_UNIVERSE_PROVIDER_DESIGN.md`
- **PHASE26-0 리포트**: `docs/PHASE26/PHASE26-0_UNIVERSE_PROVIDER_REPORT.md`
- **Universe Provider**: `common/universe_provider.py`
- **Config Loader**: `common/config_loader.py::load_universe_config()`
- **Engine**: `execution/engine.py`
- **Portfolio Manager**: `execution/portfolio_manager.py`
- **Risk Manager**: `execution/risk_manager.py`

---

**END OF DESIGN DOCUMENT**
