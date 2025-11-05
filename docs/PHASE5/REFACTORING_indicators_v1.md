# Indicators 모듈 리팩토링 계획 (v1)

**최종 업데이트**: 2025-11-02 20:00
**상태**: ✅ PR 4 구현 완료 (인터페이스 표준화, Contract 테스트 12개)

---

## 목적
- 모든 전략/시그널이 재사용하는 지표 계산을 표준화하고 성능/정확성을 보장
- 컬럼 명세/결측 처리/타임존/윈도우 경계 등 불변 규칙을 문서화

## 현행
- 위치: `indicators/core_indicators.py`
- 역할: SMA/EMA/RSI/ATR/Bollinger 등 핵심 지표 계산
- 의존: pandas/numpy, 입력 DataFrame 컬럼 요구(`open, high, low, close, volume, time`)

## 인터페이스 규약(제안)
- 입력: `df: pd.DataFrame`, 최소 컬럼: `time, open, high, low, close`
- 출력: 입력 df와 동일 인덱스, 지표 컬럼 추가한 DataFrame 반환(원본 불변)
- 규칙:
  - NaN 전파: 초기 구간은 NaN 허용, 시그널단에서 `min_bars_for_signal`로 제어
  - 타임존: 입력 time은 UTC 기준, tz-naive 허용(문서화)
  - 캐시: 동일 파라미터 호출 시 재계산 방지(옵션)

## 데이터 흐름
```mermaid
flowchart LR
  DC[Collector] --> IN[Indicators]
  IN --> SG[Signals]
  SG --> ST[Strategies]
```

## 리팩토링 과제(To‑Do)
1) 컬럼 스키마/타임존/NaN 정책 문서화 및 유닛 테스트 추가
2) 지표 함수 시그니처 통일(signatures.md, 내부 참조)
3) 반복 호출 캐시/백테스트 구간 슬라이싱 최적화(선택)
4) 벡터화 점검: 루프 제거 및 연산 축소

## 테스트
- 각 지표에 대해 경계값/단위/NaN 구간 단위 테스트
- 슬라이스 재현성(동일 입력 → 동일 출력) 해시 비교

## 참고
- Signals: `REFACTORING_signals_v1.md`
- Strategies: `REFACTORING_strategies_v1.md`
- 아키텍처: `REFACTORING_문서아키텍처.md`

---

## ✅ PR 4 구현 완료 상태 (2025-11-02)

### 구현된 항목

1. **인터페이스 계약 문서화 (44줄 추가)**
   ```
   indicators/core_indicators.py:
   - 입력: 필수 컬럼, 타임존, 정렬, 결측치 정책
   - 출력: 불변성, 인덱스 유지, NaN 전파 규칙
   - 최소 데이터: 각 지표별 요구사항 명시
   - NaN 처리: 3단계 정책 (계산/시그널/전략)
   ```

2. **Contract 테스트 (212줄)**
   ```
   tests/unit/test_indicators_contract.py:
   - TestIndicatorsContract (9개)
     * EMA 최소 데이터
     * SMA NaN 전파
     * RSI 최소 데이터
     * MACD 출력 스키마
     * BB 출력 스키마
     * ATR 최소 데이터
     * 불변성
     * add_indicators 완전성
     * regime 출력
   - TestIndicatorsEdgeCases (3개)
     * 빈 DataFrame
     * 불충분한 데이터
     * 거래량 0
   ```

3. **테스트 결과**
   - Contract 테스트: 12/12 통과 ✅
   - 회귀 테스트: FlowGuardian 8/8 유지 ✅
   - 실행 시간: 0.39초

### 수용 기준 달성

| 기준 | 상태 | 비고 |
|------|------|------|
| 인터페이스 계약 문서화 | ✅ | 44줄 docstring |
| 타입힌트 강화 | ✅ | 모든 함수 명시 |
| NaN 정책 명시 | ✅ | 3단계 정책 |
| 최소 데이터 명시 | ✅ | 지표별 요구사항 |
| Contract 테스트 | ✅ | 12개 통과 |
| 회귀 테스트 | ✅ | 8/8 유지 |
| 코드 변경 | ✅ | 0줄 (문서만) |

### 변경 통계
- **Docstring**: +44줄
- **테스트**: +212줄
- **코드 변경**: 0줄
- **총 증가**: 256줄

### 기술 세부사항

**설계 원칙**:
1. **최소 변경**: 로직 변경 없이 문서화만
2. **명시적 계약**: 입력/출력/NaN 정책 명확화
3. **테스트 우선**: Contract 기반 검증
4. **하위 호환성**: 기존 코드 100% 호환

**NaN 처리 정책**:
- **지표 계산**: NaN 전파 허용 (pandas rolling 기본)
- **시그널 생성**: `dropna()` 또는 `min_bars_for_signal` 체크
- **전략 실행**: NaN 행 건너뜀

**최소 데이터 요구사항**:
```python
sma(length=20)  # 20개 행
ema(length=20)  # 20개 행 (2*20 권장)
rsi(length=14)  # 15개 행
macd(12,26,9)   # 35개 행 (slow+signal)
atr(length=14)  # 15개 행 (shift 고려)
```

### 다음 단계
- PR 5: Execution 큐/백프레셔 지표 노출

---
