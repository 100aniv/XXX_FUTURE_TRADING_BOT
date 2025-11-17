# PHASE17 V4 → V5 → V5b 실행 분석 리포트

**작성일**: 2025-11-18 01:45 KST  
**목적**: V4 조기 종료 문제 해결 시도 및 근본 원인 분석

---

## 📊 실행 결과 요약

| 항목 | V4 | V5 | V5b | 목표 |
|------|----|----|-----|------|
| **실행 시간** | 6m 30s | ~10m | ~2m | 3시간+ |
| **Entry** | 37개 | 38개 | 7개 | 50개+ |
| **조기 종료 원인** | Volume Guard | Portfolio Budget | Portfolio Budget | N/A |
| **Volume Guard 차단** | 수십 회 | 0회 | 0회 | 0회 |
| **Equity** | $49,955 | $46,474 | $49,874 | $50,000+ |
| **최종 판정** | ❌ FAIL | ❌ FAIL | ❌ FAIL | - |

---

## 🔍 V4 문제 분석

### 원인
- **Volume Guard 과도 작동**
- `vol_spike_mult: 2.5` (거래량이 MA의 2.5배 초과 시 차단)
- 정상 거래량 변동도 "급증"으로 오인
- 00:55 이후 Entry 완전 중단

### 로그 증거
```
"⚠️ BTCUSDT 거래량 급증으로 신호 보류" (반복)
```

### 해결 시도
- V5에서 `enable_vol_spike_filter: false` (완전 비활성화)

---

## 🔍 V5 문제 분석

### 변경 사항
```yaml
# V5 변경 1: Volume Guard 비활성화
enable_vol_spike_filter: false

# V5 변경 2: Entry Cooldown 추가
strategies:
  scalping:
    entry_cooldown_seconds: 20
```

### 결과
- ✅ Volume Guard 차단 0회 (문제 해결)
- ❌ Portfolio Budget 초과로 BLOCK

### 새로운 문제: Portfolio Budget 초과

**로그 증거**:
```
[ENTRY BLOCK] reason=portfolio_check_failed 
detail="전략 예산 초과: scalping $14,738.06 > $12,488.84"
```

**근본 원인**:
- Portfolio Budget: ~$12,500 (Equity의 25%)
- 시도 Entry: ~$14,700 (Budget의 118%)
- 01:33:20 이후 Entry 완전 중단

**Budget 계산**:
```
Portfolio Budget = Equity * 0.25 / max_strategy_positions
$12,500 = $50,000 * 0.25 / 1 (실제 오픈 포지션 수?)
```

---

## 🔍 V5b 문제 분석

### 변경 사항
```yaml
# V5b 변경: max_strategy_positions 증가
portfolio:
  max_strategy_positions: 10  # 5 → 10 (Budget 2배)
```

### 결과
- ❌ 동일한 Portfolio Budget 문제 발생
- Budget 여전히 ~$12,455
- 즉, `max_strategy_positions`는 Budget 계산에 영향 없음

### 결론
- `max_strategy_positions`는 Portfolio Manager의 Budget 계산 로직과 무관
- Config 수정만으로는 근본 해결 불가
- 코드 레벨 분석 또는 다른 Config 파라미터 필요

---

## 🚨 근본 원인: Portfolio Budget 로직 불일치

### 문제
1. **Budget 계산 로직**:
   - Portfolio Manager가 Budget을 계산하는 방식이 불명확
   - `max_strategy_positions`, `per_trade`, `max_total_exposure` 등의 관계 불명확

2. **Position Size 계산**:
   - Position Sizer가 계산한 크기 ($10,000+)
   - Portfolio Budget ($12,500)을 고려하지 않음
   - Exposure Guard에서 ALLOW_REDUCED 적용 후에도 Budget 초과

3. **Multi-position Scaling vs Portfolio Budget**:
   - Multi-position Scaling: 동시 포지션 수에 따라 크기 조정
   - Portfolio Budget: 전략별 총 exposure 제한
   - 두 로직이 서로 충돌

---

## 📈 PHASE17 핵심 기능 검증

### ✅ 검증 성공
1. **ALLOW_REDUCED 작동**:
   - V4: 29개 (78.4%)
   - V5: 다수 발생 확인
   - qty 0.095 → 0.045 등 축소 적용

2. **Multi-position Scaling**:
   - 동시 포지션 수에 따른 크기 조정 확인
   - 로그에서 "조정 적용" 메시지 확인

3. **Exposure Guard 3단계**:
   - ALLOW, ALLOW_REDUCED, BLOCK 모두 작동 확인
   - Exposure 제한 내에서 정상 작동

### ❌ 실패: 지속 실행
- 목표: 3시간+ → 실제: 2~10분
- 원인: Guard 과도 작동 (Volume → Portfolio Budget)
- PHASE17 기능은 정상이나, Guard 설정이 과도함

---

## 💡 해결 방안

### 즉시 조치 (Code 수정 불가 시)
1. **Portfolio Budget 우회**:
   - `per_trade`를 낮춰서 Position Size 축소
   - 예: `0.003 → 0.0015` (-50%)

2. **Exposure 제한 완화**:
   - `max_exposure_per_symbol: 0.35 → 0.50`
   - 단, 리스크 증가

3. **Entry Cooldown 제거**:
   - `entry_cooldown_seconds: 20 → 0`
   - Entry 기회 증가

### 중기 조치 (Code 수정 가능 시)
1. **Portfolio Manager 로직 수정**:
   - Budget 계산 방식 명확화
   - Position Size와 Budget 연동

2. **Multi-position Scaling 개선**:
   - Portfolio Budget을 고려한 Scaling
   - Budget 초과 시 자동 축소

3. **Guard 우선순위 명확화**:
   - Exposure Guard → Portfolio Manager 순서 조정
   - Guard 간 충돌 해결

### 장기 조치 (PHASE18+)
1. **Dynamic Budget 구현**:
   - Equity 변화에 따른 Budget 자동 조정
   - 시간대별/변동성별 Budget 차별화

2. **Guard Framework 통합**:
   - 모든 Guard를 하나의 프레임워크로 통합
   - 우선순위, 충돌 해결 로직 명확화

3. **Config Validation**:
   - 실행 전 Config 검증
   - 불가능한 조합 사전 차단

---

## 📊 V4 vs V5 vs V5b 비교

### 실행 지표
| 지표 | V4 | V5 | V5b |
|------|----|----|-----|
| 실행 시간 | 6m 30s | ~10m | ~2m |
| Entry 시도 | 227개 | 추정 200개+ | 추정 50개 |
| Entry 성공 | 37개 (16.3%) | 38개 | 7개 |
| Exit | 74개 | 추정 76개 | 14개 |
| PnL | -$103 | -$3,481 | -$126 |

### Guard 활성화
| Guard | V4 | V5 | V5b |
|-------|----|----|-----|
| Volume Guard | ✅ 과도 | ❌ 비활성화 | ❌ 비활성화 |
| Portfolio Budget | ✅ 정상 | 🔴 과도 | 🔴 과도 |
| Exposure Guard | ✅ 정상 | ✅ 정상 | ✅ 정상 |
| Entry Cooldown | ❌ 없음 | ✅ 20초 | ✅ 20초 |

### 개선 효과
| 항목 | V4 → V5 | V5 → V5b |
|------|---------|----------|
| 실행 시간 | +54% | -80% |
| Entry | +2.7% | -81.6% |
| Volume Guard | ✅ 해결 | - |
| Portfolio Budget | 🔴 새 문제 | ❌ 미해결 |

---

## 🎯 최종 결론

### 성과
1. ✅ **Volume Guard 문제 해결**:
   - V5에서 완전 비활성화로 차단 0회 달성
   - V4의 핵심 문제 해결

2. ✅ **PHASE17 기능 검증**:
   - Multi-position Scaling 작동 확인
   - ALLOW_REDUCED 정상 작동 (70%+)
   - Exposure Guard 3단계 의사결정 검증

### 실패
1. 🔴 **Portfolio Budget 문제 발견**:
   - V5/V5b 모두 Budget 초과로 조기 종료
   - Config 수정만으로는 해결 불가
   - 코드 레벨 분석 필요

2. 🔴 **장기 실행 실패**:
   - 목표 3시간+ → 실제 최대 10분
   - V4, V5, V5b 모두 실패

### 교훈
1. **Guard의 양면성**:
   - Guard는 리스크 관리 필수 요소
   - 하지만 과도한 Guard는 "거래 중단" 초래
   - Balance 필요: "안전" vs "기회"

2. **Multi-layer Guard의 충돌**:
   - Volume Guard → Portfolio Budget → Exposure Guard
   - 각 Guard가 독립적으로 작동하면서 충돌
   - 통합 프레임워크 필요

3. **Config vs Code**:
   - Config 수정만으로는 근본 문제 해결 불가
   - Portfolio Manager 로직 자체를 수정해야 함
   - 하지만 "DO-NOT-TOUCH Core Engine" 원칙 위배

---

## 🚀 다음 단계

### 즉시 (PHASE17 완료)
1. ✅ V4 vs V5 비교 리포트 작성 (본 문서)
2. ⬜ Portfolio Manager 코드 분석
3. ⬜ Budget 계산 로직 문서화
4. ⬜ V6 Config 설계 (per_trade 축소)

### 단기 (PHASE17.5)
1. V6 실행: `per_trade: 0.0015`, Portfolio Budget 우회
2. 3시간+ 실행 달성
3. PHASE17 기능 장기 검증

### 중기 (PHASE18)
1. Portfolio Manager 리팩토링
2. Multi-position Scaling + Portfolio Budget 통합
3. Guard Framework 설계

### 장기 (PHASE19+)
1. Dynamic Budget 구현
2. Real Live 테스트 준비
3. Multi-symbol 지원

---

**작성 완료**: 2025-11-18 01:45 KST  
**최종 판정**: V4/V5/V5b 모두 조기 종료, Portfolio Budget 문제 발견  
**다음 작업**: Portfolio Manager 코드 분석 → V6 설계
