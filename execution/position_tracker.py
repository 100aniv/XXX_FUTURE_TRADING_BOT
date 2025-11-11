#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Tracker
================
포지션 추적 및 관리 (TUNING_VIBLE P1 통합)

역할:
- TP 분할 (TP1 30%, TP2 40%, Trail 30%)
- 트레일링 스탑 업데이트
- TP/SL 체크
- 포지션 상태 관리
"""
from typing import Dict, Tuple, Optional
from common.logger import setup_logger
from execution.tp_manager import TPManager

logger = setup_logger(__name__)


class PositionTracker:
    """포지션 추적 및 관리 (TP 분할 지원)"""
    
    def __init__(self, config: Dict = None):
        """
        Args:
            config: config.yml (exits 섹션 사용)
        """
        self.positions = {}  # {position_id: position_dict}
        self.config = config or {}
        
        # TP Manager 초기화
        self.tp_manager = TPManager(self.config)
    
    def update_trailing_stop(self, position: Dict, current_price: float, config: Dict) -> Dict:
        """
        Trailing Stop 업데이트
        
        Args:
            position: 포지션 딕셔너리
            current_price: 현재 가격
            config: 전략 설정
        
        Returns:
            업데이트된 포지션
        """
        if not config.get('enable_trailing_stop', False):
            return position
        
        entry = position['entry']
        current_sl = position['sl']
        side = position['side']
        
        if side == 'LONG':
            # 2% 이익 시 Break-even
            if current_price > entry * 1.02 and current_sl < entry:
                position['sl'] = entry
                position['trailing_active'] = True
                logger.info(f"🔒 Trailing: SL → Break-even (${entry:,.2f})")
            
            # 3% 이익 시 Trailing 시작
            if position.get('trailing_active') and current_price > entry * 1.03:
                new_sl = current_price * 0.985  # 1.5% 아래
                if new_sl > current_sl:
                    position['sl'] = new_sl
                    logger.info(f"📈 Trailing: SL → ${new_sl:,.2f}")
        
        else:  # SHORT
            # 2% 이익 시 Break-even
            if current_price < entry * 0.98 and current_sl > entry:
                position['sl'] = entry
                position['trailing_active'] = True
                logger.info(f"🔒 Trailing: SL → Break-even (${entry:,.2f})")
            
            # 3% 이익 시 Trailing 시작
            if position.get('trailing_active') and current_price < entry * 0.97:
                new_sl = current_price * 1.015  # 1.5% 위
                if new_sl < current_sl:
                    position['sl'] = new_sl
                    logger.info(f"📉 Trailing: SL → ${new_sl:,.2f}")
        
        return position
    
    def check_tpsl(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """
        TP/SL 체크 (레거시 - 단일 TP/SL)
        
        Args:
            position: 포지션
            current_price: 현재 가격
        
        Returns:
            (should_close, reason)
        """
        side = position['side']
        tp = position['tp']
        sl = position['sl']
        
        if side == 'LONG':
            if current_price >= tp:
                return True, 'TP'
            elif current_price <= sl:
                reason = 'TRAILING_SL' if position.get('trailing_active') else 'SL'
                return True, reason
        else:  # SHORT
            if current_price <= tp:
                return True, 'TP'
            elif current_price >= sl:
                reason = 'TRAILING_SL' if position.get('trailing_active') else 'SL'
                return True, reason
        
        return False, ''
    
    def check_tpsl_with_partial(self, position: Dict, current_price: float, 
                                atr: float = None, candle: Dict = None, config: dict = None) -> Tuple[bool, Optional[float], str]:
        """
        TP 분할 체크 (TUNING_VIBLE P1 + PHASE7-1 OHLC)
        
        ⭐ PHASE7-2 Phase 1: Trailing Stop 조기 활성화 지원
        - config 전달 시: exits.trailing_activate_at 적용 (TP1/TP2)
        - config 미전달 시: 기존 동작 (TP2 이후 trailing)
        
        ⭐ PHASE7-2 Phase 2: SL 청산 가격 슬리피지 적용
        - SL/EXTREME_LOSS 시 동적 슬리피지 반영된 청산 가격 반환
        
        Args:
            position: 포지션
            current_price: 현재 가격
            atr: ATR 값 (트레일링용, 슬리피지 계산용)
            candle: 캠들 OHLC 데이터 (high, low, close)
            config: 설정 딕셔너리 (exits 섹션 포함, PHASE7-2 Phase 1)
        
        Returns:
            (should_action, partial_qty, reason, exit_price)
            - should_action: 액션 필요 여부
            - partial_qty: 부분 청산 수량 (None = 전체 청산)
            - reason: 이유 (TP1/TP2/SL/TRAILING_SL/EXTREME_LOSS)
            - exit_price: 청산 가격 (SL/EXTREME_LOSS 시만 사용, 나머지는 None)
        """
        side = position['side']
        entry = position['entry']
        stop = position['sl']
        total_qty = position['qty']
        
        # ⭐ PHASE7-1: SL 우선 체크 (OHLC 기반)
        # - LONG: candle['low'] <= sl 체크
        # - SHORT: candle['high'] >= sl 체크
        if candle and stop:
            sl_hit = False
            if side == 'SHORT' and candle.get('high', current_price) >= stop:
                sl_hit = True
                logger.warning(
                    f"❌ [SL OHLC] SHORT SL 도달: High ${candle['high']:.6f} >= SL ${stop:.6f} | "
                    f"Entry: ${entry:.6f}"
                )
            elif side == 'LONG' and candle.get('low', current_price) <= stop:
                sl_hit = True
                logger.warning(
                    f"❌ [SL OHLC] LONG SL 도달: Low ${candle['low']:.6f} <= SL ${stop:.6f} | "
                    f"Entry: ${entry:.6f}"
                )
            
            if sl_hit:
                # ⭐ PHASE7-2 Phase 2: SL 청산 가격 슬리피지 적용
                from common.calculations import calculate_dynamic_slippage
                
                # 슬리피지 계산 (ATR 제공 시)
                if atr and config:
                    sl_slip = calculate_dynamic_slippage(atr, stop, 'SL', config)
                    # SL 가격에서 슬리피지만큼 악화
                    exit_price = stop * (1 + sl_slip) if side == 'SHORT' else stop * (1 - sl_slip)
                    logger.warning(
                        f"💸 [SL 슬리피지] {sl_slip*100:.2f}% 적용: "
                        f"SL ${stop:.6f} → 청산 ${exit_price:.6f}"
                    )
                else:
                    exit_price = current_price  # ATR 없으면 현재가 사용 (기존 동작)
                
                reason = 'TRAILING_SL' if position.get('tp2_hit', False) else 'SL'
                return True, None, reason, exit_price  # 전체 청산 + 청산 가격
        
        # ⭐ PHASE7-1: Extreme Loss -20% 체크 (SL 다음 우선순위)
        current_pnl_pct = 0.0
        if side == 'LONG':
            current_pnl_pct = ((current_price - entry) / entry) * 100
        else:  # SHORT
            current_pnl_pct = ((entry - current_price) / entry) * 100
        
        if current_pnl_pct <= -20.0:
            logger.warning(
                f"🚨 [EXTREME_LOSS] 극단 손실 감지: {current_pnl_pct:.2f}% <= -20% | "
                f"Entry: ${entry:.4f} → Current: ${current_price:.4f}"
            )
            # EXTREME_LOSS도 슬리피지 적용 (급격한 손실 시)
            return True, None, 'EXTREME_LOSS', current_price  # 전체 강제 청산
        
        # TP 레벨 확인
        tp_levels = position.get('tp_levels', {})
        if not tp_levels:
            # TP 레벨 없으면 레거시 방식 (SL은 위에서 이미 체크)
            should_close, reason = self.check_tpsl(position, current_price)
            return should_close, None if should_close else 0, reason, None  # exit_price 없음
        
        # TP1 체크
        if not position.get('tp1_hit', False):
            tp1_price = tp_levels.get('tp1')
            if tp1_price:
                if (side == 'LONG' and current_price >= tp1_price) or \
                   (side == 'SHORT' and current_price <= tp1_price):
                    partial_qty = self.tp_manager.calculate_partial_size(total_qty, 1)
                    position['tp1_hit'] = True
                    position['remaining_pct'] = 70.0
                    
                    # ⭐ PHASE7-2 Phase 1: TP1 도달 시 Trailing Stop 활성화
                    if config:
                        exits_config = config.get('exits', {})
                        trailing_activate_at = exits_config.get('trailing_activate_at', 'TP2')
                        if trailing_activate_at == 'TP1':
                            position['trailing_active'] = True
                            position['highest'] = current_price if side == 'LONG' else entry
                            position['lowest'] = entry if side == 'LONG' else current_price
                            logger.info(f"✅ TP1 도달 → Trailing Stop 활성화: {position.get('symbol', 'N/A')}")
                    
                    logger.info(f"🎯 TP1 도달: ${tp1_price:.6f} | 청산 {partial_qty:.4f} (30%)")
                    return True, partial_qty, 'TP1', None  # TP는 current_price 사용
        
        # TP2 체크
        if not position.get('tp2_hit', False) and position.get('tp1_hit', False):
            tp2_price = tp_levels.get('tp2')
            if tp2_price:
                if (side == 'LONG' and current_price >= tp2_price) or \
                   (side == 'SHORT' and current_price <= tp2_price):
                    partial_qty = self.tp_manager.calculate_partial_size(total_qty, 2)
                    position['tp2_hit'] = True
                    position['remaining_pct'] = 30.0
                    
                    # ⭐ PHASE7-2 Phase 1: TP2 도달 시에도 Trailing 활성화 (하위 호환)
                    if not position.get('trailing_active', False):
                        position['trailing_active'] = True
                        position['highest'] = current_price if side == 'LONG' else entry
                        position['lowest'] = entry if side == 'LONG' else current_price
                        logger.info(f"✅ TP2 도달 → Trailing Stop 활성화: {position.get('symbol', 'N/A')}")
                    
                    logger.info(f"🎯 TP2 도달: ${tp2_price:.6f} | 청산 {partial_qty:.4f} (40%)")
                    return True, partial_qty, 'TP2', None  # TP는 current_price 사용
        
        # BE 이동 체크 (TP1 이후)
        if position.get('tp1_hit', False) and not position.get('be_moved', False):
            be_price = tp_levels.get('be')
            if be_price:
                one_r = abs(entry - stop)
                new_sl = self.tp_manager.check_be_move(entry, current_price, stop, side, one_r)
                if new_sl:
                    position['sl'] = new_sl
                    position['be_moved'] = True
        
        # ⭐ PHASE7-2 Phase 1: 트레일링 업데이트 (TP1 또는 TP2 이후, config에 따라)
        # - trailing_active가 True면 업데이트 (TP1에서 활성화 가능)
        # - 하위 호환: trailing_active 없으면 tp2_hit 조건 사용
        is_trailing_active = position.get('trailing_active', False) or position.get('tp2_hit', False)
        if is_trailing_active and atr:
            highest = position.get('highest', entry)
            lowest = position.get('lowest', entry)
            
            if side == 'LONG':
                highest = max(highest, current_price)
                position['highest'] = highest
            else:
                lowest = min(lowest, current_price)
                position['lowest'] = lowest
            
            trail_price = position.get('trail_price', stop)
            new_trail, updated, metadata = self.tp_manager.update_trailing_stop(
                current_price, trail_price, side, atr, highest, lowest, entry=position.get('entry_price')
            )
            
            if updated:
                position['trail_price'] = new_trail
                position['sl'] = new_trail
                logger.info(f"📈 Trailing 업데이트: ${new_trail:,.2f}")
        
        # ⭐ PHASE7-1: Close 가격 기반 SL 체크 (Fallback, OHLC 없을 때)
        # - OHLC가 있으면 위에서 이미 체크했으므로 여기서는 Fallback만
        if not candle:
            current_sl = position['sl']
            if (side == 'LONG' and current_price <= current_sl) or \
               (side == 'SHORT' and current_price >= current_sl):
                reason = 'TRAILING_SL' if position.get('tp2_hit', False) else 'SL'
                logger.info(f"❌ {reason} 도달 (Close): ${current_price:,.2f} (SL: ${current_sl:,.2f})")
                return True, None, reason, None  # 전체 청산 (Close 가격 사용)
        
        return False, 0, '', None  # 액션 없음
    
    def check_extreme_loss_realtime(self, position: dict, current_price: float) -> tuple[bool, str]:
        """
        실시간 Extreme Loss 체크 (WebSocket 가격 업데이트마다)
        
        ⭐ PHASE7-2 Phase 0: 1분 내 급락 감지용
        - 기존 check_tpsl_with_partial()은 캔들 종료 시에만 호출
        - 이 함수는 WebSocket 가격 업데이트마다 호출되어 즉시 감지
        
        Args:
            position: 포지션 정보
            current_price: 현재 가격
        
        Returns:
            (should_close, reason): 청산 여부 및 사유
        """
        entry = position.get('entry', 0)
        side = position.get('side', 'LONG')
        
        if entry <= 0:
            return False, ''
        
        # PnL 계산
        if side == 'LONG':
            current_pnl_pct = ((current_price - entry) / entry) * 100
        else:  # SHORT
            current_pnl_pct = ((entry - current_price) / entry) * 100
        
        # -20% 체크
        if current_pnl_pct <= -20.0:
            logger.warning(
                f"🚨 [EXTREME_LOSS_REALTIME] 극단 손실 감지: {current_pnl_pct:.2f}% <= -20% | "
                f"Entry: ${entry:.4f} → Current: ${current_price:.4f}"
            )
            return True, 'EXTREME_LOSS'
        
        return False, ''
