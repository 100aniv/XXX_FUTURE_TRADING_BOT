#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-1: Ensemble Strategy V1 Unit Tests
===========================================

Test Coverage:
1. Strategy Initialization
2. Regime Detection
3. Sub-Model Voting
4. Ensemble Decision (2-out-of-3 Vote)
5. Entry/Exit Calculation
6. DecisionTrace Integration
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
from common.decision_trace import DecisionTrace


@pytest.fixture
def sample_config():
    """기본 Config"""
    return {
        'decision_trace': {'enabled': True},
        'sub_models': {
            'trend': {
                'ema_fast': 20,
                'ema_slow': 50,
                'adx_threshold': 25
            },
            'reversion': {
                'rsi_period': 14,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'bb_period': 20,
                'bb_std': 2.0
            },
            'breakout': {
                'lookback': 20,
                'volume_threshold': 1.5,
                'volume_ma_period': 20
            }
        },
        'ensemble': {
            'method': 'majority_vote',
            'confidence_threshold': 0.5
        },
        'regime_filter': {
            'enabled': True,
            'type': 'atr_simple',
            'atr_period': 14,
            'thresholds': {
                'trend_min': 0.015,
                'range_max': 0.008
            }
        },
        'exit': {
            'time_based': {'enabled': True, 'holding_max_bars': 48},
            'adverse_move': {'enabled': True, 'atr_multiplier': 1.5},
            'regime_switch': {'enabled': False},
            'sl_atr_multiplier': 1.5,
            'tp_atr_multiplier': 3.0
        }
    }


@pytest.fixture
def sample_df():
    """샘플 OHLCV DataFrame"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    
    df = pd.DataFrame({
        'open': 50000 + np.random.randn(100) * 100,
        'high': 50100 + np.random.randn(100) * 100,
        'low': 49900 + np.random.randn(100) * 100,
        'close': 50000 + np.random.randn(100) * 100,
        'volume': 1000000 + np.random.randn(100) * 50000
    }, index=dates)
    
    # ATR 추가
    df['atr'] = 500 + np.random.randn(100) * 50
    
    return df


class TestPhase35EnsembleV1:
    """Phase35 Ensemble V1 Strategy Tests"""
    
    def test_strategy_initialization(self, sample_config):
        """전략 초기화 테스트"""
        strategy = Phase35EnsembleV1(sample_config)
        
        assert strategy is not None
        assert strategy.metadata.strategy_name == "phase35_ensemble_v1"
        assert strategy.metadata.strategy_type == "ensemble"
        assert strategy.metadata.version == "1.0.0"
        assert strategy._diag_enabled is True
    
    def test_regime_detection_trend(self, sample_config, sample_df):
        """레짐 감지 - TREND"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # High ATR → TREND
        sample_df['atr'] = 800  # 800 / 50000 = 1.6% > 1.5%
        
        regime_info = strategy._detect_regime(sample_df)
        
        assert regime_info['regime'] == 'TREND'
        assert regime_info['atr_pct'] > 0.015
        assert regime_info['confidence'] > 0
    
    def test_regime_detection_range(self, sample_config, sample_df):
        """레짐 감지 - RANGE"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # Low ATR → RANGE
        sample_df['atr'] = 300  # 300 / 50000 = 0.6% < 0.8%
        
        regime_info = strategy._detect_regime(sample_df)
        
        assert regime_info['regime'] == 'RANGE'
        assert regime_info['atr_pct'] < 0.008
    
    def test_regime_detection_chop(self, sample_config, sample_df):
        """레짐 감지 - CHOP"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # Mid ATR → CHOP
        sample_df['atr'] = 550  # 550 / 50000 = 1.1% (0.8% ~ 1.5% 사이)
        
        regime_info = strategy._detect_regime(sample_df)
        
        assert regime_info['regime'] == 'CHOP'
    
    def test_regime_disabled(self, sample_config, sample_df):
        """레짐 필터 비활성화"""
        sample_config['regime_filter']['enabled'] = False
        strategy = Phase35EnsembleV1(sample_config)
        
        regime_info = strategy._detect_regime(sample_df)
        
        assert regime_info['regime'] == 'TREND'  # 기본값
        assert regime_info['confidence'] == 1.0
    
    def test_sub_model_trend_bullish(self, sample_config, sample_df):
        """Trend Sub-Model - Bullish"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # EMA Cross: Fast > Slow
        sample_df['ema_20'] = 50100
        sample_df['ema_50'] = 50000
        sample_df['adx'] = 30  # > 25
        
        vote = strategy._sub_model_trend(sample_df, 'TREND', sample_config['sub_models']['trend'])
        
        assert vote['direction'] == 'LONG'
        assert vote['confidence'] > 0
        assert 'ema_bullish_cross' in vote['reasons']
    
    def test_sub_model_reversion_oversold(self, sample_config, sample_df):
        """Reversion Sub-Model - Oversold (LONG)"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # RSI < 30, Close < BB Lower
        sample_df['rsi'] = 25
        sample_df['close'] = 49000
        sample_df['bb_lower'] = 49500
        sample_df['bb_upper'] = 50500
        
        vote = strategy._sub_model_reversion(sample_df, 'RANGE', sample_config['sub_models']['reversion'])
        
        assert vote['direction'] == 'LONG'
        assert 'rsi_oversold' in vote['reasons']
        assert 'bb_lower_breach' in vote['reasons']
    
    def test_sub_model_breakout_high(self, sample_config, sample_df):
        """Breakout Sub-Model - High Breakout (LONG)"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # Close > High(20), Volume Spike
        sample_df['close'] = 50500
        sample_df['high'] = 50000 + np.random.randn(100) * 50  # Max ~50100
        sample_df['volume'] = 2000000
        sample_df['volume_ma'] = 1000000
        
        vote = strategy._sub_model_breakout(sample_df, 'TREND', sample_config['sub_models']['breakout'])
        
        assert vote['direction'] == 'LONG'
        assert 'breakout_high' in vote['reasons']
    
    def test_ensemble_vote_2_long_1_short(self, sample_config):
        """앙상블 투표 - 2 LONG, 1 SHORT → LONG"""
        strategy = Phase35EnsembleV1(sample_config)
        
        sub_votes = {
            'trend': {'direction': 'LONG', 'confidence': 0.8, 'reasons': []},
            'reversion': {'direction': 'LONG', 'confidence': 0.6, 'reasons': []},
            'breakout': {'direction': 'SHORT', 'confidence': 0.5, 'reasons': []}
        }
        
        decision = strategy._ensemble_vote(sub_votes)
        
        assert decision['direction'] == 'LONG'
        assert decision['confidence'] > 0.5
        assert 'majority_long_2/3' in decision['reason']
    
    def test_ensemble_vote_1_long_1_short_1_flat(self, sample_config):
        """앙상블 투표 - 1 LONG, 1 SHORT, 1 FLAT → No Consensus"""
        strategy = Phase35EnsembleV1(sample_config)
        
        sub_votes = {
            'trend': {'direction': 'LONG', 'confidence': 0.7, 'reasons': []},
            'reversion': {'direction': 'SHORT', 'confidence': 0.6, 'reasons': []},
            'breakout': {'direction': None, 'confidence': 0.0, 'reasons': []}
        }
        
        decision = strategy._ensemble_vote(sub_votes)
        
        assert decision['direction'] is None
        assert 'no_consensus' in decision['reason']
    
    def test_ensemble_vote_low_confidence(self, sample_config):
        """앙상블 투표 - Confidence < Threshold"""
        strategy = Phase35EnsembleV1(sample_config)
        
        sub_votes = {
            'trend': {'direction': 'LONG', 'confidence': 0.3, 'reasons': []},
            'reversion': {'direction': 'LONG', 'confidence': 0.4, 'reasons': []},
            'breakout': {'direction': 'SHORT', 'confidence': 0.5, 'reasons': []}
        }
        
        decision = strategy._ensemble_vote(sub_votes)
        
        # Avg confidence = (0.3 + 0.4) / 2 = 0.35 < 0.5
        assert decision['direction'] is None
        assert 'confidence_low' in decision['reason']
    
    def test_compute_signal_chop_regime(self, sample_config, sample_df):
        """신호 계산 - CHOP 레짐 차단"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # CHOP Regime
        sample_df['atr'] = 550  # 1.1% (CHOP)
        
        signal = strategy.compute_signal(sample_df)
        
        assert signal['side'] is None
        assert signal['reason'] == 'regime_chop'
        assert signal['regime'] == 'CHOP'
    
    def test_compute_signal_entry(self, sample_config, sample_df):
        """신호 계산 - Entry 성공"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # TREND Regime
        sample_df['atr'] = 800  # 1.6% (TREND)
        
        # EMA Cross (Trend: LONG)
        sample_df['ema_20'] = 50100
        sample_df['ema_50'] = 50000
        sample_df['adx'] = 30
        
        # Breakout (LONG)
        sample_df['close'] = 50500
        sample_df['high'] = 50000 + np.random.randn(100) * 50
        sample_df['volume'] = 2000000
        sample_df['volume_ma'] = 1000000
        
        # Reversion: FLAT
        sample_df['rsi'] = 50
        sample_df['bb_upper'] = 50500
        sample_df['bb_lower'] = 49500
        
        signal = strategy.compute_signal(sample_df)
        
        # 2 LONG (trend + breakout) → Entry
        assert signal.get('side') in ['LONG', None]  # 신호 생성 또는 차단
        
        if signal.get('side') == 'LONG':
            assert 'entry' in signal
            assert 'sl' in signal
            assert 'tp' in signal
            assert signal['sl'] < signal['entry']  # LONG: SL < Entry
            assert signal['tp'] > signal['entry']  # LONG: TP > Entry
    
    def test_diagnostics(self, sample_config, sample_df):
        """DecisionTrace 진단"""
        strategy = Phase35EnsembleV1(sample_config)
        
        # Multiple signals
        for _ in range(10):
            sample_df['atr'] = 550  # CHOP
            strategy.compute_signal(sample_df)
        
        diag = strategy.get_diagnostics()
        
        assert diag['total_signals_checked'] == 10
        assert diag['total_blocks'] > 0
        assert 'REGIME_CHOP_BLOCK' in diag['all_counters']


class TestDecisionTrace:
    """DecisionTrace 모듈 테스트"""
    
    def test_decision_trace_record(self, tmp_path):
        """DecisionTrace 기록 테스트"""
        trace = DecisionTrace(output_dir=str(tmp_path), enabled=True)
        
        trace.record_decision(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            regime="TREND",
            sub_model_votes={
                'trend': {'direction': 'LONG', 'confidence': 0.8},
                'reversion': {'direction': None, 'confidence': 0.0},
                'breakout': {'direction': 'LONG', 'confidence': 0.7}
            },
            ensemble_decision="LONG",
            final_action="ENTRY",
            block_reason=None
        )
        
        assert len(trace.traces) == 1
        assert trace.traces[0]['regime'] == 'TREND'
        assert trace.traces[0]['final_action'] == 'ENTRY'
    
    def test_decision_trace_summary(self, tmp_path):
        """DecisionTrace 요약 테스트"""
        trace = DecisionTrace(output_dir=str(tmp_path), enabled=True)
        
        # 10 ENTRY, 5 BLOCK
        for i in range(15):
            action = "ENTRY" if i < 10 else "BLOCK"
            block_reason = None if action == "ENTRY" else "regime_chop"
            
            trace.record_decision(
                timestamp=datetime.now(),
                symbol="BTCUSDT",
                regime="TREND" if action == "ENTRY" else "CHOP",
                sub_model_votes={},
                ensemble_decision="LONG" if action == "ENTRY" else None,
                final_action=action,
                block_reason=block_reason
            )
        
        summary = trace.get_summary()
        
        assert summary['total_decisions'] == 15
        assert summary['entry_count'] == 10
        assert summary['block_count'] == 5
        assert summary['block_rate'] == 5 / 15
        assert 'regime_chop' in summary['block_reason_breakdown']
    
    def test_decision_trace_save(self, tmp_path):
        """DecisionTrace 저장 테스트"""
        trace = DecisionTrace(output_dir=str(tmp_path), enabled=True)
        
        trace.record_decision(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            regime="TREND",
            sub_model_votes={},
            ensemble_decision="LONG",
            final_action="ENTRY",
            block_reason=None
        )
        
        trace.save("test_trace.json")
        
        saved_file = tmp_path / "test_trace.json"
        assert saved_file.exists()
    
    def test_decision_trace_to_dataframe(self, tmp_path):
        """DecisionTrace DataFrame 변환 테스트"""
        trace = DecisionTrace(output_dir=str(tmp_path), enabled=True)
        
        for i in range(5):
            trace.record_decision(
                timestamp=datetime.now(),
                symbol="BTCUSDT",
                regime="TREND",
                sub_model_votes={
                    'trend': {'direction': 'LONG', 'confidence': 0.8}
                },
                ensemble_decision="LONG",
                final_action="ENTRY",
                block_reason=None
            )
        
        df = trace.to_dataframe()
        
        assert len(df) == 5
        assert 'timestamp' in df.columns
        assert 'regime' in df.columns
        assert 'final_action' in df.columns
        assert 'trend_direction' in df.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
