# PHASE16 REAL PAPER Duration 설계 문서

## 📌 개요

PHASE16에서 Paper Trading 모드는 **두 가지 duration 평가 방식**을 지원해야 합니다:

1. **market_time 모드** (기존): 시장 타임스탬프/캔들 기준으로 duration 판단
   - 빠른 기능 테스트, 회귀 테스트, 튜닝용
   - 예: 1시간 설정 → 실제 10분 만에 완료 가능

2. **wall_clock 모드** (신규): 현실 시계(wall-clock) 기준으로 duration 판단
   - REAL PAPER SOAK (1h/12h/72h) 용
   - 예: 1시간 설정 → 반드시 54분 이상 실행 필요

---

## 🎯 문제 정의

### 현재 상황
- `duration-hours` 파라미터가 "시장 시간" 기준으로만 평가됨
- 결과적으로 현실 시계 10분 만에 "논리상 1시간"이 채워져 테스트 종료
- 이는 **72시간 REAL PAPER SOAK**의 원래 목적(실제 시간 동안 돌리는 것)과 어긋남

### 요구사항
- REAL PAPER 1h/12h/72h 테스트는 **현실 시간 기준**으로 실행되어야 함
- 기존 market_time 모드는 그대로 유지 (회귀 테스트용)
- 두 모드를 명확히 분리하고 선택 가능하게 구현

---

## 🏗️ 설계

### A) Duration Mode 추가

#### 1. 설정 레벨 (configs/base.yml)

```yaml
paper:
  duration_mode: "market_time"  # "market_time" | "wall_clock"
  # market_time: 시장 타임스탬프 기준 (기존, 빠른 테스트용)
  # wall_clock: 현실 시계 기준 (REAL PAPER SOAK용)
```

#### 2. CLI 레벨 (run_paper.py)

```bash
# 기존 (market_time 모드, 기본값)
python scripts/run_paper.py --strategy scalping --symbol BTCUSDT --duration-hours 1

# REAL PAPER 1h (wall_clock 모드)
python scripts/run_paper.py --strategy scalping --symbol BTCUSDT --duration-hours 1 --duration-mode wall_clock

# REAL PAPER 12h
python scripts/run_paper.py --strategy scalping --symbol BTCUSDT --duration-hours 12 --duration-mode wall_clock

# REAL PAPER 72h
python scripts/run_paper.py --strategy scalping --symbol BTCUSDT --duration-hours 72 --duration-mode wall_clock
```

### B) 엔진 레벨 구현 (execution/engine.py)

#### market_time 모드 (기존)
```python
# 현재 로직 그대로 유지
# 시장 타임스탐프 기준으로 duration 판단
if market_ts >= end_market_ts:
    break
```

#### wall_clock 모드 (신규)
```python
# 현실 시계 기준으로 duration 판단
import time
start_wall_time = time.time()
duration_seconds = duration_hours * 3600

while True:
    elapsed_wall = time.time() - start_wall_time
    if elapsed_wall >= duration_seconds:
        break
    # ... 캔들 처리 ...
```

### C) run_paper.py 수정

```python
def main():
    parser = argparse.ArgumentParser()
    # ... 기존 인자들 ...
    parser.add_argument('--duration-mode', 
                       choices=['market_time', 'wall_clock'],
                       default='market_time',
                       help='Duration 평가 기준')
    
    args = parser.parse_args()
    
    # config에 duration_mode 설정
    cfg['paper']['duration_mode'] = args.duration_mode
    
    # engine.run()에 전달
    engine.run(
        feed=feed,
        broker=broker,
        clock=clock,
        strategies=strategies,
        ensemble_module=ensemble_module,
        config=cfg
    )
```

### D) engine.run() 수정

```python
def run(self, feed, broker, clock, strategies, ensemble_module, config):
    duration_mode = config.get('paper', {}).get('duration_mode', 'market_time')
    duration_hours = config.get('paper', {}).get('duration_hours', 1)
    
    start_wall_time = time.time()
    duration_seconds = duration_hours * 3600
    
    while True:
        # wall_clock 모드: 현실 시계 기준 종료
        if duration_mode == 'wall_clock':
            elapsed_wall = time.time() - start_wall_time
            if elapsed_wall >= duration_seconds:
                logger.info(f"✅ Wall-clock duration 도달: {elapsed_wall:.1f}초 >= {duration_seconds}초")
                break
        
        # market_time 모드: 기존 로직 유지
        # ... 캔들 처리 ...
```

---

## 📊 REAL PAPER vs Fast PAPER 비교

| 항목 | Fast PAPER | REAL PAPER 1h | REAL PAPER 12h | REAL PAPER 72h |
|------|-----------|---------------|----------------|----------------|
| **Duration Mode** | market_time | wall_clock | wall_clock | wall_clock |
| **실제 실행 시간** | ~10분 | 54분 이상 | 12시간 | 72시간 |
| **용도** | 기능 테스트, 튜닝 | 1시간 안정성 검증 | 12시간 안정성 검증 | 72시간 SOAK 테스트 |
| **거래 수** | 250~400 | 1,500~3,000 | 18,000~36,000 | 108,000~216,000 |
| **PASS 기준** | Entry ≥ 1 | 현실 54분 + Entry ≥ 1 | 현실 12h + Entry ≥ 1 | 현실 72h + Entry ≥ 1 |

---

## 🧪 REAL PAPER 1h 테스트 절차

### STEP 0: 환경 체크

```bash
# 1. 가상환경 활성화 확인
python --version
pip list | grep -E "pandas|numpy|redis"

# 2. Docker 컨테이너 상태
docker ps | grep -E "trading_redis|trading_db"

# 3. Redis 연결 확인
docker exec trading_redis redis-cli PING
docker exec trading_redis redis-cli DBSIZE

# 4. PostgreSQL 연결 확인
docker exec trading_db_postgres psql -U trading_user -d trading_db -c "SELECT 1"
```

### STEP 1: 초기화

```bash
# Redis 초기화
docker exec trading_redis redis-cli FLUSHALL

# Scorecard 디렉토리 초기화
rm -rf scorecards/paper_phase16
mkdir -p scorecards/paper_phase16

# 로그 초기화
> logs/application.log
```

### STEP 2: REAL PAPER 1h 실행

```bash
# wall_clock 모드로 1시간 실행
python scripts/run_paper.py \
  --strategy scalping \
  --symbol BTCUSDT \
  --timeframe 3m \
  --duration-hours 1 \
  --duration-mode wall_clock
```

### STEP 3: 모니터링 (첫 60분)

**체크포인트**:
- **5분**: Entry Open ≥ 10, 에러 없음
- **10분**: Entry Open ≥ 20, Redis DBSIZE > 0
- **15분**: Entry Open ≥ 30, Closed ≥ 10
- **30분**: Entry Open ≥ 60, Closed ≥ 30, Guard 정상
- **45분**: Entry Open ≥ 90, Closed ≥ 50, PnL 계산 정상
- **60분**: 프로세스 정상 종료, Scorecard 생성 확인

**모니터링 명령어**:
```bash
# Entry Open 수
grep -c "ENTRY OPEN" logs/application.log

# Closed 수
grep -c "SL:|TP:" logs/application.log

# 에러 확인
grep -E "ERROR|Traceback" logs/application.log | tail -10

# Redis 활동도
docker exec trading_redis redis-cli DBSIZE
```

### STEP 4: 종료 및 검증

```bash
# Scorecard 생성 확인
ls -la scorecards/paper_phase16/*/scorecard.csv

# 메트릭 확인
cat scorecards/paper_phase16/*/scorecard.csv | head -5
```

### STEP 5: PASS/FAIL 판정

**PASS 기준**:
- ✅ 현실 시계 54분 이상 실행
- ✅ Entry Open ≥ 1
- ✅ Closed ≥ 1
- ✅ 치명적 에러/Traceback 없음
- ✅ Scorecard 생성됨

**FAIL 기준**:
- ❌ 현실 시계 54분 미만 실행
- ❌ Entry Open = 0 (거래 없음)
- ❌ Traceback 또는 RuntimeError 발생
- ❌ Scorecard 미생성

---

## 📝 구현 체크리스트

- [ ] `configs/base.yml`에 `paper.duration_mode` 추가
- [ ] `scripts/run_paper.py`에 `--duration-mode` CLI 인자 추가
- [ ] `execution/engine.py`의 `run()` 메서드에 wall_clock 모드 구현
- [ ] `execution/engine.py`에서 `start_wall_time` 기록 및 elapsed_wall 계산
- [ ] 로그에 wall_clock 모드 시작/종료 메시지 추가
- [ ] REAL PAPER 1h 테스트 실행 및 모니터링
- [ ] 테스트 결과 리포트 작성 (PHASE16_REAL_PAPER_1H_REPORT.md)

---

## 🔗 관련 문서

- `docs/PHASE16/PHASE16_REAL_PAPER_MODE.md`: REAL PAPER 모드 개요
- `docs/PHASE16/PHASE16_ENGINE_STRUCTURAL_FIXES.md`: 구조적 수정 내역
- `docs/PHASE16/PHASE16_REAL_PAPER_1H_REPORT.md`: 1h 테스트 결과 (작성 예정)

---

**작성일**: 2025-11-17  
**상태**: 설계 완료, 구현 대기
