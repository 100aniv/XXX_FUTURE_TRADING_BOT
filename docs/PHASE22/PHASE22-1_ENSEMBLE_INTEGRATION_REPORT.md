# PHASE22-1 Ensemble Integration Report – Single-Symbol Ensemble v1

**Date**: 2025-11-22  
**Status**: 🔄 **IN PROGRESS** (구현 진행 중)  
**Goal**: 4개 IMPLEMENTED 전략 (scalping, breakout, reversion, trend) 단일 심볼 통합 테스트

---

## 1. Objective

PHASE22-1의 핵심 목표는 **Ensemble v1 (4 IMPLEMENTED 전략)**을 단일 심볼 (BTCUSDT) 환경에서 통합하고, 30분 wall-clock Paper 테스트를 통해 인프라 안정성을 검증하는 것이다.

**Target Ensemble v1 구성**:
1. **scalping** (3m) - Core HF Momentum
2. **breakout** (15m) - Volatility Breakout
3. **reversion** (5m) - Mean Reversion
4. **trend** (1h) - Trend Follow

---

## 2. System Architecture

### 2.1 Ensemble Layer 위치

```
┌────────────────────────────────────────┐
│         Config (YML)                   │
│  - 4 strategies enabled                │
│  - Multi-TF feeds (3m/5m/15m/1h)      │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│    Ensemble Orchestration Layer        │
│  - EnsembleAggregator                  │
│  - ScoreEngine (Factors)               │
│  - Multi-Strategy Decision             │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│      Core Engine (DO-NOT-TOUCH)        │
│  - Portfolio Manager (SSOT)            │
│  - Risk Manager                        │
│  - Position Tracker                    │
│  - FlowGuardian                        │
└────────────────────────────────────────┘
```

### 2.2 핵심 설계 원칙

1. **DO-NOT-TOUCH 레이어**: execution/, portfolio_manager.py, risk_manager.py 등 코어 엔진은 수정하지 않음
2. **Config-Driven**: 전략 활성화/비활성화는 YAML config로 제어
3. **Single Engine**: Backtest/Paper/Live 공통 엔진 재사용
4. **SSOT 유지**: Portfolio 상태는 PortfolioManager 단일 소스

---

## 3. Configuration

### 3.1 Config 파일
**파일**: `configs/paper/phase22_ensemble_single_symbol.yml`

**주요 설정**:
```yaml
mode: paper
symbol: BTCUSDT
timeframe: 5m  # base timeframe

ensemble:
  enabled: true
  type: single_symbol_v1
  strategies:
    - scalping   # 3m
    - breakout   # 15m
    - reversion  # 5m
    - trend      # 1h

feed:
  type: binance_websocket
  timeframes:
    - 3m
    - 5m
    - 15m
    - 1h

paper:
  duration_mode: wall_clock
  duration_hours: 0.5  # 30분
```

### 3.2 개별 전략 파라미터
각 전략은 PHASE21 검증 완료 파라미터 사용:
- **Scalping**: entry_threshold=0.5, exit_threshold=0.3
- **Reversion**: RSI(14), BB(20,2.0)
- **Breakout**: ATR(14), breakout_mult=1.5
- **Trend**: EMA(12/26), ADX(14)

---

## 4. Test Scenarios

### 4.1 Unit Tests
**파일**: `tests/test_phase22_ensemble_single_symbol.py`

**테스트 케이스**:
1. ✅ Config 파일 존재 및 파싱
2. ✅ Ensemble 모드 활성화
3. ✅ 4개 전략 정의 확인
4. ✅ Feed timeframes 설정 (3m/5m/15m/1h)
5. ✅ Duration 30분, wall_clock 모드
6. ✅ 전략 모듈 import 가능
7. ✅ Ensemble 구조 (aggregator, score_engine) 존재

**결과**: 19 passed, 1 skipped

### 4.2 회귀 테스트
**파일**: `tests/test_phase19_3_aggregator.py`

**결과**: 7 passed (Ensemble Aggregator 기본 로직 검증)

### 4.3 30분 Paper Integration Test

**목표**:
- 30분 wall-clock 실시간 실행
- 4개 전략 모두 활성화 상태
- 최소 2개 이상 전략에서 진입 시도
- 치명적 에러 없이 정상 종료

**실행 명령**:
```bash
python scripts/run_phase22_ensemble_single_symbol.py \
    --config configs/paper/phase22_ensemble_single_symbol.yml \
    --duration-hours 0.5
```

**현재 상태**: 🔄 스크립트 수정 중 (engine 호출 방식 조정 필요)

---

## 5. Implementation Progress

### 5.1 완료된 작업 ✅
1. Config 파일 작성 완료
   - `configs/paper/phase22_ensemble_single_symbol.yml`
   - 4개 전략 정의, multi-TF feeds, 30분 duration

2. 단위 테스트 작성 및 통과
   - `tests/test_phase22_ensemble_single_symbol.py`
   - 19/20 tests passed

3. 실행 스크립트 초안 작성
   - `scripts/run_phase22_ensemble_single_symbol.py`
   - CLI 인자 파싱, config 로딩 구현

### 5.2 진행 중인 작업 🔄
1. **실행 스크립트 완성** (현재 작업)
   - Issue: main() 함수 호출 방식 문제
   - Solution: run_paper.py 패턴으로 전환 (어댑터 + engine.run() 직접 호출)

2. **30분 Paper 테스트 실행** (대기 중)
   - 스크립트 완성 후 즉시 실행
   - 실시간 모니터링 필수

### 5.3 대기 중인 작업 ⏳
1. 테스트 결과 분석
2. 트레이드 통계 수집
3. 문서 업데이트 (이 리포트 완성)
4. PHASE_ROADMAP 업데이트
5. Git 커밋

---

## 6. Issues & Solutions

### Issue 1: main() 함수 시그니처 불일치
**문제**: `main()` 함수가 config 인자를 받지 않음
```python
# 현재 (오류)
from main import main as engine_main
engine_main(config=cfg)  # TypeError

# 해결책 (run_paper.py 패턴)
from execution import engine
from execution.adapters import create_adapters
from strategies import load_strategies

feed, broker, clock = create_adapters(mode='paper', symbols=[symbol], config=cfg)
strategies = load_strategies(config=cfg)
engine.run(feed, broker, clock, strategies, ensemble_module=None, config=cfg)
```

**상태**: 🔄 수정 중

### Issue 2: Logging File Permission Error
**문제**: application.log 파일 회전 시 PermissionError
**원인**: 다른 프로세스가 로그 파일 사용 중
**해결책**: 기존 프로세스 종료 또는 로그 파일 경로 변경
**상태**: ⚠️ 재현 가능, 실행 전 확인 필요

---

## 7. Acceptance Criteria - Current Status

| Criteria | Status | Notes |
|----------|--------|-------|
| Config 파일 작성 (4 strategies) | ✅ PASS | phase22_ensemble_single_symbol.yml |
| 실행 스크립트 존재 | ✅ PASS | run_phase22_ensemble_single_symbol.py (수정 중) |
| 단위 테스트 PASS | ✅ PASS | 19/20 tests passed |
| 회귀 테스트 PASS | ✅ PASS | Ensemble aggregator 7/7 passed |
| 30분 Paper 실행 정상 종료 | ⏳ PENDING | 스크립트 수정 완료 후 실행 |
| 2개 이상 전략 진입 시도 | ⏳ PENDING | Paper 테스트 후 확인 |
| 치명적 에러 없음 | ⏳ PENDING | Paper 테스트 후 확인 |
| 문서 작성 | 🔄 IN PROGRESS | 이 리포트 |
| ROADMAP 업데이트 | ⏳ PENDING | Paper 테스트 완료 후 |

**Current Overall Status**: 🔄 **IN PROGRESS** (50% complete)

---

## 8. Next Steps

### Immediate (진행 중)
1. **실행 스크립트 완성** (최우선)
   - run_paper.py 패턴으로 재작성
   - adapter, strategies, engine.run() 호출 구조

2. **5분 Smoke Test** (스크립트 완성 후)
   - 구조 검증용 짧은 테스트
   - 에러 즉시 감지 및 수정

3. **30분 Full Paper Test**
   - Acceptance Criteria 검증
   - 실시간 로그 모니터링

### After Test Completion
1. 결과 분석 및 통계 수집
2. 이 리포트 업데이트 (결과 섹션 추가)
3. PHASE_ROADMAP.md 업데이트
4. Git 커밋

---

## 9. References

**Config**:
- `configs/paper/phase22_ensemble_single_symbol.yml`

**Scripts**:
- `scripts/run_phase22_ensemble_single_symbol.py`
- `scripts/run_paper.py` (reference)

**Tests**:
- `tests/test_phase22_ensemble_single_symbol.py`
- `tests/test_phase19_3_aggregator.py`

**Docs**:
- `PHASE_ROADMAP.md` (PHASE22-1 section)
- `docs/PHASE22/PHASE22-0_STRATEGY_POOL.md`

---

**Report Status**: 🔄 DRAFT (Paper 테스트 완료 후 FINAL)  
**Last Updated**: 2025-11-22 01:30 KST  
**Next Update**: Paper 테스트 완료 시
