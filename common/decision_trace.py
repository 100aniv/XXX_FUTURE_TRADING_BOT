#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DecisionTrace - 진입/차단 사유 구조화 기록
==========================================
PHASE35-1: 품질 원인 추적 시스템

Purpose:
- PHASE34 교훈: "왜 이 WR/PF가 나오는지" 수치로 증명
- 레짐별/전략별/차단 사유별 분해 통계
- 백테스트 후 분석 가능한 구조화된 로그

Output Format:
{
  "timestamp": "2025-01-15T10:30:00",
  "symbol": "BTCUSDT",
  "regime": "TREND_UP",
  "sub_model_votes": {...},
  "ensemble_decision": "LONG",
  "final_action": "ENTRY" | "BLOCK",
  "block_reason": null | "regime_chop" | "no_consensus" | ...
}
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import pandas as pd

logger = logging.getLogger(__name__)


class DecisionTrace:
    """
    DecisionTrace Logger
    
    진입/차단 사유를 구조화하여 기록하고,
    백테스트 후 레짐별/전략별 분해 통계 제공
    
    Usage:
        trace = DecisionTrace(output_dir="reports/backtest/phase35/traces")
        
        trace.record_decision(
            timestamp=now,
            symbol="BTCUSDT",
            regime="TREND",
            sub_model_votes={...},
            ensemble_decision="LONG",
            final_action="ENTRY",
            block_reason=None
        )
        
        summary = trace.get_summary()
    """
    
    def __init__(self, output_dir: str = "reports/backtest/phase35/traces", enabled: bool = True):
        self.output_dir = Path(output_dir)
        self.enabled = enabled
        self.traces: List[Dict[str, Any]] = []
        
        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def record_decision(
        self,
        timestamp: datetime,
        symbol: str,
        regime: str,
        sub_model_votes: Dict[str, Dict[str, Any]],
        ensemble_decision: str,
        final_action: str,
        block_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        진입/차단 결정 기록
        
        Args:
            timestamp: 결정 시각
            symbol: 심볼
            regime: 레짐 (TREND/RANGE/CHOP)
            sub_model_votes: 각 Sub-Model의 투표
            ensemble_decision: 앙상블 결정 (LONG/SHORT/None)
            final_action: 최종 액션 (ENTRY/BLOCK)
            block_reason: 차단 사유 (None if ENTRY)
            metadata: 추가 메타데이터
        """
        if not self.enabled:
            return
        
        trace_entry = {
            'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
            'symbol': symbol,
            'regime': regime,
            'sub_model_votes': sub_model_votes,
            'ensemble_decision': ensemble_decision,
            'final_action': final_action,
            'block_reason': block_reason,
            'metadata': metadata or {}
        }
        
        self.traces.append(trace_entry)
    
    def save(self, filename: str = "decision_trace.json"):
        """
        Trace 데이터를 JSON 파일로 저장
        
        Args:
            filename: 출력 파일명
        """
        if not self.enabled or not self.traces:
            logger.warning("[DecisionTrace] No traces to save")
            return
        
        output_path = self.output_dir / filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.traces, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ [DecisionTrace] Saved {len(self.traces)} traces to {output_path}")
        
        except Exception as e:
            logger.error(f"❌ [DecisionTrace] Failed to save: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        DecisionTrace 요약 통계
        
        Returns:
            {
                'total_decisions': int,
                'entry_count': int,
                'block_count': int,
                'block_rate': float,
                'regime_breakdown': {...},
                'block_reason_breakdown': {...},
                'sub_model_contribution': {...}
            }
        """
        if not self.traces:
            return {}
        
        total_decisions = len(self.traces)
        entry_count = sum(1 for t in self.traces if t['final_action'] == 'ENTRY')
        block_count = sum(1 for t in self.traces if t['final_action'] == 'BLOCK')
        
        # Regime별 분해
        regime_breakdown = defaultdict(lambda: {'total': 0, 'entry': 0, 'block': 0})
        for trace in self.traces:
            regime = trace['regime']
            regime_breakdown[regime]['total'] += 1
            if trace['final_action'] == 'ENTRY':
                regime_breakdown[regime]['entry'] += 1
            else:
                regime_breakdown[regime]['block'] += 1
        
        # Block Reason별 분해
        block_reason_breakdown = defaultdict(int)
        for trace in self.traces:
            if trace['final_action'] == 'BLOCK' and trace['block_reason']:
                block_reason_breakdown[trace['block_reason']] += 1
        
        # Sub-Model 기여도
        sub_model_contribution = defaultdict(lambda: {'LONG': 0, 'SHORT': 0, 'FLAT': 0})
        for trace in self.traces:
            votes = trace.get('sub_model_votes', {})
            for model_name, vote in votes.items():
                direction = vote.get('direction')
                if direction is None:
                    sub_model_contribution[model_name]['FLAT'] += 1
                else:
                    sub_model_contribution[model_name][direction] += 1
        
        # Top Blockers
        sorted_blockers = sorted(
            block_reason_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'total_decisions': total_decisions,
            'entry_count': entry_count,
            'block_count': block_count,
            'block_rate': block_count / total_decisions if total_decisions > 0 else 0.0,
            'regime_breakdown': dict(regime_breakdown),
            'block_reason_breakdown': dict(block_reason_breakdown),
            'top_blockers': sorted_blockers[:10],
            'sub_model_contribution': dict(sub_model_contribution)
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Trace 데이터를 DataFrame으로 변환
        
        Returns:
            pd.DataFrame with columns:
            - timestamp, symbol, regime, ensemble_decision, final_action, block_reason
        """
        if not self.traces:
            return pd.DataFrame()
        
        flattened = []
        for trace in self.traces:
            row = {
                'timestamp': trace['timestamp'],
                'symbol': trace['symbol'],
                'regime': trace['regime'],
                'ensemble_decision': trace['ensemble_decision'],
                'final_action': trace['final_action'],
                'block_reason': trace['block_reason']
            }
            
            # Sub-Model Votes 평탄화
            for model_name, vote in trace.get('sub_model_votes', {}).items():
                row[f'{model_name}_direction'] = vote.get('direction')
                row[f'{model_name}_confidence'] = vote.get('confidence', 0.0)
            
            flattened.append(row)
        
        return pd.DataFrame(flattened)
    
    def analyze_regime_performance(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        레짐별 성과 분석 (Trade 결과와 결합)
        
        Args:
            trades_df: Trade 결과 DataFrame (columns: entry_time, exit_time, pnl, ...)
        
        Returns:
            {
                'TREND': {'trades': int, 'win_rate': float, 'avg_pnl': float, ...},
                'RANGE': {...},
                'CHOP': {...}
            }
        """
        if not self.traces or trades_df.empty:
            return {}
        
        trace_df = self.to_dataframe()
        
        # Entry만 필터
        entry_df = trace_df[trace_df['final_action'] == 'ENTRY'].copy()
        
        if entry_df.empty:
            return {}
        
        # Trade와 매칭 (timestamp 기준)
        entry_df['timestamp'] = pd.to_datetime(entry_df['timestamp'])
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        
        merged = pd.merge_asof(
            trades_df.sort_values('entry_time'),
            entry_df.sort_values('timestamp'),
            left_on='entry_time',
            right_on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta('1min')
        )
        
        # Regime별 집계
        regime_perf = {}
        for regime in merged['regime'].dropna().unique():
            regime_trades = merged[merged['regime'] == regime]
            
            if len(regime_trades) == 0:
                continue
            
            wins = len(regime_trades[regime_trades['pnl'] > 0])
            total = len(regime_trades)
            
            regime_perf[regime] = {
                'trades': total,
                'win_rate': wins / total if total > 0 else 0.0,
                'avg_pnl': regime_trades['pnl'].mean(),
                'total_pnl': regime_trades['pnl'].sum(),
                'profit_factor': self._calculate_pf(regime_trades['pnl'])
            }
        
        return regime_perf
    
    def _calculate_pf(self, pnl_series: pd.Series) -> float:
        """Profit Factor 계산"""
        wins = pnl_series[pnl_series > 0].sum()
        losses = abs(pnl_series[pnl_series < 0].sum())
        
        if losses == 0:
            return float('inf') if wins > 0 else 0.0
        
        return wins / losses
    
    def clear(self):
        """Trace 데이터 초기화"""
        self.traces.clear()
        logger.info("[DecisionTrace] Cleared all traces")


class DecisionTraceAnalyzer:
    """
    DecisionTrace 분석기
    
    저장된 Trace JSON을 로드하여 상세 분석 제공
    
    Usage:
        analyzer = DecisionTraceAnalyzer("reports/backtest/phase35/traces/decision_trace.json")
        summary = analyzer.analyze()
    """
    
    def __init__(self, trace_file: str):
        self.trace_file = Path(trace_file)
        self.traces = []
        
        if self.trace_file.exists():
            self._load()
    
    def _load(self):
        """Trace JSON 로드"""
        try:
            with open(self.trace_file, 'r', encoding='utf-8') as f:
                self.traces = json.load(f)
            logger.info(f"✅ [DecisionTraceAnalyzer] Loaded {len(self.traces)} traces from {self.trace_file}")
        except Exception as e:
            logger.error(f"❌ [DecisionTraceAnalyzer] Failed to load: {e}")
    
    def analyze(self) -> Dict[str, Any]:
        """
        전체 분석 실행
        
        Returns:
            {
                'summary': {...},
                'regime_analysis': {...},
                'block_reason_analysis': {...},
                'sub_model_analysis': {...}
            }
        """
        if not self.traces:
            return {}
        
        # 기본 요약
        trace_obj = DecisionTrace(enabled=False)
        trace_obj.traces = self.traces
        summary = trace_obj.get_summary()
        
        # 레짐별 분석
        regime_analysis = self._analyze_regime()
        
        # Block Reason 분석
        block_reason_analysis = self._analyze_block_reasons()
        
        # Sub-Model 분석
        sub_model_analysis = self._analyze_sub_models()
        
        return {
            'summary': summary,
            'regime_analysis': regime_analysis,
            'block_reason_analysis': block_reason_analysis,
            'sub_model_analysis': sub_model_analysis
        }
    
    def _analyze_regime(self) -> Dict[str, Any]:
        """레짐별 상세 분석"""
        regime_stats = defaultdict(lambda: {
            'total': 0,
            'entry': 0,
            'block': 0,
            'block_reasons': defaultdict(int)
        })
        
        for trace in self.traces:
            regime = trace['regime']
            regime_stats[regime]['total'] += 1
            
            if trace['final_action'] == 'ENTRY':
                regime_stats[regime]['entry'] += 1
            else:
                regime_stats[regime]['block'] += 1
                if trace['block_reason']:
                    regime_stats[regime]['block_reasons'][trace['block_reason']] += 1
        
        # Entry Rate 계산
        for regime, stats in regime_stats.items():
            stats['entry_rate'] = stats['entry'] / stats['total'] if stats['total'] > 0 else 0.0
            stats['block_rate'] = stats['block'] / stats['total'] if stats['total'] > 0 else 0.0
            stats['top_block_reasons'] = sorted(
                stats['block_reasons'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        
        return dict(regime_stats)
    
    def _analyze_block_reasons(self) -> Dict[str, Any]:
        """차단 사유별 분석"""
        block_reasons = defaultdict(int)
        
        for trace in self.traces:
            if trace['final_action'] == 'BLOCK' and trace['block_reason']:
                block_reasons[trace['block_reason']] += 1
        
        sorted_reasons = sorted(
            block_reasons.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_blocks = sum(block_reasons.values())
        
        return {
            'total_blocks': total_blocks,
            'unique_reasons': len(block_reasons),
            'top_reasons': [
                {
                    'reason': reason,
                    'count': count,
                    'pct': count / total_blocks if total_blocks > 0 else 0.0
                }
                for reason, count in sorted_reasons[:10]
            ],
            'all_reasons': dict(block_reasons)
        }
    
    def _analyze_sub_models(self) -> Dict[str, Any]:
        """Sub-Model별 기여도 분석"""
        sub_model_stats = defaultdict(lambda: {
            'LONG': 0,
            'SHORT': 0,
            'FLAT': 0,
            'total': 0,
            'avg_confidence': 0.0,
            'confidence_sum': 0.0
        })
        
        for trace in self.traces:
            votes = trace.get('sub_model_votes', {})
            for model_name, vote in votes.items():
                direction = vote.get('direction')
                confidence = vote.get('confidence', 0.0)
                
                sub_model_stats[model_name]['total'] += 1
                sub_model_stats[model_name]['confidence_sum'] += confidence
                
                if direction is None:
                    sub_model_stats[model_name]['FLAT'] += 1
                else:
                    sub_model_stats[model_name][direction] += 1
        
        # 평균 confidence 계산
        for model_name, stats in sub_model_stats.items():
            if stats['total'] > 0:
                stats['avg_confidence'] = stats['confidence_sum'] / stats['total']
            
            stats['vote_distribution'] = {
                'LONG': stats['LONG'] / stats['total'] if stats['total'] > 0 else 0.0,
                'SHORT': stats['SHORT'] / stats['total'] if stats['total'] > 0 else 0.0,
                'FLAT': stats['FLAT'] / stats['total'] if stats['total'] > 0 else 0.0
            }
        
        return dict(sub_model_stats)
    
    def save_analysis(self, output_file: str = "decision_trace_analysis.json"):
        """분석 결과 저장"""
        analysis = self.analyze()
        
        output_path = self.trace_file.parent / output_file
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ [DecisionTraceAnalyzer] Saved analysis to {output_path}")
        
        except Exception as e:
            logger.error(f"❌ [DecisionTraceAnalyzer] Failed to save analysis: {e}")
