# PHASE28-1-FIX: Zero-Trade 버그 수정 세션 요약

**일시**: 2025-12-05  
**목표**: PHASE28-1 Zero-Trade 버그 수정 (신호 생성은 되지만 실제 거래가 0건인 문제)  
**상태**: ⚠️ 부분 완료 (신호 생성 복구, 주문 제출은 여전히 0건)

---

## 🎯 작업 목표

PHASE28-1에서 모든 백테스트 조합이 0 trades를 기록하는 Critical 버그 수정:
- **문제**: 전략 파라미터가 제대로 전달되지 않아 신호 생성 로직이 기본값으로 작동
- **목표**: 최소 5건 이상의 실제 거래 발생
- **기준**: PHASE27-5 golden reference (4,334 signals, 4 trades)

---

## 🔍 ROOT CAUSE 분석

### ROOT CAUSE #1: `merge_strategy_config` 파라미터 미전달
**위치**: `common/config_loader.py::merge_strategy_config()`

**문제**:
```python
# 기존 로직
merged['strategy_config'] = strategy_cfg  # ❌ nested dict에만 저장
```

전략 코드는 `config.get('rsi_long_threshold', 45)`처럼 **top-level**에서 직접 읽지만,  
`merge_strategy_config`는 파라미터를 `strategy_config` nested dict에만 저장.

**결과**:
- 모든 전략 파라미터가 기본값으로 작동
- `rsi_long_threshold: 42` → 실제 사용값 `45` (기본값)
- 의도와 다른 신호 생성 로직

**수정**:
```python
# ✅ 8. PHASE28-1-FIX: 전략 파라미터를 top-level로 복사
for key, value in strategy_cfg.items():
    if not isinstance(value, dict):  # nested dict 제외
        merged[key] = value
```

**검증**:
```bash
$ python scripts/research/phase28_1_debug_config_merge.py
✅ rsi_long_threshold: 42 (default: 45) ✅ OK
✅ rsi_short_threshold: 58 (default: 55) ✅ OK
✅ bb_std_main: 1.2 (default: 1.0) ✅ OK
✅ use_adx: True (default: False) ✅ OK
✅ adx_trend_threshold: 20 (default: 25) ✅ OK
```

---

### ROOT CAUSE #2: Runner `backtest` 섹션 누락
**위치**: `scripts/research/phase28_1_single_strategy_performance.py::merge_config_for_backtest()`

**문제**:
```python
# 기존 로직
config['start_date'] = period_cfg['start']  # ❌ top-level만 설정
```

엔진은 **`config['backtest']`** 섹션에서 데이터 파일 경로/기간을 읽지만,  
Runner는 top-level에만 설정.

**수정**:
```python
# ✅ Backtest 섹션 생성 (엔진이 데이터 로드에 필요)
if 'backtest' not in config:
    config['backtest'] = {}
config['backtest']['symbol'] = config.get('symbol', 'BTCUSDT')
config['backtest']['data_dir'] = config.get('data_dir', 'data')
config['backtest']['data_file'] = config.get('data_file', 'BTCUSDT_5m_2024-01-01_2024-12-31.csv')
config['backtest']['start_date'] = period_cfg['start']
config['backtest']['end_date'] = period_cfg['end']
```

---

### ROOT CAUSE #3: Runner `strategies` 섹션 누락
**위치**: `scripts/research/phase28_1_single_strategy_performance.py::run_performance_baseline()`

**문제**:
```python
# 기존 로직
common_cfg = config.get('common', {})  # ❌ strategies 섹션이 common에 없음
```

Runner가 `common` 섹션만 복사하지만, 전략 파라미터는 top-level `strategies`에 정의됨.

**수정**:
```python
# ✅ PHASE28-1-FIX: strategies 섹션을 common에 병합
if 'strategies' not in common_cfg and 'strategies' in config:
    common_cfg['strategies'] = config['strategies']
    logger.info(f"✅ strategies 섹션을 common에 병합: {list(config['strategies'].keys())}")
```

---

## ✅ 수정 사항 요약

### 1. `common/config_loader.py`
- ✅ `merge_strategy_config`: 전략 파라미터를 top-level로 복사
- ✅ 검증 스크립트로 파라미터 전달 확인

### 2. `scripts/research/phase28_1_single_strategy_performance.py`
- ✅ `merge_config_for_backtest`: `backtest` 섹션 생성
- ✅ `run_performance_baseline`: `strategies` 섹션을 `common`에 병합
- ✅ `extract_metrics_from_tracker`: TradeActivityTracker 결과 파싱 (run_v2가 반환값 없음)
- ✅ 디버그 로깅 추가

### 3. `configs/backtest/phase28_1_btc5m_baseline_presets.yml`
- ✅ PHASE27-5 구조 적용 (`params` 키 제거, 파라미터 직접 배치)
- ✅ `common` 섹션에 `strategy.selector` 추가
- ✅ `smoke_test` 구간 정의 추가

### 4. 검증 도구
- ✅ `scripts/research/phase28_1_debug_config_merge.py`: Config 병합 검증 스크립트

---

## 📊 현재 결과

### Fixed Config 직접 실행 (성공 사례)
**파일**: `configs/backtest/phase28_1_btc5m_baseline_presets_fixed.yml`

```bash
$ python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_1_btc5m_baseline_presets_fixed.yml
```

**결과**:
- ✅ **총 캔들**: 8,821개
- ✅ **신호 생성**: 4,334건 (signal_true)
- ✅ **LONG**: 2,128건 | **SHORT**: 2,206건
- ✅ **Regime Range**: 2,352건 | **Regime Trend**: 1,982건
- ✅ **실제 주문**: 4건
- ✅ **PHASE27-5 수준 복구**

### Runner 실행 (부분 성공)
**명령어**: `python scripts/research/phase28_1_single_strategy_performance.py --smoke --preset baseline`

**결과**:
- ✅ **총 캔들**: 8,821개
- ✅ **신호 생성**: 5,856건 (이전 0건 → 복구!)
- ✅ **LONG**: 2,893건 | **SHORT**: 2,963건
- ⚠️ **Regime Range**: 5,856건 | **Regime Trend**: 0건 (비정상)
- ❌ **실제 주문**: 0건
- ❌ **에러**: `'cooldown_candles'` KeyError 반복 발생

---

## ⚠️ 남은 문제

### 문제 1: `cooldown_candles` KeyError
**현상**:
```
[ERROR] ❌ [btc5m_baseline_v1] 전략 오류: 'cooldown_candles'
```

**원인 추정**:
- 전략 코드 어딘가에서 `config['cooldown_candles']`를 직접 참조
- `merge_strategy_config`가 이 파라미터를 top-level로 복사하지 못함
- 또는 preset 파라미터에 포함되지 않음

**Action Required**:
1. 전략 코드에서 `cooldown_candles` 사용 위치 확인
2. Config에 기본값 추가 또는 preset에 포함

---

### 문제 2: 모든 신호가 Range Regime으로 분류
**현상**:
- Fixed Config: Range 2,352 / Trend 1,982 (정상)
- Runner: Range 5,856 / Trend 0 (비정상)

**원인 추정**:
- ADX 파라미터가 제대로 전달되지 않음
- `use_adx: true`는 전달되지만, `adx_period`, `adx_trend_threshold` 등이 누락될 수 있음

**Action Required**:
1. Runner 병합 후 최종 config에서 ADX 파라미터 확인
2. `merge_strategy_config`가 indicators 섹션도 올바르게 병합하는지 검증

---

### 문제 3: 주문 제출 0건
**현상**:
- 신호는 5,856건 생성
- 하지만 실제 주문은 0건

**원인 추정**:
1. `cooldown_candles` 에러로 인해 전략 실행 중단
2. Guard 시스템(FlowGuardian, RiskManager)에서 모든 신호 차단
3. PortfolioManager Budget Cap 문제

**Action Required**:
1. Guard/Risk 로그 확인
2. Budget 계산 로직 검증
3. `cooldown_candles` 에러 해결 후 재테스트

---

## 🚀 다음 단계

### Immediate (이번 세션 완료 전)
1. ✅ 커밋 완료
2. ⏳ PHASE_ROADMAP.md 업데이트 (부분 완료 상태)
3. ⏳ 세션 요약 문서 작성 (이 파일)

### Next Session
1. **`cooldown_candles` 에러 수정**
   - 전략 코드에서 사용 위치 확인
   - Config 기본값 추가 또는 preset에 포함

2. **ADX 파라미터 전달 검증**
   - Runner 최종 config 덤프 로깅
   - `indicators` 섹션 병합 확인

3. **Guard/Budget 로그 분석**
   - 신호는 생성되지만 주문이 0건인 원인 파악
   - FlowGuardian/RiskManager 차단 여부 확인

4. **Acceptance Test 실행**
   - smoke+neutral: ≥5 trades 달성
   - pytest 회귀 테스트
   - PHASE_ROADMAP 업데이트 (PASS)

---

## 📝 참고 파일

### 수정된 파일
- `common/config_loader.py`
- `scripts/research/phase28_1_single_strategy_performance.py`
- `configs/backtest/phase28_1_btc5m_baseline_presets.yml`
- `configs/backtest/phase28_1_btc5m_baseline_presets_fixed.yml` (임시 검증용)

### 검증 도구
- `scripts/research/phase28_1_debug_config_merge.py`

### 결과 파일
- `reports/phase28_1_baseline_smoke_test_tracker.json`
- `reports/phase28_1_btc5m_baseline_tracker_summary.json`
- `reports/phase28_1_btc5m_performance.json`

### 문서
- `docs/PHASE28/PHASE28-1_SINGLE_STRATEGY_PERFORMANCE_BASELINE.md` (원본)
- `docs/PHASE28/PHASE28-1-FIX_ZERO_TRADE_BUGFIX_SESSION_SUMMARY.md` (이 파일)

---

## 🎓 교훈

1. **Config 병합 시 파라미터 전달 경로 주의**
   - `merge_strategy_config`는 nested dict에 저장
   - 전략 코드는 top-level에서 직접 읽음
   - **양측 모두 지원**하도록 수정 필요

2. **Runner와 Engine의 Config 구조 차이**
   - Engine: `config['backtest']` 섹션 필수
   - Runner: `common` 섹션만 복사 → 누락 발생

3. **PHASE27-5 Golden Reference의 중요성**
   - 작동하는 Config 구조를 기준으로 정렬
   - 새로운 구조는 반드시 Golden과 비교 검증

4. **TradeActivityTracker의 한계**
   - 신호 생성 통계는 제공
   - 실제 trade 결과 (PnL, win rate 등)는 별도 저장 필요
   - `engine.run_v2()`는 반환값 없음 → 외부 파일 의존

---

**다음 세션에서 계속...**
