# DB 메트릭 비교: 복원 전/후 및 24h 베이스라인

**작성일**: 2025-11-13  
**복원 커밋**: 31cd5d7 (2025-11-13 18:09:40+09:00)  
**목적**: 복원 전(Pre) 6h vs 복원 후(Post) 2.75h vs 24h 베이스라인 비교

---

## 📊 요약 비교

| 구간 | 기간 | Closed | Win Rate | Avg PnL | Min PnL | Max PnL | >8% 손실 |
|------|------|--------|----------|---------|---------|---------|----------|
| **Pre (복원 전)** | 6h (12:09~18:09) | 392 | 34.4% | -0.40% | -32.47% | +70.40% | 22건 |
| **Post (복원 후)** | 2.75h (18:09~현재) | 1,158 | 36.3% | -0.37% | -31.01% | +62.25% | 42건 |
| **24h 베이스라인** | 24h | 1,550 | 35.8% | -0.38% | -32.47% | +70.40% | 64건 |

---

## 🔍 상세 분석

### 1. 복원 전 (Pre) - 6시간
**기간**: 2025-11-13 12:09:40 ~ 18:09:40 (6h)

#### 요약
- Closed: 392건
- Win Rate: **34.4%**
- Avg PnL: -0.40%
- Min/Max: -32.47% / +70.40%
- **>8% 손실: 22건** (5.6%)

#### 종료 사유 분포
| Exit Reason | Count | Avg PnL | Min PnL | Max PnL |
|-------------|-------|---------|---------|---------|
| TP1 | 214 (54.6%) | +2.50% | -4.86% | +70.40% |
| SL | 177 (45.2%) | -3.91% | -32.47% | +4.98% |
| ONE_WAY_MODE | 1 (0.3%) | +0.32% | +0.32% | +0.32% |

#### 특이사항
- TP1에서 손실 발생: -4.86% (수수료 반영 후 손실)
- 시간당 거래: 65.3건 (392/6)

---

### 2. 복원 후 (Post) - 2.75시간
**기간**: 2025-11-13 18:09:40 ~ 현재 (약 2.75h)

#### 요약
- Closed: 1,158건
- Win Rate: **36.3%** (+1.9%p vs Pre)
- Avg PnL: -0.37% (+0.03%p vs Pre)
- Min/Max: -31.01% / +62.25%
- **>8% 손실: 42건** (3.6%, Pre 대비 -2.0%p)

#### 종료 사유 분포
| Exit Reason | Count | Avg PnL | Min PnL | Max PnL |
|-------------|-------|---------|---------|---------|
| TP1 | 687 (59.3%) | +1.95% | -5.90% | +62.25% |
| SL | 467 (40.3%) | -3.79% | -31.01% | +4.98% |
| ONE_WAY_MODE | 4 (0.3%) | +0.86% | -0.88% | +4.50% |

#### 특이사항
- TP1에서 손실 발생: -5.90% (Pre보다 악화)
- 시간당 거래: 421.1건 (1,158/2.75) ← **Pre 대비 6.4배 증가**
- TP1 비율 증가: 54.6% → 59.3% (+4.7%p)
- SL 비율 감소: 45.2% → 40.3% (-4.9%p)

---

### 3. 24시간 베이스라인
**기간**: 최근 24시간

#### 요약
- Closed: 1,550건
- Win Rate: **35.8%**
- Avg PnL: -0.38%
- Min/Max: -32.47% / +70.40%
- **>8% 손실: 64건** (4.1%)

#### 종료 사유 분포
| Exit Reason | Count | Avg PnL | Min PnL | Max PnL |
|-------------|-------|---------|---------|---------|
| TP1 | 901 (58.1%) | +2.08% | -5.90% | +70.40% |
| SL | 644 (41.5%) | -3.83% | -32.47% | +4.98% |
| ONE_WAY_MODE | 5 (0.3%) | +0.75% | -0.88% | +4.50% |

#### 특이사항
- 시간당 거래: 64.6건 (1,550/24)
- TP1 손실 최악: -5.90%

---

### 4. 무결성 (현재 상태)
- **양방향 동시 오픈**: 0건 ✅
- **현재 오픈 포지션**: 12개

---

## 🚨 핵심 발견

### 1. 승률 개선 미미 (+1.9%p)
- Pre: 34.4% → Post: 36.3%
- 통계적으로 유의미하지 않을 수 있음 (거래 수 차이 고려 필요)

### 2. 거래 빈도 폭증 (6.4배)
- Pre: 시간당 65.3건
- Post: 시간당 421.1건
- **원인 추정**: 복원 후 쿨다운/필터 설정 차이 또는 시장 변동성 증가

### 3. >8% 손실 비율 개선
- Pre: 5.6% (22/392)
- Post: 3.6% (42/1,158)
- 절대 건수는 증가했지만, 비율은 감소

### 4. TP1 손실 악화
- Pre: -4.86%
- Post: -5.90%
- **문제**: TP1 도달 후에도 손실 발생 (수수료 + 슬리피지 영향 추정)

### 5. TP1/SL 비율 변화
- TP1 비율: 54.6% → 59.3% (+4.7%p)
- SL 비율: 45.2% → 40.3% (-4.9%p)
- **해석**: 복원 후 TP1 도달이 더 빈번해짐 (긍정적)

---

## 📋 결론 및 권장사항

### 현황
1. **승률**: 35~36% 수준 유지 (목표 45% 대비 -10%p 부족)
2. **거래 빈도**: 복원 후 급증 (원인 분석 필요)
3. **손실 상한**: >8% 손실 비율은 개선되었으나 절대 건수는 여전히 높음
4. **무결성**: 양방향 동시 오픈 0건 (정상)

### 권장 액션
1. **A/B 1시간 실험 필수**
   - 현행 설정(A) vs 복원 전 설정(B)
   - run_id 격리로 동일 조건 비교
   - 거래 빈도 차이 원인 규명

2. **거래 빈도 분석**
   - 쿨다운 설정 확인 (config.yml)
   - 전략별 신호 발생 빈도 로그 분석
   - 시장 변동성 vs 설정 변경 영향 분리

3. **TP1 손실 원인 규명**
   - 수수료 반영 로직 재검증
   - 슬리피지 영향 분석 (현재 0.05% 고정)
   - OHLC 체크 로직 검증

4. **승률 개선 계획**
   - 현재 35.8% → 목표 45% (PHASE7-2 최소 게이트)
   - 전략별 성과 분석 필요 (PHASE7-4)
   - 신호 필터링 강화 검토

---

## 📌 다음 단계

1. **즉시**: A/B 1시간 실험 실행 (SMOKE_TEST_MONITOR.md 절차 참조)
2. **단기**: 거래 빈도 급증 원인 분석 (로그/설정 확인)
3. **중기**: 승률 45% 달성 계획 수립 (PHASE7-2/4 재개 검토)
4. **장기**: 상용 수준(55~60%) 달성 로드맵 (PHASE7_ALGORITHM_BEST.md)

---

## 📊 SQL 쿼리 (재현용)

### Pre (복원 전 6h)
```sql
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)
             / NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM trading.trades
WHERE mode='paper'
  AND created_at >= '2025-11-13 12:09:40+09:00'
  AND created_at < '2025-11-13 18:09:40+09:00';
```

### Post (복원 후)
```sql
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)
             / NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM trading.trades
WHERE mode='paper'
  AND created_at >= '2025-11-13 18:09:40+09:00';
```

### 24h 베이스라인
```sql
SELECT COUNT(*) FILTER (WHERE status='CLOSED') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status='CLOSED' AND pnl_pct > 0)
             / NULLIF(COUNT(*) FILTER (WHERE status='CLOSED'),0), 1) AS win_rate,
       ROUND(AVG(pnl_pct)::numeric,2) AS avg_pnl,
       ROUND(MIN(pnl_pct)::numeric,2) AS min_pnl,
       ROUND(MAX(pnl_pct)::numeric,2) AS max_pnl
FROM trading.trades
WHERE mode='paper'
  AND created_at >= NOW() - INTERVAL '24 hours';
```
