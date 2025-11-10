# PHASE7-1 스모크 테스트 모니터링

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
- ✅ 오류 없음
- ✅ 정상 작동
- ✅ PHASE7-1 변경사항 적용 확인 완료

---

## 다음 체크 시간
- **1시간**: 11:13 KST
- **3시간**: 13:13 KST
- **24시간**: 2025-11-11 10:13 KST
