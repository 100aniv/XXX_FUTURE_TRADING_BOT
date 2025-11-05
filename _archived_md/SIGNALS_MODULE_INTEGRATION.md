# 🔧 signals 모듈 통합 완료

**날짜:** 2025-10-20  
**작업:** signals 모듈을 engine.py에 통합하여 기존 기능 최대 활용

---

## 📊 **통합 전/후 비교**

### **Before (통합 전):**
```python
# engine.py - 단순 전략 호출
for strategy_id, strategy_module in strategies.items():
    signal = strategy_module.signal_logic(df, cfg)
    if signal and signal.get('side'):
        signals.append(signal)
```

**문제점:**
- ❌ MTF (멀티타임프레임) 검증 없음
- ❌ 쿨다운 (중복 신호 방지) 없음
- ❌ 거래량 급증 필터 없음
- ❌ Flash Guard (급등락 감지) 미연동
- ❌ 신호 DB 저장 없음

---

### **After (통합 후):**
```python
# engine.py - SignalGenerator 활용
signal_gen = SignalGenerator(config=config, strategy_modules=strategies)

for strategy_id, strategy_module in strategies.items():
    signal = strategy_module.signal_logic(df, cfg)
    
    if signal and signal.get('side'):
        signal['ts'] = candle.get('time', 0)
        
        # ⭐ 신호 검증 (MTF, 쿨다운, 거래량 필터)
        if signal_gen.validate_signal(symbol, signal, df):
            # ⭐ 신호 DB 저장
            save_signal(symbol, signal, config)
            signals.append(signal)
```

**개선점:**
- ✅ MTF 검증 추가
- ✅ 쿨다운 체크
- ✅ 거래량 급증 필터
- ✅ Flash Guard 연동
- ✅ 신호 DB 저장 (monitoring.signals)

---

## 🎯 **통합된 기능**

### **1. SignalGenerator (신호 생성 및 검증)**

#### **MTF (멀티타임프레임) 확인**
```python
def _mtf_confirm(self, symbol: str, side: str) -> bool:
    """상위 타임프레임 추세 확인"""
    # 예: 5m 전략인데 1h가 반대 추세면 거부
    if side == "LONG":
        return htf_regime in ("상승장", "횡보장")
    else:
        return htf_regime in ("하락장", "횡보장")
```

#### **쿨다운 체크**
```python
def _should_alert(self, symbol: str, side: str, ts: int) -> bool:
    """중복 신호 방지"""
    cooldown = timeframe_ms * config["cooldown_candles"]
    if prev_signal_time and ts - prev_signal_time < cooldown:
        return False  # 너무 빨리 다시 신호 → 거부
```

#### **거래량 급증 필터**
```python
def validate_signal(self, symbol: str, signal: dict, df: pd.DataFrame) -> bool:
    """거래량 스파이크 필터"""
    if volume > vol_ma * vol_spike_mult:
        return False  # 거래량 급증 → 신호 보류
```

### **2. signal_storage (신호 DB 저장)**
```python
def save_signal(symbol: str, signal: dict, config: dict) -> bool:
    """monitoring.signals 테이블에 저장"""
    save_signal_to_db(
        signal_id, strategy_id, symbol, timeframe,
        direction, confidence, entry, sl, tp, ...
    )
```

### **3. Flash Guard (급등락 감지)**
```python
# engine.py에서 활용
risk.flash_guard_update(symbol, price, timestamp)

if not risk.flash_guard_allowed(symbol, timestamp):
    logger.warning("🛡 Flash Guard 활성화 - 신호 보류")
    continue
```

---

## 📝 **실밥 리팩토링 주석**

### **engine.py 주석 위치:**

```python
# ⭐⭐⭐ 실밥 리팩토링 시작: 기존 전략 호출 로직 → SignalGenerator 활용 ⭐⭐⭐
# =============================================================================
# [기존 코드 - 주석 처리]
# 전략별 신호 생성
# signals = []
# for strategy_id, strategy_module in strategies.items():
#     try:
#         signal = strategy_module.signal_logic(df, cfg)
#         if signal and signal.get('side'):
#             signals.append(signal)
#     except Exception as e:
#         logger.error(f"❌ [{strategy_id}] 전략 오류: {e}")
# =============================================================================

# ⭐ [새 코드] SignalGenerator 활용 (MTF, 쿨다운, 거래량 필터 포함)
signals = []
for strategy_id, strategy_module in strategies.items():
    signal = strategy_module.signal_logic(df, cfg)
    
    if signal and signal.get('side'):
        # ⭐ 신호 검증 (MTF, 쿨다운, 거래량 필터)
        if signal_gen.validate_signal(symbol, signal, df):
            # ⭐ 신호 DB 저장
            save_signal(symbol, signal, config)
            signals.append(signal)
# ⭐⭐⭐ 실밥 리팩토링 종료 ⭐⭐⭐
```

---

## 🔄 **데이터 플로우**

```
캔들 수신
   ↓
DataFrame 생성 + 지표 계산
   ↓
전략 모듈 호출 (scalping, daytrade, swing...)
   ↓
신호 생성 (entry, sl, tp)
   ↓
⭐ SignalGenerator.validate_signal() ⭐
   ├─ MTF 확인 (상위 타임프레임 추세)
   ├─ 쿨다운 체크 (중복 방지)
   └─ 거래량 필터 (급증 감지)
   ↓
⭐ save_signal() ⭐ (monitoring.signals)
   ↓
⭐ Flash Guard 체크 ⭐ (급등락)
   ↓
Ensemble (신호 통합)
   ↓
Position Sizer (수량 계산)
   ↓
Risk Manager (리스크 체크)
   ↓
Broker 실행
```

---

## 📊 **DB 테이블 활용**

### **monitoring.signals (신호 기록)**
```sql
INSERT INTO monitoring.signals (
    signal_id, strategy_id, symbol, timeframe,
    direction, confidence, entry_price, sl_price, tp_price,
    atr, leverage, features, candle_closed_at
) VALUES (...);
```

**활용:**
- 전략별 신호 발생 빈도 분석
- 신호 품질 (confidence) 추적
- 백테스트 vs 실거래 비교

### **trading.trades (실제 거래)**
```sql
INSERT INTO trading.trades (
    trade_id, symbol, side, entry_price, quantity,
    sl_price, tp_price, strategy_id, leverage, status
) VALUES (...);
```

---

## ⚙️ **설정 파라미터**

### **.env 설정:**
```bash
# MTF 검증
ENABLE_MTF_CONFIRM=true
REQUIRE_HTF_ALIGNED=true
HTF=1h  # 상위 타임프레임

# 쿨다운
COOLDOWN_CANDLES=3  # 타임프레임 * 3

# 거래량 필터
ENABLE_VOL_SPIKE_FILTER=true
VOL_SPIKE_MULT=2.5  # 거래량 > MA * 2.5 → 필터

# Flash Guard
ENABLE_FLASH_GUARD=true
FLASH_WINDOW_SEC=60  # 60초 윈도우
FLASH_PCT=0.03  # 3% 변동 시 일시 중단
FLASH_PAUSE_CANDLES=3  # 3개 캔들 대기
```

---

## 🎯 **효과**

### **거래 품질 향상:**
1. **MTF 정렬** - 상위 추세와 일치하는 신호만 실행
2. **중복 방지** - 쿨다운으로 과도한 진입 차단
3. **변동성 대응** - 급등락/거래량 급증 시 보류

### **데이터 추적:**
- 모든 신호 DB 저장 → 분석 가능
- 전략별 성과 추적
- 실거래 vs 신호 비교

### **리스크 관리:**
- Flash Guard로 급변 상황 대응
- Risk Manager와 통합
- 일일 손실 한도, 포지션 제한

---

## 📚 **관련 파일**

### **signals 모듈:**
- `signals/signal_generator.py` - SignalGenerator 클래스
- `signals/signal_storage.py` - save_signal() 함수
- `signals/__init__.py` - 모듈 export

### **통합 위치:**
- `execution/engine.py` - 메인 트레이딩 루프

### **설정:**
- `.env` - 환경 변수 설정
- `strategy_params.yaml` - 전략별 파라미터

---

## 🚀 **다음 단계**

### **C. 전략 필터 완화 (거래 빈도 증가)**
- 현재: 1건/일
- 목표: 30-50건/일
- 방법: 필터 조건 완화, 타임프레임 추가 (1m, 3m)

### **D. 불필요 모듈 정리**
- ✅ signals/ - 통합 완료
- ⬜ execution/executors/ - 삭제 예정 (adapters로 대체)

### **Docker 재배포**
- ⬜ 페이퍼 모드 재빌드
- ⬜ 라이브 모드 테스트

---

## 🎉 **완료!**

**signals 모듈이 engine.py에 완전 통합되었습니다!**

- ✅ MTF 검증
- ✅ 쿨다운 체크
- ✅ 거래량 필터
- ✅ Flash Guard
- ✅ 신호 DB 저장
- ✅ 실밥 리팩토링 주석

**기존 코드를 최대한 활용하면서 기능을 강화했습니다!**
