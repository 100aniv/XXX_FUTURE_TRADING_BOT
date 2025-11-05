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
                                atr: float = None) -> Tuple[bool, Optional[float], str]:
        """
        TP 분할 체크 (TUNING_VIBLE P1)
        
        Args:
            position: 포지션
            current_price: 현재 가격
            atr: ATR 값 (트레일링용)
        
        Returns:
            (should_action, partial_qty, reason)
            - should_action: 액션 필요 여부
            - partial_qty: 부분 청산 수량 (None = 전체 청산)
            - reason: 이유 (TP1/TP2/SL/TRAILING_SL)
        """
        side = position['side']
        entry = position['entry']
        stop = position['sl']
        total_qty = position['qty']
        
        # TP 레벨 확인
        tp_levels = position.get('tp_levels', {})
        if not tp_levels:
            # TP 레벨 없으면 레거시 방식
            should_close, reason = self.check_tpsl(position, current_price)
            return should_close, None if should_close else 0, reason
        
        # TP1 체크
        if not position.get('tp1_hit', False):
            tp1_price = tp_levels.get('tp1')
            if tp1_price:
                if (side == 'LONG' and current_price >= tp1_price) or \
                   (side == 'SHORT' and current_price <= tp1_price):
                    partial_qty = self.tp_manager.calculate_partial_size(total_qty, 1)
                    position['tp1_hit'] = True
                    position['remaining_pct'] = 70.0
                    logger.info(f"🎯 TP1 도달: {partial_qty:.4f} 청산 (30%)")
                    return True, partial_qty, 'TP1'
        
        # TP2 체크
        if not position.get('tp2_hit', False) and position.get('tp1_hit', False):
            tp2_price = tp_levels.get('tp2')
            if tp2_price:
                if (side == 'LONG' and current_price >= tp2_price) or \
                   (side == 'SHORT' and current_price <= tp2_price):
                    partial_qty = self.tp_manager.calculate_partial_size(total_qty, 2)
                    position['tp2_hit'] = True
                    position['remaining_pct'] = 30.0
                    logger.info(f"🎯 TP2 도달: {partial_qty:.4f} 청산 (40%)")
                    return True, partial_qty, 'TP2'
        
        # BE 이동 체크 (TP1 이후)
        if position.get('tp1_hit', False) and not position.get('be_moved', False):
            be_price = tp_levels.get('be')
            if be_price:
                one_r = abs(entry - stop)
                new_sl = self.tp_manager.check_be_move(entry, current_price, stop, side, one_r)
                if new_sl:
                    position['sl'] = new_sl
                    position['be_moved'] = True
        
        # 트레일링 업데이트 (TP2 이후)
        if position.get('tp2_hit', False) and atr:
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
        
        # SL 체크
        current_sl = position['sl']
        if (side == 'LONG' and current_price <= current_sl) or \
           (side == 'SHORT' and current_price >= current_sl):
            reason = 'TRAILING_SL' if position.get('tp2_hit', False) else 'SL'
            logger.info(f"❌ {reason} 도달: ${current_price:,.2f} (SL: ${current_sl:,.2f})")
            return True, None, reason  # 전체 청산
        
        return False, 0, ''
