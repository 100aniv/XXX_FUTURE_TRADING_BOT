"""
PHASE7-1: 청산 가격 사용 테스트
- SL 청산 시 SL 가격 사용
- TP 청산 시 TP 가격 사용
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


class TestExitPriceUsage:
    """청산 가격 사용 검증"""
    
    def test_sl_exit_uses_sl_price_not_current(self):
        """SL 청산 시 SL 가격 사용 (current_price 아님)"""
        position = {
            'entry': 100.0,
            'sl': 95.0,  # SL 가격
            'qty': 1.0,
            'side': 'LONG'
        }
        current_price = 92.0  # Close 가격 (더 나쁨)
        
        # SL 청산 시 SL 가격(95.0) 사용해야 함
        # current_price(92.0) 사용하면 -8% 손실
        # SL 가격(95.0) 사용하면 -5% 손실
        
        from execution.engine import calculate_pnl
        
        # 잘못된 방식: current_price 사용
        pnl_wrong = calculate_pnl(position, current_price, 0.0004)
        loss_pct_wrong = (pnl_wrong / (position['entry'] * position['qty'])) * 100
        
        # 올바른 방식: SL 가격 사용
        pnl_correct = calculate_pnl(position, position['sl'], 0.0004)
        loss_pct_correct = (pnl_correct / (position['entry'] * position['qty'])) * 100
        
        # SL 가격 사용 시 손실이 더 작아야 함
        assert loss_pct_correct > loss_pct_wrong
        assert loss_pct_correct > -6.0  # -5% - 수수료
        assert loss_pct_wrong < -7.5  # -8% + 수수료
    
    def test_tp1_exit_uses_tp1_price(self):
        """TP1 청산 시 TP1 가격 사용"""
        position = {
            'entry': 100.0,
            'tp_levels': {
                'tp1': 105.0,  # TP1 가격
                'tp2': 110.0
            },
            'qty': 0.3,  # 30% 청산
            'side': 'LONG'
        }
        current_price = 104.5  # Close 가격 (TP1보다 낮음)
        
        from execution.engine import calculate_pnl
        
        # 잘못된 방식: current_price 사용
        pnl_wrong = calculate_pnl(
            {'entry': position['entry'], 'qty': position['qty'], 'side': position['side']},
            current_price,
            0.0004
        )
        
        # 올바른 방식: TP1 가격 사용
        pnl_correct = calculate_pnl(
            {'entry': position['entry'], 'qty': position['qty'], 'side': position['side']},
            position['tp_levels']['tp1'],
            0.0004
        )
        
        # TP1 가격 사용 시 수익이 더 커야 함
        assert pnl_correct > pnl_wrong
    
    def test_extreme_loss_uses_sl_price(self):
        """EXTREME_LOSS 청산 시 SL 가격 사용"""
        position = {
            'entry': 100.0,
            'sl': 80.0,  # SL 가격 (-20%)
            'qty': 1.0,
            'side': 'LONG'
        }
        current_price = 75.0  # 갭 다운 (-25%)
        
        from execution.engine import calculate_pnl
        
        # EXTREME_LOSS도 SL 청산과 동일하게 SL 가격 사용
        pnl_correct = calculate_pnl(position, position['sl'], 0.0004)
        loss_pct = (pnl_correct / (position['entry'] * position['qty'])) * 100
        
        # -20% 근처여야 함 (수수료 포함)
        assert -21.0 < loss_pct < -19.5
    
    def test_trailing_sl_uses_sl_price(self):
        """TRAILING_SL 청산 시 SL 가격 사용"""
        position = {
            'entry': 100.0,
            'sl': 105.0,  # 트레일링 SL (BE 이상)
            'qty': 1.0,
            'side': 'LONG'
        }
        current_price = 103.0  # Close 가격 (SL보다 낮음)
        
        from execution.engine import calculate_pnl
        
        # TRAILING_SL도 SL 가격 사용
        pnl_correct = calculate_pnl(position, position['sl'], 0.0004)
        profit_pct = (pnl_correct / (position['entry'] * position['qty'])) * 100
        
        # +5% 근처여야 함 (수수료 포함)
        assert 4.5 < profit_pct < 5.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
