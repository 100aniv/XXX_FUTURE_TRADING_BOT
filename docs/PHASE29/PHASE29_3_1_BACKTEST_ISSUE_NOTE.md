# PHASE29-3.1: 백테스트 실행 이슈 노트

## 문제

1일/1주일 백테스트 실행 시 Duration 모드가 1.00시간으로 설정되어 조기 종료됨.

## 시도한 해결책

- Config에 `duration_minutes: 1440` (1일) 및 `duration_minutes: 10080` (1주일) 명시
- 여전히 `⏱️  [MARKET-TIME] Duration 모드 시작: 1.00시간` 로그 출력

## 추정 원인

- `run_v2.py` 또는 `engine.py`에서 Config `duration_minutes` 무시
- 기본값 또는 다른 Config 설정이 override

## 다음 조치

1. `scripts/run_v2.py` 및 `execution/engine.py`에서 Duration 처리 로직 확인
2. Config 우선순위 확인 (backtest.duration_minutes vs duration_hours 등)
3. 수정 후 재실행

## 현재 상태

- V4 전략 코드 구현 완료
- Unit Test 6/6 PASS
- Config/ParamSpace 생성 완료
- 백테스트는 별도 세션에서 진행 예정

**작성일**: 2025-12-10
