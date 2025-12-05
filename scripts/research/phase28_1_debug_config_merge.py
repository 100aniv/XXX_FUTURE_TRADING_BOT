#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-1-FIX: Config 병합 디버그 스크립트
merge_strategy_config가 전략 파라미터를 제대로 top-level로 올리는지 확인
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import merge_strategy_config
from common.logger import setup_logger
import json
import yaml

logger = setup_logger("phase28_1_debug")

def main():
    """Config 병합 테스트"""
    logger.info("=" * 80)
    logger.info("🔍 PHASE28-1-FIX: Config 병합 디버그")
    logger.info("=" * 80)
    
    # Config 로드 (YAML 직접 로드)
    config_path = project_root / "configs" / "backtest" / "phase28_1_btc5m_baseline_presets_fixed.yml"
    logger.info(f"📋 Config: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 전략 섹션 확인
    logger.info("\n" + "=" * 80)
    logger.info("📦 Strategies 섹션 확인")
    logger.info("=" * 80)
    
    strategies = config.get('strategies', {})
    logger.info(f"Strategies keys: {list(strategies.keys())}")
    
    btc5m_cfg = strategies.get('btc5m_baseline_v1', {})
    logger.info(f"\nbtc5m_baseline_v1 keys: {list(btc5m_cfg.keys())}")
    logger.info(f"  rsi_long_threshold: {btc5m_cfg.get('rsi_long_threshold', 'NOT FOUND')}")
    logger.info(f"  rsi_short_threshold: {btc5m_cfg.get('rsi_short_threshold', 'NOT FOUND')}")
    logger.info(f"  bb_std_main: {btc5m_cfg.get('bb_std_main', 'NOT FOUND')}")
    logger.info(f"  use_adx: {btc5m_cfg.get('use_adx', 'NOT FOUND')}")
    
    # merge_strategy_config 테스트
    logger.info("\n" + "=" * 80)
    logger.info("🔧 merge_strategy_config 테스트")
    logger.info("=" * 80)
    
    strategy_selector = config.get("strategy", {}).get("selector", "btc5m_baseline_v1")
    logger.info(f"Strategy selector: {strategy_selector}")
    
    merged = merge_strategy_config(config, strategy_selector)
    
    logger.info(f"\n✅ 병합 결과 - Top-level keys: {list(merged.keys())}")
    logger.info(f"  rsi_long_threshold (top-level): {merged.get('rsi_long_threshold', 'NOT FOUND')}")
    logger.info(f"  rsi_short_threshold (top-level): {merged.get('rsi_short_threshold', 'NOT FOUND')}")
    logger.info(f"  bb_std_main (top-level): {merged.get('bb_std_main', 'NOT FOUND')}")
    logger.info(f"  use_adx (top-level): {merged.get('use_adx', 'NOT FOUND')}")
    logger.info(f"  adx_period (top-level): {merged.get('adx_period', 'NOT FOUND')}")
    logger.info(f"  adx_trend_threshold (top-level): {merged.get('adx_trend_threshold', 'NOT FOUND')}")
    
    # strategy_config 키 확인
    strategy_config = merged.get('strategy_config', {})
    logger.info(f"\n  strategy_config keys: {list(strategy_config.keys())}")
    logger.info(f"  strategy_config.rsi_long_threshold: {strategy_config.get('rsi_long_threshold', 'NOT FOUND')}")
    
    # Indicators 섹션 확인
    logger.info("\n" + "=" * 80)
    logger.info("📊 Indicators 섹션 확인")
    logger.info("=" * 80)
    logger.info(f"use_adx (indicators): {config.get('indicators', {}).get('use_adx', 'NOT FOUND')}")
    logger.info(f"adx_period (indicators): {config.get('indicators', {}).get('adx_period', 'NOT FOUND')}")
    logger.info(f"use_adx (merged top-level): {merged.get('use_adx', 'NOT FOUND')}")
    logger.info(f"adx_period (merged top-level): {merged.get('adx_period', 'NOT FOUND')}")
    
    # 전략이 읽을 수 있는지 시뮬레이션
    logger.info("\n" + "=" * 80)
    logger.info("🎯 전략 파라미터 읽기 시뮬레이션")
    logger.info("=" * 80)
    
    def simulate_strategy_param_read(cfg, param_name, default_value):
        """전략 코드처럼 config.get() 사용"""
        value = cfg.get(param_name, default_value)
        status = "✅ OK" if value != default_value else "❌ DEFAULT"
        logger.info(f"{param_name}: {value} (default: {default_value}) {status}")
        return value
    
    simulate_strategy_param_read(merged, 'rsi_long_threshold', 45)
    simulate_strategy_param_read(merged, 'rsi_short_threshold', 55)
    simulate_strategy_param_read(merged, 'bb_std_main', 1.0)
    simulate_strategy_param_read(merged, 'use_adx', False)
    simulate_strategy_param_read(merged, 'adx_period', 14)
    simulate_strategy_param_read(merged, 'adx_trend_threshold', 25)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 디버그 완료")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
