#!/bin/bash
# ============================================
# Docker 컨테이너 정리 스크립트
# ============================================
# 옛날 봇들 중지 및 삭제
# 기존 DB(future_alarm_bot_postgres)는 유지

echo "============================================"
echo "🗑️  옛날 Docker 컨테이너 정리"
echo "============================================"

# 중지할 컨테이너 목록
CONTAINERS=(
  "signal_bot_scalp"
  "signal_bot_daytrade"
  "signal_bot_intraday"
  "signal_bot_swing"
  "signal_bot_trend"
  "signal_bot_reversion"
  "signal_bot_breakout"
  "signal_bot_ensemble"
  "trading_manager"
)

echo ""
echo "🛑 컨테이너 중지 중..."
for container in "${CONTAINERS[@]}"; do
  if docker ps -a | grep -q "$container"; then
    echo "  ⏸️  중지: $container"
    docker stop "$container" 2>/dev/null
    docker rm "$container" 2>/dev/null
    echo "  ✅ 삭제: $container"
  else
    echo "  ⏭️  없음: $container"
  fi
done

echo ""
echo "============================================"
echo "✅ 정리 완료!"
echo "============================================"
echo ""
echo "유지된 컨테이너:"
echo "  ✅ future_alarm_bot_postgres (DB)"
echo ""
echo "다음 단계:"
echo "  1. docker-compose up -d  (새로운 시스템 시작)"
echo "============================================"
