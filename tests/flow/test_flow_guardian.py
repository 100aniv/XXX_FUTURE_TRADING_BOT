#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FlowGuardian Gate Tests
=======================
엔드투엔드 게이트 검증 테스트

목적:
- READY 경로 검증 (정상 통과)
- FAIL 경로 검증 (고의 실패)
- logs/trial_0000.json 생성 확인
- DB==JSON score_total 검증 (선택)

제약 (.windsurfrules):
- tests/flow/test_flow_guardian.py 통과 필수
- coverage > 85%
"""
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 테스트용 DATABASE_URL 설정 (import 전에 필요)
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")

from core.flow_guardian import FlowGuardian, GateResult


class MockDataSource:
    """테스트용 데이터 소스"""
    
    def __init__(self, fail=False):
        self.fail = fail
    
    def fetch(self, candle_range):
        if self.fail:
            return pd.DataFrame()  # 빈 DataFrame
        
        # 간단한 테스트 데이터 (300 rows)
        data = {
            'timestamp': pd.date_range('2024-01-01', periods=300, freq='15min'),
            'open': [100 + i * 0.1 for i in range(300)],
            'high': [101 + i * 0.1 for i in range(300)],
            'low': [99 + i * 0.1 for i in range(300)],
            'close': [100.5 + i * 0.1 for i in range(300)],
            'volume': [1000000 + i * 1000 for i in range(300)],
        }
        return pd.DataFrame(data)


class MockStrategy:
    """테스트용 전략"""
    
    def __init__(self, fail=False):
        self.fail = fail
    
    def generate_signals(self, df):
        if self.fail:
            return None  # 실패
        
        return {
            'signal': 'BUY',
            'confidence': 0.85,
            'order_intent': {
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'quantity': 0.1,
                'price': 100.0,
                'sl': 98.0,
                'tp': 105.0,
            }
        }


class MockRisk:
    """테스트용 리스크 관리자"""
    
    def __init__(self, fail=False):
        self.fail = fail
    
    def assess(self, order_intent, account):
        if self.fail:
            return {'allowed': False, 'reason': '테스트 실패'}
        
        return {
            'allowed': True,
            'reason': 'ok',
            'adjusted_intent': order_intent,
        }


class MockBroker:
    """테스트용 브로커"""
    
    def __init__(self, fail=False):
        self.fail = fail
    
    def dry_run(self, order_intent):
        if self.fail:
            return None
        
        return {
            'filled': True,
            'fill_price': 100.0,
            'pnl': 50.0,
            'commission': 0.5,
        }
    
    def place(self, order_intent):
        return 'test_order_id_123'


class MockMetrics:
    """테스트용 메트릭 계산기"""
    
    def __init__(self, fail=False, low_pf=False):
        self.fail = fail
        self.low_pf = low_pf
    
    def compute(self, trade_log):
        if self.fail:
            return None
        
        if self.low_pf:
            return {
                'profit_factor': 0.8,  # 기준 미달
                'winrate': 0.4,  # 기준 미달
                'exp_score': 0.5,
                'score_total': 0.4,
                'total_trades': 10,
            }
        
        return {
            'profit_factor': 1.5,
            'winrate': 0.6,
            'exp_score': 0.9,
            'score_total': 0.85,
            'total_trades': 10,
        }


class TestFlowGuardian(unittest.TestCase):
    """FlowGuardian 게이트 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = {
            'flow_guardian': {
                'enabled': True,
                'selftest': {
                    'max_runtime_sec': 120,
                    'require_metrics': ['profit_factor', 'winrate', 'score_total', 'exp_score'],
                    'min_profit_factor': 1.0,
                    'min_winrate': 0.45,
                    'consistency_checks': {
                        'db_vs_json_score_equal': False,  # 테스트에서는 DB 검증 비활성화
                        'signals_no_nan': True,
                        'risk_never_oversize': True,
                    },
                    'artifacts': {
                        'require_files': ['logs/trial_0000.json'],
                    },
                },
            },
        }
        
        # 테스트 아티팩트 정리
        trial_file = Path('logs/trial_0000.json')
        if trial_file.exists():
            trial_file.unlink()
    
    def test_ready_path_success(self):
        """READY 경로: 정상 통과"""
        # Given: 정상 모듈들
        guardian = FlowGuardian(
            config=self.config,
            source=MockDataSource(),
            strategy=MockStrategy(),
            risk=MockRisk(),
            executor=MockBroker(),
            metrics=MockMetrics(),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: READY
        self.assertTrue(result.ready)
        self.assertEqual(len(result.errors), 0)
        self.assertIn('profit_factor', result.metrics)
        self.assertGreaterEqual(result.metrics['profit_factor'], 1.0)
        
        # 아티팩트 확인
        trial_file = Path('logs/trial_0000.json')
        self.assertTrue(trial_file.exists())
        
        with open(trial_file, 'r', encoding='utf-8') as f:
            trial_data = json.load(f)
        
        self.assertIn('metrics', trial_data)
        self.assertEqual(trial_data['status'], 'READY')
    
    def test_fail_path_data_source(self):
        """FAIL 경로: 데이터 소스 실패"""
        # Given: 데이터 소스 실패
        guardian = FlowGuardian(
            config=self.config,
            source=MockDataSource(fail=True),
            strategy=MockStrategy(),
            risk=MockRisk(),
            executor=MockBroker(),
            metrics=MockMetrics(),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: FAIL
        self.assertFalse(result.ready)
        self.assertGreater(len(result.errors), 0)
        self.assertIn('데이터', result.errors[0])
    
    def test_fail_path_strategy(self):
        """FAIL 경로: 전략 실패"""
        # Given: 전략 실패
        guardian = FlowGuardian(
            config=self.config,
            source=MockDataSource(),
            strategy=MockStrategy(fail=True),
            risk=MockRisk(),
            executor=MockBroker(),
            metrics=MockMetrics(),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: FAIL
        self.assertFalse(result.ready)
        self.assertGreater(len(result.errors), 0)
    
    def test_fail_path_risk(self):
        """FAIL 경로: 리스크 차단"""
        # Given: 리스크 차단
        guardian = FlowGuardian(
            config=self.config,
            source=MockDataSource(),
            strategy=MockStrategy(),
            risk=MockRisk(fail=True),
            executor=MockBroker(),
            metrics=MockMetrics(),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: FAIL
        self.assertFalse(result.ready)
        self.assertGreater(len(result.errors), 0)
        self.assertIn('리스크', result.errors[0])
    
    def test_fail_path_metrics_threshold(self):
        """FAIL 경로: 메트릭 임계치 미달"""
        # Given: 낮은 PF
        guardian = FlowGuardian(
            config=self.config,
            source=MockDataSource(),
            strategy=MockStrategy(),
            risk=MockRisk(),
            executor=MockBroker(),
            metrics=MockMetrics(low_pf=True),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: FAIL
        self.assertFalse(result.ready)
        self.assertGreater(len(result.errors), 0)
        self.assertIn('Profit Factor', result.errors[0])
    
    def test_gate_disabled(self):
        """게이트 비활성화 시 우회"""
        # Given: 게이트 비활성화
        config = self.config.copy()
        config['flow_guardian']['enabled'] = False
        
        guardian = FlowGuardian(
            config=config,
            source=MockDataSource(),
            strategy=MockStrategy(),
            risk=MockRisk(),
            executor=MockBroker(),
            metrics=MockMetrics(),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: READY (우회)
        self.assertTrue(result.ready)
        self.assertIn('bypassed', result.metrics)
    
    @patch('core.flow_guardian.get_db_connection')
    def test_db_verification(self, mock_db):
        """DB==JSON score_total 검증"""
        # Given: DB 검증 활성화된 설정
        config_with_db = self.config.copy()
        config_with_db['flow_guardian']['selftest']['consistency_checks']['db_vs_json_score_equal'] = True
        
        # Mock DB connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0.85]  # score_total from DB
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_db.return_value = mock_conn
        
        guardian = FlowGuardian(
            config=config_with_db,
            source=MockDataSource(),
            strategy=MockStrategy(),
            risk=MockRisk(),
            executor=MockBroker(),
            metrics=MockMetrics(),
        )
        
        # When: 셀프테스트 실행
        result = guardian.run_selftest()
        
        # Then: READY + DB 검증 완료
        self.assertTrue(result.ready)
        mock_db.assert_called()  # DB 연결 시도 확인
    
    def test_gate_result_structure(self):
        """GateResult 구조 검증"""
        # Given: GateResult 생성
        result = GateResult(
            ready=True,
            errors=[],
            metrics={'pf': 1.5, 'wr': 0.6},
        )
        
        # Then: 구조 확인
        self.assertTrue(result.ready)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.metrics['pf'], 1.5)


if __name__ == '__main__':
    unittest.main()
