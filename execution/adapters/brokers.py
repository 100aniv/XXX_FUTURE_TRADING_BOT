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
    
    def __init__(self, fee_rate: float = 0.0004, slippage_pct: float = 0.0005, config: dict = None):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        self.virtual_orders = []
        self.virtual_tpsl_orders = {}  # {position_id: [order_dicts]}
        
        # ⭐ PR12: 초기 자본 설정 (포트폴리오와 동기화 용도)
        self.config = config or {}
        self.equity = self.config.get('capital', {}).get('initial', 50000)
        
        logger.info(f"✅ PaperBroker 초기화: Equity=${self.equity:,.0f}")
    
    def execute(self, decision: dict, qty: float, atr: float = None) -> dict:
        """
        ⭐ PHASE7-2 Phase 2: 가상 실행 (동적 슬리피지)
        
        Args:
            decision: ensemble 결정 {'side': 'LONG', 'entry': 100, ...}
            qty: 수량
            atr: ATR 값 (동적 슬리피지 계산용, None이면 고정값 사용)
        
        Returns:
            체결 결과 {'success': bool, 'filled_price': float, ...}
        """
        side = decision.get('side')
        price = float(decision.get('entry', 0))
        qty = float(qty)  # Decimal → float 변환
        
        # ⭐ PHASE7-2 Phase 2: 동적 슬리피지 계산
        if atr:
            from common.calculations import calculate_dynamic_slippage
            slip = calculate_dynamic_slippage(atr, price, 'MARKET', self.config, mode='paper')
        else:
            slip = self.slippage_pct  # 기존 고정값 폴백 (하위 호환)
        
        # 슬리피지 적용
        if side == 'LONG':
            filled_price = price * (1 + slip)
        else:
            filled_price = price * (1 - slip)
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
        logger.info(f"📄 [PAPER] {side} @ {filled_price:.2f} qty={qty:.4f} (slip={slip*100:.2f}%)")
        
        return order
    
    def create_sl_order(self, position: dict, sl_price: float,
                        working_type: str = 'CONTRACT_PRICE',
                        price_protect: str = 'TRUE') -> dict:
        """
        SL 주문만 등록 (가상, Option C)
        
        Args:
            position: 포지션 정보 {'id': int, 'symbol': str, 'side': str, 'qty': float}
            sl_price: SL 가격
            working_type: 트리거 가격 기준 ('MARK_PRICE' | 'CONTRACT_PRICE')
            price_protect: 가격 보호 활성화 ('TRUE' | 'FALSE')
        
        Returns:
            {'success': bool, 'order_id': str}
        """
        position_id = position['id']
        symbol = position['symbol']
        side = position['side']
        
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        
        # ⭐ PR10: SL 가상 주문 (LiveBroker와 동일 파라미터)
        sl_order = {
            'id': f"PAPER_SL_{int(datetime.now().timestamp() * 1000)}",
            'symbol': symbol,
            'side': close_side,
            'type': 'STOP_MARKET',
            'stopPrice': sl_price,
            'closePosition': True,
            'positionSide': 'BOTH',
            'workingType': working_type,
            'priceProtect': price_protect
        }
        
        # 가상 SL 주문 저장
        if not hasattr(self, 'virtual_sl_orders'):
            self.virtual_sl_orders = {}
        self.virtual_sl_orders[position_id] = sl_order['id']
        
        logger.info(f"✅ [PAPER] SL 주문 등록: {symbol} @ ${sl_price:.2f}")
        return {'success': True, 'order_id': sl_order['id']}
    
    def update_sl_price(self, position_id: int, symbol: str, side: str, new_sl_price: float) -> dict:
        """
        트레일링 스톱 가격 업데이트 (가상)
        
        Args:
            position_id: 포지션 ID
            symbol: 심볼
            side: 원래 방향 ('LONG' or 'SHORT')
            new_sl_price: 새 SL 가격
        
        Returns:
            {'success': bool}
        """
        if not hasattr(self, 'virtual_sl_orders'):
            self.virtual_sl_orders = {}
            
        order_id = self.virtual_sl_orders.get(position_id)
        if not order_id:
            logger.warning(f"⚠️ [PAPER] 포지션 {position_id} SL 주문 없음")
            return {'success': False, 'error': 'No SL order found'}
        
        # 가상 SL 가격 업데이트
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
        return {
            'success': True, 
            'balances': [{
                'asset': 'USDT',
                'balance': str(self.equity),
                'withdrawAvailable': str(self.equity)
            }]
        }
        
    def sync_equity_with_exchange(self) -> float:
        """
        ⭐ PR12: 가상 자산 반환 (동기화 불필요)
        
        Returns:
            float: 현재 가용 USDT 자산
        """
        # 페이퍼 모드에서는 내부 저장값 반환
        logger.debug(f"✅ [PAPER] 자산 동기화 (내부 고정값: ${self.equity:,.2f})")
        return self.equity
    
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
        # API 키/시크릿 기본 검증
        if not api_key or len(api_key) < 10:
            logger.error(f"❌ [LIVE API] 유효하지 않은 API 키 형식 (길이: {len(api_key) if api_key else 0})")  
        if not api_secret or len(api_secret) < 10:
            logger.error(f"❌ [LIVE API] 유효하지 않은 API 시크릿 형식")
            
        self.client = Client(api_key, api_secret)
        self.fee_rate = fee_rate
        self.tpsl_orders = {}  # {position_id: [order_ids]}
        
        # API 키 마스킹하여 로그 출력
        masked_key = api_key[:4] + '...' + api_key[-4:] if len(api_key) > 8 else "유효하지 않은 키"
        logger.info(f"✅ LiveBroker 초기화 (API 키: {masked_key})")  
        
        # 초기화 시 API 연결 테스트 수행
        connection_status = self.check_api_connection()
        if connection_status['success']:
            logger.info(f"✅ [LIVE API] 연결 테스트 성공: ${connection_status.get('wallet_balance', 0):,.2f} USDT")
        else:
            logger.error(f"❌ [LIVE API] 연결 테스트 실패: {connection_status.get('error', '알 수 없는 오류')}")
        
    
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
    
    def create_sl_order(self, position: dict, sl_price: float, 
                        working_type: str = 'CONTRACT_PRICE',
                        price_protect: str = 'TRUE') -> dict:
        """
        SL 주문만 등록 (Binance API, Option C)
        
        Args:
            position: 포지션 정보 {'id': int, 'symbol': str, 'side': str, 'qty': float}
            sl_price: SL 가격
            working_type: 트리거 가격 기준 ('MARK_PRICE' | 'CONTRACT_PRICE')
            price_protect: 가격 보호 활성화 ('TRUE' | 'FALSE')
        
        Returns:
            {'success': bool, 'order_id': int}
        """
        try:
            position_id = position['id']
            symbol = position['symbol']
            side = position['side']
            
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            
            # ⭐ PR10: SL 주문 (workingType + priceProtect 추가)
            sl_order = self.client.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=sl_price,
                closePosition=True,
                positionSide='BOTH',
                workingType=working_type,      # 트리거 가격 기준
                priceProtect=price_protect     # Flash crash/pump 보호
            )
            
            # SL 주문 ID 저장
            if not hasattr(self, 'sl_orders'):
                self.sl_orders = {}
            self.sl_orders[position_id] = sl_order['orderId']
            
            logger.info(f"✅ [LIVE] SL 주문 등록: {symbol} @ ${sl_price:.2f} (Order ID: {sl_order['orderId']})")
            return {'success': True, 'order_id': sl_order['orderId']}
            
        except BinanceAPIException as e:
            logger.error(f"❌ [LIVE] SL 주문 등록 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_sl_price(self, position_id: int, symbol: str, side: str, new_sl_price: float) -> dict:
        """
        트레일링 스톱 가격 업데이트 (Modify Order 우선, Cancel&Replace 폴백)
        
        Args:
            position_id: 포지션 ID
            symbol: 심볼
            side: 원래 방향 ('LONG' or 'SHORT')
            new_sl_price: 새 SL 가격
        
        Returns:
            {'success': bool}
        """
        try:
            # 기존 SL 주문 ID 조회
            if not hasattr(self, 'sl_orders'):
                self.sl_orders = {}
            
            sl_order_id = self.sl_orders.get(position_id)
            if not sl_order_id:
                logger.warning(f"⚠️ [LIVE] 포지션 {position_id} SL 주문 없음")
                return {'success': False, 'error': 'No SL order found'}
            
            # 1순위: Modify Order 시도
            try:
                self.client.futures_modify_order(
                    orderId=sl_order_id,
                    symbol=symbol,
                    stopPrice=new_sl_price
                )
                logger.info(f"📈 [LIVE] SL 가격 업데이트 (Modify): {symbol} → ${new_sl_price:.2f}")
                return {'success': True, 'method': 'modify'}
                
            except (BinanceAPIException, AttributeError) as modify_error:
                # 2순위: Cancel & Replace 폴백
                logger.warning(f"⚠️ [LIVE] Modify 실패, Cancel&Replace 시도: {modify_error}")
                
                try:
                    # 기존 SL 취소
                    self.client.futures_cancel_order(
                        symbol=symbol,
                        orderId=sl_order_id
                    )
                    
                    # 새 SL 등록
                    close_side = 'SELL' if side == 'LONG' else 'BUY'
                    new_sl_order = self.client.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='STOP_MARKET',
                        stopPrice=new_sl_price,
                        closePosition=True,
                        positionSide='BOTH'
                    )
                    
                    # 새 주문 ID 저장
                    self.sl_orders[position_id] = new_sl_order['orderId']
                    
                    logger.info(f"📈 [LIVE] SL 가격 업데이트 (Cancel&Replace): {symbol} → ${new_sl_price:.2f}")
                    return {'success': True, 'method': 'cancel_replace'}
                    
                except BinanceAPIException as replace_error:
                    logger.error(f"❌ [LIVE] SL 업데이트 완전 실패: {replace_error}")
                    return {'success': False, 'error': str(replace_error)}
            
        except Exception as e:
            logger.error(f"❌ [LIVE] SL 업데이트 오류: {e}")
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
            
    def check_api_connection(self) -> dict:
        """
        API 연결 및 권한 진단 함수
        
        Returns:
            dict: {'success': bool, 'wallet_balance': float, 'error': str}
        """
        try:
            # 1. 서버 시간 확인 (가장 기본적인 API 호출)
            try:
                server_time = self.client.get_server_time()
                logger.info(f"✅ [LIVE API] 서버 시간 확인 성공: {server_time}")
            except Exception as e:
                logger.error(f"❌ [LIVE API] 서버 시간 확인 실패: {e}")
                return {'success': False, 'error': f'서버 시간 확인 실패: {e}'}
            
            # 2. 계정 정보 확인
            try:
                account = self.client.futures_account()
                total_wallet_balance = float(account['totalWalletBalance'])
                available_balance = float(account['availableBalance'])
                logger.info(f"✅ [LIVE API] 계정 확인 성공: 총 잔고=${total_wallet_balance:,.2f}, 가용=${available_balance:,.2f}")
            except Exception as e:
                logger.error(f"❌ [LIVE API] 계정 정보 확인 실패: {e}")
                return {'success': False, 'error': f'계정 정보 확인 실패: {e}'}
            
            # 3. 권한 확인 시도
            try:
                api_permissions = self.client.get_api_permissions()
                futures_enabled = api_permissions.get('enableFutures', False)
                logger.info(f"✅ [LIVE API] 권한 확인: Futures={futures_enabled}")
            except Exception as e:
                logger.warning(f"⚠️ [LIVE API] 권한 확인 실패 (무시됨): {e}")
            
            return {
                'success': True,
                'wallet_balance': total_wallet_balance,
                'available_balance': available_balance
            }
        except Exception as e:
            logger.error(f"❌ [LIVE API] 연결 진단 실패: {e.__class__.__name__} - {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def sync_equity_with_exchange(self) -> float:
        """
        ⭐ PR12: 거래소 자산과 동기화
        
        Returns:
            float: 현재 가용 USDT 자산
            
        Raises:
            Exception: 동기화 실패 시
        """
        logger.info(f"\u231b [LIVE] 거래소 자산 동기화 시도 (Binance Futures API)")
        try:
            # 재시도
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = self.get_account_balance()
                    break
                except Exception as retry_err:
                    if attempt < max_retries - 1:
                        logger.warning(f"\u26a0️ [LIVE] 자산 조회 재시도 ({attempt+1}/{max_retries}): {retry_err}")
                        time.sleep(1)
                    else:
                        raise
                        
            if not result['success']:
                logger.error(f"\u274c [LIVE] 자산 동기화 실패: {result.get('error')}")
                return 0.0
            
            # 'USDT' 잔고 찾기
            logger.info(f"\u2705 [LIVE] 자산 조회 성공: {len(result['balances'])}개 자산 정보 받음")
            for balance in result['balances']:
                logger.debug(f"\u2139️ [LIVE] 자산: {balance['asset']} = {balance['balance']}")
                if balance['asset'] == 'USDT':
                    equity = float(balance['balance'])
                    logger.info(f"\u2705 [LIVE] 거래소 자산 동기화 성공: ${equity:,.2f} USDT")
                    return equity
            
            # USDT 잔고가 없는 경우 상세 로깅
            assets = [f"{b['asset']}:{b['balance']}" for b in result['balances'][:5]]
            logger.error(f"\u274c [LIVE] USDT 잔고를 찾을 수 없음. 가용 자산: {', '.join(assets)}...")
            return 0.0
            
        except Exception as e:
            logger.error(f"\u274c [LIVE] 자산 동기화 오류: {e}")
            return 0.0
    
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
        포지션 청산 (부분/전체, reduceOnly 보장)
        
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
                # 부분 청산 (reduceOnly=True)
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='MARKET',
                    quantity=float(qty),
                    reduceOnly=True,  # ⭐ Option C: 반대 포지션 방지
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
            logger.error(f"❌ [LIVE] 청산 실패: {e}")
            return {'success': False, 'error': str(e)}
