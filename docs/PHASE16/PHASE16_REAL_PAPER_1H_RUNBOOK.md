# PHASE16 REAL PAPER 1시간 테스트 Runbook

## 📌 개요

이 문서는 **REAL PAPER 1시간 테스트**를 실행하고 모니터링하는 절차를 정의합니다.

**테스트 목표**:
- ✅ 현실 시계 54분 이상 연속 실행
- ✅ Entry Open ≥ 1, Closed ≥ 1
- ✅ 치명적 에러/Traceback 없음
- ✅ Scorecard 정상 생성

---

## 🔧 STEP 0: 환경 체크

### 0-1. 가상환경 활성화

```bash
# PowerShell (Windows)
& .\trading_bot_env\Scripts\Activate.ps1

# Bash (Linux/Mac)
source trading_bot_env/bin/activate
```

**확인**:
```bash
python --version  # Python 3.9+
pip list | grep -E "pandas|numpy|redis|websocket"
```

### 0-2. Docker 컨테이너 상태 확인

```bash
# 컨테이너 실행 확인
docker ps | grep -E "trading_redis|trading_db"

# 예상 출력:
# CONTAINER ID   IMAGE                    STATUS
# abc123...      redis:7-alpine           Up 2 hours
# def456...      postgres:15-alpine       Up 2 hours
```

### 0-3. Redis 연결 확인

```bash
# Redis PING
docker exec trading_redis redis-cli PING
# 예상 출력: PONG

# Redis DBSIZE
docker exec trading_redis redis-cli DBSIZE
# 예상 출력: (integer) 0 (또는 기존 데이터)
```

### 0-4. PostgreSQL 연결 확인

```bash
# PostgreSQL 연결 테스트
docker exec trading_db_postgres psql -U trading_user -d trading_db -c "SELECT 1"
# 예상 출력: ?column?
#           1
```

---

## 🧹 STEP 1: 초기화

### 1-1. Redis 초기화

```bash
docker exec trading_redis redis-cli FLUSHALL
docker exec trading_redis redis-cli DBSIZE
# 예상 출력: (integer) 0
```

### 1-2. Scorecard 디렉토리 초기화

```bash
# PowerShell (Windows)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (Test-Path "scorecards\paper_phase16") {
    Move-Item -Path "scorecards\paper_phase16" -Destination "scorecards\paper_phase16_backup_$timestamp" -Force
}
New-Item -ItemType Directory -Path "scorecards\paper_phase16" -Force | Out-Null
Write-Host "✅ Scorecard 초기화: $timestamp"

# Bash (Linux/Mac)
timestamp=$(date +%Y%m%d_%H%M%S)
[ -d "scorecards/paper_phase16" ] && mv "scorecards/paper_phase16" "scorecards/paper_phase16_backup_$timestamp"
mkdir -p "scorecards/paper_phase16"
echo "✅ Scorecard 초기화: $timestamp"
```

### 1-3. 로그 초기화

```bash
# PowerShell (Windows)
"" | Set-Content logs\application.log

# Bash (Linux/Mac)
> logs/application.log
```

---

## 🚀 STEP 2: REAL PAPER 1h 실행

### 2-1. 기본 실행 (wall_clock 모드)

```bash
python scripts/run_paper.py \
  --strategy scalping \
  --symbol BTCUSDT \
  --timeframe 3m \
  --duration-hours 1 \
  --duration-mode wall_clock \
  --config configs/scalping/real_paper_1h.yml
```

**예상 로그**:
```
🚀 PHASE16 Paper Trading - REAL Mode
📊 Strategy: scalping
💱 Symbol: BTCUSDT
⏱️  Timeframe: 3m
⏳ Duration: 1.00 hours
📍 Duration 모드: wall_clock (1.00h)
⏱️  [WALL-CLOCK] Duration 모드 시작: 1.00시간 (3600초)
```

### 2-2. 실행 시간 기록

```
시작 시간: [현재 시간 기록]
예상 종료: [시작 + 1시간]
```

---

## 📊 STEP 3: 모니터링 (첫 60분)

### 3-1. 체크포인트 일정

| 시간 | 항목 | 기준 |
|------|------|------|
| **5분** | Entry Open | ≥ 10 |
| **5분** | 에러 | 없음 |
| **10분** | Entry Open | ≥ 20 |
| **10분** | Redis DBSIZE | > 0 |
| **15분** | Entry Open | ≥ 30 |
| **15분** | Closed | ≥ 10 |
| **30분** | Entry Open | ≥ 60 |
| **30분** | Closed | ≥ 30 |
| **45분** | Entry Open | ≥ 90 |
| **45분** | Closed | ≥ 50 |
| **60분** | 프로세스 | 정상 종료 |
| **60분** | Scorecard | 생성됨 |

### 3-2. 모니터링 명령어

#### Entry Open 수 확인

```bash
# PowerShell (Windows)
(Get-Content logs\application.log | Select-String "ENTRY OPEN" | Measure-Object).Count

# Bash (Linux/Mac)
grep -c "ENTRY OPEN" logs/application.log
```

#### Closed 수 확인

```bash
# PowerShell (Windows)
(Get-Content logs\application.log | Select-String "SL:|TP:" | Measure-Object).Count

# Bash (Linux/Mac)
grep -c "SL:\|TP:" logs/application.log
```

#### 에러 확인

```bash
# PowerShell (Windows)
Get-Content logs\application.log | Select-String "ERROR|Traceback" | Select-Object -Last 10

# Bash (Linux/Mac)
grep -E "ERROR|Traceback" logs/application.log | tail -10
```

#### Redis 활동도

```bash
docker exec trading_redis redis-cli DBSIZE
```

#### 최근 로그 확인

```bash
# PowerShell (Windows)
Get-Content logs\application.log -Tail 50

# Bash (Linux/Mac)
tail -50 logs/application.log
```

### 3-3. 실시간 모니터링 스크립트 (선택)

```bash
# 매 30초마다 상태 확인
while true; do
  clear
  echo "=== REAL PAPER 1h 모니터링 ==="
  echo "시간: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""
  echo "Entry Open: $(grep -c 'ENTRY OPEN' logs/application.log)"
  echo "Closed: $(grep -c 'SL:\|TP:' logs/application.log)"
  echo "Redis DBSIZE: $(docker exec trading_redis redis-cli DBSIZE)"
  echo ""
  echo "최근 로그:"
  tail -5 logs/application.log
  echo ""
  sleep 30
done
```

---

## ✅ STEP 4: 종료 및 검증

### 4-1. 프로세스 종료 확인

프로세스가 자동으로 종료되거나, 60분 후 수동 종료:

```bash
# PowerShell (Windows)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Bash (Linux/Mac)
pkill -f "run_paper.py"
```

### 4-2. Scorecard 생성 확인

```bash
# PowerShell (Windows)
Get-ChildItem "scorecards\paper_phase16" -Recurse -Filter "scorecard.csv"

# Bash (Linux/Mac)
find scorecards/paper_phase16 -name "scorecard.csv"
```

**예상 경로**:
```
scorecards/paper_phase16/{run_id}/scorecard.csv
```

### 4-3. Scorecard 내용 확인

```bash
# PowerShell (Windows)
Get-Content "scorecards\paper_phase16\*\scorecard.csv" | Select-Object -First 10

# Bash (Linux/Mac)
head -10 scorecards/paper_phase16/*/scorecard.csv
```

**예상 내용**:
```
trade_id,symbol,side,entry_price,exit_price,qty,entry_time,exit_time,pnl,pnl_pct,reason
1,BTCUSDT,LONG,45000.00,45100.00,0.1,2025-11-17T14:30:00,2025-11-17T14:35:00,10.00,0.22%,TP
2,BTCUSDT,SHORT,45100.00,45050.00,0.1,2025-11-17T14:36:00,2025-11-17T14:40:00,5.00,0.11%,TP
...
```

---

## 📋 STEP 5: PASS/FAIL 판정

### PASS 기준 (모두 충족해야 함)

- ✅ **현실 시계 54분 이상 실행**
  ```bash
  # 로그에서 시작/종료 시간 확인
  grep "WALL-CLOCK" logs/application.log | head -1  # 시작
  grep "WALL-CLOCK" logs/application.log | tail -1  # 종료
  ```

- ✅ **Entry Open ≥ 1**
  ```bash
  grep -c "ENTRY OPEN" logs/application.log
  ```

- ✅ **Closed ≥ 1**
  ```bash
  grep -c "SL:\|TP:" logs/application.log
  ```

- ✅ **치명적 에러/Traceback 없음**
  ```bash
  grep -E "ERROR|Traceback|RuntimeError" logs/application.log | wc -l
  # 결과: 0 (또는 경고만 있고 에러 없음)
  ```

- ✅ **Scorecard 생성됨**
  ```bash
  ls -la scorecards/paper_phase16/*/scorecard.csv
  ```

### FAIL 기준 (하나라도 해당하면 FAIL)

- ❌ **현실 시계 54분 미만 실행**
- ❌ **Entry Open = 0** (거래 없음)
- ❌ **Closed = 0** (청산 없음)
- ❌ **Traceback 또는 RuntimeError 발생**
- ❌ **Scorecard 미생성**

---

## 📝 STEP 6: 결과 리포트 작성

테스트 완료 후 다음 정보를 기록:

```markdown
# PHASE16 REAL PAPER 1h 테스트 결과

## 테스트 정보
- 실행 날짜: [YYYY-MM-DD]
- 시작 시간: [HH:MM:SS]
- 종료 시간: [HH:MM:SS]
- 실제 실행 시간: [MM분 SS초]
- Duration 모드: wall_clock
- Run ID: [run_id]

## 거래 통계
- Entry Open: [수]
- Closed: [수]
- 평균 거래 시간: [분]
- 최대 손실: [%]
- 최대 수익: [%]

## 시스템 상태
- Redis: ✅ 정상
- PostgreSQL: ✅ 정상
- Telegram: ✅ 정상 (또는 ⚠️ 비활성화)
- Guard 트리거: [횟수]

## 판정
- **결과**: PASS / FAIL
- **사유**: [상세 설명]
- **다음 단계**: [12h 테스트 진행 / 디버깅 필요 등]
```

---

## 🔗 관련 문서

- `docs/PHASE16/PHASE16_REAL_PAPER_DURATION_DESIGN.md`: Duration 설계
- `docs/PHASE16/PHASE16_ENGINE_STRUCTURAL_FIXES.md`: 구조적 수정 내역
- `docs/PHASE16/PHASE16_REAL_PAPER_MODE.md`: REAL PAPER 모드 개요

---

**작성일**: 2025-11-17  
**상태**: Runbook 완성, 테스트 대기
