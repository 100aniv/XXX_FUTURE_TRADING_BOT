# ==================================================================
# 페이퍼 모드 검증 스크립트
# ==================================================================
# 페이퍼 모드 실행 상태 및 DB 연결 확인
# 
# 사용법: .\verify_paper_mode.ps1
# ==================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 페이퍼 모드 검증" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. 컨테이너 상태 확인
Write-Host "[1/4] 컨테이너 상태 확인..." -ForegroundColor Yellow

$paperStatus = docker ps --filter "name=trading_bot_paper" --format "{{.Status}}"
$pgStatus = docker ps --filter "name=trading_db_postgres" --format "{{.Status}}"
$redisStatus = docker ps --filter "name=trading_redis" --format "{{.Status}}"

if ($paperStatus) {
    Write-Host "  ✅ Paper 컨테이너: $paperStatus" -ForegroundColor Green
} else {
    Write-Host "  ❌ Paper 컨테이너 실행 안됨" -ForegroundColor Red
    Write-Host ""
    Write-Host "실행 방법: docker compose --profile paper up -d" -ForegroundColor Yellow
    exit 1
}

if ($pgStatus) {
    Write-Host "  ✅ PostgreSQL: $pgStatus" -ForegroundColor Green
} else {
    Write-Host "  ❌ PostgreSQL 실행 안됨" -ForegroundColor Red
    exit 1
}

if ($redisStatus) {
    Write-Host "  ✅ Redis: $redisStatus" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Redis 실행 안됨 (선택 사항)" -ForegroundColor Yellow
}

Write-Host ""

# 2. 로그 확인 (최근 20줄)
Write-Host "[2/4] 페이퍼 모드 로그 확인..." -ForegroundColor Yellow
docker logs --tail 20 trading_bot_paper 2>&1 | Select-Object -Last 10
Write-Host ""

# 3. DB 연결 확인
Write-Host "[3/4] DB 연결 확인..." -ForegroundColor Yellow

$tradesCount = docker exec trading_db_postgres psql -U trading_user -d trading_db -t -c "SELECT COUNT(*) FROM trading.trades WHERE status='CLOSED';" 2>&1
$signalsCount = docker exec trading_db_postgres psql -U trading_user -d trading_db -t -c "SELECT COUNT(*) FROM monitoring.signals WHERE timestamp > NOW() - INTERVAL '24 hours';" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ DB 연결 정상" -ForegroundColor Green
    Write-Host "  📊 거래 기록(CLOSED): $tradesCount" -ForegroundColor Cyan
    Write-Host "  📊 신호(24h): $signalsCount" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  DB 쿼리 실패 (스키마 확인 필요)" -ForegroundColor Yellow
}

Write-Host ""

# 4. config.yml mode 확인
Write-Host "[4/4] Config 설정 확인..." -ForegroundColor Yellow

if (Test-Path "config.yml") {
    $configMode = Select-String -Path "config.yml" -Pattern "^mode:" | Select-Object -First 1
    Write-Host "  $configMode" -ForegroundColor Cyan
    Write-Host "  ℹ️  Docker 환경변수(TRADING_MODE)가 우선 적용됩니다" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  config.yml 없음" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 검증 완료!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  - 7일 거래 데이터 축적 대기" -ForegroundColor White
Write-Host "  - 로그 모니터링: docker logs -f trading_bot_paper" -ForegroundColor White
Write-Host "  - 거래 확인: docker exec trading_db_postgres psql -U trading_user -d trading_db" -ForegroundColor White
Write-Host ""
