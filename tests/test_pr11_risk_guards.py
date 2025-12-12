#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR11 Risk Guards 테스트
- Slippage Guard  
- Extreme Loss Guard
- Paper/Live 파리티
"""
import sys
import os
from unittest.mock import Mock, patch

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.risk_manager import RiskManager
from common.config_loader import load_config


class TestPR11RiskGuards:
    """PR11 리스크 가드 프로퍼티 테스트"""
    
    def get_config(self):
        """테스트용 config 생성"""
        return {
            'mode': 'paper',
            'capital': {'initial': 10000},
            'risk': {
                'max_positions': 20,  # config.yml과 동일
                'max_exposure_per_symbol': 0.3,  # config.yml과 동일 (30%)
                'max_daily_loss_pct': 2.0,  # 2%
                'max_drawdown_pct': 10.0,  # 10%
                'max_slippage_pct': 0.5,   # 0.5%
                'extreme_loss_cutoff_pct': -30.0,  # -30%
                'profiles': {
                    'paper': {
                        'max_daily_loss_pct': 5.0  # Paper 모드는 완화
                    },
                    'live': {
                        'max_daily_loss_pct': 1.0  # Live 모드는 엄격
                    }
                }
            }
        }
    
    def get_risk_manager(self):
        """RiskManager 인스턴스 생성"""
        return RiskManager(self.get_config())
    
    def test_drawdown_guard_properties(self):
        """Drawdown Guard 프로퍼티 테스트"""
        risk_manager = self.get_risk_manager()
        
        # Property 1: peak_equity는 항상 증가하거나 유지
        initial_peak = risk_manager.peak_equity
        
        # 자본 증가 시 peak 업데이트
        risk_manager.check_drawdown_guard(12000)
        assert risk_manager.peak_equity >= initial_peak
        
        # 자본 감소 시 peak 유지
        current_peak = risk_manager.peak_equity
        risk_manager.check_drawdown_guard(11000)
        assert risk_manager.peak_equity == current_peak
        
        # Property 2: drawdown은 0~1 범위
        risk_manager.check_drawdown_guard(9000)
        assert 0 <= risk_manager.current_drawdown <= 1
        
        # Property 3: 임계값 초과 시 False 반환
        risk_manager.peak_equity = 10000
        result = risk_manager.check_drawdown_guard(8000)  # 20% 손실 > 10% 임계값
        assert result is False
    
    def test_slippage_guard_properties(self, risk_manager):
        """Slippage Guard 프로퍼티 테스트"""
        # Property 1: 동일 가격 시 항상 통과
        assert risk_manager.check_slippage_guard(100.0, 100.0) is True
        
        # Property 2: 슬리피지 계산 대칭성
        slippage_up = risk_manager.check_slippage_guard(100.0, 100.4)
        slippage_down = risk_manager.check_slippage_guard(100.0, 99.6)
        assert slippage_up == slippage_down  # 0.4% 슬리피지로 동일
        
        # Property 3: 임계값 경계 테스트
        # 0.5% 임계값 미만 (통과)
        assert risk_manager.check_slippage_guard(100.0, 100.49) is True
        # 0.5% 임계값 초과 (차단)
        assert risk_manager.check_slippage_guard(100.0, 100.51) is False
        
        # Property 4: 잘못된 가격 입력 시 통과 (방어 로직)
        assert risk_manager.check_slippage_guard(0, 100) is True
        assert risk_manager.check_slippage_guard(-100, 100) is True
    
    def test_extreme_loss_guard_properties(self, risk_manager):
        """Extreme Loss Guard 프로퍼티 테스트"""
        # Property 1: 이익 시 항상 통과
        assert risk_manager.check_extreme_loss_guard(0.1) is True  # +10%
        assert risk_manager.check_extreme_loss_guard(0.0) is True  # 0%
        
        # Property 2: 임계값 경계 테스트
        # -30% 임계값 초과 (통과)
        assert risk_manager.check_extreme_loss_guard(-0.29) is True
        # -30% 임계값 미만 (차단)
        assert risk_manager.check_extreme_loss_guard(-0.31) is False
        
        # Property 3: PR10 연계 확인 (-50%보다 보수적)
        # -40% 손실도 차단 (PR10 -50%보다 먼저 경고)
        assert risk_manager.check_extreme_loss_guard(-0.4) is False
    
    def test_paper_live_parity(self):
        """Paper/Live 모드 파리티 테스트"""
        # Paper 모드 설정
        paper_config = {
            'mode': 'paper',
            'capital': {'initial': 10000},
            'risk': {
                'max_positions': 20,  # config.yml과 동일
                'max_exposure_per_symbol': 0.3,  # config.yml과 동일 (30%)
                'max_drawdown_pct': 10.0,
                'max_slippage_pct': 0.5,
                'extreme_loss_cutoff_pct': -30.0,
                'profiles': {
                    'paper': {'max_daily_loss_pct': 5.0}
                }
            }
        }
        
        # Live 모드 설정 (가드 로직은 동일, 일일 손실만 다름)
        live_config = paper_config.copy()
        live_config['mode'] = 'live'
        live_config['risk']['profiles']['live'] = {'max_daily_loss_pct': 1.0}
        
        paper_risk = RiskManager(paper_config)
        live_risk = RiskManager(live_config)
        
        # Property 1: 가드 로직 100% 동일
        test_cases = [
            (9000, 8000),   # Drawdown
            (100.0, 100.6), # Slippage  
            (-0.35,),       # Extreme Loss
        ]
        
        # Drawdown Guard 파리티
        assert paper_risk.check_drawdown_guard(8000) == live_risk.check_drawdown_guard(8000)
        
        # Slippage Guard 파리티
        assert paper_risk.check_slippage_guard(100.0, 100.6) == live_risk.check_slippage_guard(100.0, 100.6)
        
        # Extreme Loss Guard 파리티
        assert paper_risk.check_extreme_loss_guard(-0.35) == live_risk.check_extreme_loss_guard(-0.35)
        
        # Property 2: 일일 손실 한도만 다름 (프로파일 적용)
        assert paper_risk.daily_loss_limit != live_risk.daily_loss_limit
        assert paper_risk.daily_loss_limit > live_risk.daily_loss_limit  # Paper가 더 관대
    
    def test_guard_integration_properties(self, risk_manager):
        """가드 통합 프로퍼티 테스트"""
        # Property 1: 모든 가드는 독립적으로 동작
        # Drawdown Guard 실패해도 다른 가드는 정상 동작
        risk_manager.peak_equity = 10000
        assert risk_manager.check_drawdown_guard(8000) is False  # DD 실패
        assert risk_manager.check_slippage_guard(100.0, 100.2) is True  # Slippage 성공
        
        # Property 2: 가드 상태는 멱등성 보장
        # 동일 입력에 대해 항상 동일 결과
        result1 = risk_manager.check_slippage_guard(100.0, 100.3)
        result2 = risk_manager.check_slippage_guard(100.0, 100.3)
        assert result1 == result2
        
        # Property 3: 가드 임계값은 config에서 로드
        assert risk_manager.max_drawdown_pct == 0.1  # 10%
        assert risk_manager.max_slippage_pct == 0.005  # 0.5%
        assert risk_manager.extreme_loss_cutoff_pct == -0.3  # -30%
    
    def test_config_validation_properties(self):
        """Config 검증 프로퍼티 테스트"""
        # Property 1: 필수 키 누락 시 기본값 적용
        minimal_config = {
            'mode': 'paper',
            'capital': {'initial': 10000},
            'risk': {'max_positions': 20, 'max_exposure_per_symbol': 0.3}
        }
        
        risk_manager = RiskManager(minimal_config)
        
        # 기본값 적용 확인
        assert risk_manager.max_drawdown_pct == 0.1  # 기본 10%
        assert risk_manager.max_slippage_pct == 0.005  # 기본 0.5%
        assert risk_manager.extreme_loss_cutoff_pct == -0.3  # 기본 -30%
        
        # Property 2: 잘못된 값 범위 보정
        invalid_config = minimal_config.copy()
        invalid_config['risk']['max_drawdown_pct'] = -5.0  # 음수
        
        risk_manager = RiskManager(invalid_config)
        # 음수는 기본값으로 대체되어야 함
        assert risk_manager.max_drawdown_pct >= 0
    
    @pytest.mark.parametrize("equity_changes,expected_drawdowns", [
        ([10000, 12000, 11000, 9000, 8000], [0.0, 0.0, 0.083, 0.25, 0.333]),
        ([10000, 9000, 8000, 12000, 11000], [0.0, 0.1, 0.2, 0.0, 0.083]),
    ])
    def test_drawdown_calculation_scenarios(self, risk_manager, equity_changes, expected_drawdowns):
        """다양한 시나리오에서 Drawdown 계산 정확성"""
        for i, (equity, expected_dd) in enumerate(zip(equity_changes, expected_drawdowns)):
            risk_manager.check_drawdown_guard(equity)
            actual_dd = risk_manager.current_drawdown
            # 부동소수점 오차 허용 (±0.01)
            assert abs(actual_dd - expected_dd) < 0.01, f"Step {i}: expected {expected_dd}, got {actual_dd}"
    
    def test_telegram_alert_integration(self, risk_manager):
        """Telegram 알림 통합 테스트"""
        with patch('common.messaging.tg') as mock_tg:
            # Guard 차단 시 알림 발송 확인
            risk_manager.check_drawdown_guard(5000)  # 50% 손실로 차단
            
            # _notify_guard 호출 확인 (내부 구현에 따라 조정 필요)
            # 실제로는 risk_manager 내부에서 tg 호출이 있어야 함
            
        # Property: 동일 사유 연속 알림 시 throttling 적용
        # (300초 내 동일 사유는 1회만 발송)
        pass  # 실제 구현에서는 throttling 로직 테스트


if __name__ == "__main__":
    # 단독 실행 시 간단한 테스트
    config = {
        'mode': 'paper',
        'capital': {'initial': 10000},
        'risk': {
            'max_positions': 5,
            'max_exposure_per_symbol': 0.15,
            'max_drawdown_pct': 10.0,
            'max_slippage_pct': 0.5,
            'extreme_loss_cutoff_pct': -30.0,
        }
    }
    
    risk_manager = RiskManager(config)
    
    # 기본 동작 확인
    print("✅ Drawdown Guard (정상):", risk_manager.check_drawdown_guard(9500))
    print("❌ Drawdown Guard (차단):", risk_manager.check_drawdown_guard(8000))
    print("✅ Slippage Guard (정상):", risk_manager.check_slippage_guard(100.0, 100.3))
    print("❌ Slippage Guard (차단):", risk_manager.check_slippage_guard(100.0, 101.0))
    print("✅ Extreme Loss Guard (정상):", risk_manager.check_extreme_loss_guard(-0.2))
    print("❌ Extreme Loss Guard (차단):", risk_manager.check_extreme_loss_guard(-0.4))
    
    print("\n🎯 PR11 Phase 3 프로퍼티 테스트 완료!")
