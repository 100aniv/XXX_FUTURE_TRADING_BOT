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
    """페이퍼 트레이딩 브로커 - 가상 실행 (LiveBroker와 100% 동일한 로직)"""
    
    def __init__(self, fee_rate: float = 0.0004, slippage_pct: float = 0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        self.virtual_orders = []
        self.virtual_tpsl_orders = {}  # {position_id: [order_dicts]}
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
    
    def create_tpsl_orders(self, position: dict, tp_prices: list = None, sl_price: float = None) -> dict:
        """
        TP/SL 조건부 주문 등록 (가상, Binance와 동일한 로직)
        
        Args:
            position: 포지션 정보 {'id': int, 'symbol': str, 'side': str, 'qty': float}
            tp_prices: TP 가격 리스트 [tp1, tp2]
            sl_price: SL 가격
        
        Returns:
            {'success': bool, 'order_ids': [...]}
        """
        position_id = position['id']
        symbol = position['symbol']
        side = position['side']
        total_qty = position['qty']
        
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        virtual_order_ids = []
        
        # SL 가상 주문 (전체 청산)
        if sl_price:
            sl_order = {
                'id': f"PAPER_SL_{int(datetime.now().timestamp() * 1000)}",
                'symbol': symbol,
                'side': close_side,
                'type': 'STOP_MARKET',
                'stopPrice': sl_price,
                'closePosition': True,
                'positionSide': 'BOTH'
            }
            virtual_order_ids.append(sl_order['id'])
            logger.info(f"✅ [PAPER] SL 주문 등록: {symbol} @ ${sl_price:.2f}")
        
        # TP1 가상 주문 (30%)
        if tp_prices and len(tp_prices) > 0:
            tp1_qty = round(total_qty * 0.3, 4)
            tp1_order = {
                'id': f"PAPER_TP1_{int(datetime.now().timestamp() * 1000)}",
                'symbol': symbol,
                'side': close_side,
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': tp_prices[0],
                'quantity': tp1_qty,
                'positionSide': 'BOTH'
            }
            virtual_order_ids.append(tp1_order['id'])
            logger.info(f"✅ [PAPER] TP1 주문 등록: {symbol} @ ${tp_prices[0]:.2f} ({tp1_qty:.4f})")
        
        # TP2 가상 주문 (40%)
        if tp_prices and len(tp_prices) > 1:
            tp2_qty = round(total_qty * 0.4, 4)
            tp2_order = {
                'id': f"PAPER_TP2_{int(datetime.now().timestamp() * 1000)}",
                'symbol': symbol,
                'side': close_side,
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': tp_prices[1],
                'quantity': tp2_qty,
                'positionSide': 'BOTH'
            }
            virtual_order_ids.append(tp2_order['id'])
            logger.info(f"✅ [PAPER] TP2 주문 등록: {symbol} @ ${tp_prices[1]:.2f} ({tp2_qty:.4f})")
        
        # 가상 주문 저장
        self.virtual_tpsl_orders[position_id] = virtual_order_ids
        
        return {'success': True, 'order_ids': virtual_order_ids}
    
    def update_sl_price(self, position_id: int, symbol: str, new_sl_price: float) -> dict:
        """
        트레일링 스톱 가격 업데이트 (가상, Binance와 동일한 로직)
        
        Args:
            position_id: 포지션 ID
            symbol: 심볼
            new_sl_price: 새 SL 가격
        
        Returns:
            {'success': bool}
        """
        order_ids = self.virtual_tpsl_orders.get(position_id, [])
        if not order_ids:
            logger.warning(f"⚠️ 포지션 {position_id} SL 주문 없음")
            return {'success': False, 'error': 'No SL order found'}
        
        # 가상 SL 가격 업데이트 (실제로는 position_tracker가 처리)
        logger.info(f"📈 [PAPER] SL 가격 업데이트: {symbol} → ${new_sl_price:.2f}")
        return {'success': True}
    
    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """
        주문 취소 (가상)
        
        Args:
            symbol: 심볼
            order_id: 주문 ID
        
        Returns:
            {'success': bool}
        """
        logger.info(f"✅ [PAPER] 주문 취소: {symbol} #{order_id}")
        return {'success': True}
    
    def get_account_balance(self) -> dict:
        """
        계정 자산 조회 (가상, config에서 읽음)
        
        Returns:
            {'success': bool, 'balances': [...]}
        """
        # 페이퍼는 고정값 또는 DB에서 계산
        logger.debug(f"✅ [PAPER] 자산 조회 (고정값)")
        return {'success': True, 'balances': []}
    
    def get_positions(self) -> dict:
        """
        포지션 조회 (가상, DB에서 읽음)
        
        Returns:
            {'success': bool, 'positions': [...]}
        """
        logger.debug(f"✅ [PAPER] 포지션 조회 (DB)")
        return {'success': True, 'positions': []}
    
    def close_position(self, position_id: int, symbol: str, side: str, qty: float, reason: str = '') -> dict:
        """
        포지션 청산 (가상, 부분/전체)
        
        Args:
            position_id: 포지션 ID
            symbol: 심볼
            side: 원래 방향 ('LONG' or 'SHORT')
            qty: 청산 수량 (None = 전체)
            reason: 청산 이유
        
        Returns:
            {'success': bool, 'filled_price': float, ...}
        """
        # 가상 청산 (현재가는 engine에서 전달)
        logger.info(f"✅ [PAPER] 청산: {symbol} {qty or 'ALL'} ({reason})")
        
        return {
            'success': True,
            'filled_price': 0.0,  # engine에서 실제 가격 사용
            'qty': qty,
            'order_id': f"PAPER_CLOSE_{int(datetime.now().timestamp() * 1000)}"
        }


class LiveBroker:
    """실거래 브로커 - Binance API"""
    
    def __init__(self, api_key: str, api_secret: str, fee_rate: float = 0.0004):
        self.client = Client(api_key, api_secret)
        self.fee_rate = fee_rate
        self.tpsl_orders = {}  # {position_id: [order_ids]}
        logger.info(f"✅ LiveBroker 초기화 (실거래)")
    
    def execute(self, decision: dict, qty: float) -> dict:
        """Binance API 실제 실행 (One-Way Mode)"""
        side = decision.get('side')
        symbol = decision.get('symbol', 'BTCUSDT')
        qty = float(qty)  # Decimal → float 변환
        
        try:
            if side == 'LONG':
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=qty,
                    positionSide='BOTH'  # ⭐ One-Way Mode
                )
            else:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=qty,
                    positionSide='BOTH'  # ⭐ One-Way Mode
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
    
    def create_tpsl_orders(self, position: dict, tp_prices: list = None, sl_price: float = None) -> dict:
        """
        TP/SL 조건부 주문 등록 (Binance API)
        
        Args:
            position: 포지션 정보 {'id': int, 'symbol': str, 'side': str, 'qty': float}
            tp_prices: TP 가격 리스트 [tp1, tp2] (분할 익절)
            sl_price: SL 가격
        
        Returns:
            {'success': bool, 'order_ids': [...]}
        """
        try:
            position_id = position['id']
            symbol = position['symbol']
            side = position['side']
            total_qty = position['qty']
            
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            order_ids = []
            
            # SL 주문 (전체 청산)
            if sl_price:
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    closePosition=True,  # 전체 청산
                    positionSide='BOTH'
                )
                order_ids.append(sl_order['orderId'])
                logger.info(f"✅ [LIVE] SL 주문 등록: {symbol} @ ${sl_price:.2f}")
            
            # TP1 주문 (30%)
            if tp_prices and len(tp_prices) > 0:
                tp1_qty = round(total_qty * 0.3, 4)
                tp1_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp_prices[0],
                    quantity=tp1_qty,
                    positionSide='BOTH'
                )
                order_ids.append(tp1_order['orderId'])
                logger.info(f"✅ [LIVE] TP1 주문 등록: {symbol} @ ${tp_prices[0]:.2f} ({tp1_qty:.4f})")
            
            # TP2 주문 (40%)
            if tp_prices and len(tp_prices) > 1:
                tp2_qty = round(total_qty * 0.4, 4)
                tp2_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp_prices[1],
                    quantity=tp2_qty,
                    positionSide='BOTH'
                )
                order_ids.append(tp2_order['orderId'])
                logger.info(f"✅ [LIVE] TP2 주문 등록: {symbol} @ ${tp_prices[1]:.2f} ({tp2_qty:.4f})")
            
            # 주문 ID 저장
            self.tpsl_orders[position_id] = order_ids
            
            return {'success': True, 'order_ids': order_ids}
            
        except BinanceAPIException as e:
            logger.error(f"❌ TP/SL 주문 등록 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_sl_price(self, position_id: int, symbol: str, new_sl_price: float) -> dict:
        """
        트레일링 스톱 가격 업데이트 (Modify Order API)
        
        Args:
            position_id: 포지션 ID
            symbol: 심볼
            new_sl_price: 새 SL 가격
        
        Returns:
            {'success': bool}
        """
        try:
            # 기존 SL 주문 ID 조회
            order_ids = self.tpsl_orders.get(position_id, [])
            if not order_ids:
                logger.warning(f"⚠️ 포지션 {position_id} SL 주문 없음")
                return {'success': False, 'error': 'No SL order found'}
            
            # 첫 번째 주문이 SL (STOP_MARKET)
            sl_order_id = order_ids[0]
            
            # Modify Order API
            self.client.futures_modify_order(
                orderId=sl_order_id,
                symbol=symbol,
                stopPrice=new_sl_price
            )
            
            logger.info(f"📈 [LIVE] SL 가격 업데이트: {symbol} → ${new_sl_price:.2f}")
            return {'success': True}
            
        except BinanceAPIException as e:
            logger.error(f"❌ SL 업데이트 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """
        주문 취소
        
        Args:
            symbol: 심볼
            order_id: 주문 ID
        
        Returns:
            {'success': bool}
        """
        try:
            self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            logger.info(f"✅ [LIVE] 주문 취소: {symbol} #{order_id}")
            return {'success': True}
        except BinanceAPIException as e:
            logger.error(f"❌ 주문 취소 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_account_balance(self) -> dict:
        """
        계정 자산 조회 (GET /fapi/v2/balance)
        
        Returns:
            {'success': bool, 'balances': [...]}
        """
        try:
            balances = self.client.futures_account_balance()
            logger.debug(f"✅ [LIVE] 자산 조회: {len(balances)}개")
            return {'success': True, 'balances': balances}
        except BinanceAPIException as e:
            logger.error(f"❌ 자산 조회 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_positions(self) -> dict:
        """
        포지션 조회 (GET /fapi/v2/positionRisk)
        
        Returns:
            {'success': bool, 'positions': [...]}
        """
        try:
            positions = self.client.futures_position_information()
            # 실제 포지션만 필터링 (positionAmt != 0)
            open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            logger.debug(f"✅ [LIVE] 포지션 조회: {len(open_positions)}개 OPEN")
            return {'success': True, 'positions': open_positions}
        except BinanceAPIException as e:
            logger.error(f"❌ 포지션 조회 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_position(self, position_id: int, symbol: str, side: str, qty: float, reason: str = '') -> dict:
        """
        포지션 청산 (부분/전체)
        
        Args:
            position_id: 포지션 ID
            symbol: 심볼
            side: 원래 방향 ('LONG' or 'SHORT')
            qty: 청산 수량 (None = 전체)
            reason: 청산 이유
        
        Returns:
            {'success': bool, 'filled_price': float, ...}
        """
        try:
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            
            # 전체 청산
            if qty is None:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='MARKET',
                    closePosition=True,
                    positionSide='BOTH'
                )
            else:
                # 부분 청산
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='MARKET',
                    quantity=float(qty),
                    positionSide='BOTH'
                )
            
            filled_price = float(order['avgPrice'])
            logger.info(f"✅ [LIVE] 청산: {symbol} {qty or 'ALL'} @ ${filled_price:.2f} ({reason})")
            
            return {
                'success': True,
                'filled_price': filled_price,
                'qty': qty,
                'order_id': order['orderId']
            }
            
        except BinanceAPIException as e:
            logger.error(f"❌ 청산 실패: {e}")
            return {'success': False, 'error': str(e)}
