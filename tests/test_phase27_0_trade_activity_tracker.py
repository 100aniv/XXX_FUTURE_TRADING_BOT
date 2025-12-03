#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for TradeActivityTracker (PHASE27-0)
==========================================
Unit tests for drop-off instrumentation module
"""
import pytest
import json
import tempfile
from pathlib import Path
from metrics.trade_activity_tracker import TradeActivityTracker


class TestTradeActivityTrackerBasics:
    """Basic functionality tests"""
    
    def test_initialization(self):
        """Test tracker initialization"""
        tracker = TradeActivityTracker(run_id="test_run", duration_minutes=30.0)
        
        assert tracker.run_id == "test_run"
        assert tracker.duration_minutes == 30.0
        assert tracker.totals["strategy_signals_total"] == 0
        assert tracker.totals["orders_submitted"] == 0
    
    def test_record_strategy_signal_true(self):
        """Test recording strategy signal (has_signal=True)"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        
        summary = tracker.get_summary()
        assert summary["totals"]["strategy_signals_total"] == 1
        assert summary["totals"]["strategy_signals_true"] == 1
        assert summary["totals"]["strategy_signals_false"] == 0
        
        # Check per-symbol data
        btc_data = summary["symbols"]["BTCUSDT"]
        assert btc_data["strategy_signals"]["scalping_v3"]["total_calls"] == 1
        assert btc_data["strategy_signals"]["scalping_v3"]["signal_true"] == 1
    
    def test_record_strategy_signal_false(self):
        """Test recording strategy signal (has_signal=False)"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=False)
        
        summary = tracker.get_summary()
        assert summary["totals"]["strategy_signals_total"] == 1
        assert summary["totals"]["strategy_signals_true"] == 0
        assert summary["totals"]["strategy_signals_false"] == 1
    
    def test_record_multiple_strategies(self):
        """Test recording signals from multiple strategies"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        tracker.record_strategy_signal("BTCUSDT", "trend_follow_v2", has_signal=True)
        tracker.record_strategy_signal("BTCUSDT", "mean_reversion_v2", has_signal=False)
        
        summary = tracker.get_summary()
        assert summary["totals"]["strategy_signals_total"] == 3
        assert summary["totals"]["strategy_signals_true"] == 2
        assert summary["totals"]["strategy_signals_false"] == 1
        
        # Check per-strategy breakdown
        btc_data = summary["symbols"]["BTCUSDT"]["strategy_signals"]
        assert btc_data["scalping_v3"]["signal_true"] == 1
        assert btc_data["trend_follow_v2"]["signal_true"] == 1
        assert btc_data["mean_reversion_v2"]["signal_false"] == 1


class TestEnsembleDecisions:
    """Test ensemble decision tracking"""
    
    def test_record_tier1_decision(self):
        """Test recording Tier1 ensemble decision"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        
        summary = tracker.get_summary()
        assert summary["totals"]["ensemble_tier1"] == 1
        assert summary["totals"]["ensemble_tier2"] == 0
        assert summary["totals"]["ensemble_skip"] == 0
        
        btc_data = summary["symbols"]["BTCUSDT"]
        assert btc_data["ensemble_decisions"]["tier1"] == 1
    
    def test_record_tier2_decision(self):
        """Test recording Tier2 ensemble decision"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_ensemble_decision("BTCUSDT", tier="tier2", side="SHORT")
        
        summary = tracker.get_summary()
        assert summary["totals"]["ensemble_tier2"] == 1
    
    def test_record_skip_decision(self):
        """Test recording Skip decision"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_ensemble_decision("BTCUSDT", tier="skip", side=None)
        
        summary = tracker.get_summary()
        assert summary["totals"]["ensemble_skip"] == 1
    
    def test_record_mixed_decisions(self):
        """Test recording mixed ensemble decisions"""
        tracker = TradeActivityTracker(run_id="test")
        
        # Simulate multiple candles
        tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        tracker.record_ensemble_decision("BTCUSDT", tier="skip", side=None)
        tracker.record_ensemble_decision("BTCUSDT", tier="skip", side=None)
        tracker.record_ensemble_decision("BTCUSDT", tier="tier2", side="SHORT")
        
        summary = tracker.get_summary()
        assert summary["totals"]["ensemble_tier1"] == 1
        assert summary["totals"]["ensemble_tier2"] == 1
        assert summary["totals"]["ensemble_skip"] == 2


class TestGuardBlocks:
    """Test guard block tracking"""
    
    def test_record_guard_block(self):
        """Test recording guard block"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_guard_block("BTCUSDT", reason="cooldown_active")
        
        summary = tracker.get_summary()
        assert summary["totals"]["guard_blocks_total"] == 1
        
        btc_data = summary["symbols"]["BTCUSDT"]
        assert btc_data["guard_blocks"]["cooldown_active"] == 1
    
    def test_record_multiple_guard_blocks(self):
        """Test recording multiple guard blocks with different reasons"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_guard_block("BTCUSDT", reason="cooldown_active")
        tracker.record_guard_block("BTCUSDT", reason="dd_exceeded")
        tracker.record_guard_block("BTCUSDT", reason="cooldown_active")
        tracker.record_guard_block("ETHUSDT", reason="flash_guard")
        
        summary = tracker.get_summary()
        assert summary["totals"]["guard_blocks_total"] == 4
        
        btc_data = summary["symbols"]["BTCUSDT"]["guard_blocks"]
        assert btc_data["cooldown_active"] == 2
        assert btc_data["dd_exceeded"] == 1
        
        eth_data = summary["symbols"]["ETHUSDT"]["guard_blocks"]
        assert eth_data["flash_guard"] == 1


class TestOrderSubmission:
    """Test order submission tracking"""
    
    def test_record_order_submitted(self):
        """Test recording order submission"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        
        summary = tracker.get_summary()
        assert summary["totals"]["orders_submitted"] == 1
        
        btc_data = summary["symbols"]["BTCUSDT"]
        assert btc_data["orders_submitted"] == 1
    
    def test_record_multiple_orders(self):
        """Test recording multiple order submissions"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        tracker.record_order_submitted("BTCUSDT", side="SHORT", size=0.2)
        tracker.record_order_submitted("ETHUSDT", side="LONG", size=0.5)
        
        summary = tracker.get_summary()
        assert summary["totals"]["orders_submitted"] == 3
        assert summary["symbols"]["BTCUSDT"]["orders_submitted"] == 2
        assert summary["symbols"]["ETHUSDT"]["orders_submitted"] == 1


class TestMultiSymbol:
    """Test multi-symbol tracking"""
    
    def test_multiple_symbols(self):
        """Test tracking across multiple symbols"""
        tracker = TradeActivityTracker(run_id="test")
        
        # BTCUSDT activity
        tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        
        # ETHUSDT activity
        tracker.record_strategy_signal("ETHUSDT", "trend_follow_v2", has_signal=True)
        tracker.record_ensemble_decision("ETHUSDT", tier="skip", side=None)
        tracker.record_guard_block("ETHUSDT", reason="cooldown_active")
        
        summary = tracker.get_summary()
        
        # Check totals
        assert summary["totals"]["strategy_signals_true"] == 2
        assert summary["totals"]["ensemble_tier1"] == 1
        assert summary["totals"]["ensemble_skip"] == 1
        assert summary["totals"]["orders_submitted"] == 1
        assert summary["totals"]["guard_blocks_total"] == 1
        
        # Check per-symbol data
        assert "BTCUSDT" in summary["symbols"]
        assert "ETHUSDT" in summary["symbols"]
        assert summary["symbols"]["BTCUSDT"]["orders_submitted"] == 1
        assert summary["symbols"]["ETHUSDT"]["orders_submitted"] == 0


class TestSurvivalRate:
    """Test signal survival rate calculation"""
    
    def test_survival_rate_calculation(self):
        """Test survival rate calculation"""
        tracker = TradeActivityTracker(run_id="test")
        
        # Simulate pipeline: 100 strategy calls, 10 signals, 5 tier1, 1 guard block, 4 orders
        for i in range(100):
            tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=(i < 10))
        
        for i in range(5):
            tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        
        tracker.record_guard_block("BTCUSDT", reason="cooldown_active")
        
        for i in range(4):
            tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        
        rate = tracker.get_signal_survival_rate()
        
        assert rate["strategy_signals"] == 10
        assert rate["ensemble_active"] == 5
        assert rate["guard_blocks"] == 1
        assert rate["orders_submitted"] == 4
        
        # Survival rates
        assert rate["ensemble_survival_rate"] == 0.5  # 5/10
        assert rate["guard_survival_rate"] == 0.8  # (5-1)/5
        assert rate["order_submission_rate"] == 1.0  # 4/(5-1)
    
    def test_survival_rate_per_symbol(self):
        """Test survival rate calculation per symbol"""
        tracker = TradeActivityTracker(run_id="test")
        
        # BTCUSDT: 5 signals → 2 tier1 → 2 orders
        for i in range(5):
            tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        
        rate = tracker.get_signal_survival_rate(symbol="BTCUSDT")
        
        assert rate["strategy_signals"] == 5
        assert rate["ensemble_active"] == 2
        assert rate["orders_submitted"] == 2


class TestJSONSerialization:
    """Test JSON save/load"""
    
    def test_save_json(self):
        """Test saving tracker data to JSON"""
        tracker = TradeActivityTracker(run_id="test_run", duration_minutes=30.0)
        
        tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        tracker.record_ensemble_decision("BTCUSDT", tier="tier1", side="LONG")
        tracker.record_order_submitted("BTCUSDT", side="LONG", size=0.1)
        
        # Save to temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.json"
            tracker.save_json(output_path)
            
            # Verify file exists
            assert output_path.exists()
            
            # Load and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["run_id"] == "test_run"
            assert data["duration_minutes"] == 30.0
            assert data["totals"]["strategy_signals_true"] == 1
            assert data["totals"]["orders_submitted"] == 1
            assert "BTCUSDT" in data["symbols"]
    
    def test_json_structure(self):
        """Test JSON output structure"""
        tracker = TradeActivityTracker(run_id="test", duration_minutes=10.0)
        
        tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        
        summary = tracker.get_summary()
        
        # Verify required keys
        assert "run_id" in summary
        assert "duration_minutes" in summary
        assert "timestamp" in summary
        assert "end_timestamp" in summary
        assert "symbols" in summary
        assert "totals" in summary
        
        # Verify symbols structure
        assert isinstance(summary["symbols"], dict)
        btc_data = summary["symbols"]["BTCUSDT"]
        assert "strategy_signals" in btc_data
        assert "ensemble_decisions" in btc_data
        assert "guard_blocks" in btc_data
        assert "orders_submitted" in btc_data


class TestThreadSafety:
    """Test thread safety (basic check)"""
    
    def test_concurrent_updates(self):
        """Test thread safety with concurrent updates"""
        import threading
        
        tracker = TradeActivityTracker(run_id="test")
        
        def worker():
            for i in range(100):
                tracker.record_strategy_signal("BTCUSDT", "scalping_v3", has_signal=True)
        
        # Run 10 threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        summary = tracker.get_summary()
        # Should have 1000 total signals (10 threads × 100 each)
        assert summary["totals"]["strategy_signals_total"] == 1000
        assert summary["totals"]["strategy_signals_true"] == 1000


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_tracker(self):
        """Test tracker with no data"""
        tracker = TradeActivityTracker(run_id="empty")
        
        summary = tracker.get_summary()
        assert summary["totals"]["strategy_signals_total"] == 0
        assert summary["totals"]["orders_submitted"] == 0
        assert len(summary["symbols"]) == 0
    
    def test_set_duration_after_init(self):
        """Test updating duration after initialization"""
        tracker = TradeActivityTracker(run_id="test")
        
        assert tracker.duration_minutes is None
        
        tracker.set_duration(45.0)
        assert tracker.duration_minutes == 45.0
        
        summary = tracker.get_summary()
        assert summary["duration_minutes"] == 45.0
    
    def test_tier_normalization(self):
        """Test tier string normalization (case-insensitive)"""
        tracker = TradeActivityTracker(run_id="test")
        
        tracker.record_ensemble_decision("BTCUSDT", tier="TIER1", side="LONG")
        tracker.record_ensemble_decision("BTCUSDT", tier="Tier2", side="SHORT")
        tracker.record_ensemble_decision("BTCUSDT", tier="SKIP", side=None)
        
        summary = tracker.get_summary()
        # All should be normalized to lowercase
        btc_data = summary["symbols"]["BTCUSDT"]["ensemble_decisions"]
        assert btc_data["tier1"] == 1
        assert btc_data["tier2"] == 1
        assert btc_data["skip"] == 1
