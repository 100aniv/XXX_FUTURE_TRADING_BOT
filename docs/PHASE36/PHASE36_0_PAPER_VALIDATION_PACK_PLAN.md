# PHASE36-0: Paper Trading Validation Pack - 설계 문서

**Date**: 2025-12-20  
**Status**: 🟡 IN PROGRESS  
**Phase**: PHASE36-0 – Paper Trading Validation Pack (20m/1h/3h)  
**Purpose**: PHASE35-5 Backtest Validation Pack 다음 단계로, 실시간 Paper Trading 조건에서 검증 체계 구축  
**Acceptance**: TBD

---

## 0. Executive Summary

### 0.1 목표
- **Backtest → Paper 전환**: PHASE35-5에서 확립한 Backtest Validation Pack 다음 단계
- **실시간 조건 검증**: 레이트리밋, 네트워크, 데이터 피드 등 운영 리스크 포함
- **3단 검증 체계**: 20m Smoke / 1h Baseline / 3h Long-run으로 단계적 안정성 확인
- **단일 SSOT Runner**: 한 스크립트로 3단 검증을 일관되게 수행
- **재발 방지**: Backtest에서 발견된 이슈(numpy scalar, qualified query)가 Paper에서도 재현되지 않도록 계약 테스트 포함

### 0.2 PHASE35-5와의 차이점
| 항목 | PHASE35-5 (Backtest) | PHASE36-0 (Paper) |
|------|---------------------|-------------------|
| **데이터 소스** | Historical CSV (고정) | Real-time Feed (Binance API) |
| **실행 모드** | Backtest (시뮬레이션) | Paper (실시간, 가상 거래) |
| **Duration** | 날짜 범위 (7d/1m/3m) | Wall-clock 시간 (20m/1h/3h) |
| **운영 리스크** | 없음 | 레이트리밋, 네트워크 장애, 데이터 누락 |
| **검증 목표** | 전략 로직 정합성 | 실시간 인프라 안정성 |

### 0.3 SSOT 재사용 (ROOT SCAN 결과)

**재사용 가능한 기존 SSOT:**
1. **PHASE25-0 Long-run PAPER Harness** (`scripts/infra/phase25_0_long_run_paper.py`)
   - ✅ 2H+ 장시간 Paper 자동화 하네스 (완전 구현)
   - ✅ Pre-flight → Clean State → Run → Monitor → Analysis → Report 전체 플로우
   - ✅ 실시간 ERROR 감지 & 중단 메커니즘
   - ⚠️ 단, 2H 고정 (20m/1h/3h 가변 지원 필요)
   
2. **PHASE35-5 Validation Pack 구조** (`scripts/phase35/run_phase35_5_validation_pack.py`)
   - ✅ persist_trace 계측 (db_persist_called, db_insert_success)
   - ✅ DB evidence 수집 (qualified query: trading.trades)
   - ✅ AC (Acceptance Criteria) 체크 프레임워크
   - ✅ Artifacts 표준 경로 (artifacts/phase##/phase##_#/)
   - ✅ to_native() numpy 스칼라 변환 (재발 방지)

3. **Paper Entry Point** (`scripts/run_paper.py`)
   - ✅ PHASE23-3 Thin Wrapper
   - ✅ `engine.run_v2(mode='paper')` 호출
   - ✅ `--config`, `--duration-hours`, `--clean-state` 지원

4. **Contract Tests 패턴** (`tests/test_phase35_5_validation_pack_contract.py`)
   - ✅ Runner 구조 검증
   - ✅ SSOT 재사용 검증
   - ✅ DB/계측/artifacts 경로 검증

**재사용 불가 (신규 작성 필요):**
- 20m/1h/3h 가변 duration 지원 (PHASE25-0은 2H 고정)
- Paper 모드 특화 AC 체크 (레이트리밋 허용 횟수, 네트워크 재연결 등)
- Stage 개념 (smoke/baseline/longrun) 추가

---

## 1. 목적 (Purpose)

### 1.1 주요 목표
- **Paper Trading Validation Pack 구축**: Backtest에서 Paper로 전환하는 표준 검증 체계
- **운영 리스크 조기 발견**: 레이트리밋, 네트워크, 데이터 피드 등 실시간 조건에서만 나타나는 이슈 사전 차단
- **3단 검증 체계 표준화**: 
  - **20m Smoke**: 배관 검증 (데이터/주문/DB/계측)
  - **1h Baseline**: 기본 안정성 (메모리 누수, 지표 수집)
  - **3h Long-run**: 장시간 운영 (간헐 장애, 누적 오류)
- **완전 자동화**: 사용자는 단일 명령으로 3단 검증을 순차 실행 가능

### 1.2 배경
**PHASE35-5 완료 상태** (Backtest Validation Pack 확립):
- ✅ 7D/1M/3M Backtest 검증 완료
- ✅ 203 trades, 100% DB persist 성공
- ✅ 36/36 계약 테스트 PASS
- ✅ numpy scalar, qualified query 재발 방지 확정

**다음 단계: Paper Trading 검증 필요**
- Backtest는 "과거 데이터 재생"이므로 네트워크/레이트리밋/실시간 피드 문제를 검증 불가
- Live Trading 전에 Paper에서 운영 리스크를 검증해야 함
- PHASE_ROADMAP 권장 경로: PHASE35-5 → PHASE36-0 → PHASE37 (Live Pilot)

### 1.3 PHASE36-0이 해결하는 문제
**Before (AS-IS)**:
```
개발자가 수동으로:
1. Paper config 작성
2. Python 프로세스 종료
3. Docker 확인
4. clean_state_complete.py 실행
5. run_paper.py 실행 (duration 수동 지정)
6. 로그 파일 tail하며 ERROR 감시 (몇 시간)
7. 종료 후 DB/로그 수동 분석
8. 리포트 수동 작성
→ 총 소요 시간: 3H 실행 + 준비/분석 30분 = 3.5H (사람이 대기)
```

**After (TO-BE)**:
```
python scripts/phase36/run_phase36_0_paper_validation_pack.py --stage smoke --profile L4
python scripts/phase36/run_phase36_0_paper_validation_pack.py --stage baseline --profile L3
python scripts/phase36/run_phase36_0_paper_validation_pack.py --stage longrun --profile L3
→ 자동으로 전체 플로우 수행 + 리포트/JSON 생성
→ 개발자는 결과만 확인
```

---

## 2. 산출물 (Deliverables)

### 2.1 Scripts
- `scripts/phase36/run_phase36_0_paper_validation_pack.py` (단일 SSOT Runner)
- `scripts/phase36/preflight_phase36_0.py` (Preflight Check) - 또는 PHASE35-5 재사용
- `scripts/phase36/monitor_phase36_0.py` (실시간 모니터링, 선택) - 또는 기존 모듈 재사용

### 2.2 Tests
- `tests/test_phase36_0_paper_validation_pack_contract.py` (재발 방지 계약 테스트)

### 2.3 Artifacts
```
artifacts/phase36/phase36_0/
├── preflight/
│   └── preflight_evidence_{stage}.json
├── runs/
│   ├── phase36_0_{profile}_{stage}_{timestamp}_trace.json
│   └── ...
└── results/
    ├── phase36_0_{profile}_{stage}.json
    └── ...
```

### 2.4 Docs
- `docs/PHASE36/PHASE36_0_PAPER_VALIDATION_PACK_PLAN.md` (이 문서)
- `docs/PHASE36/PHASE36_0_PAPER_VALIDATION_PACK_REPORT.md` (실행 결과 리포트)

### 2.5 PHASE_ROADMAP 업데이트
- PHASE35-5 완료 체크 (이미 완료)
- PHASE36-0 추가 + 진행 상태 반영

---

## 3. Acceptance Criteria (AC)

### AC1: 단일 SSOT Runner로 Paper 3단 실행 가능
- `--stage smoke|baseline|longrun` 옵션 지원
- `--profile L4|L3|L0` 프로파일 지원
- `--symbol BTCUSDT` 심볼 지정 (기본 BTCUSDT)
- `--timeframe 15m` 타임프레임 지정 (기본 15m)
- Duration 자동 매핑:
  - smoke: 20분 (0.33h)
  - baseline: 1시간 (1.0h)
  - longrun: 3시간 (3.0h)

### AC2: 각 run에서 trades>0 + DB Insert 성공 + Report JSON 생성
- trades >= 1 (최소 1개 이상)
- db_insert_success == trades (100% 성공률)
- report JSON 생성: `reports/paper/paper_{timestamp}.json`
- artifacts 저장: `artifacts/phase36/phase36_0/results/` 에 결과 JSON

### AC3: 재발 방지 계약 테스트
**PHASE35-5에서 확립한 이슈가 Paper에서도 재현되지 않도록:**
- ✅ numpy scalar → Python native 변환 (`to_native()` 경로 유지)
- ✅ `database.enabled=True` 강제 (우회 금지)
- ✅ persist_trace 계측 (db_persist_called, db_insert_success 키 고정)
- ✅ qualified table query (`trading.trades` 유지, unqualified 금지)
- ✅ Paper 모드 특화:
  - 레이트리밋 429 에러 허용 (재시도 메커니즘 포함)
  - 네트워크 타임아웃 허용 (지수 백오프)
  - 데이터 피드 일시 중단 허용 (재연결)

### AC4: 기존 회귀 테스트 100% PASS
- PHASE35 계약 테스트 묶음 (SSOT 관련)
- 핵심 엔진/DB 관련 테스트 묶음
- 신규 PHASE36-0 계약 테스트 추가

### AC5: 문서/ROADMAP 동기화 + Git Commit + Push
- PLAN 문서 작성 완료
- REPORT 문서 생성 (실행 결과 포함)
- PHASE_ROADMAP.md 업데이트 (PHASE36-0 추가)
- Git commit + push origin main
- 대용량 artifacts는 .gitignore로 제외

---

## 4. 아키텍처 설계

### 4.1 Runner 구조 (PHASE25-0 + PHASE35-5 패턴 재사용)

```python
# scripts/phase36/run_phase36_0_paper_validation_pack.py

def main():
    args = parse_args()  # --stage, --profile, --symbol, --timeframe
    
    # STEP 1: Duration 매핑
    duration_map = {"smoke": 0.33, "baseline": 1.0, "longrun": 3.0}
    duration_hours = duration_map[args.stage]
    
    # STEP 2: Config 준비
    config = prepare_config(args.profile, args.symbol, args.timeframe, duration_hours)
    
    # STEP 3: Preflight (PHASE35-5 패턴)
    run_preflight(args.stage)
    
    # STEP 4: persist_trace 계측 (PHASE35-5 SSOT)
    reset_trace()
    instrument_save_trade_to_db()  # to_native() 포함
    
    # STEP 5: Engine 실행 (run_v2, mode='paper')
    run_paper_with_monitoring(config, duration_hours, args.stage)
    
    # STEP 6: DB Evidence 수집 (PHASE35-5 패턴)
    db_evidence = get_db_evidence(trial_id=config['run_id'])
    
    # STEP 7: AC 체크
    ac_results = check_acceptance_criteria(db_evidence, get_trace(), args.stage)
    
    # STEP 8: Artifacts 저장
    save_artifacts(args.stage, args.profile, ac_results, db_evidence)
    
    # STEP 9: Report 생성
    generate_report(args.stage, ac_results)
    
    return 0 if ac_results['all_pass'] else 1
```

### 4.2 Preflight (PHASE35-5 재사용 또는 최소 확장)
```python
# scripts/phase36/preflight_phase36_0.py (또는 기존 재사용)

def run_preflight(stage):
    # 1. Docker 체크
    check_docker_containers(['trading_db_postgres', 'trading_redis'])
    
    # 2. DB 연결 체크
    check_db_connection()
    
    # 3. DB cleanup (trading.trades)
    clean_db_trades()
    
    # 4. Redis cleanup (namespace 초기화)
    clean_redis_state()
    
    # 5. Evidence 저장
    save_preflight_evidence(stage)
```

### 4.3 Monitoring (PHASE25-0 패턴 재사용)
```python
def run_paper_with_monitoring(config, duration_hours, stage):
    # 1. 새 CMD 창에서 run_paper.py 실행
    process = start_paper_in_new_window(config, duration_hours)
    
    # 2. 실시간 로그 모니터링
    start_time = datetime.now()
    target_duration_sec = duration_hours * 3600
    
    while True:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Duration 경과 체크
        if elapsed >= target_duration_sec:
            break
        
        # 로그 tail & ERROR 패턴 감지
        if check_critical_error_in_logs():
            kill_process(process)
            return {'status': 'FAIL', 'reason': 'CRITICAL ERROR'}
        
        # 30초 주기
        time.sleep(30)
    
    return {'status': 'PASS'}
```

### 4.4 AC 체크
```python
def check_acceptance_criteria(db_evidence, persist_trace, stage):
    ac1 = db_evidence['trial_trades'] >= 1
    ac2 = persist_trace['db_insert_success'] == db_evidence['trial_trades']
    ac3 = persist_trace['db_persist_called'] > 0
    ac4 = report_json_exists()
    
    # Paper 특화: 레이트리밋 허용
    ac5 = rate_limit_429_count <= 10  # 허용 임계치
    ac6 = network_reconnect_count <= 5
    
    return {
        'ac1_trades_gt_zero': ac1,
        'ac2_db_persist_valid': ac2,
        'ac3_persist_trace_valid': ac3,
        'ac4_report_generated': ac4,
        'ac5_rate_limit_acceptable': ac5,
        'ac6_network_stable': ac6,
        'all_pass': all([ac1, ac2, ac3, ac4, ac5, ac6])
    }
```

---

## 5. 계약 테스트 (Contract Tests)

### 5.1 PHASE35-5 재발 방지 계약
```python
# tests/test_phase36_0_paper_validation_pack_contract.py

class TestPhase36_0_PaperValidationPackContract:
    def test_runner_script_exists(self):
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        assert runner_path.exists()
    
    def test_runner_has_stage_option(self):
        # --stage smoke|baseline|longrun 지원 검증
        ...
    
    def test_runner_forces_db_enabled(self):
        # database.enabled=True 강제 검증
        ...
    
    def test_runner_has_persist_trace(self):
        # persist_trace 계측 포함 검증
        ...
    
    def test_runner_uses_to_native(self):
        # to_native() 경로 유지 검증 (numpy scalar 방지)
        ...
    
    def test_runner_uses_qualified_query(self):
        # trading.trades (qualified) 사용 검증
        ...
    
    def test_runner_handles_rate_limit(self):
        # 429 에러 재시도 메커니즘 포함 검증
        ...
    
    def test_artifacts_directory_structure(self):
        # artifacts/phase36/phase36_0/ 표준 경로 검증
        ...
```

---

## 6. 실행 계획

### 6.1 STEP A: ROOT SCAN (완료)
✅ 재사용 SSOT 확정:
- PHASE25-0 Long-run PAPER Harness
- PHASE35-5 Validation Pack 구조
- Paper Entry Point (run_paper.py)
- Contract Tests 패턴

### 6.2 STEP B: PRE-FLIGHT
- [ ] 가상환경 활성화 확인
- [ ] Python 프로세스 정리
- [ ] Docker 상태 확인
- [ ] DB/Redis 연결 확인
- [ ] DB cleanup (trading.trades)

### 6.3 STEP C: IMPLEMENT
- [ ] Runner 구현 (`run_phase36_0_paper_validation_pack.py`)
- [ ] Preflight 구현 또는 재사용
- [ ] Monitor 구현 또는 재사용
- [ ] to_native() 계측 추가 (PHASE35-5 SSOT)

### 6.4 STEP D: TESTS
- [ ] Fast Gate (신규 모듈 테스트)
- [ ] Core Regression (PHASE35 계약 테스트)
- [ ] Full Suite (필요 시)

### 6.5 STEP E: RUN & VALIDATE
- [ ] Smoke (20m) 실행 → AC 체크
- [ ] Baseline (1h) 실행 → AC 체크
- [ ] Long-run (3h) 실행 → AC 체크

### 6.6 STEP F: DOCS
- [ ] REPORT 문서 작성
- [ ] PHASE_ROADMAP 업데이트

### 6.7 STEP G: GIT
- [ ] git commit
- [ ] git push origin main

---

## 7. 금지 사항 (DO NOT)

### 7.1 중복 구현 금지
- ❌ PHASE25-0 harness를 무시하고 처음부터 새로 작성
- ❌ PHASE35-5 persist_trace 패턴을 버리고 새 계측 방식 도입
- ✅ 기존 SSOT를 최대한 재사용하고 최소한만 확장

### 7.2 우회 금지
- ❌ `database.enabled=False`로 우회
- ❌ numpy scalar을 Python native로 변환하지 않음
- ❌ unqualified query (FROM trades) 사용
- ✅ PHASE35-5 재발 방지 룰 100% 준수

### 7.3 수동 실행 금지
- ❌ 사용자에게 "이제 수동으로 실행해주세요" 요청
- ❌ 로그 모니터링을 사용자에게 떠넘김
- ✅ 완전 자동화 (사용자는 결과만 확인)

---

## 8. 위험 요소 및 대응

### 8.1 레이트리밋 (429 Too Many Requests)
**위험**: Binance API 레이트리밋 초과로 Paper 실행 중단
**대응**:
- 지수 백오프 + jitter (1s → 2s → 4s → 8s, max 60s)
- 최대 재시도 횟수 제한 (10회)
- 429 카운트 <= 10 허용 (AC5)

### 8.2 네트워크 타임아웃
**위험**: 간헐적 네트워크 장애로 데이터 피드 중단
**대응**:
- Connection timeout: 10s
- Read timeout: 30s
- 재연결 메커니즘 (최대 5회)
- 네트워크 재연결 카운트 <= 5 허용 (AC6)

### 8.3 메모리 누수
**위험**: 장시간 실행 시 메모리 누수로 프로세스 종료
**대응**:
- 1h/3h 실행 중 메모리 사용량 모니터링
- 임계치 초과 시 경고 (FAIL 아님, 경고만)

### 8.4 로그 파일 비대
**위험**: 3h 실행 시 로그 파일이 수 GB로 증가
**대응**:
- 로그 tail만 모니터링 (마지막 200줄 유지)
- 전체 로그는 파일로 저장 (검증 후 확인)

---

## 9. 다음 단계 (PHASE36-0 완료 후)

### 9.1 PHASE36-1: Extended Paper Validation (선택)
- 6H/12H/24H 장시간 Paper 검증
- 멀티 심볼 Paper 검증

### 9.2 PHASE37: Live Trading Pilot
- 소규모 자본으로 Live 실전 검증
- Paper vs Live 성과 비교

---

## 10. 참고 문서
- `docs/PHASE35/PHASE35_5_VALIDATION_PACK_REPORT.md`
- `docs/PHASE25/PHASE25-0_LONG_RUN_PAPER_DESIGN.md`
- `docs/PHASE17/PHASE17_V6_1_EXECUTION_30MIN_CHECKPOINT.md`
- `PHASE_ROADMAP.md`

---

**End of PLAN Document**
