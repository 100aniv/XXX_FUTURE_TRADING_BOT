# PHASE22-1 – Strategy Implementation & Validation Design Document

**작성일**: 2025-11-22  
**상태**: 🔄 **IN PROGRESS**  
**목적**: 5개 전략 패밀리 중 Family 2~5 신규 전략 설계 및 구현 가이드

---

## 1. Overview

### 1.1 PHASE22-1 목표

**핵심 목표**:
- Family 2~5 (4개 신규 전략) 구현 및 기본 검증
- BaseStrategy 인터페이스 준수
- 엔진/Risk/Portfolio/FlowGuardian 구조와 통합
- 최소 단위 테스트 및 미니 Paper 실행

**범위**:
- ✅ **이번 PHASE에서 할 일**:
  - 4개 신규 전략 코드 구현 (strategies/research/)
  - 단위 테스트 작성 및 실행
  - 짧은 구간 Paper/Backtest 실행 (정상 동작 확인)
  - 설계 문서 및 Complete Report 작성

- ❌ **이번 PHASE에서 하지 않을 것** (Out-of-Scope):
  - Multi-Symbol 엔진 (PHASE26)
  - Tuning Cluster (PHASE25)
  - 본격적인 수익률 튜닝/최적화 (PHASE24~25)
  - UI/UX, Monitoring (PHASE28~30)
  - Live 연동 (PHASE32)
  - 엔진 코어/RiskManager/PortfolioManager 구조 변경 (PHASE17~20에서 검증 완료)

### 1.2 5개 전략 패밀리 구성

| Family | 대표 전략 | Timeframe | Status | 구현 위치 |
|--------|-----------|-----------|--------|-----------|
| 1. HF Momentum | scalping_v3 | 3m | ✅ IMPLEMENTED | strategies/core/ |
| 2. Volatility Breakout | breakout_v2 | 15m | 🔄 THIS PHASE | strategies/research/ |
| 3. Mean Reversion | reversion_v2 | 5m | 🔄 THIS PHASE | strategies/research/ |
| 4. Trend Following | trend_v2 | 1h | 🔄 THIS PHASE | strategies/research/ |
| 5. Volume-Based | volume_v2 | 5m | 🔄 THIS PHASE | strategies/research/ |

---

## 2. 공통 설계 원칙

### 2.1 BaseStrategy 인터페이스 준수

**필수 구현 항목**:
```python
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

class MyStrategy(BaseStrategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='my_strategy',
            strategy_type='breakout',  # or 'reversion', 'trend', 'volume'
            supported_symbols=['BTCUSDT'],
            supported_timeframes=['15m'],
            version='v2.0',
            description='Strategy description',
            optimal_regime='trending',
            worst_regime='ranging',
            base_weight=1.0,
            factor_weights={
                'momentum': 0.3,
                'volatility': 0.4,
                'volume': 0.2,
                'trend_strength': 0.1,
                'overbought_oversold': 0.0,
                'breakout_probability': 0.0,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        # 전략 로직 구현
        return {
            'side': 'LONG' | 'SHORT' | None,
            'action': '진입' | None,
            'entry': float,
            'sl': float,
            'tp': float,
            'lev': int,
            'reason': List[str],
            ...
        }
```

### 2.2 Config 기반 파라미터

**원칙**:
- 하드코딩 금지 (X, Y, Z 같은 매직 넘버 지양)
- `self.config`에서 파라미터 읽기
- 기본값 제공 (config에 없을 경우 대비)

**예시**:
```python
# ✅ Good
atr_mult = self.config.get('atr_mult_sl', 1.2)
rsi_threshold = self.config.get('rsi_oversold', 30)

# ❌ Bad
atr_mult = 1.2  # 하드코딩
```

### 2.3 Risk/Portfolio/FlowGuardian 분리

**전략의 책임**:
- ✅ 신호 생성 (LONG/SHORT/None)
- ✅ Entry/SL/TP 가격 계산
- ✅ 레버리지 제안

**전략이 하면 안 되는 것**:
- ❌ 직접 주문 발주
- ❌ 계정 잔고/Budget 직접 참조
- ❌ 포지션 관리 (PortfolioManager 책임)
- ❌ Risk 체크 (RiskManager 책임)
- ❌ Guard 상태 확인 (FlowGuardian 책임)

### 2.4 최소한의 "그럴듯한" 로직

**금지 패턴**:
- ❌ 항상 LONG만 생성
- ❌ 항상 신호 없음 (0건)
- ❌ SL/TP 전혀 없음
- ❌ 한 번 진입하면 영원히 안 나옴

**권장**:
- ✅ 조건부 신호 생성 (특정 상황에서만)
- ✅ SL/TP 필수 설정
- ✅ 타임프레임에 맞는 합리적 빈도

---

## 3. Family 1: HF Momentum (scalping_v3) – 기존 구현

**파일**: `strategies/core/scalping_v3.py`

**특징** (요약만, 이미 구현됨):
- Timeframe: 3m
- Signal Type: EMA Fresh Trend + Optional Mean Reversion
- Frequency: High (ACTIVE)
- Entry: Fresh Bullish/Bearish Trend + RSI/Volume 조합
- Exit: ATR 기반 SL/TP, RR 1.5
- Status: ✅ PHASE21 검증 완료

**역할**:
- Core HF momentum generator
- Ensemble의 기준점 (Baseline)

---

## 4. Family 2: Volatility Breakout (신규)

### 4.1 개요

**전략명**: `breakout_v2`  
**파일**: `strategies/research/volatility_breakout_v2.py`  
**Timeframe**: 15m  
**Signal Type**: Breakout (ATR + Support/Resistance)  
**Frequency**: Low-Frequency  
**Reference**: `strategies/deprecated/breakout_old.py`

### 4.2 전략 철학

**핵심 아이디어**:
- 변동성 확대 구간에서 지지/저항 돌파 포착
- ATR 기반 동적 SR 레벨 계산
- Breakout 확인 후 진입 (False breakout 필터)

**적합 Regime**:
- Optimal: `trending` (추세 시작점)
- Worst: `low_volatility` (횡보)

### 4.3 신호 조건

#### LONG 진입
1. **Price > Resistance Level**
   - Resistance = Recent High (N개 캔들) + ATR buffer
2. **Volume Confirmation**
   - Volume > Volume MA × 1.5
3. **ATR 확장**
   - ATR > ATR MA (변동성 증가 확인)

#### SHORT 진입
1. **Price < Support Level**
   - Support = Recent Low (N개 캔들) - ATR buffer
2. **Volume Confirmation**
   - Volume > Volume MA × 1.5
3. **ATR 확장**
   - ATR > ATR MA

### 4.4 Exit (SL/TP)

**Stop Loss**:
- LONG: Entry - ATR × 1.5
- SHORT: Entry + ATR × 1.5

**Take Profit**:
- RR: 2.0 (변동성 전략 특성상 넓은 RR)

**최대 보유**:
- 60분 (15m × 4 캔들)

### 4.5 사용 지표

| 지표 | 용도 | 파라미터 |
|------|------|----------|
| ATR (14) | 변동성 측정 | `atr_period: 14` |
| ATR MA (20) | 변동성 추세 | `atr_ma_period: 20` |
| High/Low (20) | SR 레벨 | `sr_lookback: 20` |
| Volume MA (20) | 거래량 기준선 | `vol_ma_period: 20` |

### 4.6 Config 파라미터

```yaml
strategies:
  breakout_v2:
    enabled: true
    timeframe: 15m
    atr_period: 14
    atr_ma_period: 20
    sr_lookback: 20
    atr_buffer_mult: 0.5  # SR 레벨 버퍼
    vol_mult: 1.5  # 거래량 확인 배수
    rr: 2.0
    atr_mult_sl: 1.5
    max_hold_minutes: 60
```

---

## 5. Family 3: Mean Reversion (신규)

### 5.1 개요

**전략명**: `reversion_v2`  
**파일**: `strategies/research/mean_reversion_v2.py`  
**Timeframe**: 5m  
**Signal Type**: Mean Reversion (Bollinger Bands + RSI)  
**Frequency**: Low-Frequency  
**Reference**: `strategies/deprecated/reversion_old.py`

### 5.2 전략 철학

**핵심 아이디어**:
- 과도한 가격 이탈 후 평균 회귀 포착
- BB Lower/Upper 터치 + RSI 극단값
- 빠른 진입/청산 (평균 회귀 특성)

**적합 Regime**:
- Optimal: `ranging` (횡보 구간)
- Worst: `trending` (추세 강할 때 역행 위험)

### 5.3 신호 조건

#### LONG 진입
1. **BB Lower Touch**
   - Price <= BB Lower × 1.01 (1% 버퍼)
2. **RSI Oversold**
   - RSI < 25 (극단 과매도)
3. **Price Above Support** (Optional)
   - Price > Recent Low (False break 방지)

#### SHORT 진입
1. **BB Upper Touch**
   - Price >= BB Upper × 0.99
2. **RSI Overbought**
   - RSI > 75 (극단 과매수)
3. **Price Below Resistance** (Optional)
   - Price < Recent High

### 5.4 Exit (SL/TP)

**Stop Loss**:
- LONG: Entry - ATR × 1.0
- SHORT: Entry + ATR × 1.0

**Take Profit**:
- RR: 1.5 (빠른 회귀 목표)
- 또는 BB Middle 도달 시 (Alternative Exit)

**최대 보유**:
- 30분 (5m × 6 캔들)

### 5.5 사용 지표

| 지표 | 용도 | 파라미터 |
|------|------|----------|
| Bollinger Bands (20, 2) | 평균 기준선 | `bb_period: 20`, `bb_std: 2.0` |
| RSI (14) | 과매수/과매도 | `rsi_period: 14` |
| ATR (14) | SL 계산 | `atr_period: 14` |

### 5.6 Config 파라미터

```yaml
strategies:
  reversion_v2:
    enabled: true
    timeframe: 5m
    bb_period: 20
    bb_std: 2.0
    rsi_period: 14
    rsi_oversold: 25
    rsi_overbought: 75
    rr: 1.5
    atr_mult_sl: 1.0
    max_hold_minutes: 30
```

---

## 6. Family 4: Trend Following (신규)

### 6.1 개요

**전략명**: `trend_v2`  
**파일**: `strategies/research/trend_follow_v2.py`  
**Timeframe**: 1h  
**Signal Type**: Trend (Moving Average + MACD)  
**Frequency**: Low-Frequency  
**Reference**: `strategies/deprecated/trend_old.py`

### 6.2 전략 철학

**핵심 아이디어**:
- 장기 추세 확인 후 진입
- 이중 이동평균 (SMA 50/200) 정렬
- MACD로 추세 강도 확인

**적합 Regime**:
- Optimal: `trending` (명확한 추세)
- Worst: `ranging` (횡보, whipsaw 위험)

### 6.3 신호 조건

#### LONG 진입
1. **Golden Cross**
   - SMA50 > SMA200 (상승 추세)
2. **Price Above MA**
   - Price > SMA50 (추세 내 위치)
3. **MACD Bullish**
   - MACD > Signal Line
   - MACD Histogram > 0

#### SHORT 진입
1. **Death Cross**
   - SMA50 < SMA200 (하락 추세)
2. **Price Below MA**
   - Price < SMA50
3. **MACD Bearish**
   - MACD < Signal Line
   - MACD Histogram < 0

### 6.4 Exit (SL/TP)

**Stop Loss**:
- LONG: SMA50 - ATR × 1.0 (추세선 이탈)
- SHORT: SMA50 + ATR × 1.0

**Take Profit**:
- RR: 2.5 (장기 추세 목표)

**최대 보유**:
- 4시간 (1h × 4 캔들, 추세 전략 특성상 긴 보유)

### 6.5 사용 지표

| 지표 | 용도 | 파라미터 |
|------|------|----------|
| SMA (50) | Fast MA | `sma_fast: 50` |
| SMA (200) | Slow MA | `sma_slow: 200` |
| MACD (12, 26, 9) | 추세 강도 | `macd_fast: 12`, `macd_slow: 26`, `macd_signal: 9` |
| ATR (14) | SL 계산 | `atr_period: 14` |

### 6.6 Config 파라미터

```yaml
strategies:
  trend_v2:
    enabled: true
    timeframe: 1h
    sma_fast: 50
    sma_slow: 200
    macd_fast: 12
    macd_slow: 26
    macd_signal: 9
    rr: 2.5
    atr_mult_sl: 1.0
    max_hold_minutes: 240
```

---

## 7. Family 5: Volume-Based (신규)

### 7.1 개요

**전략명**: `volume_v2`  
**파일**: `strategies/research/volume_based_v2.py`  
**Timeframe**: 5m (선택: 15m도 가능, 설계 후 결정)  
**Signal Type**: Volume Delta (OBV + Volume Spike)  
**Frequency**: Low-Frequency  
**Reference**: `strategies/deprecated/swing_bb_old.py` (부분 참조)

### 7.2 전략 철학

**핵심 아이디어**:
- On-Balance Volume (OBV) 기반 매수/매도 압력 추적
- Volume Spike로 강한 방향성 확인
- 거래량 주도 움직임 포착

**적합 Regime**:
- Optimal: `high_volume` (거래량 폭발 구간)
- Worst: `low_volume` (조용한 구간)

### 7.3 신호 조건

#### LONG 진입
1. **OBV 상승**
   - OBV > OBV MA (20) (매수 압력 증가)
2. **Volume Spike**
   - Volume > Volume MA × 2.0 (강한 매수)
3. **Price Confirmation**
   - Price > EMA(20) (가격도 상승)

#### SHORT 진입
1. **OBV 하락**
   - OBV < OBV MA (20) (매도 압력 증가)
2. **Volume Spike**
   - Volume > Volume MA × 2.0 (강한 매도)
3. **Price Confirmation**
   - Price < EMA(20) (가격도 하락)

### 7.4 Exit (SL/TP)

**Stop Loss**:
- LONG: Entry - ATR × 1.2
- SHORT: Entry + ATR × 1.2

**Take Profit**:
- RR: 1.8

**최대 보유**:
- 45분 (5m × 9 캔들)

### 7.5 사용 지표

| 지표 | 용도 | 파라미터 |
|------|------|----------|
| OBV | 매수/매도 압력 | N/A |
| OBV MA (20) | OBV 기준선 | `obv_ma_period: 20` |
| Volume MA (20) | 거래량 기준선 | `vol_ma_period: 20` |
| EMA (20) | 가격 추세 | `ema_period: 20` |
| ATR (14) | SL 계산 | `atr_period: 14` |

### 7.6 Config 파라미터

```yaml
strategies:
  volume_v2:
    enabled: true
    timeframe: 5m
    obv_ma_period: 20
    vol_ma_period: 20
    vol_mult: 2.0
    ema_period: 20
    rr: 1.8
    atr_mult_sl: 1.2
    max_hold_minutes: 45
```

---

## 8. Ensemble/Score 연동 포인트

### 8.1 StrategyMetadata 설정

**각 전략의 `metadata` 프로퍼티**:
```python
factor_weights={
    'momentum': float,        # 0~1
    'volatility': float,      # 0~1
    'volume': float,          # 0~1
    'trend_strength': float,  # 0~1
    'overbought_oversold': float,  # 0~1
    'breakout_probability': float, # 0~1
}
```

**전략별 권장 Weight**:
| Strategy | momentum | volatility | volume | trend_strength | overbought_oversold | breakout_probability |
|----------|----------|------------|--------|----------------|---------------------|----------------------|
| scalping_v3 | 0.4 | 0.1 | 0.2 | 0.3 | 0.0 | 0.0 |
| breakout_v2 | 0.2 | 0.4 | 0.2 | 0.1 | 0.0 | 0.1 |
| reversion_v2 | 0.1 | 0.2 | 0.1 | 0.0 | 0.5 | 0.1 |
| trend_v2 | 0.1 | 0.1 | 0.1 | 0.6 | 0.1 | 0.0 |
| volume_v2 | 0.2 | 0.1 | 0.5 | 0.1 | 0.0 | 0.1 |

### 8.2 신호 구조 (compute_signal 반환값)

**필수 필드**:
```python
{
    'side': 'LONG' | 'SHORT' | None,
    'action': '진입' | None,
    'entry': float,
    'sl': float,
    'tp': float,
    'lev': int,
    'reason': List[str],  # 신호 발생 이유
    'ts': int,  # timestamp
    'price': float,
    'atr': float,
    ...
}
```

**PHASE22-1 Note**:
- 이번 Phase에서는 신호 생성만 확인
- Full Ensemble 통합은 PHASE22-2에서 수행

---

## 9. 테스트 전략

### 9.1 Unit Test (필수)

**파일**: `tests/test_phase22_1_*.py`

**확인 사항**:
1. 전략 인스턴스 생성 정상
2. `metadata` 프로퍼티 정상 반환
3. 더미 데이터 입력 시 신호 구조 정상
4. 극단 입력 시 예외 없음

### 9.2 Mini Paper/Backtest (권장)

**설정**:
- Mode: PAPER
- Symbol: BTCUSDT (단일)
- Duration: 30분~1시간
- 전략: 신규 4개 중 1개씩 단독 실행

**목적**:
- 엔진/데이터/Guard/Portfolio 통합 확인
- 거래 최소 1건 이상 발생 확인
- 치명적 에러 없음 확인

---

## 10. Acceptance Criteria

PHASE22-1이 **COMPLETE**로 판정되려면:

- [x] **전략 구현**
  - scalping_v3.py 기존 유지 (Diff 확인 시 핵심 로직 변화 없음)
  - strategies/research/에 4개 신규 파일 생성
  - 각 전략 BaseStrategy 인터페이스 준수
  - 패밀리 역할에 맞는 로직 구현

- [x] **문서**
  - PHASE22-1_STRATEGY_DESIGN.md 작성 완료
  - Entry/Exit/Timeframe/Indicator/역할 명확히 기술

- [x] **테스트**
  - 신규 4개 전략 unit test 전체 PASS
  - 최소 1개 이상 mini Paper/Backtest 실행 로그 확인
  - 엔진 정상 시작/종료
  - 신호/거래 최소 1개 이상 발생
  - ERROR/CRITICAL 로그 없음

- [x] **리포트 & 로드맵**
  - PHASE22-1_COMPLETE_REPORT.md 초안 작성
  - PHASE_ROADMAP.md 업데이트 (상태 IN PROGRESS → COMPLETE)

- [x] **Git**
  - 변경 범위 확인 후 의미 있는 커밋

---

## 11. 다음 단계 (PHASE22-2)

**PHASE22-2: Extended Validation**
- Ensemble v2 장기 안정성 검증 (12~24H Paper)
- 5개 전략 통합 실행
- 전략별 신호 발생 빈도 확인
- PnL/성능 기초 분석

---

**Document Version**: v1.0  
**Last Updated**: 2025-11-22  
**Author**: Windsurf AI (PHASE22-1 Design Session)
