# PHASE29-3: 전략 재설계 TODO

## 📋 Document Control

| 항목 | 내용 |
|------|------|
| **PHASE** | PHASE29-3 |
| **작성일** | 2025-12-10 |
| **상태** | ✅ **V3 폐기 완료** → 🔵 **재설계 대기** |
| **이전 PHASE** | PHASE29-2C-R (V3 전략 FAIL) |
| **다음 PHASE** | PHASE29-3.1 (새로운 전략 설계) |

---

## 🎯 요약

**PHASE29-3 완료 사항**: btc5m_baseline_v3 전략 공식 폐기 (DEPRECATED)

**폐기 근거**:
- 1개월 백테스트: 17건/80-240건 (달성률 7.1~21.3%)
- AND 로직 과잉 결합 + 엄격한 Threshold → 교집합 극소
- Scenario A+ (최대 완화)로도 목표 미달
- Config 파라미터 전달 버그와 무관

**다음 목표**: 새로운 전략 설계로 진입 (PHASE29-3.1)

---

## ❌ V3 전략 실패 원인 분석

### 1. 구조적 신호 부족

**AND 로직 과잉 결합**:
```
V3 진입 로직 (Trend Mode):
- RSI < 45 AND
- Price < BB Lower AND
- EMA 20 < Price < EMA 5 AND
- DI+ > DI-

→ 4개 조건의 교집합이 극소
→ Trend 캔들 1,620개 중 진입 0건
```

**Range Mode 교집합 극소**:
```
V3 진입 로직 (Range Mode):
- RSI < 40 AND
- Price < BB Lower AND
- ADX < 20

→ 3개 조건 중 최소 1개만 충족 (Scenario A+)
→ Range 캔들 585개 중 진입 1건
```

### 2. 완화 Scenario 결과

| Scenario | Range Min Cond | RSI Threshold | 1주 거래 | 1개월 거래 | 판정 |
|---------|---------------|--------------|--------|----------|------|
| Baseline | 3/3 | 30/70 | 1건 | 2건 | ❌ FAIL |
| A | 2/3 | 35/65 | 13건 | N/A | ❌ 목표 미달 |
| A+ | 1/3 | 40/60 | 20건 | 17건 | ❌ 1주 PASS, 1개월 FAIL |

**Scenario A+ (최대 완화) 결론**:
- 1주일: 20건 (목표 달성)
- 1개월: 17건 (목표 78.8~92.9% 부족)
- 1주일 → 1개월 선형 확장 실패

### 3. V2 대비 차이

| 지표 | V2 | V3 | 변화 |
|------|----|----|------|
| 진입 로직 | OR (RSI OR BB OR Volume) | AND (RSI AND BB AND EMA/ADX) | ❌ 99% 신호 감소 |
| Threshold | Relaxed | Strict | ❌ 신호 부족 |
| TP/SL | 단일 TP | Multi-TP | ✅ 구조 개선 |
| Regime 분리 | 약함 | 명확 | ✅ Regime Detection 정상 |

**핵심 문제**: V2의 **OR 기반 진입**을 버리고 **AND 기반**으로 갔으나, AND 조건이 과잉 결합됨

---

## 🔧 다음 전략 설계 원칙

### 필수 조건 (Non-Negotiable)

1. **신호 빈도 최소 기준**:
   - 1주일: 20~60건
   - 1개월: 80~240건
   - **이 조건을 충족하지 못하면 전략 폐기**

2. **성능 목표**:
   - Win Rate ≥ 45%
   - Sharpe Ratio > 0
   - Max DD ≤ 15% (1개월)
   - Profit Factor ≥ 1.2

3. **인프라 호환성**:
   - 단일 엔진 구조 (run_v2) 유지
   - FlowGuardian/RiskManager 호환
   - Multi-Symbol 확장 가능
   - Tuning Pipeline (Random → Bayesian → Local Grid) 활용

### 설계 고려사항

#### Option 1: OR 기반 + 조건 가중치 조합 ✅ **권장**

**개념**:
```python
# V3 실패: AND 과잉
if RSI < 40 AND Price < BB_Lower AND ADX < 20:
    signal = LONG

# V4 제안: OR 기반 + 점수 합산
score = 0
if RSI < 40: score += 3
if Price < BB_Lower: score += 2
if ADX < 20: score += 1
if Momentum < 0: score += 1

if score >= 4:  # Threshold 조정 가능
    signal = LONG
```

**장점**:
- 신호 빈도 조절 가능 (Threshold 조정)
- 조건별 가중치로 중요도 표현
- Tuning 파라미터 명확 (각 가중치, Threshold)

**단점**:
- 조건 수가 많아지면 파라미터 과잉

#### Option 2: V2 복귀 + Multi-TP 추가 ⚠️ **차선**

**개념**:
```python
# V2 OR 로직 그대로
if RSI < 30 OR (Price < BB_Lower AND Volume > MA):
    signal = LONG

# V3의 Multi-TP 구조만 가져옴
tp1 = entry + 1.2 * ATR  # 60% 청산
tp2 = entry + 3.0 * ATR  # 40% 청산
```

**장점**:
- V2는 신호 빈도 충분 (검증됨)
- Multi-TP로 R:R 개선 가능

**단점**:
- V2의 Win Rate < 45% 문제 미해결
- Regime 분리 없음

#### Option 3: Hybrid (Regime별 OR + Multi-TP) ✅ **최적**

**개념**:
```python
# Trend Mode: OR 기반 Pullback
if Trend == BULL:
    score = 0
    if RSI < rsi_threshold: score += 3
    if Price < BB_Lower: score += 2
    if EMA_20 < Price < EMA_5: score += 2
    if DI+ > DI-: score += 1
    
    if score >= 3:
        signal = LONG, tp=[1.2*ATR, 3.0*ATR], sl=2.0*ATR

# Range Mode: OR 기반 Mean Reversion
if Trend == RANGE:
    score = 0
    if RSI < rsi_range_threshold: score += 3
    if Price < BB_Lower: score += 2
    if ADX < 20: score += 1
    
    if score >= 2:
        signal = LONG, tp=[1.0*ATR, 2.0*ATR], sl=1.5*ATR
```

**장점**:
- Regime 분리 유지 (V3의 장점)
- OR 기반 신호 빈도 확보
- 가중치로 조건 중요도 표현
- Multi-TP 구조 유지

**단점**:
- 파라미터 수 증가 (Trend/Range 각각)

---

## 📊 Regime Detection 유지 (V3의 장점)

V3 실패 원인은 **진입 로직**이지, **Regime Detection**은 정상 작동했다.

**PHASE29-2A 결과**:
- Trend: 74.5%, Range: 25.5% ✅ 정상
- ADX/DI+/DI- 기반 탐지 정확

**유지할 구조**:
- `detect_regime(df)` 함수
- Trend vs Range 모드 분리
- Regime별 SL/TP/홀드 타임 분리

---

## 🎯 다음 단계 (PHASE29-3.1)

### Task 1: 새로운 전략 설계 문서 작성

**문서**: `docs/PHASE29/PHASE29_3_1_NEW_STRATEGY_DESIGN.md`

**내용**:
1. Hybrid Approach (Regime별 OR + 가중치 점수) 설계
2. 파라미터 정의 및 기본값
3. 예상 신호 빈도 계산 (백테스트 없이 로직 분석)
4. Tuning ParamSpace 정의

### Task 2: 스켈레톤 코드 구현

**파일**: `strategies/btc5m_baseline_v4.py` (또는 다른 이름)

**구조**:
```python
def signal_logic(df, config):
    # Regime Detection (V3 재사용)
    regime = detect_regime(df)
    
    # Trend Mode: OR 기반 점수 합산
    if regime == TREND:
        score = _calculate_trend_score(df, config)
        if score >= config['trend_min_score']:
            return generate_signal(...)
    
    # Range Mode: OR 기반 점수 합산
    elif regime == RANGE:
        score = _calculate_range_score(df, config)
        if score >= config['range_min_score']:
            return generate_signal(...)
```

### Task 3: 1일 스모크 백테스트

**목표**:
- 신호 발생 확인 (최소 1~5건)
- ERROR 0건
- Regime 분리 정상 작동

### Task 4: 1주일 백테스트

**목표**:
- 거래 건수: 20~60건 ✅
- Guard 차단율 < 50%
- 로그 분석으로 신호 빈도 검증

**Gate**: 1주일 목표 미달 시 **즉시 설계 재검토**

### Task 5: 1개월 백테스트

**목표**:
- 거래 건수: 80~240건
- Win Rate ≥ 45%
- Max DD ≤ 15%

**Gate**: PASS → PHASE29-4 (튜닝)

---

## 🚫 금지 사항

### 절대 하지 말 것

1. **AND 로직 과잉 결합 금지**:
   - 3개 이상 AND는 신중히 검토
   - 교집합 크기를 백테스트 없이 로직으로 추정

2. **엔진/인프라 수정 금지**:
   - `execution/engine.py` 수정 금지
   - SSOT (Signal/Portfolio/Risk) 수정 금지
   - 전략 레벨에서만 해결

3. **하드코딩 금지**:
   - 모든 파라미터는 Config로 관리
   - "이 값이 좋을 것 같다" → Config + Tuning

4. **중간 WIP 커밋 금지**:
   - 테스트 PASS + 문서화 완료 후 커밋

---

## 📁 참고 문서

- `docs/PHASE29/PHASE29_0_BTC5M_BASELINE_V2_STRATEGY_REDESIGN_KR.md` (V3 설계 배경)
- `docs/PHASE29/PHASE29_2A_BTC5M_BASELINE_V3_DEBUG_KR.md` (V3 병목 분석)
- `docs/PHASE29/PHASE29_2B_BTC5M_BASELINE_V3_SCENARIO_A_KR.md` (Scenario A+ 결과)
- `docs/PHASE29/PHASE29_2C_BTC5M_BASELINE_V3_MONTH_BACKTEST_KR.md` (V3 최종 판정)
- `strategies/btc5m_baseline_v3.py` (폐기된 V3 코드 - 참고용)

---

**작성 완료**: 2025-12-10  
**다음 작업**: PHASE29-3.1 새로운 전략 설계 시작
