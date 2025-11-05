#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulation Executor
===================
백테스트용 시뮬레이션 실행기
"""
from datetime import datetime


class SimulationExecutor:
    """백테스트 시뮬레이션 실행기"""
    
    def __init__(self, fee_rate: float = 0.0004, slippage_pct: float = 0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
    
    def execute(self, side: str, price: float, qty: float) -> dict:
        """
        주문 실행 (시뮬레이션)
        
        Args:
            side: 'LONG' | 'SHORT'
            price: 진입 가격
            qty: 코인 개수 (base_qty)
        
        Returns:
            실행 결과
        """
        # None 값 체크
        if price is None or qty is None:
            return {
                'success': False,
                'error': 'Invalid price or qty (None)',
                'executed_price': None,
                'qty': None
            }
        
        # 타입 변환 (Decimal → float)
        try:
            price = float(price)
            qty = float(qty)
        except (TypeError, ValueError):
            return {
                'success': False,
                'error': 'Type conversion failed',
                'executed_price': None,
                'qty': None
            }
        
        # 슬리피지 적용
        if side == 'LONG':
            executed_price = price * (1 + self.slippage_pct)
        else:
            executed_price = price * (1 - self.slippage_pct)
        
        # 수수료 계산
        value = executed_price * qty
        fee = value * self.fee_rate
        
        return {
            'success': True,
            'executed_price': executed_price,
            'qty': qty,
            'value': value,
            'fee': fee,
            'timestamp': datetime.now(),
        }
