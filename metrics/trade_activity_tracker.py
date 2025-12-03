#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade Activity Tracker
======================
Drop-off instrumentation for Signal → Trade pipeline

PHASE27-0: Diagnosis of 0-trade issue

Purpose:
- Track signal survival across pipeline stages
- Identify where signals are being dropped
- Provide quantitative data for parameter tuning

Usage:
    tracker = TradeActivityTracker(run_id="phase27_0_test")
    
    # In engine/strategy code:
    tracker.record_strategy_signal(symbol="BTCUSDT", strategy_id="scalping_v3", has_signal=True)
    tracker.record_ensemble_decision(symbol="BTCUSDT", tier="tier1", side="LONG")
    tracker.record_guard_block(symbol="BTCUSDT", reason="cooldown_active")
    tracker.record_order_submitted(symbol="BTCUSDT", side="LONG", size=0.1)
    
    # At end of run:
    tracker.save_json(Path("output.json"))
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict


class TradeActivityTracker:
    """
    Drop-off instrumentation for Signal → Trade pipeline
    
    Tracks:
    - Strategy signals (per symbol, per strategy)
    - Ensemble decisions (Tier1/Tier2/Skip)
    - Guard blocks (by reason)
    - Order submissions
    
    Thread-safe for multi-threaded environments.
    """
    
    def __init__(self, run_id: str, duration_minutes: Optional[float] = None):
        """
        Initialize tracker
        
        Args:
            run_id: Unique identifier for this run
            duration_minutes: Duration of the run (optional, can be updated later)
        """
        self.run_id = run_id
        self.duration_minutes = duration_minutes
        self.start_time = datetime.now()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Per-symbol counters
        # Structure: symbols[symbol][category][...] = count
        self.symbols: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "strategy_signals": defaultdict(lambda: {"total_calls": 0, "signal_true": 0, "signal_false": 0}),
            "ensemble_decisions": defaultdict(int),  # tier1, tier2, skip
            "guard_blocks": defaultdict(int),  # reason -> count
            "orders_submitted": 0
        })
        
        # Global totals (for quick summary)
        self.totals = {
            "strategy_signals_total": 0,
            "strategy_signals_true": 0,
            "strategy_signals_false": 0,
            "ensemble_tier1": 0,
            "ensemble_tier2": 0,
            "ensemble_skip": 0,
            "guard_blocks_total": 0,
            "orders_submitted": 0
        }
    
    def record_strategy_signal(self, symbol: str, strategy_id: str, has_signal: bool) -> None:
        """
        Record strategy signal generation
        
        Args:
            symbol: Trading symbol
            strategy_id: Strategy identifier
            has_signal: True if strategy generated a signal, False otherwise
        """
        with self._lock:
            symbol_data = self.symbols[symbol]
            strategy_data = symbol_data["strategy_signals"][strategy_id]
            
            strategy_data["total_calls"] += 1
            self.totals["strategy_signals_total"] += 1
            
            if has_signal:
                strategy_data["signal_true"] += 1
                self.totals["strategy_signals_true"] += 1
            else:
                strategy_data["signal_false"] += 1
                self.totals["strategy_signals_false"] += 1
    
    def record_ensemble_decision(self, symbol: str, tier: str, side: Optional[str] = None) -> None:
        """
        Record ensemble aggregator decision
        
        Args:
            symbol: Trading symbol
            tier: Decision tier ("tier1", "tier2", "skip")
            side: Trade side ("LONG", "SHORT", None for skip)
        """
        with self._lock:
            symbol_data = self.symbols[symbol]
            
            # Normalize tier string
            tier_key = tier.lower() if tier else "skip"
            
            symbol_data["ensemble_decisions"][tier_key] += 1
            
            # Update totals
            if tier_key == "tier1":
                self.totals["ensemble_tier1"] += 1
            elif tier_key == "tier2":
                self.totals["ensemble_tier2"] += 1
            else:
                self.totals["ensemble_skip"] += 1
    
    def record_guard_block(self, symbol: str, reason: str) -> None:
        """
        Record guard block event
        
        Args:
            symbol: Trading symbol
            reason: Block reason (e.g., "cooldown_active", "dd_exceeded", "flash_guard")
        """
        with self._lock:
            symbol_data = self.symbols[symbol]
            symbol_data["guard_blocks"][reason] += 1
            self.totals["guard_blocks_total"] += 1
    
    def record_order_submitted(self, symbol: str, side: str, size: float) -> None:
        """
        Record order submission
        
        Args:
            symbol: Trading symbol
            side: Trade side ("LONG", "SHORT")
            size: Order size
        """
        with self._lock:
            symbol_data = self.symbols[symbol]
            symbol_data["orders_submitted"] += 1
            self.totals["orders_submitted"] += 1
    
    def set_duration(self, duration_minutes: float) -> None:
        """
        Update duration (can be called after initialization)
        
        Args:
            duration_minutes: Actual run duration in minutes
        """
        with self._lock:
            self.duration_minutes = duration_minutes
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get complete summary statistics
        
        Returns:
            Dictionary with all tracked metrics
        """
        with self._lock:
            # Convert defaultdicts to regular dicts for JSON serialization
            symbols_dict = {}
            for symbol, data in self.symbols.items():
                symbols_dict[symbol] = {
                    "strategy_signals": dict(data["strategy_signals"]),
                    "ensemble_decisions": dict(data["ensemble_decisions"]),
                    "guard_blocks": dict(data["guard_blocks"]),
                    "orders_submitted": data["orders_submitted"]
                }
            
            return {
                "run_id": self.run_id,
                "duration_minutes": self.duration_minutes,
                "timestamp": self.start_time.isoformat(),
                "end_timestamp": datetime.now().isoformat(),
                "symbols": symbols_dict,
                "totals": self.totals.copy()
            }
    
    def save_json(self, output_path: Path) -> None:
        """
        Save results to JSON file
        
        Args:
            output_path: Path to output JSON file
        """
        summary = self.get_summary()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def get_signal_survival_rate(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate signal survival rate (for analysis)
        
        Args:
            symbol: If provided, calculate for specific symbol. Otherwise, global rate.
        
        Returns:
            Dictionary with survival rates at each stage
        """
        with self._lock:
            if symbol:
                # Per-symbol rate
                if symbol not in self.symbols:
                    return {}
                
                data = self.symbols[symbol]
                total_signals = sum(
                    s["signal_true"]
                    for s in data["strategy_signals"].values()
                )
                ensemble_active = (
                    data["ensemble_decisions"].get("tier1", 0) +
                    data["ensemble_decisions"].get("tier2", 0)
                )
                guard_blocks = sum(data["guard_blocks"].values())
                orders = data["orders_submitted"]
                
            else:
                # Global rate
                total_signals = self.totals["strategy_signals_true"]
                ensemble_active = self.totals["ensemble_tier1"] + self.totals["ensemble_tier2"]
                guard_blocks = self.totals["guard_blocks_total"]
                orders = self.totals["orders_submitted"]
            
            # Calculate survival rates
            result = {
                "strategy_signals": total_signals,
                "ensemble_active": ensemble_active,
                "guard_blocks": guard_blocks,
                "orders_submitted": orders
            }
            
            if total_signals > 0:
                result["ensemble_survival_rate"] = ensemble_active / total_signals
                if ensemble_active > 0:
                    result["guard_survival_rate"] = (ensemble_active - guard_blocks) / ensemble_active
                    if ensemble_active > guard_blocks:
                        result["order_submission_rate"] = orders / (ensemble_active - guard_blocks)
            
            return result
    
    def __repr__(self) -> str:
        return f"TradeActivityTracker(run_id={self.run_id}, symbols={len(self.symbols)}, orders={self.totals['orders_submitted']})"
