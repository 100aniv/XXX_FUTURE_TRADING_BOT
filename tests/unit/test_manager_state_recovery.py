#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE7-2 항목 8: Manager 상태 복원 단위 테스트
==============================================
PortfolioManager 및 RiskManager의 상태 저장/복원 기능 검증
"""
import pytest
import psycopg2
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
import time

from execution.portfolio_manager import PortfolioManager
from execution.risk_manager import RiskManager


@pytest.fixture
def mock_db_conn():
    """Mock DB connection"""
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return conn, cursor


@pytest.fixture
def portfolio_config():
    """PortfolioManager 테스트 설정"""
    return {
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 20,
            'max_exposure_per_symbol': 0.3
        },
        'portfolio': {
            'max_total_exposure': 0.8,
            'max_strategy_positions': 5
        }
    }


@pytest.fixture
def risk_config():
    """RiskManager 테스트 설정"""
    return {
        'mode': 'paper',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 20,
            'max_daily_loss_pct': 2.0,
            'max_drawdown_pct': 10.0,
            'max_consecutive_losses': 4,
            'cooldown_after_consecutive': 30
        }
    }


class TestPortfolioManagerState:
    """PortfolioManager 상태 저장/복원 테스트"""
    
    def test_save_state_success(self, mock_db_conn, portfolio_config):
        """상태 저장 성공"""
        conn, cursor = mock_db_conn
        pm = PortfolioManager(portfolio_config)
        
        # equity 변경
        pm.equity = 52000
        pm.daily_pnl = 2000
        pm.realized_pnl = 5000
        pm.unrealized_pnl = 500
        
        # 저장
        pm.save_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert "INSERT INTO trading.portfolio_state" in call_args[0]
        assert call_args[1] == ("paper", "test-run-123", 52000, 2000, 5000, 500)
        conn.commit.assert_called_once()
    
    def test_restore_state_success(self, mock_db_conn, portfolio_config):
        """상태 복원 성공"""
        conn, cursor = mock_db_conn
        pm = PortfolioManager(portfolio_config)
        
        # Mock DB 응답
        cursor.fetchone.return_value = (
            52000,  # current_equity
            2000,   # daily_pnl
            5000,   # realized_pnl
            500,    # unrealized_pnl
            datetime.now()  # updated_at
        )
        
        # 복원
        result = pm.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        assert result is True
        assert pm.equity == 52000
        assert pm.daily_pnl == 2000
        assert pm.realized_pnl == 5000
        assert pm.unrealized_pnl == 500
    
    def test_restore_state_no_data(self, mock_db_conn, portfolio_config):
        """복원할 데이터 없음"""
        conn, cursor = mock_db_conn
        pm = PortfolioManager(portfolio_config)
        
        # Mock DB 응답 (데이터 없음)
        cursor.fetchone.return_value = None
        
        # 복원
        result = pm.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        assert result is False
        assert pm.equity == 50000  # 초기값 유지
    
    def test_save_state_db_error(self, mock_db_conn, portfolio_config):
        """DB 오류 시 rollback"""
        conn, cursor = mock_db_conn
        pm = PortfolioManager(portfolio_config)
        
        # Mock DB 오류
        cursor.execute.side_effect = Exception("DB Error")
        
        # 저장 (예외 발생하지 않아야 함)
        pm.save_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        conn.rollback.assert_called_once()


class TestRiskManagerState:
    """RiskManager 상태 저장/복원 테스트"""
    
    def test_save_state_success(self, mock_db_conn, risk_config):
        """상태 저장 성공"""
        conn, cursor = mock_db_conn
        rm = RiskManager(risk_config)
        
        # 상태 변경
        rm.peak_equity = 55000
        rm.current_drawdown = 0.05
        rm.consecutive_losses = 2
        rm.in_cooldown = False
        
        # 저장
        rm.save_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert "INSERT INTO trading.risk_state" in call_args[0]
        assert call_args[1][0] == "paper"
        assert call_args[1][1] == "test-run-123"
        assert call_args[1][2] == 55000  # peak_equity
        assert call_args[1][3] == 0.05   # current_drawdown
        assert call_args[1][4] == 2      # consecutive_losses
        assert call_args[1][5] is False  # in_cooldown
        conn.commit.assert_called_once()
    
    def test_save_state_with_cooldown(self, mock_db_conn, risk_config):
        """쿨다운 상태 저장"""
        conn, cursor = mock_db_conn
        rm = RiskManager(risk_config)
        
        # 쿨다운 상태
        rm.in_cooldown = True
        rm.cooldown_start_time = time.time()
        rm.cooldown_minutes = 30
        
        # 저장
        rm.save_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        call_args = cursor.execute.call_args[0]
        assert call_args[1][5] is True  # in_cooldown
        assert call_args[1][6] is not None  # cooldown_until
    
    def test_restore_state_success(self, mock_db_conn, risk_config):
        """상태 복원 성공"""
        conn, cursor = mock_db_conn
        rm = RiskManager(risk_config)
        
        # Mock DB 응답
        cursor.fetchone.return_value = (
            55000,  # peak_equity
            0.05,   # current_drawdown
            2,      # consecutive_losses
            False,  # in_cooldown
            None,   # cooldown_until
            datetime.now()  # updated_at
        )
        
        # 복원
        result = rm.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        assert result is True
        assert rm.peak_equity == 55000
        assert rm.current_drawdown == 0.05
        assert rm.consecutive_losses == 2
        assert rm.in_cooldown is False
    
    def test_restore_state_with_active_cooldown(self, mock_db_conn, risk_config):
        """활성 쿨다운 복원"""
        conn, cursor = mock_db_conn
        rm = RiskManager(risk_config)
        
        # Mock DB 응답 (쿨다운 아직 진행 중)
        cooldown_until = datetime.now() + timedelta(minutes=15)
        cursor.fetchone.return_value = (
            55000,  # peak_equity
            0.05,   # current_drawdown
            4,      # consecutive_losses
            True,   # in_cooldown
            cooldown_until,  # cooldown_until (15분 남음)
            datetime.now()  # updated_at
        )
        
        # 복원
        result = rm.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        assert result is True
        assert rm.in_cooldown is True
        assert rm.cooldown_start_time > 0
    
    def test_restore_state_with_expired_cooldown(self, mock_db_conn, risk_config):
        """만료된 쿨다운 복원"""
        conn, cursor = mock_db_conn
        rm = RiskManager(risk_config)
        
        # Mock DB 응답 (쿨다운 이미 종료)
        cooldown_until = datetime.now() - timedelta(minutes=5)
        cursor.fetchone.return_value = (
            55000,  # peak_equity
            0.05,   # current_drawdown
            4,      # consecutive_losses
            True,   # in_cooldown (DB 값)
            cooldown_until,  # cooldown_until (이미 지남)
            datetime.now()  # updated_at
        )
        
        # 복원
        result = rm.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        assert result is True
        assert rm.in_cooldown is False  # 자동으로 False로 변경
        assert rm.cooldown_start_time == 0
    
    def test_restore_state_no_data(self, mock_db_conn, risk_config):
        """복원할 데이터 없음"""
        conn, cursor = mock_db_conn
        rm = RiskManager(risk_config)
        
        # Mock DB 응답 (데이터 없음)
        cursor.fetchone.return_value = None
        
        # 복원
        result = rm.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 검증
        assert result is False
        assert rm.peak_equity == 50000  # 초기값 유지


class TestManagerStateIntegration:
    """Manager 상태 통합 테스트"""
    
    def test_full_save_restore_cycle(self, mock_db_conn, portfolio_config, risk_config):
        """전체 저장/복원 사이클"""
        conn, cursor = mock_db_conn
        
        # 1. 초기 Manager 생성
        pm1 = PortfolioManager(portfolio_config)
        rm1 = RiskManager(risk_config)
        
        # 2. 상태 변경
        pm1.equity = 52000
        pm1.daily_pnl = 2000
        rm1.peak_equity = 52000
        rm1.consecutive_losses = 1
        
        # 3. 저장
        pm1.save_state(conn, mode="paper", run_id="test-run-123")
        rm1.save_state(conn, mode="paper", run_id="test-run-123")
        
        # 4. 새 Manager 생성 (재시작 시뮬레이션)
        pm2 = PortfolioManager(portfolio_config)
        rm2 = RiskManager(risk_config)
        
        # 5. Mock DB 응답 설정
        cursor.fetchone.side_effect = [
            # Portfolio 복원
            (52000, 2000, 5000, 500, datetime.now()),
            # Risk 복원
            (52000, 0.0, 1, False, None, datetime.now())
        ]
        
        # 6. 복원
        pm2.restore_state(conn, mode="paper", run_id="test-run-123")
        rm2.restore_state(conn, mode="paper", run_id="test-run-123")
        
        # 7. 검증
        assert pm2.equity == 52000
        assert pm2.daily_pnl == 2000
        assert rm2.peak_equity == 52000
        assert rm2.consecutive_losses == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
