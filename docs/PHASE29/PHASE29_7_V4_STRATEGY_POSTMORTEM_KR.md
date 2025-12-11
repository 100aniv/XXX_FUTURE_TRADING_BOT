# PHASE29-7: V4 Strategy Postmortem & Retirement

**작성일**: 2025-12-11  
**상태**: ✅ COMPLETE  
**판정**: ❌ **STRATEGY RETIRED** (Research Graveyard)

---

## 목차

1. [개요](#1-개요)
2. [V4 전략 설계 컨셉](#2-v4-전략-설계-컨셉)
3. [PHASE29 검증 결과 요약](#3-phase29-검증-결과-요약)
4. [근본 실패 원인 분석](#4-근본-실패-원인-분석)
5. [보존할 요소 vs 폐기할 요소](#5-보존할-요소-vs-폐기할-요소)
6. [PHASE30 To-BE 전략 설계 권고](#6-phase30-to-be-전략-설계-권고)
7. [결론](#7-결론)

---

## 1. 개요

### 1.1 전략 배경

**btc5m_baseline_v4**는 PHASE29-3.1에서 V3 전략의 실패(AND 로직 과잉 → 신호 극소)를 극복하기 위해 설계된 Regime-Aware Hybrid 전략이다.

**설계 목표**:
- V2 문제(OR 과잉 → Win Rate < 45%) 해결
- V3 문제(AND 과잉 → 신호 극소 17건/월) 해결
- OR 기반 + 가중치 점수 합산으로 신호 빈도와 품질 균형

### 1.2 PHASE29에서의 역할

PHASE29 전체에서 V4는 다음 역할을 수행했다:
1. **Gate Test** (1주): 신호 빈도 검증 (목표: 20-60건)
2. **1M Baseline** (1개월): 성능 기준 검증 (목표: Win Rate ≥ 45%, Max DD ≤ 15%)
3. **Light Tuning** (24개 조합): 파라미터 최적화 시도
4. **AC3 최종 판정** (PHASE29-6): 정확한 성능 지표 기반 평가

---

## 2. V4 전략 설계 컨셉

### 2.1 핵심 설계

**Regime Detection**:
- Trend (BULL/BEAR) vs Range 구분
- ADX 기반 레짐 분류 (Trend: ADX ≥ 25, Range: ADX < 20)

**진입 로직 (OR + Score)**:
- **Trend Mode**: RSI(3점) + BB(2점) + EMA Pullback(2점) + DI(1점)
- **Range Mode**: RSI(3점) + BB(2점) + ADX(1점)
- **Threshold**: trend_min_score=3, range_min_score=3

**Multi-TP 구조**:
- TP1 (60% 포지션): RR = 1.2 (Trend) / 1.0 (Range)
- TP2 (40% 포지션): RR = 3.0 (Trend) / 2.0 (Range)

**SL/TP 설정**:
- Trend: SL = 2.0 ATR, TP1 = 1.2x SL, TP2 = 3.0x SL
- Range: SL = 1.5 ATR, TP1 = 1.0x SL, TP2 = 2.0x SL

### 2.2 V3 대비 주요 변경

| 항목 | V3 (AND 과잉) | V4 (OR + Score) |
|------|---------------|-----------------|
| 진입 조건 | AND (모두 충족) | OR + Score (점수 합산) |
| 신호 빈도 | 극소 (17건/월) | 정상 (140건/월) |
| 설계 철학 | 보수적 진입 | 유연한 진입 + 품질 제어 |

---

## 3. PHASE29 검증 결과 요약

### 3.1 Gate Test (1주, PHASE29-3.4)

| 항목 | 결과 | 판정 |
|------|------|------|
| 신호 발생 | 96건 | ✅ |
| Guard OFF 체결 | 35건 | ✅ PASS (목표: 20-60건) |
| Guard ON 체결 | 0건 | ❌ (호환성 문제) |

**발견**: V4와 기존 Guard 설정(min_rr_required=1.2)은 호환되지 않음.

### 3.2 1M Baseline (PHASE29-4.1)

| 항목 | 결과 | 판정 |
|------|------|------|
| 거래 건수 | 140건 | ✅ PASS (Gate_1M: 80-240건) |
| 신호 발생 | 406건 | ✅ |
| Guard 차단 | 222건 (54.7%) | - |
| 선형 확장 | 1주 35건 × 4 = 140건 | ✅ |

### 3.3 Light Tuning (PHASE29-4.2, 24개 조합)

**파라미터 범위**:
- range_min_score: {2, 3, 4}
- trend_min_score: {2, 3}
- min_rr_required: {1.0, 1.2}
- cooldown_candles: {0, 1}

**결과**:
- Gate_1M 통과 (80-240건): 12/24 조합
- 모두 min_rr=1.0 조합 (min_rr=1.2는 모두 실패)
- 상위 3개: range=2, trend=2, RR=1.0 조합들

### 3.4 AC3 최종 판정 (PHASE29-6)

**재실행 정보**:
- trial_id/run_id 정합성 수정 후 재실행
- trial_id: `phase29_4_0_btc5m_baseline_v4_month_gate`
- DB 저장 확인: 140건 정상 매핑

#### 1M Gate Baseline

| 지표 | 실제 값 | AC3 기준 | 판정 |
|------|---------|---------|------|
| **Trades** | 140건 | - | ✅ |
| **Win Rate** | **27.86%** | >= 45% | ❌ **FAIL** (-17.14%p) |
| **Max Drawdown** | **23.21%** | <= 15% | ❌ **FAIL** (+8.21%p) |
| **PnL Total** | -2,245.21 USDT | > 0 | ❌ |
| **Profit Factor** | 0.525 | > 1.0 | ❌ |
| **Sharpe Ratio** | -4.59 | > 0 | ❌ |
| **ROI** | -22.45% | > 0 | ❌ |

**Win/Loss 분포**:
- Wins: 39건 (27.86%)
- Losses: 101건 (72.14%)
- Avg Win: +63.66 USDT
- Avg Loss: -46.81 USDT
- Max Consecutive Losses: 10건

#### Top 3 튜닝 조합

모두 AC3 FAIL (Win Rate 30.4%, Max DD 64.6%)

**종합 판정**: **4/4 조합 모두 AC3 FAIL (0/4 PASS)**

---

## 4. 근본 실패 원인 분석

### 4.1 정량적 증거

**1. 과도한 손실 비율** (72.14%)
- 목표: 55% 이하
- 실제: 72.14% (17%p 초과)
- 원인: 진입 조건의 품질 문제

**2. 낮은 Win Rate** (27.86%)
- 목표: 45% 이상
- 실제: 27.86% (17.14%p 부족)
- 원인: OR 기반 로직이 저품질 신호 과다 생성

**3. 불리한 Win/Loss 비율**
- Avg Win: $63.66
- Avg Loss: $46.81
- R:R 자체는 1.36으로 나쁘지 않으나, Win Rate가 낮아 전체 손실 발생

**4. 높은 연속 손실**
- Max Consecutive Losses: 10건
- 10건 연속 손실 시 심리적/자본적 리스크 과다

### 4.2 구조적 문제

#### 4.2.1 OR 기반 진입 조건의 과도한 유연성

**문제**:
- V4는 "OR + Score"로 설계되어, 4개 조건 중 3점만 충족하면 진입
- 예: Trend Mode에서 RSI Pullback(3점)만으로 진입 가능
- 결과: 단일 지표의 오류가 바로 손실로 이어짐

**V3와의 차이**:
- V3: AND → 모든 조건 충족 → 신호 극소 (17건/월)
- V4: OR + Score → 일부 조건만 충족 → 신호 과다 (140건/월, 품질 저하)

**중간 지점 실패**:
- "AND 과잉"과 "OR 과잉"의 중간을 찾으려 했으나, 실제로는 OR 과잉 쪽에 치우침

#### 4.2.2 Score Threshold의 부적절성

**문제**:
- trend_min_score=3, range_min_score=3
- 최대 점수 (Trend: 8점, Range: 6점) 대비 너무 낮음
- 결과: 저품질 신호도 통과

**Light Tuning 결과**:
- range_min_score를 4로 올려도 성능 개선 없음
- Score 구조 자체가 문제 (가중치 설계 부실)

#### 4.2.3 Regime Detection의 부정확성

**문제**:
- ADX 기반 Trend vs Range 구분
- 실제 시장은 ADX만으로 정확히 분류하기 어려움
- 결과: Trend Mode에서 Range 시장 진입 → 손실

**정량적 증거 부족**:
- DB에 metadata 컬럼이 없어 Regime별 성능 분석 불가
- 하지만 전체 성능이 나쁘므로 어떤 Regime에서든 실패했을 가능성

#### 4.2.4 SL/TP 비율의 시장 미스매치

**문제**:
- Trend: SL=2.0 ATR, TP1=1.2x SL → RR 1.2 (너무 낮음)
- Range: SL=1.5 ATR, TP1=1.0x SL → RR 1.0 (최소 기준)
- 실제 BTC 5m 시장에서 이 RR로는 Win Rate 45%를 달성하기 어려움

**수학적 근거**:
- RR=1.2, Win Rate=45% → 기대값 = 0.45 * 1.2 - 0.55 * 1.0 = -0.01 (손실)
- RR=1.5, Win Rate=45% → 기대값 = 0.45 * 1.5 - 0.55 * 1.0 = +0.125 (이익)
- 즉, RR=1.2로는 Win Rate 54%가 필요

#### 4.2.5 5m Timeframe의 과도한 노이즈

**문제**:
- 5m 타임프레임은 노이즈가 많아 전략 신뢰도 저하
- RSI, BB 등 지표가 빈번하게 False Signal 생성
- 결과: 높은 손실 비율

**대안**:
- 15m, 30m 등 더 긴 타임프레임 고려 필요

---

## 5. 보존할 요소 vs 폐기할 요소

### 5.1 보존할 가치 있는 아이디어

#### ✅ Regime-Aware 구조
- **컨셉**: Trend/Range 분리 전략
- **보존 이유**: 시장 상황에 따른 적응형 전략은 유효
- **개선 방향**: ADX 외 다른 지표 조합 (예: ATR, Volume, Directional Movement)

#### ✅ Multi-TP 구조
- **컨셉**: TP1 (60%) + TP2 (40%) 분할 청산
- **보존 이유**: 리스크 관리 측면에서 유효
- **개선 방향**: RR 비율 재설계 필요

#### ✅ ATR 기반 SL/TP 계산
- **컨셉**: 변동성 적응형 손절/익절
- **보존 이유**: 시장 변동성 반영은 필수
- **개선 방향**: ATR 배수 조정 (현재 2.0 ATR SL → 1.5 ATR 또는 동적 조정)

#### ✅ Guard 시스템 연동 구조
- **컨셉**: 전략 외부에서 진입 제어
- **보존 이유**: 엔진 레벨 리스크 관리는 필수
- **개선 방향**: 전략과 Guard 간 파라미터 조율 필요

### 5.2 완전히 폐기해야 할 설계

#### ❌ OR 기반 Score 조합
- **이유**: 저품질 신호 과다 생성
- **문제**: 단일 지표 오류가 바로 손실로 이어짐
- **대안**: AND 기반 + 일부 조건 유연화 (예: "Core 조건 AND + Optional 조건 OR")

#### ❌ 현재 Score 가중치 구조
- **이유**: 가중치 설계가 부실 (RSI 3점, BB 2점 등)
- **문제**: Score Threshold를 높여도 성능 개선 없음
- **대안**: 데이터 기반 가중치 학습 (백테스트 통계 분석)

#### ❌ 낮은 RR 비율 (1.0~1.2)
- **이유**: Win Rate 45%로는 손실 불가피
- **문제**: 수학적으로 기대값 음수
- **대안**: 최소 RR 1.5 이상, 또는 동적 RR 조정

#### ❌ ADX 단일 지표 기반 Regime 분류
- **이유**: 정확도 부족
- **문제**: Regime 오판 시 전략 전체 실패
- **대안**: 복합 지표 조합 (ADX + ATR + Volume + Directional Movement)

#### ❌ 5m Timeframe 고집
- **이유**: 과도한 노이즈, 신호 품질 저하
- **문제**: 거래 건수는 많지만 Win Rate 낮음
- **대안**: 15m, 30m 등 더 긴 타임프레임 테스트

---

## 6. PHASE30 To-BE 전략 설계 권고

PHASE30에서 새로운 코어 전략을 설계할 때 **반드시 고려해야 할 사항**:

### 6.1 진입 조건 설계

**✅ 권장**:
- **Core 조건 AND**: 필수 조건들은 AND로 결합 (예: Trend 확인 + ATR 충분)
- **Optional 조건 OR**: 부가 조건들은 OR로 가점 (예: BB + RSI 중 하나)
- **Hybrid 구조**: "Core AND + (Optional1 OR Optional2)"

**❌ 금지**:
- 모든 조건을 OR로 결합
- Score Threshold가 최대 점수의 50% 이하

### 6.2 Regime Detection 재설계

**✅ 권장**:
- **복합 지표**: ADX + ATR + Volume + Directional Movement
- **확률적 접근**: Regime별 신뢰도 점수 (예: Trend 확률 70%)
- **백테스트 검증**: 각 Regime에서 실제 성능 분리 측정

**❌ 금지**:
- ADX 단일 지표만 사용
- Threshold 하드코딩 (예: ADX > 25 = Trend)

### 6.3 SL/TP 비율

**✅ 권장**:
- **최소 RR 1.5**: Win Rate 40%만 되어도 이익
- **동적 RR 조정**: 변동성에 따라 SL/TP 거리 조정
- **Trailing Stop**: 이익 구간에서 SL 상향 조정

**❌ 금지**:
- 고정 RR 1.0~1.2 (Win Rate 50% 이상 필요)
- ATR 배수 하드코딩 (시장 변동성 무시)

### 6.4 Timeframe 선택

**✅ 권장**:
- **15m, 30m 우선 테스트**: 노이즈 감소, 신호 품질 향상
- **Multi-Timeframe 확인**: 상위 타임프레임에서 Trend 확인
- **백테스트 비교**: 5m vs 15m vs 30m 성능 비교

**❌ 금지**:
- 5m에만 의존
- 단일 타임프레임만 사용 (Multi-TF 무시)

### 6.5 Guard 호환성

**✅ 권장**:
- **전략 설계 시 Guard 고려**: min_rr_required, cooldown 등
- **Config 기반 조율**: 전략과 Guard 파라미터 동기화
- **백테스트 시 Guard ON/OFF 비교**: 호환성 검증

**❌ 금지**:
- Guard 무시하고 전략만 설계
- Guard OFF 성능만 평가 (실제 운영 불가)

### 6.6 성능 목표 재설정

**현실적 목표**:
- Win Rate: **40~45%** (RR 1.5 기준)
- Max DD: **≤ 12%** (보수적 목표)
- Profit Factor: **> 1.2** (명확한 이익 구조)
- 거래 건수: **1개월 60~120건** (5m 140건보다 보수적)

**백테스트 기준**:
- 최소 3개월 이상
- Bull/Bear/Sideways 시장 모두 포함
- Out-of-Sample 검증 필수

---

## 7. 결론

### 7.1 V4 전략 최종 판정

**❌ STRATEGY RETIRED (Research Graveyard)**

- V4 전략은 PHASE29 전체 검증 과정에서 **AC3 성능 기준을 충족하지 못했다**.
- 1M Gate Baseline: Win Rate 27.86%, Max DD 23.21%
- Top 3 튜닝 조합: 모두 AC3 FAIL
- 구조적 설계 결함으로 파라미터 튜닝만으로는 개선 불가능
- 라이브/앙상블 후보에서 **영구 제외**

### 7.2 PHASE29 전체 성과

**Infrastructure 100% 완료**:
- Portfolio Budget & Position Infra 안정화 (PHASE17 V6.1)
- trial_id/run_id 정합성 수정 (PHASE29-6)
- Performance Metrics 자동 수집 (PHASE29-5)
- 향후 모든 백테스트에서 정확한 성능 지표 자동 생성 가능

**전략 검증 완료**:
- V3 전략: AND 과잉 → 신호 극소 → **RETIRED**
- V4 전략: OR 과잉 → Win Rate 부족 → **RETIRED**
- 교훈: AND/OR의 중간 지점 설계가 핵심

### 7.3 다음 단계 (PHASE30)

**PHASE30-0: New Core Strategy Design**

**목표**: V3/V4 실패 교훈을 반영한 새로운 코어 전략 설계

**입력 자료**:
- PHASE29-7 Postmortem (본 문서)
- PHASE29-4/5/6 성능 데이터
- V3/V4 코드 및 백테스트 결과

**설계 원칙** (6.1~6.6 권고사항 적용):
1. Core AND + Optional OR 구조
2. 복합 지표 기반 Regime Detection
3. 최소 RR 1.5 이상
4. 15m/30m Timeframe 우선
5. Guard 호환성 사전 검증
6. 3개월 이상 백테스트 + Out-of-Sample

**판정 기준**:
- Win Rate ≥ 40% (RR 1.5 기준)
- Max DD ≤ 12%
- Profit Factor > 1.2
- 거래 건수 60~120건/월

---

**작성자**: Cascade AI (Claude 4.5 Thinking)  
**검토일**: 2025-12-11  
**상태**: ✅ COMPLETE

**V4 전략은 Research Graveyard로 이관되었습니다. PHASE30에서 새로운 코어 전략 설계를 시작합니다.**
