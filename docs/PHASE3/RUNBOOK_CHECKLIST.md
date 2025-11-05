# 🏃 백테스트 실행 체크리스트 (RUNBOOK)

**작성일**: 2025-10-23  
**목적**: 백테스트 실행 전후 필수 확인 사항 체계화

---

## ✅ 실행 전 체크리스트 (Pre-Flight)

### 1. 문서 정독
- [ ] `TEST_SCENARIO.md` 정독 (단계별 진행 순서)
- [ ] `TEST_CHECKLIST.md` 확인 (현재 실험 상태)
- [ ] `BACKTEST_PERIODS.md` 확인 (데이터 기간)

### 2. 데이터 준비
- [ ] 올바른 기간 데이터 존재 확인
- [ ] 캔들 수 검증 (5m 기준: 3개월 ≈ 25,920개)
- [ ] NULL/중복 데이터 확인

### 3. 설정 검증
- [ ] `config.yml` backup 생성
- [ ] `mode: backtest` 확인
- [ ] `symbol` 설정 확인
- [ ] `timeframe` 설정 확인
- [ ] 전략 `selector` 또는 `use_ensemble` 확인

### 4. 코드 상태
- [ ] 최근 변경사항 확인
- [ ] 중복 모듈 없음 확인
- [ ] import 오류 없음 확인

---

## 🚀 실행 단계

### 1. 환경 확인
```powershell
# Python 환경
python --version  # 3.8+

# 패키지 확인
pip list | Select-String "pandas|numpy|ta"
```

### 2. 간단 테스트 (1일치)
```powershell
# config.yml에서 데이터 기간을 1일로 제한
# 오류 없이 완료되는지 확인 (5~10분)
python main.py
```

### 3. 전체 백테스트
```powershell
# 전체 기간 실행
python main.py

# 또는 백그라운드 실행 (로그 파일로 저장)
python main.py > backtest_output.log 2>&1
```

---

## 📊 실행 중 모니터링

### 1. 로그 확인
```powershell
# 실시간 로그 확인 (PowerShell)
Get-Content backtest_output.log -Wait -Tail 50
```

### 2. 주요 확인 사항
- [ ] 자본 업데이트 정상 (`💰 Equity 업데이트`)
- [ ] 거래 빈도 적정 (일평균 30~50건 목표)
- [ ] 연속 손실 제한 작동 (`🛑 연속 손실 X/4회`)
- [ ] 오류 메시지 없음

### 3. 이상 징후 대응
| 징후 | 원인 | 조치 |
|------|------|------|
| 거래 0건 | 전략 조건 너무 엄격 | 조건 완화 |
| 거래 1000건/일 | 전략 조건 너무 느슨 | 조건 강화 |
| 자본 0 이하 | 리스크 관리 미작동 | 즉시 중단 |
| 연속 손실 10회+ | 리스크 제한 미작동 | 즉시 중단 |

---

## 📝 실행 후 체크리스트 (Post-Flight)

### 1. 결과 확인
- [ ] HTML 리포트 생성 확인 (`reports/backtest/*.html`)
- [ ] SQLite DB 확인 (`backtest_results.db`)
- [ ] 핵심 지표 확인:
  - [ ] Total Trades
  - [ ] Win Rate
  - [ ] Profit Factor
  - [ ] MDD
  - [ ] Expectancy

### 2. 게이트 기준 비교
| 지표 | 목표 | 실제 | 통과 |
|------|------|------|------|
| Expectancy | ≥ 0.10 R |  | ☐ |
| PF | ≥ 1.3 |  | ☐ |
| MDD | ≤ -20% |  | ☐ |
| Win Rate | ≥ 40% |  | ☐ |

### 3. 문서 업데이트
- [ ] `TEST_CHECKLIST.md` 업데이트 (실험 결과)
- [ ] `ROOT_CAUSE_ANALYSIS.md` 업데이트 (문제 발견 시)
- [ ] 실험 ID 기록 (EXP-AX-XX)

### 4. 설정 보존
```powershell
# 성공한 설정 백업
Copy-Item config.yml "config_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').yml"
```

---

## 🔧 문제 해결 (Troubleshooting)

### 1. 자주 발생하는 오류

#### A. `AttributeError: 'PositionTracker' object has no attribute 'remove_position'`
**원인**: `PositionTracker`에 없는 메서드 호출  
**해결**: `tracker.remove_position()` 제거 (포트폴리오 매니저가 처리)

#### B. `FileNotFoundError: CSV 없음`
**원인**: 데이터 파일 경로 불일치  
**해결**: 
```powershell
# 파일 존재 확인
Test-Path "data/BTCUSDT_5m_2024-01-01_2024-12-31.csv"

# 없으면 다운로드
python scripts/download_data.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --end 2024-12-31
```

#### C. `거래 0건`
**원인**: 전략 조건 불충족  
**해결**: 
1. 전략 파일 확인 (`strategies/scalping.py`)
2. 조건 완화 (RSI 범위, BB 터치 허용치)
3. 로그에서 `신호 검증 실패` 메시지 확인

#### D. `자본 0 이하 계속 거래`
**원인**: 리스크 제한 미작동  
**해결**: `execution/risk_manager.py`에 자본 0 체크 추가

---

## 📋 빠른 참조 (Quick Reference)

### 실험 ID 규칙
```
EXP-{Stage}-{Number}
예: EXP-A2-01, EXP-A3-02, EXP-B1-01
```

### 주요 파일 경로
```
config.yml                      # 설정 파일
data/BTCUSDT_5m_*.csv          # 데이터
logs/application_*.log          # 로그
reports/backtest/*.html         # 리포트
data/trading.db                 # 백테스트 결과 DB
configs/scalping/<study>/       # 튜닝 Trial 설정
logs/tuning/trial_*.json        # 튜닝 Trial 메트릭
scripts/tuning/tune_scalping.py # 튜닝 스크립트
```

### 간단 명령어
```powershell
# 백테스트 실행
python main.py

# 튜닝 실행 (Optuna)
python -u scripts/tuning/tune_scalping.py --study scalping_v1 --trials 20 --use-wfa 1

# 로그 확인
Get-Content logs/application_*.log -Tail 100

# 결과 분석
python analyze_backtest.py

# TUNING_VIBLE 점수 확인
python -c "from reports.trading_reporter import print_tuning_score_report; print_tuning_score_report()"

# 데이터 다운로드
python scripts/download_data.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --end 2024-03-31
```

---

## ⚠️ 금지 사항

1. **PowerShell 복잡한 파이프 조합 사용 금지**
2. **config.yml 설정 중복 금지**
3. **여러 변경 동시 진행 금지** (한 번에 하나씩)
4. **OOS 데이터로 튜닝 금지**
5. **문서 업데이트 생략 금지**

---

**다음 문서**: `TEST_CHECKLIST.md` (실험 기록)  
**참조**: `TEST_SCENARIO.md` (테스트 시나리오)
