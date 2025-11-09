# PHASE7-1 마스터 플랜: 긴급 패치 (수수료 + TP/SL OHLC)

## 배경/의도 (Overview)

1,859건 거래 분석 결과 **치명적 오류 3개** 발견:
1. **수수료 미반영**: PnL 계산에서 0.08% 완전 누락
2. **TP/SL 로직 오류**: 손실을 TP1으로 기록 (63건+)
3. **Extreme Loss**: -131.24% 발생 (임계값 무용)

Live 운영 불가 상태. 긴급 패치로 **최소 조건** 달성.

## 목표 (Goals)

- 수수료 0.08% PnL 반영
- OHLC High/Low로 정확한 SL 체크
- Extreme Loss -50% → -20%
- Paper 24h 검증: 8% 초과 0건

## 범위 (Scope, In)

### 1. 수수료 반영 (2h)
- **파일**: `execution/engine.py::calculate_pnl()`
- **변경**: 진입+청산 수수료 차감
- **config**: `fees.taker: 0.0004`

### 2. TP/SL OHLC 체크 (3h)
- **파일**: `execution/position_tracker.py::check_tpsl_with_partial()`
- **변경**: 
  - 파라미터 `candle: Dict` 추가
  - LONG: `low <= sl` 체크
  - SHORT: `high >= sl` 체크
  - **SL 우선 체크**
- **엔진**: `engine.py`에서 캔들 전달

### 3. Extreme Loss (30m)
- **파일**: `position_tracker.py`
- **변경**: `-50.0` → `-20.0`

## 제외 (Out-of-Scope)

- 전략 로직, TP/TP2 비율 조정
- Graceful Shutdown, 중복 진입 방지
- 펀딩피 반영

## 영향 파일

**필수**:
- `execution/engine.py`
- `execution/position_tracker.py`
- `config.yml`

**테스트**:
- `tests/execution/test_engine.py`
- `tests/execution/test_position_tracker.py`

**문서**:
- `docs/PHASE7/PHASE7-1_IMPLEMENTATION_LOG.md`

## 설정 키

```yaml
fees:
  taker: 0.0004  # 0.04%

risk:
  extreme_loss_threshold: -20.0

exits:
  use_ohlc_check: true
  sl_priority: "BEFORE_TP"
```

## 구현 상세

### calculate_pnl 수정

```python
def calculate_pnl(position: Dict, exit_price: float, fee_rate: float = 0.0004) -> float:
    entry, qty, side = position["entry"], position["qty"], position["side"]
    
    # Gross PnL
    gross_pnl = (exit_price - entry) * qty if side == "LONG" else (entry - exit_price) * qty
    
    # 수수료
    total_fee = (entry + exit_price) * qty * fee_rate
    
    # Net PnL
    return gross_pnl - total_fee
```

### check_tpsl_with_partial 수정

```python
def check_tpsl_with_partial(self, position, current_price, atr=None, candle=None):
    # 1. SL 우선 체크 (OHLC)
    if candle and position.get('sl'):
        sl = position['sl']
        if position['side'] == 'SHORT' and candle['high'] >= sl:
            return True, None, 'SL'
        elif position['side'] == 'LONG' and candle['low'] <= sl:
            return True, None, 'SL'
    
    # 2. Extreme Loss -20%
    pnl_pct = ((current_price - position['entry']) / position['entry']) * 100
    if position['side'] == 'SHORT':
        pnl_pct = -pnl_pct
    if pnl_pct < -20.0:
        return True, None, 'EXTREME_LOSS'
    
    # 3. TP 체크
    # ...
```

## 금지 사항

❌ 하드코딩: `fee = 0.0004` → `config.get('fees', {}).get('taker', 0.0004)`  
❌ 중복 함수: `calculate_pnl_with_fees()` 생성 금지  
❌ 과도한 리팩토링: 최소 변경만

## 수용 기준

### 필수

- [ ] Paper 100건: 모든 PnL 수수료 차감
- [ ] 0~0.1% 수익: 수수료 후 손실 전환
- [ ] 24h Paper: 8% 초과 손실 **0건**
- [ ] 24h Paper: TP1 손실 **0건**
- [ ] Extreme Loss -20% 도달 시 청산

### 선택

- [ ] OHLC 체크 지연 < 10ms
- [ ] Paper/Live 파리티
- [ ] Backtest 모드 유지

## 테스트 플랜

### 단위 테스트

```python
# tests/execution/test_engine.py
def test_calculate_pnl_with_fees():
    position = {'entry': 100.0, 'qty': 1.0, 'side': 'LONG'}
    pnl = calculate_pnl(position, 100.10, fee_rate=0.0004)
    # 0.1% 수익 - 0.08% 수수료 = 0.02%
    assert 0.01 < pnl < 0.03

def test_calculate_pnl_negative_after_fees():
    position = {'entry': 100.0, 'qty': 1.0, 'side': 'SHORT'}
    pnl = calculate_pnl(position, 99.95, fee_rate=0.0004)
    # 0.05% 수익 - 0.08% 수수료 = -0.03%
    assert pnl < 0

# tests/execution/test_position_tracker.py
def test_sl_check_ohlc_high_short():
    position = {'entry': 100.0, 'sl': 108.0, 'side': 'SHORT', 'tp1': 95.0}
    candle = {'high': 110.0, 'low': 94.0, 'close': 95.0}
    should_action, qty, reason = tracker.check_tpsl_with_partial(position, 95.0, candle=candle)
    assert reason == 'SL'  # TP1 아님!

def test_extreme_loss_20pct():
    position = {'entry': 100.0, 'side': 'LONG', 'sl': 92.0}
    should_action, qty, reason = tracker.check_tpsl_with_partial(position, 80.0)
    assert reason == 'EXTREME_LOSS'
```

### 통합 테스트

```sql
-- 24시간 Paper 후 검증
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN pnl_pct < -8 THEN 1 END) as over_8pct,  -- 0건 목표
  COUNT(CASE WHEN exit_reason='TP1' AND pnl_pct < 0 THEN 1 END) as tp1_loss  -- 0건 목표
FROM trading.trades 
WHERE mode='paper' AND ts_open >= NOW() - INTERVAL '24 hours';
```

## 체크리스트

### 구현

- [ ] `calculate_pnl()` 수수료 로직
- [ ] 모든 호출부 `fee_rate` 파라미터
- [ ] `check_tpsl_with_partial()` `candle` 파라미터
- [ ] OHLC SL 체크 (HIGH/LOW)
- [ ] SL 우선 체크
- [ ] Extreme Loss -20%
- [ ] config.yml 키 추가

### 테스트

- [ ] 단위 테스트 (수수료/OHLC/Extreme)
- [ ] Paper 24h 실행
- [ ] 8% 초과 0건
- [ ] TP1 손실 0건
- [ ] pre-commit 통과
- [ ] coverage > 85%

### 문서

- [ ] IMPLEMENTATION_LOG.md
- [ ] CRITICAL_SYSTEM_ANALYSIS 업데이트

## 배포/롤백

- Paper 24h 검증 → Live 소액 테스트
- 이상 시 git revert

## 리스크/완화

- OHLC 데이터 없으면? → Close 가격으로 fallback
- 수수료율 변경? → config.yml 동적 수정
- 성능 저하? → 프로파일링 후 최적화

## 릴리즈 노트

PHASE7-1: 수수료 반영 + OHLC SL 체크로 Live 운영 최소 조건 달성. 8% 초과 손실 0건, TP1 손실 0건 목표.
