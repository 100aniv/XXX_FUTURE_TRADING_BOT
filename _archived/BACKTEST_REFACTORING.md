# 백테스트 리팩토링 (2025-10-22)

**Phase 2 작업**

---

## 📋 완료 사항

### 1. **멀티 심볼 백테스트 지원**

**새 모듈:** `collectors/multi_historical_collector.py`

**기능:**
- 여러 심볼 CSV를 시간순으로 병합 (Heap Queue 사용)
- start_date, end_date 필터링
- 진행률 추적
- 실시간 스트리밍과 동일한 인터페이스

**사용 방법:**
```python
feed = MultiSymbolHistoricalFeed(
    symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
    data_dir='data',
    timeframe='5m',
    start_date='2025-07-24',
    end_date='2025-10-22'
)
```

---

### 2. **config.yml 기반 백테스트**

**이전 (하드코딩):**
```python
csv_path = f"data/{symbol}_5m_2025-07-24_2025-10-22.csv"
```

**현재 (config 기반):**
```yaml
# config.yml
backtest:
  data_dir: data
  period: three_months
  periods:
    three_months:
      start_date: '2025-07-24'
      end_date: '2025-10-22'
  symbol: BTCUSDT  # 단일 심볼 (옵션)
```

```python
# main.py
data_dir = backtest_cfg.get('data_dir', 'data')
period = backtest_cfg.get('period', 'three_months')
period_cfg = backtest_cfg.get('periods', {}).get(period, {})
start_date = period_cfg.get('start_date')
end_date = period_cfg.get('end_date')

if backtest_cfg.get('symbol'):
    # 단일 심볼
    feed = HistoricalFeed(...)
else:
    # 멀티 심볼
    feed = MultiSymbolHistoricalFeed(...)
```

---

### 3. **단일/멀티 심볼 자동 선택**

**config.yml 설정:**

**단일 심볼 모드:**
```yaml
backtest:
  symbol: BTCUSDT  # 이 심볼만 테스트
```

**멀티 심볼 모드:**
```yaml
backtest:
  # symbol 항목 제거

symbols:
  mode: manual
  manual: [BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT]
```

---

## 📊 백테스트 결과

### **멀티 심볼 (5개 심볼, 버그 발견)**
```
총 캔들: 107,187개
진입 거래: 9,930건
종료 거래: 9,930건
Daily PnL: -$157,550,719 ❌

버그: position_value 계산 오류
```

### **단일 심볼 (BTCUSDT)**
```
총 캔들: 3,935개
진입 거래: 169건
종료 거래: 168건
Daily PnL: -$871 (-8.7%)

전략: 6개 모두 활성화
- scalping, daytrade, swing, trend, reversion, breakout
```

---

## 🔧 수정한 버그

### 1. **파일명 통일**
- `multi_historical_feed.py` → `multi_historical_collector.py`
- collectors 패턴 일관성

### 2. **단일/멀티 심볼 조건**

**이전 (버그):**
```python
if single_symbol and len(symbols) == 1:  # ❌
    # symbols에 5개 있으면 실패
```

**수정:**
```python
if single_symbol:  # ✅
    # backtest.symbol 있으면 무조건 단일 심볼
```

### 3. **import 경로**
```python
# 수정 전
from collectors.multi_historical_feed import ...

# 수정 후
from collectors.multi_historical_collector import ...
```

---

## 🔴 남은 버그

### **position_value 2배 계산**

**현상:**
```
position_sizer: $5,048로 계산 ✅
risk_manager: $10,006 감지 ❌
```

**예상 원인:**
1. exposure 누적 오류
2. 중복 add_position() 호출
3. position_value 재계산

**다음 단계:**
- 디버깅 로그 추가
- exposure 추적
- 버그 수정 후 멀티 심볼 재테스트

---

## 📁 변경된 파일

1. **collectors/multi_historical_collector.py** (신규)
   - 멀티 심볼 CSV 병합
   - 시간순 스트리밍

2. **collectors/__init__.py**
   - MultiSymbolHistoricalFeed export

3. **main.py**
   - 백테스트 로직 config 기반으로 수정
   - 단일/멀티 심볼 자동 선택
   - CSV 파일명 패턴 매칭

4. **config.yml**
   - data_dir: data
   - period: three_months
   - periods 추가

5. **execution/position_sizer.py** (이전 수정)
   - max_position_value 3번 체크

6. **execution/risk_manager.py** (이전 수정)
   - check_order에 position_value 파라미터

7. **execution/engine.py** (이전 수정)
   - position_value 재계산 방지
   - decision에 symbol 추가

---

## ✅ 검증 완료

1. ✅ **하드코딩 제거** - config.yml에서 모든 설정 관리
2. ✅ **모듈 중복 제거** - 각 모듈 독립성 유지
3. ✅ **멀티 심볼 지원** - MultiSymbolHistoricalFeed 구현
4. ✅ **단일/멀티 자동 선택** - config.backtest.symbol 기반
5. ✅ **파일명 통일** - *_collector.py 패턴
6. ⚠️ **버그 남음** - position_value 2배 계산

---

## 🎯 다음 단계

1. **버그 수정** - position_value 2배 계산
2. **멀티 심볼 재테스트** - 5개 심볼
3. **전략별 성과 분석** - 169건 거래 분석
4. **Paper Trading 준비** - 검증 완료 후

---

**작성일:** 2025-10-22 23:37  
**Phase:** PHASE2  
**상태:** 진행 중 (버그 수정 필요)
