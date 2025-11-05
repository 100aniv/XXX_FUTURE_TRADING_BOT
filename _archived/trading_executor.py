#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Executor - 매매 실행 & 포지션 추적
==========================================
⚠️  리팩토링 완료: execution/ 모듈로 분리됨

이 파일은 더 이상 사용되지 않습니다.
새로운 구조:
- execution/executor.py: TradingExecutor 클래스 (라인 30-278)
- execution/position_sizer.py: PositionSizer 클래스 (라인 289-376)
- execution/risk_manager.py: RiskManager 클래스 (라인 387-533)
- execution/position_tracker.py: PositionTracker 클래스 (라인 540-661)

참고: docs/implementation/EXECUTION_MODULE_REFACTORING.md
"""
import os
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# ============================================
# 0. LOGGING (로그 설정) - 공통 모듈 사용
# ============================================
from common.logger import setup_logger
from common.calculations import tp_from_rr
logger = setup_logger(__name__, log_type="trading")


# ============================================
# 1. TRADING EXECUTOR (주문 실행 엔진)
# ============================================
class TradingExecutor:
    """
    주문 실행 전담 (본질만)
    
    Attributes:
        mode (str): 'backtest' | 'paper' | 'live'
        client: Binance API 클라이언트 (live 모드만)
    """
    
    def __init__(self, mode='backtest', binance_api_key=None, binance_secret=None):
        """
        초기화
        
        Args:
            mode: 'backtest' | 'paper' | 'live'
            binance_api_key: Binance API 키 (live 모드 필수)
            binance_secret: Binance Secret (live 모드 필수)
        """
        self.mode = mode
        self.client = None
        
        # ⭐ 핵심 컴포넌트 초기화
        self.position_sizer = PositionSizer()
        self.risk_manager = RiskManager()
        
        # Live 모드: Binance 클라이언트 초기화
        if mode == 'live':
            if not binance_api_key or not binance_secret:
                raise ValueError("Live 모드는 API 키가 필요합니다")
            try:
                from binance.client import Client
                self.client = Client(binance_api_key, binance_secret)
                logger.info("✅ Binance 클라이언트 연결 성공")
            except Exception as e:
                logger.error(f"❌ Binance 클라이언트 연결 실패: {e}")
                raise
        
        logger.info(f"✅ TradingExecutor 초기화 완료 (모드: {mode})")
    
    # ============================================
    # 2. ORDER EXECUTION (주문 실행)
    # ============================================
    
    def execute_order(self, signal: Dict) -> Optional[Dict]:
        """
        신호를 받아서 주문 실행
        
        Args:
            signal: {
                'symbol': str,
                'side': 'BUY' | 'SELL',
                'entry_price': float,
                'sl_price': float,
                'tp_price': float,
                'confidence': float (optional)
            }
        
        Returns:
            주문 결과 또는 None
        """
        # 1️⃣ 포지션 사이징 (동적)
        qty, sizing_meta = self.position_sizer.calculate(signal)
        if qty <= 0:
            logger.warning(f"❌ 수량 계산 실패: {signal['symbol']} - {sizing_meta.get('reason', 'unknown')}")
            return None
        
        logger.info(f"📊 포지션 사이징: {signal['symbol']}")
        logger.info(f"   Base QTY: {sizing_meta.get('base_qty', 0):.3f}")
        logger.info(f"   Quality Weight: {sizing_meta.get('quality_weight', 1.0):.2f}")
        logger.info(f"   Final QTY: {qty:.3f} (Value: ${sizing_meta.get('position_value', 0):.2f})")
        
        # 2️⃣ 리스크 체크
        allowed, reason = self.risk_manager.check_order(signal, qty)
        if not allowed:
            logger.warning(f"🚫 리스크 체크 실패: {reason}")
            return None
        
        logger.info(f"✅ 리스크 체크 통과: {signal['symbol']}")
        
        # 3️⃣ 모드별 실행
        if self.mode == 'backtest':
            result = self._backtest_order(signal, qty)
        elif self.mode == 'paper':
            result = self._paper_order(signal, qty)
        elif self.mode == 'live':
            result = self._live_order(signal, qty)
        else:
            logger.error(f"❌ 알 수 없는 모드: {self.mode}")
            return None
        
        # 4️⃣ 성공 시 리스크 매니저 업데이트
        if result and result.get('status') in ['FILLED', 'success']:
            position_value = qty * signal['entry_price']
            self.risk_manager.add_position(signal['symbol'], position_value)
            logger.info(f"✅ 주문 체결: {signal['symbol']} x{qty:.3f}")
        
        return result
    
    def _backtest_order(self, signal: Dict, qty: float) -> Dict:
        """
        Backtest: 과거 데이터 시뮬레이션
        - 슬리피지 적용 (0.05%)
        - 즉시 체결
        """
        slippage = 0.0005  # 0.05% 슬리피지
        entry = signal['entry_price']
        
        if signal['side'] == 'LONG':
            fill_price = entry * (1 + slippage)
        else:  # SHORT
            fill_price = entry * (1 - slippage)
        
        order = {
            'order_id': f"BT_{int(time.time() * 1000)}",
            'symbol': signal['symbol'],
            'side': signal['side'],
            'qty': qty,
            'fill_price': fill_price,
            'status': 'FILLED',
            'timestamp': datetime.now()
        }
        
        logger.info(f"📊 [BACKTEST] {signal['symbol']} {signal['side']} @ {fill_price:.2f} qty={qty}")
        return order
    
    def _paper_order(self, signal: Dict, qty: float) -> Dict:
        """
        Paper Trading: 실시간 가상 주문
        - 슬리피지 없음
        - 즉시 체결
        """
        order = {
            'order_id': f"PP_{int(time.time() * 1000)}",
            'symbol': signal['symbol'],
            'side': signal['side'],
            'qty': qty,
            'fill_price': signal['entry_price'],
            'status': 'FILLED',
            'timestamp': datetime.now()
        }
        
        logger.info(f"📄 [PAPER] {signal['symbol']} {signal['side']} @ {signal['entry_price']:.2f} qty={qty}")
        return order
    
    def _live_order_with_retry(self, signal: Dict, qty: float, max_retries=3) -> Optional[Dict]:
        """
        Live Trading: 실제 주문 (재시도 로직)
        """
        for attempt in range(max_retries):
            try:
                # Binance Futures 주문
                order = self.client.futures_create_order(
                    symbol=signal['symbol'],
                    side='BUY' if signal['side'] == 'LONG' else 'SELL',
                    type='MARKET',
                    quantity=qty
                )
                
                logger.info(f"💰 [LIVE] {signal['symbol']} {signal['side']} 주문 ID: {order['orderId']}")
                
                # 체결 확인
                filled_order = self._wait_for_fill(order['orderId'], signal['symbol'])
                
                if filled_order:
                    return {
                        'order_id': str(order['orderId']),
                        'symbol': signal['symbol'],
                        'side': signal['side'],
                        'qty': float(filled_order['executedQty']),
                        'fill_price': float(filled_order['avgPrice']),
                        'status': filled_order['status'],
                        'timestamp': datetime.now()
                    }
                
            except Exception as e:
                logger.warning(f"⚠️  [LIVE] 주문 시도 {attempt + 1}/{max_retries} 실패: {e}")
                
                if attempt < max_retries - 1:
                    # 지수 백오프 (1초, 2초, 4초)
                    wait_time = 2 ** attempt
                    logger.info(f"   {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ [LIVE] 최종 주문 실패: {signal['symbol']}")
        
        return None
    
    def _wait_for_fill(self, order_id: str, symbol: str, timeout=10) -> Optional[Dict]:
        """
        주문 체결 확인 (최대 10초 대기)
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                order = self.client.futures_get_order(
                    symbol=symbol,
                    orderId=order_id
                )
                
                if order['status'] == 'FILLED':
                    logger.info(f"✅ [LIVE] 체결 완료: {symbol} ID={order_id}")
                    return order
                elif order['status'] in ['CANCELED', 'REJECTED', 'EXPIRED']:
                    logger.error(f"❌ [LIVE] 주문 실패: {order['status']}")
                    return None
                
                # 0.5초 대기 후 재확인
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"⚠️  체결 확인 에러: {e}")
                time.sleep(0.5)
        
        logger.warning(f"⏱️  [LIVE] 체결 확인 타임아웃: {symbol}")
        return None
    
    # ============================================
    # 3. UTILITIES (유틸리티)
    # ============================================
    
    def _calculate_qty(self, signal: Dict) -> float:
        """
        포지션 크기 계산 (리스크 기반)
        """
        equity = float(os.getenv('EQUITY_USDT', '10000'))
        risk_pct = float(os.getenv('RISK_PER_TRADE', '0.01'))
        
        risk_usdt = equity * risk_pct
        entry = signal['entry_price']
        sl = signal['sl_price']
        
        dist = abs(entry - sl)
        if dist <= 0:
            return 0.0
        
        qty = risk_usdt / dist
        
        # 거래소 최소 수량 확인
        min_qty = 0.001
        if qty < min_qty:
            return 0.0
        
        return round(qty, 3)
    
    def get_mode(self) -> str:
        """현재 모드 반환"""
        return self.mode


# ============================================
# 2. POSITION SIZER (포지션 사이징)
# ============================================
# 리팩토링 시: execution/position_sizer.py로 분리
# - 리스크 기반 기본 계산
# - 신호 품질 가중치 (confidence, experience 등)
# - ATR/변동성 조절
# - Kelly Criterion (선택)
# ============================================
class PositionSizer:
    """
    포지션 크기 동적 계산
    (업계 표준: Risk-per-trade + Quality weighting)
    """
    
    def __init__(self):
        # 기본 설정
        self.equity = float(os.getenv('EQUITY_USDT', '10000'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.01'))  # 1%
        
        # 품질 가중치 범위
        self.quality_weight_min = float(os.getenv('QUALITY_WEIGHT_MIN', '0.7'))
        self.quality_weight_max = float(os.getenv('QUALITY_WEIGHT_MAX', '1.3'))
        
        # 포지션 한도
        self.max_position_value = float(os.getenv('MAX_POSITION_VALUE', '5000'))
        self.min_position_value = float(os.getenv('MIN_POSITION_VALUE', '10'))
        
        logger.info(f"✅ PositionSizer 초기화: Equity={self.equity}, RPT={self.risk_per_trade}")
    
    def calculate(self, signal: Dict) -> Tuple[float, Dict]:
        """
        포지션 크기 계산
        
        Args:
            signal: {
                'entry_price': float,
                'sl_price': float,
                'confidence': float (0~1, 선택),
                'atr': float (선택),
                'symbol': str
            }
        
        Returns:
            (qty, metadata)
        """
        entry = signal['entry_price']
        sl = signal['sl_price']
        
        # 1) 기본 리스크 기반 계산
        stop_distance = abs(entry - sl)
        if stop_distance <= 0:
            return 0.0, {"reason": "invalid_stop"}
        
        risk_usdt = self.equity * self.risk_per_trade
        base_qty = risk_usdt / stop_distance
        
        # 2) 품질 가중치 적용 (confidence 있으면)
        quality_weight = self._calculate_quality_weight(signal)
        adjusted_qty = base_qty * quality_weight
        
        # 3) 포지션 가치 한도 적용
        position_value = adjusted_qty * entry
        if position_value > self.max_position_value:
            adjusted_qty = self.max_position_value / entry
        elif position_value < self.min_position_value:
            return 0.0, {"reason": "below_min_value"}
        
        # 4) 거래소 최소 수량
        final_qty = round(adjusted_qty, 3)
        if final_qty < 0.001:
            return 0.0, {"reason": "below_min_qty"}
        
        metadata = {
            "risk_usdt": risk_usdt,
            "stop_distance": stop_distance,
            "quality_weight": quality_weight,
            "base_qty": base_qty,
            "final_qty": final_qty,
            "position_value": final_qty * entry
        }
        
        return final_qty, metadata
    
    def _calculate_quality_weight(self, signal: Dict) -> float:
        """
        신호 품질 기반 가중치
        (나중에 ensemble confidence, experience_score 등 추가 가능)
        """
        confidence = signal.get('confidence', 0.8)  # 기본값 0.8
        
        # 간단한 선형 맵핑: 0.5 → 0.7, 1.0 → 1.3
        weight = self.quality_weight_min + (confidence - 0.5) * 1.2
        
        # 범위 제한
        return max(self.quality_weight_min, min(weight, self.quality_weight_max))


# ============================================
# 3. RISK MANAGER (리스크 관리)
# ============================================
# 리팩토링 시: execution/risk_manager.py로 분리
# - 일일 손실 한도
# - 동시 포지션 수 제한
# - 심볼별/전략별 한도
# - 순노출 한도
# ============================================
class RiskManager:
    """
    리스크 관리 및 한도 체크
    (업계 표준: Daily loss limit + Position limits + Flash Guard)
    """
    
    def __init__(self, config=None):
        # 일일 한도
        self.daily_loss_limit_pct = float(os.getenv('DAILY_LOSS_LIMIT_PCT', '0.03'))  # 3%
        self.daily_loss_limit = self.daily_loss_limit_pct * float(os.getenv('EQUITY_USDT', '10000'))
        
        # 포지션 한도
        self.max_positions = int(os.getenv('MAX_CONCURRENT_POSITIONS', '5'))
        self.max_exposure_per_symbol_pct = float(os.getenv('MAX_EXPOSURE_PER_SYMBOL_PCT', '0.3'))  # 30%
        
        # 현재 상태 (나중에 DB에서 읽기)
        self.current_daily_loss = 0.0
        self.active_positions_count = 0
        self.symbol_exposures = {}  # {symbol: position_value}
        
        # Flash Guard (급등락 감지 - Circuit Breaker)
        self.config = config or {}
        self.flash_buffers = {}  # {symbol: deque[(ts_ms, price)]}
        self.flash_pause_until = {}  # {symbol: pause_until_ts}
        
        logger.info(f"✅ RiskManager 초기화: Daily limit={self.daily_loss_limit:.2f}")
    
    # ============================================
    # Flash Guard (급등락 감지 - Circuit Breaker)
    # ============================================
    def _tf_ms(self) -> int:
        """타임프레임을 밀리초로 변환"""
        tf = self.config.get("timeframe", "5m")
        if tf.endswith("m"): return int(tf[:-1]) * 60 * 1000
        if tf.endswith("h"): return int(tf[:-1]) * 60 * 60 * 1000
        if tf.endswith("d"): return int(tf[:-1]) * 24 * 60 * 60 * 1000
        return 5*60*1000
    
    def flash_guard_update(self, symbol: str, price: float, ts_ms: int):
        """
        Flash Guard 업데이트 (급등락 감지)
        
        Args:
            symbol: 심볼
            price: 현재 가격
            ts_ms: 타임스탬프 (ms)
        """
        if not self.config.get("enable_flash_guard", False):
            return
        
        from collections import deque
        
        # Buffer 초기화
        if symbol not in self.flash_buffers:
            self.flash_buffers[symbol] = deque(maxlen=600)
        
        buf = self.flash_buffers[symbol]
        buf.append((ts_ms, price))
        
        # 윈도우 밖 데이터 제거
        window = self.config.get("flash_window_sec", 60) * 1000
        while buf and ts_ms - buf[0][0] > window:
            buf.popleft()
        
        # 변동률 체크
        if len(buf) >= 2:
            p0 = buf[0][1]
            change = abs(price - p0) / p0
            flash_pct = self.config.get("flash_pct", 0.03)
            
            if change >= flash_pct:
                pause_candles = self.config.get("flash_pause_candles", 3)
                self.flash_pause_until[symbol] = ts_ms + self._tf_ms() * pause_candles
                logger.warning(f"🛡 {symbol} Flash-Guard: {self.config.get('flash_window_sec', 60)}초에 닱{change*100:.2f}% 변동 → 신호 일시 보류")
    
    def flash_guard_allowed(self, symbol: str, ts_ms: int) -> bool:
        """
        Flash Guard 허용 여부 확인
        
        Args:
            symbol: 심볼
            ts_ms: 타임스탬프 (ms)
        
        Returns:
            bool: 허용 여부
        """
        until = self.flash_pause_until.get(symbol)
        if not until:
            return True
        return ts_ms >= until
    
    
    # ============================================
    # Pre-Trade Risk Checks
    # ============================================
    def check_order(self, signal: Dict, qty: float) -> Tuple[bool, str]:
        """
        주문 실행 전 리스크 체크
        
        Returns:
            (allowed, reason)
        """
        symbol = signal.get('symbol', 'UNKNOWN')
        position_value = qty * signal['entry_price']
        
        # 1) 일일 손실 한도 체크
        if abs(self.current_daily_loss) >= self.daily_loss_limit:
            return False, f"일일 손실 한도 초과: {self.current_daily_loss:.2f}"
        
        # 2) 동시 포지션 수 체크
        if self.active_positions_count >= self.max_positions:
            return False, f"동시 포지션 한도 도달: {self.active_positions_count}/{self.max_positions}"
        
        # 3) 심볼별 노출 한도 체크
        equity = float(os.getenv('EQUITY_USDT', '10000'))
        max_per_symbol = equity * self.max_exposure_per_symbol_pct
        current_exposure = self.symbol_exposures.get(symbol, 0.0)
        
        if current_exposure + position_value > max_per_symbol:
            return False, f"심볼별 한도 초과: {symbol} {current_exposure + position_value:.2f} > {max_per_symbol:.2f}"
        
        # 모든 체크 통과
        return True, "OK"
    
    def update_daily_pnl(self, pnl: float):
        """일일 PnL 업데이트"""
        self.current_daily_loss += pnl
        logger.info(f"📊 RiskManager: Daily PnL = {self.current_daily_loss:.2f} / {self.daily_loss_limit:.2f}")
    
    def add_position(self, symbol: str, position_value: float):
        """포지션 추가"""
        self.active_positions_count += 1
        self.symbol_exposures[symbol] = self.symbol_exposures.get(symbol, 0.0) + position_value
        logger.info(f"➕ 포지션 추가: {symbol}, 총 {self.active_positions_count}개")
    
    def remove_position(self, symbol: str, position_value: float):
        """포지션 제거"""
        self.active_positions_count = max(0, self.active_positions_count - 1)
        if symbol in self.symbol_exposures:
            self.symbol_exposures[symbol] = max(0.0, self.symbol_exposures[symbol] - position_value)
        logger.info(f"➖ 포지션 제거: {symbol}, 남은 {self.active_positions_count}개")
    
    def reset_daily(self):
        """일일 리셋 (자정)"""
        self.current_daily_loss = 0.0
        logger.info("📅 RiskManager 일일 리셋")


# ============================================
# 4. POSITION TRACKER (포지션 추적)
# ============================================
# 리팩토링 시: execution/position_tracker.py로 분리
# ============================================
class PositionTracker:
    """
    포지션 추적 및 TP/SL 관리
    (trade_manager.py에서 이동)
    """
    
    def __init__(self, mode='paper'):
        """
        초기화
        
        Args:
            mode: 'backtest' | 'paper' | 'live'
        """
        self.mode = mode
        self.active_positions = {}
        self.daily_pnl = 0.0
        self.today = time.strftime("%Y-%m-%d")
        
        # 설정
        self.tp1_rr = float(os.getenv('TP1_RR', '1.0'))
        self.tp2_rr = float(os.getenv('TP2_RR', '2.0'))
        self.enable_tp_trail = os.getenv('ENABLE_TP_TRAIL', 'true').lower() == 'true'
        self.trail_after_tp1 = os.getenv('TRAIL_AFTER_TP1', 'true').lower() == 'true'
        
        logger.info(f"✅ PositionTracker 초기화 (모드: {mode})")
    
    def track_new_position(self, symbol: str, side: str, entry: float, sl: float, tp: float, qty: float, timestamp: int):
        """새 포지션 추적 시작"""
        position_key = f"{symbol}_{side}_{timestamp}"
        
        # TP1, TP2 계산
        signal_info = {"entry": entry, "sl": sl, "side": side}
        tp1 = tp_from_rr(signal_info, self.tp1_rr) if self.enable_tp_trail else None
        tp2 = tp
        
        self.active_positions[position_key] = {
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "qty": qty,
            "open_ts": timestamp,
            "status": "OPEN",
            "tp1_hit": False
        }
        
        logger.info(f"📊 포지션 추적 시작: {position_key}")
        logger.info(f"   Entry: {entry:.4f}, SL: {sl:.4f}, TP1: {tp1:.4f if tp1 else 'N/A'}, TP2: {tp2:.4f}")
    
    def check_tp_sl(self, symbol: str, price: float, timestamp: int, callback=None):
        """TP/SL 터치 확인 및 청산"""
        # 일자 변경 확인
        today_now = time.strftime("%Y-%m-%d")
        if today_now != self.today:
            self.today = today_now
            self.daily_pnl = 0.0
            logger.info(f"📅 일자 변경: {self.today}, PnL 리셋")
        
        # 각 포지션 확인
        for key, pos in list(self.active_positions.items()):
            if pos["symbol"] != symbol or pos["status"] == "CLOSED":
                continue
            
            side, entry, sl = pos["side"], pos["entry"], pos["sl"]
            tp1, tp2, qty = pos["tp1"], pos["tp2"], pos["qty"]
            is_long = (side == "LONG")
            
            # PnL 계산
            def calc_pnl(exit_price, qty_closed):
                return (exit_price - entry) * qty_closed if is_long else (entry - exit_price) * qty_closed
            
            # SL 체크
            if (is_long and price <= sl) or (not is_long and price >= sl):
                pnl = calc_pnl(sl, qty)
                self.daily_pnl += pnl
                pos["status"] = "CLOSED"
                logger.info(f"🔴 손절: {symbol} {side} @ {sl:.4f}, PnL: {pnl:.2f} USDT")
                if callback:
                    callback(f"🔴 {symbol} 손절 완료: {pnl:.2f} USDT")
                continue
            
            # TP1 체크 (부분익절 50%)
            if tp1 and not pos.get("tp1_hit"):
                if (is_long and price >= tp1) or (not is_long and price <= tp1):
                    pnl = calc_pnl(tp1, qty * 0.5)
                    self.daily_pnl += pnl
                    pos["tp1_hit"] = True
                    if self.trail_after_tp1:
                        pos["sl"] = entry
                    logger.info(f"🟡 TP1 달성: {symbol} @ {tp1:.4f}, PnL: +{pnl:.2f} USDT")
                    if callback:
                        callback(f"🟡 {symbol} TP1 달성: +{pnl:.2f} USDT (50% 청산)")
                    continue
            
            # TP2 체크 (전체 청산)
            if (is_long and price >= tp2) or (not is_long and price <= tp2):
                qty_closed = qty * 0.5 if pos.get("tp1_hit") else qty
                pnl = calc_pnl(tp2, qty_closed)
                self.daily_pnl += pnl
                pos["status"] = "CLOSED"
                logger.info(f"🟢 TP2 완료: {symbol} @ {tp2:.4f}, PnL: +{pnl:.2f} USDT")
                if callback:
                    callback(f"🟢 {symbol} TP2 완료: +{pnl:.2f} USDT")
    
    def get_goal_progress(self) -> str:
        """일일 목표 달성률"""
        equity = float(os.getenv('EQUITY_USDT', '10000'))
        daily_goal_pct = float(os.getenv('DAILY_GOAL_PCT', '0.02'))
        goal = equity * daily_goal_pct
        pct = (self.daily_pnl / goal * 100.0) if goal > 0 else 0.0
        return f"*일일 목표 진행률:* {self.daily_pnl:.2f}/{goal:.2f} USDT ({pct:.1f}%)"
    
    def get_active_positions(self) -> Dict:
        """활성 포지션 조회"""
        return {k: v for k, v in self.active_positions.items() if v["status"] == "OPEN"}
    
    def get_daily_pnl(self) -> float:
        """일일 손익 조회"""
        return self.daily_pnl


# ============================================
# 4. MAIN (테스트용)
# ============================================
# 리팩토링 시: 제거
# - 테스트 코드는 tests/ 디렉터리로 이동
# - 순수 모듈로 사용 (if __name__ 블록 불필요)
# ============================================
if __name__ == "__main__":
    # 테스트: Backtest 모드
    executor = TradingExecutor(mode='backtest')
    tracker = PositionTracker(mode='paper')
    
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 67000.0,
        'sl_price': 66500.0,
        'tp_price': 68000.0,
        'confidence': 0.8
    }
    
    # 주문 실행
    order = executor.execute_order(signal)
    
    if order:
        logger.info(f"📊 주문 결과: {order}")
        
        # 포지션 추적 시작
        tracker.track_new_position(
            symbol=signal['symbol'],
            side=signal['side'],
            entry=signal['entry_price'],
            sl=signal['sl_price'],
            tp=signal['tp_price'],
            qty=order['qty'],
            timestamp=int(time.time() * 1000)
        )
        logger.info(f"포지션 추적 시작: {tracker.get_active_positions()}")
    else:
        logger.error("주문 실패")
