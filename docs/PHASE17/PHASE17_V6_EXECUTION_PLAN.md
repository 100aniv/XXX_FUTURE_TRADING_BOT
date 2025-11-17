# PHASE17 V6 REAL PAPER 12H Execution Plan

**작성일**: 2025-01-XX  
**목적**: Portfolio Budget SSOT 구현 검증 (V5/V5b 문제 해결)

---

## 📌 Executive Summary

### 문제 (V5/V5b)
```
Portfolio Budget 초과로 10분 내 Entry 완전 중단
- Position Sizer가 Budget 무시 → $14,700 요청
- Portfolio Manager가 $12,500 Budget 초과 검증 → BLOCK
```

### 해결 (V6)
```
Position Sizer에 available_budget 전달 (Budget SSOT)
- Position Sizer가 Budget 내에서만 크기 결정
- Portfolio Manager는 최종 검증만 수행
```

### 구현 완료
```
✅ PortfolioManager: get_available_budget() 추가
✅ PositionSizer: available_budget parameter 추가
✅ Engine: Budget 조회 및 전달
✅ Tests: 모든 시나리오 PASS
```

---

## 🎯 V6 실행 목표

| 지표 | V5/V5b | V6 목표 |
|------|--------|---------|
| **실행 시간** | ~10분 | 12시간 완주 |
| **Entry 수** | 38개 | 150-300개 |
| **Budget BLOCK** | 80%+ | <10% |
| **Portfolio Budget 초과** | ❌ FAIL | ✅ PASS |

---

## 🔧 환경 초기화 (Execution Mode)

### 1. Python 프로세스 종료
```powershell
# 기존 Python 프로세스 확인
Get-Process python -ErrorAction SilentlyContinue

# 종료 (필요 시)
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
```

### 2. Docker 확인
```powershell
# 상태 확인
docker ps -a --filter "name=trading"

# Redis, Postgres가 UP인지 확인
# trading_redis: Up
# trading_db_postgres: Up (healthy)
```

### 3. Redis 초기화
```powershell
# Redis FLUSHALL (모든 키 삭제)
docker exec trading_redis redis-cli FLUSHALL

# 확인
docker exec trading_redis redis-cli DBSIZE
# (integer) 0
```

### 4. 로그 백업 및 초기화
```powershell
# 로그 디렉토리로 이동
cd c:\Users\bback\OneDrive\Documents\future_alarm_bot\logs

# 백업 (타임스탬프)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item application.log "backup/application_v5_${timestamp}.log" -ErrorAction SilentlyContinue
Copy-Item trading.log "backup/trading_v5_${timestamp}.log" -ErrorAction SilentlyContinue

# 로그 초기화
"" | Out-File -FilePath application.log
"" | Out-File -FilePath trading.log
```

### 5. Virtual Environment 활성화
```powershell
cd c:\Users\bback\OneDrive\Documents\future_alarm_bot
.\trading_bot_env\Scripts\Activate.ps1
```

---

## 🚀 V6 실행 (Paper Mode)

### 실행 명령
```powershell
# 새 CMD 창에서 실행 (Execution Mode)
python scripts/run_paper.py --config configs/scalping/real_paper_12h_v6_phase17.yml
```

**예상 실행 시간**: 12시간 (wall_clock 모드)

### 핵심 로그 패턴 (모니터링)
```
✅ 정상 패턴:
[ENTRY CHECK] ... available_budget=$12,500
📉 [Budget Cap] Position capped by available budget: $9,000 → $4,500
✅ [ENTRY SUCCESS]
⚠️  [ENTRY REDUCED]

🔴 문제 패턴:
❌ [ENTRY BLOCK] reason=portfolio_check_failed detail="전략 예산 초과"
❌ [ENTRY BLOCK] reason=position_size_zero
```

---

## 📊 모니터링 체크포인트

### M5 (5분 체크포인트)
```powershell
# application.log 최근 100줄
Get-Content logs\application.log -Tail 100

# 확인 항목:
# ✅ Entry 발생 (≥1개)
# ✅ Budget Cap 로그 확인
# ❌ Portfolio Budget 초과 BLOCK 없어야 함
```

### M10 (10분 체크포인트)
```powershell
# 통계 확인
Select-String -Path logs\application.log -Pattern "\[ENTRY SUCCESS\]" | Measure-Object
Select-String -Path logs\application.log -Pattern "\[ENTRY REDUCED\]" | Measure-Object
Select-String -Path logs\application.log -Pattern "Budget Cap" | Measure-Object
Select-String -Path logs\application.log -Pattern "portfolio_check_failed" | Measure-Object

# 예상 결과:
# ENTRY SUCCESS: ≥3개
# ENTRY REDUCED: ≥2개
# Budget Cap: ≥1개
# portfolio_check_failed: 0개 (V5/V5b에서는 많음!)
```

### M30, M60, M120 (30분, 1시간, 2시간)
```powershell
# 누적 통계
Select-String -Path logs\application.log -Pattern "\[ENTRY SUCCESS\]" | Measure-Object
Select-String -Path logs\application.log -Pattern "\[ENTRY BLOCK\].*portfolio_check_failed" | Measure-Object

# 목표:
# M30: Entry ≥10개, Portfolio Budget BLOCK ≤1개
# M60: Entry ≥25개, Portfolio Budget BLOCK ≤2개
# M120: Entry ≥50개, Portfolio Budget BLOCK ≤5개
```

---

## 🛑 조기 종료 조건 (Auto-Restart)

### 종료 조건
1. **0 Entry 5분 지속**: 5분간 Entry 없음
2. **Portfolio Budget BLOCK 반복**: 3분 내 연속 5회 이상
3. **예외 발생**: Python exception
4. **프로세스 비정상 종료**: Exit code ≠ 0

### 재시작 절차
```powershell
# 1. 프로세스 종료
Stop-Process -Name python -Force

# 2. 로그 분석 (최근 100줄)
Get-Content logs\application.log -Tail 100

# 3. 문제 식별 및 Config 수정 (필요 시)
# 예: budget allocation 증가, max_position_notional 감소

# 4. 재실행
python scripts/run_paper.py --config configs/scalping/real_paper_12h_v6_phase17.yml
```

---

## 📈 성공 기준

### 정량적 기준
| 지표 | V6 목표 | 판정 |
|------|---------|------|
| **실행 시간** | ≥10시간 | 12H 목표의 83%+ |
| **Entry 수** | ≥150개 | 10분당 평균 2개+ |
| **Portfolio Budget BLOCK** | <10% | Entry의 10% 미만 |
| **ALLOW_REDUCED** | ≥70% | Exposure Guard 작동 |

### 정성적 기준
```
✅ Budget Cap이 정상 작동 (로그 확인)
✅ Position Sizer가 Budget 내에서만 크기 결정
✅ Portfolio Manager의 Budget 검증이 거의 통과 (BLOCK < 10%)
✅ 12시간 동안 Entry가 지속적으로 발생
```

---

## 📝 최종 결과 수집

### 로그 분석
```powershell
# 전체 통계
$logs = Get-Content logs\application.log
$entry_success = ($logs | Select-String "\[ENTRY SUCCESS\]").Count
$entry_reduced = ($logs | Select-String "\[ENTRY REDUCED\]").Count
$entry_block_portfolio = ($logs | Select-String "\[ENTRY BLOCK\].*portfolio_check_failed").Count
$budget_cap = ($logs | Select-String "Budget Cap").Count

Write-Host "=== V6 실행 결과 ==="
Write-Host "Entry Success: $entry_success"
Write-Host "Entry Reduced: $entry_reduced"
Write-Host "Portfolio Budget BLOCK: $entry_block_portfolio"
Write-Host "Budget Cap Applied: $budget_cap"
```

### 리포트 생성
```powershell
# TASK 6로 진행: 최종 리포트 작성
# docs/PHASE17/PHASE17_PORTFOLIO_BUDGET_FIX_V6_REPORT.md
```

---

## 🔄 V5 vs V6 비교 예상

| 항목 | V5 | V6 | 개선 |
|------|----|----|------|
| **실행 시간** | ~10분 | 12시간+ | 72배+ |
| **Entry 수** | 38개 | 150-300개 | 4-8배 |
| **Portfolio Budget BLOCK** | 80%+ | <10% | 90% 감소 |
| **Budget 활용률** | 50% (조기 중단) | 95%+ | 안정적 소진 |

---

**다음 작업**: V6 실행 → 모니터링 → TASK 6 최종 리포트
