# 🐳 Docker 배포 가이드

**통합 트레이딩 시스템 v2.0 - Docker 배포**

---

## 📋 목차

1. [개요](#개요)
2. [기존 컨테이너 정리](#기존-컨테이너-정리)
3. [새로운 구조](#새로운-구조)
4. [배포 방법](#배포-방법)
5. [모니터링](#모니터링)

---

## 개요

### **옛날 구조 (제거 필요)**
```
✅ future_alarm_bot_postgres  (DB - 유지)
❌ signal_bot_scalp           (삭제)
❌ signal_bot_daytrade         (삭제)
❌ signal_bot_intraday         (삭제)
❌ signal_bot_swing            (삭제)
❌ signal_bot_trend            (삭제)
❌ signal_bot_reversion        (삭제)
❌ signal_bot_breakout         (삭제)
❌ signal_bot_ensemble         (삭제)
❌ trading_manager             (삭제)
```

### **새로운 구조 (통합)**
```
✅ trading_system_postgres  (DB - 또는 기존 future_alarm_bot_postgres 사용)
✅ trading_system_main      (통합 시스템 - main.py)
```

---

## 기존 컨테이너 정리

### **Windows (PowerShell)**

```powershell
# 정리 스크립트 실행
PowerShell -ExecutionPolicy Bypass -File cleanup_docker.ps1
```

또는 수동:

```powershell
# 옛날 봇들 중지 및 삭제
docker stop signal_bot_scalp signal_bot_daytrade signal_bot_intraday signal_bot_swing
docker stop signal_bot_trend signal_bot_reversion signal_bot_breakout
docker stop signal_bot_ensemble trading_manager

docker rm signal_bot_scalp signal_bot_daytrade signal_bot_intraday signal_bot_swing
docker rm signal_bot_trend signal_bot_reversion signal_bot_breakout
docker rm signal_bot_ensemble trading_manager

# DB는 유지!
# docker ps | grep postgres  (확인)
```

### **Linux/Mac (Bash)**

```bash
# 정리 스크립트 실행
bash cleanup_docker.sh
```

---

## 새로운 구조

### **docker-compose.yml**

```yaml
version: '3.8'

services:
  # PostgreSQL (기존 사용 가능)
  postgres:
    image: postgres:16
    container_name: trading_system_postgres
    ...
  
  # 통합 트레이딩 시스템
  main:
    build: .
    container_name: trading_system_main
    command: python -u main.py
    ...
```

---

## 배포 방법

### **1. 기존 컨테이너 정리**

```bash
# Windows
PowerShell -ExecutionPolicy Bypass -File cleanup_docker.ps1

# Linux/Mac
bash cleanup_docker.sh
```

### **2. 환경변수 설정**

`.env` 파일:

```bash
# Database (기존 DB 사용)
DATABASE_URL=postgresql://trading_user:trading_pw_2024@postgres:5432/trading_db

# Strategy & Mode
STRATEGY_SELECTOR=ensemble
TRADING_MODE=paper

# Risk
EQUITY_USDT=10000
RISK_PER_TRADE=0.01

# Symbols
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAME=5m
```

### **3. Docker 빌드 및 실행**

```bash
# Dockerfile 교체
mv Dockerfile _archived/Dockerfile_old
mv Dockerfile.new Dockerfile

# 빌드 및 시작
docker-compose build
docker-compose up -d

# 또는 DB만 시작 (기존 DB 사용)
docker-compose up -d postgres

# 메인 시스템 시작
docker-compose up -d main
```

### **4. 로그 확인**

```bash
# 실시간 로그
docker logs -f trading_system_main

# 최근 100줄
docker logs --tail 100 trading_system_main
```

---

## 모니터링

### **컨테이너 상태**

```bash
# 실행 중인 컨테이너
docker ps

# 모든 컨테이너
docker ps -a

# 리소스 사용량
docker stats
```

### **DB 확인**

```bash
# DB 접속
docker exec -it trading_system_postgres psql -U trading_user -d trading_db

# 신호 확인
SELECT * FROM monitoring.signals ORDER BY created_at DESC LIMIT 10;

# 결정 확인
SELECT * FROM trading.decisions ORDER BY created_at DESC LIMIT 10;

# 거래 확인
SELECT * FROM trading.trades ORDER BY created_at DESC LIMIT 10;
```

### **로그 확인**

```bash
# 호스트에서
cd logs/
tail -f application/2025-10-19.log
tail -f trading/2025-10-19.log
```

---

## 문제 해결

### **Q: 컨테이너가 시작되지 않습니다**

```bash
# 로그 확인
docker logs trading_system_main

# 상태 확인
docker ps -a | grep trading_system

# 재시작
docker-compose restart main
```

### **Q: DB 연결 실패**

```bash
# PostgreSQL 상태 확인
docker ps | grep postgres

# DB 로그
docker logs trading_system_postgres

# 연결 테스트
docker exec -it trading_system_postgres pg_isready -U trading_user
```

### **Q: 기존 데이터 유지하고 싶습니다**

```bash
# 기존 DB 컨테이너 유지
# docker-compose.yml에서 postgres 서비스 주석 처리

# DATABASE_URL을 기존 컨테이너로 변경
DATABASE_URL=postgresql://trading_user:trading_pw_2024@future_alarm_bot_postgres:5432/trading_db
```

---

## 중지 및 제거

### **중지**

```bash
docker-compose stop
```

### **제거 (데이터 유지)**

```bash
docker-compose down
```

### **완전 제거 (데이터 포함)**

```bash
# ⚠️ 주의: 모든 데이터 삭제!
docker-compose down -v
rm -rf pgdata/
```

---

## 업데이트

### **코드 업데이트**

```bash
# Git pull
git pull

# 재빌드 및 재시작
docker-compose build
docker-compose up -d
```

### **설정 업데이트**

```bash
# .env 파일 수정
nano .env

# 재시작
docker-compose restart main
```

---

**최종 업데이트**: 2025-10-19  
**버전**: v2.0
