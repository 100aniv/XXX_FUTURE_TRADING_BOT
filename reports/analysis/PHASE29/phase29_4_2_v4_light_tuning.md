# PHASE29-4.2: V4 경량 튜닝 결과

**분석일**: 2025-12-11 10:30:34
**튜닝 실행**: 2025-12-11T04:07:09.361740
**총 조합**: 24개

---

## 📊 Executive Summary

- **성공**: 24/24개
- **AC3 PASS**: 12개 (거래 건수 80~240건 기준)

**주의**: 현재 Summary JSON에는 Win Rate/Max DD 정보가 없어 AC3 완전 평가 불가

## 🎯 튜닝 그리드

| 파라미터 | 값 |
|----------|-----|
| range_min_score | {2, 3, 4} (3개) |
| trend_min_score | {2, 3} (2개) |
| min_rr_required | {1.0, 1.2} (2개) |
| cooldown_candles | {0, 1} (2개) |
| **총 조합** | **24개** |

## 🏆 상위 3개 조합

### 1. phase29_4_tuning_r2_t2_rr1.0_cd0

| 항목 | 값 |
|------|-----|
| **range_min_score** | 2 |
| **trend_min_score** | 2 |
| **min_rr_required** | 1.0 |
| **cooldown_candles** | 0 |
| 체결 건수 | 140건 |
| 신호 발생 | 406건 |
| Guard 통과율 | 34.5% |
| LONG 신호 | 148건 |
| SHORT 신호 | 258건 |
| AC3 판정 | ✅ PASS (거래 건수 기준) |

### 2. phase29_4_tuning_r2_t2_rr1.0_cd1

| 항목 | 값 |
|------|-----|
| **range_min_score** | 2 |
| **trend_min_score** | 2 |
| **min_rr_required** | 1.0 |
| **cooldown_candles** | 1 |
| 체결 건수 | 140건 |
| 신호 발생 | 406건 |
| Guard 통과율 | 34.5% |
| LONG 신호 | 148건 |
| SHORT 신호 | 258건 |
| AC3 판정 | ✅ PASS (거래 건수 기준) |

### 3. phase29_4_tuning_r2_t3_rr1.0_cd0

| 항목 | 값 |
|------|-----|
| **range_min_score** | 2 |
| **trend_min_score** | 3 |
| **min_rr_required** | 1.0 |
| **cooldown_candles** | 0 |
| 체결 건수 | 140건 |
| 신호 발생 | 406건 |
| Guard 통과율 | 34.5% |
| LONG 신호 | 148건 |
| SHORT 신호 | 258건 |
| AC3 판정 | ✅ PASS (거래 건수 기준) |

## 📋 전체 결과 (상위 10개)

| 순위 | run_id | Range | Trend | RR | CD | 체결 | AC3 |
|------|--------|-------|-------|----|----|------|-----|
| 1 | phase29_4_tuning_r2_t2_rr1.0_cd0 | 2 | 2 | 1.0 | 0 | 140 | ✅ |
| 2 | phase29_4_tuning_r2_t2_rr1.0_cd1 | 2 | 2 | 1.0 | 1 | 140 | ✅ |
| 3 | phase29_4_tuning_r2_t3_rr1.0_cd0 | 2 | 3 | 1.0 | 0 | 140 | ✅ |
| 4 | phase29_4_tuning_r2_t3_rr1.0_cd1 | 2 | 3 | 1.0 | 1 | 140 | ✅ |
| 5 | phase29_4_tuning_r3_t2_rr1.0_cd0 | 3 | 2 | 1.0 | 0 | 140 | ✅ |
| 6 | phase29_4_tuning_r3_t2_rr1.0_cd1 | 3 | 2 | 1.0 | 1 | 140 | ✅ |
| 7 | phase29_4_tuning_r3_t3_rr1.0_cd0 | 3 | 3 | 1.0 | 0 | 140 | ✅ |
| 8 | phase29_4_tuning_r3_t3_rr1.0_cd1 | 3 | 3 | 1.0 | 1 | 140 | ✅ |
| 9 | phase29_4_tuning_r4_t2_rr1.0_cd0 | 4 | 2 | 1.0 | 0 | 107 | ✅ |
| 10 | phase29_4_tuning_r4_t2_rr1.0_cd1 | 4 | 2 | 1.0 | 1 | 107 | ✅ |

## 💡 분석 코멘트

### 거래 건수 분포

- **80~240건 (Gate_1M 범위)**: 12개
- **80건 미만 (신호 부족)**: 12개
- **240건 초과 (오버트레이딩)**: 0개

### Score Threshold 영향

- **range_min_score=2**: 평균 70.0건 체결
- **range_min_score=3**: 평균 70.0건 체결
- **range_min_score=4**: 평균 53.5건 체결

## 🚀 다음 단계

### AC3 완전 평가를 위한 추가 작업

현재 Summary JSON에는 **Win Rate, Max DD 정보가 없습니다.**

**옵션 A**: Engine 또는 Reporter를 수정하여 Summary JSON에 Win Rate/Max DD 추가
- 장점: 향후 모든 백테스트에서 자동 수집
- 단점: 코어 엔진 수정 필요

**옵션 B**: 별도 분석 스크립트로 거래 로그에서 Win Rate/Max DD 계산
- 장점: 엔진 수정 불필요
- 단점: 거래 로그가 필요, 추가 스크립트 작성

**권장**: 옵션 A (Engine 수정)를 후속 PHASE에서 진행

## 📝 PHASE29-4의 역할

이 PHASE의 목표는:
- ✅ V4 전략이 1개월 기준으로 실질적인 후보가 될 수 있는지 **성능 탐색**
- ✅ 다양한 파라미터 조합으로 **신호 빈도 범위 확인**
- ✅ Guard 설정이 V4에 미치는 영향 분석

**전략 최종 선정 및 Ensemble 반영은 후속 PHASE에서 진행**합니다.
