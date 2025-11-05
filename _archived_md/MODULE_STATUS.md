# 📊 모듈 사용 현황 분석

## ✅ **사용 중인 모듈**

### **1. Core Engine (engine.py)**
- ✅ **사용 중**
- `execution/engine.py` - 공통 트레이딩 루프
- 역할: Feed/Broker/Clock 어댑터로 모든 모드 실행

### **2. Adapters**
- ✅ **사용 중**
- `execution/adapters/brokers.py` - SimBroker, PaperBroker, LiveBroker
- `execution/adapters/clocks.py` - SimClock, LiveClock
- 역할: 모드별 거래 실행 및 시간 제공

### **3. Collectors**
- ✅ **사용 중**
- `collectors/historical_collector.py` - HistoricalFeed (백테스트)
- `collectors/websocket_collector.py` - WebSocketCollector (실시간)
- `collectors/rest_collector.py` - REST API (데이터 수집)
- 역할: 데이터 공급

### **4. Position Sizer**
- ✅ **사용 중**
- `execution/position_sizer.py`
- 역할: RPT 기반 포지션 크기 계산
- 기능: Risk-per-trade, Quality Weight, Position Caps

### **5. Risk Manager**
- ✅ **사용 중**
- `execution/risk_manager.py`
- 역할: 일일 손실 한도, 동시 포지션 수 제한
- 현재 상태: **메서드 미구현** (allow_entry 등)

### **6. Strategies (6개)**
- ✅ **사용 중**
- `strategies/scalping.py`
- `strategies/daytrade.py`
- `strategies/swing.py`
- `strategies/trend.py`
- `strategies/reversion.py`
- `strategies/breakout.py`
- 역할: 전략별 신호 생성

### **7. Ensemble**
- ✅ **사용 중**
- `strategies/ensemble.py`
- 역할: 다수결 + 가중 평균으로 신호 통합
- 현재: 간단 버전 (combine_signals)

### **8. Indicators**
- ✅ **사용 중**
- `indicators/__init__.py` - add_indicators()
- `indicators/regime.py` - 시장 상태 분석
- 역할: 기술 지표 계산 (EMA, RSI, BB, MACD 등)

### **9. Common Utilities**
- ✅ **사용 중**
- `common/logger.py` - 로깅
- `common/database.py` - DB 연결
- `common/config.py` - 설정 로드
- `common/calculations.py` - position_size 계산
- `common/strategy_config.py` - 전략 파라미터

---

## ⚠️ **부분 사용 / 미완성 모듈**

### **1. Position Tracker**
- ⚠️ **미사용**
- `execution/position_tracker.py`
- 역할: 진입 후 포지션 추적, TP/SL 관리
- 문제: **engine.py에서 호출 안됨**
- 필요: 포지션 종료 로직 추가

### **2. Signals Module**
- ⚠️ **미사용**
- `signals/signal_generator.py`
- `signals/signal_storage.py`
- 역할: 신호 생성 및 DB 저장
- 문제: 전략 모듈과 중복
- 필요: 전략 모듈로 통합 또는 제거

### **3. Old Executors**
- ❌ **사용 안함**
- `execution/executors/simulation.py`
- `execution/executors/paper.py`
- `execution/executors/live.py`
- 문제: adapters로 대체됨
- 조치: 삭제 가능

---

## 🔧 **성능 튜닝 포인트**

### **1. Position Tracker 통합 (우선순위: 높음)**
```python
# engine.py에 추가 필요
from execution.position_tracker import PositionTracker

tracker = PositionTracker()

# 거래 후
tracker.add_position(trade_id, decision, qty, entry_price)

# 매 루프마다
closed_trades = tracker.update(current_price)
for trade in closed_trades:
    # TP/SL 처리
    broker.close_position(trade)
```

### **2. Risk Manager 메서드 구현 (우선순위: 높음)**
```python
# risk_manager.py에 추가
def allow_entry(self, symbol: str, side: str) -> bool:
    # 1. 일일 손실 체크
    # 2. 동시 포지션 수 체크
    # 3. 심볼별 노출 체크
    return True/False
```

### **3. Ensemble 개선 (우선순위: 중간)**
- 현재: 간단 다수결
- 개선: 전략별 가중치, 신뢰도 점수, 과거 성과 반영

### **4. 전략 필터 완화 (우선순위: 높음)**
```
목표: 30-50건/일
현재: 1건/일
개선: 조건 완화, 타임프레임 추가 (1m, 3m)
```

### **5. DB 트랜잭션 에러 해결 (우선순위: 높음)**
```
현재: 첫 에러 후 모든 INSERT 실패
원인: 트랜잭션 rollback 누락
해결: engine.py save_trade_to_db() 개선
```

---

## 📈 **기능 추가 제안**

### **1. 포지션 종료 로직**
- TP/SL 도달 시 자동 종료
- Trailing Stop
- 시간 기반 종료

### **2. 포트폴리오 관리**
- 심볼별 배분
- 전략별 자본 배분
- 전체 위험도 모니터링

### **3. 백테스트 레포트**
- HTML 결과 생성
- 그래프 (Equity Curve, Drawdown)
- 전략별 성과 비교

### **4. 텔레그램 알림**
- 거래 실행 알림
- 일일 요약
- 에러 알림

### **5. Context Scaling**
- Volatility Regime 기반 포지션 조정
- 시장 상황별 리스크 조정

---

## 🗑️ **제거 가능 모듈**

### **1. execution/executors/**
- ❌ `simulation.py`
- ❌ `paper.py`
- ❌ `live.py`
- 이유: `execution/adapters/`로 대체

### **2. signals/ (선택적)**
- ⚠️ `signal_generator.py`
- ⚠️ `signal_storage.py`
- 이유: 전략 모듈과 기능 중복
- 조치: 통합 또는 제거

---

## 📋 **우선순위별 작업 목록**

### **🔥 긴급 (지금 해야 할 것)**
1. ✅ DB 트랜잭션 에러 해결
2. ⬜ Position Tracker 통합
3. ⬜ Risk Manager 메서드 구현
4. ⬜ 전략 필터 완화 (거래 빈도 증가)

### **⚡ 중요 (다음 단계)**
5. ⬜ TP/SL 자동 종료 로직
6. ⬜ Ensemble 개선
7. ⬜ 백테스트 레포트 생성
8. ⬜ 불필요 모듈 정리

### **💡 개선 (여유 있을 때)**
9. ⬜ 텔레그램 알림
10. ⬜ Context Scaling
11. ⬜ Half-Kelly 포지션 사이징
12. ⬜ Experience Score 추가

---

## 🎯 **다음 작업 추천**

```bash
# 1. Position Tracker 통합
# 2. Risk Manager 완성
# 3. 전략 필터 완화
# 4. 백테스트 레포트
```

**추천 순서:**
1. Position Tracker → 포지션 종료 로직
2. Risk Manager → 안전장치
3. 전략 필터 → 거래 빈도 증가
4. 백테스트 → 성과 검증
