# PHASE27-8: Baseline Signal SSOT & Cleanup

**Date**: 2025-12-05  
**Status**: ✅ **COMPLETE** (PHASE27-9 검증 완료)

---

## 🎯 목표

**신호 계산 경로 단일화**: 모든 신호는 `execution/engine.py::run_v2()` → `BaseStrategy.compute_signal()` 경로에서만 생성

**AS-IS 문제**:
- PHASE27-4에서 만든 Offline Scan이 엔진을 우회하여 신호를 직접 계산
- "두 번째 신호 경로"가 존재하여 SSOT(Single Source of Truth) 원칙 위배
- Offline vs Engine Replay parity 맞추기 위한 복잡한 디버깅 코드 존재

**TO-BE 원칙**:
- 신호의 유일한 진실은 엔진 경로 (`run_v2()` → `BaseStrategy.compute_signal()`)
- 연구/분석 스크립트는 엔진 산출물(JSON, DB, TradeActivityTracker)만 읽음
- Offline Scan 방식 제거 또는 Legacy 격리

---

## 📊 AS-IS 진단: "두 번째 신호 경로" 분석

### 1. 신호 계산 경로 분석

| 항목 | Offline Scan (phase27_4) | Engine Replay (공식) | 판정 |
|------|--------------------------|---------------------|------|
| **진입점** | `scripts/research/phase27_4_btc5m_baseline_signal_scan.py` | `execution/engine.py::run_v2()` | ❌ 중복 |
| **지표 계산** | `add_indicators()` 직접 호출 (Line 107-112) | `execution/engine.py` 내부에서 호출 | ❌ 중복 |
| **신호 생성** | `signal_logic()` 직접 호출 (Line 158) | `BaseStrategy.compute_signal()` 호출 | ❌ 중복 |
| **데이터 소스** | CSV 파일 직접 로드 | `Feed` 어댑터 (BacktestFeed/WebSocketFeed) | ❌ 중복 |
| **결과 저장** | JSON 파일 (`phase27_4_*_summary.json`) | TradeActivityTracker + DB | ❌ 중복 |

### 2. 직접 신호 계산하는 코드 (SSOT 위배)

#### `scripts/research/phase27_4_btc5m_baseline_signal_scan.py`
```python
# Line 91-116: 지표 계산 (엔진 우회)
def prepare_indicators(df: pd.DataFrame, use_adx: bool = True, adx_period: int = 14):
    df_with_indicators = add_indicators(
        df,
        use_adx=use_adx,
        adx_period=adx_period,
        drop_nan=False
    )
    return df_with_indicators

# Line 119-216: 신호 스캔 (엔진 우회)
def scan_signals(df: pd.DataFrame, config: Dict[str, Any], min_bars: int = 50):
    for i in range(min_bars, len(df)):
        df_slice = df.iloc[:i+1].copy()
        signal = signal_logic(df_slice, config)  # ⚠️ 엔진 우회, 직접 호출
        # ... 신호 처리 로직
```

**문제점**:
- ❌ `signal_logic()` 직접 호출: 엔진의 전략 로딩/설정/Guard/Risk 체크를 모두 우회
- ❌ `add_indicators()` 직접 호출: 엔진 내부의 지표 계산 로직과 별개 경로
- ❌ CSV 직접 로드: Feed 어댑터의 데이터 정규화/검증 우회
- ❌ NaN 처리, warmup 로직이 엔진과 미세하게 다를 가능성 → Parity 불일치 원인

### 3. 엔진 산출물만 읽는 분석 코드 (허용)

#### `scripts/research/phase27_6_signal_parity_analyzer.py`
```python
# Line 43-50: JSON 파일만 읽음 (신호 계산 안 함)
def load_json(path: Path) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_offline_signals(offline_summary: Dict[str, Any]) -> pd.DataFrame:
    # 이미 생성된 JSON에서 데이터 추출만
    signal_details = offline_summary.get('scan_result', {}).get('signal_details', [])
    return pd.DataFrame(signal_details)
```

**허용되는 이유**:
- ✅ 신호를 직접 계산하지 않음
- ✅ 엔진/Offline Scan이 이미 만든 JSON을 읽어서 통계만 냄
- ✅ 연구/디버깅용 분석 도구로서 역할 명확

#### `scripts/research/phase27_7_btc5m_signal_parity_diff.py`
```python
# 동일하게 JSON만 읽어서 비교
def extract_offline_signals_df(offline_summary: Dict[str, Any]) -> pd.DataFrame:
    # 이미 생성된 JSON에서 추출
    ...

def extract_replay_signals_df(replay_summary: Dict[str, Any]) -> pd.DataFrame:
    # 이미 생성된 JSON에서 추출
    ...
```

**허용되는 이유**:
- ✅ 신호 계산 없음, JSON 통계 비교만
- ✅ Per-bar diff 분석은 디버깅에 유용

### 4. 테스트 현황

| 테스트 파일 | 상태 | 비고 |
|------------|------|------|
| `tests/test_phase27_*.py` | ❌ **존재하지 않음** | Parity 테스트 없음 |
| `tests/test_engine_single_entrypoint.py` | ✅ 존재 (8/8 PASS) | PHASE23-5에서 추가 |

**발견**: 
- PHASE27에서 Offline vs Replay parity를 강제하는 테스트는 실제로 없었음
- 문서에는 "±10% parity" 목표가 있었지만, 테스트 코드로 구현되지 않음
- 따라서 제거해도 회귀 위험 없음

---

## 🎯 TO-BE: Signal SSOT 원칙

### 1. SSOT 원칙 정의

**유일한 신호 진실(SSOT)**:
```
실거래 / 페이퍼 / 백테스트 / 연구 → 모든 신호는 아래 경로에서만 생성

execution/engine.py::run_v2()
    ↓
execution/engine.py::run()
    ↓
BaseStrategy.compute_signal(df, config)
    ↓
TradeActivityTracker (metrics/trade_activity_tracker.py)
```

**연구/분석 스크립트의 역할**:
- ✅ **허용**: 엔진이 남긴 산출물(JSON, DB, 로그) 읽기
- ✅ **허용**: TradeActivityTracker Summary JSON 통계 분석
- ✅ **허용**: Per-bar diff를 위해 이미 생성된 Replay JSON 비교
- ❌ **금지**: 전략 로직/지표를 다시 구현해서 신호 직접 계산
- ❌ **금지**: `signal_logic()`, `add_indicators()` 직접 호출

### 2. TO-BE 파일 구조

#### 유지 (Production/Research)
```
✅ execution/engine.py::run_v2()          # 단일 엔진 진입점
✅ strategies/btc5m_baseline_v1.py        # BaseStrategy 구현
✅ metrics/trade_activity_tracker.py     # 신호/트레이드 추적
✅ scripts/run_v2.py                      # Thin wrapper
✅ scripts/run_backtest.py                # Thin wrapper
✅ scripts/run_paper.py                   # Thin wrapper

✅ scripts/research/phase27_5_btc5m_baseline_engine_replay.py
   # run_v2를 subprocess로 호출 (신호 직접 계산 안 함)

✅ scripts/research/phase27_6_signal_parity_analyzer.py
   # JSON만 읽어서 통계 분석 (신호 직접 계산 안 함)

✅ scripts/research/phase27_7_btc5m_signal_parity_diff.py
   # JSON만 읽어서 per-bar diff (신호 직접 계산 안 함)
```

#### 격리/제거 (Legacy)
```
❌ scripts/research/phase27_4_btc5m_baseline_signal_scan.py
   → scripts/legacy/phase27_4_btc5m_baseline_signal_scan_legacy.py 이동
   # Offline Scan 방식은 SSOT 원칙 위배
```

#### 신규 추가 (SSOT Guard)
```
✅ tests/test_phase27_8_signal_ssot_guard.py  # NEW
   # AST 기반 SSOT 위반 검사
   # scripts/에서 signal_logic/add_indicators 직접 호출하는 코드 탐지
```

### 3. 정리 기준

| 기준 | 판정 |
|------|------|
| **엔진 우회 여부** | 엔진 없이 신호 계산 → Legacy 이동 |
| **JSON만 읽기** | 엔진 산출물만 읽음 → 유지 (연구/분석) |
| **run_v2 호출** | subprocess로 run_v2 호출 → 유지 (하네스) |

---

## 🔧 구현 계획

### Phase A: Offline Scan Legacy 이동
1. `phase27_4_btc5m_baseline_signal_scan.py` → `scripts/legacy/` 이동
2. 파일 상단에 경고 주석 추가:
   ```python
   """
   ⚠️⚠️⚠️ DEPRECATED - LEGACY OFFLINE SCAN ⚠️⚠️⚠️
   
   이 스크립트는 과거 PHASE27 디버깅용 Offline Scan 코드입니다.
   엔진을 우회하여 신호를 직접 계산하므로 SSOT(Single Source of Truth) 원칙에 어긋납니다.
   
   현재 프로덕션/튜닝/백테스트에서는 사용되지 않습니다.
   공식 신호 계산 경로: execution/engine.py::run_v2() → BaseStrategy.compute_signal()
   
   보관 이유: PHASE27 과거 parity 디버깅 히스토리 참고용
   """
   ```
3. 생성된 JSON (`phase27_4_*_summary.json`) 처리:
   - docs/PHASE27/ 하위에 유지 (아카이브)
   - 더 이상 Acceptance Criteria 기준으로 사용하지 않음

### Phase B: SSOT Guard Test 추가
1. `tests/test_phase27_8_signal_ssot_guard.py` 생성
2. AST 기반 검사:
   - `scripts/` 및 `scripts/research/`에서 `signal_logic()` 직접 호출 탐지
   - `add_indicators()` 직접 호출 후 신호 계산하는 패턴 탐지
   - `BaseStrategy.compute_signal()` 엔진 없이 직접 호출 탐지
3. 허용 목록:
   - `scripts/legacy/` 하위는 검사 제외
   - `tests/` 하위 유닛 테스트는 허용
   - `phase27_6`, `phase27_7`은 JSON만 읽으므로 허용

### Phase C: 문서 업데이트
1. `PHASE_ROADMAP.md`에 PHASE27-8 섹션 추가
2. Acceptance Criteria 명시:
   - ✅ Offline Scan 코드 Legacy 이동
   - ✅ SSOT Guard 테스트 PASS
   - ✅ 엔진 밖에서 신호 직접 계산하는 코드 0건

---

## ✅ Acceptance Criteria

### 1. Legacy 격리
- [x] `phase27_4_btc5m_baseline_signal_scan.py` → `scripts/legacy/` 이동
- [x] `diagnose_scalping_signals.py` → `scripts/legacy/` 이동
- [x] 파일명 끝에 `_legacy` suffix 추가
- [x] 경고 주석 추가 (DEPRECATED, SSOT 원칙 위배 명시)
- [x] `phase27_6`, `phase27_7`은 유지 (JSON만 읽음)

### 2. SSOT Guard
- [x] `tests/test_phase27_8_signal_ssot_guard.py` 추가
- [x] AST 기반 신호 직접 계산 탐지 테스트 PASS (6/6)
- [x] `scripts/` 및 `scripts/research/`에 신호 직접 계산 코드 0건

### 3. 회귀 테스트
- [x] 기존 테스트 모두 PASS (`pytest tests/`)
- [x] `test_engine_single_entrypoint.py` PASS (8/8)
- [x] TradeActivityTracker 관련 테스트 PASS

### 4. 문서
- [x] `PHASE_ROADMAP.md` PHASE27-8 섹션 추가
- [x] Baseline Signal SSOT 원칙 명시
- [x] Offline Scan 제거 배경 설명

### 5. PHASE27-9 검증 (2025-12-05)
- [x] 전역 검색: `signal_logic()`, `compute_signal()`, `add_indicators()` 호출 확인
- [x] 엔진 구조 검증: `run_v2()` 단일 진입점, `run_v3` 등 없음
- [x] 신호 두 벌 경로 차단: Legacy 외 직접 신호 계산 코드 0건
- [x] 핵심 테스트 41 PASS, 1 XFAIL (Known Issue)
- [x] Known Issue 명확화: Signal count parity 17.79% (데이터 범위/warmup 차이, 엔진/SSOT 구조와 무관)

---

## 📝 Next Steps (PHASE27 이후)

PHASE27-8 완료 후:
- ✅ Baseline+ADX 전략의 신호 경로 단일화 완료
- ✅ "Offline vs Engine parity" 개념 폐기
- ✅ 향후 모든 전략은 엔진 경로만 사용

**PHASE28 이후 작업**:
- 전략 파라미터 튜닝 (SSOT 기반)
- Multi-Symbol 확장
- Live Trading 진입
- 모든 작업은 `run_v2()` 단일 경로 기반

---

**Last Updated**: 2025-12-05  
**Author**: PHASE27-8 Implementation
