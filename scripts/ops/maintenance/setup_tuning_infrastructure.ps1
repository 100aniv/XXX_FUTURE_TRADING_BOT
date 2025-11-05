# ==================================================================
# 튜닝 인프라 설정 스크립트 (Phase 4)
# ==================================================================
# Redis 컨테이너 시작 및 Optuna DB 생성
# 
# 사용법: .\setup_tuning_infrastructure.ps1
# ==================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Phase 4 튜닝 인프라 설정" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Redis 컨테이너 시작
Write-Host "[1/3] Redis 컨테이너 시작..." -ForegroundColor Yellow
docker compose up -d redis

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Redis 컨테이너 시작 실패" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 3
Write-Host "✅ Redis 컨테이너 시작 완료" -ForegroundColor Green
Write-Host ""

# 2. PostgreSQL 상태 확인
Write-Host "[2/3] PostgreSQL 상태 확인..." -ForegroundColor Yellow
$pgStatus = docker ps --filter "name=trading_db_postgres" --format "{{.Status}}"

if (-not $pgStatus) {
    Write-Host "⚠️  PostgreSQL 컨테이너 없음. 시작 중..." -ForegroundColor Yellow
    docker compose up -d db_postgres
    Start-Sleep -Seconds 10
} else {
    Write-Host "✅ PostgreSQL 컨테이너 실행 중" -ForegroundColor Green
}
Write-Host ""

# 3. Optuna DB 생성
Write-Host "[3/3] Optuna DB 생성..." -ForegroundColor Yellow

$createDbCommand = "CREATE DATABASE optuna;"
docker exec trading_db_postgres psql -U trading_user -d postgres -c $createDbCommand 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Optuna DB 생성 완료" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Optuna DB 이미 존재 (정상)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 설정 완료!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  1. 페이퍼 모드 실행: docker compose --profile paper up -d" -ForegroundColor White
Write-Host "  2. 7일 거래 데이터 축적 대기" -ForegroundColor White
Write-Host "  3. 튜닝 실행: docker compose --profile tuning up tuner_scalping" -ForegroundColor White
Write-Host ""
