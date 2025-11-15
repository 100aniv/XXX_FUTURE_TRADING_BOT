# PHASE9-6: 신규 고빈도 스캘핑 전략 V1 설계 및 구현

## 📋 Executive Summary

**목표**: 1분봉 기반 진정한 고빈도 스캘핑 전략 구현  
**상태**: ✅ **V1 뼈대 완료** (튜닝 전 초기 버전)  
**전략 ID**: `scalping` (기존 ID 유지, 로직만 교체)  
**타임프레임**: 1m (1분봉)  
**목표 거래 빈도**: 10~50건/일 (90일 기준 100건 이상)

---

## 🎯 전략 철학 (PHASE9-6)

### 기존 문제점
- PHASE9-5 이전: `scalping` 전략은 실제로는 저빈도 BB 기반 스윙/데이 트레이딩 (0.3건/일)
- PHASE9-5: 기존 로직을 `swing_bb`로 분리

### 새로운 방향
- **타임프레임**: 1m (1분봉, 고빈도)
- **보유 시간**: 짧은 구간 (수분 ~ 30분 이내)
- **RR**: 작은 RR (1.2~1.5, 빠른 청산)
- **빈도**: 높은 거래 빈도 (10~50건/일)

### 핵심 아이디어
빠른 EMA 교차와 RSI 극단 구간을 활용하여:
1. 과매도/과매수 구간에서 반등 포착
2. 모멘텀 패턴으로 신뢰도 강화
3. 작은 RR로 빠르게 진입/청산

---

## 🔧 전략 로직 (Signal Logic)

### LONG 신호 조건

모든 조건을 만족해야 함 (AND 구조):

1. **EMA 교차/정렬**
   - 골든크로스: `fast EMA > slow EMA` (이전 캔들에서는 `<=`)
   - 또는 bullish 정렬: `fast EMA > slow EMA`
   
2. **RSI 극단 (과매도)**
   - RSI < 30 (과매도 구간)
   - 또는 과매도에서 반등 중 (이전 캔들 RSI < 30, 현재 RSI 상승)
   
3. **모멘텀 패턴 (Higher Low)**
   - 최근 N개 캔들(기본 5개)의 저점이 상승 추세
   - 각 저점이 이전 저점의 99.8% 이상
   
4. **거래량 급증**
   - 현재 거래량 > 평균 거래량 * 1.3배

### SHORT 신호 조건

모든 조건을 만족해야 함 (AND 구조):

1. **EMA 교차/정렬**
   - 데드크로스: `fast EMA < slow EMA` (이전 캔들에서는 `>=`)
   - 또는 bearish 정렬: `fast EMA < slow EMA`
   
2. **RSI 극단 (과매수)**
   - RSI > 70 (과매수 구간)
   - 또는 과매수에서 하락 중 (이전 캔들 RSI > 70, 현재 RSI 하락)
   
3. **모멘텀 패턴 (Lower High)**
   - 최근 N개 캔들(기본 5개)의 고점이 하락 추세
   - 각 고점이 이전 고점의 100.2% 이하
   
4. **거래량 급증**
   - 현재 거래량 > 평균 거래량 * 1.3배

---

## 📊 사용 지표

### EMA (Exponential Moving Average)
- **Fast EMA**: 8기간 (빠른 반응)
- **Slow EMA**: 21기간 (중기 추세)
- **용도**: 교차 신호 및 추세 방향 확인

### RSI (Relative Strength Index)
- **기간**: 14
- **과매도**: < 30
- **과매수**: > 70
- **중립**: 40~60
- **용도**: 극단 구간 포착

### 거래량 (Volume)
- **지표**: 단순 이동평균 (SMA)
- **배수**: 1.3x (base.yml), 1.2x (backtest_raw.yml)
- **용도**: 거래량 급증 확인

### ATR (Average True Range)
- **기간**: 14
- **용도**: SL/TP 레벨 계산, 레버리지 계산

---

## 💰 위험 관리 (Risk Management)

### SL/TP 구조

#### 손절 (Stop Loss)
```python
SL = Entry ± (ATR * atr_mult_sl * vol_regime_mult)
```
- **atr_mult_sl**: 0.8 (매우 좁은 SL, 고빈도용)
- **vol_regime_mult**: 변동성 레짐에 따라 조정
  - high_vol: 1.2x
  - neutral: 1.0x
  - low_vol: 0.9x

#### 익절 (Take Profit)
```python
TP = Entry + (Entry - SL) * RR
```
- **RR**: 1.3 (작은 RR, 빠른 청산)

### 포지션 크기 (Position Sizing)
- **Risk per trade**: 0.3% (계좌 대비)
- **레버리지**: ATR 기반 동적 계산 (min~max 범위)

### 최대 보유 시간
- **max_hold_minutes**: 30분
- 30분 이상 보유 시 강제 청산 (구현 예정)

---

## ⚙️ CONFIG 파라미터

### configs/base.yml (strategies.scalping)

```yaml
scalping:
  # 기본 설정
  atr_mult_sl: 0.8           # 매우 좁은 SL (고빈도)
  cooldown_candles: 1        # 쿨다운 최소화
  min_bars_for_signal: 60    # 최소 캔들 수
  timeframe: 1m              # 1분봉
  enabled: true
  
  filters:
    mtf_confirm: false
    regime: false
    volume_spike: false      # 전략 내부에서 체크
    volume_spike_guard: false
    allow_short: true
    session_whitelist: []
  
  # 신호 조건 파라미터
  rsi_oversold: 30           # RSI 과매도 임계값
  rsi_overbought: 70         # RSI 과매수 임계값
  rsi_neutral_min: 40        # RSI 중립 구간 하한
  rsi_neutral_max: 60        # RSI 중립 구간 상한
  momentum_lookback: 5       # 모멘텀 패턴 확인 캔들 수
  volume_mult: 1.3           # 거래량 급증 배수
  
  # 위험 관리
  risk_per_trade: 0.003      # 0.3%
  rr: 1.3                    # 작은 RR
  max_hold_minutes: 30       # 최대 보유 시간
```

### configs/modes/backtest_raw.yml (조건 완화)

```yaml
strategies:
  scalping:
    timeframe: 1m
    cooldown_candles: 0         # 쿨다운 완전 제거
    
    # 조건 완화 (연구용 - 거래 빈도 증가)
    rsi_oversold: 35            # 과매도 임계값 완화 (30 → 35)
    rsi_overbought: 65          # 과매수 임계값 완화 (70 → 65)
    momentum_lookback: 3        # 모멘텀 lookback 축소 (5 → 3)
    volume_mult: 1.2            # 거래량 배수 완화 (1.3 → 1.2)
```

---

## 📝 로깅 구조

### 초기화 로그 (1회만)

```
=============================================================
[SCALPING V2 INIT] 파라미터 로드 완료 (PHASE9-6)
=============================================================
📊 신호 조건:
  - RSI 과매도: < 30
  - RSI 과매수: > 70
  - RSI 중립: 40~60
  - EMA fast: 8, slow: 21
  - 모멘텀 lookback: 5개 캔들
  - 거래량 배수: 1.3x
📈 위험 관리:
  - RR: 1.3
  - SL 배수: 0.8x ATR
  - 최대 보유: 30분
  - 숏 허용: True
=============================================================
```

### 디버그 로그 (100캔들마다)

```
🔍 [SCALPING V2 DEBUG] 신호 조건 체크 (캔들 #100):
  - EMA: fast=95123.45, slow=95000.00 | bullish=True, bearish=False
  - EMA Cross: golden=False, dead=False
  - RSI: 28.5 | oversold_signal=True, overbought_signal=False
  - Momentum: higher_low=True, lower_high=False
  - Volume: 1234567 vs ma=1000000 | spike=True
  ➡️ LONG=True, SHORT=False
```

### 신호 생성 로그

```
✅ [SCALPING V2 SIGNAL] LONG 신호 생성! (캔들 #156)
  - Price: 95123.45 | RSI: 28.5 | EMA_fast: 95123.45 | EMA_slow: 95000.00
  - Reason: RSI 과매도 반등 (28.5), Higher low 패턴, 거래량 급증
```

---

## 🧪 테스트 및 검증

### 필수 데이터
- **1분봉 데이터 필요**: `data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv`
- ⚠️ **현재 미존재**: 5분봉 데이터로 임시 테스트 가능

### 검증 명령어

#### 1. 7일 샘플 테스트 (backtest_raw)
```bash
python scripts/run_backtest.py \
  --mode backtest_raw \
  --strategy scalping \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-10-07 \
  --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**확인 사항**:
- Trades 수 (7일 기준 몇 건 나오는지)
- 로그에 [SCALPING V2 INIT], [SCALPING V2 DEBUG], [SCALPING V2 SIGNAL] 출력 확인

#### 2. 90일 전체 테스트 (backtest_clean)
```bash
python scripts/run_backtest.py \
  --mode backtest_clean \
  --strategy scalping \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-12-30 \
  --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**확인 사항**:
- Trades ≥ 100 여부 (목표 달성 확인)
- Winrate, PF는 참고용 (이번 단계에서는 pass/fail 기준 아님)
- Max DD / Loss > 8%는 "폭발만 안 하면 OK" 수준

---

## ⚠️ 주의사항 및 제한사항

### 이 버전은 튜닝 전 초기 뼈대(V1)입니다

**현재 상태**:
- ✅ 신호 생성 로직 구현 완료
- ✅ CONFIG 파라미터 정의 완료
- ✅ 로깅 구조 구현 완료
- ⚠️ 1분봉 데이터 미확보
- ⚠️ 실제 백테스트 미실행
- ⚠️ 파라미터 튜닝 미진행

**향후 작업 (다음 PHASE)**:
1. **PHASE10**: 베이시안 최적화 / Optuna 튜닝
   - RSI 임계값 튜닝
   - EMA 기간 튜닝
   - 모멘텀 lookback 튜닝
   - RR 최적화
   
2. **PHASE11**: 앙상블 통합
   - 다른 전략(swing_bb 등)과 결합
   - 포트폴리오 매니저 연동
   - 동적 가중치 조정

3. **PHASE12**: 실전 배포
   - 페이퍼 트레이딩
   - 라이브 트레이딩 준비

### 금지 사항
- ❌ `strategies/swing_bb.py` 수정 금지 (기존 전략 유지)
- ❌ 엔진/리스크/포트폴리오 모듈 수정 금지
- ❌ DB 스키마 변경 금지

---

## 📁 변경된 파일 목록

### 신규 작성
- `strategies/scalping.py` (**완전 교체**)

### 수정
- `configs/base.yml` (scalping 섹션 PHASE9-6 파라미터로 교체)
- `configs/modes/backtest_raw.yml` (scalping 섹션 업데이트)

### 변경 없음 (보호됨)
- `strategies/swing_bb.py` (기존 BB 기반 로직 유지)
- `strategies/__init__.py` (등록 구조 유지)
- `signals/signal_generator.py` (변경 없음)
- `execution/*` (변경 금지)

---

## 📈 성능 목표 (참고용)

### 거래 빈도
- **목표**: 10~50건/일
- **90일 기준**: 100건 이상

### 성능 지표 (목표, 강제 조건 아님)
- **Winrate**: 35~45% (참고용)
- **Profit Factor**: 1.1 이상 (참고용)
- **Max DD**: -20% 이내 (폭발 방지)
- **Loss > 8%**: 0건 (폭발 방지)

### 현실적 기대치
- 이 버전은 "뼈대" 단계이므로, 성능보다는 **구조 검증**이 목표
- 거래 빈도가 100건 이상 나오는지 확인
- 폭발하지 않는지 확인 (Max DD < -50%, Loss < 15%)

---

## 🔄 다음 단계 (PHASE10 이후)

### 1. 1분봉 데이터 확보
```bash
# Binance API로 1분봉 다운로드
python scripts/download_data.py --symbol BTCUSDT --timeframe 1m --start-date 2024-10-01 --end-date 2024-12-31
```

### 2. 백테스트 실행 및 분석
- 7일 샘플 테스트
- 90일 전체 테스트
- 결과 분석 및 스코어카드 생성

### 3. 파라미터 튜닝 (PHASE10)
- 베이시안 최적화로 RSI/EMA/모멘텀 파라미터 튜닝
- Optuna로 RR/SL 최적화
- 거래 빈도 vs 성능 트레이드오프 분석

### 4. 앙상블 통합 (PHASE11)
- swing_bb와 결합하여 다양한 타임프레임 커버
- 포트폴리오 매니저와 연동
- 동적 가중치 조정

---

## 💡 핵심 설계 결정 (Design Decisions)

### 1. EMA 교차 vs BB 반등
- **선택**: EMA 교차
- **이유**: 1분봉에서 BB 반등은 노이즈가 많음, EMA 교차가 더 명확

### 2. RSI 극단 구간
- **선택**: RSI < 30 (과매도), RSI > 70 (과매수)
- **이유**: 극단 구간에서 반등/조정 포착, 스캘핑에 적합

### 3. 모멘텀 패턴 (Higher Low / Lower High)
- **선택**: 최근 N개 캔들의 저점/고점 추세
- **이유**: 신뢰도 강화, false signal 감소

### 4. 작은 RR (1.2~1.5)
- **선택**: RR 1.3
- **이유**: 고빈도 전략은 작은 RR로 빠르게 청산, 승률보다는 빈도

### 5. 최대 보유 시간 30분
- **선택**: max_hold_minutes = 30
- **이유**: 스캘핑은 빠른 청산, 30분 이상 보유는 "스윙"

---

## 📚 참고 자료

### 관련 문서
- `docs/PHASE9/PHASE9-5_STRATEGY_SEPARATION.md` (전략 분리 완료)
- `docs/PHASE9/PHASE9-3.4_SCALPING_90D_BASELINE.md` (기존 scalping 결과)
- `docs/PHASE8/PHASE8_MASTER_PLAN.md` (전체 구조)

### 관련 코드
- `strategies/scalping.py` (이 전략)
- `strategies/swing_bb.py` (기존 BB 기반 전략)
- `configs/base.yml` (전략 파라미터)
- `configs/modes/backtest_raw.yml` (연구용 설정)

---

**Status**: ✅ **V1 뼈대 완료** (튜닝 전)  
**Next**: PHASE10 (베이시안 튜닝 / Optuna)  
**Generated**: 2025-11-15  
**Version**: Scalping V2 (PHASE9-6)
