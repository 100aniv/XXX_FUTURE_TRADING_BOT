#!/usr/bin/env python3
"""프로젝트 파일 정리 스크립트"""
import os
import shutil
from pathlib import Path

print("=" * 60)
print("프로젝트 파일 정리 시작")
print("=" * 60)

# 1. Setup 카테고리
setup_files = [
    'TELEGRAM_SETUP.md',
    'SETUP_3BOTS.md',
    'DEPLOYMENT_CHECKLIST.md'
]

for f in setup_files:
    src = f'docs/{f}'
    dst = f'docs/setup/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → setup/')

# 2. Strategy 카테고리
strategy_files = [
    '6_STRATEGY_SYSTEM.md',
    'ENSEMBLE_6_STRATEGIES.md',
    'ENSEMBLE_ARCHITECTURE.md',
    'ENSEMBLE_DECISION_LOGIC.md',
    'STRATEGY_GUIDE.md',
    'EXTREME_LEVERAGE_STRATEGY.md',
    'POSITION_SIZING.md',
    'DAILY_TARGET_GUIDE.md'
]

for f in strategy_files:
    src = f'docs/{f}'
    dst = f'docs/strategy/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → strategy/')

# 3. Backtest 카테고리
backtest_files = [
    'BACKTEST_QUICKSTART.md',
    'BACKTEST_STRATEGY.md'
]

for f in backtest_files:
    src = f'docs/{f}'
    dst = f'docs/backtest/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → backtest/')

# 4. Implementation 카테고리
impl_files = [
    'IMPLEMENTATION_ROADMAP.md',
    'ROADMAP_TO_AUTOMATION.md',
    '4DAY_IMPLEMENTATION_PLAN.md'
]

for f in impl_files:
    src = f'docs/{f}'
    dst = f'docs/implementation/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → implementation/')

# 5. Architecture 카테고리
arch_files = [
    'TRADING_EXECUTOR.md',
    'TRADING_DECISION.md',
    'TRADING_BOT_SPEC.md',
    'REFACTORING.md',
    'DB_SCHEMA_GUIDE.md'
]

for f in arch_files:
    src = f'docs/{f}'
    dst = f'docs/architecture/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → architecture/')

# 6. Deployment 카테고리
deploy_files = [
    'DOCKER_DEPLOYMENT.md'
]

for f in deploy_files:
    src = f'docs/{f}'
    dst = f'docs/deployment/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → deployment/')

# 7. Reference 카테고리
ref_files = [
    'TELEGRAM_MESSAGE_DESIGN.md',
    'BINANCE_CONNECTOR_UPGRADE.md',
    'SCALPING_FIX.md',
    'CHANGELOG_v13.3.1.md',
    'FINAL_VERIFICATION.md'
]

for f in ref_files:
    src = f'docs/{f}'
    dst = f'docs/reference/{f}'
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'✅ {f} → reference/')

# 8. 루트의 불필요한 파일 정리
root_cleanup = [
    'setup_conda_env.bat',
    'organize_docs.bat',
    'test_system.bat'
]

cleanup_dir = 'cleanup'
os.makedirs(cleanup_dir, exist_ok=True)

for f in root_cleanup:
    if os.path.exists(f):
        shutil.move(f, f'{cleanup_dir}/{f}')
        print(f'🗑️  {f} → cleanup/')

print("\n" + "=" * 60)
print("✅ 정리 완료!")
print("=" * 60)
