# PHASE8 → PHASE9 MASTER PLAN (Latest)

## 📌 개요
PHASE8은 "백테스트 인프라 재건 + 재현성 확보 + 데이터 검증"을 목표로 진행되었고,  
PHASE8-5까지 모두 100% 완료되어 *환경/데이터/엔진은 정상*이라는 결론을 획득했다.

PHASE9는 **전략 성능 개선 단계**로 진입하며,  
특히 scalping 전략에 대해 "가드/필터/리스크에 눌린 순수 전략 성향"을 먼저 분석한 뒤,  
TP/SL 튜닝 → 파라미터 조정 → 변동성 기반 적응을 순차적으로 진행한다.

---

# ✅ PHASE8 요약

## ✔ PHASE8-1: Config/Baseline 통합
- base.yml 구조화
- modes/backtest_clean.yml 생성
- config_loader 병합 순서 확립
- effective_config.yml 스냅샷 기능

## ✔ PHASE8-2: Backtest Engine 연결
- run_backtest.py 실제 엔진 연동
- DB 격리 실행 (load_existing=False)
- Redis dedup OFF
- DB INSERT 제약 에러 해결 (21개 컬럼 전체 명시)
- mode=backtest_clean CHECK 제약 추가

## ✔ PHASE8-3: 30일 기준선 성능 측정
- scalping 30일 baseline
- 결과: Trades=25, PF=0.68 → 성능 부족 확인

## ✔ PHASE8-4: 데이터 투명성 확보
- Raw CSV vs Used window 로깅
- days 슬라이싱 완전 정합
- Scorecard Period 정보 추가

## ✔ PHASE8-5: CSV 품질 검증 + 기간별 분석
- CSV 품질: 100/100 (missing/duplicate/gap = 0)
- 10~12월 기간별 백테스트 비교
- 결과: 평균 0.19 trades/day → 전략 문제로 확정

---

# 🎯 PHASE9 목표

## 핵심 목적
1. **가드/필터 OFF 상태에서의 순수 전략 베이스라인 확보**
2. **전략 구조 및 파라미터 문서화**
3. **과도한 필터링/진입 억제 요소 제거**
4. **TP/SL 비율 최적화**
5. **변동성 적응(ATR 기반) 전략 도입 준비**

---

# 📌 PHASE9 상세 계획

## 🔥 PHASE9-0: `backtest_raw` 모드 구축 (가드 OFF 환경)
### 목표
- 기존 `backtest_clean`은 "격리 환경 + FULL 가드"  
- 새로운 `backtest_raw`는:
  - 격리는 유지
  - 리스크·포지션·엔진 주요 가드는 최소화  
  - → 순수 전략 성향을 확인하는 연구용 모드

### 작업 항목
- configs/modes/backtest_raw.yml 생성
- exposure guard OFF or very minimal
- flash_guard OFF
- max_trades_per_day 제거 또는 대폭 완화
- extreme_loss_guard 완화 (계좌 손실 보호 수준만 최소 유지)
- run_backtest.py에서 mode=backtest_raw 지원
- baseline 비교 문서 생성:
  - backtest_clean vs backtest_raw  
  - 3개 기간(10월/11월/12월) 비교

문서 출력:  
`docs/PHASE9/PHASE9-0_GUARD_BASELINE.md`

---

## 🔥 PHASE9-1: scalping 전략 구조 분석
### 목표
- 전략 로직을 완전히 가시화하여 어떤 부분을 튜닝할지 근거 확보

### 작업 항목
- Entry logic 전체 정리
- Filters (추세/세션/변동성/플로우 필터 등)
- Exit logic (TP/SL/time/trailing)
- Risk logic
- 모든 hyperparameter 목록화 (튜닝 가능 여부 포함)

문서 출력:  
`docs/PHASE9/SCALPING_STRATEGY_MAP.md`

---

## 🔥 PHASE9-2: 단순 파라미터 튜닝
### 목표
- 순수 baseline 대비 가장 문제되는 파트를 수치로 교정
  - 진입 조건 완화
  - TP/SL 비율 수정
  - 변동성 기반 동적 레버리지/SL 도입 준비

문서 출력:  
`docs/PHASE9/PHASE9-2_TUNING_RESULTS.md`

---

# 📦 산출물 관리 (Windsurf 자동 생성)
- PHASE9-0_GUARD_BASELINE.md
- SCALPING_STRATEGY_MAP.md
- PHASE9-2_TUNING_RESULTS.md
- 각 백테스트 run artifacts
- 변경된 configs/modes/*.yml
- run_backtest.py 수정

---

# 🔒 RULE (PHASE9 공통 규칙)

1. **전략 코드 수정 시 항상 문서 먼저!**
2. **PHASE9에서는 엔진/DB/collector는 절대 건드리지 말 것**
3. **튜닝 단위는 명확한 근거를 남길 것**
4. **각 실험은 반드시 Run ID + config snapshot 포함**
5. **모든 실험은 backtest_raw → backtest_clean 순으로 진행**
6. **문서 없는 코드는 생성 금지**

---

# 🚀 배포/PR 정책
- 각 단계는 1 commit 단위로 PR
- 문서 1개 + 코드 1개 → 1 PR
- PHASE9 완료 시 전체 review 진행 후 PHASE10 준비