# 🔍 바이낸스 선물 API TP/SL 분석

**작성일**: 2025-11-07
**목적**: 현재 구현과 바이낸스 API 공식 스펙 비교, 누락된 기능 파악

---

## 1. 바이낸스 API 주문 타입별 파라미터

### 📋 STOP_MARKET (현재 SL 구현에 사용 중)

| 파라미터 | 필수 | 설명 | 현재 구현 |
|---------|------|------|-----------|
| **symbol** | ✅ | 심볼 | ✅ 구현 |
| **side** | ✅ | BUY/SELL | ✅ 구현 (close_side) |
| **type** | ✅ | STOP_MARKET | ✅ 구현 |
| **stopPrice** | ✅ | 트리거 가격 | ✅ 구현 |
| **positionSide** | ✅ | BOTH/LONG/SHORT | ✅ 구현 (BOTH) |
| **closePosition** | ⚠️ | true = 전체 청산 | ✅ 구현 (true) |
| **workingType** | ❌ | MARK_PRICE/CONTRACT_PRICE | ❌ **누락** |
| **priceProtect** | ❌ | 가격 보호 메커니즘 | ❌ **누락** |
| **timeInForce** | ❌ | GTC/IOC/FOK/GTD | ❌ 미사용 (기본 GTC) |

### 📋 TAKE_PROFIT_MARKET (TP 서버 등록 시 사용 가능)

| 파라미터 | 필수 | 설명 | 현재 구현 |
|---------|------|------|-----------|
| **symbol** | ✅ | 심볼 | ❌ **미구현** |
| **side** | ✅ | BUY/SELL | ❌ **미구현** |
| **type** | ✅ | TAKE_PROFIT_MARKET | ❌ **미구현** |
| **stopPrice** | ✅ | 트리거 가격 | ❌ **미구현** |
| **positionSide** | ✅ | BOTH/LONG/SHORT | ❌ **미구현** |
| **closePosition** | ⚠️ | true = 전체 청산 | ❌ **미구현** |
| **workingType** | ❌ | MARK_PRICE/CONTRACT_PRICE | ❌ **미구현** |
| **priceProtect** | ❌ | 가격 보호 메커니즘 | ❌ **미구현** |

### 📋 TRAILING_STOP_MARKET (트레일링 서버 등록 시 사용 가능)

| 파라미터 | 필수 | 설명 | 현재 구현 |
|---------|------|------|-----------|
| **symbol** | ✅ | 심볼 | ❌ **미구현** |
| **side** | ✅ | BUY/SELL | ❌ **미구현** |
| **type** | ✅ | TRAILING_STOP_MARKET | ❌ **미구현** |
| **callbackRate** | ✅ | 콜백 비율 (0.1% ~ 5%) | ❌ **미구현** |
| **activationPrice** | ⚠️ | 활성화 가격 (선택) | ❌ **미구현** |
| **positionSide** | ✅ | BOTH/LONG/SHORT | ❌ **미구현** |
| **workingType** | ❌ | MARK_PRICE/CONTRACT_PRICE | ❌ **미구현** |

---

## 2. 중요 파라미터 상세 분석

### 🔴 workingType (매우 중요!)

**기능**: SL/TP 트리거 가격 기준 선택

| 값 | 설명 | 장점 | 단점 |
|----|------|------|------|
| **MARK_PRICE** | 마크 가격 기준 (기본값) | 청산 가격과 동일 기준, 조작 방지 | 약간의 지연 가능 |
| **CONTRACT_PRICE** | 거래소 실제 가격 | 실시간 반영 빠름 | 순간 스파이크에 취약 |

**트리거 조건**:
- **STOP_MARKET (SL)**:
  - BUY (SHORT 청산): `latest price >= stopPrice`
  - SELL (LONG 청산): `latest price <= stopPrice`
- **TAKE_PROFIT_MARKET (TP)**:
  - BUY (SHORT 청산): `latest price <= stopPrice`
  - SELL (LONG 청산): `latest price >= stopPrice`

**현재 문제**: `workingType` 미지정 → **기본값 MARK_PRICE** 사용 중
- COAIUSDT -438% 손실 케이스: MARK_PRICE와 CONTRACT_PRICE 괴리 가능성

### 🔴 priceProtect (극단 가격 변동 보호)

**기능**: `stopPrice` 도달 시 MARK_PRICE와 CONTRACT_PRICE 차이 검증

```
if priceProtect == true:
    if |MARK_PRICE - CONTRACT_PRICE| / MARK_PRICE > triggerProtect:
        주문 트리거 안 됨 (보호 발동)
```

**triggerProtect**: 심볼별로 설정된 최대 허용 괴리율
- `GET /fapi/v1/exchangeInfo`에서 조회 가능

**현재 문제**: `priceProtect` 미설정 → **극단 가격 변동에 무방비**
- Flash Crash, Pump & Dump 상황에서 SL이 엉뚱한 가격에 트리거될 수 있음

### 🔴 closePosition=true (전체 청산)

**제약 사항**:
1. `quantity` 파라미터와 함께 사용 불가
2. `reduceOnly` 파라미터와 함께 사용 불가
3. **Hedge Mode에서 사용 제한**:
   - BUY 주문은 LONG 포지션 사이드에서 사용 불가
   - SELL 주문은 SHORT 포지션 사이드에서 사용 불가

**현재 상태**: ✅ `closePosition=true` 사용 중
- One-Way Mode에서만 동작 → ✅ 정상

---

## 3. 누락된 기능 및 위험성

### 🔴 CRITICAL: workingType 미지정

**위험도**: ★★★★★

**문제**:
- 기본값 MARK_PRICE 사용
- 극단적 변동 시 MARK_PRICE와 CONTRACT_PRICE 괴리 발생 가능
- SL이 의도한 가격에 트리거 안 될 수 있음

**예시** (COAIUSDT 케이스 추정):
```
Entry: $0.9155 (SHORT)
SL: $1.10 (MARK_PRICE 기준)

상황: Flash Pump 발생
- CONTRACT_PRICE: $4.934 (급등)
- MARK_PRICE: $1.10 (아직 도달 안 함, 지연)

결과: SL 트리거 안 됨 → 손실 -438%
```

**해결책**: `workingType='CONTRACT_PRICE'` 명시적 설정 권장

### 🔴 HIGH: priceProtect 미설정

**위험도**: ★★★★☆

**문제**:
- 극단 가격 변동에서 SL/TP가 잘못된 가격에 트리거
- Flash Crash/Pump에서 불리한 가격에 청산

**해결책**: `priceProtect=True` 설정 권장

### 🟡 MEDIUM: TP 서버 등록 미구현

**위험도**: ★★★☆☆

**현재**: TP는 로컬에서만 체크 (engine.py → PositionTracker)
**문제**: 
- 컨테이너 재시작 시 TP 정보 유실 가능
- 네트워크 지연 시 TP 놓칠 수 있음

**장점**: 
- TP 분할 청산 유연성 (30% → 40% → 30%)
- 로컬 로직으로 정밀 제어 가능

**판단**: 현재 방식 유지 (Option C), 필요시 PR12에서 개선

### 🟡 LOW: TRAILING_STOP_MARKET 미구현

**위험도**: ★★☆☆☆

**현재**: 로컬 트레일링 로직 (PositionTracker)
**서버 트레일링**: `callbackRate` 기반 자동 트레일링

**판단**: 로컬 로직이 더 유연함, 서버 API는 선택사항

---

## 4. 현재 구현 vs 바이낸스 권장 사항

### 현재 구현 (brokers.py)

```python
sl_order = self.client.futures_create_order(
    symbol=symbol,
    side=close_side,
    type='STOP_MARKET',
    stopPrice=sl_price,
    closePosition=True,
    positionSide='BOTH'
)
```

### ⭐ 권장 개선안

```python
sl_order = self.client.futures_create_order(
    symbol=symbol,
    side=close_side,
    type='STOP_MARKET',
    stopPrice=sl_price,
    closePosition=True,
    positionSide='BOTH',
    workingType='CONTRACT_PRICE',  # ⭐ 추가: 실시간 가격 기준
    priceProtect=True              # ⭐ 추가: 가격 보호 활성화
)
```

**변경 사유**:
1. **workingType='CONTRACT_PRICE'**: 실시간 가격 기준, 지연 최소화
2. **priceProtect=True**: Flash Crash/Pump 보호

**trade-off**:
- CONTRACT_PRICE는 스파이크에 민감 → 하지만 `-50% 극단 손실 방지` 로직과 조합 시 안전
- priceProtect는 극단 상황에서 SL 트리거 안 될 수 있음 → 하지만 극단 손실 방지 로직이 백업

---

## 5. 개선 계획

### Phase 1: workingType + priceProtect 추가 (CRITICAL)

**파일**: `execution/adapters/brokers.py`
**메서드**: 
- `LiveBroker.create_sl_order()`
- `PaperBroker.create_sl_order()` (파라미터 파리티)

**변경**:
```python
def create_sl_order(self, position: dict, sl_price: float, 
                    working_type: str = 'CONTRACT_PRICE',
                    price_protect: bool = True) -> dict:
```

**config.yml 추가**:
```yaml
exits:
  working_type: "CONTRACT_PRICE"  # MARK_PRICE | CONTRACT_PRICE
  price_protect: true              # Flash crash 보호
```

### Phase 2: Modify Order API 검증 (HIGH)

**현재**: `futures_modify_order` 사용 중 (update_sl_price)
**확인 필요**: Binance Python 라이브러리가 이 API를 지원하는지 검증
**폴백**: Cancel & Replace (현재 구현됨)

### Phase 3: TP 서버 등록 (선택, PR12)

**판단**: 현재 로컬 TP 로직 유지
**이유**: 분할 청산 유연성 > 서버 등록 안정성

---

## 6. 참고 문서

- [Binance Futures API - New Order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order)
- [Binance Futures API - Change Log](https://developers.binance.com/docs/derivatives/change-log)

---

## 7. 체크리스트

- [x] 바이낸스 API 공식 문서 정독
- [x] 현재 구현과 API 스펙 비교
- [x] 누락된 파라미터 식별 (workingType, priceProtect)
- [x] COAIUSDT -438% 케이스 원인 추정 (workingType 미지정)
- [ ] config.yml에 working_type, price_protect 추가
- [ ] brokers.py에 파라미터 구현
- [ ] Paper/Live 파리티 보장
- [ ] 30분 재검증으로 확인
