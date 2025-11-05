# Cycle 2 실행 계획

**시작일**: 2025-10-23  
**목표**: TEST_SCENARIO.md 원칙 준수 + 게이트 통과  
**전략**: REVERSION (성공 패턴 기반)

---

## 🎯 목표

### 최소 목표 (게이트)
- **OOS Expectancy**: ≥ 0.10 R/trade
- **PF**: ≥ 1.3
- **MDD**: ≤ -20%
- **승률**: ≥ 40%
- **레짐별**: 모두 Expectancy ≥ 0

### 최적 목표
- **OOS Expectancy**: ≥ 0.15 R/trade
- **PF**: ≥ 1.5
- **MDD**: ≤ -15%
- **승률**: ≥ 60%
- **거래 빈도**: 10~30건/9개월

---

## 📅 단계별 일정

### Week 1: 준비 (Day 1-2)
**목표**: 데이터 분리, 전략 재설계

#### Day 1 (2025-10-23)
- [x] Cycle 1 종료 문서화
- [ ] OOS 분리 스크립트 작성
- [ ] Train/OOS CSV 생성
- [ ] 레짐 태깅 도구 준비

#### Day 2
- [ ] REVERSION 전략 재설계
- [ ] 단위 테스트 (1주일 데이터)
- [ ] config.yml 백업 및 설정 조정

### Week 1: A-2 Exits 튜닝 (Day 3-4)
**목표**: 손익비 구조 확립

#### Day 3
- [ ] Exits 파라미터 그리드 정의
- [ ] LHS 20 샘플 생성
- [ ] Train 백테스트 (9개월)

#### Day 4
- [ ] OOS 검증 (3개월)
- [ ] 레짐별 성과 분석
- [ ] 최적 Exits 선택

### Week 2: A-3 Entries 튜닝 (Day 5-6)
**목표**: 허수 제거, 승률 개선

#### Day 5
- [ ] Exits 고정
- [ ] Entries 파라미터 그리드
- [ ] Train 백테스트

#### Day 6
- [ ] OOS 검증
- [ ] 레짐별 성과 분석
- [ ] 프리셋 확정

### Week 2: A-4 검증 (Day 7)
**목표**: 최종 확인

- [ ] 전체 OOS 재검증
- [ ] 게이트 기준 확인
- [ ] 문서 업데이트
- [ ] Cycle 2 종료

---

## 📂 필요한 스크립트

### 1. `scripts/split_train_oos.py`
```python
# OOS 분리
# Input: BTCUSDT_5m_2024-01-01_2024-12-31.csv
# Output:
#   - BTCUSDT_5m_2024-01-01_2024-09-30_TRAIN.csv
#   - BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv
```

### 2. `scripts/tag_regime.py`
```python
# 레짐 태깅
# 구간: 트렌드/레인지/고변동/저변동
# Output: regime_tags.csv
```

### 3. `scripts/run_lhs_exits.py`
```python
# LHS 샘플링 + Exits 그리드 테스트
# Params: stop.k, tp1_rr, tp2_rr, trailing.k
# Output: exits_results.csv
```

### 4. `scripts/run_lhs_entries.py`
```python
# Entries 그리드 테스트 (Exits 고정)
# Params: rsi_threshold, bb_touch_pct, volume_spike
# Output: entries_results.csv
```

---

## 🔧 전략 재설계 상세

### REVERSION v2 (성공 패턴 기반)

```python
# strategies/reversion.py

def signal_logic(df: pd.DataFrame, config: dict):
    """
    REVERSION v2: 과매도 반등 포착
    
    성공 패턴 (100% 승률, 12건):
    - RSI < 30 + BB 하단 + EMA 역배열
    """
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 기본 정보
    price = float(last["close"])
    atr = float(last["atr"])
    
    # === 진입 조건 ===
    
    # 1) RSI 과매도 (강)
    rsi_oversold = last["rsi"] < config.get('rsi_threshold', 30)
    
    # 2) BB 하단 터치
    bb_touch = last["close"] <= last["bb_lower"] * config.get('bb_touch_pct', 1.005)
    
    # 3) EMA 역배열 (하락 추세)
    ema_downtrend = last["ema_fast"] < last["ema_slow"]
    
    # 4) 거래량 (선택적)
    volume_ok = True
    if config.get('require_volume_spike', False):
        volume_ok = last["volume"] > last["vol_ma"] * 1.2
    
    # 5) 반등 시작 확인 (선택적)
    bounce_start = last["close"] > prev["close"]  # 상승 캔들
    
    # === 신호 생성 ===
    
    # LONG: 과매도 + BB 하단 + 하락 추세 (반등 기대)
    signal_long = (rsi_oversold and bb_touch and ema_downtrend and 
                   volume_ok and bounce_start)
    
    side = None
    if signal_long:
        side = "LONG"
        
        # 가격 레벨 계산
        entry, sl, tp = price_levels(
            side, price, atr,
            config.get("rr", 2.5),
            config.get("atr_mult_sl", 1.5)
        )
        
        return {
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "confidence": 0.85,  # 성공 패턴 기반
            "atr": atr,
            "reason": ["RSI 과매도", "BB 하단 터치", "반등 시작"]
        }
    
    return {"side": None}
```

### config.yml 설정

```yaml
strategies:
  reversion:
    enabled: true
    timeframe: 5m
    rr: 2.5
    atr_mult_sl: 1.5
    risk_per_trade: 0.01
    
    # Entries 파라미터 (튜닝 대상)
    rsi_threshold: 30  # LHS: [25, 30, 35]
    bb_touch_pct: 1.005  # LHS: [1.000, 1.005, 1.010]
    require_volume_spike: false  # LHS: [true, false]
    
    # Exits는 exits 섹션에서 관리
    cooldown_candles: 10
    
    filters:
      regime: false  # 레짐 무시 (단순화)
      volume_spike: false
      mtf_confirm: false
```

---

## 📋 체크리스트

### 준비 단계
- [x] Cycle 1 문서화 완료
- [ ] OOS 분리 스크립트 작성
- [ ] 레짐 태깅 도구 작성
- [ ] REVERSION v2 구현
- [ ] config.yml 백업
- [ ] TEST_CHECKLIST 초기화 (Cycle 2)

### 실행 단계
- [ ] A-2 Exits 튜닝 (LHS 20 샘플)
- [ ] A-3 Entries 튜닝 (Exits 고정)
- [ ] OOS 검증
- [ ] 레짐별 성과 분석
- [ ] 게이트 기준 확인

### 문서화
- [ ] 실험 로그 기록 (TEST_CHECKLIST)
- [ ] 레짐별 성과 표 작성
- [ ] Cycle 2 종료 보고서
- [ ] docs/PHASE3 업데이트

---

## ⚠️ 주의사항

1. **OOS 오염 금지**
   - OOS 데이터로 파라미터 튜닝 절대 금지
   - OOS는 최종 검증만 사용

2. **단일 변경 원칙**
   - Exits 튜닝 시 Entries 고정
   - Entries 튜닝 시 Exits 고정

3. **레짐별 확인**
   - 모든 레짐에서 Expectancy ≥ 0 확인
   - 특정 레짐 과적합 경계

4. **게이트 기준 엄수**
   - OOS 기준 미달 시 다음 단계 진행 금지
   - Train 성과만 보고 판단 금지

---

**상태**: 준비 중  
**다음 작업**: OOS 분리 스크립트 작성  
**Last Updated**: 2025-10-23
