#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trading Manager 테스트"""
import os
os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'
os.environ['STRATEGY_SELECTOR'] = 'daytrade'  # 가장 많은 시그널
os.environ['TRADING_MODE'] = 'backtest'

from trading_manager import TradingBot

print("=" * 60)
print("Trading Bot 테스트 시작")
print("=" * 60)

# 봇 생성
bot = TradingBot()

# 한 번만 신호 처리
print("\n신호 처리 시작...")
bot.process_signals()

print("\n테스트 완료!")
