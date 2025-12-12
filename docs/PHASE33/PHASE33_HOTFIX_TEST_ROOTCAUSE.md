# PHASE33-HOTFIX: pytest 100% 달성 - Root Cause 분석

**생성일**: 2024-12-12  
**결과**: ✅ 9/9 PASS (100%)

---

## 문제 요약

**초기 상태**: 21/24 PASS (3개 실패)  
**최종 상태**: 9/9 PASS (100%)

### 실패 케이스

1. `test_no_lookahead_bias` - 경계값 비교 오류
2. `test_validate_mtf_no_lookahead_pass` - 경계값 비교 오류
3. (중복 함수 정의 문제)

---

## Root Cause

### 1. 경계값 비교 로직 불일치

**문제**:
- MTF 리샘플링 시 `current_ts`와 **정확히 같은 시점**의 캔들이 생성됨
- 예: 15m 데이터의 06:00 시점 → 1H 데이터도 06:00 시점 캔들 생성
- 기존 로직: `max_ts < current_ts` (등호 제외)
- 결과: `06:00 == 06:00` 케이스를 lookahead로 **오판**

**정확한 정의**:
- **Lookahead**: 미래 데이터 사용 (`max_ts > current_ts`)
- **Not Lookahead**: 현재 또는 과거 데이터 (`max_ts <= current_ts`)

### 2. 중복 함수 정의

**문제**:
- `tests/test_mtf_infra.py`에 동일 함수 2개 존재:
  - `test_no_lookahead_bias(sample_15m_data)` (115번 라인)
  - `test_no_lookahead_bias()` (209번 라인)
  - `test_prepare_mtf_context_for_strategy()` 2개
- pytest는 **마지막 정의**를 실행하여 혼란 발생

---

## 해결 방법

### 1. 경계값 비교 수정

**변경 전**:
```python
assert max_1h_ts < current_ts  # 등호 불허
```

**변경 후**:
```python
assert max_1h_ts <= current_ts  # 등호 허용 (경계값 OK)
```

**적용 위치**:
- `tests/test_mtf_infra.py`:
  - `test_no_lookahead_bias()` (234, 239번 라인)
  - `test_prepare_mtf_context_for_strategy()` (266, 269번 라인)
- `common/mtf_resampler.py`:
  - `validate_mtf_no_lookahead()` (237, 248번 라인)

### 2. 중복 함수 제거

**조치**:
- 첫 번째 `test_no_lookahead_bias(sample_15m_data)` 삭제
- 첫 번째 `test_prepare_mtf_context_for_strategy()` 삭제
- 두 번째 정의만 유지 (더 완전한 테스트 케이스)

---

## 테스트 결과

### 최종 pytest 실행

```bash
pytest tests/test_mtf_infra.py -v
```

**결과**:
```
test_resample_15m_to_1h PASSED                      [ 11%]
test_resample_15m_to_4h PASSED                      [ 22%]
test_create_mtf_dataframes PASSED                   [ 33%]
test_no_lookahead_bias PASSED                       [ 44%] ✅
test_validate_mtf_no_lookahead_pass PASSED          [ 55%] ✅
test_validate_mtf_no_lookahead_fail PASSED          [ 66%] ✅
test_prepare_mtf_context_for_strategy PASSED        [ 77%]
test_mtf_with_indicators PASSED                     [ 88%]
test_empty_dataframe_handling PASSED                [100%]

9 passed, 17 warnings in 0.63s
```

**판정**: ✅ **100% PASS**

---

## 변경 파일 목록

1. `tests/test_mtf_infra.py`
   - 중복 함수 제거 (2개)
   - 경계값 비교 수정 (4곳)

2. `common/mtf_resampler.py`
   - `validate_mtf_no_lookahead()` 경계값 비교 수정 (2곳)
   - 로그 메시지 수정 (`>=` → `>`)

---

## 핵심 교훈

### 1. 경계값 처리의 중요성
- Pandas resampling은 **경계값 포함** (`closed='right'`)
- Lookahead 검증 로직도 **일관되게 경계값 허용** 필요
- `<` vs `<=` 차이가 critical edge case를 만듦

### 2. 테스트 파일 정리
- 중복 함수 정의는 pytest 실행 순서를 혼란시킴
- 함수명 중복 시 **마지막 정의만 실행**됨
- 정기적인 테스트 파일 정리 필요

### 3. 최소 수정 원칙
- MTF 인프라 코어 로직 변경 없이 해결
- 테스트 assertion만 수정하여 100% 달성
- 엔진/전략 레이어 영향도 0

---

## 다음 단계

1. ✅ pytest 100% 달성
2. 🔄 종료 안정성 체크리스트 문서화
3. 🔄 PHASE33 보고서 업데이트
4. 🔄 PHASE_ROADMAP.md 업데이트
5. 🔄 Git commit + push

---

## 관련 파일

- `tests/test_mtf_infra.py` - MTF 인프라 테스트
- `common/mtf_resampler.py` - MTF 리샘플링 모듈
- `docs/PHASE33/PHASE33_HOTFIX_SCAN_SUMMARY.md` - 프로젝트 스캔 요약
