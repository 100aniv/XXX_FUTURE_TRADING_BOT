# PHASE22-2 Execution Guide

**작성일**: 2025-11-22  
**목적**: PHASE22-2 Ensemble v2 Extended Validation 실행 가이드

---

## 1. 사전 준비 (Pre-flight Checklist)

### 1.1 환경 확인

**가상환경 활성화**:
```bash
# Windows
.\trading_bot_env\Scripts\activate

# Linux/Mac
source trading_bot_env/bin/activate
```

**Docker 서비스 확인**:
```bash
docker ps
# Postgres, Redis 컨테이너가 실행 중인지 확인
```

**DB 연결 테스트**:
```bash
python scripts/check_db_config.py
```

**Redis 초기화** (기존 Guard/쿨다운 상태 클리어):
```bash
# Redis CLI 접속
docker exec -it <redis-container-name> redis-cli

# 기존 Guard 키 삭제
FLUSHDB
# 또는 선택적 삭제
DEL flow_guardian:*
DEL strategy_cooldown:*
```

### 1.2 Config 검증

**Config 파일 확인**:
```bash
# Quick Smoke Test용
cat configs/paper/phase22_2_ensemble_quick.yml

# 12H Main Run용
cat configs/paper/phase22_2_ensemble_12h.yml
```

**주요 확인 사항**:
- [ ] `ensemble.enabled: true`
- [ ] 5개 전략 모두 `enabled: true`
- [ ] `symbols: [BTCUSDT]`
- [ ] `timeframe: 5m`
- [ ] `duration_mode: wall_clock`

### 1.3 로그/출력 준비

**디렉토리 생성 확인**:
```bash
# 자동 생성되지만 사전 확인
mkdir -p logs
mkdir -p scorecards/paper_phase22_2
```

---

## 2. Quick Smoke Test 실행 (30분)

### 2.1 실행 명령

**기본 실행** (30분):
```bash
python scripts/run_phase22_2_ensemble.py \
    --config configs/paper/phase22_2_ensemble_quick.yml \
    --duration-hours 0.5
```

**Clean-State 포함**:
```bash
python scripts/run_phase22_2_ensemble.py \
    --config configs/paper/phase22_2_ensemble_quick.yml \
    --duration-hours 0.5 \
    --clean-state
```

### 2.2 실시간 모니터링

**로그 Tail** (별도 터미널):
```bash
# 전체 로그
tail -f logs/phase22_2_*.log

# ERROR/CRITICAL만 필터링
tail -f logs/phase22_2_*.log | grep -E "CRITICAL|ERROR"
```

**트레이드 카운트 확인** (실행 중 별도 터미널):
```bash
python scripts/check_paper_trades.py
```

### 2.3 Acceptance Criteria (Quick Test)

**실행 후 확인 사항**:
- [x] 엔진 정상 시작 및 종료 (no crash)
- [x] 최소 3건 이상 트레이드 발생
- [x] 5개 전략 중 최소 2개 이상 신호 발생
- [x] CRITICAL/ERROR 로그 없음
- [x] Scorecard 정상 생성 (`scorecards/paper_phase22_2/{run_id}/`)

**결과 확인**:
```bash
# Run ID 확인 (로그에서 출력됨)
RUN_ID="20251122_XXXXXX_XXXX"

# Scorecard 확인
cat scorecards/paper_phase22_2/${RUN_ID}/scorecard.md

# Trades 확인
cat scorecards/paper_phase22_2/${RUN_ID}/trades.log
```

---

## 3. Main 12H Run 실행

### 3.1 실행 명령

**12시간 실행**:
```bash
python scripts/run_phase22_2_ensemble.py \
    --config configs/paper/phase22_2_ensemble_12h.yml \
    --duration-hours 12 \
    --clean-state
```

**백그라운드 실행** (nohup):
```bash
nohup python scripts/run_phase22_2_ensemble.py \
    --config configs/paper/phase22_2_ensemble_12h.yml \
    --duration-hours 12 \
    --clean-state \
    > logs/phase22_2_12h_console.log 2>&1 &

# PID 확인
echo $!
# 예: 12345
```

**tmux/screen 사용** (권장):
```bash
# tmux 세션 생성
tmux new -s phase22_2

# 실행
python scripts/run_phase22_2_ensemble.py \
    --config configs/paper/phase22_2_ensemble_12h.yml \
    --duration-hours 12 \
    --clean-state

# Detach: Ctrl+B, D
# Attach: tmux attach -t phase22_2
```

### 3.2 주기적 모니터링 (1시간마다)

**체크리스트**:
```bash
# 1. 프로세스 살아있는지
ps aux | grep run_phase22_2_ensemble.py

# 2. 로그에 CRITICAL/ERROR 없는지
tail -n 100 logs/phase22_2_*.log | grep -E "CRITICAL|ERROR"

# 3. 트레이드 카운트 증가하는지
python scripts/check_paper_trades.py

# 4. 포지션 비정상 누적 없는지 (미청산 < 5개)
# → Scorecard 또는 로그에서 확인

# 5. 특정 전략만 과도하게 거래하지 않는지
# → 최종 Report에서 분석
```

**이상 징후 발견 시**:
- **CRITICAL 로그**: 즉시 중단 (`Ctrl+C` 또는 `kill -SIGTERM <PID>`)
- **포지션 누적** (5개 초과): 수동 청산 또는 엔진 재시작 검토
- **특정 전략 80% 초과 편중**: Config 재조정 검토 (PHASE22-3에서 다룰 예정)

### 3.3 중간 결과 확인

**6시간 경과 시점 (중간 점검)**:
```bash
# Scorecard 미리보기 (실시간 생성되지 않으므로 종료 후 확인)
# 대신 로그에서 PnL 추출
grep "Total PnL" logs/phase22_2_*.log | tail -n 10

# 트레이드 수 확인
python scripts/check_trades_simple.py
```

### 3.4 Acceptance Criteria (12H Run)

**필수 조건** (PASS 기준):
- [x] 12H 동안 CRITICAL 로그 0건
- [x] ERROR 로그 < 10건 (일시적 네트워크 리트라이 제외)
- [x] FlowGuardian 비정상 STOP 없음
- [x] 5개 전략 모두 최소 1건 이상 트레이드 발생
- [x] 특정 전략 편중도 < 80%
- [x] Max Drawdown < 50%
- [x] Equity > Initial Balance × 0.5
- [x] 미청산 포지션 < 5개
- [x] DB/Redis 기록 누락 없음

**권장 조건** (NICE-TO-HAVE):
- [ ] Total Trades > 20
- [ ] Win-rate > 20%
- [ ] Total PnL > -$500

---

## 4. 결과 분석

### 4.1 Scorecard 확인

**실행 완료 후**:
```bash
RUN_ID="20251122_XXXXXX_XXXX"  # 로그에서 확인

# Scorecard 확인
cat scorecards/paper_phase22_2/${RUN_ID}/scorecard.md

# CSV 데이터 확인
cat scorecards/paper_phase22_2/${RUN_ID}/scorecard.csv
```

### 4.2 DB 트레이드 확인

**전략별 트레이드 분포**:
```bash
python scripts/check_trades_detail.py --run-id ${RUN_ID}
```

**SQL 직접 조회**:
```sql
-- Postgres에 접속 (docker exec 또는 psql)
SELECT 
    strategy,
    COUNT(*) as trade_count,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl
FROM paper_trades
WHERE run_id = '20251122_XXXXXX_XXXX'
GROUP BY strategy
ORDER BY trade_count DESC;
```

### 4.3 로그 분석

**ERROR/CRITICAL 추출**:
```bash
grep -E "CRITICAL|ERROR" logs/phase22_2_*.log > phase22_2_errors.txt
cat phase22_2_errors.txt
```

**전략별 신호 카운트**:
```bash
grep "Signal:" logs/phase22_2_*.log | grep -oP "strategy=\K\w+" | sort | uniq -c
```

---

## 5. 문제 해결 (Troubleshooting)

### 5.1 일반적인 이슈

**1) 엔진이 시작 후 즉시 종료**:
- **원인**: Config 오류, DB/Redis 연결 실패
- **해결**: 
  ```bash
  # Config 검증
  python -c "import yaml; print(yaml.safe_load(open('configs/paper/phase22_2_ensemble_quick.yml')))"
  
  # DB 연결 테스트
  python scripts/check_db_config.py
  ```

**2) WebSocket 연결 실패**:
- **원인**: 네트워크 불안정, Binance API 제한
- **해결**: 재시도 로직은 자동 처리됨, 로그에서 재연결 확인

**3) 트레이드 0건 발생**:
- **원인**: 전략 조건 너무 엄격, 시장 정체
- **해결**: Entry threshold 낮추기, 시장 활성 시간대 재실행

**4) 특정 전략만 거래 (90%+ 편중)**:
- **원인**: 해당 전략의 Entry 조건이 너무 느슨
- **해결**: PHASE22-3에서 파라미터 튜닝 예정

### 5.2 긴급 중단

**Graceful Shutdown**:
```bash
# Ctrl+C (SIGINT) 또는
kill -SIGTERM <PID>
# 엔진이 현재 캔들 처리 완료 후 종료
```

**강제 종료** (권장하지 않음):
```bash
kill -9 <PID>
# 데이터 손실 가능, 최후의 수단
```

---

## 6. 다음 단계

**Quick Smoke Test 완료 후**:
- [ ] Smoke Test 결과를 `PHASE22-2_EXTENDED_VALIDATION_DESIGN.md`의 Section 10에 기록
- [ ] 이슈 발견 시 수정 후 재실행

**12H Main Run 완료 후**:
- [ ] Complete Report 작성 (`PHASE22-2_EXTENDED_VALIDATION_REPORT.md`)
- [ ] Acceptance Criteria 평가 (PASS/FAIL)
- [ ] PHASE_ROADMAP 업데이트 (PHASE22-2 → COMPLETE)
- [ ] Git commit

---

**Document Version**: v1.0  
**Last Updated**: 2025-11-22  
**Author**: Windsurf AI (PHASE22-2 Execution Guide)
