# PHASE27-4: Baseline+ADX Offline Signal Validation & 30m Real PAPER - 설계 문서

**작성일**: 2025-12-04  
**상태**: ✅ **IN PROGRESS**  
**목표**: Offline Signal Validation + Auto-Calibration + 30m Real PAPER 검증

---

## Executive Summary

### 핵심 목표

**Primary Goal**: Baseline+ADX 전략의 실제 신호 발생 검증
- ✅ Offline Signal Scan Harness 구현
- ✅ Grid Search 기반 Auto-Calibration
- ⏳ 30분 Real PAPER 실행 (진행 중)
- ⏳ ActivityTracker 기반 신호 파이프라인 검증

### 배경

**PHASE27-3 결과**:
- 구현: ✅ COMPLETE (ADX 지표, 전략 통합, 테스트 25/25 PASS)
- 검증: ❌ INCONCLUSIVE (10분 실행, 0 신호 발생)
- 원인: 낮은 변동성 (0.08%), 데이터 부족 (2개 캔들)

**PHASE27-4 접근**:
1. **Offline Signal Scan**: 역사 데이터에서 실제 신호 발생 빈도 검증
2. **Auto-Calibration**: Grid Search로 파라미터 최적화
3. **30m Real PAPER**: 충분한 시간으로 실제 신호 발생 확인

---

## 1. Offline Signal Scan Harness

### 1.1 설계 원칙

**목표**:
- 실제 시장 데이터에서 전략이 얼마나 많은 신호를 생성하는지 검증
- ADX Regime별 신호 분포 확인
- 파라미터 최적화를 위한 정량적 데이터 제공

**재사용 우선**:
- 기존 `strategies/btc5m_baseline_v1.py` 재사용
- 기존 `indicators/core_indicators.py` 재사용
- 새로운 Strategy 클래스 생성 금지

### 1.2 구현

**스크립트**: `scripts/research/phase27_4_btc5m_baseline_signal_scan.py`

**주요 기능**:
1. **데이터 로드**: `data/BTCUSDT_5m_2024-01-01_2024-12-31.csv`
2. **기간 필터링**: 최근 N일 (기본 30일)
3. **지표 계산**: `add_indicators(use_adx=True, adx_period=14)`
4. **신호 스캔**: 각 캔들에 대해 `signal_logic()` 호출
5. **결과 집계**:
   - `signals_true`: 신호 발생 횟수
   - `signals_false`: 신호 미발생 횟수
   - `long_signals` / `short_signals`: 방향별 신호
   - `regime_range_signals` / `regime_trend_signals`: Regime별 신호

**출력**: `docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json`

### 1.3 실행 결과

**기본 파라미터 (PHASE27-3)**:
```
데이터: 최근 30일 (2024-11-30 ~ 2024-12-30)
총 캔들: 8,612개
평가 캔들: 8,562개 (warmup 50개 제외)
신호 발생: 5,741개 (67.05%)
  - LONG: 2,798개 (48.7%)
  - SHORT: 2,943개 (51.3%)
  - RANGE Regime: 4,221개 (73.5%)
  - TREND Regime: 1,520개 (26.5%)
하루 평균 신호: 191.4개
```

**판정**: ⚠️ **신호 과다** (하루 191개는 너무 많음)

---

## 2. Auto-Calibration (Grid Search)

### 2.1 설계

**목표**:
- 하루 신호 수를 적정 범위(20~50개)로 조정
- Long/Short 균형 유지 (40~60%)
- RANGE/TREND Regime 분포 확인

**파라미터 그리드**:
```python
{
    'rsi_long_threshold': [42, 45, 48],
    'rsi_short_threshold': [52, 55, 58],
    'bb_std_main': [0.8, 1.0, 1.2],
    'bb_std_strong': [1.2, 1.5],
    'adx_trend_threshold': [20, 25, 30]
}
```

**조합 수**: 3 × 3 × 3 × 2 × 3 = **162개**

**탐색 데이터**: 최근 7일 (빠른 탐색)

### 2.2 실행 결과

**Top 3 파라미터 셋**:

| Rank | Set Name | Signals/Day | Long Ratio | Parameters |
|------|----------|-------------|------------|------------|
| 1 | set_52 | 139.4 | 54.7% | rsi_long=42, rsi_short=58, bb_main=1.2, bb_strong=1.5, adx_threshold=20 |
| 2 | set_49 | 144.1 | 54.7% | rsi_long=42, rsi_short=58, bb_main=1.2, bb_strong=1.2, adx_threshold=20 |
| 3 | set_34 | 150.6 | 54.7% | rsi_long=42, rsi_short=55, bb_main=1.2, bb_strong=1.5, adx_threshold=20 |

**선택**: **set_52** (하루 139.4개 신호)

**변경 사항**:
- `rsi_long_threshold`: 45 → **42** (더 공격적)
- `rsi_short_threshold`: 55 → **58** (더 공격적)
- `bb_std_main`: 1.0 → **1.2** (더 완화)
- `adx_trend_threshold`: 25 → **20** (TREND 구간 확대)

**판정**: ⚠️ **여전히 많음** (하루 139개)
- 하지만 기본 파라미터(191개)보다 27% 감소
- 30분 Real PAPER에서 실제 신호 발생 확인 필요

---

## 3. 30분 Real PAPER 설계

### 3.1 목표

**Primary**:
- **Strategy Signals (True) > 0**: 실제 신호 발생 확인
- **ERROR/CRITICAL = 0**: 안정성 검증
- **정상 종료**: Duration 정확히 30분

**Secondary**:
- **Ensemble Decisions > 0**: 신호 → Ensemble 파이프라인 확인
- **Orders Submitted ≥ 0**: 주문 파이프라인 확인 (옵션)

### 3.2 Config

**파일**: `configs/paper/phase27_4_single_symbol_30m_baseline_adx.yml`

**핵심 설정**:
```yaml
paper:
  duration_mode: "wall_clock"
  duration_hours: 0.5  # 30분 (0.5시간)
  clean_start: true

strategies:
  btc5m_baseline_v1:
    # Auto-Calibrated Parameters (Grid Search Top 1)
    rsi_long_threshold: 42
    rsi_short_threshold: 58
    bb_std_main: 1.2
    bb_std_strong: 1.5
    use_adx: true
    adx_period: 14
    adx_trend_threshold: 20
```

**ActivityTracker**:
```yaml
trade_activity_tracker:
  enabled: true
  log_interval: 60
  summary_file: "docs/PHASE27/phase27_4_single_symbol_30m_activity_summary.json"
```

### 3.3 실행 절차

1. **환경 준비**:
   - `trading_bot_env` 활성화
   - Docker 컨테이너 확인 (Redis, Postgres)
   - 이전 실행 데이터 정리 (옵션)

2. **실행**:
   ```bash
   python scripts/run_v2.py --mode paper --config configs/paper/phase27_4_single_symbol_30m_baseline_adx.yml
   ```

3. **모니터링**:
   - 진행률 로그 확인 (30초 단위)
   - ERROR/CRITICAL 로그 추적
   - 신호 발생 여부 확인

4. **결과 확인**:
   - ActivityTracker summary JSON 분석
   - `strategy_signals.true` > 0 확인
   - `ensemble_decisions.total` > 0 확인

---

## 4. Acceptance Criteria

### 4.1 MUST (필수 조건)

| 항목 | 기준 | 판정 |
|------|------|------|
| **Offline Signal Scan** | 30일 데이터에서 신호 발생 > 0 | ✅ PASS (5,741개) |
| **Grid Search** | 162개 조합 탐색 완료 | ✅ PASS |
| **Config 반영** | Top 1 파라미터 적용 | ✅ PASS |
| **단위 테스트** | 7/7 PASS | ✅ PASS |
| **30m PAPER 실행** | 정상 종료 (exit code 0) | ⏳ PENDING |
| **Strategy Signals (True)** | > 0 | ⏳ PENDING |
| **ERROR/CRITICAL** | = 0 | ⏳ PENDING |

### 4.2 SHOULD (권장 조건)

| 항목 | 기준 | 판정 |
|------|------|------|
| **Ensemble Decisions** | > 0 | ⏳ PENDING |
| **Orders Submitted** | ≥ 0 | ⏳ PENDING |
| **Signal Frequency** | 하루 20~50개 | ⚠️ PARTIAL (139개, 여전히 많음) |

### 4.3 최종 판정 기준

**PASS**:
- Offline Scan: ✅ 신호 발생 확인
- 30m PAPER: ✅ Strategy Signals (True) > 0
- 안정성: ✅ ERROR/CRITICAL = 0

**PARTIAL PASS**:
- Offline Scan: ✅ 신호 발생 확인
- 30m PAPER: ⚠️ Strategy Signals (True) = 0 (시장 상황)
- 안정성: ✅ ERROR/CRITICAL = 0

**FAIL**:
- Offline Scan: ❌ 신호 발생 없음
- 30m PAPER: ❌ 구조적 에러 발생

---

## 5. 기술적 세부사항

### 5.1 Duration 인식 문제 해결

**PHASE27-3 이슈**:
- Config `duration_minutes` 사용 시 엔진이 인식하지 못함
- 60분(3600초)으로 잘못 인식됨

**PHASE27-4 해결**:
- `duration_hours` 사용으로 변경
- 30분 = **0.5 hours**
- 10분 = **0.167 hours**

### 5.2 Signal Scan 최적화

**Warmup 처리**:
- 최소 50개 캔들 warmup
- 지표 계산 안정화 후 신호 평가

**진행률 로그**:
- 10% 단위로 진행률 출력
- 대용량 데이터 처리 시 사용자 피드백

**메모리 효율**:
- 신호 상세 정보는 처음 100개만 저장
- 전체 통계는 카운터로 관리

### 5.3 Grid Search 효율화

**탐색 데이터 축소**:
- 전체 30일 대신 최근 7일만 사용
- 탐색 시간 단축 (162개 조합 × 7일)

**정렬 기준**:
- 하루 신호 수를 30개에 가깝게 정렬
- `abs(signals_per_day - 30)` 최소화

---

## 6. 산출물

### 6.1 코드

1. **Signal Scan Harness**: `scripts/research/phase27_4_btc5m_baseline_signal_scan.py` (426 LOC)
2. **Config**: `configs/paper/phase27_4_single_symbol_30m_baseline_adx.yml` (236 LOC)
3. **단위 테스트**: `tests/test_phase27_4_btc5m_signal_scan.py` (7개 테스트)

### 6.2 데이터

1. **Offline Scan 결과**: `docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json`
   - 기본 파라미터 스캔 결과
   - Grid Search Top 10 결과
   - 신호 샘플 100개

2. **30m PAPER 결과**: `docs/PHASE27/phase27_4_single_symbol_30m_activity_summary.json` (예정)
   - ActivityTracker 요약
   - Strategy Signals 통계
   - Ensemble Decisions 통계

### 6.3 문서

1. **설계 문서**: `docs/PHASE27/PHASE27-4_BASELINE_SIGNAL_VALIDATION_DESIGN.md` (본 문서)
2. **실행 보고서**: `docs/PHASE27/PHASE27-4_BASELINE_SIGNAL_VALIDATION_REPORT.md` (예정)

---

## 7. 다음 단계

### 7.1 30m PAPER 완료 후

**성공 시 (Signals True > 0)**:
- ✅ PHASE27-4 COMPLETE 판정
- PHASE_ROADMAP 업데이트
- Git 커밋 (코드 + 문서 + 테스트)

**실패 시 (Signals True = 0)**:
- 파라미터 추가 완화 검토
- 더 긴 실행 (1시간) 재시도
- 백테스트로 과거 데이터 검증

### 7.2 PHASE27-5 (예정)

**옵션 A**: Multi-Symbol 확장
- Top 10 심볼로 확장
- 심볼별 신호 발생 확인

**옵션 B**: 신호 품질 분석
- 신호 → 수익성 상관관계 분석
- False Positive 필터링

**옵션 C**: 앙상블 복구
- PHASE19 Ensemble 프레임워크 복구
- 다중 전략 통합

---

## 8. 참고 문서

- `docs/PHASE27/PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_REPORT.md`
- `docs/PHASE27/PHASE27-2_STRATEGY_REDESIGN_DESIGN.md`
- `docs/PHASE27/PHASE27-3_ADX_INTEGRATION_DESIGN.md`
- `docs/PHASE27/PHASE27-3_ADX_INTEGRATION_REPORT.md`
- `PHASE_ROADMAP.md`

---

**작성일**: 2025-12-04  
**상태**: ✅ IN PROGRESS (30m PAPER 실행 중)  
**다음 단계**: 30m PAPER 완료 후 결과 분석 및 보고서 작성
