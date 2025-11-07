# PR10 중대 분석 - 기존 시스템 정확한 이해

**작성 시각**: 2025-11-06 21:00 UTC+09:00  
**목적**: 제가 성급하게 구현한 brokers.py의 심각한 문제들을 파악하고 해결

---

## ❌ 발견된 심각한 문제들

### 1. **하드코딩 문제 (CRITICAL)**

**문제**: `brokers.py`에 TP 비율을 하드코딩

```python
# ❌ brokers.py L194, L208 - 하드코딩!
tp1_qty = round(total_qty * 0.3, 4)  # 30% 하드코딩
tp2_qty = round(total_qty * 0.4, 4)  # 40% 하드코딩
```

**실제 시스템**: `config.yml` + `TPManager`가 이미 설정 기반으로 동작!

```yaml
# config.yml L169-172
exits:
  take_profits:
    - r_multiple: 1.0
      size_pct: 30  # ⭐ 설정 파일에 있음!
    - r_multiple: 2.0
      size_pct: 40  # ⭐ 설정 파일에 있음!
```

```python
# tp_manager.py L34-38
self.tp_levels = exits.get('take_profits', [
    {'r_multiple': 1.0, 'size_pct': 30},
    {'r_multiple': 2.0, 'size_pct': 40}
])

# tp_manager.py L116-130
def calculate_partial_size(self, total_qty: float, tp_level: int) -> float:
    for level in self.tp_levels:
        if level['r_multiple'] == tp_level:
            return total_qty * (level['size_pct'] / 100)
    return 0
```

**영향**:
- 페이퍼/라이브 모드에서 다른 TP 비율 사용 불가
- 튜닝 시 TP 비율 조정 불가 (하드코딩)
- `.windsurfrules` 위반 (하드코딩 제거 원칙)

---

### 2. **기존 모듈 중복 구현 문제 (CRITICAL)**

**문제**: `PositionTracker`가 이미 `TPManager`를 사용하는데, `brokers.py`에서 중복 구현

**기존 시스템 구조**:

```
engine.py
  ↓
position_tracker.py  ← 이미 TPManager 사용 중
  ↓
tp_manager.py  ← config.yml에서 설정 읽음
```

**내가 만든 구조** (중복!):

```
brokers.py
  ↓
create_tpsl_orders()  ← TPManager 로직 복제 (하드코딩)
```

**실제 코드**:

```python
# position_tracker.py L32-33
self.tp_manager = TPManager(self.config)

# position_tracker.py L148
partial_qty = self.tp_manager.calculate_partial_size(total_qty, 1)

# position_tracker.py L160
partial_qty = self.tp_manager.calculate_partial_size(total_qty, 2)
```

**결론**: `TPManager`는 이미 `PositionTracker`가 사용 중! 중복 구현 불필요!

---

### 3. **Binance API TP/SL 자동 등록의 문제**

**내가 구현한 방식**:
- 진입 시 즉시 TP/SL 주문을 Binance 서버에 등록
- TP1 30%, TP2 40% 비율 하드코딩

**실제 시스템의 방식**:
- `position_tracker.py`가 Python에서 매 캔들마다 체크
- `check_tpsl_with_partial()` 메서드로 분할 청산 처리
- 설정 기반 유연한 비율 조정

**질문**:
1. Binance API에 TP/SL을 미리 등록해야 하는가?
2. 아니면 Python에서 체크하는 현재 방식이 맞는가?
3. 두 방식의 장단점은?

---

### 4. **broker.execute() 호출 후 TP/SL 등록 누락**

**현재 engine.py 구조**:

```python
# engine.py에서 진입 시
order_result = broker.execute(decision, qty)

# ⭐ 여기서 TP/SL 주문 등록이 없음!
# ⭐ position_tracker만 포지션 추적
```

**내가 추가한 메서드**:
- `create_tpsl_orders()` - 하지만 engine.py에서 호출 안 함!

**문제**:
- Live 모드에서 TP/SL 주문이 Binance에 등록되지 않음
- Paper 모드는 position_tracker가 처리하므로 문제 없음
- Live/Paper 로직 불일치 발생!

---

## 🔍 기존 시스템 분석 (확정)

### A. TP/SL 처리 흐름 (현재 - Python 기반)

```
1. 진입 (engine.py L1033-1102):
   - broker.execute(decision, qty)  ⭐ 진입 주문만!
   - TP 레벨 계산: tracker.tp_manager.calculate_tp_levels()  ⭐ config.yml 사용
   - active_positions[id] = {..., 'tp_levels': tp_levels}

2. 포지션 추적 (engine.py L458-498):
   - 매 캔들마다 같은 심볼 포지션만 체크
   - tracker.check_tpsl_with_partial(position, current_price, atr)
   - tp_manager.calculate_partial_size(total_qty, 1)  ⭐ config.yml 비율 사용
   - 부분 청산: position['qty'] -= close_qty
   - 전체 청산: positions_to_close.append()

3. 청산 (engine.py L500-533):
   - close_trade_in_db(pos_id, price, pnl, reason)
   - portfolio.update_equity(new_equity)
   - risk.update_daily_pnl(pnl)
   - active_positions.pop(pos_id)  ⭐ 삭제
```

**핵심**: Binance API에 TP/SL 주문을 미리 등록하지 않음!

### B. Binance API 사용 현황 (확정)

**collectors/rest_collector.py** (데이터 수집만):
- `futures_klines()`: 히스토리 캔들 로드
- `futures_exchange_info()`: 거래소 정보
- `futures_ticker()`: 24시간 통계
- ⭐ 주문 실행 API 없음!

**collectors/websocket_collector.py** (실시간 데이터):
- WebSocket 캔들 스트림 구독
- ⭐ 주문 실행 없음!

**execution/adapters/brokers.py**:
- `LiveBroker.execute()`: `futures_create_order()` ⭐ 유일한 주문 API
- ⭐ TP/SL 자동 등록 로직 없음!

**결론**: 
- **Paper 모드**: Python `position_tracker`가 모든 TP/SL 체크
- **Live 모드**: Python `position_tracker`가 모든 TP/SL 체크 (동일!)
- ⭐ **Binance TP/SL API는 현재 미사용**

---

## 🎯 해결 방안 (최종 결정 필요)

### Option A: Binance TP/SL API 완전 활용

**장점**:
- ✅ 서버 측 실행 (Python 다운타임 무관)
- ✅ 슬리피지 최소화
- ✅ 실시간 체결 보장

**단점**:
- ❌ 트레일링 스톱 업데이트 시 API 호출 반복 (rate limit)
- ❌ Paper 모드와 동기화 복잡 (가상 주문 vs 실제 주문)
- ❌ config.yml 비율 변경 시 실시간 반영 불가

**구현 난이도**: 중 (하드코딩 제거 + engine.py 수정)

---

### Option B: Python 체크 유지 (현재 방식, 최소 변경)

**장점**:
- ✅ 유연한 비율 조정 (config.yml 즉시 반영)
- ✅ Paper/Live 100% 동일 로직 보장
- ✅ 현재 시스템과 완벽 호환
- ✅ 트레일링 스톱 자유롭게 업데이트

**단점**:
- ❌ Python 다운 시 청산 불가 (심각!)
- ❌ 매 캔들 체크 부하 (20심볼×초당 1캔들 = 초당 20회)

**구현 난이도**: 하 (brokers.py 수정만)

---

### Option C: 하이브리드 (추천! 🌟)

**전략**:
1. **SL만 Binance API** (안전망)
   - 진입 즉시 STOP_MARKET 주문 등록
   - Python 다운 시에도 손절 보장
   
2. **TP는 Python 체크** (유연성)
   - position_tracker가 분할 청산 처리
   - config.yml 비율 즉시 반영
   - 트레일링 스톱 자유롭게 업데이트

**장점**:
- ✅ 리스크 관리 (SL 서버 측 실행)
- ✅ 유연성 (TP Python 체크)
- ✅ Paper/Live 로직 동일 (PaperBroker가 SL만 시뮬레이션)

**단점**:
- ⚠️ 하이브리드 복잡도 증가

**구현 난이도**: 중

**구현 계획**:
```python
# engine.py L1103 이후 추가
if mode == 'live':
    # Live 모드: Binance에 SL 주문 등록
    broker.create_sl_order(
        position={'id': position_id, 'symbol': candle_symbol, 
                  'side': decision['side'], 'qty': qty},
        sl_price=decision['sl']
    )
elif mode == 'paper':
    # Paper 모드: 가상 SL 주문 등록 (추적용)
    broker.create_sl_order(
        position={'id': position_id, 'symbol': candle_symbol,
                  'side': decision['side'], 'qty': qty},
        sl_price=decision['sl']
    )
```

---

## 📋 수정 계획 (롤백 + 재구현)

### 1단계: 잘못된 코드 롤백 (5분)

```bash
git revert HEAD~2  # 마지막 2개 커밋 취소
```

**삭제할 내용**:
- `brokers.py`: `create_tpsl_orders()` 메서드 (하드코딩)
- `brokers.py`: 0.3, 0.4 하드코딩된 모든 로직

---

### 2단계: Option 선택 (사용자 결정 필요)

**질문드립니다**:
1. Option A, B, C 중 어떤 방식을 선호하시나요?
2. Python 다운타임 시 SL 실패 리스크를 어떻게 보시나요?
3. Paper/Live 로직 100% 동일이 최우선인가요?

---

### 3단계: 선택된 Option 구현

**Option C 선택 시** (추천):

1. **brokers.py 수정** (20분):
   ```python
   def create_sl_order(self, position: dict, sl_price: float) -> dict:
       """SL 주문만 등록 (안전망)"""
       # config.yml 사용 안 함 (sl_price는 engine에서 계산)
       ...
   ```

2. **engine.py 수정** (15분):
   ```python
   # L1103 이후 추가
   if mode == 'live':
       broker.create_sl_order(position, decision['sl'])
   elif mode == 'paper':
       broker.create_sl_order(position, decision['sl'])  # 가상
   ```

3. **TP 체크는 유지** (변경 없음):
   - `position_tracker.check_tpsl_with_partial()`
   - `tp_manager.calculate_partial_size()`
   - config.yml 비율 사용

---

### 4단계: 테스트 (30분)

1. **Unit Test**: `create_sl_order()` 메서드
2. **Paper Test**: 24시간 실행 (SL 가상 주문 확인)
3. **Live Test**: 소액 1회 거래 (Binance SL 주문 확인)

---

## 🚨 반성 및 교훈

### 내가 저지른 실수

1. ❌ **프로젝트 이해 부족**
   - tp_manager.py, position_tracker.py를 제대로 읽지 않음
   - config.yml 구조 미파악

2. ❌ **하드코딩 추가**
   - 0.3, 0.4 하드코딩 (config.yml에 이미 있음)
   - `.windsurfrules` 위반

3. ❌ **기존 모듈 중복 구현**
   - TPManager 로직을 brokers.py에 복제
   - 유지보수성 악화

4. ❌ **전체 구조 미파악**
   - engine.py 호출 흐름 모름
   - collectors/ 역할 확인 안 함

### 교훈

- ✅ **10분 분석 > 1시간 구현**
- ✅ **기존 모듈 먼저 확인**
- ✅ **config.yml이 Single Source of Truth**
- ✅ **하드코딩은 절대 금지**

**다음부터는**: grep, read_file로 철저히 조사 후 구현

---

## 💬 사용자께 질문

1. **Option A/B/C 중 어떤 방식이 좋으실까요?**
   - Option C (하이브리드) 추천: SL 안전망 + TP 유연성

2. **brokers.py 롤백할까요?**
   - 현재 커밋 취소 후 재구현

3. **다른 Binance 프로그램 비교 필요한가요?**
   - Python TP/SL vs Binance API TP/SL 모범 사례

4. **기타 놓친 부분이 있을까요?**
   - collectors/, execution/ 외 다른 모듈 확인 필요
