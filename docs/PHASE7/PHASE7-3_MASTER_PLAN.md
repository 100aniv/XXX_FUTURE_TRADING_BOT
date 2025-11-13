# PHASE7-3 마스터 플랜: 운영 안정성 강화 (Live 모드 준비)

**작성일**: 2025-11-11  
**최종 업데이트**: 2025-11-13  
**문서 역할**: Live 전환 전 운영 안정성 표준  
**목적**: Graceful Shutdown, State Recovery, Healthcheck, Monitoring  
**현행 코드(b84c03c)**: 상태 DB/TP 거래소 등록 미구현  
**상태**: ⚠️ PHASE7-2 미완으로 7-3 항목 모두 TO-BE (미구현)

## 📌 Executive Summary (TL;DR)

- **역할**: Live 운영 필수 안전장치. 종료/재시작/복원/헬스/모니터링 표준화.
- **현행**: b84c03c 복원 완료. PHASE7-2 미완으로 7-3 보류 중.
- **핵심**: ① Graceful Shutdown ② State Recovery ③ Docker Healthcheck ④ Monitoring Dashboard.
- **예상 효과**: 컨테이너 재시작 안전, 포지션 유실 0건, Live 전환 준비 완료.

## 🔎 Quick Nav

- [현재 상태](#-현재-상태)
- [목표](#-목표)
- [범위](#-범위)
- [수용 기준](#-수용-기준)
- [참조 문서](#-참조-문서)

## 📊 Standard Snapshot (Paper)

- **최근 2시간**: closed=818, win_rate=38.3%, avg_pnl=-0.24%, >8% 손실=29
- **최근 24시간**: closed=1,550, win_rate=35.8%, avg_pnl=-0.38%, >8% 손실=64
- 출처: SMOKE_TEST_MONITOR.md (2025-11-13)

---

## ⚠️ 현재 상태

**프로젝트**: ⏸️ 보류 (PHASE7-2 미완)  
**현행 코드**: b84c03c (안정 버전)  
**미구현 항목**: Graceful Shutdown, State Recovery, TP 거래소 등록  
**선행 조건**: PHASE7-2 완료 후 착수

---

## 🎯 목표

| 항목 | 목표 | 필요성 |
|------|------|--------|
| **Graceful Shutdown** | 종료 전 모든 포지션 정리 | 강제 종료 시 포지션 방치 방지 |
| **State Recovery** | 재시작 시 포지션/주문 동기화 | 컨테이너 재시작 후 상태 복원 |
| **Healthcheck** | DB/Redis/API 연결 검증 | 장애 자동 감지 및 복구 |
| **Monitoring** | Grafana 대시보드 | 실시간 시스템 상태 모니터링 |

---

## 📋 범위

### 1. Graceful Shutdown + --reset 옵션 (1.5일)

**문제**: `sys.exit(1)` 강제 종료 → OPEN 포지션 방치  
**해결**:
- Signal handler (SIGTERM, SIGINT)
- 종료 시 OPEN 포지션 시장가 청산
- Binance SL/TP 주문 취소 (Live)
- 상태 저장 (DB + Redis)

**--reset 옵션** (Paper만):
- DB OPEN 포지션 강제 청산
- equity → config.initial_capital
- 새 run_id 생성
- Redis 상태 초기화

**파일**: `main.py`, `execution/engine.py`, `execution/adapters/brokers.py`

### 2. TP 거래소 등록 (1일) 🚨 Live 안전장치

**문제**: TP는 메모리만 → 프로그램 종료 시 미작동  
**해결**: TP1을 Binance에 TAKE_PROFIT_MARKET 주문으로 등록

```python
# LiveBroker.create_tp_order()
tp_order = client.futures_create_order(
    symbol=symbol,
    side=close_side,
    type='TAKE_PROFIT_MARKET',
    stopPrice=tp_price,
    quantity=qty * 0.6,  # TP1 60%
    reduceOnly=True
)
```

**파일**: `execution/adapters/brokers.py`, `execution/engine.py`

### 3. State Recovery (1일)

**Paper 모드**:
- DB에서 status='OPEN' AND mode='paper' 조회
- active_positions 복원
- equity 계산

**Live 모드**:
- Binance API: GET /fapi/v2/positionRisk
- 거래소 포지션과 DB 동기화

**파일**: `execution/engine.py`, `common/database.py`

### 4. Docker Healthcheck (0.5일)

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "python", "scripts/healthcheck.py"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

**체크 항목**:
- DB 연결
- Redis 연결
- Binance API 연결 (Live)
- 메모리 사용률 < 80%

**파일**: `scripts/healthcheck.py`, `docker-compose.yml`

### 5. Monitoring Dashboard (1일)

**Grafana + Prometheus**:
- 거래 건수, 승률, PnL
- 포지션 수, 노출도
- 시스템 리소스 (CPU, 메모리)

**파일**: `docker-compose.yml`, `monitoring/grafana/dashboard.json`

---

## ✅ 수용 기준

**PHASE7-4 진입 전 필수**:
- Graceful Shutdown: 종료 시 OPEN 포지션 0건
- State Recovery: 재시작 직후 포지션 일치율 100%
- Healthcheck: unhealthy 자동 복구 성공률 100%
- 무결성: 중복 진입 0, 양방향 동시 0, 미결 주문 유실 0

---

## 📋 체크리스트

**구현 전**:
- [ ] SYSTEM_OPERATIONS_ANALYSIS.md 운영 정책 재검토
- [ ] Binance API 주문 취소/등록 테스트
- [ ] .windsurfrules 준수: 단계별 3파일 이하

**구현 중**:
- [ ] Signal handler (main.py)
- [ ] Shutdown 메서드 (engine.py)
- [ ] TP 거래소 등록 (LiveBroker)
- [ ] State Recovery (engine.py, database.py)
- [ ] Healthcheck 스크립트

**검증**:
- [ ] Paper --reset 테스트
- [ ] Live TP 주문 등록/체결 테스트
- [ ] 재시작 후 포지션 복원 테스트
- [ ] Healthcheck 장애 복구 테스트

---

## 🔗 참조 문서

- **SYSTEM_OPERATIONS_ANALYSIS.md** - 운영 안정성 표준 (상세)
- **PHASE7_ALGORITHM_BEST.md** - TO-BE 전체 설계 (MASTER)
- **PHASE7-2_MASTER_PLAN.md** - 선행 단계
- **SMOKE_TEST_MONITOR.md** - 실시간 관측

---

## 📝 업데이트 로그

- **2025-11-13**: 문서 간소화 (887→300라인). MASTER 템플릿 적용. 핵심만 유지.
- **2025-11-12**: PHASE7-3 계획 수립
- **2025-11-11**: PHASE7-2 연기 항목 통합

---

**최종 업데이트**: 2025-11-13  
**다음 단계**: PHASE7-2 완료 후 착수
