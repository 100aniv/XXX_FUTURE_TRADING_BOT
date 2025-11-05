# 기존 설정 파일 archived로 이동
Move-Item "strategy_params.yaml" -Destination "_archived\" -Force -ErrorAction SilentlyContinue
Move-Item "data\backtest_config.yaml" -Destination "_archived\" -Force -ErrorAction SilentlyContinue
Move-Item ".env.new" -Destination "_archived\" -Force -ErrorAction SilentlyContinue
Move-Item "common\config_new.py" -Destination "_archived\" -Force -ErrorAction SilentlyContinue

Write-Host "✅ 기존 설정 파일 archived로 이동 완료"
