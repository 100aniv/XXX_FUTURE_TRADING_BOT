#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE30-1: Core V1 Config 검증 스크립트
======================================

Config 파일의 필수 키 및 파라미터 검증
"""
import yaml
import sys
from pathlib import Path
from datetime import datetime

def check_config(config_path: str):
    """
    Config 파일 검증
    
    Args:
        config_path: Config 파일 경로
    """
    print(f"=== PHASE30-1: Core V1 Config 검증 ===")
    print(f"Config 파일: {config_path}\n")
    
    # 파일 존재 확인
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"❌ Config 파일이 존재하지 않습니다: {config_path}")
        return False
    
    # YAML 로드
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("✅ YAML 파싱 성공\n")
    except Exception as e:
        print(f"❌ YAML 파싱 실패: {e}")
        return False
    
    # 필수 키 검증
    required_keys = [
        'mode', 'symbol', 'timeframe', 'backtest', 'strategy',
        'capital', 'portfolio', 'risk', 'entries', 'fees'
    ]
    
    missing_keys = []
    for key in required_keys:
        if key not in config:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ 누락된 필수 키: {missing_keys}\n")
        return False
    else:
        print(f"✅ 필수 키 검증 통과 ({len(required_keys)}개)\n")
    
    # 백테스트 설정 확인
    print("=== Backtest 설정 ===")
    backtest = config.get('backtest', {})
    print(f"  Symbol: {backtest.get('symbol')}")
    print(f"  Data File: {backtest.get('data_file')}")
    print(f"  Start Date: {backtest.get('start_date')}")
    print(f"  End Date: {backtest.get('end_date')}")
    print(f"  Duration: {backtest.get('duration_minutes')} 분")
    print(f"  Output: {backtest.get('output_file')}\n")
    
    # 전략 설정 확인
    print("=== Strategy 설정 ===")
    strategy = config.get('strategy', {})
    print(f"  Selector: {strategy.get('selector')}")
    print(f"  Use Ensemble: {strategy.get('use_ensemble')}")
    
    # Core V1 파라미터 확인
    params = strategy.get('params', {}).get('btc15m_core_v1', {})
    if not params:
        print("  ❌ btc15m_core_v1 파라미터가 없습니다.\n")
        return False
    
    print("\n  Core V1 파라미터:")
    
    # Regime Detection
    regime = params.get('regime_detection', {})
    print(f"    Regime Detection:")
    print(f"      - ADX Trend Threshold: {regime.get('adx_trend_threshold')}")
    print(f"      - ADX Range Threshold: {regime.get('adx_range_threshold')}")
    print(f"      - Min Confidence: {regime.get('min_confidence')}")
    
    # Filters
    filters = params.get('filters', {})
    print(f"    Filters:")
    print(f"      - Min ATR %: {filters.get('min_atr_pct')}")
    print(f"      - Min Volume Ratio: {filters.get('min_volume_ratio')}")
    
    # SL/TP
    sl_tp = params.get('sl_tp', {})
    print(f"    SL/TP:")
    print(f"      - Trend SL Mult: {sl_tp.get('sl_mult_trend')}")
    print(f"      - Trend TP1 RR: {sl_tp.get('tp1_rr_trend')}")
    print(f"      - Trend TP2 RR: {sl_tp.get('tp2_rr_trend')}")
    print(f"      - Range SL Mult: {sl_tp.get('sl_mult_range')}")
    print(f"      - Range TP1 RR: {sl_tp.get('tp1_rr_range')}")
    print(f"      - Range TP2 RR: {sl_tp.get('tp2_rr_range')}")
    
    # RR 검증 (최소 1.5)
    tp1_rr_trend = sl_tp.get('tp1_rr_trend', 0)
    tp1_rr_range = sl_tp.get('tp1_rr_range', 0)
    
    if tp1_rr_trend < 1.5:
        print(f"\n  ⚠️  Trend TP1 RR ({tp1_rr_trend}) < 1.5 (목표 미달)")
    if tp1_rr_range < 1.5:
        print(f"\n  ⚠️  Range TP1 RR ({tp1_rr_range}) < 1.5 (목표 미달)")
    
    print()
    
    # Guard 설정 확인
    print("=== Guard 설정 (Guard ON 전제) ===")
    entries = config.get('entries', {})
    print(f"  Cooldown Candles: {entries.get('cooldown_candles')}")
    print(f"  Min RR Required: {entries.get('min_rr_required')}")
    
    risk = config.get('risk', {})
    print(f"  Max Drawdown: {risk.get('max_drawdown', 0) * 100:.1f}%")
    print(f"  Max Consecutive Losses: {risk.get('max_consecutive_losses')}")
    
    flow_guardian = config.get('flow_guardian', {})
    print(f"  FlowGuardian Enabled: {flow_guardian.get('enabled')}")
    
    # Guard ON 검증
    if entries.get('cooldown_candles', 0) == 0:
        print("\n  ⚠️  Cooldown이 0입니다 (Guard OFF 상태)")
    if entries.get('min_rr_required') is None:
        print("  ⚠️  Min RR Required가 없습니다 (Guard OFF 상태)")
    if risk.get('max_drawdown', 1.0) >= 1.0:
        print("  ⚠️  Max DD가 100% 이상입니다 (Guard OFF 상태)")
    
    print()
    
    # Timeframe 확인
    print("=== Timeframe 검증 ===")
    timeframe = config.get('timeframe')
    strategy_selector = strategy.get('selector')
    
    if timeframe == '15m' and 'btc15m' in strategy_selector:
        print(f"  ✅ Timeframe ({timeframe})과 전략 ({strategy_selector})이 일치합니다.")
    else:
        print(f"  ⚠️  Timeframe ({timeframe})과 전략 ({strategy_selector}) 불일치")
    
    print()
    
    # 기간 검증
    print("=== 백테스트 기간 검증 ===")
    try:
        start = datetime.strptime(backtest.get('start_date'), "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(backtest.get('end_date'), "%Y-%m-%d %H:%M:%S")
        days = (end - start).days
        
        print(f"  시작: {start}")
        print(f"  종료: {end}")
        print(f"  기간: {days}일")
        
        if days >= 90:
            print(f"  ✅ 3개월 이상 ({days}일)")
        else:
            print(f"  ⚠️  3개월 미만 ({days}일)")
    except Exception as e:
        print(f"  ❌ 날짜 파싱 실패: {e}")
    
    print()
    
    # 최종 판정
    print("=== 최종 판정 ===")
    print("✅ Config 검증 완료")
    print("\n다음 단계: python scripts/run_backtest.py --config configs/backtest/phase30_1_btc15m_core_v1_3m_baseline.yml")
    
    return True


if __name__ == '__main__':
    config_path = 'configs/backtest/phase30_1_btc15m_core_v1_3m_baseline.yml'
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    success = check_config(config_path)
    sys.exit(0 if success else 1)
