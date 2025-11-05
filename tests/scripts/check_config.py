#!/usr/bin/env python3
from common.config_loader import load_config

cfg = load_config()
print("=== Config Check ===")
print(f"backtest.symbol: {cfg.get('backtest', {}).get('symbol')}")
print(f"symbols.mode: {cfg.get('symbols', {}).get('mode')}")
print(f"symbols.manual: {cfg.get('symbols', {}).get('manual')}")
print(f"strategy.use_ensemble: {cfg.get('strategy', {}).get('use_ensemble')}")
