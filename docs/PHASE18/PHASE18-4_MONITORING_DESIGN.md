# PHASE18-4 설계 문서: Monitoring Framework

**작성일**: 2025-11-19  
**작업 ID**: PHASE18-4  
**목표**: 프로덕션 운영 수준의 모니터링 인프라 구축  
**진입 조건**: PHASE18-3 완료 (Graceful Shutdown)

---

## 1. 목표 정의

### 1.1 왜 Monitoring Framework가 필요한가?

**프로덕션 운영 관점**:
- **장시간 실행 안정성**: PHASE17 12H 테스트에서 10H 세션 끊김 발생
- **문제 조기 감지**: WebSocket 연결 끊김, 지연, 메모리 누수 등
- **상태 가시성**: 시스템 각 컴포넌트의 정상 작동 여부 실시간 확인
- **알림 준비**: 이상 징후 발생 시 Telegram 등으로 즉시 알림

**현재 상황의 문제점**:
- ❌ 컴포넌트별 헬스 체크 없음
- ❌ WebSocket 연결 끊김 감지 지연
- ❌ 시스템 전반 상태 모니터링 부재
- ❌ 에러/지연 발생 시 수동 로그 확인 필요

**Monitoring Framework의 장점**:
- ✅ 실시간 헬스 체크 (heartbeat)
- ✅ 워치독(Watchdog) 자동 감지
- ✅ 레이턴시 모니터링
- ✅ 모듈별 상태 집계
- ✅ Telegram 알림 레이어 준비

---

## 2. 아키텍처 개요

### 2.1 모니터링 레이어

```
┌──────────────────────────────────────────────────────────────┐
│ RuntimeContext (PHASE18-3)                                   │
│ - shutdown_event                                             │
│ - monitor_registry (NEW)  ← 모니터 인스턴스 등록             │
└────────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Health      │  │ Watchdog    │  │ Latency     │
│ Checker     │  │ Monitor     │  │ Monitor     │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                ┌─────────────────┐
                │ Module Status   │
                │ Aggregator      │
                └─────────────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Heartbeat       │
                │ Monitor         │
                └─────────────────┘
```

### 2.2 모니터링 흐름

```
1. 시스템 시작
   └─> RuntimeContext 생성
       └─> MonitorRegistry 초기화
           └─> 각 모니터 인스턴스 등록

2. 실행 중 (Main Loop)
   ├─> Engine: heartbeat 업데이트
   ├─> WebSocketCollector: heartbeat + latency 업데이트
   ├─> Watchdog: 주기적으로 heartbeat 체크
   └─> HealthChecker: 모듈 상태 확인

3. 이상 감지 시
   └─> Watchdog: 경고 로그 + (향후) Telegram 알림
       └─> RuntimeContext: shutdown 요청 (선택적)

4. 시스템 종료
   └─> 모니터 stop()
       └─> 최종 상태 리포트
```

---

## 3. 컴포넌트 설계

### 3.1 MonitorRegistry (`common/monitoring/__init__.py`)

**역할**: 모든 모니터 인스턴스의 중앙 레지스트리

**인터페이스**:
```python
class MonitorRegistry:
    def __init__(self):
        self._monitors: Dict[str, BaseMonitor] = {}
    
    def register(self, name: str, monitor: BaseMonitor):
        """모니터 등록"""
    
    def unregister(self, name: str):
        """모니터 해제"""
    
    def get(self, name: str) -> Optional[BaseMonitor]:
        """모니터 가져오기"""
    
    def stop_all(self):
        """모든 모니터 중지"""
    
    def get_status(self) -> Dict[str, Any]:
        """전체 모니터 상태 집계"""
```

### 3.2 HeartbeatMonitor (`common/monitoring/heartbeat_monitor.py`)

**역할**: 컴포넌트별 heartbeat 타임스탬프 관리

**데이터 구조**:
```python
{
    'engine': 1700123456.789,  # 마지막 heartbeat timestamp
    'websocket': 1700123457.123,
    'feed': 1700123456.999,
}
```

**인터페이스**:
```python
class HeartbeatMonitor(BaseMonitor):
    def update(self, component: str):
        """Heartbeat 업데이트"""
        self._heartbeats[component] = time.time()
    
    def get_last_heartbeat(self, component: str) -> Optional[float]:
        """마지막 heartbeat 시간 반환"""
    
    def get_age(self, component: str) -> Optional[float]:
        """마지막 heartbeat 이후 경과 시간 (초)"""
    
    def is_alive(self, component: str, max_age: float = 60.0) -> bool:
        """컴포넌트 활성 여부 확인"""
```

### 3.3 Watchdog (`common/monitoring/watchdog.py`)

**역할**: 주기적으로 heartbeat를 체크하고 비정상 상태 감지

**동작**:
- 별도 thread에서 5초마다 실행
- HeartbeatMonitor의 모든 컴포넌트 체크
- 지정된 threshold 초과 시 경고 로그

**인터페이스**:
```python
class Watchdog(BaseMonitor):
    def __init__(self, heartbeat_monitor: HeartbeatMonitor, 
                 check_interval: float = 5.0,
                 max_age: float = 60.0):
        """
        Args:
            heartbeat_monitor: HeartbeatMonitor 인스턴스
            check_interval: 체크 주기 (초)
            max_age: heartbeat 최대 허용 시간 (초)
        """
    
    def start(self):
        """Watchdog thread 시작"""
    
    def stop(self):
        """Watchdog thread 중지"""
    
    def _check_loop(self):
        """체크 루프 (thread)"""
```

### 3.4 LatencyMonitor (`common/monitoring/latency_monitor.py`)

**역할**: 작업별 처리 시간 측정 및 지연 감지

**사용 예시**:
```python
latency_monitor = LatencyMonitor()

# Context manager 방식
with latency_monitor.measure('candle_processing'):
    process_candle(candle)

# 또는 수동 방식
start = latency_monitor.start_measure('signal_generation')
generate_signal(df)
latency_monitor.end_measure('signal_generation', start)

# 통계 조회
stats = latency_monitor.get_stats('candle_processing')
# {'count': 100, 'mean': 0.05, 'max': 0.12, 'p95': 0.08}
```

**인터페이스**:
```python
class LatencyMonitor(BaseMonitor):
    def measure(self, task_name: str) -> ContextManager:
        """Context manager로 측정"""
    
    def start_measure(self, task_name: str) -> float:
        """측정 시작 (timestamp 반환)"""
    
    def end_measure(self, task_name: str, start_time: float):
        """측정 종료"""
    
    def get_stats(self, task_name: str) -> Dict[str, float]:
        """통계 조회 (count, mean, max, p95, p99)"""
    
    def is_slow(self, task_name: str, threshold: float) -> bool:
        """평균 처리 시간이 threshold 초과 여부"""
```

### 3.5 HealthChecker (`common/monitoring/health_checker.py`)

**역할**: 시스템 전반의 헬스 상태 확인

**체크 항목**:
- Redis 연결 상태
- DB 연결 상태
- WebSocket 연결 상태
- 메모리 사용량
- 시스템 uptime

**인터페이스**:
```python
class HealthChecker(BaseMonitor):
    def check_redis(self) -> bool:
        """Redis 연결 확인"""
    
    def check_db(self) -> bool:
        """DB 연결 확인"""
    
    def check_websocket(self, collector) -> bool:
        """WebSocket 연결 확인"""
    
    def check_all(self) -> Dict[str, bool]:
        """전체 헬스 체크"""
```

### 3.6 ModuleStatus (`common/monitoring/module_status.py`)

**역할**: 모듈별 상태 집계 및 리포트

**상태 레벨**:
- `OK`: 정상
- `WARNING`: 경고 (일부 지연/경고)
- `CRITICAL`: 심각 (연결 끊김, 장애)

**인터페이스**:
```python
class ModuleStatus(BaseMonitor):
    def set_status(self, module: str, status: str, message: str = ""):
        """모듈 상태 설정"""
    
    def get_status(self, module: str) -> Dict[str, Any]:
        """모듈 상태 조회"""
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """전체 모듈 상태 조회"""
    
    def is_healthy(self) -> bool:
        """전체 시스템 정상 여부"""
```

---

## 4. RuntimeContext 확장

### 4.1 monitor_registry 추가

**변경 위치**: `common/runtime_context.py`

**추가 필드**:
```python
class RuntimeContext:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.run_id: Optional[str] = None
        self.env: Optional[str] = None
        self._shutdown_reason: Optional[str] = None
        
        # ⭐ PHASE18-4: 모니터링 레지스트리
        self.monitor_registry: Optional[MonitorRegistry] = None
```

**사용 방식**:
```python
# run_paper.py에서
from common.monitoring import MonitorRegistry, setup_monitoring

runtime_ctx = RuntimeContext()
runtime_ctx.monitor_registry = MonitorRegistry()

# 모니터링 시스템 초기화
setup_monitoring(runtime_ctx, config)

# 실행 중
runtime_ctx.monitor_registry.get('heartbeat').update('engine')

# 종료 시
runtime_ctx.monitor_registry.stop_all()
```

---

## 5. 통합 지점

### 5.1 run_paper.py / run_backtest.py

**변경 위치**: main 함수

**추가 코드**:
```python
from common.monitoring import setup_monitoring

# RuntimeContext 생성
runtime_ctx = RuntimeContext()
runtime_ctx.run_id = run_id
runtime_ctx.env = 'paper'

# 모니터링 시스템 초기화
setup_monitoring(runtime_ctx, cfg)
logger.info("✅ 모니터링 시스템 초기화 완료")

# Config에 주입
cfg['runtime_context'] = runtime_ctx

try:
    engine.run(...)
finally:
    # 리소스 정리
    logger.info("🧹 리소스 정리 시작...")
    if runtime_ctx.monitor_registry:
        runtime_ctx.monitor_registry.stop_all()
        logger.info("  ✅ 모니터링 중지 완료")
    ...
```

### 5.2 execution/engine.py

**변경 위치**: 메인 루프 (최소 변경)

**추가 코드**:
```python
# Runtime context 추출
runtime_ctx = config.get('runtime_context', None)

# 메인 루프
for candle in feed.stream():
    # Shutdown 체크 (PHASE18-3)
    if runtime_ctx and runtime_ctx.is_shutdown_requested():
        ...
    
    # ⭐ PHASE18-4: Heartbeat 업데이트
    if runtime_ctx and runtime_ctx.monitor_registry:
        heartbeat = runtime_ctx.monitor_registry.get('heartbeat')
        if heartbeat:
            heartbeat.update('engine')
    
    # ... 기존 로직 ...
```

### 5.3 collectors/websocket_collector.py

**변경 위치**: `_on_message` 메서드

**추가 코드**:
```python
def __init__(self, ..., runtime_ctx: Optional[RuntimeContext] = None):
    ...
    self.runtime_ctx = runtime_ctx

def _on_message(self, ws, message):
    # ⭐ PHASE18-4: Heartbeat 업데이트
    if self.runtime_ctx and self.runtime_ctx.monitor_registry:
        heartbeat = self.runtime_ctx.monitor_registry.get('heartbeat')
        if heartbeat:
            heartbeat.update('websocket')
    
    # ⭐ PHASE18-4: Latency 측정
    if self.runtime_ctx and self.runtime_ctx.monitor_registry:
        latency = self.runtime_ctx.monitor_registry.get('latency')
        if latency:
            with latency.measure('websocket_message'):
                # 기존 처리 로직
                ...
```

---

## 6. 성능 고려사항

### 6.1 성능 영향 최소화

**목표**: 성능 영향 ≤ 2% 내

**최적화 전략**:
1. **Heartbeat 업데이트**: 단순 dict 쓰기 (O(1), < 0.1ms)
2. **Watchdog**: 별도 thread, 5초 주기 (메인 루프 영향 없음)
3. **Latency 측정**: Context manager로 최소화 (선택적 측정)
4. **로그 레벨**: INFO 이하만 출력, DEBUG는 선택적

**벤치마크**:
- Heartbeat 업데이트: < 0.1ms
- Latency context manager: < 0.05ms overhead
- Watchdog thread: 메인 루프와 독립

### 6.2 메모리 사용

**Latency 통계**:
- 최근 1000개 샘플만 유지 (deque(maxlen=1000))
- Task당 약 8KB (1000 * 8 bytes)
- 총 메모리 영향: < 1MB

---

## 7. 테스트 전략

### 7.1 Unit 테스트

**파일**: `tests/test_phase18_4_monitoring.py`

**시나리오**:
1. **MonitorRegistry 동작**:
   - register/unregister
   - get/get_status

2. **HeartbeatMonitor**:
   - update 후 get_last_heartbeat
   - is_alive 체크

3. **Watchdog**:
   - 정상 heartbeat → 경고 없음
   - 오래된 heartbeat → 경고 로그

4. **LatencyMonitor**:
   - Context manager 측정
   - 통계 계산 (mean, max, p95)

5. **HealthChecker**:
   - Redis 연결 체크
   - DB 연결 체크

### 7.2 Integration 테스트

**REAL PAPER 10분 실행**:
```bash
python scripts/run_paper.py \
  --clean-state \
  --duration-hours 0.167 \
  --symbol BTCUSDT \
  --timeframe 1m
```

**검증 항목**:
- 모니터링 시스템 초기화 로그
- Heartbeat 업데이트 로그 (주기적)
- Watchdog 정상 동작 (경고 없음)
- Latency 통계 로그 (종료 시)
- 모니터링 중지 로그

---

## 8. Acceptance Criteria

### 8.1 필수 조건

- [ ] `common/monitoring/` 디렉토리 생성
- [ ] `MonitorRegistry`, `HeartbeatMonitor`, `Watchdog`, `LatencyMonitor`, `HealthChecker`, `ModuleStatus` 구현
- [ ] `RuntimeContext`에 `monitor_registry` 추가
- [ ] `run_paper.py`, `run_backtest.py`에 모니터링 통합
- [ ] `collectors/websocket_collector.py`에 heartbeat 추가
- [ ] 단위 테스트 작성 및 PASS
- [ ] REAL PAPER 10분 실행 성공
- [ ] 완료 리포트 작성

### 8.2 검증 조건

**로그 검증**:
- ✅ "모니터링 시스템 초기화 완료"
- ✅ Heartbeat 업데이트 (주기적)
- ✅ Watchdog 체크 로그
- ✅ "모니터링 중지 완료"
- ✅ ERROR/CRITICAL 로그 0건

**성능 검증**:
- ✅ 성능 영향 ≤ 2%
- ✅ 메모리 영향 < 1MB

**기능 검증**:
- ✅ 모니터링 등록/해제
- ✅ Heartbeat 정상 업데이트
- ✅ Watchdog 비정상 감지 (테스트)
- ✅ Latency 측정 및 통계

### 8.3 PHASE18-4 판정 기준

**PASS 조건**:
- 모든 Acceptance Criteria 만족
- 단위 테스트 100% PASS
- REAL PAPER smoke test ERROR 0건
- 기존 기능 회귀 없음
- DO-NOT-TOUCH 영역 변경 없음
- 성능 영향 ≤ 2%

---

## 9. 향후 확장 (PHASE19+)

### 9.1 Telegram 알림

**개념**:
- Watchdog가 이상 감지 시 Telegram 메시지 전송
- Critical 레벨: 즉시 알림
- Warning 레벨: 집계 후 5분마다 알림

**구현 위치**:
- `common/monitoring/telegram_notifier.py` (PHASE19+)

### 9.2 Prometheus/Grafana 통합

**개념**:
- Monitoring metrics를 Prometheus 형식으로 export
- Grafana 대시보드로 시각화

**구현 위치**:
- `common/monitoring/prometheus_exporter.py` (PHASE20+)

### 9.3 Auto-Recovery

**개념**:
- Watchdog가 이상 감지 시 자동 복구 시도
- 예: WebSocket 재연결, 프로세스 재시작

**구현 위치**:
- `common/monitoring/auto_recovery.py` (PHASE20+)

---

## 10. 구현 범위 제한

### 10.1 이번 PHASE에서 다루는 것

✅ MonitorRegistry (중앙 레지스트리)  
✅ HeartbeatMonitor (컴포넌트 활성 체크)  
✅ Watchdog (비정상 상태 감지)  
✅ LatencyMonitor (처리 시간 측정)  
✅ HealthChecker (시스템 헬스)  
✅ ModuleStatus (상태 집계)  
✅ RuntimeContext 확장

### 10.2 이번 PHASE에서 다루지 않는 것

❌ Telegram 알림 구현 (구조만 준비)  
❌ Prometheus/Grafana 통합  
❌ Auto-Recovery  
❌ Web Dashboard  
❌ 외부 모니터링 시스템 연동

---

## 11. 회귀 보호

### 11.1 DO-NOT-TOUCH 레이어

**절대 변경 금지**:
- `execution/portfolio_manager.py` ✅
- `execution/position_sizer.py` ✅
- `execution/risk_manager.py` ✅
- `execution/position_tracker.py` ✅
- `strategies/scalping.py` (전략 코어) ✅

**최소 변경 허용**:
- `execution/engine.py`: Heartbeat 업데이트만 추가 (2~3줄)
- `collectors/websocket_collector.py`: Heartbeat 업데이트 추가 (2~3줄)
- `common/runtime_context.py`: monitor_registry 필드 추가

---

## 12. 결론

### 12.1 설계 요약

✅ **중앙 집중식 모니터링 레지스트리**  
✅ **컴포넌트별 Heartbeat 관리**  
✅ **Watchdog 자동 감지**  
✅ **Latency 측정 및 통계**  
✅ **시스템 헬스 체크**  
✅ **최소 성능 영향 (≤2%)**  
✅ **DO-NOT-TOUCH 영역 보존**

### 12.2 예상 산출물

| 구분 | 파일 | 상태 |
|------|------|------|
| **모니터링 패키지** | `common/monitoring/__init__.py` | 생성 예정 |
| **HeartbeatMonitor** | `common/monitoring/heartbeat_monitor.py` | 생성 예정 |
| **Watchdog** | `common/monitoring/watchdog.py` | 생성 예정 |
| **LatencyMonitor** | `common/monitoring/latency_monitor.py` | 생성 예정 |
| **HealthChecker** | `common/monitoring/health_checker.py` | 생성 예정 |
| **ModuleStatus** | `common/monitoring/module_status.py` | 생성 예정 |
| **RuntimeContext** | `common/runtime_context.py` | 수정 예정 |
| **run_paper.py** | `scripts/run_paper.py` | 수정 예정 |
| **run_backtest.py** | `scripts/run_backtest.py` | 수정 예정 |
| **engine.py** | `execution/engine.py` | 수정 예정 (최소) |
| **websocket_collector.py** | `collectors/websocket_collector.py` | 수정 예정 (최소) |
| **테스트** | `tests/test_phase18_4_monitoring.py` | 생성 예정 |

---

**문서 작성**: 2025-11-19  
**작성자**: Cascade AI (Claude 4.5 Thinking)  
**승인**: PHASE18-4 설계 문서 초안
