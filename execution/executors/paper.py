#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper Executor
==============
가상 주문 실행기 (실시간 데이터, 가상 체결)
"""
from datetime import datetime
from common.logger import setup_logger

logger = setup_logger(__name__)


class PaperExecutor:
    """페이퍼 트레이딩 실행기"""
    
    def __init__(self, fee_rate: float = 0.0004):
        self.fee_rate = fee_rate
        self.virtual_orders = []
    
    def execute(self, side: str, price: float, qty: float) -> dict:
        """
        가상 주문 실행
        
        Args:
            side: 'LONG' | 'SHORT'
            price: 진입 가격
            qty: 코인 개수
        
        Returns:
            실행 결과
        """
        # None 값 체크
        if price is None or qty is None:
            logger.error(f"❌ 잘못된 주문: price={price}, qty={qty}")
            return {
                'success': False,
                'error': 'Invalid price or qty (None)',
                'executed_price': None,
                'qty': None
            }
        
        # 타입 변환 (Decimal → float)
        try:
            executed_price = float(price)
            qty = float(qty)
        except (TypeError, ValueError) as e:
            logger.error(f"❌ 타입 변환 실패: price={price} ({type(price)}), qty={qty} ({type(qty)})")
            return {
                'success': False,
                'error': f'Type conversion failed: {e}',
                'executed_price': None,
                'qty': None
            }
        
        # 수수료 계산
        value = executed_price * qty
        fee = value * self.fee_rate
        
        order = {
            'success': True,
            'executed_price': executed_price,
            'qty': qty,
            'value': value,
            'fee': fee,
            'timestamp': datetime.now(),
            'order_id': f"PAPER_{int(datetime.now().timestamp() * 1000)}"
        }
        
        self.virtual_orders.append(order)
        logger.info(f"📄 [PAPER] {side} @ {executed_price:.2f} qty={qty:.4f}")
        
        return order
