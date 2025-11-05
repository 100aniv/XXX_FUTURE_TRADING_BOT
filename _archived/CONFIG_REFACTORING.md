# Config 기반 백테스트 리팩토링

**날짜:** 2025-10-22  
**목적:** 하드코딩 제거, config.yml 중심 설계 완성

---

## 📋 변경 사항

### **1. main.py 백테스트 부분**

#### ❌ 이전 (하드코딩)
```python
csv_path = f"data/{symbol}_5m_2025-07-24_2025-10-22.csv"
feed = HistoricalFeed(csv_path, symbol=symbol, timeframe=timeframe)
```

**문제점:**
- 데이터 디렉토리 하드코딩: `"data"`
- 타임프레임 하드코딩: `"5m"`
- 날짜 하드코딩: `"2025-07-24_2025-10-22"`
- 단일 심볼만 지원

#### ✅ 수정 후 (config.yml 기반)
```python
# 백테스트 설정 (config.yml 기반, 하드코딩 없음)
backtest_cfg = CFG.get('backtest', {})
data_dir = backtest_cfg.get('data_dir', 'data')

# 기간 설정
period = backtest_cfg.get('period', 'three_months')
period_cfg = backtest_cfg.get('periods', {}).get(period, {})
start_date = period_cfg.get('start_date')
end_date = period_cfg.get('end_date')

# 단일/멀티 심볼 자동 선택
if single_symbol and len(symbols) == 1:
    # HistoricalFeed (단일)
else:
    # MultiSymbolHistoricalFeed (멀티)
```

**개선점:**
- ✅ 모든 설정 config.yml에서 관리
- ✅ 하드코딩 완전 제거
- ✅ 단일/멀티 심볼 모두 지원
- ✅ CSV 파일명 자동 감지 (패턴 매칭)

---

### **2. config.yml**

#### 추가된 설정
```yaml
backtest:
  data_dir: data              # 데이터 디렉토리
  period: three_months        # 사용할 기간
  periods:
    three_months:
      start_date: '2025-07-24'
      end_date: '2025-10-22'
    one_year: ...
    three_years: ...
    ten_years: ...
  symbol: DOTUSDT             # 단일 심볼 (옵션)
```

**사용 방법:**
1. `backtest.period` 변경 → 원하는 기간 선택
2. `backtest.symbol` 설정 → 단일 심볼 백테스트
3. `backtest.symbol` 제거 → 멀티 심볼 백테스트

---

### **3. 새 모듈: MultiSymbolHistoricalFeed**

**파일:** `collectors/multi_historical_feed.py`

**기능:**
- 여러 심볼 CSV를 동시에 로드
- 시간순으로 캔들 병합 (heap queue)
- start_date, end_date 필터링
- 진행률 추적

**사용 예:**
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

## 🎯 설정 계층 (우선순위)

```
1. config.yml        (최우선)
   ↓
2. 환경변수          (fallback)
   ↓
3. 기본값            (최후)
```

**예시:**
```python
data_dir = backtest_cfg.get('data_dir', 'data')  # yml → 기본값
```

---

## 📊 백테스트 결과

### **버그 수정 전**
- 거래: 3건 ❌
- 문제: position_value 재계산 오류

### **버그 수정 후**
- 거래: 1,047건 ✅ (349배 증가)
- 성과: 분석 중

---

## 🔧 수정된 버그

### **1. position_value 재계산 오류**
- 문제: position_sizer, engine, risk_manager가 각각 재계산
- 해결: 1곳에서만 계산, 나머지는 전달받음

### **2. symbol 키 누락**
- 문제: decision에 symbol 없어서 'UNKNOWN'으로 저장
- 해결: decision['symbol'] = candle_symbol 추가

### **3. exposure 누적 오류**
- 문제: 포지션 종료 시 재계산으로 다른 값 사용
- 해결: 포지션에 position_value 저장

---

## ✅ 체크리스트

- [x] main.py 하드코딩 제거
- [x] config.yml 기반 백테스트
- [x] 단일 심볼 지원 (HistoricalFeed)
- [x] 멀티 심볼 지원 (MultiSymbolHistoricalFeed)
- [x] CSV 파일명 자동 감지
- [x] 기간 설정 (config.yml)
- [x] position_value 버그 수정
- [x] MASTER_PLAN.md 업데이트
- [x] config_backup.yml 생성

---

## 📁 변경된 파일

1. **main.py**
   - 백테스트 로직 전면 수정
   - 하드코딩 제거
   - 멀티 심볼 지원 추가

2. **config.yml**
   - data_dir 수정 (data/historical → data)
   - period 추가 (three_months)
   - periods 정리

3. **collectors/multi_historical_feed.py**
   - 새 모듈 생성
   - 멀티 심볼 CSV 병합

4. **execution/position_sizer.py**
   - max_position_value 3번 체크 강화
   - 디버깅 로그 추가

5. **execution/risk_manager.py**
   - check_order에 position_value 파라미터 추가

6. **execution/engine.py**
   - position_value 재계산 방지
   - decision에 symbol 추가
   - 포지션에 position_value 저장

7. **Docs/PHASE2/MASTER_PLAN.md**
   - 최신 결과 추가
   - 아키텍처 업데이트

---

## 🎓 핵심 원칙 (Phase 1 완료)

1. **단일 소스 진실 (Single Source of Truth)**
   - 모든 설정 → config.yml
   - 하드코딩 금지

2. **모듈 독립성**
   - 각 모듈은 config만 받음
   - 중복 계산 금지

3. **확장성**
   - 단일/멀티 심볼 자동 선택
   - 새 기간 추가 쉬움

---

## 📝 사용 예시

### **단일 심볼 백테스트**
```yaml
# config.yml
backtest:
  symbol: DOTUSDT
  period: three_months
```

### **멀티 심볼 백테스트**
```yaml
# config.yml
backtest:
  # symbol 항목 제거 또는 주석
  period: three_months

symbols:
  mode: manual
  manual:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
```

### **기간 변경**
```yaml
backtest:
  period: one_year  # three_months → one_year
```

---

**완료일:** 2025-10-22 20:40  
**다음 단계:** 백테스트 결과 분석 (1,047건)
