# ============================================
# Docker 컨테이너 정리 스크립트 (Windows)
# ============================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🗑️  옛날 Docker 컨테이너 정리" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 중지할 컨테이너 목록
$containers = @(
    "signal_bot_scalp",
    "signal_bot_daytrade",
    "signal_bot_intraday",
    "signal_bot_swing",
    "signal_bot_trend",
    "signal_bot_reversion",
    "signal_bot_breakout",
    "signal_bot_ensemble",
    "trading_manager"
)

Write-Host ""
Write-Host "🛑 컨테이너 중지 및 삭제 중..." -ForegroundColor Yellow

foreach ($container in $containers) {
    $exists = docker ps -a --filter "name=$container" --format "{{.Names}}"
    
    if ($exists) {
        Write-Host "  ⏸️  중지: $container" -ForegroundColor Yellow
        docker stop $container 2>$null
        docker rm $container 2>$null
        Write-Host "  ✅ 삭제: $container" -ForegroundColor Green
    } else {
        Write-Host "  ⏭️  없음: $container" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ 정리 완료!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "유지된 컨테이너:" -ForegroundColor White
Write-Host "  ✅ future_alarm_bot_postgres (DB)" -ForegroundColor Green
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor White
Write-Host "  1. docker-compose up -d postgres  (DB 시작)" -ForegroundColor Cyan
Write-Host "  2. docker-compose up -d main       (새 시스템 시작)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
