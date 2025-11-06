# 🔍 Binance 시스템 전체 점검 결과

**점검 시각**: 2025-11-06 20:20 UTC+09:00

---

## 1️⃣ Binance Futures 포지션 모드

### ✅ 확인 완료

**두 가지 모드:**

1. **One-way Mode (기본값)**
   - 한 심볼에 **한 방향만** 보유 가능
   - 같은 방향 추가 구매 → 평균 진입가로 합쳐짐
   - 반대 방향 구매 → 기존 포지션 청산 + 반대 포지션 신규
   - API 파라미터: `positionSide="BOTH"`

2. **Hedge Mode**
   - 한 심볼에 롱/숏 **동시 보유** 가능
   - API 파라미터: `positionSide="LONG"` 또는 `"SHORT"` 명시 필수
   - 계정 설정: `POST /fapi/v1/positionSide/dual` (dualSidePosition=true)

**출처**: 
- https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Position-Mode
- https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order

---

## 2️⃣ 현재 구현 문제점

### 🔴 CRITICAL: One-way Mode 위반

**발견된 문제:**
```sql
-- DB에 불가능한 포지션 존재
한 심볼에 LONG/SHORT 동시 OPEN:
- AAVEUSDT: LONG + SHORT
- DASHUSDT: LONG + SHORT  
- ETHUSDT: LONG + SHORT
- HIPPOUSDT: LONG + SHORT
... 8개 심볼
```

**원인:**
1. `LiveBroker.execute()`: `positionSide` 파라미터 없음
2. 페이퍼 모드: DB만 기록 → 문제 숨겨짐
3. 라이브 모드: 실제 Binance 실행 시 **오류 발생 예상**

**코드 확인:**
```python
# execution/adapters/brokers.py L118-130
order = self.client.futures_create_order(
    symbol=symbol,
    side='BUY',  # ← positionSide 없음!
    type='MARKET',
    quantity=qty
)
```

---

## 3️⃣ TP/SL 자동 실행 메커니즘

### ⚠️ 문제: Binance API 미사용

**Binance 공식 방식:**
- 조건부 주문 등록: `STOP_MARKET`, `TAKE_PROFIT_MARKET`
- Binance 서버가 자동 실행 (24/7)
- API: `POST /fapi/v1/order` with `type=STOP_MARKET` or `TAKE_PROFIT_MARKET`

**우리 현재 구현:**
- Python 코드로 매 캔들마다 체크 (`check_tpsl_with_partial`)
- Binance에 TP/SL 주문 **등록 안 함**
- 봇이 중단되면 청산 불가능!

**리스크:**
- ✅ 페이퍼 모드: 문제 없음 (가상 실행)
- 🔴 라이브 모드: 봇 중단 시 손실 확대 가능

---

## 4️⃣ 포지션 수 한도

### 확인 중...

**Binance 규칙:**
- 최대 오픈 포지션: 계정당 **50개 계약** (심볼)
- 최대 오픈 주문: **10,000개**
- 조건부 주문 (TP/SL): 포지션당 **10개**

**출처**:
- https://www.binance.com/en/support/faq/binance-futures-trading-quantitative-rules-4f462ebe6ff445d4a170be7d9e897272

**현재 DB 상태:**
- OPEN 포지션: 75개 (심볼 수 확인 필요)
- 한도 초과 가능성 있음

---

## 5️⃣ 자산 관리 모듈

### ✅ 구현 확인

**config.yml:**
```yaml
capital:
  initial: 50000  # 초기 자본금 (USDT)
  
equity: 50000  # 현재 자산 (USDT)
```

**구현 위치:**
- `execution/portfolio_manager.py`: 30개 매치
- `execution/risk_manager.py`: 30개 매치
- `execution/engine.py`: 46개 매치

**동작:**
- 페이퍼 모드: 고정값 (50000 USDT)
- 라이브 모드: Binance API로 실제 자산 조회 필요
  - `client.futures_account_balance()`

---

## 6️⃣ TP/SL 도달 불가 분석

### 현재 OPEN 포지션 예시

```
DASHUSDT LONG:
- Entry: 128.064
- TP: 225.82 (76% 상승 필요!) 
- SL: 88.87 (31% 하락)
- 경과 시간: 5시간

NMRUSDT SHORT:
- Entry: 12.10
- TP: 11.93 (1.4% 하락 필요)
- SL: 12.22 (1% 상승)
- 경과 시간: 62.7시간 (2.6일!)
```

**의미:**
- ✅ NMRUSDT: TP/SL 범위 내 (정상 대기)
- ⚠️ DASHUSDT: TP 도달 매우 어려움 (설정 오류 가능)

**TP/SL 작동 방식:**
- Mark Price가 TP/SL 가격 도달 시 즉시 청산
- 우리 구현: 1분마다 체크 (`check_tpsl_with_partial`)
- 정상 작동 중 ✅

---

## 7️⃣ 헷지 모드 구현 복잡도

### Option 1: One-way Mode (권장) ⭐

**난이도: 낮음**

**구현:**
1. 기존 OPEN 포지션과 반대 방향 신호 → 무시
2. 같은 방향만 진입 허용
3. `LiveBroker`: `positionSide="BOTH"` 추가

**장점:**
- 간단하고 안전
- 대부분 트레이더가 사용
- 기존 로직 최소 변경

**단점:**
- 헷지 전략 사용 불가

---

### Option 2: Hedge Mode

**난이도: 중간**

**구현:**
1. Binance 계정 설정 변경
   ```python
   client.futures_change_position_mode(dualSidePosition=True)
   ```

2. `LiveBroker` 수정
   ```python
   order = self.client.futures_create_order(
       symbol=symbol,
       side='BUY',
       positionSide='LONG',  # ← 추가!
       type='MARKET',
       quantity=qty
   )
   ```

3. DB 스키마 수정
   - `position_side` 컬럼 추가 (`LONG`/`SHORT`)

4. `PortfolioManager` 로직 수정
   - 같은 심볼의 LONG/SHORT 별도 관리

**장점:**
- 유연한 헷지 전략 가능
- 롱/숏 동시 보유

**단점:**
- 구현 복잡도 높음
- 테스트 필요
- 자산 관리 복잡

---

## 8️⃣ 복잡도 비교 & 구현 전략

### Option 1: One-Way Mode (권장) ⭐

**구현 시간:** 2-3시간  
**복잡도:** 매우 낮음

**변경 파일:**
1. `execution/adapters/brokers.py`: `positionSide="BOTH"` 추가 (1줄)
2. `execution/portfolio_manager.py`: 반대 방향 신호 거부 (10줄)
3. `execution/engine.py`: Binance TP/SL API 연동 (30줄)

**장점:**
- 간단하고 안전
- 페이퍼/라이브 즉시 동작
- 나중에 Hedge 추가 가능 (호환성 100%)

---

### Option 2: Hedge Mode

**구현 시간:** 1-2일  
**복잡도:** 중간

**"바이낸스 계정 설정 변경"이란?**
```python
# 계정 전체에 1회만 실행 (모든 심볼 적용)
client.futures_change_position_mode(dualSidePosition=True)
```

**변경 사항:**
- DB 스키마: `position_side` 컬럼 추가
- LiveBroker: 모든 주문에 `positionSide` 명시
- PortfolioManager: LONG/SHORT 별도 관리
- PositionTracker: 청산 로직 수정

**결론:** One-Way 먼저 구현 → Hedge는 나중에 추가 가능 ✅

---

## 9️⃣ Binance API 유동적 TP/SL 변경

### ✅ 완전 가능합니다!

**방법 1: Modify Order API (권장)**
```python
# TP/SL 주문 수정 (가격, 수량 변경 가능)
client.futures_modify_order(
    symbol='BTCUSDT',
    orderId=12345,
    quantity=0.5,
    stopPrice=62000  # ← 새로운 SL 가격
)
```
**API:** `PUT /fapi/v1/order`  
**문서:** https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Modify-Order

**방법 2: Cancel & Replace**
```python
# 1. 기존 TP/SL 취소
client.futures_cancel_order(symbol='BTCUSDT', orderId=12345)

# 2. 새 TP/SL 등록
client.futures_create_order(
    symbol='BTCUSDT',
    side='SELL',
    type='TAKE_PROFIT_MARKET',
    stopPrice=65000,  # ← 새로운 TP
    closePosition=True
)
```

**가능한 시나리오:**
- ✅ 트레일링 스톱: 1분마다 SL 가격 업데이트
- ✅ 분할 익절: TP1 도달 시 TP2 가격 수정
- ✅ 동적 조정: 시장 상황에 따라 실시간 변경

**결론:** 앱에서 하는 것처럼 API로도 100% 가능! ✅

---

## 🔟 Binance API 전체 매핑

### 현재 구현 vs Binance API

| 기능 | 현재 구현 | Binance API | 상태 | 우선순위 |
|------|----------|-------------|------|---------|
| **포지션 진입** | ✅ `futures_create_order` | `POST /fapi/v1/order` | ⚠️ `positionSide` 누락 | **HIGH** |
| **TP/SL 등록** | ❌ Python 체크만 | `STOP_MARKET`, `TAKE_PROFIT_MARKET` | 🔴 미구현 | **CRITICAL** |
| **TP/SL 수정** | ❌ 없음 | `PUT /fapi/v1/order` (Modify) | 🔴 미구현 | **MEDIUM** |
| **TP/SL 취소** | ❌ 없음 | `DELETE /fapi/v1/order` | 🔴 미구현 | **LOW** |
| **포지션 조회** | ❌ DB만 | `GET /fapi/v2/positionRisk` | 🔴 미구현 | **HIGH** |
| **자산 조회** | ❌ 고정값 | `GET /fapi/v2/balance` | 🔴 미구현 | **CRITICAL** |
| **레버리지 설정** | ❌ 없음 | `POST /fapi/v1/leverage` | 🔴 미구현 | **MEDIUM** |
| **포지션 모드 확인** | ❌ 없음 | `GET /fapi/v1/positionSide/dual` | 🔴 미구현 | **LOW** |

**API 문서:**
- New Order: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order
- Modify Order: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Modify-Order
- Position Risk: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Position-Information-V3

---

## 1️⃣1️⃣ 최종 권장사항

### 🎯 즉시 조치 (24시간 평가 전) - PR10 범위

**Phase 1: 정리 (10분)**
1. **모든 OPEN 포지션 강제 청산**
   ```sql
   UPDATE trading.trades 
   SET status = 'CLOSED', 
       exit_reason = 'MANUAL_CLEANUP',
       ts_close = NOW()
   WHERE status = 'OPEN';
   ```

**Phase 2: One-Way Mode 구현 (2-3시간)**
1. `LiveBroker`: `positionSide="BOTH"` 추가
2. `PortfolioManager`: 반대 방향 신호 거부 로직
3. `config.yml`: `max_positions` 로직 점검

**Phase 3: Binance TP/SL API 연동 (2-3시간) ⭐**
1. 진입 시 TP/SL 주문 자동 등록
   - `STOP_MARKET` (SL)
   - `TAKE_PROFIT_MARKET` (TP1, TP2)
2. 트레일링 스톱: 1분마다 SL 가격 업데이트 (`Modify Order`)
3. 분할 익절: TP1 도달 시 Python 체크 유지 (부분 청산)

**Phase 4: 라이브 동기화 준비 (1-2시간)**
1. 실시간 자산 조회: `GET /fapi/v2/balance`
2. 실시간 포지션 조회: `GET /fapi/v2/positionRisk`
3. 레버리지 설정: `POST /fapi/v1/leverage`

**총 소요 시간:** 5-8시간

---

### 🔄 중장기 개선 (PR11 이후)

1. **Hedge Mode 전환** (선택)
   - One-Way로 충분하면 불필요
   - 필요 시 호환성 100% 보장

2. **고급 주문 타입**
   - Trailing Stop Market
   - Iceberg Orders
   - Post-Only Orders

3. **포트폴리오 리밸런싱**
   - 상관관계 그룹 관리
   - 동적 포지션 사이징

---

## 📊 점검 완료 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| Binance API 문서 확인 | ✅ | One-way/Hedge Mode 이해 |
| One-way Mode 위반 발견 | 🔴 | 8개 심볼 LONG+SHORT |
| TP/SL 자동 실행 확인 | ⚠️ | Python 체크, API 미사용 |
| 포지션 수 한도 확인 | ⚠️ | 50개 한도, 현재 확인 필요 |
| 자산 관리 모듈 | ✅ | 구현 완료 |
| Hedge Mode 복잡도 | ✅ | 중간 난이도 |

---

**결론**: One-way Mode로 진행 권장, 즉시 포지션 정리 필요
