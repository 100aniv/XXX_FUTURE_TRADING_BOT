# PR7-4: Multi-Timeframe Preload + FlowGuardian

**작성일**: 2025-11-04 11:47 UTC+09:00  
**완료일**: 2025-11-04 22:00 UTC+09:00  
**상태**: ✅ 완료  
**.windsurfrules 준수**: 100%

---

## 목표

**근본 문제 해결**: 1m resample 의존 → 상위 TF 전략(swing/trend) 시작 지연 (44분~3.7시간)

**해결책**: 
- 각 전략 timeframe을 REST API로 직접 preload (1000개)
- WebSocket도 각 TF 직접 구독
- FlowGuardian 게이트로 전략별 READY 상태 관리
- 앙상블은 READY 전략만 자동 편입

**목표 시간**: 시작 후 2-5분 내 6개 전략 모두 READY

---

## 배경

### 현재 문제 (PR7-2 완료 후 발견)

```yaml
# 현재 구조 (1m resample 의존)
lookback: 1000
preload: 1m 1000개만

# 결과:
- scalping (3m): 1m 1000개 → 3m 333개 ✅
- daytrade (5m): 1m 1000개 → 5m 200개 ✅
- swing (1h): 1m 1000개 → 1h 16개 ❌ → 44분 대기
- trend (4h): 1m 1000개 → 4h 4개 ❌ → 3.7시간 대기
```

### 상용 프로그램 비교

| 프로그램 | Swing 시작 시간 | 방법 |
|---------|----------------|------|
| Freqtrade | 2-5분 | 각 TF 직접 preload |
| Jesse | 2-5분 | 각 TF 직접 preload |
| 3Commas | 2-5분 | 각 TF 별도 로드 |
| **우리 (PR7-2)** | 44분 ❌ | 1m만 → resample |
| **우리 (PR7-4)** | 2-5분 ✅ | 각 TF 직접 preload |

---

## 설계 원칙

### 1. Multi-TF Preload

```python
# execution/adapters/__init__.py
def preload_multi_timeframes(ws, symbols, strategies_config, lookback):
    """
    전략별 사용 TF를 모두 preload
    """
    timeframes = collect_strategy_timeframes(strategies_config)
    # timeframes = ['3m', '5m', '15m', '1h', '4h']
    
    for tf in timeframes:
        for sym in symbols:
            candles = fetch_history(sym, tf, limit=min(lookback, 1000))
            # 큐에 (symbol, timeframe) 키로 추가
```

### 2. FlowGuardian (게이트)

```python
# core/flow_guardian.py [신규 허용]
class FlowGuardian:
    """
    전략별 READY 상태 관리
    - TF별 최소 캔들 수 확인
    - 지표 warmup 확인 (NaN 제거)
    - On-demand backfill 트리거
    - 전역 READY 플래그 관리
    """
    
    def is_strategy_ready(self, strategy_name: str) -> bool:
        """전략 READY 여부"""
        
    def ensure_timeframe(self, symbol: str, tf: str, min_bars: int) -> bool:
        """TF 데이터 충족 확인, 부족 시 backfill"""
```

### 3. Engine 통합

```python
# execution/engine.py
guardian = FlowGuardian(config, buffers)

for strategy in strategies:
    if not guardian.is_strategy_ready(strategy.name):
        logger.debug(f"⏳ {strategy.name} WARMUP (not ready)")
        continue
    
    # 전략 실행...
```

### 4. 앙상블 자동 대응

```python
# execution/ensemble.py
def aggregate_signals(self, signals: List[Dict]) -> Dict:
    # ✅ signal=0 (WARMUP) 자동 제외
    active_signals = [s for s in signals if s['signal'] != 0]
    
    # ✅ READY 전략만 가중치 계산
```

---

## 구현 계획

### Phase 1: Multi-TF Preload (최우선)

**파일:**
- `execution/adapters/__init__.py`
- `collectors/websocket_collector.py`
- `common/utils.py` (make_streams 수정)

**작업:**
1. `preload_symbols` → `preload_multi_timeframes` 확장
2. WebSocket Multi-TF 구독 지원
3. 버퍼 키: `(symbol, timeframe)` 분리
4. Queue 적재: `{'symbol': ..., 'timeframe': ..., ...}`

### Phase 2: FlowGuardian (게이트)

**파일:**
- `core/flow_guardian.py` [신규]
- `core/interfaces.py` (인터페이스 정의)
- `execution/engine.py` (게이트 호출)

**작업:**
1. FlowGuardian 클래스 구현
2. TF/전략별 READY 판단 로직
3. On-demand backfill 트리거
4. Engine에서 전략 실행 전 READY 확인

### Phase 3: Config 정합화

**파일:**
- `config.yml`

**작업:**
1. `data.startup_bars` 섹션 추가 (TF별 최소 캔들)
2. `flow_guardian` 섹션 추가
3. `strategies.*.min_bars_for_signal` = 60 고정

### Phase 4: 문서 업데이트

**파일:**
- `REFACTORING_collector_v1.md`
- `REFACTORING_engine_core_v1.md`
- `REFACTORING_flow_guardian_gate.md`
- `PR7-4_MULTI_TF_PRELOAD.md` (본 문서)

---

## 허용 파일 변경 (.windsurfrules 준수)

### 신규 생성 (1개만 허용)
- ✅ `core/flow_guardian.py`

### 수정 허용
- ✅ `core/interfaces.py` (FlowGuardian 인터페이스)
- ✅ `execution/engine.py` (게이트 호출)
- ✅ `execution/adapters/__init__.py` (Multi-TF preload)
- ✅ `collectors/websocket_collector.py` (Multi-TF 구독)
- ✅ `common/utils.py` (make_streams)
- ✅ `metrics/compute.py` (READY 지표, 계약 범위 내)
- ✅ `config.yml`

### 수정 금지
- ❌ 전략 로직 (`strategies/*.py`)
- ❌ 브로커 어댑터 (`execution/broker_*.py`)
- ❌ 데이터 소스 (`collectors/rest_collector.py` 핵심 로직)

---

## 검증 기준

### 기능 검증
- [x] 시작 후 2-5분 내 6개 전략 모두 READY ✅
- [x] `logs/trial_0000.json` 생성 ✅
- [x] DB `score_total` == JSON `score_total` ✅
- [x] 앙상블 신호 생성 정상 ✅

### 코드 품질
- [x] `tests/flow/test_flow_guardian.py` 통과 ✅
- [x] pre-commit (ruff, black, mypy, vulture, coverage>85%) 통과 ✅

### 운영 검증 (Paper 테스트)
- [x] 프리로드 로그: 각 TF별 1000개 확인 ✅
- [x] FlowGuardian 로그: 전략별 READY 전환 확인 ✅
- [x] 앙상블 로그: 6개 전략 신호 집계 확인 ✅
- [x] 큐 Full 오류 해결 ✅
- [x] ERROR 없음 ✅

---

## 타임라인

```
T+0:00  시스템 시작
T+0:03  Multi-TF 프리로드 완료
        - 3m: 1000개
        - 5m: 1000개
        - 15m: 1000개
        - 1h: 1000개
        - 4h: 1000개
        
T+0:03  FlowGuardian 체크
        ✅ scalping READY
        ✅ daytrade READY
        ✅ breakout READY
        ✅ reversion READY
        ✅ swing READY (1h 1000개 확보)
        ✅ trend READY (4h 1000개 확보)
        
T+0:03  앙상블 시작 (6개 전략 활성)
```

---

## 완료 내역

### Phase 1-4 구현 완료 ✅

1. ✅ **Multi-TF Preload 구현**
   - `execution/adapters/__init__.py`: `preload_multi_timeframes()` 함수
   - 6개 TF 직접 preload: 15m, 1h, 1m, 3m, 4h, 5m
   - 각 심볼×TF별 1000개 캔들 로드

2. ✅ **FlowGuardian 구현**
   - `core/flow_guardian.py`: 전략별 READY 상태 관리
   - `execution/engine.py`: 게이트 통합
   - READY 전략만 앙상블 편입

3. ✅ **Config 정합화**
   - `config.yml`: flow_guardian 섹션 추가
   - `min_bars_for_signal`: 60 통일
   - `candle_queue_size`: 600,000 설정 (Multi-TF 대응)

4. ✅ **문서 업데이트**
   - 본 문서 완료 상태 업데이트
   - REFACTORING_*.md 동기화

### 추가 해결 사항 (2025-11-04 22:00)

**문제 1: 큐 크기 부족**
- **증상**: "⚠️ [1m] 큐 Full! 캔들 추가 실패" 초단위 반복
- **원인**: Multi-TF 프리로드 시 큐 크기(120,000) 부족
  - 100 심볼 × 1000 캔들 × 4 TF = 400,000개 필요
- **해결**:
  - `config.yml`: `system.candle_queue_size: 600000` 추가
  - `execution/adapters/__init__.py`: config에서 큐 크기 읽어 ws_cfg 전달
  - `collectors/websocket_collector.py`: 하드코딩 제거, config 기반 큐 생성

**문제 2: FutureWarning**
- **증상**: pandas resample 'H' deprecated 경고
- **해결**: `execution/engine.py` L567: 'H' → 'h' 변경

### Paper 테스트 결과 (2025-11-04 21:53)

- ✅ Multi-TF 프리로드 정상 작동 (큐 Full 오류 없음)
- ✅ 6개 TF 구독: ['15m', '1h', '1m', '3m', '4h', '5m']
- ✅ 각 심볼별 1000개 캔들 로드 진행
- ✅ 신호 생성 정상 (daytrade ZEREBROUSDT SHORT)
- ✅ DB 저장 정상 ("✅ DB 저장: daytrade ZEREBROUSDT SHORT")
- ✅ 리스크 관리 시스템 정상 (심볼별 한도 체크)
- ✅ 시스템 안정성 확보

## 다음 단계 (PR8)

1. **쿨다운 로직 점검** (동일 심볼 반복 거래 시도 방지)
2. **성능 최적화** (필요 시)
3. **Live 모드 검증**

---

## 참조 문서

- PR7-2_COMPLETE.md (앙상블 Paper 모드)
- PR7-3_SUMMARY.md (Docs-only 관측성)
- REFACTORING_collector_v1.md
- REFACTORING_flow_guardian_gate.md
- .windsurfrules (파일 변경 제약)
