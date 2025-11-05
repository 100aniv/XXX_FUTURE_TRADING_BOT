# 🐳 Docker 사용 가이드

## 📋 **3가지 모드 개요**

| 모드 | 컨테이너명 | 용도 | 실제 거래 |
|------|-----------|------|----------|
| **SIM** | `trading_bot_sim` | 백테스트 (과거 데이터) | ❌ |
| **PAPER** | `trading_bot_paper` | 페이퍼 트레이딩 (실시간 데이터, 가상 거래) | ❌ |
| **LIVE** | `trading_bot_live` | 실거래 (Binance API) | ✅ |

---

## 🚀 **1. 시작하기**

### **1-1. DB만 시작 (공통)**
```bash
docker-compose up -d db_postgres
```

### **1-2. 백테스트 모드**
```bash
# 백테스트 실행
docker-compose --profile sim up -d

# 로그 확인
docker-compose --profile sim logs -f trading_bot_sim
```

### **1-3. 페이퍼 모드**
```bash
# 페이퍼 트레이딩 실행
docker-compose --profile paper up -d

# 로그 확인
docker-compose --profile paper logs -f trading_bot_paper
```

### **1-4. 라이브 모드** ⚠️ **실제 거래 주의!**
```bash
# .env 파일에 API 키 설정 필수
# BINANCE_API_KEY=...
# BINANCE_SECRET=...

# 라이브 실행
docker-compose --profile live up -d

# 로그 확인
docker-compose --profile live logs -f trading_bot_live
```

---

## 🛠️ **2. 관리 명령어**

### **2-1. 중지**
```bash
# 백테스트 중지
docker-compose --profile sim down

# 페이퍼 중지
docker-compose --profile paper down

# 라이브 중지
docker-compose --profile live down

# 전체 중지 (DB 포함)
docker-compose down
```

### **2-2. 재시작**
```bash
# 페이퍼 재시작
docker-compose --profile paper restart trading_bot_paper
```

### **2-3. 로그 확인**
```bash
# 실시간 로그
docker-compose --profile paper logs -f

# 최근 100줄
docker-compose --profile paper logs --tail=100

# 파일로 저장
docker-compose --profile paper logs > logs/docker_paper.log
```

### **2-4. 상태 확인**
```bash
# 컨테이너 상태
docker-compose ps

# 리소스 사용량
docker stats trading_bot_paper
```

---

## 🔧 **3. 설정 변경**

### **3-1. .env 파일 수정**
```bash
# .env 파일 수정
nano .env

# 컨테이너 재시작 (설정 반영)
docker-compose --profile paper restart trading_bot_paper
```

### **3-2. 코드 수정 후 재빌드**
```bash
# 이미지 재빌드
docker-compose build trading_bot_paper

# 재시작
docker-compose --profile paper up -d
```

### **3-3. 전략 파라미터 변경**
```bash
# strategy_params.yaml 수정
nano strategy_params.yaml

# hot reload (재시작 필요)
docker-compose --profile paper restart trading_bot_paper
```

---

## 📊 **4. DB 접속**

### **4-1. psql 접속**
```bash
docker exec -it trading_db_postgres psql -U trading_user -d trading_db
```

### **4-2. SQL 쿼리 예시**
```sql
-- 최근 거래 확인
SELECT * FROM trading.trades ORDER BY ts_open DESC LIMIT 10;

-- 오늘 거래 수익
SELECT 
    COUNT(*) as trades,
    SUM(pnl) as total_pnl
FROM trading.trades 
WHERE DATE(ts_open) = CURRENT_DATE;
```

---

## 🗂️ **5. 로그 및 데이터**

### **5-1. 로그 위치**
```
./logs/
├── application/   # 일반 로그
├── trading/       # 거래 로그
└── errors/        # 에러 로그
```

### **5-2. DB 데이터 백업**
```bash
# 덤프 생성
docker exec trading_db_postgres pg_dump -U trading_user trading_db > backup_$(date +%Y%m%d).sql

# 복구
docker exec -i trading_db_postgres psql -U trading_user -d trading_db < backup_20251020.sql
```

---

## ⚙️ **6. 멀티 모드 동시 실행**

```bash
# 백테스트 + 페이퍼 동시 실행
docker-compose --profile sim --profile paper up -d

# 전체 실행 (위험! 실거래 포함)
docker-compose --profile sim --profile paper --profile live up -d
```

---

## 🔍 **7. 트러블슈팅**

### **7-1. DB 연결 실패**
```bash
# DB 상태 확인
docker-compose ps db_postgres

# DB 로그 확인
docker-compose logs db_postgres

# DB 재시작
docker-compose restart db_postgres
```

### **7-2. 메모리 부족**
```bash
# 리소스 제한 설정 (docker-compose.yml)
resources:
  limits:
    memory: 2G
```

### **7-3. 네트워크 문제**
```bash
# 네트워크 재생성
docker network rm xxx_trading_network
docker network create xxx_trading_network
docker-compose up -d
```

---

## 📝 **8. 개발 워크플로우**

### **8-1. 로컬 개발 → Docker 테스트**
```bash
# 1. 로컬에서 개발
python main.py

# 2. Docker 빌드
docker-compose build trading_bot_paper

# 3. Docker 테스트
docker-compose --profile paper up

# 4. 문제 없으면 배포
docker-compose --profile paper up -d
```

### **8-2. Hot Reload (개발용)**
```bash
# volumes에 소스 마운트 (docker-compose.yml)
volumes:
  - .:/app  # 소스 코드 실시간 반영
  - ./logs:/app/logs
```

---

## 🎯 **9. 프로덕션 체크리스트**

### **라이브 모드 시작 전 확인사항:**

- [ ] `.env` 파일에 올바른 API 키 설정
- [ ] DB 백업 완료
- [ ] 전략 파라미터 검증 완료
- [ ] 백테스트 & 페이퍼 테스트 완료
- [ ] Risk 설정 확인 (`RISK_PER_TRADE`, `DAILY_LOSS_LIMIT_PCT`)
- [ ] Telegram 알림 설정 (`ENABLE_TELEGRAM=true`)
- [ ] 자본금 설정 확인 (`EQUITY_USDT`)
- [ ] 최대 포지션 수 제한 (`MAX_CONCURRENT_POSITIONS`)

---

## 📞 **10. 유용한 명령어 모음**

```bash
# 전체 재시작 (DB 제외)
docker-compose --profile paper restart

# 로그 실시간 + 검색
docker-compose --profile paper logs -f | grep "거래 실행"

# 컨테이너 셸 접속
docker exec -it trading_bot_paper /bin/bash

# 디스크 정리
docker system prune -a

# 이미지 재빌드 (캐시 무시)
docker-compose build --no-cache
```

---

## 🚨 **비상 정지**

```bash
# 즉시 중지
docker-compose --profile live stop trading_bot_live

# 완전 삭제 (재시작 불가)
docker-compose --profile live down

# 긴급 전체 중지 (DB 포함)
docker-compose down
```

---

## 📚 **참고 자료**

- **Docker Compose 문서**: https://docs.docker.com/compose/
- **PostgreSQL Docker**: https://hub.docker.com/_/postgres
- **프로젝트 구조**: `SYSTEM_ARCHITECTURE.md`
- **전략 가이드**: `STRATEGY_GUIDE.md`
