# PHASE10 Scalping 1m 튜닝 실행 가이드

**작성일:** 2024-11-15  
**대상:** PHASE9-6 1분 스캘핑 전략 하이퍼파라미터 튜닝 (백테스트 모드)  
**방법론:** Optuna 베이지안 최적화 + Train/Validation 분할

---

## 목차

1. [사전 준비](#1-사전-준비)
2. [단일 Trial 테스트](#2-단일-trial-테스트-sanity-check)
3. [30-Trial 메인 튜닝](#3-30-trial-메인-튜닝)
4. [엄격한 Validation Penalty 튜닝](#4-엄격한-validation-penalty-튜닝-선택)
5. [병렬 워커 실행](#5-병렬-워커-실행)
6. [트러블슈팅](#6-트러블슈팅)
7. [다음 단계](#7-다음-단계-phase11)

---

## 1. 사전 준비

### 1.1 환경 확인

```bash
# 가상환경 활성화
.\trading_bot_env\Scripts\activate

# Python 버전 확인 (3.9+)
python --version

# 필수 패키지 확인
pip list | grep -E "optuna|psycopg2|pandas|numpy"
```

### 1.2 데이터 준비

**필수 데이터 파일:**
- `data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv`

데이터가 없으면 다운로드:

```bash
python scripts/download_data.py \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-12-31 \
  --output data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**데이터 검증:**
```bash
# CSV 파일 확인
head -5 data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv

# 기대 포맷:
# timestamp,open,high,low,close,volume
# 2024-10-01 00:00:00,61234.5,61250.0,61200.0,61245.3,123.45
```

### 1.3 설정 파일 확인

- ✅ `configs/base.yml` 존재 (execution, risk, strategies 섹션)
- ✅ `strategies/scalping.py` PHASE9-6 버전
- ✅ `scripts/run_backtest.py` 실행 가능

### 1.4 Optuna Storage 확인

**기본 Storage: PostgreSQL (`trading_db`)**

튜닝 인프라는 기본적으로 Postgres를 사용합니다. 환경변수 `TUNING_DB_URL` 또는 `DATABASE_URL`로 자동 결정됩니다.

```bash
# Docker 환경
echo $DATABASE_URL
# 예: postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db

# DB 접속 테스트
psql -h db_postgres -U trading_user -d trading_db -c "SELECT 1;"
```

**로컬 환경 (localhost):**
```bash
export DATABASE_URL="postgresql://trading_user:trading_pw_2024@localhost:5432/trading_db"
```

**SQLite (개발용, 권장하지 않음):**
```bash
# 로컬 테스트 시에만 사용
python -m tuning.tuning_cli \
  --storage "sqlite:///artifacts/tuning/optuna.db" \
  (... 나머지 옵션 ...)
```

> ⚠️ **주의**: SQLite는 동시 쓰기 제한이 있어 병렬 튜닝 시 문제가 발생할 수 있습니다. 프로덕션에서는 반드시 Postgres를 사용하세요.

---

## 2. 단일 Trial 테스트 (Sanity Check)

**목적:** 백테스트 튜닝 파이프라인 전체 검증 (약 6분 소요)

### 2.1 실행 명령

```bash
python -m tuning.tuning_cli \
  --strategy scalping \
  --study scalping_1m_test \
  --trials 1 \
  --mode backtest \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-12-30 \
  --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

### 2.2 확인할 로그

**1) 설정 확인 섹션:**
```
================================================================================
🔍 백테스트 튜닝 설정 확인
================================================================================
  전략:     scalping
  Study:    scalping_1m_test
  Trials:   1회
  심볼/TF:  BTCUSDT / 1m
  기간:     2024-10-01 ~ 2024-12-30
  데이터:   data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
  Train/Val 분할: 활성화
  Val Penalty 가중치: 0.3
  최소 거래수 (t_min): 전략별 기본값
  MDD Cap:  8.0%
================================================================================
```

**2) Train/Val 날짜 분할:**
```
📅 Train/Val 분할: Train=2024-10-01~2024-11-30, Val=2024-12-01~2024-12-30
```

**3) Train 백테스트 실행:**
```
🔧 [TUNER BT] TRAIN 백테스트 실행 중...
   - Strategy: scalping
   - Symbol/TF: BTCUSDT / 1m
   - Period: 2024-10-01 ~ 2024-11-30
   - Data: data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv

✅ [TUNER BT] 백테스트 완료 (train)
   - Artifacts: 20241115_143022_scalping_BTCUSDT_1m
   - Scorecard: artifacts/backtest_clean/20241115_143022_scalping_BTCUSDT_1m/scorecard.csv

📊 [TUNER BT] TRAIN Metrics:
   PF=0.450, WR=35.0%, Trades=18, MDD=5.23%, Sharpe=0.12, ROI=2.34%
```

**4) Train Score 계산:**
```
💯 [TUNER BT] TRAIN Score 계산:
   base_score = PF(0.450) + 0.1*WR(35.0) = 3.950
   dd_penalty = max(0, (MDD 5.23% - cap 8.0%) * 0.05) = 0.000
   trades_penalty = 0.05 * max(0, t_min 50 - Trades 18) = 1.600
   final_score = 3.950 - 0.000 - 1.600 = 2.350
```

**5) Validation 백테스트 및 Score:**
```
🔧 [TUNER BT] VAL 백테스트 실행 중...
✅ [TUNER BT] 백테스트 완료 (val)
📊 [TUNER BT] VAL Metrics:
   PF=0.300, WR=28.0%, Trades=7, MDD=7.12%, Sharpe=-0.05, ROI=-1.23%

💯 [TUNER BT] VAL Score 계산:
   base_score = PF(0.300) + 0.1*WR(28.0) = 3.100
   dd_penalty = max(0, (MDD 7.12% - cap 8.0%) * 0.05) = 0.000
   trades_penalty = 0.05 * max(0, t_min 50 - Trades 7) = 2.150
   final_score = 3.100 - 0.000 - 2.150 = 0.950
```

**6) 최종 결과:**
```
================================================================================
🎯 [TUNER BT] Trial#0 최종 결과:
   📈 TRAIN: PF=0.450, WR=35.0%, T=18, score=2.350
   📊 VAL:   PF=0.300, WR=28.0%, T=7, score=0.950
   ⚖️  VAL PENALTY: 0.3 * |2.350 - 0.950| = 0.420
   ✅ FINAL SCORE: 2.350 - 0.420 = 1.930
================================================================================
```

### 2.3 성공 기준

- ✅ Train 백테스트 정상 완료 (return code 0)
- ✅ Val 백테스트 정상 완료
- ✅ scorecard.csv 파싱 성공 (PF, Winrate, Trades 값 출력)
- ✅ Score 계산 과정 로그 출력
- ✅ Final score > 0

**⚠️  예상 이슈:**
- Trades가 매우 적을 수 있음 (전략 V1은 보수적 설계)
- Trades penalty가 높게 나옴 → 정상 (튜닝으로 개선 예정)

### 2.4 실패 시 체크리스트

| 오류 | 원인 | 해결 |
|------|------|------|
| `scorecard.csv 파일 없음` | run_backtest.py 실행 실패 | `scripts/run_backtest.py` 단독 실행 테스트 |
| `artifacts 디렉토리 없음` | 백테스트 artifacts 생성 실패 | `artifacts/` 디렉토리 권한 확인 |
| `백테스트 타임아웃` | 데이터 파일 너무 큼 또는 전략 과부하 | 기간 축소 (60일로 재시도) |
| `Trades=0` | 전략 조건 너무 엄격 | 정상 (일부 파라미터 조합에서 발생 가능) |

---

## 3. 30-Trial 메인 튜닝

**목적:** Bayesian Optimization으로 최적 하이퍼파라미터 탐색  
**소요 시간:** 약 3시간 (순차 실행 시)

### 3.1 실행 명령

```bash
python -m tuning.tuning_cli \
  --strategy scalping \
  --study scalping_1m_v1 \
  --trials 30 \
  --mode backtest \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-12-30 \
  --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

### 3.2 진행 상황 모니터링

**Terminal 출력:**
- 각 Trial마다 `🎯 [TUNER BT] Trial#N 최종 결과` 블록 출력
- Train/Val metrics, scores, final score 확인

**Optuna Dashboard (선택):**
```bash
# 별도 터미널에서 실행
optuna-dashboard $OPTUNA_STORAGE

# 브라우저에서 http://localhost:8080 접속
# Study "scalping_1m_v1" 선택하여 실시간 시각화
```

### 3.3 예상 결과

**Trial 진행 예시:**
```
Trial#0: final_score=1.930
Trial#1: final_score=2.145
Trial#2: final_score=1.782 (Pruned - Trades < 15)
Trial#3: final_score=2.567
...
Trial#29: final_score=3.201
```

**Best Trial 확인:**
```bash
# Optuna Study 조회
python -c "
import optuna
study = optuna.load_study(
    study_name='scalping_1m_v1',
    storage='postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db'
)
print(f'Best Trial: {study.best_trial.number}')
print(f'Best Score: {study.best_value:.3f}')
print(f'Best Params: {study.best_params}')
"
```

**예상 Best Params:**
```python
{
    'rsi_oversold': 32,
    'rsi_overbought': 68,
    'ema_fast': 7,
    'ema_slow': 19,
    'momentum_lookback': 8,
    'volume_mult': 2.3,
    'rr': 1.4,
    'atr_mult_sl': 1.2,
    'max_hold_minutes': 25,
    'allow_short': True
}
```

### 3.4 튜닝 후 파라미터 발행

**Best params를 active.yml에 발행:**
```bash
python -c "
import optuna
import yaml
from pathlib import Path

study = optuna.load_study(
    study_name='scalping_1m_v1',
    storage='postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db'
)

# Best params 추출
best_params = study.best_params

# YAML 구조로 변환
config = {
    'strategies': {
        'scalping': best_params
    }
}

# 발행
output_path = Path('configs/scalping/active.yml')
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

print(f'✅ Best params 발행 완료: {output_path}')
"
```

---

## 4. 엄격한 Validation Penalty 튜닝 (선택)

**목적:** Overfitting을 더욱 강하게 방지  
**적용 시점:** 30-trial 결과에서 Train/Val 점수 차이가 크게 나타날 때

### 4.1 실행 명령

```bash
python -m tuning.tuning_cli \
  --strategy scalping \
  --study scalping_1m_strict \
  --trials 30 \
  --mode backtest \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-12-30 \
  --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv \
  --val-penalty-weight 0.5
```

### 4.2 효과

- `val_penalty_weight=0.3` (기본): Train 점수 우선, Val 차이 30% 페널티
- `val_penalty_weight=0.5`: Train/Val 균형, Val 차이 50% 페널티
- `val_penalty_weight=0.7`: Val 점수 우선, Val 차이 70% 페널티

**예시:**
```
# 기본 (0.3)
Train score=3.5, Val score=2.0 → penalty=0.3*1.5=0.45 → final=3.05

# 엄격 (0.5)
Train score=3.5, Val score=2.0 → penalty=0.5*1.5=0.75 → final=2.75

# 초엄격 (0.7)
Train score=3.5, Val score=2.0 → penalty=0.7*1.5=1.05 → final=2.45
```

---

## 5. 병렬 워커 실행

**목적:** 여러 터미널에서 동시 실행하여 튜닝 속도 향상  
**원리:** Optuna는 동일 storage를 공유하면 자동으로 미완료 trial 분배

### 5.1 멀티 워커 실행

**Terminal 1:**
```bash
python -m tuning.tuning_cli \
  --strategy scalping \
  --study scalping_1m_v1 \
  --trials 50 \
  --mode backtest \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2024-10-01 \
  --end-date 2024-12-30 \
  --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**Terminal 2 (동시 실행):**
```bash
# 동일 명령어
python -m tuning.tuning_cli \
  --strategy scalping \
  --study scalping_1m_v1 \
  --trials 50 \
  --mode backtest \
  (... 동일 ...)
```

**Terminal 3 (동시 실행):**
```bash
# 동일 명령어 (3개 워커)
```

### 5.2 효과

- 3개 워커 → 100 trials를 약 3.5시간에 완료 (순차 실행 10시간 → 70% 단축)
- Trial 중복 없음 (Optuna가 자동 관리)
- 각 워커는 독립적으로 trial을 가져와 실행

### 5.3 주의사항

- 워커 수는 CPU 코어 수 이하로 권장 (메모리 부족 방지)
- 각 워커는 동일한 `--study` 이름 사용
- 동일한 `--storage` (PostgreSQL) 사용 필수

---

## 6. 트러블슈팅

### 6.1 scorecard.csv 파일 없음

**증상:**
```
❌ [TUNER BT] scorecard.csv 파일 없음: artifacts/backtest_clean/.../scorecard.csv
```

**원인:**
- `scripts/run_backtest.py` 실행 실패
- ScorecardGenerator 오류

**해결:**
1. 백테스트 단독 실행 테스트:
   ```bash
   python scripts/run_backtest.py \
     --mode backtest_clean \
     --strategy scalping \
     --symbol BTCUSDT \
     --timeframe 1m \
     --start-date 2024-10-01 \
     --end-date 2024-10-30 \
     --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
   ```
2. `artifacts/backtest_clean/` 디렉토리 확인
3. 백테스트 로그에서 에러 확인

### 6.2 Trades=0 (거래 없음)

**증상:**
```
⚠️  [TUNER BT] train 기간 거래 없음 (전략 조건 너무 엄격)
   ⚠️  Train score=0.0 (거래 없음)
```

**원인:**
- 샘플링된 파라미터 조합이 너무 보수적
- EMA 크로스, RSI, 모멘텀, 볼륨 조건 동시 충족 불가

**해결:**
- 정상 현상 (일부 trial에서 발생 가능)
- MedianPruner가 자동으로 조기 종료
- 튜닝 계속 진행 (다른 trial이 더 나은 조합 찾음)

### 6.3 백테스트 타임아웃 (10분 초과)

**증상:**
```
⏱️  [TUNER BT] 백테스트 타임아웃 (train) - 10분 초과
```

**원인:**
- 데이터 파일이 너무 큼 (90일 1분봉 = 약 130,000 캔들)
- 전략 로직이 과부하 (너무 많은 계산)

**해결:**
1. 기간 축소 (90일 → 60일):
   ```bash
   --start-date 2024-11-01 --end-date 2024-12-30
   ```
2. 타임아웃 연장 (`tuning_core.py` 수정):
   ```python
   timeout=1200  # 20분
   ```

### 6.4 subprocess 실행 실패 (return code != 0)

**증상:**
```
❌ [TUNER BT] 백테스트 실행 실패 (train)
   Return code: 1
   STDERR: ModuleNotFoundError: No module named 'collectors'
```

**원인:**
- Python 경로 문제
- 가상환경 미활성화
- 모듈 import 오류

**해결:**
1. 가상환경 확인:
   ```bash
   which python
   # 기대값: .../trading_bot_env/Scripts/python
   ```
2. PYTHONPATH 설정:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```
3. 모듈 import 테스트:
   ```bash
   python -c "import collectors; import execution; import strategies"
   ```

### 6.5 Optuna Storage 연결 실패

**증상:**
```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**원인:**
- PostgreSQL 서버 중단 또는 미실행
- 잘못된 연결 URL (호스트명: `db_postgres` vs `localhost`)
- 환경변수 미설정

**해결 (우선순위대로):**

1. **환경변수 확인:**
   ```bash
   echo $DATABASE_URL
   echo $TUNING_DB_URL
   # 둘 중 하나는 있어야 함
   ```

2. **PostgreSQL 상태 확인:**
   ```bash
   # Docker 환경
   docker ps | grep postgres
   
   # 로컬 환경
   systemctl status postgresql  # Linux
   pg_ctl status  # Windows/Mac
   ```

3. **연결 테스트:**
   ```bash
   # Docker
   psql -h db_postgres -U trading_user -d trading_db -c "SELECT 1;"
   
   # 로컬
   psql -h localhost -U trading_user -d trading_db -c "SELECT 1;"
   ```

4. **PostgreSQL 재시작:**
   ```bash
   docker-compose restart db_postgres
   ```

5. **최후의 수단: SQLite 개발 모드 (권장하지 않음):**
   ```bash
   python -m tuning.tuning_cli \
     --storage "sqlite:///artifacts/tuning/optuna.db" \
     (... 나머지 동일 ...)
   ```
   > ⚠️ SQLite는 병렬 실행 시 문제 발생 가능. 근본 원인(Postgres 연결) 해결을 권장.

---

## 7. 다음 단계 (PHASE11)

### 7.1 PHASE11.1: 튜닝 결과 검증

1. **Best params 추출 및 분석**
   ```bash
   python -c "
   import optuna
   study = optuna.load_study(study_name='scalping_1m_v1', storage='...')
   print(study.best_params)
   print(f'Best Score: {study.best_value:.3f}')
   print(f'Train/Val 메트릭 확인')
   "
   ```

2. **Best config로 재백테스트**
   ```bash
   # best params를 configs/scalping/active.yml에 발행 후
   python scripts/run_backtest.py \
     --mode backtest_clean \
     --strategy scalping \
     --symbol BTCUSDT \
     --timeframe 1m \
     --start-date 2024-10-01 \
     --end-date 2024-12-30 \
     --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
   ```

3. **OOS 기간 검증 (2025-01)**
   - 2024-10~12 튜닝 결과를 2025-01 데이터로 테스트
   - 일반화 성능 확인

### 7.2 PHASE11.2: 앙상블 통합

1. **튜닝된 scalping 전략을 앙상블에 추가**
   - `configs/base.yml` 앙상블 가중치 조정
   - scalping(1m) + daytrade(5m) + swing(1h) 다전략 조합

2. **앙상블 메타 파라미터 튜닝**
   - alpha, beta, gamma (전략 가중치)
   - 상관관계 분석

### 7.3 PHASE11.3: 리스크 가드 튜닝

1. **연속 손실 쿨다운 시간**
   - 현재 20분 고정 → 튜닝 대상
   - 범위: 10~60분

2. **일일 손실 한도**
   - 현재 5% 고정 → 튜닝 대상
   - 범위: 3~10%

3. **ATR 기반 동적 레버리지**
   - 변동성에 따른 레버리지 조정

### 7.4 PHASE11.4: 프로덕션 배포

1. **페이퍼 모드 재시작**
   ```bash
   docker-compose restart paper_container
   ```

2. **1주일 페이퍼 검증**
   - 실시간 데이터로 성능 모니터링
   - Trades, PF, MDD 추적

3. **라이브 배포 승인**
   - 페이퍼 검증 통과 시 라이브 모드 활성화
   - 소액 자본으로 시작 (예: 1,000 USDT)

---

## 부록: 예상 튜닝 시간표

| 단계 | Trials | 예상 시간 (순차) | 예상 시간 (3워커 병렬) |
|------|--------|------------------|-------------------------|
| 단일 테스트 | 1 | 6분 | 6분 |
| Sanity Check | 10 | 1시간 | 20분 |
| 메인 튜닝 | 30 | 3시간 | 1시간 |
| 확장 튜닝 | 100 | 10시간 | 3.5시간 |

**권장 일정:**
- **Day 1:** 단일 테스트 + 10-trial sanity (1.5시간)
- **Day 2:** 30-trial 메인 튜닝 (3시간, 병렬 실행 시 1시간)
- **Day 3:** 결과 분석 + 재백테스트 + 검증
- **Day 4~:** PHASE11 앙상블 통합

---

**문서 끝 - PHASE10.2 완료**
