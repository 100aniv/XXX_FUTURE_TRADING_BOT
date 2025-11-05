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
    
    def __init__(self, config: dict = None, fee_rate: float = 0.0004, slippage_pct: float = 0.0005):
        self.config = config or {}
        # config에서 수수료/슬리피지 추출 (없으면 기본값)
        fees_cfg = self.config.get('fees', {})
        self.fee_rate = fees_cfg.get('taker_fee', fee_rate)
        self.slippage_pct = fees_cfg.get('slippage', slippage_pct)
        
        # 레거시 파라미터 우선 (하위 호환)
        if fee_rate != 0.0004:
            self.fee_rate = fee_rate
        if slippage_pct != 0.0005:
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
    
    def dry_run(self, order_intent: dict) -> dict:
        """
        IBroker 계약 충족: 주문 시뮬레이션 (실제 체결 없이 결과 계산)
        
        Args:
            order_intent: {
                "symbol": str,
                "side": str,  # "BUY" or "SELL" or "LONG" or "SHORT"
                "quantity": float,
                "price": float,
                "sl": float,
                "tp": float,
                ...
            }
        
        Returns:
            {
                "filled": bool,
                "fill_price": float,
                "pnl": float,
                "commission": float,
                ...
            }
        """
        side = order_intent.get('side', 'LONG')
        price = order_intent.get('price', 0.0)
        qty = order_intent.get('quantity', 0.0)
        
        # execute() 재사용
        result = self.execute(side, price, qty)
        
        if not result.get('success', False):
            return {
                'filled': False,
                'fill_price': 0.0,
                'pnl': 0.0,
                'commission': 0.0,
                'error': result.get('error', 'unknown'),
            }
        
        # 간단한 PnL 계산 (TP 도달 가정)
        tp = order_intent.get('tp', price * 1.02)  # 기본 2% 이익
        entry_price = result['executed_price']
        
        if side in ['LONG', 'BUY']:
            pnl = (tp - entry_price) * qty
        else:
            pnl = (entry_price - tp) * qty
        
        # 수수료 차감
        pnl_net = pnl - result['fee'] * 2  # 진입 + 청산
        
        return {
            'filled': True,
            'fill_price': entry_price,
            'pnl': pnl_net,
            'commission': result['fee'] * 2,
            'qty': qty,
            'side': side,
        }
    
    def place(self, order_intent: dict) -> str:
        """
        IBroker 계약 충족: 실제 주문 배치 (시뮬레이션에서는 dry_run과 동일)
        
        Args:
            order_intent: 주문 의도
        
        Returns:
            order_id: 주문 ID
        """
        # 시뮬레이션에서는 dry_run과 동일하게 처리
        result = self.dry_run(order_intent)
        
        if result.get('filled', False):
            # 타임스탬프 기반 주문 ID 생성
            order_id = f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            return order_id
        else:
            raise Exception(f"Order placement failed: {result.get('error', 'unknown')}")
