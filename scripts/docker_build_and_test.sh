#!/bin/bash
# Docker 빌드 및 테스트 자동화 스크립트
# 사용: bash scripts/docker_build_and_test.sh

set -e

echo "=========================================="
echo "🐳 Docker 빌드 및 테스트 자동화"
echo "=========================================="

# 1. Docker 이미지 빌드
echo ""
echo "1️⃣  Docker 이미지 빌드 중..."
docker-compose -f docker-compose.yml build trading_bot_paper_ensemble

# 2. 컨테이너 시작
echo ""
echo "2️⃣  컨테이너 시작 중..."
docker-compose -f docker-compose.yml up -d trading_bot_paper_ensemble

# 3. 컨테이너 준비 대기
echo ""
echo "3️⃣  컨테이너 준비 대기 중 (30초)..."
sleep 30

# 4. Pre-commit 검사 실행
echo ""
echo "4️⃣  Pre-commit 검사 실행 중..."
docker exec trading_bot_paper_ensemble bash scripts/pre_commit_check.sh

# 5. 결과 수집
echo ""
echo "5️⃣  테스트 결과 수집 중..."
docker exec trading_bot_paper_ensemble python -m pytest tests/flow/ --cov=core --cov=execution --cov=metrics --cov-report=json --cov-report=html

# 6. 로그 확인
echo ""
echo "6️⃣  시스템 로그 확인..."
docker logs trading_bot_paper_ensemble | tail -50

echo ""
echo "=========================================="
echo "✅ Docker 빌드 및 테스트 완료"
echo "=========================================="
echo ""
echo "📊 결과 요약:"
echo "  - Docker 이미지: 빌드 완료"
echo "  - 컨테이너: 실행 중"
echo "  - Pre-commit: 검사 완료"
echo "  - Coverage: HTML 리포트 생성 (htmlcov/index.html)"
echo ""
echo "🚀 다음 단계:"
echo "  1. htmlcov/index.html 열어서 커버리지 확인"
echo "  2. 필요시 컨테이너 중지: docker-compose stop"
echo ""
