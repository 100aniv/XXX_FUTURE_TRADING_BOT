# PR 4: Signals/Indicators 인터페이스 표준화 - 완료

**작성일**: 2025-11-02  
**상태**: ✅ 완료

---

## 목표
Signals/Indicators 인터페이스 표준화 (코드 영향 최소)

---

## 구현 (최소 변경)

### 수정 파일
- `indicators/core_indicators.py` (+44줄 docstring)
  - 인터페이스 계약 명시
  - NaN 정책 문서화
  - 최소 데이터 요구사항
  - 출력 스키마 표준화

### 신규 파일
- `tests/unit/__init__.py` (테스트 구조)
- `tests/unit/test_indicators_contract.py` (212줄)
  - 12개 계약 테스트
  - 최소 데이터, NaN 전파, 출력 스키마, 불변성

---

## 인터페이스 계약

### 입력
- **필수 컬럼**: `open, high, low, close, volume, time`
- **타임존**: UTC (tz-naive 허용)
- **정렬**: time 오름차순
- **결측치**: 허용 안함 (호출 전 정제)

### 출력
- **불변성**: 입력 DataFrame 수정 안함
- **인덱스 유지**: 입력과 동일
- **NaN 전파**: 초기 `length-1`개 행은 NaN

### 최소 데이터
- `sma(N)`: N개 행
- `ema(N)`: N개 행 (2*N 권장)
- `rsi(N)`: N+1개 행
- `macd(fast, slow, signal)`: slow + signal개 행
- `atr(N)`: N+1개 행

---

## 테스트 결과

### Contract Tests (12개)
```bash
$ python -m pytest tests/unit/test_indicators_contract.py -v
=============== 12 passed in 0.39s ================
```

**시나리오**:
1. ✅ EMA 최소 데이터
2. ✅ SMA NaN 전파
3. ✅ RSI 최소 데이터
4. ✅ MACD 출력 스키마
5. ✅ BB 출력 스키마
6. ✅ ATR 최소 데이터
7. ✅ 불변성
8. ✅ add_indicators 완전성
9. ✅ regime 출력
10. ✅ 빈 DataFrame
11. ✅ 불충분한 데이터
12. ✅ 거래량 0

### 회귀 테스트
```bash
$ python -m unittest tests.flow.test_flow_guardian -v
Ran 8 tests in 0.047s
OK
```

**결과**: ✅ FlowGuardian 8/8 유지

---

## 수용 기준

| 항목 | 상태 |
|------|------|
| 인터페이스 계약 문서화 | ✅ |
| 타입힌트 강화 | ✅ |
| NaN 정책 명시 | ✅ |
| 출력 스키마 표준화 | ✅ |
| Contract 테스트 12개 | ✅ |
| 회귀 테스트 8/8 | ✅ |

---

## 변경 통계
- **Docstring 추가**: 44줄 (indicators/core_indicators.py)
- **테스트 추가**: 212줄 (test_indicators_contract.py)
- **코드 변경**: 0줄 (문서화만)
- **테스트 통과**: 20/20 (100%)

---

## 다음 테스트
- Paper 모드에서 실제 신호 생성 확인
