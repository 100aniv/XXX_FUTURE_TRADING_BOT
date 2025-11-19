# PHASE18-3 설계 문서: Graceful Shutdown & Signal Handling

**작성일**: 2025-11-19  
**작업 ID**: PHASE18-3  
**목표**: OS 시그널 수신 시 리소스를 안전하게 정리하고 예측 가능한 방식으로 종료  
**진입 조건**: PHASE18-2 완료 (run_id 네임스페이스)

---

## 1. 목표 정의

### 1.1 왜 Graceful Shutdown이 필요한가?

**실서비스 운영 관점**:
- **외부 종료 시나리오**: 
  - PHASE17 12H 테스트 중 10H에 세션 끊김으로 비정상 종료
  - Cloud 환경에서 스케일 다운/재시작 시 SIGTERM 수신
  - 사용자가 CTRL+C로 중단
  - 시스템 재부팅/서비스 업데이트

**하드 킬의 문제점**:
- 진행 중인 거래 상태가 DB에 저장되지 않음
- 오픈 포지션 정보 손실 가능
- WebSocket 연결 정리 안 됨 → 서버 측 세션 잔류
- Redis 상태와 실제 상태 불일치
- 로그에 종료 원인 기록 안 됨 → 디버깅 곤란

**Graceful Shutdown의 장점**:
- ✅ 모든 리소스(WebSocket, DB, Redis) 명시적 정리
- ✅ 최종 상태를 로그/DB에 안전하게 저장
- ✅ 종료 원인 명확히 기록
- ✅ 재시작 시 일관된 상태에서 시작 가능
- ✅ 운영 환경에서 신뢰성 향상

---

## 2. 아키텍처 개요

### 2.1 Shutdown 요청 흐름

```
┌─────────────────────────────────────────────────────────────┐
│ OS Signal (SIGINT/SIGTERM)                                  │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Signal Handler (run_paper.py / run_backtest.py)            │
│ - signal.signal(SIGINT, handler) 등록                       │
│ - shutdown_event.set() 호출                                 │
│ - 로그: "Shutdown signal received (SIGINT)"                 │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Shutdown Context (common/runtime_context.py)               │
│ - threading.Event() 기반 shutdown_event                     │
│ - Config에 주입: config['shutdown_event']                   │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Engine Main Loop (execution/engine.py)                      │
│ - 매 iteration마다 shutdown_event.is_set() 체크             │
│ - True면:                                                   │
│   1) 새 진입 중단                                           │
│   2) 현재 작업 마무리                                       │
│   3) break로 루프 탈출                                      │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Resource Cleanup (run_paper.py / engine.py)                │
│ - WebSocket: feed.stop()                                   │
│ - Redis: redis_client.close()                              │
│ - DB: 커넥션 풀 정리                                        │
│ - 로그: "Shutdown complete"                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 OS Signal vs. 내부 Shutdown Flag

**OS Signal (SIGINT/SIGTERM)**:
- 외부에서 프로세스 종료 요청
- Signal Handler가 포착
- `shutdown_event.set()` 호출로 내부 플래그 세트

**내부 Shutdown Flag (`shutdown_event`)**:
- `threading.Event()` 객체
- Engine/Collector 등이 주기적으로 체크
- 모든 컴포넌트가 동일한 플래그 공유 (config 통해 전파)

**Windows 제약**:
- SIGTERM 지원 제한적
- SIGINT (CTRL+C) 중심으로 구현
- 코드 구조는 SIGTERM 확장 가능하도록 설계

---

## 3. 구현 전략

### 3.1 공용 Shutdown Context

**파일**: `common/runtime_context.py` (신규)

```python
import threading
from typing import Optional

class RuntimeContext:
    """
    실행 시점 공용 컨텍스트
    
    - shutdown_event: 종료 요청 플래그
    - run_id: 실행 인스턴스 ID
    - env: 실행 환경 (backtest, paper, live)
    """
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.run_id: Optional[str] = None
        self.env: Optional[str] = None
    
    def request_shutdown(self, reason: str = "Unknown"):
        """종료 요청"""
        self.shutdown_event.set()
        return reason
    
    def is_shutdown_requested(self) -> bool:
        """종료 요청 여부 확인"""
        return self.shutdown_event.is_set()
```

**사용 방식**:
- Runner(run_paper.py)에서 생성
- Config에 주입: `config['runtime_context'] = runtime_ctx`
- Engine/Collector에서 `config['runtime_context'].is_shutdown_requested()` 체크

### 3.2 run_paper.py / run_backtest.py Signal Handling

**변경 위치**: `run_paper.py` 및 `run_backtest.py`

**구현 내용**:
```python
import signal
from common.runtime_context import RuntimeContext

# Runtime context 생성
runtime_ctx = RuntimeContext()
runtime_ctx.run_id = run_id
runtime_ctx.env = 'paper'  # or 'backtest'

# Config에 주입
cfg['runtime_context'] = runtime_ctx

# Signal Handler 등록
def signal_handler(signum, frame):
    sig_name = 'SIGINT' if signum == signal.SIGINT else f'Signal {signum}'
    logger.info(f"🛑 Shutdown signal received: {sig_name}")
    reason = runtime_ctx.request_shutdown(reason=sig_name)
    logger.info(f"✅ Shutdown requested: {reason}")

signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

# Engine 실행 (try/finally로 정리 보장)
try:
    engine.run(feed, broker, clock, strategies, ensemble_module, cfg)
except KeyboardInterrupt:
    logger.info("⏹️  사용자 중단 (KeyboardInterrupt)")
    runtime_ctx.request_shutdown(reason="KeyboardInterrupt")
finally:
    # 리소스 정리
    logger.info("🧹 리소스 정리 시작...")
    if hasattr(feed, 'stop'):
        feed.stop()
        logger.info("  ✅ Feed 중지 완료")
    logger.info("✅ Shutdown complete")
```

### 3.3 execution/engine.py Shutdown 체크

**변경 위치**: `execution/engine.py` 메인 루프 (line 504~)

**구현 내용**:
```python
# Runtime context 추출
runtime_ctx = config.get('runtime_context', None)

# 메인 루프
for candle in feed.stream():
    # ⭐ Shutdown 체크 (최우선)
    if runtime_ctx and runtime_ctx.is_shutdown_requested():
        logger.info("🛑 Shutdown requested - 메인 루프 종료")
        break
    
    # ⭐ Wall-clock Duration 체크
    if duration_mode == 'wall_clock':
        elapsed_wall = time.time() - start_wall_time
        if elapsed_wall >= duration_seconds:
            logger.info(f"✅ [WALL-CLOCK] Duration 도달")
            break
    
    # ... 기존 로직 ...
```

**최소 변경 원칙**:
- 기존 duration 체크 유지
- Shutdown 체크를 **추가 조건**으로만 삽입
- 엔진 구조 변경 최소화

### 3.4 collectors/websocket_collector.py Shutdown 체크

**변경 위치**: `collectors/websocket_collector.py`

**기존 코드**:
```python
def stop(self):
    """데이터 수집 중지"""
    self.running = False
    if self.ws:
        self.ws.close()
    if hasattr(self, 'redis_client'):
        self.redis_client.close()
    logger.info("⏹️  Collector 중지")
```

**개선 방향**:
- Runtime context 참조 추가 (선택적)
- WebSocket thread join 명시
- 정리 순서 명확화:
  1. `self.running = False`
  2. WebSocket close
  3. Thread join (타임아웃 포함)
  4. Redis close

**구현 예시**:
```python
def stop(self, timeout=5.0):
    """데이터 수집 중지"""
    logger.info("🛑 WebSocketCollector 중지 시작...")
    self.running = False
    
    # WebSocket 종료
    if self.ws:
        try:
            self.ws.close()
            logger.info("  ✅ WebSocket 연결 종료")
        except Exception as e:
            logger.warning(f"  ⚠️ WebSocket 종료 실패: {e}")
    
    # Thread join (타임아웃)
    if hasattr(self, '_ws_thread') and self._ws_thread.is_alive():
        self._ws_thread.join(timeout=timeout)
        if self._ws_thread.is_alive():
            logger.warning(f"  ⚠️ WebSocket thread 타임아웃 ({timeout}s)")
        else:
            logger.info("  ✅ WebSocket thread 종료")
    
    # Redis 종료
    if hasattr(self, 'redis_client'):
        try:
            self.redis_client.close()
            logger.info("  ✅ Redis 연결 종료")
        except Exception as e:
            logger.warning(f"  ⚠️ Redis 종료 실패: {e}")
    
    logger.info("✅ WebSocketCollector 중지 완료")
```

---

## 4. 리소스 정리 정책

### 4.1 정리 순서

**우선순위**:
1. **새 작업 중단**: 신호 생성/진입 차단
2. **현재 작업 마무리**: 진행 중인 캔들 처리 완료
3. **WebSocket 종료**: `feed.stop()` 호출
4. **Thread 정리**: Worker thread join (타임아웃 5초)
5. **Redis 종료**: `redis_client.close()`
6. **DB 커넥션**: Connection pool 정리 (자동 또는 명시적)
7. **로그 마무리**: "Shutdown complete" 메시지

### 4.2 리소스별 정리 방법

| 리소스 | 정리 방법 | 위치 | 필수 여부 |
|--------|----------|------|-----------|
| **WebSocket** | `feed.stop()` | run_paper.py finally | ✅ 필수 |
| **Redis** | `redis_client.close()` | WebSocketCollector.stop() | ✅ 필수 |
| **DB Connection** | Context manager 자동 정리 | engine.py (자동) | ✅ 필수 |
| **Thread** | `thread.join(timeout=5)` | WebSocketCollector.stop() | ⚠️ 권장 |
| **로그** | "Shutdown complete" | run_paper.py finally | ✅ 필수 |

### 4.3 Graceful vs. 강제 종료

**정상 종료 (Graceful)**:
- Signal 수신 → shutdown_event 세트
- 메인 루프 자연스럽게 탈출
- 리소스 정리 수행
- 종료 로그 남김

**강제 종료 (Hard Kill)**:
- 두 번째 SIGINT/SIGTERM
- 타임아웃 초과 (정리 작업이 너무 오래 걸림)
- 즉시 종료 (리소스 정리 스킵)

**구현**:
```python
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    if shutdown_requested:
        logger.warning("🚨 강제 종료 (두 번째 시그널)")
        sys.exit(1)
    
    logger.info("🛑 Graceful shutdown 시작...")
    shutdown_requested = True
    runtime_ctx.request_shutdown(reason="SIGINT")
```

---

## 5. 테스트 전략

### 5.1 Unit 테스트

**파일**: `tests/test_phase18_3_graceful_shutdown.py`

**시나리오**:
1. **RuntimeContext 동작 테스트**
   - `shutdown_event` 생성 및 set/is_set 동작 확인
   - `request_shutdown()` 호출 시 플래그 세트 확인

2. **Engine Shutdown 플래그 체크 테스트**
   - Fake feed/broker로 축소 엔진 구성
   - `runtime_ctx.request_shutdown()` 호출
   - 메인 루프가 break로 탈출하는지 확인

3. **리소스 정리 테스트**
   - WebSocketCollector.stop() 호출
   - running=False, ws.close(), redis.close() 순서 확인
   - Thread join 타임아웃 동작 확인

### 5.2 Integration 테스트 (subprocess)

**시나리오**:
```python
import subprocess
import signal
import time

def test_real_paper_graceful_shutdown():
    """실제 run_paper.py 프로세스 SIGINT 테스트"""
    proc = subprocess.Popen(
        ["python", "scripts/run_paper.py", 
         "--clean-state", "--duration-hours", "0.1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 30초 실행 후 SIGINT 전송
    time.sleep(30)
    proc.send_signal(signal.SIGINT)
    
    # 종료 대기 (타임아웃 10초)
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        pytest.fail("Graceful shutdown 타임아웃 (10초 초과)")
    
    # 로그 검증
    assert "Shutdown signal received" in stdout
    assert "Shutdown complete" in stdout
    assert proc.returncode == 0  # 정상 종료
```

### 5.3 REAL PAPER Smoke Test

**목표**: 실제 환경에서 Graceful Shutdown 동작 확인

**실행**:
```bash
# 10분 실행 후 자동 종료 (내부 트리거)
python scripts/run_paper.py \
  --clean-state \
  --duration-hours 0.167 \
  --duration-mode wall_clock
```

**검증 항목**:
1. **로그 확인**:
   - "Shutdown signal received" (또는 duration 도달)
   - "리소스 정리 시작..."
   - "Feed 중지 완료"
   - "Shutdown complete"

2. **Redis 키 확인**:
   - run_id 관련 키가 더 이상 증가하지 않음
   - 기존 키는 유지 (정리 안 함)

3. **프로세스 확인**:
   - Python 프로세스 정상 종료
   - 좀비 프로세스 없음
   - WebSocket 백그라운드 thread 없음

4. **에러 로그**:
   - ERROR/CRITICAL 레벨 로그 없음
   - 정상적인 종료 시퀀스만 존재

---

## 6. Acceptance Criteria

### 6.1 필수 조건

- [ ] `common/runtime_context.py` 생성 완료
- [ ] `run_paper.py` Signal Handler 구현
- [ ] `run_backtest.py` Signal Handler 구현
- [ ] `execution/engine.py` Shutdown 체크 추가
- [ ] `collectors/websocket_collector.py` stop() 개선
- [ ] 단위 테스트 작성 및 PASS
- [ ] Integration 테스트 작성 및 PASS
- [ ] REAL PAPER smoke test 성공 (10~15분)
- [ ] 완료 리포트 작성

### 6.2 검증 조건

**로그 검증**:
- ✅ "Shutdown signal received" 또는 "Duration 도달"
- ✅ "리소스 정리 시작"
- ✅ "Feed 중지 완료"
- ✅ "Shutdown complete"
- ✅ ERROR/CRITICAL 로그 0건

**프로세스 검증**:
- ✅ 정상 종료 코드 (exit code 0)
- ✅ 좀비 프로세스 없음
- ✅ 백그라운드 thread 없음

**Redis 검증**:
- ✅ Shutdown 후 run_id 키 증가 중단
- ✅ 기존 키 유지 (삭제 안 됨)

### 6.3 PHASE18-3 판정 기준

**PASS 조건**:
- 모든 Acceptance Criteria 만족
- 단위/통합 테스트 100% PASS
- REAL PAPER smoke test ERROR 0건
- 기존 기능 회귀 없음

**FAIL 조건**:
- Signal Handler 미작동
- 리소스 정리 실패 (WebSocket/Redis 잔류)
- ERROR/CRITICAL 로그 발생
- 좀비 프로세스 발생

---

## 7. 구현 범위 제한

### 7.1 이번 PHASE에서 다루는 것

✅ OS Signal Handling (SIGINT/SIGTERM)  
✅ Runtime Context 공용 유틸  
✅ Engine/Collector Shutdown 플래그 체크  
✅ 리소스 정리 (WebSocket, Redis, Thread)  
✅ 종료 로그 표준화

### 7.2 이번 PHASE에서 다루지 않는 것

❌ State Snapshot 저장/복구 (PHASE19+ 고려)  
❌ Graceful Restart (프로세스 관리자 영역)  
❌ Health Check Endpoint (PHASE18-4 모니터링)  
❌ K8s Readiness/Liveness Probe (PHASE18-D58)  
❌ 포지션 강제 청산 로직 (기존 Risk Manager 유지)

---

## 8. 회귀 보호

### 8.1 DO-NOT-TOUCH 레이어

**보존 대상**:
- `execution/portfolio_manager.py`: 변경 없음 ✅
- `execution/position_sizer.py`: 변경 없음 ✅
- `execution/risk_manager.py`: 변경 없음 ✅
- `execution/position_tracker.py`: 변경 없음 ✅

**변경 대상**:
- `execution/engine.py`: 메인 루프에 shutdown 체크 **추가** (기존 로직 유지)
- `collectors/websocket_collector.py`: stop() 메서드 **개선** (기존 기능 유지)

### 8.2 기존 기능 영향도

**영향 없음**:
- Budget/Portfolio 시스템 ✅
- Multi-position Scaling ✅
- Risk Manager ✅
- Signal Generation ✅
- Duration 체크 (wall_clock/market_time) ✅

**영향 있음 (의도된 개선)**:
- 종료 시퀀스 → Graceful Shutdown 추가
- 리소스 정리 → 명시적 정리 강화

---

## 9. 향후 확장 (PHASE19+)

### 9.1 State Snapshot (선택적)

**개념**:
- Graceful Shutdown 시 현재 상태를 JSON/DB에 저장
- 재시작 시 스냅샷 복구 → 연속성 유지

**저장 대상**:
- 오픈 포지션 목록
- Portfolio Equity
- 마지막 처리 캔들 timestamp

**파일**: `shutdown_snapshot_{run_id}.json`

### 9.2 Graceful Restart

**개념**:
- 프로세스 관리자(systemd, supervisord, K8s)가 자동 재시작
- Snapshot 복구로 상태 연속성 유지

**구현 위치**:
- PHASE19 이후 (프로세스 감시 프레임워크와 함께)

### 9.3 Health Check Endpoint

**개념**:
- HTTP Endpoint (`/health`, `/ready`)
- K8s Liveness/Readiness Probe 지원

**구현 위치**:
- PHASE18-4 (모니터링 프레임워크)

---

## 10. 결론

### 10.1 설계 요약

✅ **OS Signal 기반 Graceful Shutdown 인프라 구축**  
✅ **Runtime Context로 shutdown 상태 전파**  
✅ **Engine/Collector에 shutdown 체크 추가 (최소 변경)**  
✅ **리소스 정리 순서 명확화 (WebSocket → Thread → Redis → DB)**  
✅ **테스트 전략 명확 (Unit + Integration + REAL PAPER)**

### 10.2 예상 산출물

| 구분 | 파일 | 상태 |
|------|------|------|
| **신규 유틸** | `common/runtime_context.py` | 생성 예정 |
| **수정 Runner** | `scripts/run_paper.py` | Signal Handler 추가 |
| **수정 Runner** | `scripts/run_backtest.py` | Signal Handler 추가 |
| **수정 Engine** | `execution/engine.py` | Shutdown 체크 추가 |
| **수정 Collector** | `collectors/websocket_collector.py` | stop() 개선 |
| **테스트** | `tests/test_phase18_3_graceful_shutdown.py` | 신규 |
| **문서** | `docs/PHASE18/PHASE18-3_COMPLETE_REPORT.md` | 신규 |

### 10.3 다음 단계

**PHASE18-3 완료 후**:
- PHASE18-4: 모니터링 프레임워크 (선택적)
- PHASE19: 앙상블 프레임워크 복구

---

**문서 작성**: 2025-11-19  
**작성자**: Cascade AI (Claude 4.5 Thinking)  
**승인**: PHASE18-3 설계 문서 초안
