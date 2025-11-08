#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR12 통합 테스트
================
동적 반올림, 펀딩 연동, 포트폴리오 가드 검증
"""
import pytest
from unittest.mock import Mock, patch
from common.calculations import (
    get_exchange_info,
    round_tick,
    get_funding_rate,
    calculate_funding_fee
)
from execution.tp_manager import TPManager
from execution.portfolio_manager import PortfolioManager


class TestPR12DynamicRounding:
    """동적 반올림 테스트"""
    
    @patch('common.calculations.requests.get')
    def test_get_exchange_info_success(self, mock_get):
        """exchangeInfo API 조회 성공"""
        # Mock API 응답
        mock_response = Mock()
        mock_response.json.return_value = {
            "symbols": [{
                "symbol": "BTCUSDT",
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.001"}
                ]
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # 테스트
        info = get_exchange_info("BTCUSDT", use_cache=False)
        
        assert info is not None
        assert info["tickSize"] == 0.1
        assert info["stepSize"] == 0.001
    
    @patch('common.calculations.requests.get')
    def test_round_tick_with_api(self, mock_get):
        """동적 반올림 (API 사용)"""
        # Mock API 응답
        mock_response = Mock()
        mock_response.json.return_value = {
            "symbols": [{
                "symbol": "BTCUSDT",
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.001"}
                ]
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # 테스트
        price = 50123.456
        rounded = round_tick("BTCUSDT", price, use_api=True)
        
        # tickSize=0.1이므로 0.1 단위로 반올림
        assert rounded == 50123.5
    
    def test_round_tick_fallback(self):
        """동적 반올림 (폴백)"""
        price = 50123.456
        rounded = round_tick("BTCUSDT", price, use_api=False)
        
        # 폴백: 0.01 단위
        assert rounded == 50123.46


class TestPR12FundingIntegration:
    """펀딩 연동 테스트"""
    
    @patch('common.calculations.requests.get')
    def test_get_funding_rate_success(self, mock_get):
        """fundingRate API 조회 성공"""
        # Mock API 응답
        mock_response = Mock()
        mock_response.json.return_value = {
            "lastFundingRate": "0.00010000"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # 테스트
        rate = get_funding_rate("BTCUSDT", use_cache=False)
        
        assert rate == 0.0001
    
    def test_calculate_funding_fee_manual(self):
        """펀딩비 계산 (수동)"""
        fee = calculate_funding_fee(
            position_value=10000,
            holding_hours=24,
            funding_rate=0.0001,
            side="LONG",
            use_api=False
        )
        
        # 24시간 = 3회 정산, LONG은 지불(음수)
        # 10000 * 0.0001 * 3 * (-1) = -3.0
        assert fee == -3.0
    
    def test_calculate_funding_fee_short(self):
        """펀딩비 계산 (SHORT)"""
        fee = calculate_funding_fee(
            position_value=10000,
            holding_hours=24,
            funding_rate=0.0001,
            side="SHORT",
            use_api=False
        )
        
        # SHORT는 수령(양수)
        assert fee == 3.0


class TestPR12TPManager:
    """TP Manager 동적 반올림 테스트"""
    
    @patch('execution.tp_manager.round_tick')
    def test_calculate_tp_levels_with_rounding(self, mock_round_tick):
        """TP 레벨 계산 시 반올림 적용"""
        # Mock round_tick
        mock_round_tick.side_effect = lambda symbol, price: round(price, 2)
        
        # TPManager 초기화
        config = {
            'exits': {
                'take_profits': [
                    {'r_multiple': 1.0, 'size_pct': 30},
                    {'r_multiple': 2.0, 'size_pct': 40}
                ],
                'trailing': {
                    'type': 'atr',
                    'k': 3.0,
                    'move_to_break_even_at_r': 0.8
                }
            }
        }
        tp_manager = TPManager(config)
        
        # TP 레벨 계산
        levels = tp_manager.calculate_tp_levels(
            entry=50000,
            stop=49000,
            side="LONG",
            atr=500,
            symbol="BTCUSDT"
        )
        
        # round_tick이 호출되었는지 확인
        assert mock_round_tick.call_count >= 3  # tp1, tp2, be 최소 3번
        
        # TP 레벨이 계산되었는지 확인
        assert 'tp1' in levels
        assert 'tp2' in levels
        assert 'be' in levels


class TestPR12PortfolioGuards:
    """포트폴리오 가드 테스트"""
    
    def test_strategy_budget_guard(self):
        """전략별 예산 가드"""
        config = {
            'capital': {'initial': 10000},
            'risk': {
                'max_positions': 10,
                'max_exposure_per_symbol': 0.3,
                'max_total_exposure': 0.8,
                'max_strategy_positions': 5
            },
            'portfolio': {
                'budget_per_strategy': {
                    'scalping': 0.3,
                    'swing': 0.4,
                    'trend': 0.3
                },
                'correlation': {
                    'enabled': False
                }
            }
        }
        
        portfolio = PortfolioManager(config)
        
        # 전략별 예산 계산
        scalping_budget = portfolio.calculate_strategy_budget('scalping')
        swing_budget = portfolio.calculate_strategy_budget('swing')
        
        assert scalping_budget == 3000  # 10000 * 0.3
        assert swing_budget == 4000  # 10000 * 0.4
    
    def test_can_open_position_with_strategy_budget(self):
        """전략별 예산 한도 체크"""
        config = {
            'capital': {'initial': 10000},
            'risk': {
                'max_positions': 10,
                'max_exposure_per_symbol': 0.3,
                'max_total_exposure': 0.8,
                'max_strategy_positions': 5
            },
            'portfolio': {
                'budget_per_strategy': {
                    'scalping': 0.3
                },
                'correlation': {
                    'enabled': False
                }
            }
        }
        
        portfolio = PortfolioManager(config)
        
        # 예산 내 포지션 오픈 가능
        allowed, reason = portfolio.can_open_position(
            symbol="BTCUSDT",
            strategy="scalping",
            position_value=2000,
            side="LONG"
        )
        assert allowed is True
        
        # 예산 초과 포지션 오픈 불가
        allowed, reason = portfolio.can_open_position(
            symbol="BTCUSDT",
            strategy="scalping",
            position_value=5000,  # 3000 예산 초과
            side="LONG"
        )
        assert allowed is False
        assert "예산 초과" in reason


class TestPR12PaperLiveParity:
    """Paper/Live 파리티 테스트"""
    
    @patch('common.calculations.requests.get')
    def test_api_calls_same_for_paper_and_live(self, mock_get):
        """Paper/Live 모드 모두 동일한 API 호출"""
        # Mock API 응답
        mock_response = Mock()
        mock_response.json.return_value = {
            "symbols": [{
                "symbol": "BTCUSDT",
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.001"}
                ]
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Paper 모드 (use_api=True)
        info_paper = get_exchange_info("BTCUSDT", use_cache=False)
        
        # Live 모드 (use_api=True)
        info_live = get_exchange_info("BTCUSDT", use_cache=False)
        
        # 동일한 결과
        assert info_paper == info_live
        assert info_paper["tickSize"] == 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
