@echo off
REM ==================================
REM Trading Bot 빠른 시작 스크립트 (Windows)
REM ==================================

echo ======================================
echo 🐳 Trading Bot Docker Manager
echo ======================================
echo.

echo 모드를 선택하세요:
echo 1) SIM (백테스트)
echo 2) PAPER (페이퍼 트레이딩)
echo 3) LIVE (실거래 ⚠️)
echo 4) DB만 시작
echo 5) 전체 중지
echo.

set /p choice="선택 (1-5): "

if "%choice%"=="1" (
    echo ✅ 백테스트 모드 시작...
    docker-compose --profile sim up -d
    echo.
    echo 📊 로그 확인: docker-compose --profile sim logs -f
    goto end
)

if "%choice%"=="2" (
    echo ✅ 페이퍼 모드 시작...
    docker-compose --profile paper up -d
    echo.
    echo 📄 로그 확인: docker-compose --profile paper logs -f
    goto end
)

if "%choice%"=="3" (
    echo ⚠️  라이브 모드 - 실제 거래가 실행됩니다!
    set /p confirm="정말 시작하시겠습니까? (yes/no): "
    if /i "%confirm%"=="yes" (
        echo ✅ 라이브 모드 시작...
        docker-compose --profile live up -d
        echo.
        echo 🔴 로그 확인: docker-compose --profile live logs -f
    ) else (
        echo ❌ 취소되었습니다.
    )
    goto end
)

if "%choice%"=="4" (
    echo ✅ DB만 시작...
    docker-compose up -d db_postgres
    echo.
    echo ✅ DB 준비 완료
    goto end
)

if "%choice%"=="5" (
    echo ⏹️  전체 중지...
    docker-compose --profile sim down
    docker-compose --profile paper down
    docker-compose --profile live down
    echo ✅ 중지 완료
    goto end
)

echo ❌ 잘못된 선택입니다.
exit /b 1

:end
echo.
echo ======================================
echo ✅ 완료!
echo ======================================
pause
