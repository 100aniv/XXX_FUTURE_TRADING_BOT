# PHASE_ROADMAP.md 수동 업데이트 가이드

PHASE23 섹션을 다음과 같이 수정해주세요:

## 변경 위치: Line 648-709

## 현재 (잘못됨):
- PHASE23 섹션에 PHASE22의 sub-phases (22-0, 22-1, 22-2, 22-3, 22-4)가 포함되어 있음

## 수정 내용:

```markdown
🧩 **PHASE23** – 전략·앙상블 TO-BE 재설계 블록 🔄 **IN PROGRESS**

**상태**: 🔄 **IN PROGRESS** (2025-11-29 시작, PHASE23-1 완료 2025-12-01)

**목적**: 5개 전략 패밀리 기반 단일 엔진 중심 아키텍처 확립 및 Ensemble v2 Score 구조 설계

**배경**:
- PHASE22-4에서 config propagation runtime 이슈 발생 → 근본 원인: script-level orchestration 문제
- 해결 방향: Thin script wrapper + Single-engine-centric architecture
- 목표: PHASE22-4 이슈를 아키텍처 레벨에서 해결하고 5개 전략 통합 준비

**Sub-phases**:
- **23-0: ✅ TO-BE Architecture V2 문서화 (COMPLETE - 2025-11-29)**
  - **산출물**: `docs/PHASE23/PHASE23-0_ARCHITECTURE_TOBE_V2.md`, `ENSEMBLE_STRATEGY_TOBE_V2.md`
  - **주요 내용**: PHASE22-4 근본 원인 분석, TO-BE Principles, 5-family ensemble
  - **상태**: ✅ COMPLETE
  
- **23-1: ✅ Script Layer Cleanup & Engine Refactor (COMPLETE - 2025-12-01)**
  - **목표**: PHASE22-4 config propagation 이슈 해결 (architectural refactoring)
  - **Tasks**: 
    - ✅ Create `scripts/run_v2.py` (thin wrapper, 97 lines)
    - ✅ Add `engine.run_v2()` entry point
    - ✅ Move load_strategies() call from script to engine
    - ✅ 30min paper smoke test
  - **Acceptance Criteria**: ✅ ALL PASS
    - ✅ RSI 45/55 correctly propagated (NOT 30/70 defaults)
    - ✅ Unit tests 6/6 PASS
    - ✅ Actual trade executed (1 entry + 1 TP1 exit)
  - **산출물**: `docs/PHASE23/PHASE23-1_ENGINE_ENTRYPOINT_REFACTOR.md`
  - **코드**: `scripts/run_v2.py`, `execution/engine.py` (run_v2 추가)
  - **상태**: ✅ COMPLETE
  
- **23-2: 🟦 Strategy Interface Unification (PLANNED)**
  - Duration: 3-5h, scalping_v3 → BaseStrategy 마이그레이션, 1H paper test
  
- **23-3: 🟦 Individual Strategy Validation (PLANNED)**
  - Duration: 4-6h, 각 전략 3H backtest, rough param tuning
  
- **23-4: 🟦 Ensemble Integration Test (PLANNED)**
  - Duration: 2-3h, 5개 전략 3H ensemble paper test

**진입 조건**: PHASE22-4 PARTIAL 완료 (code-level fix done, runtime integration deferred)

**퇴출 조건**: 
- ✅ TO-BE 아키텍처 V2 문서화 (PHASE23-0)
- ✅ Config propagation 정상 작동 (PHASE23-1)
- [ ] 5개 전략 인터페이스 통일 (PHASE23-2)
- [ ] 각 전략 개별 검증 PASS (PHASE23-3)
- [ ] 앙상블 통합 테스트 PASS (PHASE23-4)
```

---

**중요**: Line 664-702의 잘못된 "22-0" ~ "22-4" sub-phases를 모두 삭제하고 위의 "23-0" ~ "23-4"로 교체해야 합니다.
