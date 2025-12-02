#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE24-0: PAPER 실행 결과 분석
"""
import re
from pathlib import Path
from collections import defaultdict

log_file = Path(__file__).parent.parent / "logs" / "application.log"

# 통계 변수
ensemble_aggregates = 0
trades = 0
strategies_participated = set()
tier_counts = defaultdict(int)

# 09:19 이후 로그만 분석 (config 수정 후)
with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        # 09:19 이후만
        if not re.search(r"2025-12-02 (09:19|09:[2-5]\d|10:|11:)", line):
            continue
        
        # Ensemble Aggregate
        if "[ENSEMBLE V2] Aggregate 결과" in line or "[ENSEMBLE V2] Aggregate" in line:
            ensemble_aggregates += 1
            # Tier 추출
            if "tier=tier1" in line:
                tier_counts["tier1"] += 1
            elif "tier=tier2" in line:
                tier_counts["tier2"] += 1
            elif "tier=skip" in line:
                tier_counts["skip"] += 1
        
        # Trade 실행
        if "[ENTRY OPEN]" in line or "[DB] 거래 저장완료" in line:
            trades += 1
            # 전략 추출
            match = re.search(r"strategy=([\w_]+)", line)
            if match:
                strategies_participated.add(match.group(1))

print("=" * 80)
print("PHASE24-0: PAPER 실행 결과 (09:19~ 현재)")
print("=" * 80)
print(f"\n📊 Ensemble Aggregate 평가:")
print(f"  - 총 평가 횟수: {ensemble_aggregates}회")
print(f"  - Tier1 (High Confidence): {tier_counts['tier1']}회 ({tier_counts['tier1']/max(ensemble_aggregates,1)*100:.1f}%)")
print(f"  - Tier2 (Consensus): {tier_counts['tier2']}회 ({tier_counts['tier2']/max(ensemble_aggregates,1)*100:.1f}%)")
print(f"  - Skip: {tier_counts['skip']}회 ({tier_counts['skip']/max(ensemble_aggregates,1)*100:.1f}%)")

print(f"\n💼 Trade 실행:")
print(f"  - 총 Trades: {trades}개")
print(f"  - 참여 전략: {len(strategies_participated)}개")
if strategies_participated:
    print(f"  - 전략 목록: {', '.join(sorted(strategies_participated))}")

print("\n" + "=" * 80)
