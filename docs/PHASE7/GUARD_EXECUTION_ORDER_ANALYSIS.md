# 가드/차단 기능 실행 순서 분석 및 최적화

**작성일**: 2025-11-12  
**관련 PR**: PR11 (슬리피지 가드), PR9 (멱등성), PR10 (중복 방지)  
**상태**: ⚠️  슬리피지 가드 이중 검증 문제 발견

---

## 🎯 목적

1. 전체 가드/차단 기능의 실행 순서 검증
2. 불필요한 이중 검증 제거
3. 상용 프로그램 패턴과 비교
4. 최적 실행 순서 제안

---

## 📊 현재 실행 순서 (engine.py)

### 1. 시스템 초기화 단계
```
FlowGuardian 게이트 (L72-97)
  ↓
READY 상태 검증
  ↓
PAPER/LIVE 모드 진입 허가
```

### 2. 캔들 처리 단계 (메인 루프)
```
1. 일일 PnL 자동 리셋 체크 (L513-514)
2. 캔들 Dedup 체크 (L582-591)
   - Redis 키: dedup:{symbol}:{tf}:{ts}
   - TTL: 타임프레임 길이
3. Flash Guard 업데이트 (L639-641)
   - 60초 내 급등락 감지
```

### 3. 포지션 종료 단계
```
1. Extreme Loss 체크 (L643-652)
   - 실시간 급락 감지
   - 1분 내 -8% 초과
   
2. TP/SL 체크 (L654-733)
   - TP1/TP2 분할 청산
   - Trailing Stop
   - OHLC High/Low 기반 SL
   
3. Drawdown Guard 체크 (L739-741)
   - 최대 낙폭 한도
```

### 4. 신호 생성 및 검증 단계
```
1. 전략 신호 생성 (L1100-1147)
   
2. Risk 기본 체크 (L1159-1163)
   - allow_entry() 메서드
   
3. 포지션 사이즈 계산 (L1165-1178)
```

### 5. ⭐ 진입 검증 단계 (핵심)

```
1. 쿨다운 체크 (L1180-1207)
   ├─ Redis 쿨다운 (전략별, 재시작 후 유지)
   └─ 메모리 쿨다운 (Fallback)
   
2. 신호 멱등성 체크 (L1209-1232)
   ├─ Redis 키: signal:{symbol}:{side}:{candle_ts}
   ├─ TTL: 타임프레임 길이
   └─ 같은 봉 내 중복 신호 차단
   
3. Risk Manager 체크 (L1234-1253)
   ├─ 일일 손실 한도
   ├─ 최대 낙폭 한도
   ├─ 연속 손실 쿨다운
   ├─ Equity 스톱
   └─ 포지션 한도
   
4. Portfolio Manager 체크 (L1255-1280)
   ├─ 전체 포지션 한도
   ├─ 전략별 포지션 한도
   ├─ 심볼별 노출도 한도
   └─ 전략별 예산 한도
   
5. 중복 진입 방지 (L1286-1314)
   ├─ 메모리 체크 (active_positions)
   └─ DB 체크 (trading.trades)
   
6. 반대 포지션 청산 (L1316-1343)
   └─ One-Way Mode 강제

7. ⭐ Broker 실행 (L1345-1351)
   ├─ 동적 슬리피지 적용 (0.05%~6%)
   └─ filled_price 반환

8. ⚠️  Slippage Guard 체크 (L1353-1359)
   ├─ expected_price vs filled_price 비교
   ├─ 차이가 0.5% 초과 시 차단
   └─ ⚠️  문제: 이중 검증!

9. DB 저장 (L1366-1371)

10. Manager 등록 (L1373-1383)
    ├─ risk.add_position()
    └─ portfolio.add_position()
```

---

## 🚨 문제 분석

### Issue 1: 슬리피지 가드 이중 검증

**충돌하는 설정:**
```python
# common/calculations.py::calculate_dynamic_slippage
max_slip = 6%  # 동적 슬리피지 최대값

# execution/risk_manager.py
max_slippage_pct = 0.5%  # Paper 슬리피지 가드
```

**문제:**
1. `broker.execute()`에서 이미 동적 슬리피지 적용 (0.05%~6%)
2. `check_slippage_guard()`에서 0.5%만 허용
3. 결과: **대부분의 진입 차단** (4-5% 슬리피지는 정상 변동성인데 차단됨)

**상용 프로그램 기준:**

| 플랫폼 | 슬리피지 처리 | 가드 |
|--------|--------------|------|
| **QuantConnect** | `VolumePercentPriceImpactModel` | max_percent 내장 |
| **Backtrader** | `PercentSizer` + `slippage` | max 파라미터 |
| **Zipline** | `VolumeShareSlippage` | max_percent 내장 |
| **TradingView** | 슬리피지 모델 | 별도 가드 없음 |

**공통점:**
- 슬리피지 모델 자체가 최대값을 제한
- **별도의 "슬리피지 가드" 없음**
- 이중 검증 없이 단일 제한

### Issue 2: 순서 문제 (해결됨)

**이전 문제:**
```python
risk.add_position()  # 카운트 증가
portfolio.add_position()  # 등록

# 슬리피지 가드 체크
if 슬리피지 초과:
    continue  # risk.add_position()은 이미 실행됨!
```

**현재 (수정됨):**
```python
# broker.execute() → filled_price
# 슬리피지 가드 체크
if 슬리피지 초과:
    continue

# DB 저장 + Manager 등록
```

---

## ✅ 최적 실행 순서 (제안)

### 원칙
1. **빠른 체크 우선** (쿨다운, 캐시)
2. **비용 낮은 체크** (메모리)
3. **비용 높은 체크** (DB, API)
4. **상태 변경 최소화** (실패 시 롤백 불필요)

### 순서

```
┌─────────────────────────────────────────┐
│ 1. 빠른 사전 검증 (캐시 기반)           │
├─────────────────────────────────────────┤
│  - 쿨다운 체크 (Redis/메모리)           │
│  - 신호 멱등성 (Redis)                  │
│  - 중복 진입 방지 (메모리)              │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. 비즈니스 로직 검증                   │
├─────────────────────────────────────────┤
│  - Risk Manager 체크                    │
│  - Portfolio Manager 체크               │
│  - 중복 진입 방지 (DB 재확인)           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. 실행 및 상태 변경                    │
├─────────────────────────────────────────┤
│  - Broker 실행 (동적 슬리피지)          │
│  - DB 저장                              │
│  - Manager 등록                         │
└─────────────────────────────────────────┘
```

**제거:**
- ❌ 슬리피지 가드 체크 (이중 검증 불필요)
- ✅ `calculate_dynamic_slippage()`의 `max_slip=6%`가 유일한 제한

---

## 🔧 권장 수정 사항

### Option 1: 슬리피지 가드 제거 (권장)

**이유:**
- 상용 프로그램 패턴과 일치
- `calculate_dynamic_slippage()`의 `max_slip`이 이미 제한
- 이중 검증 불필요

**수정:**
```python
# execution/engine.py L1353-1359 제거
# ⭐ PR11: Slippage Guard 체크
# if not risk.check_slippage_guard(expected_price, filled_price):
#     continue
```

### Option 2: 슬리피지 가드를 "극단 이상치 감지"로 변경

**목적:**
- API 오류/시스템 오류 감지
- 정상 범위를 벗어난 경우만 차단

**수정:**
```python
# execution/risk_manager.py
max_slippage_pct = 10.0  # 극단 이상치만 (정상: 0.05%~6%)

# execution/engine.py
if expected_price > 0 and filled_price > 0:
    if not risk.check_slippage_guard(expected_price, filled_price):
        logger.critical(f"🚨 극단 슬리피지 감지: {candle_symbol} - API 오류 가능성")
        continue
```

---

**최종 업데이트**: 2025-11-12  
**다음 단계**: 사용자 의사 결정 (Option 1 또는 2)  
**체크리스트**: [PHASE7-2_MASTER_PLAN.md 항목 4](PHASE7-2_MASTER_PLAN.md) 참조  
**관련 파일**:
- `execution/engine.py`
- `execution/risk_manager.py`
- `common/calculations.py`
- `execution/adapters/brokers.py`
