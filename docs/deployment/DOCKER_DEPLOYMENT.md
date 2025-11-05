# 🐳 Docker 배포 전략 가이드

**작성일**: 2024-10-18  
**목적**: 다양한 봇 배포 시나리오에 최적화된 Docker 전략

---

## 📋 **현재 구조 분석**

### **봇 구성 (총 8개 컨테이너)**

```
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL (1개)                                        │
│  - 모든 봇이 공유하는 중앙 DB                              │
│  - 포트: 5433 (호스트) → 5432 (컨테이너)                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  시그널 봇 (6개)                                          │
│  1. scalp-bot      (1분봉 스캘핑)                         │
│  2. intraday-bot   (5분봉 단타)                          │
│  3. swing-bot      (15분봉 스윙)                         │
│  4. trend-bot      (1시간봉 추세)                        │
│  5. reversion-bot  (5분봉 평균회귀)                      │
│  6. breakout-bot   (15분봉 돌파)                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  앙상블 봇 (1개)                                          │
│  - 6개 시그널을 통합하여 최종 결정                          │
│  - DB에서 시그널 읽기 → 앙상블 로직 → 최종 결정 저장        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  트레이딩 봇 (1개)                                        │
│  - 앙상블 결정 읽기 → 실제 매매 실행                        │
│  - 모드: BACKTEST / PAPER / LIVE                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 **배포 시나리오별 전략**

### **시나리오 1: 백테스트 모드 (개발/테스트)**

```bash
# 목적: 과거 데이터로 전략 검증

# 필요한 컨테이너:
✅ postgres (DB)
❌ 시그널 봇 (불필요 - 백테스트는 로컬 데이터 사용)
❌ 앙상블 봇 (불필요)
✅ trading-bot (백테스트 엔진 실행)

# 실행 방법:
docker-compose up postgres  # DB만 시작
python backtest/backtest_engine.py --strategy scalping --start 2024-07-01 --end 2024-10-01
```

**장점:**
- 리소스 절약 (DB만 실행)
- 빠른 반복 테스트
- 로컬에서 스크립트 직접 실행

**단점:**
- Docker의 격리 환경 미사용

---

### **시나리오 2: Paper Trading 모드 (실전 준비)**

```bash
# 목적: 실시간 데이터로 가상 매매

# 필요한 컨테이너:
✅ postgres
✅ 시그널 봇 6개 (실시간 시그널 생성)
✅ ensemble-bot (시그널 통합)
✅ trading-bot (모드=PAPER)

# 실행 방법:
docker-compose up -d

# 환경변수 설정:
TRADING_MODE=paper
```

**장점:**
- 전체 시스템 검증
- 실시간 데이터 사용
- 실전과 동일한 환경

**단점:**
- 리소스 사용 많음 (8개 컨테이너)
- 관리 복잡도 증가

---

### **시나리오 3: Live Trading 모드 (실전)**

```bash
# 목적: 실제 자금으로 매매

# 필요한 컨테이너:
✅ postgres
✅ 시그널 봇 6개
✅ ensemble-bot
✅ trading-bot (모드=LIVE)

# 실행 방법:
docker-compose up -d

# 환경변수 설정:
TRADING_MODE=live
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret
```

**장점:**
- 완전 자동화
- 24/7 운영
- 모든 봇 독립 실행

**단점:**
- 높은 리소스 요구
- 장애 시 빠른 대응 필요

---

## 🔧 **최적화 전략**

### **전략 A: 선택적 봇 실행**

특정 전략만 테스트하고 싶을 때:

```bash
# 예: SCALPING 전략만 테스트
docker-compose up -d postgres scalp-bot

# 예: 3개 전략만 실행 (TREND + REVERSION + BREAKOUT)
docker-compose up -d postgres trend-bot reversion-bot breakout-bot ensemble-bot
```

**docker-compose.yml에 프로파일 추가:**

```yaml
services:
  scalp-bot:
    profiles: ["scalping", "all"]
    # ...
  
  trend-bot:
    profiles: ["trend", "all"]
    # ...

# 사용법:
docker-compose --profile scalping up -d  # scalping만
docker-compose --profile all up -d       # 전체
```

---

### **전략 B: 개발/운영 환경 분리**

**docker-compose.yml** (기본 - 개발용)
```yaml
# 최소 구성: postgres + 1개 봇
services:
  postgres:
    # ...
  
  test-bot:
    # ...
```

**docker-compose.prod.yml** (운영용)
```yaml
# 전체 구성: postgres + 8개 봇
services:
  postgres:
    # ...
  scalp-bot:
    # ...
  # ... 나머지 봇들
```

**사용법:**
```bash
# 개발
docker-compose up -d

# 운영
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

### **전략 C: 리소스 제한 설정**

각 봇에 리소스 제한 추가:

```yaml
services:
  scalp-bot:
    deploy:
      resources:
        limits:
          cpus: '0.5'      # CPU 50%
          memory: 512M     # RAM 512MB
        reservations:
          cpus: '0.25'
          memory: 256M
    restart: unless-stopped
```

---

## 📊 **추천 배포 전략**

### **Phase 1: 백테스트 (현재 단계)**

```bash
# 목적: 전략 검증 및 파라미터 튜닝

# 방법 1: Docker 없이 (추천)
python backtest/backtest_engine.py --strategy scalping
python backtest/backtest_engine.py --strategy ensemble

# 방법 2: Docker 사용
docker-compose up -d postgres
docker exec -it trading_manager python /app/backtest/backtest_engine.py
```

**추천 이유:**
- 빠른 반복 실험
- 리소스 효율적
- 디버깅 용이

---

### **Phase 2: Paper Trading**

```bash
# 목적: 실시간 검증 (2주간)

# 단계별 실행:
# 1. DB 시작
docker-compose up -d postgres

# 2. 핵심 전략 3개만 시작
docker-compose up -d trend-bot reversion-bot breakout-bot

# 3. 앙상블 시작
docker-compose up -d ensemble-bot

# 4. 트레이딩 봇 시작 (PAPER 모드)
docker-compose up -d trading-bot

# 5. 모니터링
docker-compose logs -f --tail=100
```

**체크포인트:**
- [ ] 하루 10회 이상 거래 발생
- [ ] 승률 55% 이상 유지
- [ ] 일일 수익 3% 이상
- [ ] 예외 상황 없이 안정적 운영

---

### **Phase 3: Live Trading (소액)**

```bash
# 목적: 실전 검증 (소액 100-500 USDT)

# 전체 봇 실행
docker-compose --profile all up -d

# 환경변수 확인
docker-compose config | grep TRADING_MODE
docker-compose config | grep BINANCE_API_KEY

# 실시간 모니터링
watch -n 5 'docker-compose ps'
```

---

## 🛠️ **관리 명령어 모음**

### **기본 명령어**

```bash
# 전체 시작
docker-compose up -d

# 특정 봇만 시작
docker-compose up -d postgres scalp-bot

# 로그 확인
docker-compose logs -f scalp-bot

# 상태 확인
docker-compose ps

# 전체 중지
docker-compose down

# 재시작
docker-compose restart scalp-bot

# 리빌드 후 시작
docker-compose up -d --build
```

---

### **디버깅 명령어**

```bash
# 컨테이너 접속
docker exec -it signal_bot_scalp bash

# DB 접속
docker exec -it future_alarm_bot_postgres psql -U trading_user -d trading_db

# 리소스 사용량 확인
docker stats

# 네트워크 확인
docker network inspect future_alarm_bot_bot-network

# 볼륨 확인
docker volume ls
```

---

### **모니터링 명령어**

```bash
# 모든 봇 로그 (최근 100줄)
docker-compose logs --tail=100

# 특정 봇 실시간 로그
docker-compose logs -f ensemble-bot

# 에러만 필터링
docker-compose logs | grep ERROR

# CPU/메모리 모니터링
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## 🔄 **백테스트 전용 Docker 설정**

백테스트만을 위한 경량 설정:

**docker-compose.backtest.yml** (새로 생성)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: backtest_postgres
    environment:
      POSTGRES_USER: trading_user
      POSTGRES_PASSWORD: trading_pw_2024
      POSTGRES_DB: trading_db
    ports:
      - "5433:5432"
    volumes:
      - ./pgdata_backtest:/var/lib/postgresql/data
    networks:
      - backtest-network

  backtest-runner:
    build:
      context: .
      dockerfile: Dockerfile.backtest
    container_name: backtest_runner
    volumes:
      - ./backtest:/app/backtest
      - ./data:/app/data
      - ./results:/app/results
    environment:
      - DATABASE_URL=postgresql://trading_user:trading_pw_2024@postgres:5432/trading_db
    depends_on:
      - postgres
    networks:
      - backtest-network
    command: tail -f /dev/null  # 계속 실행 유지

networks:
  backtest-network:
    driver: bridge
```

**Dockerfile.backtest** (새로 생성)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 필요한 패키지만 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install pandas matplotlib seaborn

# 백테스트 관련 파일만 복사
COPY backtest/ ./backtest/
COPY trading_executor.py .
COPY config_*.txt ./

CMD ["bash"]
```

**사용법:**

```bash
# 백테스트 환경 시작
docker-compose -f docker-compose.backtest.yml up -d

# 백테스트 실행
docker exec -it backtest_runner python backtest/backtest_engine.py \
  --strategy scalping \
  --start 2024-07-01 \
  --end 2024-10-01 \
  --output results/scalping_bt.json

# 리포트 생성
docker exec -it backtest_runner python backtest/backtest_reporter.py \
  --input results/scalping_bt.json \
  --output reports/

# 종료
docker-compose -f docker-compose.backtest.yml down
```

---

## 📈 **리소스 요구사항**

### **최소 사양 (백테스트)**
- CPU: 2코어
- RAM: 4GB
- 디스크: 50GB (히스토리컬 데이터)

### **권장 사양 (Paper Trading)**
- CPU: 4코어
- RAM: 8GB
- 디스크: 100GB

### **운영 사양 (Live Trading)**
- CPU: 8코어
- RAM: 16GB
- 디스크: 200GB
- 네트워크: 안정적인 인터넷 연결

---

## ⚠️ **주의사항**

### **1. DB 데이터 백업**
```bash
# 백업
docker exec -it future_alarm_bot_postgres pg_dump -U trading_user trading_db > backup.sql

# 복원
docker exec -i future_alarm_bot_postgres psql -U trading_user trading_db < backup.sql
```

### **2. 로그 로테이션**
```yaml
# docker-compose.yml에 추가
services:
  scalp-bot:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### **3. 헬스 체크**
```yaml
services:
  scalp-bot:
    healthcheck:
      test: ["CMD", "python", "-c", "import psycopg2"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 🎯 **최종 권장 사항**

### **현재 단계 (백테스트)**
```bash
# ✅ 추천: Docker 없이 로컬 실행
python backtest/backtest_engine.py --strategy scalping

# 장점:
# - 빠른 실행
# - 쉬운 디버깅
# - 유연한 파라미터 조정
```

### **다음 단계 (Paper Trading)**
```bash
# ✅ 추천: 핵심 봇만 Docker로 실행
docker-compose up -d postgres trend-bot reversion-bot breakout-bot ensemble-bot trading-bot

# 장점:
# - 실전과 유사한 환경
# - 안정성 검증
# - 성능 모니터링
```

### **최종 단계 (Live Trading)**
```bash
# ✅ 추천: 전체 봇 Docker로 실행
docker-compose --profile all up -d

# 장점:
# - 완전 자동화
# - 격리된 환경
# - 쉬운 확장성
```

---

## 📝 **체크리스트**

### **백테스트 시작 전**
- [ ] 히스토리컬 데이터 다운로드 완료
- [ ] `backtest_engine.py` 테스트
- [ ] `backtest_reporter.py` 테스트
- [ ] PostgreSQL 접속 확인

### **Paper Trading 시작 전**
- [ ] 백테스트 결과 검토 완료
- [ ] 모든 봇 로그 확인
- [ ] DB 스키마 확인
- [ ] Telegram 알림 테스트

### **Live Trading 시작 전**
- [ ] Paper Trading 2주 이상 안정적 운영
- [ ] Binance API 키 설정
- [ ] 소액 자금 입금 (100-500 USDT)
- [ ] 긴급 중단 프로세스 확립
- [ ] 모니터링 대시보드 구축

---

**Last Updated:** 2024-10-18  
**Next Review:** Paper Trading 시작 전
