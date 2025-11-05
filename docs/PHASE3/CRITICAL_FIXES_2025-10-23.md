# 긴급 수정 사항 (Critical Fixes)

**작성일**: 2025-10-23  
**버전**: v1.0  
**상태**: ✅ 적용 완료

---

## 🚨 발견된 치명적 문제 3가지

### **문제 1: 자본 0 이하에서도 거래 계속**
**증상**: 
```
💰 $0 → $-802
💰 $0 → $-576
💰 $0 → $-257
```
- 자본이 음수가 되어도 거래 계속 진행
- MDD -1,568% 폭발

**원인**: `RiskManager.check_order()`에 자본 체크 누락

**해결**: 
```python
# execution/risk_manager.py Line 156-158
if self.equity <= 0:
    return False, f"자본 소진: ${self.equity:.2f}"
```

---

### **문제 2: 백테스트 모드 연속 손실 제한 미작동**
**증상**:
```
연속 손실: 15/4회 (목표: 4회)
연속 손실: 23회
```
- 백테스트에서 경고만 출력, 거래 차단 안 됨
- 라이브와 백테스트 결과 괴리

**원인**: 
```python
# 기존 코드 - 백테스트 제외
if self.in_cooldown and self.mode != 'backtest':
    return False, "연속 손실 쿨다운"
```

**해결**:
```python
# execution/risk_manager.py Line 160-164
if self.in_cooldown:
    if self.mode == 'backtest':
        logger.warning(f"🛑 [백테스트] 연속 손실 {self.consecutive_losses}회 → 거래 차단")
    return False, f"연속 손실 쿨다운 ({self.consecutive_losses}회)"
```

---

### **문제 3: Scalping 전략 과도한 신호 생성**
**증상**:
```
총 거래: 388,926건/년 (일평균 1,065건)
목표: 30~50건/일 → 실제: 21배 초과
```

**원인**: 조건이 너무 느슨함
- RSI 범위: 20~80 (너무 넓음)
- BB 반등 허용치: 1.5% (과대)
- 거래량: 단순 평균 이상 (약함)

**해결** (성공 패턴 적용):
```python
# strategies/scalping.py

# 1. RSI 범위 축소 (80 → 70)
rsi_ok_long = 30 < last["rsi"] < 70

# 2. EMA 3선 정렬 필수
ema_trend_long = (last["ema_fast"] > last["ema_mid"] and 
                  last["ema_mid"] > last["ema_slow"])

# 3. BB 반등 허용치 축소 (1.5% → 0.8%)
bb_bounce_long = (
    last["close"] > last["bb_lower"] * 1.003 and
    prev["close"] <= prev["bb_lower"] * 1.008 and
    last["close"] > prev["close"]
)

# 4. 거래량 임계값 상향 (1.0x → 1.5x)
vol_ok = last["volume"] > last["vol_ma"] * 1.5

# 5. MACD 크로스 추가
macd_cross_up = (last["macd"] > last["macd_signal"] and 
                 prev["macd"] <= prev["macd_signal"])

# 6. 5가지 조건 모두 충족
pullback_long = (bb_bounce_long and (macd_cross_up or macd_up) and 
                 ema_trend_long and rsi_ok_long and vol_ok)
```

---

## 📊 예상 효과

### Before (수정 전)
- ❌ 자본 0 이하 거래: 계속 진행
- ❌ 연속 손실 제한: 백테스트 미적용
- ❌ 거래 빈도: 1,065건/일 (21배 초과)

### After (수정 후)
- ✅ 자본 0 이하 거래: 즉시 차단
- ✅ 연속 손실 제한: 모든 모드 적용
- ✅ 거래 빈도: 30~50건/일 예상 (적정)

---

## 🔗 관련 파일

### 수정된 파일
1. `execution/risk_manager.py`
   - Line 156-158: 자본 체크 추가
   - Line 160-164: 백테스트 연속 손실 적용

2. `strategies/scalping.py`
   - Line 50-95: 조건 강화 (5가지)

### 새로 작성된 문서
1. `docs/PHASE3/RUNBOOK_CHECKLIST.md`
2. `docs/PHASE3/CRITICAL_FIXES_2025-10-23.md` (본 문서)

---

## ✅ 다음 단계

1. ✅ 문제 수정 완료
2. ⏭ 기존 데이터 삭제 (2025년 데이터)
3. ⏭ 새 데이터 다운로드 (2024년 1년치)
4. ⏭ 개선된 백테스트 재실행
5. ⏭ TEST_CHECKLIST.md 업데이트

---

**Last Updated**: 2025-10-23  
**Status**: ✅ 수정 완료, 테스트 대기
