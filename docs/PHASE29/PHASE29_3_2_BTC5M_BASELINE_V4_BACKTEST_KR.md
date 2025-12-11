# PHASE29-3.2: Duration Fix & V4 Backtest 실행 완료

**작성일**: 2025-12-10  
**판정**: ⚠️ **PARTIAL SUCCESS** (Duration 수정 성공 / V4 신호 생성 실패)

---

## 1. Duration 버그 수정

### 1.1. 문제 원인

**증상**:
- PHASE29-3.1에서 V4 1일/1주 백테스트 실행 시 1시간 후 조기 종료
- Config에 `duration_minutes: 1440` 설정했으나 무시됨
- 로그: `⏱️  [MARKET-TIME] Duration 모드 시작: 1.00시간`

**근본 원인**:
```python
# execution/engine.py Line 906-907 (수정 전)
duration_mode = config.get('paper', {}).get('duration_mode', 'market_time')
duration_hours = config.get('paper', {}).get('duration_hours', 1)  # 기본값 1시간
```

- Backtest Config에는 `paper` 섹션이 없음 → 기본값 1시간 사용
- Backtest는 `start_date/end_date`로 범위가 정해져 있으므로 Duration 제약 불필요

### 1.2. 해결 방법

**설계 원칙**:
1. Backtest 모드는 기본적으로 `unlimited` Duration
2. Paper/Live 모드는 기존 Duration 로직 유지
3. 헬퍼 함수로 Duration 초기화 로직을 분리하여 테스트 가능하게 구성

**구현**:
```python
def _init_duration_state(config: dict, mode: str) -> dict:
    """
    PHASE29-3.2: Duration 상태 초기화 헬퍼
    
    Backtest 모드에서는 start/end 날짜로 범위가 정해져 있으므로
    Duration 제약을 적용하지 않는다 (unlimited).
    """
    import time
    
    # Backtest 모드는 기본적으로 unlimited (start/end 날짜로 범위 제어)
    if mode == 'backtest':
        logger.info("🔧 [PHASE29-3.2] Backtest 모드: Duration unlimited (start/end 날짜 기반)")
        return {
            'duration_mode': 'unlimited',
            'duration_hours': 0,
            'duration_seconds': 0,
            'start_wall_time': time.time()
        }
    
    # Paper/Live 모드는 기존 로직 유지
    duration_mode = config.get('paper', {}).get('duration_mode', 'market_time')
    duration_hours = config.get('paper', {}).get('duration_hours', 1)
    duration_seconds = duration_hours * 3600
    
    # Duration 설정 검증
    if duration_hours <= 0:
        logger.warning(f"⚠️ Duration 설정 이상: {duration_hours}h → 무제한 실행 모드")
        duration_mode = 'unlimited'
        duration_hours = 0
        duration_seconds = 0
    
    return {
        'duration_mode': duration_mode,
        'duration_hours': duration_hours,
        'duration_seconds': duration_seconds,
        'start_wall_time': time.time()
    }
```

**적용 지점** (`execution/engine.py`):
```python
# Line 956 (수정 후)
duration_state = _init_duration_state(config, mode)
duration_mode = duration_state['duration_mode']
duration_hours = duration_state['duration_hours']
duration_seconds = duration_state['duration_seconds']
start_wall_time = duration_state['start_wall_time']
```

### 1.3. 테스트 검증

**파일**: `tests/test_phase29_3_2_duration_backtest.py`

**결과**: ✅ **8/8 PASS**

| 테스트 케이스 | 결과 | 검증 내용 |
|--------------|------|-----------|
| `test_backtest_mode_unlimited` | ✅ PASS | Backtest → unlimited 자동 설정 |
| `test_paper_mode_market_time_default` | ✅ PASS | Paper 기본값 (market_time, 1h) |
| `test_paper_mode_wall_clock` | ✅ PASS | Paper wall_clock 2.5h 설정 |
| `test_paper_mode_duration_zero` | ✅ PASS | duration_hours=0 → unlimited 전환 |
| `test_paper_mode_duration_negative` | ✅ PASS | duration_hours<0 → unlimited + warning |
| `test_live_mode_default` | ✅ PASS | Live 기본값 (market_time, 1h) |
| `test_backtest_config_structure` | ✅ PASS | 실제 Backtest Config 구조 검증 |
| `test_paper_config_structure` | ✅ PASS | 실제 Paper Config 구조 검증 |

**V4 전략 테스트**:
```bash
pytest tests/test_phase29_3_2_duration_backtest.py tests/test_btc5m_baseline_v4.py -v
# 결과: 14/14 PASS (Duration 8 + V4 Strategy 6)
```

### 1.4. 백테스트 실행 로그 확인

**1일 백테스트**:
```
2025-12-10 01:56:31 [INFO] 🔧 [PHASE29-3.2] Backtest 모드: Duration unlimited (start/end 날짜 기반)
2025-12-10 01:56:31 [INFO] ♾️  [UNLIMITED] Duration 제약 없음 (Backtest 모드 또는 명시적 설정)
2025-12-10 01:56:35 [INFO] ✅ Trading Engine 종료: 총 캔들=576개, 진입 거래=0건
```

**1주 백테스트**:
```
2025-12-10 02:00:08 [INFO] ♾️  [UNLIMITED] Duration 제약 없음
2025-12-10 02:00:08 [INFO] ✅ Trading Engine 종료: 총 캔들=2,304개, 진입 거래=0건
```

✅ **Duration 문제 해결 확인**: 1시간 제한 없이 전체 캔들 처리 완료

---

## 2. V4 전략 신호 생성 실패

### 2.1. 문제 현황

**백테스트 결과**:
- 1일 (576 캔들): **0건 거래** ❌
- 1주 (2,304 캔들): **0건 거래** ❌

**관찰된 사항**:
1. ✅ V4 전략이 `strategies/__init__.py`에 등록됨
2. ✅ Config 파라미터가 전략에 전달됨 (로그 확인)
3. ✅ Duration unlimited로 전체 캔들 처리됨
4. ❌ 신호가 전혀 생성되지 않음

### 2.2. 추정 원인

**가능성 1: 지표 컬럼 누락**
- V4 전략은 `rsi_14`, `adx_14`, `di_plus_14`, `di_minus_14`, `ema_5`, `ema_20` 등 필요
- Backtest 데이터 파일 또는 지표 생성 과정에서 필요한 컬럼이 없을 가능성

**가능성 2: 조건이 너무 엄격**
- Trend Mode: `trend_min_score >= 3` (최대 8점)
  - RSI Pullback (3점) + BB Lower (2점) + EMA Pullback (2점) + DI Bull (1점)
- Range Mode: `range_min_score >= 2` (최대 6점)
  - RSI Oversold (3점) + BB Lower (2점) + ADX Range (1점)
- ADX/DI/RSI 조건이 동시에 만족되기 어려울 수 있음

**가능성 3: 필터 차단**
- ATR Filter: `min_atr_pct: 0.0015` (0.15%)
- Volume Filter: `min_volume_ratio: 0.5` (MA20 대비 50%)
- 해당 기간의 변동성/거래량이 필터 기준 이하일 가능성

### 2.3. 디버깅 로그 추가

V4 전략에 다음 로그를 추가했으나 충분한 정보를 얻지 못함:
```python
logger.debug(f"[V4] Filter 차단: {filter_result['reason']} | Regime: {regime} | ATR%: {atr_pct*100:.3f}%")
logger.debug(f"[V4] Trend Score: {score}/{trend_min_score} | Side: {side} | Conditions: {len(conditions)}")
logger.info(f"[V4] ✅ Trend 신호: {side} | Score: {score}/{trend_min_score}")
```

### 2.4. 권장 조치

**즉시 조치**:
1. ✅ Duration 수정 및 테스트 완료 → Git 커밋
2. ⏳ V4 신호 생성 문제는 별도 PHASE29-3.3으로 분리

**PHASE29-3.3 계획** (별도 세션):
1. 데이터 파일 지표 컬럼 확인
   - `data/BTCUSDT_5m_2024-01-01_2024-12-31.csv` 구조 검증
   - 필요한 지표 컬럼 존재 여부 확인
2. 간단한 디버깅 스크립트 작성
   - 100개 캔들 샘플에서 Score 계산 로직 단위 테스트
   - 각 조건별 충족률 확인
3. Threshold 완화 실험
   - `trend_min_score: 3 → 2`
   - `range_min_score: 2 → 1`
   - `min_atr_pct: 0.0015 → 0.001`
4. V3 대비 비교
   - 동일 기간 V3 백테스트 실행
   - V3도 신호가 없는지 확인 (기간 문제일 수 있음)

---

## 3. 작업 요약

### 3.1. 완료된 작업

| 항목 | 상태 | 비고 |
|------|------|------|
| Duration 헬퍼 함수 구현 | ✅ COMPLETE | `_init_duration_state()` |
| Backtest unlimited 로직 | ✅ COMPLETE | mode=='backtest' → unlimited |
| Duration Unit Test | ✅ COMPLETE | 8/8 PASS |
| V4 전략 등록 | ✅ COMPLETE | `strategies/__init__.py` |
| 1일 백테스트 실행 | ✅ COMPLETE | Duration 정상, 신호 0건 |
| 1주 백테스트 실행 | ✅ COMPLETE | Duration 정상, 신호 0건 |

### 3.2. 미완료 항목

| 항목 | 상태 | 다음 조치 |
|------|------|-----------|
| V4 신호 생성 | ❌ FAIL | PHASE29-3.3으로 분리 |
| Gate 검증 (20~60건) | ⏳ PENDING | 신호 생성 후 진행 |
| 성능 지표 분석 | ⏳ PENDING | 신호 생성 후 진행 |

### 3.3. Artifacts

**코드**:
- `execution/engine.py`: Duration 헬퍼 함수 추가
- `strategies/__init__.py`: V4 전략 등록
- `strategies/btc5m_baseline_v4.py`: 디버깅 로그 추가
- `tests/test_phase29_3_2_duration_backtest.py`: Duration 테스트 (8/8 PASS)

**Config**:
- `configs/backtest/phase29_3_1_btc5m_baseline_v4_day.yml`: 1일 백테스트
- `configs/backtest/phase29_3_1_btc5m_baseline_v4_week.yml`: 1주 백테스트

**문서**:
- `docs/PHASE29/PHASE29_3_2_BTC5M_BASELINE_V4_BACKTEST_KR.md` (본 문서)

**백테스트 결과**:
- `reports/backtest/phase29_3_1/btc5m_baseline_v4_day_summary.json`: 0건
- `reports/backtest/phase29_3_1/btc5m_baseline_v4_week_summary.json`: 0건

---

## 4. 판정

### 4.1. PHASE29-3.2 판정

**상태**: ⚠️ **PARTIAL SUCCESS**

**근거**:
- ✅ **Duration 수정 성공**: Backtest 모드에서 unlimited 동작 확인
- ✅ **테스트 통과**: Duration 8/8 + V4 6/6 = 14/14 PASS
- ❌ **V4 신호 실패**: 1일/1주 백테스트 모두 0건 거래

### 4.2. 다음 단계

**우선순위 1: V4 신호 생성 디버깅** (PHASE29-3.3)
- 데이터/지표 확인
- Threshold 완화 실험
- V3 대비 비교

**우선순위 2: Duration 수정 커밋**
- 현재까지의 Duration 수정 사항만 우선 커밋
- V4 신호 문제와 분리하여 관리

**우선순위 3: ROADMAP 업데이트**
- PHASE29-3.2: Duration Fix COMPLETE
- PHASE29-3.3: V4 Signal Debug PLANNED

---

## 5. 기술 노트

### 5.1. Duration 모드별 동작 방식

| Mode | 설정 방법 | 종료 조건 | 용도 |
|------|-----------|----------|------|
| **unlimited** | duration_hours=0 또는 mode='backtest' | start/end 날짜 또는 데이터 소진 | Backtest, 무제한 Paper/Live |
| **wall_clock** | paper.duration_mode='wall_clock' | 실제 시계 기준 N시간 | Paper/Live 장시간 운영 |
| **market_time** | paper.duration_mode='market_time' (기본) | 마켓 타임 누적 N시간 | Paper/Live 정해진 시간 |

### 5.2. 기존 PHASE Duration 호환성

**영향 없음**: 기존 PAPER/LIVE Duration 로직은 그대로 유지됨
- PHASE16+: Wall-clock Duration
- PHASE22-1: Duration 로직 명확화
- PHASE22-2: Duration 로그 간격 추적

**신규 추가**: Backtest 모드만 unlimited로 자동 설정

---

**작성자**: Windsurf AI  
**검토**: Pending (사용자 확인 필요)
