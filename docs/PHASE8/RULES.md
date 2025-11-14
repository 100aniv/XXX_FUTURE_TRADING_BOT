# RULES (PHASE8)

## 1. 금지 영역
- reports/ 는 legacy → 수정/생성 절대 금지
- ensemble 로직 변경 금지 (Phase9 이전 금지)
- core(engine/broker/risk) 리팩토링 금지
- 전략 파일 수정 금지
- Score Fusion / Voting 변경 금지

## 2. 반드시 지킬 것
- 모든 환경값은 config(dict)에서만 읽는다
- 병합 순서: base.yml → modes/{mode}.yml → active/current.yml → CLI/ENV
- effective_config.yml 스냅샷 필수 저장
- 로그 헤더에 mode / fees / slippage / run_id 표기
- backtest_clean 모드에서만 테스트 (Phase8 전체)

## 3. 폴더 구조 규칙
- analytics/ 에 모든 reporting/score 기능 통합
- scorecard = analytics/scorecard/*
- legacy reports/ 는 사용 금지

## 4. PHASE8 작업 범위
- config_loader / config_validation
- backtest_clean 설정
- run_backtest.py
- analytics 기반 scorecard 생성
- artifacts 출력

## 5. 실행 테스트 규칙
- 단일 전략만
- Winrate/SR/MaxDD 기준 충족해야 다음 단계 이동
