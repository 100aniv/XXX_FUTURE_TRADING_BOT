#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collectors Module
=================
데이터 수집 모듈

- historical_collector: CSV 파일 읽기 (단일/멀티 심볼 백테스트)
- websocket_collector: WebSocket 실시간 수신 (페이퍼/라이브)
- rest_collector: Binance REST API
"""
from .historical_collector import HistoricalFeed, MultiSymbolHistoricalFeed, load_historical_data
# ⚠️ WebSocketCollector 즉시 임포트 방지 - engine.run()에서 지연 로드
# from .websocket_collector import WebSocketCollector  # 🚫 즉시 임포트 금지
from .rest_collector import fetch_history, fetch_all_symbols, fetch_ticker_24h

__all__ = [
    'HistoricalFeed',
    'MultiSymbolHistoricalFeed', 
    'load_historical_data',
    # 'WebSocketCollector',  # 🚫 지연 로드로 변경
    'fetch_history',
    'fetch_all_symbols',
    'fetch_ticker_24h'
]
