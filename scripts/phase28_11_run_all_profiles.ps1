# PHASE28-11: Profile B/C/D 순차 백테스트 실행 스크립트 (PowerShell)
# Profile A는 이미 완료됨

$PROJECT_ROOT = "C:\Users\bback\OneDrive\Documents\future_alarm_bot"
Set-Location $PROJECT_ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PHASE28-11: Profile B/C/D 순차 백테스트" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Profile B
Write-Host "[1/3] Profile B (COOLDOWN_RELAXED) 실행 중..." -ForegroundColor Yellow
Write-Host "Redis 초기화..."
docker exec trading_redis redis-cli FLUSHDB | Out-Null
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_b.yml
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Profile B 완료" -ForegroundColor Green
} else {
    Write-Host "❌ Profile B 실패 (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Profile C
Write-Host "[2/3] Profile C (PORTFOLIO_RELAXED) 실행 중..." -ForegroundColor Yellow
Write-Host "Redis 초기화..."
docker exec trading_redis redis-cli FLUSHDB | Out-Null
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_c.yml
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Profile C 완료" -ForegroundColor Green
} else {
    Write-Host "❌ Profile C 실패 (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Profile D
Write-Host "[3/3] Profile D (MIXED_RELAXED) 실행 중..." -ForegroundColor Yellow
Write-Host "Redis 초기화..."
docker exec trading_redis redis-cli FLUSHDB | Out-Null
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_d.yml
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Profile D 완료" -ForegroundColor Green
} else {
    Write-Host "❌ Profile D 실패 (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 모든 프로파일 백테스트 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계: 분석 스크립트 실행" -ForegroundColor Yellow
Write-Host "  python scripts/analysis/phase28_11_profile_comparison.py"
Write-Host ""
