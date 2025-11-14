# SCALPING 전략 구조 맵 (PHASE9-2)

## 📋 Summary

**목적**: scalping 전략의 전체 구조를 레이어별로 분석하고 파라미터 제어 가능성을 평가

---

## 🔄 신호 생성 플로우

```
DATA FEED (OHLCV + Indicators)
   ↓
STRATEGY LOGIC (scalping.py)
   - BB Bounce, MACD Cross, EMA 정렬, RSI, Volume
   → signal dict 생성
   ↓
SIGNAL VALIDATION (signal_generator.py)
   - Volume Spike, MTF, Regime, Session 필터
   → True/False
   ↓
RISK MANAGER (risk_manager.py)
   - Daily Loss, Consecutive, Flash Guard, DD Cutoff
   - Position Limit, Per-Symbol/Total Exposure
   → (True/False, reason)
   ↓
PORTFOLIO MANAGER (portfolio_manager.py)
   - Max Strategy Positions, Symbol Cooldown
   - Duplicate Entry Prevention
   → (True/False, reason)
   ↓
POSITION SIZER (position_sizer.py)
   - RPT, Context Scaling, Quality Weight
   - Position Value Limit, Liquidation Buffer
   → (qty, metadata)
   ↓
BROKER (sim_broker.py)
   - Fill Policy, Slippage, Fees
   → fill dict
   ↓
POSITION TRACKING (position_tracker.py)
   - TP Manager, SL Trailing, Time Exit
   → active_positions 업데이트
```

---

## 📊 파라미터 분류

### ✅ Config 제어 가능 (60개, 95%)

| 레이어 | 항목 수 | 주요 파라미터 |
|--------|---------|---------------|
| Strategy | 12 | BB임계값, RSI범위, Volume배수, ATR배수, RR |
| Signal Generator | 6 | Vol Spike, MTF, Regime, Session 필터 |
| Risk Manager | 11 | Daily Loss, Consecutive, DD, Flash, Exposure |
| Portfolio | 4 | Max Positions, Exposure, Cooldown |
| Position Sizer | 15 | RPT, Quality Weight, Context Scaling, Liq Buffer |
| Broker | 4 | Fill Policy, Fees, Slippage |
| Tracker | 5 | TP Levels, Trailing, BE, Time Exit |
| Engine | 3 | Reject Cooldown, Min Bars |

### ⚠️ 하드코딩 요소 (9개, 5%)

| 위치 | 값 | 영향 | 우선순위 |
|------|-----|------|----------|
| `scalping.py:165` | `vol_regime_mult` (1.2/0.9) | SL 크기 | **HIGH** |
| `tp_manager.py:76` | `vol_regime_mult` (1.2/0.9) | TP 거리 | **HIGH** |
| `engine.py:1231` | `allow_duplicate_entry=False` | 중복 진입 | **CRITICAL** |
| `position_sizer.py:147` | `epsilon=1.0` | 포지션 허용 오차 | LOW |
| `position_sizer.py:140` | `min_qty=0.001` | 최소 수량 | LOW |
| `position_sizer.py:180` | `quality_slope=1.2` | 품질 가중치 | MED |
| `risk_manager.py:237` | `flash_buffer=2` | Flash 버퍼 | LOW |
| `engine.py:69` | `websocket_wait=2s` | WS 대기 | LOW |
| `engine.py:155` | `ttl_buffer=1.05` | TTL 버퍼 | LOW |

---

## 🎯 SCALPING 신호 조건

### LONG (5가지 AND)
1. BB Bounce: `close > bb_lower*1.003 AND prev<=bb_lower*1.008 AND close>prev`
2. MACD: 상향 크로스 OR 상승 유지
3. EMA: fast > mid > slow (3선 정렬)
4. RSI: 30 < rsi < 70
5. Volume: `volume > vol_ma * 1.5`

### SHORT (5가지 AND)
1. BB Bounce: `close < bb_upper*0.997 AND prev>=bb_upper*0.992 AND close<prev`
2. MACD: 하향 크로스 OR 하락 유지
3. EMA: fast < mid < slow (3선 역정렬)
4. RSI: 30 < rsi < 70
5. Volume: `volume > vol_ma * 1.5`

---

## 🚧 개선 우선순위

### CRITICAL (즉시)
1. **중복 진입 방지**: `allow_duplicate_entry` config 추가 (현재 하드코딩)

### HIGH (PHASE9-3)
1. **변동성 레짐 배수**: `vol_regime_mult_high/low` config 추가 (SL/TP 조정)
2. **품질 가중치 계산**: `quality_weight_slope` config 추가

### MED (PHASE9-4)
1. **포지션 가치 허용 오차**: `position_value_epsilon` config 추가
2. **Flash Guard 버퍼 크기**: `flash_buffer_size` config 추가

### LOW (PHASE9-5)
1. **거래소 최소 수량**: `min_qty_exchange` config 추가
2. **WebSocket 대기 시간**: `websocket_stabilize_sec` config 추가
3. **Redis TTL 버퍼**: `redis_ttl_buffer_pct` config 추가

---

*Generated: PHASE9-2*  
*Status: ✅ 전략 구조 분석 완료*
