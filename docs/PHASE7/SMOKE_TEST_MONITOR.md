# PHASE7-1 스모크 테스트 모니터링

**최종 업데이트**: 2025-11-13  
**현행 코드(b84c03c)**: 슬리피지 미구현, OHLC SL 활성, 중복 진입/ONE-WAY 정상  

## ⚠️ 현재 상태 스냅샷 (최근 30/60분 · Paper)

- **60분**: closed=394, win_rate=31.2%, >8% 손실=20건  
  - Exit breakdown: SL 201건(avg -3.83%, min -16.65%), TP1 196건(avg +2.28%, min -4.86%), ONE_WAY_MODE 2건
- **30분**: closed=151, win_rate=26.5%, avg_pnl=-0.84%, min=-12.05%, max=+25.30%  
- **무결성**: 중복 진입 0, 양방향 OPEN 0, OPEN=13

## 실측 스냅샷 결과 (최근 2시간)

- closed=818, win_rate=38.3%, avg_pnl=-0.24%, min=-31.01%, max=+62.25
- Exit: TP1 532(avg 1.77, min -5.90, max 62.25), SL 283(avg -3.97, min -31.01, max 4.98), ONE_WAY_MODE 3(avg -1.15, min -7.45, max 4.50)
- >8% 손실: 29
- 무결성: 양방향 OPEN 0, 현재 OPEN 11

## 실측 스냅샷 결과 (최근 24시간)

- closed=1,550, win_rate=35.8%, avg_pnl=-0.38%, min=-32.47, max=+70.40
- Exit: TP1 901(avg 2.08, min -5.90, max 70.40), SL 644(avg -3.83, min -32.47, max 4.98), ONE_WAY_MODE 5(avg 0.75, min -0.88, max 4.50)
- >8% 손실: 64
- 무결성: 양방향 OPEN 0, 현재 OPEN 11

### 사용한 SQL 쿼리

```sql
-- 60m 승률/총합
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0) AS wins,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)/ NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate
FROM trading.trades
WHERE mode='paper' AND created_at >= NOW() - INTERVAL '60 minutes';

-- 30m 요약
WITH t AS (
  SELECT * FROM trading.trades WHERE mode='paper' AND created_at >= NOW() - INTERVAL '30 minutes'
)
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)/ NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM t;

-- 60m 종료 사유
WITH t AS (
  SELECT * FROM trading.trades WHERE mode='paper' AND status='CLOSED' AND created_at >= NOW() - INTERVAL '60 minutes'
)
SELECT exit_reason, COUNT(*) AS cnt,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM t GROUP BY exit_reason ORDER BY cnt DESC;

-- >8% 손실 수
SELECT COUNT(*) AS losses_over_8pct
FROM trading.trades
WHERE mode='paper' AND status='CLOSED' AND created_at >= NOW() - INTERVAL '60 minutes' AND pnl_pct <= -8;

---
## 시작 시간
- **시작**: 2025-11-10 10:13 KST
- **리빌드**: --no-cache 완전 재빌드
- **프로파일**: paper (trading_bot_paper_ensemble)

## 변경사항 적용 확인 ✅

### 1. calculate_pnl() 수수료 반영
```python
(position: Dict, exit_price: float, fee_rate: float = 0.0004) -> float
```
✅ **적용 완료** (10:28 확인)

### 2. check_tpsl_with_partial() OHLC
```python
(self, position: Dict, current_price: float, atr: float = None, candle: Dict = None)
```
✅ **적용 완료** (10:28 확인)

### 3. config.yml
```yaml
use_ohlc_check: True
sl_priority: BEFORE_TP
extreme_loss_cutoff_pct: -20.0
```
✅ **적용 완료** (10:28 확인)

## 초기 5분 모니터링 (10:13~10:28)

### 컨테이너 상태
- ✅ trading_bot_paper_ensemble: 정상
- ✅ trading_db_postgres: Healthy
- ✅ trading_redis: Started
- ✅ ERROR/Exception: 0건

### 로그 상태
- ✅ 히스토리 로드: 100개 심볼 완료
- ✅ 앙상블 신호: 정상 생성
- ✅ Leverage 계산: 정상
- ✅ 쿨다운/필터: 정상

## 모니터링 체크리스트

### 1시간 체크 (11:13)
- [ ] 컨테이너 실행 상태
- [ ] ERROR/Exception 발생 여부
- [ ] 거래 발생 시 PnL 수수료 차감 확인
- [ ] OHLC SL 체크 로그 확인
- [ ] Extreme Loss -20% 로그 확인

### 3시간 체크 (13:13)
- [ ] 컨테이너 안정성
- [ ] 메모리/CPU 사용률
- [ ] 거래 건수 및 PnL 패턴
- [ ] 8% 초과 손실 발생 여부

### 24시간 검증 (익일 10:13)
- [ ] 총 거래 건수
- [ ] 8% 초과 손실: 0건 목표
- [ ] TP1 손실: 0건 목표
- [ ] Extreme Loss -20% 청산 건수

## 모니터링 명령어

### 실시간 로그
```powershell
docker logs trading_bot_paper_ensemble -f
```

### 오류 검색
```powershell
docker logs trading_bot_paper_ensemble --tail 200 | Select-String -Pattern "ERROR|Exception|Traceback|EXTREME_LOSS" -Context 3
```

### 거래 확인 (DB)
```sql
SELECT 
  symbol, side, entry, exit_price, pnl, pnl_pct, exit_reason,
  ts_open, ts_close
FROM trading.trades 
WHERE mode='paper' AND ts_open >= NOW() - INTERVAL '1 hour'
ORDER BY ts_close DESC
LIMIT 20;
```

### 8% 초과 손실 체크
```sql
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN pnl_pct < -8 THEN 1 END) as over_8pct,
  COUNT(CASE WHEN exit_reason='TP1' AND pnl_pct < 0 THEN 1 END) as tp1_loss
FROM trading.trades 
WHERE mode='paper' AND ts_open >= '2025-11-10 10:13:00';
```

## 이슈 로그

### 10:13 - 시작
- 컨테이너 정상 시작
- 변경사항 모두 적용 확인

### 10:28 - 초기 5분 체크
- 오류 없음
- 정상 작동
- PHASE7-1 변경사항 적용 확인 완료

---

## A/B 1시간 대조 실험 절차

### 목적
- 설정 차이가 승률/PnL/손실 상한/무결성에 미치는 영향을 1h 단위로 비교.

### 사전 준비
- env=paper 고정, 동일 심볼/전략/브로커 사용.
- `run_id` 2개 생성(A/B)로 DB/Redis 완전 격리.
- A: 현행 설정(복원 후 HEAD). B: 복원 전 설정(플래시가드 15%, TP/트레일링 구조 등).

### 실행 개요
1) A 실행: RUN_ID_A로 60분 운용.
2) B 실행: 복원 전 `config.yml`만 임시 적용 후 RUN_ID_B로 60분 운용.
3) 두 실험 종료 즉시 DB 스냅샷 쿼리 실행(아래 SQL, run_id 필터 필수).

### 수집 SQL (run_id 필터 예시)
```sql
-- 1h 요약 (A 또는 B)
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)
             / NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM trading.trades
WHERE mode='paper' AND run_id='${RUN_ID_X}' AND created_at >= NOW() - INTERVAL '60 minutes';

-- 1h 종료 사유
WITH t AS (
  SELECT * FROM trading.trades
  WHERE mode='paper' AND status='CLOSED' AND run_id='${RUN_ID_X}'
    AND created_at >= NOW() - INTERVAL '60 minutes'
)
SELECT exit_reason, COUNT(*) AS cnt,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM t GROUP BY exit_reason ORDER BY cnt DESC;

-- 무결성 (오픈/양방향/중복)
WITH d AS (
  SELECT DISTINCT symbol, side FROM trading.trades
  WHERE mode='paper' AND status='OPEN' AND run_id='${RUN_ID_X}'
), c AS (
  SELECT symbol, COUNT(*) AS sides FROM d GROUP BY symbol
)
SELECT COUNT(*) AS symbols_with_both_sides FROM c WHERE sides >= 2;

SELECT COUNT(*) AS open_positions
FROM trading.trades WHERE mode='paper' AND status='OPEN' AND run_id='${RUN_ID_X}';
```

### 판정 기준(예시)
- 승률 우위(±3%p 이상) AND >8% 손실 0건 AND 무결성 100% → 채택.
- 거래 수가 크게 다르면 PF/avg PnL 함께 비교.

---

## 24h 베이스라인 스냅샷 절차

### 목적
- “현재 설정”의 24시간 성과를 베이스라인으로 고정(변경 전/후 비교 기준).

### 방법
- 별도 실험 없이, DB에서 최근 24h 집계만 수행.
- 단, “설정 변경 효과의 24h 유효성”을 보려면 변경 후 24h 연속 운용 후 동일 쿼리를 재수행.

### SQL
```sql
-- 24h 요약
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)
             / NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM trading.trades
WHERE mode='paper' AND created_at >= NOW() - INTERVAL '24 hours';

-- 24h 종료 사유
WITH t AS (
  SELECT * FROM trading.trades WHERE mode='paper' AND status='CLOSED'
    AND created_at >= NOW() - INTERVAL '24 hours'
)
SELECT exit_reason, COUNT(*) AS cnt,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM t GROUP BY exit_reason ORDER BY cnt DESC;

-- 24h >8% 손실
SELECT COUNT(*) AS losses_over_8pct
FROM trading.trades
WHERE mode='paper' AND status='CLOSED'
  AND created_at >= NOW() - INTERVAL '24 hours' AND pnl_pct <= -8;
```

---

## 다음 체크 시간
- **1시간**: 11:13 KST
- **3시간**: 13:13 KST
- **24시간**: 2025-11-11 10:13 KST
