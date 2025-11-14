# PHASE9-1: backtest_raw 모드 진단 및 수정

## 📋 Executive Summary

**목표**: backtest_raw 모드에서 Trades=0건 문제의 원인 분석 및 수정

**상태**: ✅ 완료

**결과**:
- `backtest_clean`: 6건 거래
- `backtest_raw`: 8건 거래 (33% 증가)
- 가드 완화 효과 확인됨

---

## 🔍 Problem Statement

### 초기 증상
- backtest_raw 모드 실행 시 **Trades=0건** 발생
- 신호는 정상 생성: `✅ [SCALPING SIGNAL] LONG 신호 생성!`
- 로그 통계: `진입 거래=0건, 종료 거래=0건`

### 데이터 검증
- CSV 품질: 100/100 (PHASE8-5)
- 캔들 로드: 8,928개 (정상)
- 타임프레임: 5m (일치)

---

## 🕵️ Root Cause Analysis

### 1차 조사: Config 레이어

**backtest_raw.yml 검증**:
```yaml
# 예상: 모든 가드 OFF
enable_vol_spike_filter: false  # ✅
enable_mtf_confirm: false      # ✅
risk.max_consecutive_losses: 99999  # ✅
```

**effective_config.yml 확인**:
```yaml
strategies.scalping:
  timeframe: 5m  # ✅ CLI 타임프레임과 일치
  filters.volume_spike: false  # ✅
  cooldown_candles: 0  # ✅
```

**발견**: Config는 정상 적용됨

---

### 2차 조사: Signal Generator 레이어

**신호 생성 로그**:
```
[SCALPING SIGNAL] LONG 신호 생성! (캔들 #63)
  - Price: 64118.01 | RSI: 63.2 | MACD: 65.3791
🔔 [BTCUSDT] 신호 생성: 1개 - scalping:LONG
✅ [BTCUSDT] 단일 신호 사용: LONG by scalping
```

**검증 결과**:
- `signal_generator.validate_signal()`: PASS
- `enable_vol_spike_filter: false` 확인됨
- 필터 차단 메시지 없음

**발견**: 신호는 정상 생성 및 검증 통과

---

### 3차 조사: Risk Manager 레이어

**초기 가설**: 심볼별 exposure 한도 초과

**로그 증거**:
```
⛔ [scalping] BTCUSDT 리스크 체크 실패 (쿨다운 60초):  
   심볼별 한도 초과: BTCUSDT 19983.63 > 15000.00
```

**계산**:
- Equity: $50,000
- `max_exposure_per_symbol`: 0.3 (30%)
- 한도: $15,000
- 요청: $19,983
- 결과: ❌ 거부

**수정**:
```yaml
# backtest_raw.yml
risk:
  max_exposure_per_symbol: 0.99  # 30% → 99%
```

**검증**: 수정 후에도 여전히 Trades=0건 발생

---

### 4차 조사: Engine 통계 버그

**발견**: `trade_count` 증가 코드 누락

```python
# execution/engine.py (Before)
active_positions[position_id] = {...}
# ❌ trade_count += 1 없음!

# (After - FIXED)
active_positions[position_id] = {...}
trade_count += 1  # ⭐ 추가
```

**검증**: 수정 후에도 여전히 Trades=0건 발생

---

### 🎯 ROOT CAUSE: 기존 포지션 로드

**결정적 증거**:
```
✅ 기존 OPEN 포지션 로드: 13개
  - LEVERUSDT: 1개 (ensemble_1_signals)
  - MEMEFIUSDT: 1개 (ensemble_1_signals)
  ...
```

**코드 분석**:
```python
# execution/engine.py line 168-169
is_backtest_mode = mode in ['backtest', 'backtest_clean']
portfolio = PortfolioManager(config, load_existing=not is_backtest_mode)
```

**문제**:
- `'backtest_raw'`가 리스트에 **없음**
- `is_backtest_mode = False`
- `load_existing = True` → 기존 포지션 로드됨!

**영향**:
```python
# execution/engine.py line 1226-1233
same_direction_positions = [
    (pos_id, pos) for pos_id, pos in list(active_positions.items())
    if pos["symbol"] == candle_symbol and pos["side"] == new_side
]

if same_direction_positions:
    logger.warning(f"⚠️ [중복 진입 방지] {candle_symbol} {new_side} 기존 포지션 {len(same_direction_positions)}개 존재 - 진입 스킵")
    continue  # ⭐ 중복 진입 차단!
```

---

## ✅ Solution

### Fix 1: 기존 포지션 로드 차단 (ROOT CAUSE)

```python
# execution/engine.py
# Before
is_backtest_mode = mode in ['backtest', 'backtest_clean']

# After
is_backtest_mode = mode in ['backtest', 'backtest_clean', 'backtest_raw']
```

### Fix 2: 통계 카운터 추가

```python
# execution/engine.py
active_positions[position_id] = {...}
trade_count += 1  # ⭐ 추가
```

### Fix 3: Risk 거부 시 명시적 처리

```python
# execution/engine.py
if hasattr(risk, "allow_entry") and not risk.allow_entry(candle_symbol, decision.get("side")):
    logger.warning(f"⛔ [{candle_symbol}] Risk 거부: {decision.get('side')}")
    continue  # ⭐ 추가
```

### Fix 4: Config 완화

```yaml
# configs/modes/backtest_raw.yml
risk:
  max_exposure_per_symbol: 0.99  # 심볼당 99%

# 전역 필터 OFF
enable_vol_spike_filter: false
enable_mtf_confirm: false
```

---

## 📊 Verification Results

### Before Fix
- **Trades**: 0건
- **로그**: 기존 포지션 13개 로드
- **차단**: 중복 진입 방지 로직

### After Fix  
- **Trades**: 8건 ✅
- **로그**: 기존 포지션 로드 없음
- **진입**: 정상 거래 생성

### Comparison

| Mode | Period | Trades | Winrate | PF | Max DD |
|------|--------|--------|---------|-----|--------|
| `backtest_clean` | 2024-10-01~31 | 6건 | 33.33% | 0.52 | -0.48% |
| **`backtest_raw`** | 2024-10-01~31 | **8건** | 25.0% | 0.35 | -0.8% |

**거래 증가**: 33% (6건 → 8건)

---

## 🔬 Technical Details

### 1. Config 병합 순서
```
base.yml < modes/backtest_raw.yml < active/current.yml < CLI args
```

### 2. Portfolio Manager 초기화
```python
# load_existing 파라미터
- backtest: False
- backtest_clean: False
- backtest_raw: False  # ⭐ 추가
- paper: True
- live: True
```

### 3. 중복 진입 방지 로직
```python
# 동일 심볼 + 동일 방향 체크
# load_existing=False 시 active_positions={} (empty)
# → 중복 진입 방지 통과
```

---

## 📝 Lessons Learned

### 1. Mode 일관성
- 새 모드 추가 시 **모든 분기문** 확인 필요
- `['backtest', 'backtest_clean']` 패턴 검색 필수

### 2. 격리 검증
- `load_existing` 파라미터 영향력 큼
- 로그에서 "기존 포지션 로드" 메시지 확인 필수

### 3. 통계 버그
- Counter 증가 코드는 critical path에 배치
- 로그와 DB 조회 결과 일치 여부 검증

### 4. 디버깅 순서
1. Config 적용 여부 (effective_config.yml)
2. 신호 생성 여부 (로그)
3. 신호 검증 여부 (필터)
4. Risk 체크 여부 (로그)
5. **격리 상태 여부 (기존 포지션 로드)**
6. 거래 생성 여부 (DB)

---

## 🚀 Next Steps

### PHASE9-0 완료
1. ✅ backtest_raw 모드 정상 작동 확인
2. ⏳ 11월, 12월 백테스트 실행
3. ⏳ PHASE9-0_GUARD_BASELINE.md 작성
4. ⏳ PHASE8_MASTER_PLAN.md 업데이트

### PHASE9-1 다음
1. ⏳ scalping 전략 구조 맵 작성
2. ⏳ 파라미터 튜닝 가능성 분석
3. ⏳ Guard 영향 정량화

---

## 📚 References

- **Config**: `configs/modes/backtest_raw.yml`
- **Engine**: `execution/engine.py` line 168-169, 1226-1233, 1348-1349
- **Results**: `artifacts/backtest_raw/20251114_231421_6t9b/`
- **Comparison**: `artifacts/backtest_clean/20251114_194449_zdut/`

---

*Generated: 2025-11-14 23:17*  
*Author: Windsurf AI Assistant*  
*Status: ✅ ROOT CAUSE IDENTIFIED & FIXED*
