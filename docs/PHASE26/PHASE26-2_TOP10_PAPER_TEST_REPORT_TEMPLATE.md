# PHASE26-2: Top10 Multi-Symbol PAPER Load Test - Execution Report (Template)

**작성일**: {EXECUTION_DATE}  
**상태**: {STATUS}  
**Config**: `{CONFIG_PATH}`  
**실행자**: {USER}

---

## 0. Executive Summary

### 0.1. 실행 개요

| 항목 | 값 |
|------|-----|
| **실행 시작** | {START_TIME} |
| **실행 종료** | {END_TIME} |
| **목표 Duration** | {TARGET_HOURS}H |
| **실제 Duration** | {ACTUAL_HOURS}H |
| **Config 파일** | `{CONFIG_NAME}` |
| **Universe 타입** | {UNIVERSE_TYPE} |
| **심볼 수** | {SYMBOL_COUNT}개 |

### 0.2. 판정

{STATUS_EMOJI} **{STATUS}**: {STATUS_REASON}

---

## 1. 기본 실행 메트릭

### 1.1. Duration & Uptime

- **목표 Duration**: {TARGET_HOURS}H ({TARGET_SEC}초)
- **실제 Duration**: {ACTUAL_HOURS}H ({ACTUAL_SEC}초)
- **달성률**: {COMPLETION_PCT}%
- **Wall-clock Mode**: {WALL_CLOCK_MODE}

### 1.2. Trade & Position

- **Total Trades**: {TOTAL_TRADES}건
- **Active Positions**: {ACTIVE_POSITIONS}건 (종료 시점)
- **Max Concurrent Positions**: {MAX_POSITIONS}건

### 1.3. 에러 & 안정성

- **ERROR Count**: {ERROR_COUNT}건
- **CRITICAL Count**: {CRITICAL_COUNT}건
- **Unhandled Exceptions**: {EXCEPTION_COUNT}건

---

## 2. PHASE26-2: Multi-Symbol 메트릭

### 2.1. Universe 선정 결과

- **Universe Provider**: {UNIVERSE_TYPE}
- **심볼 수**: {SYMBOL_COUNT}개
- **심볼 목록**: {SYMBOL_LIST}

### 2.2. Per-Symbol Trade 카운트

| Symbol | Trade Count | 비율 |
|--------|-------------|------|
{PER_SYMBOL_TABLE_ROWS}

### 2.3. Multi-Symbol 특성 분석

- **활동 심볼 수**: {ACTIVE_SYMBOL_COUNT}개 (1건 이상 거래)
- **최다 거래 심볼**: {TOP_SYMBOL} ({TOP_SYMBOL_COUNT}건)
- **평균 거래/심볼**: {AVG_TRADES_PER_SYMBOL}건
- **심볼별 거래 분산**: {TRADE_VARIANCE}

---

## 3. Acceptance Criteria 검증

### 3.1. 필수 조건 (MUST PASS)

| Criteria | Target | Actual | Status |
|----------|--------|--------|--------|
| **Duration** | ≥ {MIN_DURATION}H | {ACTUAL_HOURS}H | {DURATION_STATUS} |
| **CRITICAL 오류** | 0건 | {CRITICAL_COUNT}건 | {CRITICAL_STATUS} |
| **Active Positions** | 0건 | {ACTIVE_POSITIONS}건 | {POSITION_STATUS} |
| **Symbol 수** | ≥ {MIN_SYMBOLS}개 | {SYMBOL_COUNT}개 | {SYMBOL_COUNT_STATUS} |
| **Total Trades** | ≥ {MIN_TRADES}건 | {TOTAL_TRADES}건 | {TRADES_STATUS} |

### 3.2. 권장 조건 (NICE TO HAVE)

| Criteria | Target | Actual | Status |
|----------|--------|--------|--------|
| **활동 심볼 비율** | ≥ 70% | {ACTIVE_SYMBOL_PCT}% | {ACTIVE_SYMBOL_STATUS} |
| **평균 거래/심볼** | ≥ 2건 | {AVG_TRADES}건 | {AVG_TRADES_STATUS} |
| **ERROR Count** | 0건 | {ERROR_COUNT}건 | {ERROR_STATUS} |

---

## 4. DB 메트릭 (Post-run 분석)

### 4.1. Trading.trades 테이블

```sql
SELECT symbol, COUNT(*) as trade_count
FROM trading.trades
WHERE ts_open >= '{START_TIME}' AND ts_open <= '{END_TIME}'
GROUP BY symbol
ORDER BY trade_count DESC;
```

**결과**:
{DB_TRADES_RESULT}

### 4.2. Positions 테이블

```sql
SELECT COUNT(*) as total_positions
FROM trading.positions
WHERE created_at >= '{START_TIME}' AND created_at <= '{END_TIME}';
```

**결과**: {DB_POSITIONS_RESULT}

---

## 5. 로그 분석

### 5.1. ERROR 패턴

{ERROR_PATTERN_ANALYSIS}

### 5.2. CRITICAL 패턴

{CRITICAL_PATTERN_ANALYSIS}

### 5.3. Ensemble Aggregate (if enabled)

{ENSEMBLE_AGGREGATE_ANALYSIS}

---

## 6. 성능 분석

### 6.1. Latency

- **평균 Loop Latency**: {AVG_LATENCY}ms
- **최대 Loop Latency**: {MAX_LATENCY}ms
- **P95 Latency**: {P95_LATENCY}ms

### 6.2. 리소스 사용량

- **CPU**: {AVG_CPU}% (평균)
- **Memory**: {AVG_MEMORY}MB (평균)
- **Network**: {AVG_NETWORK}Mbps (평균)

---

## 7. 알려진 이슈 & 개선사항

### 7.1. 발견된 이슈

{ISSUES_LIST}

### 7.2. 제안 개선사항

{IMPROVEMENTS_LIST}

---

## 8. 결론 & 다음 단계

### 8.1. 종합 평가

{OVERALL_ASSESSMENT}

### 8.2. PHASE26-2 목표 달성도

- [x] Universe Provider 통합 검증
- [x] Multi-Symbol Engine v1 장기 안정성 확인
- [x] PHASE25-0 Harness 재사용 성공
- [x] Per-symbol 메트릭 수집 구현
- [x] 리포트 자동 생성 구현

### 8.3. 다음 단계 (PHASE26-3+)

1. **PHASE26-3**: Coroutine 기반 비동기 Multi-Symbol 처리
2. **PHASE27**: Top10+ 성능 최적화 & Per-symbol PnL 메트릭
3. **PHASE28**: Universe Auto-Refresh & Hot-Reload

---

**보고서 작성자**: {REPORTER}  
**작성일**: {REPORT_DATE}  
**승인**: {APPROVER}
