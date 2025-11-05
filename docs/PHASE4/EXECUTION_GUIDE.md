# 실행 가이드

**최종 업데이트**: 2025-10-29 00:10 UTC+09:00

---

## 🚀 페이퍼 모드 실행

```bash
# 전체 6전략 실행
docker compose --profile paper up -d

# 개별 전략 실행
docker compose --profile paper-scalping up -d

# 로그 확인
docker logs -f trading_bot_paper_scalping
```

---

## 📊 베이지안 튜닝 (전략별 데이터 수집 기간)

**config.yml에 설정된 전략별 스케줄**:

| 전략 | 실행 주기 | 데이터 수집 기간 | 최소 거래 수 |
|------|----------|----------------|-------------|
| **scalping** | 1시간마다 | 최근 1시간 | 10건 |
| **daytrade** | 4시간마다 | 최근 4시간 | 5건 |
| **reversion** | 8시간마다 | 최근 8시간 | 3건 |
| **breakout** | 8시간마다 | 최근 8시간 | 3건 |
| **swing** | 12시간마다 | 최근 24시간 | 2건 |
| **trend** | 1일마다 | 최근 24시간 | 1건 |

### 수동 튜닝 실행

```bash
# scalping 튜닝 (최근 1시간 데이터)
python common/tuning_cli.py \
  --strategy scalping \
  --study scalping_v1 \
  --trials 10 \
  --publish file

# daytrade 튜닝 (최근 4시간 데이터)
python common/tuning_cli.py \
  --strategy daytrade \
  --study daytrade_v1 \
  --trials 10 \
  --publish file
```

### 자동 튜닝 스케줄러 (Docker)

```bash
# 튜닝 스케줄러 시작
docker compose up -d tuning_scheduler

# 로그 확인
docker logs -f tuning_scheduler
```

---

## 📈 모니터링

### 거래 확인

```sql
-- 전략별 최근 거래
SELECT strategy, COUNT(*) as trades, AVG(pnl) as avg_pnl
FROM trading.trades 
WHERE status='CLOSED' 
AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY strategy;
```

### 컨테이너 상태

```bash
# 실행 중인 컨테이너
docker ps

# 로그 확인
docker logs -f trading_bot_paper_scalping
```

---

## 🔧 설정 변경

### 자산 변경

```yaml
# config.yml
capital:
  initial: 100000
equity: 100000
```

### 튜닝 주기 변경

```yaml
# config.yml
tuning:
  schedules:
    scalping:
      every_hours: 2  # 1시간 → 2시간
      recent_hours: 2  # 데이터 수집 기간도 함께 변경
```

---

**상태**: ✅ 준비 완료  
**다음**: 페이퍼 모드 실행 → 자동 튜닝
