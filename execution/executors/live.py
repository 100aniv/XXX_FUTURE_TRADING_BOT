#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Executor
=============
실제 주문 실행기 (Binance SDK 직접 사용)
"""
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from common.logger import setup_logger

logger = setup_logger(__name__)


class LiveExecutor:
    """실전 거래 실행기 (Binance SDK)"""
    
    def __init__(self, api_key: str, api_secret: str, fee_rate: float = 0.0004):
        self.client = Client(api_key, api_secret)
        self.fee_rate = fee_rate
        logger.info("✅ Binance 클라이언트 연결 성공")
    
    def fetch_balance(self) -> dict:
        """
        실제 계좌 자산 조회 (⭐ PR8: 라이브 모드 자동 로드)
        
        Returns:
            {
                'total_usdt': float,  # 총 USDT
                'free_usdt': float,   # 사용 가능 USDT
                'margin_balance': float,  # 증거금 잔고
                'unrealized_pnl': float  # 미실현 손익
            }
        """
        try:
            # 선물 계좌 정보 조회
            account = self.client.futures_account()
            
            total_usdt = float(account['totalWalletBalance'])
            free_usdt = float(account['availableBalance'])
            margin_balance = float(account['totalMarginBalance'])
            unrealized_pnl = float(account['totalUnrealizedProfit'])
            
            logger.info(f"💰 [LIVE] 자산 조회: Total=${total_usdt:,.2f}, Free=${free_usdt:,.2f}, Margin=${margin_balance:,.2f}, Unrealized PnL={unrealized_pnl:+,.2f}")
            
            return {
                'total_usdt': total_usdt,
                'free_usdt': free_usdt,
                'margin_balance': margin_balance,
                'unrealized_pnl': unrealized_pnl
            }
        except BinanceAPIException as e:
            logger.error(f"❌ 자산 조회 실패: {e}")
            return {
                'total_usdt': 0.0,
                'free_usdt': 0.0,
                'margin_balance': 0.0,
                'unrealized_pnl': 0.0
            }
    
    def execute(self, side: str, symbol: str, price: float, qty: float) -> dict:
        """
        실제 주문 실행
        
        Args:
            side: 'LONG' | 'SHORT'
            symbol: 심볼 (예: BTCUSDT)
            price: 진입 가격
            qty: 코인 개수
        
        Returns:
            실행 결과
        """
        # None 값 체크
        if price is None or qty is None:
            logger.error(f"❌ 잘못된 주문: symbol={symbol}, price={price}, qty={qty}")
            return {
                'success': False,
                'error': 'Invalid price or qty (None)',
                'executed_price': None,
                'qty': None
            }
        
        try:
            # 타입 변환 (Decimal → float)
            qty = float(qty)
            price = float(price)
            
            # Binance API 호출
            if side == 'LONG':
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=qty
                )
            else:  # SHORT
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=qty
                )
            
            executed_price = float(order['avgPrice'])
            value = executed_price * qty
            fee = value * self.fee_rate
            
            logger.info(f"🔴 [LIVE] {side} {symbol} @ {executed_price:.2f} qty={qty:.4f}")
            
            return {
                'success': True,
                'executed_price': executed_price,
                'qty': qty,
                'value': value,
                'fee': fee,
                'timestamp': datetime.now(),
                'order_id': order['orderId']
            }
            
        except BinanceAPIException as e:
            logger.error(f"❌ Binance API 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }
