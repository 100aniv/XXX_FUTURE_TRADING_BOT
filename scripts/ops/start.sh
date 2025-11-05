#!/bin/bash
# ==================================
# Trading Bot 빠른 시작 스크립트
# ==================================

set -e

echo "======================================"
echo "🐳 Trading Bot Docker Manager"
echo "======================================"
echo ""

# 모드 선택
echo "모드를 선택하세요:"
echo "1) SIM (백테스트)"
echo "2) PAPER (페이퍼 트레이딩)"
echo "3) LIVE (실거래 ⚠️)"
echo "4) DB만 시작"
echo "5) 전체 중지"
echo ""
read -p "선택 (1-5): " choice

case $choice in
  1)
    echo "✅ 백테스트 모드 시작..."
    docker-compose --profile sim up -d
    echo ""
    echo "📊 로그 확인: docker-compose --profile sim logs -f"
    ;;
  2)
    echo "✅ 페이퍼 모드 시작..."
    docker-compose --profile paper up -d
    echo ""
    echo "📄 로그 확인: docker-compose --profile paper logs -f"
    ;;
  3)
    echo "⚠️  라이브 모드 - 실제 거래가 실행됩니다!"
    read -p "정말 시작하시겠습니까? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      echo "✅ 라이브 모드 시작..."
      docker-compose --profile live up -d
      echo ""
      echo "🔴 로그 확인: docker-compose --profile live logs -f"
    else
      echo "❌ 취소되었습니다."
    fi
    ;;
  4)
    echo "✅ DB만 시작..."
    docker-compose up -d db_postgres
    echo ""
    echo "✅ DB 준비 완료"
    ;;
  5)
    echo "⏹️  전체 중지..."
    docker-compose --profile sim down
    docker-compose --profile paper down
    docker-compose --profile live down
    echo "✅ 중지 완료"
    ;;
  *)
    echo "❌ 잘못된 선택입니다."
    exit 1
    ;;
esac

echo ""
echo "======================================"
echo "✅ 완료!"
echo "======================================"
