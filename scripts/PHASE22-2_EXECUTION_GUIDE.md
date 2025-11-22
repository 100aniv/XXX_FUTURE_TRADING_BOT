# PHASE22-2 Execution Guide

## 🚀 12시간 Extended Validation 실행 가이드

### 1. 실행 전 체크리스트
- ✅ Docker containers running (postgres, redis)
- ✅ Python 프로세스 정리 완료
- ✅ 가상환경 활성화 (`trading_bot_env`)
- ✅ 현재 시각 확인 (12시간 후 종료 예정)

---

## 2. 실행 방법

### Option A: 전체 12시간 실행 (권장)

**새 CMD 창에서 실행**:
```cmd
cd C:\Users\bback\OneDrive\Documents\future_alarm_bot
.\trading_bot_env\Scripts\activate
python scripts/run_phase22_ensemble_single_symbol.py ^
  --config configs/paper/phase22_ensemble_single_symbol.yml ^
  --duration-hours 12 ^
  --clean-state
```

**예상 실행 시간**:
- 시작: 현재 시각
- 종료: 12시간 후

**주의사항**:
- CMD 창을 닫지 말 것
- PC 절전 모드 비활성화 권장
- 네트워크 안정성 확인

---

### Option B: 짧은 테스트 먼저 실행 (안전)

12시간은 매우 긴 시간이므로, 먼저 **2시간 테스트**로 정상 작동을 확인하는 것을 권장합니다.

```cmd
python scripts/run_phase22_ensemble_single_symbol.py ^
  --config configs/paper/phase22_ensemble_single_symbol.yml ^
  --duration-hours 2 ^
  --clean-state
```

**2시간 테스트 PASS 후**:
- 로그 확인
- 전략 신호 발생 확인
- 이상 없으면 12시간 재실행

---

## 3. 실시간 모니터링

**별도 CMD 창에서 모니터링 스크립트 실행**:
```cmd
cd C:\Users\bback\OneDrive\Documents\future_alarm_bot
.\trading_bot_env\Scripts\activate
python scripts/monitor_phase22_paper.py --interval 30 --duration 12
```

**모니터링 내용**:
- Candle Count
- Trade Count
- Duration Elapsed
- ERROR/CRITICAL Count
- FlowGuardian READY 비율
- Strategy Signals

**체크 간격**: 30분마다 자동 출력

---

## 4. 수동 로그 확인 방법

### PowerShell에서 실시간 로그 확인:
```powershell
# 전체 로그 tail
Get-Content logs\application\2025-11-22.log -Encoding UTF8 -Wait -Tail 50

# Duration 관련 로그만
Get-Content logs\application\2025-11-22.log -Encoding UTF8 | Select-String "WALL-CLOCK|Duration"

# ERROR/CRITICAL만
Get-Content logs\application\2025-11-22.log -Encoding UTF8 | Select-String "ERROR|CRITICAL"

# 전략 신호만
Get-Content logs\application\2025-11-22.log -Encoding UTF8 | Select-String "신호|signal"
```

---

## 5. 중단 조건 (즉시 taskkill 필요)

다음 상황 발생 시 **즉시 중단**:
1. ❌ CRITICAL 에러 발생
2. ❌ Trade Count = 0 상태 2시간 이상 지속
3. ❌ FlowGuardian READY 실패 반복
4. ❌ Feed 연결 끊김 반복
5. ❌ Duration 미작동 (12시간 초과 실행)

**중단 명령**:
```cmd
taskkill /F /IM python.exe /T
```

---

## 6. 체크포인트 일정표

| 시간 | 체크포인트 | 확인 사항 |
|------|-----------|----------|
| 0h | 시작 | Engine 시작, Duration 설정, 전략 로딩 |
| 1h | 초기 활동 | Trade Count > 0, FlowGuardian READY |
| 3h | Low-Freq 신호 | breakout/trend 신호 발생 확인 |
| 6h | 중간 점검 | ERROR 0건, Portfolio 일관성 |
| 9h | 후반 안정성 | Feed 연결, Duration 경과 확인 |
| 12h | 종료 | 자동 종료, Scorecard 생성 |

---

## 7. 실행 후 확인 사항

### 7.1 로그 파일 위치
- `logs/application/2025-11-22.log`

### 7.2 Scorecard 위치
- `scorecards/paper_phase22_1/PHASE22-1_ensemble_v1_single_symbol/`

### 7.3 최종 검증
```bash
# 테스트 실행
pytest tests/test_phase22_ensemble_single_symbol.py -v

# 로그 분석
python scripts/monitor_phase22_paper.py --interval 1 --duration 0.01
```

---

## 8. Acceptance Criteria 체크리스트

실행 완료 후 아래 항목을 확인:
- [ ] 12h 이상 wall-clock 정상 종료
- [ ] ERROR/CRITICAL 0건
- [ ] FlowGuardian READY 100% 통과
- [ ] Ensemble v1 전략 모두 활성화
- [ ] 최소 3개 전략 이상 실제 진입 발생
- [ ] Low-Freq 전략 breakout/trend 각각 최소 1회 신호 발생
- [ ] PortfolioManager 상태 일관성 유지
- [ ] Scorecard 정상 생성
- [ ] DB/Redis 상태 정상
- [ ] Duration 종료 정확도 <1% 오차

**모든 항목 PASS → PHASE22-2 PASS**  
**하나라도 FAIL → PHASE22-2 FAIL → 수정 후 재실행**

---

**Generated**: 2025-11-22 10:51 KST
