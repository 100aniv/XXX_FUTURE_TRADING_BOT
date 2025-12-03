# PHASE26-3: Multi-Symbol Performance Test Report

**실행 일시**: [YYYY-MM-DD HH:MM:SS]  
**실행 태그**: [TAG]  
**테스트 타입**: [Single Top-N | Scaling Test]  
**실행자**: [실행자 이름]

---

## Executive Summary

| 항목 | 값 |
|------|-----|
| **Top-N 단계** | [10, 20, 50, 100] |
| **각 단계 실행 시간** | [N]분 |
| **총 실행 시간** | [N]분 |
| **성공 단계** | [N]/[N] |
| **CRITICAL 오류** | [N]건 |
| **최종 판정** | ✅ PASS / ❌ FAIL |

---

## 1. Acceptance Criteria 검증

### 1.1. 성능 목표

| Criteria | Target | 실측값 | 판정 |
|----------|--------|--------|------|
| **평균 Loop Latency** | ≤ 150ms | [N]ms | ✅/❌ |
| **P95 Loop Latency** | ≤ 250ms | [N]ms | ✅/❌ |
| **CPU 사용률 (평균)** | ≤ 70% | [N]% | ✅/❌ |
| **Memory 사용량 (평균)** | ≤ 800MB | [N]MB | ✅/❌ |
| **CRITICAL 오류** | 0건 | [N]건 | ✅/❌ |

### 1.2. Trade Activity

| Criteria | Target | 실측값 | 판정 |
|----------|--------|--------|------|
| **Aggregate 평가 수** | ≥ 100건 | [N]건 | ✅/❌ |
| **활성 Trade 심볼 수** | ≥ 3개 | [N]개 | ✅/❌ |
| **Active Positions (종료 시)** | 0건 | [N]건 | ✅/❌ |

---

## 2. 단계별 실행 결과

### 2.1. Top10 Results

| 메트릭 | 값 |
|--------|-----|
| **실행 시간** | [N]분 |
| **평균 Loop Latency** | [N]ms |
| **P95 Loop Latency** | [N]ms |
| **평균 CPU** | [N]% |
| **평균 메모리** | [N]MB |
| **에러 수** | [N]건 |
| **총 Trade** | [N]건 |
| **활성 심볼** | [N]개 |

### 2.2. Top20 Results

| 메트릭 | 값 |
|--------|-----|
| **실행 시간** | [N]분 |
| **평균 Loop Latency** | [N]ms |
| **P95 Loop Latency** | [N]ms |
| **평균 CPU** | [N]% |
| **평균 메모리** | [N]MB |
| **에러 수** | [N]건 |
| **총 Trade** | [N]건 |
| **활성 심볼** | [N]개 |

### 2.3. Top50 Results

| 메트릭 | 값 |
|--------|-----|
| **실행 시간** | [N]분 |
| **평균 Loop Latency** | [N]ms |
| **P95 Loop Latency** | [N]ms |
| **평균 CPU** | [N]% |
| **평균 메모리** | [N]MB |
| **에러 수** | [N]건 |
| **총 Trade** | [N]건 |
| **활성 심볼** | [N]개 |

### 2.4. Top100 Results

| 메트릭 | 값 |
|--------|-----|
| **실행 시간** | [N]분 |
| **평균 Loop Latency** | [N]ms |
| **P95 Loop Latency** | [N]ms |
| **평균 CPU** | [N]% |
| **평균 메모리** | [N]MB |
| **에러 수** | [N]건 |
| **총 Trade** | [N]건 |
| **활성 심볼** | [N]개 |

---

## 3. 성능 비교 분석

### 3.1. Loop Latency 추세

| Top-N | 평균 Latency (ms) | 증가율 |
|-------|-------------------|--------|
| Top10 | [N] | baseline |
| Top20 | [N] | +[N]% |
| Top50 | [N] | +[N]% |
| Top100 | [N] | +[N]% |

**분석**:
- [Latency 증가 패턴 설명]
- [병목 지점 식별]

### 3.2. CPU 사용률 추세

| Top-N | 평균 CPU (%) | 증가율 |
|-------|--------------|--------|
| Top10 | [N] | baseline |
| Top20 | [N] | +[N]% |
| Top50 | [N] | +[N]% |
| Top100 | [N] | +[N]% |

**분석**:
- [CPU 사용 패턴 설명]

### 3.3. 메모리 사용량 추세

| Top-N | 평균 메모리 (MB) | 증가율 |
|-------|------------------|--------|
| Top10 | [N] | baseline |
| Top20 | [N] | +[N]% |
| Top50 | [N] | +[N]% |
| Top100 | [N] | +[N]% |

**분석**:
- [메모리 사용 패턴 설명]

### 3.4. Trade Activity 추세

| Top-N | 총 Trade | 활성 심볼 | Trade/심볼 |
|-------|----------|-----------|------------|
| Top10 | [N] | [N] | [N] |
| Top20 | [N] | [N] | [N] |
| Top50 | [N] | [N] | [N] |
| Top100 | [N] | [N] | [N] |

**분석**:
- [Trade activity 패턴 설명]

---

## 4. Hot Path 분석

### 4.1. Top 10 느린 Indicator

| Rank | Symbol | Indicator | 평균 (ms) | P95 (ms) |
|------|--------|-----------|-----------|----------|
| 1 | [SYMBOL] | [INDICATOR] | [N] | [N] |
| 2 | [SYMBOL] | [INDICATOR] | [N] | [N] |
| 3 | [SYMBOL] | [INDICATOR] | [N] | [N] |
| ... | ... | ... | ... | ... |

**개선 제안**:
1. [제안 1]
2. [제안 2]

### 4.2. Indicator Cache 효과

| 메트릭 | 값 |
|--------|-----|
| **Cache 활성화 여부** | [Yes/No] |
| **Cache Hit 비율** | [N]% |
| **Cache Miss 비율** | [N]% |
| **평균 Latency 감소** | [N]% |

---

## 5. DB 메트릭

### 5.1. Trade 통계

```sql
SELECT symbol, COUNT(*) as trade_count
FROM trading.trades
WHERE ts_open >= '[START_TIME]' AND ts_open <= '[END_TIME]'
GROUP BY symbol
ORDER BY trade_count DESC
LIMIT 10;
```

| Symbol | Trade Count |
|--------|-------------|
| [SYMBOL] | [N] |
| ... | ... |

### 5.2. Per-Symbol PnL

```sql
SELECT symbol, SUM(pnl_usdt) as total_pnl
FROM trading.trades
WHERE ts_open >= '[START_TIME]' AND ts_open <= '[END_TIME]' AND status = 'CLOSED'
GROUP BY symbol
ORDER BY total_pnl DESC;
```

| Symbol | Total PnL (USDT) |
|--------|------------------|
| [SYMBOL] | [N] |
| ... | ... |

---

## 6. 로그 분석

### 6.1. 에러 요약

```bash
# CRITICAL 오류
grep "CRITICAL" logs/application.log | wc -l
# [N]건

# ERROR 오류
grep "ERROR" logs/application.log | wc -l
# [N]건
```

**주요 에러**:
1. [에러 1 설명]
2. [에러 2 설명]

### 6.2. 로그 샘플

```
[샘플 로그 1]
[샘플 로그 2]
```

---

## 7. Known Issues & Limitations

### 7.1. 발견된 이슈

1. **[이슈 1 제목]**
   - **증상**: [설명]
   - **재현 빈도**: [N]%
   - **영향도**: High/Medium/Low
   - **해결 방안**: [제안]

2. **[이슈 2 제목]**
   - **증상**: [설명]
   - **재현 빈도**: [N]%
   - **영향도**: High/Medium/Low
   - **해결 방안**: [제안]

### 7.2. 제한사항

1. **Sequential Processing**: 심볼 수 증가 시 latency 선형 증가
   - **해결**: PHASE27에서 coroutine 도입

2. **Indicator Cache 정확도**: 최근 N개만 사용하므로 극히 드물게 오차 가능
   - **현재 상태**: 실전에서 무시 가능한 수준

---

## 8. Next Steps

### 8.1. 즉시 조치 필요

- [ ] [조치 항목 1]
- [ ] [조치 항목 2]

### 8.2. PHASE27 계획

- [ ] Coroutine 기반 비동기 처리 도입
- [ ] Top200+ 지원
- [ ] 실시간 모니터링 대시보드

### 8.3. 성능 개선 Backlog

1. [개선 항목 1]
2. [개선 항목 2]

---

## 9. 결론

### 9.1. 최종 판정

**PHASE26-3 Acceptance**: ✅ PASS / ❌ FAIL

**판정 근거**:
- [근거 1]
- [근거 2]

### 9.2. 요약

[전체 테스트 결과 요약 및 결론]

---

**리포트 생성 일시**: [YYYY-MM-DD HH:MM:SS]  
**생성 도구**: `scripts/infra/phase26_3_run_top100_paper.py`  
**JSON 요약**: `docs/PHASE26/phase26_3_top100_performance_summary.json`
