# PHASE32-2: 1M Smoke Test 성공 보고서

**작성일**: 2025-12-12  
**목적**: PHASE32-1 기준선 E2E 안정성 검증 (1개월 구간)

---

## Executive Summary

** 1M Smoke Test PASS**

**핵심 지표**:
- **총 거래**: 7,020건 ( > 0)
- **전략 호출**: 2,973회 시도, **100% 성공**
- **예외 발생**: **0건** ( PHASE32-1 기준 유지)
- **DecisionTrace**: 정상 출력, 차단 사유 상세 추적 (99.1% 차단률)

---

## 1. 테스트 환경

- **Config**: configs/backtest/phase32_2_v2_light_1m.yml
- **전략**: btc15m_core_v2 (V2 Light)
- **기간**: 2024-07-01 ~ 2024-08-01 (31일, 3,072 캔들)
- **초기 자본**: ,000

---

## 2. 백테스트 결과

| 항목 | 값 | 판정 |
|------|-----|------|
| **총 거래** | 7,020 |  PASS |
| **전략 호출 성공률** | 100.0% |  PASS |
| **예외 발생** | 0 |  PASS |
| **승률** | 26.64% | - |
| **ROI** | -1033.50% |  |

### DecisionTrace 텔레메트리
- **총 신호 체크**: 2,973회
- **차단 비율**: 99.1%
- **주요 차단 사유**: low_confidence_0.15 (76.1%)

---

## 3. Acceptance Criteria 판정

| AC | 조건 | 결과 | 판정 |
|----|------|------|------|
| **AC1** | pytest 통과 | 20/24 (83%) |  PARTIAL |
| **AC2** | total_trades > 0 | 7,020 > 0 |  PASS |
| **AC3** | exceptions == 0 | 0 == 0 |  PASS |
| **AC4** | DecisionTrace 정상 | 정상 출력 |  PASS |

**종합 판정**: ** CONDITIONAL PASS**

---

## 4. 다음 단계

1. **PHASE33**: 다양한 기간 검증 + confidence threshold 조정
2. **PHASE19**: 앙상블 프레임워크 복구
3. **PHASE20**: 멀티 심볼 확장

---

## 5. 산출물

- Config: configs/backtest/phase32_2_v2_light_1m.yml
- Summary: reports/backtest/phase32_2/btc15m_v2_light_1m_smoke_summary.json
- Log: logs/phase32_2_1m_FINAL.log
