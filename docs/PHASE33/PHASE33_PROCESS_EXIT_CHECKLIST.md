# PHASE33: 프로세스 종료 검증 체크리스트

**목적**: 백테스트/PAPER 실행 후 프로세스 종료를 **기계적으로** 검증  
**작성일**: 2024-12-12

---

## 문제 배경

**이슈**:
- 백그라운드 실행 시 상태 확인 도구가 불안정
- 로그 파일 생성 지연으로 "진행 확인 불능" 상황 발생
- 프로세스 잔존 여부를 명확히 판단하기 어려움

**목표**:
- **동기(synchronous) 실행** 우선
- **3종 종료 조건**으로 명확한 검증
- **재현 가능한 절차** 문서화

---

## 종료 검증 3종 세트

### 1. Exit Code 확인
```powershell
# 백테스트 실행
.\trading_bot_env\Scripts\activate.bat
python scripts/run_backtest.py configs/backtest/phase33_1_v2_Q1_3m.yml

# 종료 코드 확인
echo $LASTEXITCODE
```

**판정**:
- `0` → ✅ 정상 종료
- `1` 또는 기타 → ❌ 오류 종료

---

### 2. Summary JSON 파일 존재 확인

```powershell
# 출력 파일 경로 (config에서 지정)
$summaryPath = "reports/backtest/phase33/btc15m_v2_Q1_3m_summary.json"

# 파일 존재 확인
Test-Path $summaryPath
```

**판정**:
- `True` → ✅ 백테스트 완료
- `False` → ❌ 중간 종료 (오류 또는 중단)

---

### 3. Python 프로세스 잔존 확인

```powershell
# 실행 직후 프로세스 확인
Get-Process python* | Where-Object {$_.Path -like "*trading_bot_env*"}

# 또는 run_id 기준 확인
Get-Process python* | Select-Object Id, StartTime, Path
```

**판정**:
- **0개** → ✅ 정상 종료 (모든 프로세스 정리됨)
- **1개 이상** → ❌ 좀비 프로세스 잔존

**주의**:
- 런처(부모) + 워커(자식) 2개 패턴은 **실행 중**일 때 정상
- **종료 후**에는 반드시 0개여야 함

---

## 실행 절차 (Q1/Q2/Q3 예시)

### STEP 1: 환경 준비

```powershell
# 가상환경 활성화
.\trading_bot_env\Scripts\activate.bat

# Redis 초기화 (선택)
redis-cli FLUSHALL

# 이전 프로세스 종료
Get-Process python* | Where-Object {$_.Path -like "*trading_bot_env*"} | Stop-Process -Force
```

---

### STEP 2: Q1 백테스트 실행

```powershell
# 실행
python scripts/run_backtest.py configs/backtest/phase33_1_v2_Q1_3m.yml

# 종료 후 즉시 검증
echo "Exit Code: $LASTEXITCODE"
Test-Path reports/backtest/phase33/btc15m_v2_Q1_3m_summary.json
Get-Process python* | Where-Object {$_.Path -like "*trading_bot_env*"} | Measure-Object | Select-Object Count
```

**예상 출력**:
```
Exit Code: 0
True
Count: 0
```

---

### STEP 3: Q2 백테스트 실행

```powershell
# 실행
python scripts/run_backtest.py configs/backtest/phase33_2_v2_Q2_3m.yml

# 종료 후 즉시 검증
echo "Exit Code: $LASTEXITCODE"
Test-Path reports/backtest/phase33/btc15m_v2_Q2_3m_summary.json
Get-Process python* | Where-Object {$_.Path -like "*trading_bot_env*"} | Measure-Object | Select-Object Count
```

**예상 출력**:
```
Exit Code: 0
True
Count: 0
```

---

### STEP 4: Q3 백테스트 실행

```powershell
# 실행
python scripts/run_backtest.py configs/backtest/phase33_3_v2_Q3_3m.yml

# 종료 후 즉시 검증
echo "Exit Code: $LASTEXITCODE"
Test-Path reports/backtest/phase33/btc15m_v2_Q3_3m_summary.json
Get-Process python* | Where-Object {$_.Path -like "*trading_bot_env*"} | Measure-Object | Select-Object Count
```

**예상 출력**:
```
Exit Code: 0
True
Count: 0
```

---

## 로그 확인 (추가 검증)

### "RUN FINISHED" 마커 확인

```powershell
# 로그 파일에서 종료 마커 검색
Select-String -Path logs/phase33_Q1_3m.log -Pattern "RUN FINISHED"
Select-String -Path logs/phase33_Q1_3m.log -Pattern "ERROR|CRITICAL"
```

**판정**:
- `RUN FINISHED` 존재 → ✅ 정상 종료
- ERROR/CRITICAL 0건 → ✅ 예외 없음

---

## Acceptance Criteria

| 항목 | 기준 | Q1 | Q2 | Q3 |
|------|------|----|----|--- |
| **Exit Code** | == 0 | ✅ | ✅ | ✅ |
| **Summary JSON** | 존재 | ✅ | ✅ | ✅ |
| **프로세스 잔존** | == 0 | ✅ | ✅ | ✅ |
| **로그 ERROR** | == 0 | ✅ | ✅ | ✅ |

**최종 판정**: **3/3 PASS** → ✅ **종료 안정성 확보**

---

## PHASE34-0: Watchdog 기반 자동 종료 보장

**도입 배경**:
- 수동 체크는 사람의 실수 가능
- "명령은 끝났는데 Windsurf가 계속 도는 문제" 자동 감지 필요
- 종료 검증 3종을 **기계적으로** 강제

**구현**: `scripts/utils/run_watchdog.py`

### 기능

1. **대상 커맨드 실행 + Timeout**
   - subprocess로 백테스트/PAPER 실행
   - 지정된 시간 초과 시 프로세스 트리 강제 종료
   - 기본 timeout: 7200초 (2시간)

2. **3종 종료 체크 자동화**
   ```python
   checks = {
       "exit_code": exit_code == 0,
       "summary_json": Path(summary_path).exists(),
       "process_remnants": len(find_python_procs()) == 0
   }
   ```

3. **실패 시 자동 조치**
   - 프로세스 트리 kill (부모 + 자식)
   - 로그 마지막 50줄 덤프
   - Watchdog 리포트 JSON 저장

### 사용법

```powershell
# 기본 사용
python scripts/utils/run_watchdog.py \
    --command "python scripts/run_backtest.py --config configs/backtest/phase33_1_v2_Q1_3m.yml" \
    --timeout 3600 \
    --summary-path "reports/backtest/phase33/btc15m_v2_Q1_3m_summary.json" \
    --run-id "phase33_1_v2_Q1_3m" \
    --log-file "logs/watchdog_phase33_Q1.log" \
    --report-file "reports/watchdog/phase33_Q1_report.json"
```

**Timeout 설정 가이드**:
- 7D 백테스트: 300초 (5분)
- 1M 백테스트: 600초 (10분)
- 3M 백테스트: 900초 (15분)
- 9M 백테스트: 1800초 (30분)

### Watchdog 리포트 예시

```json
{
  "success": true,
  "exit_code": 0,
  "duration_seconds": 487.3,
  "timeout_triggered": false,
  "checks": {
    "exit_code": {"passed": true, "value": 0},
    "summary_json": {"passed": true, "value": "reports/..."},
    "process_remnants": {"passed": true, "count": 0}
  }
}
```

### 행 걸림 원인 4분류 (자동 감지)

| 원인 | 증상 | Watchdog 동작 |
|------|------|---------------|
| **1. 서브프로세스 미종료** | timeout 후에도 프로세스 잔존 | kill 후 remnants > 0 리포트 |
| **2. 파일 tailing 무한 루프** | exit_code=0이지만 반환 안됨 | timeout kill |
| **3. Summary 대기 루프** | exit_code=0, summary 없음 | summary_json=False |
| **4. UI 상태 갱신 버그** | 실제 종료됨, remnants=0 | success=True (오탐 아님) |

### Acceptance Criteria (Watchdog 기준)

**PASS 조건**:
```python
watchdog_result["success"] == True
# AND
all([
    checks["exit_code"]["passed"],
    checks["summary_json"]["passed"],
    checks["process_remnants"]["passed"]
])
# AND
timeout_triggered == False
```

**FAIL 케이스**:
- Timeout 발생
- Exit code != 0
- Summary JSON 없음
- 프로세스 잔존 (remnants > 0)

---

## 트러블슈팅

### 문제: Exit Code 0이지만 Summary JSON이 없음생성되지 않음

**원인**:
- 백테스트 중간 오류 (exception)
- 로그 경로 오류 (디렉토리 없음)

**해결**:
```powershell
# 로그 확인
cat logs/phase33_Q*_3m.log | Select-String -Pattern "ERROR|CRITICAL"

# 디렉토리 생성
New-Item -ItemType Directory -Force -Path reports/backtest/phase33
```

---

### 문제 2: 프로세스 잔존 (좀비 프로세스)

**원인**:
- Background thread가 종료되지 않음
- Prometheus exporter, Redis monitor 등

**해결**:
```powershell
# 강제 종료
Get-Process python* | Where-Object {$_.Path -like "*trading_bot_env*"} | Stop-Process -Force

# 원인 분석 (로그)
cat logs/phase33_Q*_3m.log | Select-String -Pattern "Thread|daemon|Prometheus"
```

---

### 문제 3: Exit Code != 0

**원인**:
- 코드 레벨 exception
- Config 오류
- 데이터 부족

**해결**:
```powershell
# 스택 트레이스 확인
cat logs/phase33_Q*_3m.log | Select-String -Pattern "Traceback"

# Config 검증
python -c "import yaml; yaml.safe_load(open('configs/backtest/phase33_1_v2_Q1_3m.yml'))"
```

---

## 다음 단계

1. ✅ 체크리스트 문서화
2. 🔄 PHASE33 보고서 업데이트
3. 🔄 PHASE_ROADMAP.md 반영
4. 🔄 Git commit

---

## 참고

- 모든 실행은 **동기(synchronous) 모드** 우선
- 비동기 실행 시 `command_status` 도구는 **신뢰하지 말 것**
- 종료 검증은 **3종 세트 전부** 확인
