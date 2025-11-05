#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Data Source
================
실시간 시세 (paper/live 공통)
"""
import ccxt
from typing import Dict


class LiveDataSource:
    """실시간 데이터 소스 (paper/live 공통)"""
    
    def __init__(self, exchange: str = 'binance', **kwargs):
        self.exchange_name = exchange
        self.exchange = getattr(ccxt, exchange)({
            'apiKey': kwargs.get('api_key'),
            'secret': kwargs.get('api_secret'),
            'enableRateLimit': True,
        })
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100):
        """OHLCV 데이터 가져오기"""
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    def fetch_ticker(self, symbol: str) -> Dict:
        """현재가 가져오기"""
        return self.exchange.fetch_ticker(symbol)
