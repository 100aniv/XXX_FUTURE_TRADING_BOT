#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE24-0: Redis Error Counter
로그 파일에서 Redis 관련 ERROR/CRITICAL 카운트
"""
import re
from pathlib import Path

log_file = Path(__file__).parent.parent / "logs" / "application.log"

redis_errors = []
redis_success = []

with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        # 오늘 날짜 (2025-12-02 09:, 10:, 11:)만 필터
        if not re.search(r"2025-12-02 (09|10|11):", line):
            continue
        
        # Redis 관련 라인
        if "Redis" in line or "redis" in line:
            # ERROR/CRITICAL/failed 체크
            if any(kw in line for kw in ["ERROR", "CRITICAL", "failed", "실패"]):
                # 단, "연결 성공" 같은 긍정 메시지 제외
                if "성공" not in line and "successful" not in line:
                    redis_errors.append(line.strip())
            # 성공 메시지
            elif "성공" in line or "successful" in line:
                redis_success.append(line.strip())

print("=" * 80)
print("PHASE24-0: Redis ERROR/CRITICAL Count")
print("=" * 80)
print(f"\n✅ Redis 연결 성공 메시지: {len(redis_success)}개")
if redis_success:
    for msg in redis_success[:5]:
        print(f"  - {msg[:120]}")

print(f"\n❌ Redis ERROR/CRITICAL 메시지: {len(redis_errors)}개")
if redis_errors:
    for msg in redis_errors[:10]:
        print(f"  - {msg[:120]}")
else:
    print("  🎉 Redis 관련 ERROR/CRITICAL 없음!")

print("\n" + "=" * 80)
print(f"결과: Redis ERROR/CRITICAL = {len(redis_errors)}건")
print("=" * 80)
