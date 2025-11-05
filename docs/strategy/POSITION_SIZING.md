# 📊 포지션 사이징 & 리스크 관리

**작성일**: 2025-10-18  
**버전**: v1.0

---

## 📋 목차

1. [개요](#개요)
2. [PositionSizer (포지션 사이징)](#positionsizer)
3. [RiskManager (리스크 관리)](#riskmanager)
4. [통합 흐름](#통합-흐름)
5. [환경변수 설정](#환경변수-설정)

---

## 개요

### 위치
```python
trading_executor.py
├─ class TradingExecutor      # 주문 실행
├─ class PositionSizer        # 포지션 사이징 ⭐
├─ class RiskManager          # 리스크 관리 ⭐
└─ class PositionTracker      # 포지션 추적
```

### 실밥 리팩토링
- **현재**: 하나의 파일에 통합
- **향후**: `execution/` 폴더로 분리 가능
- **주석**: "리팩토링 시: execution/XXX.py로 분리" 표시

---

## PositionSizer

### 책임
- 리스크 기반 기본 계산 (Risk-per-trade)
- 신호 품질 가중치 적용 (confidence)
- 포지션 가치 한도 적용
- 최소 수량 체크

### 사용법

```python
from trading_executor import PositionSizer

sizer = PositionSizer()

signal = {
    'symbol': 'BTCUSDT',
    'entry_price': 50000.0,
    'sl_price': 49000.0,
    'confidence': 0.85  # 선택 (0~1)
}

qty, metadata = sizer.calculate(signal)

print(f"수량: {qty}")
print(f"품질 가중치: {metadata['quality_weight']}")
print(f"포지션 가치: ${metadata['position_value']}")
```

### 계산 로직

1. **기본 리스크 계산**
   ```python
   risk_usdt = equity * risk_per_trade  # 예: 10000 * 0.01 = 100
   stop_distance = abs(entry - sl)      # 예: 50000 - 49000 = 1000
   base_qty = risk_usdt / stop_distance # 예: 100 / 1000 = 0.1
   ```

2. **품질 가중치 적용**
   ```python
   confidence = 0.85
   weight = 0.7 + (0.85 - 0.5) * 1.2 = 1.12
   adjusted_qty = 0.1 * 1.12 = 0.112
   ```

3. **한도 적용**
   ```python
   if position_value > max_position_value:
       adjusted_qty = max_position_value / entry
   ```

### 환경변수

```bash
EQUITY_USDT=10000                  # 자산
RISK_PER_TRADE=0.01                # 거래당 리스크 (1%)
QUALITY_WEIGHT_MIN=0.7             # 최소 가중치
QUALITY_WEIGHT_MAX=1.3             # 최대 가중치
MAX_POSITION_VALUE=5000            # 최대 포지션 가치
MIN_POSITION_VALUE=10              # 최소 포지션 가치
```

---

## RiskManager

### 책임
- 일일 손실 한도 체크
- 동시 포지션 수 제한
- 심볼별 노출 한도
- 순노출 한도 (향후)

### 사용법

```python
from trading_executor import RiskManager

risk = RiskManager()

# 주문 전 체크
allowed, reason = risk.check_order(signal, qty)
if not allowed:
    print(f"주문 거부: {reason}")
    return

# 포지션 추가
risk.add_position('BTCUSDT', position_value=1000.0)

# PnL 업데이트
risk.update_daily_pnl(pnl=-50.0)

# 포지션 제거
risk.remove_position('BTCUSDT', position_value=1000.0)
```

### 체크 로직

1. **일일 손실 한도**
   ```python
   if abs(current_daily_loss) >= daily_loss_limit:
       return False, "일일 손실 한도 초과"
   ```

2. **동시 포지션 수**
   ```python
   if active_positions_count >= max_positions:
       return False, "동시 포지션 한도 도달"
   ```

3. **심볼별 한도**
   ```python
   max_per_symbol = equity * max_exposure_per_symbol_pct
   if current_exposure + position_value > max_per_symbol:
       return False, "심볼별 한도 초과"
   ```

### 환경변수

```bash
DAILY_LOSS_LIMIT_PCT=0.03          # 일일 손실 한도 (3%)
MAX_CONCURRENT_POSITIONS=5         # 동시 포지션 수
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3    # 심볼별 최대 노출 (30%)
```

---

## 통합 흐름

### TradingExecutor.execute_order()

```python
def execute_order(self, signal):
    # 1️⃣ 포지션 사이징
    qty, sizing_meta = self.position_sizer.calculate(signal)
    if qty <= 0:
        return None
    
    # 2️⃣ 리스크 체크
    allowed, reason = self.risk_manager.check_order(signal, qty)
    if not allowed:
        logger.warning(f"리스크 체크 실패: {reason}")
        return None
    
    # 3️⃣ 주문 실행 (BACKTEST/PAPER/LIVE)
    result = self._execute_by_mode(signal, qty)
    
    # 4️⃣ 성공 시 업데이트
    if result['status'] == 'FILLED':
        self.risk_manager.add_position(symbol, position_value)
    
    return result
```

---

## 환경변수 설정

### .env 파일

```bash
# === 포지션 사이징 ===
EQUITY_USDT=10000
RISK_PER_TRADE=0.01
QUALITY_WEIGHT_MIN=0.7
QUALITY_WEIGHT_MAX=1.3
MAX_POSITION_VALUE=5000
MIN_POSITION_VALUE=10

# === 리스크 관리 ===
DAILY_LOSS_LIMIT_PCT=0.03
MAX_CONCURRENT_POSITIONS=5
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3
```

### 안전한 초기값 (보수적)

```bash
RISK_PER_TRADE=0.005              # 0.5% (안전)
DAILY_LOSS_LIMIT_PCT=0.02         # 2% (보수적)
MAX_CONCURRENT_POSITIONS=3        # 3개 (제한적)
```

---

## 향후 개선 사항

### Phase 2: 고급 사이징

1. **Kelly Criterion**
   ```python
   def _half_kelly(self, signal):
       p = signal.get('win_rate', 0.6)
       R = signal.get('reward_risk', 2.0)
       f_star = p - (1-p)/R
       return max(0.0, f_star) * 0.5
   ```

2. **ATR 기반 조절**
   ```python
   atr = signal.get('atr', 0)
   volatility_factor = min(1.0, baseline_atr / atr)
   adjusted_qty *= volatility_factor
   ```

3. **컨텍스트 스케일링**
   ```python
   if context['regime'] == 'crash':
       qty *= 0.5
   if context['liquidity'] == 'thin':
       qty *= 0.7
   ```

### Phase 3: DB 연동

- RiskManager 상태를 DB에 저장
- 포지션 추적과 연동
- 실시간 잔고 조회 (Binance API)

---

## 참고 문서

- [Trading Executor](./TRADING_EXECUTOR.md)
- [Refactoring Guide](./REFACTORING.md)
- [CHANGELOG](../CHANGELOG.md)

---

**Last Updated:** 2025-10-18  
**Status:** ✅ PositionSizer + RiskManager 추가 완료
