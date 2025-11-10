#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TP Manager - Take Profit 분할 관리
===================================
TUNING_VIBLE P1: 손익비 구조 최적화

TP 분할:
- TP1: +1R, 30% 청산
- TP2: +2R, 40% 청산
- 잔량 30%: Trailing Stop

트레일링:
- ATR × k 기반
- BE (Break Even) 이동: 0.8R 도달 시
"""
from typing import Dict, Optional, Tuple
from common.logger import setup_logger
from common.calculations import round_tick  # ⭐ PR12: 동적 반올림

logger = setup_logger(__name__)


class TPManager:
    """TP 분할 & 트레일링 관리자"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: config.yml의 exits 섹션
        """
        self.config = config
        
        # TP 분할 설정
        exits = config.get('exits', {})
        self.tp_levels = exits.get('take_profits', [
            {'r_multiple': 1.0, 'size_pct': 30},
            {'r_multiple': 2.0, 'size_pct': 40}
        ])
        
        # 트레일링 설정
        trailing = exits.get('trailing', {})
        self.trail_type = trailing.get('type', 'atr')
        self.trail_k = trailing.get('k', 3.0)
        self.be_at_r = trailing.get('move_to_break_even_at_r', 0.8)
        
        # 시간 청산
        self.time_exit_min = exits.get('time_exit_min', 360)
        
        logger.info(f"✅ TPManager 초기화: TP 레벨={self.tp_levels}, 트레일링={self.trail_type}×{self.trail_k}, BE 이동={self.be_at_r}R")
    
    def calculate_tp_levels(self, entry: float, stop: float, side: str, 
                           atr: float = None, volatility_regime: str = None,
                           symbol: str = "BTCUSDT") -> Dict[str, float]:
        """
        TP 레벨 계산 (⭐ PR12: 동적 반올림 적용)
        
        Args:
            entry: 진입가
            stop: 손절가
            side: LONG/SHORT
            atr: ATR 값 (트레일링용)
            volatility_regime: 'low_vol', 'neutral', 'high_vol' (선택)
            symbol: 거래 심볼 (⭐ PR12: 반올림용)
        
        Returns:
            {'tp1': price, 'tp2': price, 'trail': price, 'be': price}
        """
        # 1R 계산
        if side == 'LONG':
            one_r = entry - stop
        else:
            one_r = stop - entry
        
        # ⭐ PHASE7-1: 1R 검증 (음수 방지)
        if one_r <= 0:
            logger.error(f"❌ 잘못된 SL 설정: {side} Entry={entry:.4f}, SL={stop:.4f}, 1R={one_r:.4f}")
            # SL을 Entry 기준 기본 거리로 강제 설정
            if side == 'LONG':
                one_r = entry * 0.02  # Entry 대비 2%
                logger.warning(f"⚠️ 1R 강제 조정: {one_r:.4f} (Entry의 2%)")
            else:
                one_r = entry * 0.02
                logger.warning(f"⚠️ 1R 강제 조정: {one_r:.4f} (Entry의 2%)")
        
        # ⭐ 변동성 레짐 조정 (고변동성 시 SL 넓게 → 1R 증가)
        vol_mult = 1.0
        if volatility_regime == 'high_vol':
            vol_mult = 1.2  # SL 20% 넓게
        elif volatility_regime == 'low_vol':
            vol_mult = 0.9  # SL 10% 좁게
        
        adjusted_one_r = one_r * vol_mult
        
        result = {}
        
        # TP 레벨 계산 (조정된 1R 사용) + ⭐ PR12: 동적 반올림
        for level in self.tp_levels:
            r_mult = level['r_multiple']
            key = f"tp{int(r_mult)}"
            
            if side == 'LONG':
                price = entry + (adjusted_one_r * r_mult)
            else:
                price = entry - (adjusted_one_r * r_mult)
            
            # ⭐ PR12: Binance tick_size에 맞게 반올림
            result[key] = round_tick(symbol, price)
            
            # ⭐ PHASE7-1: TP 방향 검증
            if side == 'LONG' and price <= entry:
                logger.error(f"❌ TP{int(r_mult)} 방향 오류: LONG인데 TP({price:.4f}) <= Entry({entry:.4f})")
                result[key] = entry * 1.02  # Entry + 2%로 강제 조정
                logger.warning(f"⚠️ TP{int(r_mult)} 강제 조정: {result[key]:.4f}")
            elif side == 'SHORT' and price >= entry:
                logger.error(f"❌ TP{int(r_mult)} 방향 오류: SHORT인데 TP({price:.4f}) >= Entry({entry:.4f})")
                result[key] = entry * 0.98  # Entry - 2%로 강제 조정
                logger.warning(f"⚠️ TP{int(r_mult)} 강제 조정: {result[key]:.4f}")
        
        # BE (Break Even) 가격 + ⭐ PR12: 동적 반올림
        if side == 'LONG':
            be_price = entry + (adjusted_one_r * self.be_at_r)
        else:
            be_price = entry - (adjusted_one_r * self.be_at_r)
        
        result['be'] = round_tick(symbol, be_price)
        
        # 초기 트레일링 가격 (ATR 기반) + ⭐ PR12: 동적 반올림
        if atr and self.trail_type == 'atr':
            if side == 'LONG':
                trail_price = entry - (atr * self.trail_k)
            else:
                trail_price = entry + (atr * self.trail_k)
            
            # ⭐ PR12: Binance tick_size에 맞게 반올림
            result['trail'] = round_tick(symbol, trail_price)
        
        # 메타데이터 추가
        result['_meta'] = {
            'volatility_regime': volatility_regime,
            'vol_mult': vol_mult,
            'base_one_r': one_r,
            'adjusted_one_r': adjusted_one_r
        }
        
        return result
    
    def calculate_partial_size(self, total_qty: float, tp_level: int) -> float:
        """
        부분 청산 수량 계산
        
        Args:
            total_qty: 총 수량
            tp_level: TP 레벨 (1, 2)
        
        Returns:
            청산할 수량
        """
        for level in self.tp_levels:
            if level['r_multiple'] == tp_level:
                return total_qty * (level['size_pct'] / 100)
        return 0
    
    def update_trailing_stop(self, current_price: float, current_trail: float,
                            side: str, atr: float, highest: float = None,
                            lowest: float = None, entry: float = None) -> Tuple[float, bool, dict]:
        """
        트레일링 스톱 업데이트 (⭐ PR8 Phase2: BE 로직 추가)
        
        Args:
            current_price: 현재가
            current_trail: 현재 트레일링 가격
            side: LONG/SHORT
            atr: ATR 값
            highest: 최고가 (LONG용)
            lowest: 최저가 (SHORT용)
            entry: 진입가 (BE 계산용, 선택)
        
        Returns:
            (새 트레일링 가격, 업데이트 여부, 메타데이터)
        """
        if self.trail_type != 'atr':
            return current_trail, False, {"action": "none"}
        
        new_trail = current_trail
        updated = False
        action = "none"
        
        # ⭐ 1. Breakeven 이동 (진입가 있을 때)
        if entry:
            if side == 'LONG':
                one_r = abs(current_trail - entry)  # 초기 리스크
                be_trigger = entry + (one_r * self.be_at_r)
                
                # BE 트리거 도달 & SL이 아직 BE 아래
                if current_price >= be_trigger and current_trail < entry:
                    new_trail = entry
                    updated = True
                    action = "breakeven"
            else:  # SHORT
                one_r = abs(entry - current_trail)
                be_trigger = entry - (one_r * self.be_at_r)
                
                if current_price <= be_trigger and current_trail > entry:
                    new_trail = entry
                    updated = True
                    action = "breakeven"
        
        # ⭐ 2. ATR 기반 Trailing (기존 로직)
        if not updated:  # BE 이동 안 했으면
            if side == 'LONG':
                # LONG: 최고가 갱신 시 트레일 상승
                if highest:
                    candidate = highest - (atr * self.trail_k)
                    if candidate > current_trail:
                        new_trail = candidate
                        updated = True
                        action = "trailing"
            else:
                # SHORT: 최저가 갱신 시 트레일 하락
                if lowest:
                    candidate = lowest + (atr * self.trail_k)
                    if candidate < current_trail:
                        new_trail = candidate
                        updated = True
                        action = "trailing"
        
        # 메타데이터
        metadata = {
            "action": action,
            "old_trail": current_trail,
            "new_trail": new_trail,
            "updated": updated
        }
        
        return new_trail, updated, metadata
    
    def check_be_move(self, entry: float, current_price: float, 
                     current_stop: float, side: str, one_r: float) -> Optional[float]:
        """
        BE (손익분기) 이동 체크
        
        Args:
            entry: 진입가
            current_price: 현재가
            current_stop: 현재 손절가
            side: LONG/SHORT
            one_r: 1R 가격폭
        
        Returns:
            새 손절가 (BE로 이동) 또는 None
        """
        if side == 'LONG':
            unrealized_r = (current_price - entry) / one_r
            if unrealized_r >= self.be_at_r and current_stop < entry:
                logger.info(f"🔄 BE 이동: {current_stop:.2f} → {entry:.2f} (LONG)")
                return entry
        else:
            unrealized_r = (entry - current_price) / one_r
            if unrealized_r >= self.be_at_r and current_stop > entry:
                logger.info(f"🔄 BE 이동: {current_stop:.2f} → {entry:.2f} (SHORT)")
                return entry
        
        return None
    
    def check_time_exit(self, entry_time: int, current_time: int) -> bool:
        """
        시간 기반 청산 체크
        
        Args:
            entry_time: 진입 시간 (timestamp)
            current_time: 현재 시간 (timestamp)
        
        Returns:
            청산 여부
        """
        elapsed_min = (current_time - entry_time) / 60
        return elapsed_min >= self.time_exit_min
    
    def get_status(self, position: Dict) -> Dict:
        """
        포지션의 TP 상태 조회
        
        Args:
            position: 포지션 딕셔너리
        
        Returns:
            {'tp1_hit': bool, 'tp2_hit': bool, 'be_moved': bool, 
             'remaining_pct': float}
        """
        return {
            'tp1_hit': position.get('tp1_hit', False),
            'tp2_hit': position.get('tp2_hit', False),
            'be_moved': position.get('be_moved', False),
            'remaining_pct': position.get('remaining_pct', 100.0)
        }


if __name__ == '__main__':
    # 테스트
    test_config = {
        'exits': {
            'take_profits': [
                {'r_multiple': 1.0, 'size_pct': 30},
                {'r_multiple': 2.0, 'size_pct': 40}
            ],
            'trailing': {
                'type': 'atr',
                'k': 2.5,
                'move_to_break_even_at_r': 0.8
            },
            'time_exit_min': 360
        }
    }
    
    manager = TPManager(test_config)
    
    # LONG 예시
    entry = 50000
    stop = 49500
    atr = 200
    
    levels = manager.calculate_tp_levels(entry, stop, 'LONG', atr)
    print(f"\n🎯 TP 레벨 (LONG):")
    for key, price in levels.items():
        print(f"  {key}: ${price:,.2f}")
    
    # 부분 청산 수량
    total_qty = 0.1
    tp1_qty = manager.calculate_partial_size(total_qty, 1)
    tp2_qty = manager.calculate_partial_size(total_qty, 2)
    print(f"\n📊 부분 청산:")
    print(f"  총 수량: {total_qty}")
    print(f"  TP1 (30%): {tp1_qty}")
    print(f"  TP2 (40%): {tp2_qty}")
    print(f"  Trail (30%): {total_qty - tp1_qty - tp2_qty}")
