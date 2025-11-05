#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Broker Adapters
===============
거래 실행자 인터페이스

- SimBroker: 백테스트 (슬리피지만 적용)
- PaperBroker: 페이퍼 (가상 실행)
- LiveBroker: 라이브 (Binance API)
"""
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from common.logger import setup_logger

logger = setup_logger(__name__)


class SimBroker:
    """백테스트용 브로커"""
    
    def __init__(self, fee_rate: float = 0.0004, slippage_pct: float = 0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        logger.info(f"✅ SimBroker 초기화")
    
    def execute(self, decision: dict, qty: float) -> dict:
        """
        시뮬레이션 실행
        
        Args:
            decision: ensemble 결정 {'side': 'LONG', 'entry': 100, ...}
            qty: 수량
        
        Returns:
            체결 결과 {'success': bool, 'filled_price': float, 'qty': float, ...}
        """
        side = decision.get('side')
        price = float(decision.get('entry', 0))
        qty = float(qty)  # Decimal → float 변환
        
        # 슬리피지 적용
        if side == 'LONG':
            filled_price = price * (1 + self.slippage_pct)
        else:
            filled_price = price * (1 - self.slippage_pct)
        
        value = filled_price * qty
        fee = value * self.fee_rate
        
        return {
            'success': True,
            'filled_price': filled_price,
            'qty': qty,
            'value': value,
            'fee': fee,
            'timestamp': datetime.now(),
            'order_id': f"SIM_{int(datetime.now().timestamp() * 1000)}"
        }


class PaperBroker:
    """페이퍼 트레이딩 브로커"""
    
    def __init__(self, fee_rate: float = 0.0004, slippage_pct: float = 0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        self.virtual_orders = []
        logger.info(f"✅ PaperBroker 초기화")
    
    def execute(self, decision: dict, qty: float) -> dict:
        """가상 실행 (슬리피지 적용하여 백테스트와 파리티 유지)"""
        side = decision.get('side')
        price = float(decision.get('entry', 0))
        qty = float(qty)  # Decimal → float 변환
        
        # 슬리피지 적용 (SimBroker와 동일 규칙)
        if side == 'LONG':
            filled_price = price * (1 + self.slippage_pct)
        else:
            filled_price = price * (1 - self.slippage_pct)
        value = filled_price * qty
        fee = value * self.fee_rate
        
        order = {
            'success': True,
            'filled_price': filled_price,
            'qty': qty,
            'value': value,
            'fee': fee,
            'timestamp': datetime.now(),
            'order_id': f"PAPER_{int(datetime.now().timestamp() * 1000)}"
        }
        
        self.virtual_orders.append(order)
        logger.info(f"📄 [PAPER] {side} @ {filled_price:.2f} qty={qty:.4f} (slip={self.slippage_pct*100:.2f}%)")
        
        return order


class LiveBroker:
    """실거래 브로커"""
    
    def __init__(self, api_key: str, api_secret: str, fee_rate: float = 0.0004):
        self.client = Client(api_key, api_secret)
        self.fee_rate = fee_rate
        logger.info(f"✅ LiveBroker 초기화 (실거래)")
    
    def execute(self, decision: dict, qty: float) -> dict:
        """Binance API 실제 실행"""
        side = decision.get('side')
        symbol = decision.get('symbol', 'BTCUSDT')
        qty = float(qty)  # Decimal → float 변환
        
        try:
            if side == 'LONG':
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=qty
                )
            else:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=qty
                )
            
            filled_price = float(order['avgPrice'])
            value = filled_price * qty
            fee = value * self.fee_rate
            
            logger.info(f"🔴 [LIVE] {side} {symbol} @ {filled_price:.2f} qty={qty:.4f}")
            
            return {
                'success': True,
                'filled_price': filled_price,
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
