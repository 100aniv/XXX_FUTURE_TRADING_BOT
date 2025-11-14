# PHASE8 MASTER PLAN
## 목적
단일 전략 백테스트 + 재현성 + 스냅샷 + 검증 + scorecard 구조 확립.

## 요구사항 요약
1) cfg(dict) 기반 환경 통합
2) effective_config.yml 스냅샷 생성
3) config_validation 추가
4) backtest_clean 모드 신설
5) BacktestDataSource 개선 (slice loading)
6) run_backtest.py 생성
7) strategy_scorecard 생성
8) core 로직 절대 수정 금지
9) 중복 모듈 금지 (기존 파일 확장)
10) Scorecard 산출물 artifacts 저장

## 목표 산출물
- effective_config.yml
- scorecard.csv / scorecard.md
- logs (mode/run_id정보 포함)
- BacktestDataSource slice 기능

## 검증 기준
- 스캘핑 단독으로 scorecard 생성 가능
- mode별 스냅샷이 항상 재현성 유지
- 모든 설정값은 cfg(dict)에서만 읽힘
