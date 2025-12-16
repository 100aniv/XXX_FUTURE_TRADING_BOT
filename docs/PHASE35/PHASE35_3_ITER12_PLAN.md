# PHASE35-3 ITER12 PLAN: 1M Baseline + OOS + E2E DailyCap 실증

**작성일**: 2025-12-16  
**전제조건**: PHASE35-2 ITER11 완료 (check_order 차단 로직 구현)  
**목표**: 1M/OOS 백테스트 + Daily Cap E2E 연결 + 증거 기반 검증

---

## Executive Summary

**ITER12 목표**: "거래가 실제로 발생하는 검증 루프" 자동화 고정

### 핵심 과제
1. **EC4 먼저**: record_trade() E2E 연결 (체결 → 카운터 증가 증거)
2. **EC1**: Signal Window 자동 선정 (trades=0 근본 차단)
3. **EC2**: 1M Baseline 실행 (SSOT/KPI/재현성)
4. **EC3**: OOS Validation (IS 대비 KPI 비교)
5. **EC5**: Fast Gate + Core Regression 100% PASS
6. **EC6**: 문서/ROADMAP/Git + URL 출력

---

## EC1: Signal Sanity (trades > 0 보장)

**문제**: 이전 ITER에서 "1M 백테스트 실행 → trades=0" 반복 발생

**해결책**: Window Finder로 사전 검증

### 구현: find_signal_windows.py

**경로**: `scripts/phase35/find_signal_windows.py`

**기능**:
1. 2024년 여러 구간(7D 단위)을 샘플링
2. 각 구간별 빠른 스캔 (trades, consensus fail ratio, runtime)
3. `artifacts/phase35/iter12/window_scan.json` 저장

**최소 요구사항**:
- trades > 0인 1M 구간 1개 이상 발견
- 발견 실패 시: ensemble 파라미터 제한적 완화 (Light 프로파일)
  - confidence_threshold: 0.70 → 0.55 (단계적)
  - min_votes: 2 → 1 (최후 수단)
  - **완화는 DecisionTrace 분포로 수치 근거 필요**

### Exit Criteria (EC1)
- ✅ trades > 0인 1M 구간 선정
- ✅ window_scan.json 생성
- ✅ 선정 근거 (DecisionTrace 분포 포함)

---

## EC2: 1M Baseline 실행 (SSOT)

**목표**: Production 성능 기준선 확립

### 실행 구간
- **IS (In-Sample)**: EC1에서 선정된 1M 구간 (예: 2024-11-01 ~ 2024-11-30)

### 산출물 SSOT
1. **summary.json** (KPI SSOT)
   - 10종 KPI: Total Return, CAGR, Max DD, Calmar, Sharpe, Sortino, Max Consec Loss, Win Rate, Profit Factor, Avg Duration
2. **repro.json** (재현성 메타데이터)
   - git_commit, env_info, seed, config_hash
3. **effective_config.yaml** (실행 시 사용된 최종 config)
4. **decision_trace_summary.json** (상위 reason 분포)
5. **timing.json** (실행 시간 프로파일)

### Acceptance 체크 (자동)
- trades > 0 (0이면 즉시 FAIL → EC1로 회귀)
- KPI mismatch 감지/교정 로그 확인
- summary.json에 riskguard 섹션 존재 (daily_trades, blocks)

### Exit Criteria (EC2)
- ✅ 1M 백테스트 완료
- ✅ summary.json 생성 (KPI 10종)
- ✅ repro.json + effective_config.yaml + decision_trace_summary.json + timing.json
- ✅ trades > 0 확인
- ✅ riskguard stats 포함

---

## EC3: OOS Validation

**목표**: 오버피팅 방지 검증

### 실행 구간
- **OOS (Out-of-Sample)**: IS 직후 7~14D (예: 2024-12-01 ~ 2024-12-14)

### KPI 비교표 (최소)
| Metric | IS | OOS | Delta |
|--------|----|----|-------|
| Trades | X | Y | - |
| Win Rate (%) | X | Y | ±Z% |
| Sharpe Ratio | X | Y | ±Z |
| Max DD (%) | X | Y | ±Z% |
| Avg PnL/Trade | X | Y | ±Z |
| Guard Blocks | X | Y | - |

### 검증 기준
- OOS trades > 0 (0이면 FAIL)
- IS/OOS Sharpe 차이 < 50% (느슨하게 설정, 초기 단계)
- IS/OOS Win Rate 차이 < 15%

### Exit Criteria (EC3)
- ✅ OOS 백테스트 완료
- ✅ IS vs OOS 비교표 생성
- ✅ trades > 0 확인
- ✅ 오버피팅 검증 통과

---

## EC4: Daily Cap E2E 훅 연결 (최우선)

**문제**: ITER11에서 check_order() 차단 로직은 구현했지만, 실제 체결 후 record_trade() 호출 연결은 미완료

**목표**: "코드에 함수 있음" → "실제 흐름에서 불림" 증거 확보

### 구현 위치 탐색
1. **Execution 흐름 파악**:
   - order fill / trade open / position open 이벤트
   - executor, broker, exchange adapter
   - RiskManager.check_order() 호출 지점

2. **E2E 연결 후보**:
   - 체결 확정 후 훅 (가장 덜 침습적)
   - Engine.on_fill() 또는 유사 콜백

### 구현 정책
- **Entry만 카운트**: `reduce_only=False AND side not in ['close', 'exit']`
- **Timestamp**: 체결 timestamp 우선 (재현성)
- **trade_id**: 중복 방지 가능한 SSOT 키 (주문 ID 또는 체결 ID)

### 테스트 (단위 + 최소 통합)
**파일**: `tests/test_phase35_iter12_e2e_daily_cap.py`

1. **test_e2e_record_trade_called**: 가짜 fill 이벤트 → record_trade 카운트 증가
2. **test_e2e_cap_block**: cap 도달 후 check_order block + GUARD_MAX_TRADES_PER_DAY telemetry

### Exit Criteria (EC4)
- ✅ record_trade() 호출 지점 연결
- ✅ 단위 테스트 2/2 PASS
- ✅ 로그/카운터로 E2E 증거 확보

---

## EC5: Gates (Fast Gate + Core Regression)

### Fast Gate (SSOT)
**위치**: `scripts/gates/fast_gate.sh` 또는 `.ps1`

**항목**:
1. docs layout 체크
2. shadowing 체크
3. required secrets 체크
4. `python -m compileall`
5. roadmap sync 체크 (PHASE35-2 완료 상태 확인)

**실패 시**: 즉시 중단 (Exit != 0)

### Core Regression (SSOT)
**위치**: 기존 프로젝트 SSOT 탐색 → 없으면 신규 생성

**최소 구성** (신규 생성 시):
- `scripts/gates/core_regression.ps1` (또는 .sh)
- 단위 테스트 핵심 subset (예: test_risk_manager, test_portfolio, test_engine 핵심)
- 실행 시간 < 5분

### Exit Criteria (EC5)
- ✅ Fast Gate 100% PASS
- ✅ Core Regression 100% PASS

---

## EC6: 문서/ROADMAP/Git

### 문서 작성
**파일**: `docs/PHASE35/PHASE35_3_ITER12_REPORT.md`

**필수 포함 사항**:
1. EC1~EC6 체크리스트 + 증거 (artifact 경로/로그)
2. Window scan 결과 요약표
3. Baseline vs OOS 비교표
4. Daily cap E2E 증거 (테스트명/로그/카운터 스냅샷)
5. Fast Gate + Core Regression 로그
6. Git compare URL + Changed Files URLs

### ROADMAP 업데이트
**파일**: `PHASE_ROADMAP.md`

**업데이트 위치**: PHASE35 섹션
- PHASE35-2 완료 (ITER11까지)
- PHASE35-3 ITER12 완료 상태 반영

### Git Workflow
1. `git status` 증거
2. `git add` 변경 파일
3. `git commit -m "PHASE35-3 ITER12: 1M baseline + OOS + E2E daily cap"`
4. `git push origin main`

### 최종 출력 (필수)
```
================================================================================
PHASE35-3 ITER12 최종 결과
================================================================================

✅ EC1-EC6 ALL PASS
✅ X/X TESTS PASSED
✅ Git Commit + Push 완료

COMPARE_URL:
https://github.com/100aniv/XXX_FUTURE_TRADING_BOT/compare/[PREV]...[HEAD]

CHANGED_FILES (N개):
1. [file1]
   - blob: https://github.com/.../blob/[HEAD]/[file1]
   - raw:  https://raw.githubusercontent.com/.../[HEAD]/[file1]
...

================================================================================
다음 진도: [한 줄 결론]
================================================================================
```

### Exit Criteria (EC6)
- ✅ ITER12 REPORT 작성
- ✅ ROADMAP 동기화
- ✅ Git commit + push 성공
- ✅ Compare URL + Changed Files URLs 출력

---

## 실행 순서 (Strict)

```
STEP 0: 컨텍스트 로드 ✅
STEP 1: PLAN 수립 ✅
STEP 2: PROJECT SCAN (기존 모듈 파악)
STEP 3: FAST GATE 실행
STEP 4: EC4 - Daily Cap E2E 훅 연결 (최우선)
STEP 5: EC1 - Signal Window 자동 선정
STEP 6: EC2 - 1M Baseline 실행
STEP 7: EC3 - OOS Validation
STEP 8: EC5 - Core Regression
STEP 9: EC6 - 문서/ROADMAP 동기화
STEP 10: Git Commit + Push
STEP 11: 최종 출력 (URLs)
```

---

## 금지 사항

1. **사용자 개입 요구**: "수동으로 파일 수정" 절대 금지
2. **우회/부분완료**: 모든 EC 달성까지 자동 재시도
3. **사이드퀘스트**: AC 밖 작업 금지
4. **trades=0 방치**: EC1 미달성 시 즉시 FAIL → 원인 계측 후 재시도

---

## 성공 기준

**ITER12 COMPLETE**:
- ✅ EC1: Signal Window 선정 (trades > 0 보장)
- ✅ EC2: 1M Baseline 실행 (SSOT 완비)
- ✅ EC3: OOS Validation (IS 대비 비교)
- ✅ EC4: Daily Cap E2E 증거 확보
- ✅ EC5: Fast Gate + Core Regression 100% PASS
- ✅ EC6: 문서/ROADMAP/Git + URLs

**다음 단계**: PHASE35-3 ITER13 (운영 기준 + 킬스위치) 또는 PHASE35-4 (3M Validation)

---

**ITER12 PLAN 종료**
