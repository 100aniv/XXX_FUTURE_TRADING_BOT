# PHASE29-3: V3 전략 폐기 및 재설계 준비 완료 보고서

## 📋 Document Control

| 항목 | 내용 |
|------|------|
| **PHASE** | PHASE29-3 |
| **작성일** | 2025-12-10 |
| **상태** | ✅ **COMPLETE** |
| **소요 시간** | 1 session |
| **판정** | ✅ **PASS** - V3 폐기 작업 완료, 재설계 준비 완료 |

---

## 🎯 작업 목표

btc5m_baseline_v3 전략을 공식적으로 DEPRECATED 상태로 전환하고,  
다음 전략 설계를 위한 기반 문서를 작성한다.

---

## ✅ 완료 내역

### 1. V3 전략 DEPRECATED 처리 (코드 수정)

#### 1-1. `strategies/btc5m_baseline_v3.py` 수정
- ✅ 파일 상단 docstring에 DEPRECATED 표시 추가
- ✅ 폐기 이유, Deprecation Details 명시
- ✅ 클래스 내부에 `deprecated=True` flag 추가
- ✅ `deprecation_reason` 속성 추가
- ✅ metadata에 `[DEPRECATED]` 표시 및 `version="3.0.0-deprecated"` 설정

**변경 내용**:
```python
# Docstring
⚠️ STRATEGY STATUS: DEPRECATED
⚠️ REASON: PHASE29-2C-R — Structural signal deficiency.
⚠️ DO NOT USE FOR BACKTEST, PAPER, OR LIVE.

# Class
def __init__(self, config: dict):
    super().__init__(config)
    self.deprecated = True
    self.deprecation_reason = "PHASE29-2C-R: Structural signal deficiency. Trade count 17/80-240 (7.1~21.3% achievement rate)."

@property
def metadata(self) -> StrategyMetadata:
    return StrategyMetadata(
        strategy_name='btc5m_baseline_v3',
        version='3.0.0-deprecated',
        description='[DEPRECATED] BTC 5m Regime-Aware Baseline V3...'
    )
```

### 2. 전략 Auto-Discovery에서 V3 제외

#### 2-1. `strategies/__init__.py` 수정
- ✅ 단일 전략 모드: deprecated 전략 로드 시 빈 딕셔너리 반환 (로드 중단)
- ✅ 앙상블 모드: deprecated 전략 자동 스킵 (continue)

**변경 내용**:
```python
# 단일 전략 모드
if hasattr(instance, 'deprecated') and instance.deprecated:
    logger.warning(f"⚠️  [PHASE29-3] 전략 '{selector}'는 DEPRECATED 상태입니다.")
    logger.warning(f"    이유: {getattr(instance, 'deprecation_reason', 'No reason provided')}")
    logger.warning(f"    이 전략은 로드되지 않습니다. 다른 전략을 선택하세요.")
    return {}  # 빈 딕셔너리 반환으로 전략 로드 중단

# 앙상블 모드
if hasattr(instance, 'deprecated') and instance.deprecated:
    logger.warning(f"⚠️  [PHASE29-3] 전략 '{name}'는 DEPRECATED 상태로 앙상블에서 제외됩니다.")
    logger.warning(f"    이유: {getattr(instance, 'deprecation_reason', 'No reason provided')}")
    continue  # 이 전략을 스킵하고 다음 전략으로
```

### 3. Config/튜닝에서 V3 DEPRECATED 표시

#### 3-1. `configs/tuning/btc5m_baseline_v3_paramspace.yml` 수정
- ✅ 파일 상단에 DEPRECATED 경고 추가
- ✅ 실제 결과 (FAIL) 명시

**변경 내용**:
```yaml
# ========================================
# PHASE29-1: btc5m_baseline_v3 Parameter Space
# ========================================
# ⚠️ STATUS: DEPRECATED (PHASE29-3)
# ⚠️ REASON: Strategy btc5m_baseline_v3 deprecated due to structural signal deficiency
# ⚠️ DO NOT USE FOR TUNING
#
# 실제 결과: FAIL (PHASE29-2C: 17/80-240 trades, 7.1~21.3% achievement rate)
```

### 4. Deprecation 테스트 작성 및 실행

#### 4-1. `tests/test_phase29_3_v3_deprecation.py` 작성
- ✅ 테스트 1: V3 클래스에 deprecated flag 존재 확인
- ✅ 테스트 2: 단일 전략 모드에서 로드 거부 확인
- ✅ 테스트 3: 앙상블 모드에서 자동 제외 확인
- ✅ 테스트 4: metadata에 DEPRECATED 표시 확인

**테스트 결과**: ✅ **4/4 PASS**
```
tests/test_phase29_3_v3_deprecation.py::test_v3_has_deprecated_flag PASSED
tests/test_phase29_3_v3_deprecation.py::test_v3_rejected_in_single_strategy_mode PASSED
tests/test_phase29_3_v3_deprecation.py::test_v3_excluded_from_ensemble PASSED
tests/test_phase29_3_v3_deprecation.py::test_v3_metadata_deprecated_marker PASSED
```

### 5. 문서 업데이트

#### 5-1. `docs/PHASE29/PHASE29_2C_BTC5M_BASELINE_V3_MONTH_BACKTEST_KR.md` 업데이트
- ✅ PHASE29-3 폐기 결정 섹션 추가
- ✅ 폐기 근거, 폐기 작업, 다음 단계 명시

#### 5-2. `PHASE_ROADMAP.md` 업데이트
- ✅ PHASE29-3 섹션 추가 (COMPLETE 상태)
- ✅ 폐기 근거, 완료 내역, 테스트 결과, Artifacts 명시
- ✅ PHASE29-4 (튜닝) → SKIPPED 처리

#### 5-3. `docs/PHASE29/PHASE29_3_STRATEGY_REDESIGN_TODO.md` 작성
- ✅ V3 실패 원인 분석
- ✅ 다음 전략 설계 원칙
- ✅ 3가지 설계 옵션 제시 (OR 기반, V2 복귀, Hybrid)
- ✅ PHASE29-3.1 다음 단계 명시
- ✅ 금지 사항 정의

---

## 📊 폐기 근거 요약

### V3 전략 성능 (PHASE29-2C-R)
- **1개월 백테스트**: 17건/80-240건 (달성률 7.1~21.3%)
- **핵심 문제**: AND 로직 과잉 결합 + 엄격한 Threshold → 교집합 극소
- **완화 시도**: Scenario A+ (최대 완화)로도 목표 미달
- **Config 버그**: 파라미터 전달 수정 전후 거래 건수 동일 (17건) → 구조적 문제 확인

### 인프라 검증 (PHASE29-2C-R)
- ✅ Config 파라미터 전달: 정상 작동
- ✅ Summary JSON 생성: 정상 작동
- ✅ 엔진/Guard/SSOT: 모두 정상

### 결론
**인프라는 정상, 전략 로직 자체가 문제** → 전략 폐기 결정

---

## 📁 산출물

### 코드 수정
1. `strategies/btc5m_baseline_v3.py` (DEPRECATED 표시)
2. `strategies/__init__.py` (Auto-Discovery 자동 제외 로직)
3. `configs/tuning/btc5m_baseline_v3_paramspace.yml` (DEPRECATED 표시)

### 테스트
4. `tests/test_phase29_3_v3_deprecation.py` (4/4 PASS)

### 문서
5. `docs/PHASE29/PHASE29_2C_BTC5M_BASELINE_V3_MONTH_BACKTEST_KR.md` (폐기 결정 추가)
6. `PHASE_ROADMAP.md` (PHASE29-3 완료 기록)
7. `docs/PHASE29/PHASE29_3_STRATEGY_REDESIGN_TODO.md` (재설계 가이드)
8. `docs/PHASE29/PHASE29_3_COMPLETION_REPORT.md` (본 문서)

---

## 🧪 테스트 결과

### pytest 실행
```bash
pytest tests/test_phase29_3_v3_deprecation.py -v -s
```

**결과**: ✅ **4/4 PASS**

- ✅ `test_v3_has_deprecated_flag`: deprecated flag 및 reason 확인
- ✅ `test_v3_rejected_in_single_strategy_mode`: 단일 전략 모드 로드 거부
- ✅ `test_v3_excluded_from_ensemble`: 앙상블에서 자동 제외 (14개 전략 중 V3만 제외)
- ✅ `test_v3_metadata_deprecated_marker`: metadata DEPRECATED 표시 확인

---

## 🎯 다음 단계

### PHASE29-3.1: 새로운 전략 설계

**참고 문서**: `docs/PHASE29/PHASE29_3_STRATEGY_REDESIGN_TODO.md`

**권장 접근**: Hybrid (Regime별 OR + 가중치 점수 + Multi-TP)

**Task**:
1. 설계 문서 작성
2. 스켈레톤 코드 구현 (`strategies/btc5m_baseline_v4.py` 또는 새 이름)
3. 1일 스모크 백테스트 (신호 발생 확인)
4. 1주일 백테스트 (20~60건 달성 Gate)
5. 1개월 백테스트 (80~240건 + Win Rate ≥ 45%)

**Gate**: 1주일 백테스트에서 20건 미달 시 즉시 설계 재검토

---

## 🚀 최종 판정

**PHASE29-3 Status**: ✅ **COMPLETE**

**완료 내역**:
- ✅ V3 전략 공식 폐기 (코드 + 문서)
- ✅ Auto-Discovery 자동 제외 로직 추가
- ✅ Deprecation 테스트 4/4 PASS
- ✅ 재설계 가이드 문서 작성

**다음 PHASE**: PHASE29-3.1 (새로운 전략 설계)

---

**작성 완료**: 2025-12-10  
**작성자**: Future Trading Bot Team  
**다음 문서**: `docs/PHASE29/PHASE29_3_1_NEW_STRATEGY_DESIGN.md` (예정)
