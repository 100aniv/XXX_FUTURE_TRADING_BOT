# 🔄 마이그레이션 가이드

**기존 시스템 → 새 통합 시스템**

---

## 📊 구조 변경

### 기존
```
future_alarm_bot/
├── future_alarm_bot_postgres
├── signal_bot_trend
├── signal_bot_reversion
├── signal_bot_breakout
├── signal_bot_ensemble
└── trading_manager
```

### 새로운
```
future_trading_system/
├── postgres  (future_trading_system_postgres)
└── main     (future_trading_system_main)
```

---

## 🚀 마이그레이션 단계

### **1단계: 기존 데이터 백업**

```bash
# PostgreSQL 데이터 백업
docker exec future_alarm_bot_postgres pg_dump -U trading_user trading_db > backup_$(date +%Y%m%d).sql

# 또는 pgdata 폴더 복사
cp -r pgdata pgdata_backup_$(date +%Y%m%d)
```

### **2단계: 기존 컨테이너 중지 (DB 제외)**

```bash
# 신호 봇들 중지
docker stop signal_bot_trend
docker stop signal_bot_reversion
docker stop signal_bot_breakout
docker stop signal_bot_ensemble
docker stop trading_manager

# 삭제
docker rm signal_bot_trend
docker rm signal_bot_reversion
docker rm signal_bot_breakout
docker rm signal_bot_ensemble
docker rm trading_manager

# 확인
docker ps -a
```

### **3단계: 기존 DB 중지 (데이터 보존)**

```bash
# 기존 DB 중지 (데이터는 pgdata 폴더에 보존됨)
docker stop future_alarm_bot_postgres
docker rm future_alarm_bot_postgres
```

### **4단계: docker-compose.yml 교체**

```bash
# 기존 파일 백업
mv docker-compose.yml docker-compose.old.yml

# 새 파일 적용
mv docker-compose-new.yml docker-compose.yml
```

### **5단계: 데이터 이전**

**Option A: pgdata 폴더 그대로 사용 (권장)**

```bash
# pgdata 폴더가 이미 있으면 그대로 사용
# docker-compose.yml의 volume 설정이 ./pgdata를 사용하므로
# 기존 데이터가 자동으로 마운트됨
```

**Option B: 새 DB 생성 후 데이터 복원**

```bash
# 새 DB 시작
docker-compose up -d postgres

# 백업 복원
cat backup_YYYYMMDD.sql | docker exec -i future_trading_system_postgres psql -U trading_user trading_db
```

### **6단계: 새 시스템 시작**

```bash
# 빌드
docker-compose build

# 시작
docker-compose up -d

# 로그 확인
docker logs -f future_trading_system_main
```

### **7단계: 검증**

```bash
# 컨테이너 확인
docker ps

# DB 연결 확인
docker exec -it future_trading_system_postgres psql -U trading_user -d trading_db

# 데이터 확인
SELECT COUNT(*) FROM monitoring.signals;
SELECT COUNT(*) FROM trading.decisions;
SELECT COUNT(*) FROM trading.trades;
```

---

## 🔍 문제 해결

### Q: 기존 데이터가 안 보입니다

```bash
# pgdata 경로 확인
docker-compose down
ls -la pgdata/

# 권한 확인
sudo chown -R 999:999 pgdata/  # PostgreSQL UID:GID

# 다시 시작
docker-compose up -d
```

### Q: 네트워크 오류

```bash
# 기존 네트워크 정리
docker network prune

# docker-compose 재시작
docker-compose down
docker-compose up -d
```

### Q: 포트 충돌

```bash
# 5433 포트 사용 중인 프로세스 확인
netstat -ano | findstr :5433  # Windows
lsof -i :5433  # Linux/Mac

# docker-compose.yml에서 포트 변경
ports:
  - "5434:5432"  # 외부 포트 변경
```

---

## ✅ 체크리스트

### 마이그레이션 전
- [ ] 기존 데이터 백업 완료
- [ ] `.env` 파일 준비
- [ ] 기존 컨테이너 목록 확인

### 마이그레이션 중
- [ ] 기존 봇들 중지 및 삭제
- [ ] 기존 DB 중지
- [ ] docker-compose.yml 교체
- [ ] 데이터 이전 (pgdata)

### 마이그레이션 후
- [ ] 컨테이너 정상 실행 확인
- [ ] DB 연결 확인
- [ ] 데이터 존재 확인
- [ ] 로그 정상 확인
- [ ] 신호 생성 테스트

---

## 📝 롤백 방법

문제 발생 시 기존 시스템으로 복구:

```bash
# 새 시스템 중지
docker-compose down

# 기존 설정 복원
mv docker-compose.old.yml docker-compose.yml

# 기존 시스템 재시작
docker-compose up -d
```

---

**작성일**: 2025-10-19  
**버전**: v2.0
