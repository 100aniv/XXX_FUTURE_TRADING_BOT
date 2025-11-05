#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config.yml 설정값 검증 스크립트"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("config.yml 설정값 검증 (Phase 4)")
print("=" * 80)

# config.yml 로드
config_file = Path(__file__).parent / 'config.yml'
with open(config_file, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

issues = []
warnings = []
recommendations = []

# 4.1 Risk 설정 검증
print("\n📋 4.1 Risk 설정 검증")
print("-" * 80)

risk = config.get('risk', {})

# 거래당 리스크
per_trade = risk.get('per_trade', 0)
if per_trade == 0:
    issues.append("❌ risk.per_trade: 설정되지 않음")
elif per_trade < 0.005:
    warnings.append(f"⚠️ risk.per_trade: {per_trade*100:.2f}% (너무 낮음, 일반적: 1-3%)")
elif per_trade > 0.05:
    issues.append(f"❌ risk.per_trade: {per_trade*100:.2f}% (너무 높음, 최대 5%)")
else:
    print(f"   ✅ per_trade: {per_trade*100:.2f}% (합리적)")

# 일일 손실 한도
max_daily_loss = risk.get('max_daily_loss_pct', 0)
if max_daily_loss == 0:
    warnings.append("⚠️ risk.max_daily_loss_pct: 설정되지 않음")
elif max_daily_loss < 0.02:
    warnings.append(f"⚠️ max_daily_loss_pct: {max_daily_loss*100:.1f}% (너무 낮음)")
elif max_daily_loss > 0.10:
    issues.append(f"❌ max_daily_loss_pct: {max_daily_loss*100:.1f}% (너무 높음, 최대 10%)")
else:
    print(f"   ✅ max_daily_loss_pct: {max_daily_loss*100:.1f}% (합리적)")

# 연속 손실 한도
max_consecutive = risk.get('max_consecutive_losses', 0)
if max_consecutive == 0:
    warnings.append("⚠️ risk.max_consecutive_losses: 설정되지 않음")
elif max_consecutive < 3:
    warnings.append(f"⚠️ max_consecutive_losses: {max_consecutive}회 (너무 낮음)")
elif max_consecutive > 10:
    warnings.append(f"⚠️ max_consecutive_losses: {max_consecutive}회 (너무 높음)")
else:
    print(f"   ✅ max_consecutive_losses: {max_consecutive}회 (합리적)")

# 레버리지
leverage_cap = risk.get('leverage_cap', 0)
if leverage_cap == 0:
    warnings.append("⚠️ risk.leverage_cap: 설정되지 않음")
elif leverage_cap > 10:
    warnings.append(f"⚠️ leverage_cap: {leverage_cap}x (높음, 페이퍼 테스트용으로만 권장)")
else:
    print(f"   ✅ leverage_cap: {leverage_cap}x (합리적)")

# 4.2 Exits 설정 검증
print("\n📋 4.2 Exits 설정 검증")
print("-" * 80)

exits = config.get('exits', {})

# TP 레벨
tp_levels = exits.get('take_profits', [])
if not tp_levels:
    warnings.append("⚠️ exits.take_profits: 설정되지 않음")
else:
    print(f"   ✅ TP 레벨: {len(tp_levels)}개")
    for i, tp in enumerate(tp_levels, 1):
        r_mult = tp.get('r_multiple', 0)
        size_pct = tp.get('size_pct', 0)
        if r_mult < 1.0:
            warnings.append(f"⚠️ TP{i}: {r_mult}R (1R 미만)")
        elif r_mult > 5.0:
            warnings.append(f"⚠️ TP{i}: {r_mult}R (너무 높음)")
        print(f"      - TP{i}: {r_mult}R ({size_pct}%)")

# 트레일링
trailing = exits.get('trailing', {})
if trailing:
    trail_type = trailing.get('type', 'unknown')
    trail_k = trailing.get('k', 0)
    be_at_r = trailing.get('move_to_break_even_at_r', 0)
    print(f"   ✅ 트레일링: {trail_type}, k={trail_k}, BE={be_at_r}R")
else:
    warnings.append("⚠️ exits.trailing: 설정되지 않음")

# 시간 청산
time_exit = exits.get('time_exit_min', 0)
if time_exit == 0:
    warnings.append("⚠️ exits.time_exit_min: 설정되지 않음")
elif time_exit < 60:
    warnings.append(f"⚠️ time_exit_min: {time_exit}분 (너무 짧음)")
elif time_exit > 1440:
    warnings.append(f"⚠️ time_exit_min: {time_exit}분 (너무 길음, 24시간 초과)")
else:
    print(f"   ✅ time_exit_min: {time_exit}분 ({time_exit/60:.1f}시간)")

# 4.3 Portfolio 설정 검증
print("\n📋 4.3 Portfolio 설정 검증")
print("-" * 80)

portfolio = config.get('portfolio', {})

max_positions = portfolio.get('max_strategy_positions', 0) or risk.get('max_positions', 0)
if max_positions == 0:
    warnings.append("⚠️ max_positions: 설정되지 않음")
elif max_positions < 3:
    recommendations.append(f"💡 max_positions: {max_positions}개 (3-5개 권장)")
else:
    print(f"   ✅ max_positions: {max_positions}개")

max_total_exposure = portfolio.get('max_total_exposure', 0) or risk.get('max_exposure_pct', 0)
if max_total_exposure == 0:
    warnings.append("⚠️ max_total_exposure: 설정되지 않음")
elif max_total_exposure > 1.0:
    issues.append(f"❌ max_total_exposure: {max_total_exposure*100:.0f}% (100% 초과)")
elif max_total_exposure < 0.5:
    recommendations.append(f"💡 max_total_exposure: {max_total_exposure*100:.0f}% (50-95% 권장)")
else:
    print(f"   ✅ max_total_exposure: {max_total_exposure*100:.0f}%")

max_exposure_per_symbol = risk.get('max_exposure_per_symbol', 0)
if max_exposure_per_symbol == 0:
    warnings.append("⚠️ max_exposure_per_symbol: 설정되지 않음")
elif max_exposure_per_symbol > 0.5:
    warnings.append(f"⚠️ max_exposure_per_symbol: {max_exposure_per_symbol*100:.0f}% (너무 높음)")
else:
    print(f"   ✅ max_exposure_per_symbol: {max_exposure_per_symbol*100:.0f}%")

# 4.4 전략별 설정 검증
print("\n📋 4.4 전략별 설정 검증")
print("-" * 80)

strategies = config.get('strategies', {})
strategy_names = ['scalping', 'daytrade', 'swing', 'trend', 'reversion', 'breakout']

for strategy_name in strategy_names:
    strategy_cfg = strategies.get(strategy_name, {})
    if not strategy_cfg:
        warnings.append(f"⚠️ {strategy_name}: 설정 없음")
        continue
    
    print(f"\n   [{strategy_name}]")
    
    # lookback (indicators 공통 or 전략별)
    lookback = strategy_cfg.get('lookback') or config.get('lookback', 100)
    if lookback < 50:
        warnings.append(f"⚠️ {strategy_name}.lookback: {lookback} (너무 짧음)")
    else:
        print(f"      ✅ lookback: {lookback}")
    
    # timeframe
    tf = strategy_cfg.get('timeframe', 'N/A')
    print(f"      ✅ timeframe: {tf}")
    
    # RR
    rr = strategy_cfg.get('rr', 0)
    if rr == 0:
        warnings.append(f"⚠️ {strategy_name}.rr: 설정되지 않음")
    elif rr < 1.2:
        warnings.append(f"⚠️ {strategy_name}.rr: {rr} (1.2R 이상 권장)")
    else:
        print(f"      ✅ rr: {rr}R")
    
    # risk_per_trade
    rpt = strategy_cfg.get('risk_per_trade', 0)
    if rpt > 0:
        print(f"      ✅ risk_per_trade: {rpt*100:.2f}%")
    
    # enabled
    enabled = strategy_cfg.get('enabled', False)
    status = "활성" if enabled else "비활성"
    print(f"      {'✅' if enabled else '⏸'} enabled: {status}")

# 4.5 자본금 설정
print("\n📋 4.5 자본금 설정")
print("-" * 80)

equity = config.get('equity', 0) or config.get('capital', {}).get('initial', 0)
if equity == 0:
    issues.append("❌ equity: 설정되지 않음")
elif equity < 1000:
    warnings.append(f"⚠️ equity: ${equity:,.0f} (너무 낮음)")
else:
    print(f"   ✅ equity: ${equity:,.0f}")

# 결과 요약
print("\n\n" + "=" * 80)
print("📊 Phase 4 검증 결과")
print("=" * 80)

if issues:
    print(f"\n❌ Critical Issues: {len(issues)}개")
    for issue in issues:
        print(f"   {issue}")
else:
    print("\n✅ Critical Issues: 없음")

if warnings:
    print(f"\n⚠️ Warnings: {len(warnings)}개")
    for warning in warnings:
        print(f"   {warning}")
else:
    print("\n✅ Warnings: 없음")

if recommendations:
    print(f"\n💡 Recommendations: {len(recommendations)}개")
    for rec in recommendations:
        print(f"   {rec}")

print("\n" + "=" * 80)

sys.exit(1 if issues else 0)
