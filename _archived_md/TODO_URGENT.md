# 🚨 긴급 수정 사항

## ✅ **즉시 해야 할 것**

### **1. DB 통합 (최우선)**

**현재 상태:** DB 사용 안 함
**목표:** 모든 단계가 DB를 통과

```python
# 백테스트 & 실시간 공통
strategies → monitoring.signals (DB)
           → ensemble → trading.decisions (DB)
           → execution → trading.trades (DB)
```

**작업:**
- [ ] `common/database.py` - DB 연결 함수 작성
- [ ] `monitoring.signals` 테이블에 저장
- [ ] `trading.decisions` 테이블에 저장
- [ ] `trading.trades` 테이블에 저장

### **2. SignalGenerator 통합**

**현재 상태:** 백테스트는 직접 호출, 실시간은 SignalGenerator
**목표:** 모든 모드에서 SignalGenerator 사용

```python
# 백테스트
signal_gen.process_candle(candle) → DB 저장

# 실시간
signal_gen.process_candle(candle) → DB 저장
```

**작업:**
- [x] 백테스트에서 SignalGenerator 사용 (진행 중)
- [ ] lookback, config 설정 통일
- [ ] 오류 처리 개선

### **3. REST API 구현**

**현재 상태:** 없음
**목표:** 모든 데이터 조회 가능

```python
GET /api/signals?strategy=scalping
GET /api/decisions
GET /api/positions
GET /api/performance
GET /api/trades
```

**작업:**
- [ ] `api/__init__.py` 생성
- [ ] FastAPI 앱 구성
- [ ] 엔드포인트 구현
- [ ] main.py에서 API 서버 실행

### **4. 진입 조건 개선**

**현재 문제:** 
- SCALPING: 14.2% 승률 ❌
- DAYTRADE: 0.4% 승률 ❌
- SWING: 0.5% 승률 ❌
- REVERSION: 100% 승률 ✅

**원인:** 진입 조건이 너무 단순

**작업:**
- [ ] REVERSION 로직 분석
- [ ] 다른 전략에 다층 검증 추가:
  - ADX > 25 (추세 강도)
  - Volume > 2x average
  - 지지/저항선 확인
  - RSI 극단값 회피

### **5. 리포트 수정**

**현재 문제:**
- 한 전략만 표시
- 성능 리포트 없음

**작업:**
- [ ] `reports/performance_reporter.py` 수정
- [ ] DB에서 모든 전략 데이터 로드
- [ ] 전략별 섹션 추가
- [ ] 차트 추가 (Equity Curve)

---

## 📋 **구현 순서**

### **Phase 1: DB 통합 (1일)**
1. DB 스키마 생성
2. 저장 함수 작성
3. 백테스트 수정
4. 실시간 수정

### **Phase 2: SignalGenerator 통일 (0.5일)**
1. 백테스트 config 수정
2. 오류 처리
3. 테스트

### **Phase 3: REST API (0.5일)**
1. FastAPI 설정
2. 엔드포인트 구현
3. 테스트

### **Phase 4: 전략 개선 (2일)**
1. REVERSION 분석
2. 다른 전략 수정
3. 백테스트 재실행

### **Phase 5: 리포트 (0.5일)**
1. 성능 리포터 수정
2. HTML 생성
3. 차트 추가

---

## 🎯 **목표 지표**

### **최소 기준**
- 승률: > 55%
- Profit Factor: > 1.5
- Sharpe Ratio: > 1.0
- MDD: < 20%

### **현재 vs 목표**

| 전략 | 현재 승률 | 목표 승률 | 현재 PF | 목표 PF |
|------|-----------|-----------|---------|---------|
| SCALPING | 14.2% | 60% | 0.19 | 1.8 |
| DAYTRADE | 0.4% | 55% | 0.00 | 1.5 |
| SWING | 0.5% | 55% | 0.00 | 1.5 |
| TREND | 0.0% | 50% | 0.00 | 1.3 |
| REVERSION | 100% | 60% | N/A | 2.0 |
| ENSEMBLE | - | 65% | - | 2.5 |

---

## 🔴 **중단할 것**

1. **단순 파라미터 튜닝** - 근본적인 문제가 있음
2. **Trailing Stop** - 역효과, 나중에 다시 검토
3. **복잡한 필터** - 기본부터 다시

## 🟢 **집중할 것**

1. **DB 통합** - 시스템 아키텍처 완성
2. **진입 조건** - 승률 개선
3. **REVERSION 로직** - 성공 사례 분석
