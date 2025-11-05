@echo off
REM 문서 파일 정리 스크립트

echo 문서 파일 정리 중...

REM Setup 카테고리
move docs\TELEGRAM_SETUP.md docs\setup\
move docs\SETUP_3BOTS.md docs\setup\
move docs\DEPLOYMENT_CHECKLIST.md docs\setup\

REM Strategy 카테고리
move docs\6_STRATEGY_SYSTEM.md docs\strategy\
move docs\ENSEMBLE_6_STRATEGIES.md docs\strategy\
move docs\ENSEMBLE_ARCHITECTURE.md docs\strategy\
move docs\ENSEMBLE_DECISION_LOGIC.md docs\strategy\
move docs\STRATEGY_GUIDE.md docs\strategy\
move docs\EXTREME_LEVERAGE_STRATEGY.md docs\strategy\
move docs\POSITION_SIZING.md docs\strategy\
move docs\DAILY_TARGET_GUIDE.md docs\strategy\

REM Backtest 카테고리
move docs\BACKTEST_QUICKSTART.md docs\backtest\
move docs\BACKTEST_STRATEGY.md docs\backtest\

REM Implementation 카테고리
move docs\IMPLEMENTATION_ROADMAP.md docs\implementation\
move docs\ROADMAP_TO_AUTOMATION.md docs\implementation\
move docs\4DAY_IMPLEMENTATION_PLAN.md docs\implementation\

REM Architecture 카테고리
move docs\TRADING_EXECUTOR.md docs\architecture\
move docs\TRADING_DECISION.md docs\architecture\
move docs\TRADING_BOT_SPEC.md docs\architecture\
move docs\REFACTORING.md docs\architecture\
move docs\DB_SCHEMA_GUIDE.md docs\architecture\

REM Deployment 카테고리
move docs\DOCKER_DEPLOYMENT.md docs\deployment\

REM Reference 카테고리
move docs\TELEGRAM_MESSAGE_DESIGN.md docs\reference\
move docs\BINANCE_CONNECTOR_UPGRADE.md docs\reference\
move docs\SCALPING_FIX.md docs\reference\
move docs\CHANGELOG_v13.3.1.md docs\reference\
move docs\FINAL_VERIFICATION.md docs\reference\

echo 완료!
