# PHASE27-5: Baseline 전략 스펙 및 메트릭 정의

**작성일**: 2025-12-04  
**상태**: 🟦 **IN PROGRESS**  
**목표**: Baseline+ADX 전략의 역할, 정량 스펙, 백테스트 메트릭 1차 정의

---

## Executive Summary

**btc5m_baseline_v1**은 PHASE27에서 설계된 **저변동성/레인지 구간 Mean-Reversion 스캘핑 전략**입니다.  
이 문서는 전략의 역할, 정량 스펙, 향후 백테스트 메트릭을 정의하여 **전략 평가 기준선**을 제공합니다.

---

## 1. 전략 역할 정의

### 1.1 전략 개요

| 항목 | 내용 |
|------|------|
| **전략 이름** | `btc5m_baseline_v1` |
| **목적** | 저변동성/레인지 구간의 Mean-Reversion 스캘핑 |
| **심볼** | BTCUSDT (단일 심볼) |
| **타임프레임** | 5m |
| **레짐 구분** | ADX 기반 Range/Trend 구분 |
| **진입 로직** | OR 기반 (여러 조건 중 하나만 만족) |
| **위험 관리** | ATR 기반 SL, RR 1.5, 최대 보유 60분 |

### 1.2 설계 철학

**PHASE27-2에서 정의된 설계 원칙**:

1. **단순함**: 조건 2-3개 이하, AND 최소화
2. **현실성**: 퍼센타일 기반 threshold (절대값 X)
3. **빈도 우선**: False Positive 감수, Dropout 방지 우선
4. **OR 로직**: 여러 조건 중 하나만 만족해도 신호
5. **레짐 적응**: ADX 기반 Range/Trend 구분

### 1.3 전략 역할

**Baseline 전략의 역할**:
- **신호 발생 검증**: 엔진/파이프라인이 정상 작동하는지 확인하는 기준선
- **저변동성 대응**: 2024년 11~12월 저변동성 구간에서도 신호 발생
- **Mean-Reversion**: RSI/BB 기반 과매수/과매도 구간 역추세 진입
- **레짐 적응**: ADX로 Range/Trend 구분, 각 레짐에 맞는 조건 적용

**Baseline이 아닌 것**:
- ❌ 고수익 추구 전략 (수익성은 2차 목표)
- ❌ 추세 추종 전략 (Range 구간 우선)
- ❌ 멀티 심볼 전략 (단일 심볼 집중)

---

## 2. 정량 스펙 (PHASE27-4 기준)

### 2.1 신호 빈도

| 항목 | 목표 범위 | 현재 실적 (PHASE27-4) | 판정 |
|------|-----------|----------------------|------|
| **신호 빈도** | 하루 20~60개 (심볼당) | 하루 139.4개 | ⚠️ 과다 (추가 완화 필요) |
| **LONG/SHORT 균형** | 40~60% | LONG 48.7%, SHORT 51.3% | ✅ 균형 |
| **Regime 분포** | Range 60~80% | Range 73.5%, Trend 26.5% | ✅ 적절 |

**판정**:
- **신호 빈도**: Grid Search 최적화 결과 하루 139.4개로 목표(20~60개)를 초과.  
  → PHASE27-6 이후 파라미터 추가 조정 또는 필터 강화 필요.
- **LONG/SHORT 균형**: 거의 50:50으로 이상적.
- **Regime 분포**: Range 구간 신호가 73.5%로 전략 목적에 부합.

### 2.2 위험 관리 파라미터

| 항목 | 값 | 설명 |
|------|-----|------|
| **SL** | ATR × 1.5 | 손절가 = 현재가 ± (ATR × 1.5) |
| **TP** | RR 1.5 | 익절가 = SL × 1.5 |
| **최대 보유** | 60분 | 시간 기반 강제 청산 |
| **Leverage** | 기본 3x (최소 1x, 최대 5x) | Kelly Fraction 기반 동적 조정 |
| **Risk per Trade** | 2% | 포트폴리오 대비 단일 거래 리스크 |

### 2.3 전략 파라미터 (PHASE27-4 Grid Search Top 1)

**신호 조건**:
```yaml
rsi_long_threshold: 42    # Grid Search 최적화 (기존 45)
rsi_short_threshold: 58   # Grid Search 최적화 (기존 55)
bb_std_main: 1.2          # Grid Search 최적화 (기존 1.0)
bb_std_strong: 1.5        # 강한 신호 BB 밴드
momentum_lookback: 5      # 모멘텀 확인 캔들 수
momentum_threshold: 0.001 # 0.1% 모멘텀 기준
```

**ADX 레짐 설정**:
```yaml
use_adx: true             # ADX 활성화
adx_period: 14            # ADX 계산 기간
adx_trend_threshold: 20   # Grid Search 최적화 (기존 25)
```

**위험 관리**:
```yaml
rr: 1.5                   # Risk/Reward
atr_mult_sl: 1.5          # SL = ATR × 1.5
max_hold_minutes: 60      # 최대 보유 시간
min_bars_for_signal: 50   # 최소 데이터
```

### 2.4 신호 조건 (Range vs Trend)

**Range Regime (ADX ≤ 20)**: Mean Reversion 강조
- **LONG**:
  1. RSI < 42 (p25 근처) OR
  2. Price < BB Lower (1.2 std) + 최근 모멘텀 하락 OR
  3. Price < BB Lower (1.5 std)
- **SHORT**:
  1. RSI > 58 (p75 근처) OR
  2. Price > BB Upper (1.2 std) + 최근 모멘텀 상승 OR
  3. Price > BB Upper (1.5 std)

**Trend Regime (ADX > 20)**: 극단적 조건 우선, 역추세 완화
- **LONG**:
  1. Price < BB Lower (1.5 std) OR
  2. (Price < BB Lower (1.2 std) AND RSI < 42)
- **SHORT**:
  1. Price > BB Upper (1.5 std) OR
  2. (Price > BB Upper (1.2 std) AND RSI > 58)

---

## 3. 데이터 프로파일링 결과 (2024-11-30 ~ 2024-12-30, 30일)

**PHASE27-2에서 수집한 시장 통계**:

| 지표 | 값 | 설명 |
|------|-----|------|
| **RSI** | p25=39.4, p75=60.8 | 극단값 (<30: 9.96%, >70: 10.25%) |
| **BB(1.0 std)** | 돌파 ~25% | 1.0 표준편차 밴드 돌파 빈도 |
| **BB(1.5 std)** | 돌파 ~13% | 1.5 표준편차 밴드 돌파 빈도 |
| **Volume** | 평균 1.03x | 평균 대비 배수 (>1.2x 발생률 26.1%) |
| **ATR** | 평균 0.21%, 중앙값 0.17% | 변동성 지표 |

**시사점**:
- RSI 극단값 발생률이 ~10%로 낮음 → RSI 단독 조건은 신호 부족
- BB 1.0 std 돌파가 25%로 빈번 → OR 조건으로 보완
- 저변동성 구간 (ATR 0.17~0.21%) → Mean-Reversion 전략 적합

---

## 4. 향후 백테스트 메트릭 (PHASE27-7 이후)

### 4.1 수익성 메트릭

| 메트릭 | 목표 | 설명 |
|--------|------|------|
| **Sharpe Ratio** | > 1.0 | 위험 대비 수익률 (연율화) |
| **Profit Factor** | > 1.2 | 총 이익 / 총 손실 |
| **승률** | > 40% | 승리 거래 / 전체 거래 |
| **평균 RR** | > 1.2 | 실제 평균 Risk/Reward |
| **총 수익률** | > 10% (30일 기준) | 백테스트 기간 총 수익률 |

### 4.2 안정성 메트릭

| 메트릭 | 목표 | 설명 |
|--------|------|------|
| **Max Drawdown** | < 15% | 최대 낙폭 |
| **Win Streak** | - | 최대 연속 승리 |
| **Loss Streak** | < 5 | 최대 연속 손실 |
| **Calmar Ratio** | > 1.0 | 연율 수익률 / Max Drawdown |
| **Recovery Factor** | > 2.0 | 총 수익 / Max Drawdown |

### 4.3 활동성 메트릭

| 메트릭 | 목표 | 설명 |
|--------|------|------|
| **Trade Frequency** | 하루 20~60개 | 신호 빈도 (현재 139.4개는 과다) |
| **평균 보유 시간** | < 60분 | 스캘핑 전략 특성 |
| **LONG/SHORT 균형** | 40~60% | 방향성 편향 방지 |
| **Regime 분포** | Range 60~80% | Range 구간 신호 비중 |

### 4.4 위험 메트릭

| 메트릭 | 목표 | 설명 |
|--------|------|------|
| **평균 SL 크기** | ~0.3% | ATR 기반 SL 크기 |
| **평균 TP 크기** | ~0.45% | RR 1.5 기준 TP 크기 |
| **최대 동시 포지션** | ≤ 3 | Portfolio 설정 준수 |
| **최대 Exposure** | ≤ 60% | Portfolio 설정 준수 |

---

## 5. 백테스트 실행 계획 (PHASE27-7 이후)

### 5.1 백테스트 기간

| 기간 | 목적 |
|------|------|
| **In-Sample** | 2024-11-01 ~ 2024-11-30 (30일) | 파라미터 튜닝 기간 |
| **Out-of-Sample** | 2024-12-01 ~ 2024-12-30 (30일) | 검증 기간 |
| **Full Period** | 2024-01-01 ~ 2024-12-31 (1년) | 장기 안정성 검증 |

### 5.2 백테스트 시나리오

1. **Baseline Run**: 현재 파라미터 그대로 실행
2. **Sensitivity Analysis**: 주요 파라미터 변화에 따른 민감도 분석
3. **Regime Analysis**: Range vs Trend 구간별 성과 분석
4. **Slippage/Commission**: 실거래 비용 반영 시나리오

### 5.3 백테스트 산출물

- **Scorecard**: 수익성/안정성/활동성 메트릭 요약
- **Equity Curve**: 시간별 자산 변화 그래프
- **Drawdown Chart**: 낙폭 추이
- **Trade Distribution**: 승/패 분포, 보유 시간 분포
- **Regime Analysis**: Range/Trend 구간별 성과

---

## 6. 전략 개선 로드맵

### 6.1 PHASE27-6: 신호 빈도 조정

**문제**: 현재 하루 139.4개 신호는 목표(20~60개)를 초과.

**개선 방안**:
1. **필터 강화**:
   - Volume 필터 추가 (>1.2x 평균)
   - ADX 최소값 추가 (Range 구간에서도 최소 ADX > 10)
2. **파라미터 조정**:
   - `bb_std_main` 1.2 → 1.5 (밴드 돌파 조건 강화)
   - `rsi_long_threshold` 42 → 40 (극단값 조건 강화)
3. **Grid Search 재실행**:
   - 목표 신호 빈도 20~60개로 제약 조건 추가

### 6.2 PHASE27-7: 백테스트 및 수익성 검증

**목표**: Baseline 전략의 실제 수익성 검증

**작업**:
1. 30일 In-Sample 백테스트 실행
2. 30일 Out-of-Sample 백테스트 실행
3. Scorecard 생성 및 메트릭 분석
4. Sharpe > 1.0, Profit Factor > 1.2 달성 여부 확인

### 6.3 PHASE27-8: 멀티 심볼 확장 (선택적)

**목표**: Baseline 전략을 다른 심볼에 적용

**작업**:
1. ETHUSDT, SOLUSDT 등 주요 알트코인 테스트
2. 심볼별 파라미터 튜닝 필요 여부 확인
3. 멀티 심볼 포트폴리오 백테스트

---

## 7. 현재 상태 요약

### 7.1 PHASE27-5 목표

**Signal Parity 검증**:
- Offline Scan ↔ Engine Replay 신호 수 일치 검증 (±10% 허용)
- TradeActivityTracker 기반 Drop-off 분석
- Baseline 전략 스펙 1차 정의 ✅ (본 문서)

### 7.2 다음 단계

1. **PHASE27-5 완료**:
   - Engine Replay 실행
   - Signal Parity 테스트 실행
   - 실행 보고서 작성
2. **PHASE27-6**: 신호 빈도 조정 (139.4개 → 20~60개)
3. **PHASE27-7**: 백테스트 및 수익성 검증

---

## 8. 참고 문서

- `strategies/btc5m_baseline_v1.py`: 전략 코드
- `docs/PHASE27/PHASE27-2_STRATEGY_REDESIGN_REPORT.md`: 전략 설계 배경
- `docs/PHASE27/PHASE27-3_ADX_INTEGRATION_REPORT.md`: ADX 통합 과정
- `docs/PHASE27/PHASE27-4_BASELINE_SIGNAL_VALIDATION_REPORT.md`: Offline Scan 결과
- `docs/PHASE27/PHASE27-5_SIGNAL_PARITY_AND_BACKTEST_DESIGN.md`: 본 작업 설계 문서
- `docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json`: Offline Scan 데이터

---

**작성일**: 2025-12-04  
**상태**: 🟦 **IN PROGRESS**  
**다음 단계**: Engine Replay 실행 및 Signal Parity 검증
