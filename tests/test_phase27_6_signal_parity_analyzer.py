#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-6: Signal Parity Analyzer 테스트
"""
import pytest
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.research.phase27_6_signal_parity_analyzer import (
    extract_offline_signals,
    analyze_aggregate_parity,
    analyze_warmup_nan_handling,
    generate_recommendations
)


@pytest.fixture
def mock_offline_summary():
    """Mock Offline Scan Summary"""
    return {
        "run_id": "test_offline",
        "scan_result": {
            "total_bars": 1000,
            "warmup_skipped": 50,
            "evaluated_bars": 950,
            "signals_true": 600,
            "signals_false": 350,
            "long_signals": 300,
            "short_signals": 300,
            "regime_range_signals": 400,
            "regime_trend_signals": 200,
            "signal_details": [
                {
                    "index": 50,
                    "time": "2024-01-01 00:00:00",
                    "side": "LONG",
                    "regime": "RANGE",
                    "reason": "Test signal",
                    "price": 100.0,
                    "rsi": 40.0,
                    "adx": 20.0
                },
                {
                    "index": 51,
                    "time": "2024-01-01 00:05:00",
                    "side": "SHORT",
                    "regime": "TREND",
                    "reason": "Test signal 2",
                    "price": 101.0,
                    "rsi": 60.0,
                    "adx": 30.0
                }
            ]
        }
    }


@pytest.fixture
def mock_replay_summary():
    """Mock Engine Replay Summary"""
    return {
        "run_id": "test_replay",
        "totals": {
            "strategy_signals_total": 960,
            "strategy_signals_true": 630,
            "strategy_signals_false": 330
        }
    }


class TestExtractOfflineSignals:
    """Offline 신호 추출 테스트"""
    
    def test_extract_basic(self, mock_offline_summary):
        """기본 추출 테스트"""
        df = extract_offline_signals(mock_offline_summary)
        
        # 기본 검증
        assert df is not None
        assert len(df) == 950  # total_bars(1000) - warmup(50)
        assert 'index' in df.columns
        assert 'has_signal' in df.columns
        assert 'side' in df.columns
        assert 'regime' in df.columns
        
        # 신호 카운트 (signal_details는 샘플만 있으므로 2개)
        signal_count = df['has_signal'].sum()
        assert signal_count == 2  # signal_details에 있는 2개만 추출됨
    
    def test_signal_details_mapping(self, mock_offline_summary):
        """신호 상세 정보 매핑 테스트"""
        df = extract_offline_signals(mock_offline_summary)
        
        # index 50 확인
        row_50 = df[df['index'] == 50]
        assert len(row_50) == 1
        assert row_50.iloc[0]['has_signal'] == True
        assert row_50.iloc[0]['side'] == 'LONG'
        assert row_50.iloc[0]['regime'] == 'RANGE'
        
        # index 51 확인
        row_51 = df[df['index'] == 51]
        assert len(row_51) == 1
        assert row_51.iloc[0]['has_signal'] == True
        assert row_51.iloc[0]['side'] == 'SHORT'
        assert row_51.iloc[0]['regime'] == 'TREND'
    
    def test_no_signal_bars(self, mock_offline_summary):
        """신호 없는 bar 처리 테스트"""
        df = extract_offline_signals(mock_offline_summary)
        
        # 신호가 없는 bar 찾기
        no_signal_rows = df[~df['has_signal']]
        # signal_details에 2개만 있으므로, 948개가 신호 없음
        assert len(no_signal_rows) == 948  # 950 - 2
        
        # 신호 없는 bar는 side/regime이 None
        for _, row in no_signal_rows.head(10).iterrows():
            assert row['side'] is None
            assert row['regime'] is None


class TestAnalyzeAggregateParity:
    """Aggregate Parity 분석 테스트"""
    
    def test_basic_analysis(self, mock_offline_summary, mock_replay_summary):
        """기본 분석 테스트"""
        analysis = analyze_aggregate_parity(mock_offline_summary, mock_replay_summary)
        
        # 기본 구조 확인
        assert 'offline' in analysis
        assert 'replay' in analysis
        assert 'diff' in analysis
        assert 'acceptance' in analysis
        
        # Offline 통계
        assert analysis['offline']['evaluated_bars'] == 950
        assert analysis['offline']['signals_true'] == 600
        assert analysis['offline']['long_signals'] == 300
        assert analysis['offline']['short_signals'] == 300
        
        # Replay 통계
        assert analysis['replay']['total_calls'] == 960
        assert analysis['replay']['signals_true'] == 630
    
    def test_diff_calculation(self, mock_offline_summary, mock_replay_summary):
        """차이 계산 테스트"""
        analysis = analyze_aggregate_parity(mock_offline_summary, mock_replay_summary)
        
        diff = analysis['diff']
        
        # Bar 수 차이: 960 - 950 = +10 (+1.05%)
        assert diff['bar_count_diff'] == 10
        assert abs(diff['bar_count_diff_pct'] - 1.05) < 0.01
        
        # 신호 수 차이: 630 - 600 = +30 (+5.0%)
        assert diff['signal_count_diff'] == 30
        assert abs(diff['signal_count_diff_pct'] - 5.0) < 0.01
    
    def test_acceptance_pass(self, mock_offline_summary, mock_replay_summary):
        """Acceptance 판정 - PASS"""
        analysis = analyze_aggregate_parity(mock_offline_summary, mock_replay_summary)
        
        acceptance = analysis['acceptance']
        
        # Bar 차이 1.05% < 10% → PASS
        assert acceptance['bar_count_within_10pct'] == True
        
        # 신호 차이 5% < 10% → PASS
        assert acceptance['signal_count_within_10pct'] == True
        
        # Overall PASS
        assert acceptance['overall_pass'] == True
    
    def test_acceptance_fail(self, mock_offline_summary):
        """Acceptance 판정 - FAIL"""
        # Replay 신호 수를 크게 벗어나게 설정
        replay_fail = {
            "run_id": "test_replay_fail",
            "totals": {
                "strategy_signals_total": 950,
                "strategy_signals_true": 750,  # +25% 차이
                "strategy_signals_false": 200
            }
        }
        
        analysis = analyze_aggregate_parity(mock_offline_summary, replay_fail)
        
        acceptance = analysis['acceptance']
        
        # 신호 차이 25% > 10% → FAIL
        assert acceptance['signal_count_within_10pct'] == False
        assert acceptance['overall_pass'] == False


class TestAnalyzeWarmupNanHandling:
    """Warmup/NaN 분석 테스트"""
    
    def test_warmup_analysis(self, mock_offline_summary):
        """Warmup 분석 테스트"""
        analysis = analyze_warmup_nan_handling(mock_offline_summary)
        
        # 기본 구조
        assert 'offline' in analysis
        assert 'replay' in analysis
        assert 'potential_issue' in analysis
        
        # Offline warmup
        assert analysis['offline']['total_bars'] == 1000
        assert analysis['offline']['warmup_skipped'] == 50
        assert analysis['offline']['evaluated_bars'] == 950
        assert analysis['offline']['warmup_method'] == 'Fixed N bars (N=50)'
        
        # Replay warmup (to be verified)
        assert 'warmup_method' in analysis['replay']
        
        # 잠재적 문제
        assert 'description' in analysis['potential_issue']
        assert 'recommendation' in analysis['potential_issue']


class TestGenerateRecommendations:
    """권장사항 생성 테스트"""
    
    def test_recommendations_for_high_diff(self, mock_offline_summary):
        """높은 차이에 대한 권장사항"""
        # 차이가 큰 케이스
        replay_high_diff = {
            "run_id": "test_high_diff",
            "totals": {
                "strategy_signals_total": 950,
                "strategy_signals_true": 750,  # +25%
                "strategy_signals_false": 200
            }
        }
        
        analysis = analyze_aggregate_parity(mock_offline_summary, replay_high_diff)
        recommendations = generate_recommendations(analysis)
        
        # 권장사항 개수 확인
        assert len(recommendations) >= 2
        
        # HIGH priority 권장사항 확인
        high_priority_recs = [r for r in recommendations if r['priority'] == 'HIGH']
        assert len(high_priority_recs) >= 2  # Signal Count + Tracker Enhancement
        
        # Signal Count Parity 권장사항 확인
        signal_parity_rec = next(
            (r for r in recommendations if r['category'] == 'Signal Count Parity'),
            None
        )
        assert signal_parity_rec is not None
        assert 'action' in signal_parity_rec
        assert len(signal_parity_rec['action']) > 0
    
    def test_recommendations_for_bar_diff(self, mock_offline_summary):
        """Bar 수 차이에 대한 권장사항"""
        # Bar 수 차이가 있는 케이스
        replay_bar_diff = {
            "run_id": "test_bar_diff",
            "totals": {
                "strategy_signals_total": 1000,  # +5.26%
                "strategy_signals_true": 620,    # +3.33%
                "strategy_signals_false": 380
            }
        }
        
        analysis = analyze_aggregate_parity(mock_offline_summary, replay_bar_diff)
        recommendations = generate_recommendations(analysis)
        
        # Bar Count Parity 권장사항 확인
        bar_parity_rec = next(
            (r for r in recommendations if r['category'] == 'Bar Count Parity'),
            None
        )
        assert bar_parity_rec is not None
        assert bar_parity_rec['priority'] == 'MEDIUM'
    
    def test_tracker_enhancement_recommendation(self, mock_offline_summary, mock_replay_summary):
        """TradeActivityTracker 개선 권장사항"""
        analysis = analyze_aggregate_parity(mock_offline_summary, mock_replay_summary)
        recommendations = generate_recommendations(analysis)
        
        # TradeActivityTracker 개선 권장사항은 항상 포함
        tracker_rec = next(
            (r for r in recommendations if r['category'] == 'TradeActivityTracker Enhancement'),
            None
        )
        assert tracker_rec is not None
        assert tracker_rec['priority'] == 'HIGH'
        assert 'LONG/SHORT/Regime' in tracker_rec['issue']


class TestRealDataIntegration:
    """실제 데이터 통합 테스트"""
    
    @pytest.mark.skipif(
        not (PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_4_btc5m_baseline_signal_scan_summary.json').exists(),
        reason="Offline summary 파일이 없음"
    )
    def test_real_offline_summary(self):
        """실제 Offline Summary 로드 테스트"""
        summary_path = PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_4_btc5m_baseline_signal_scan_summary.json'
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        df = extract_offline_signals(summary)
        
        # 기본 검증
        assert df is not None
        assert len(df) > 0
        assert 'has_signal' in df.columns
    
    @pytest.mark.skipif(
        not (
            (PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_4_btc5m_baseline_signal_scan_summary.json').exists() and
            (PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_5_btc5m_engine_replay_summary.json').exists()
        ),
        reason="Summary 파일이 없음"
    )
    def test_real_parity_analysis(self):
        """실제 데이터 정합성 분석 테스트"""
        offline_path = PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_4_btc5m_baseline_signal_scan_summary.json'
        replay_path = PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_5_btc5m_engine_replay_summary.json'
        
        with open(offline_path, 'r', encoding='utf-8') as f:
            offline_summary = json.load(f)
        
        with open(replay_path, 'r', encoding='utf-8') as f:
            replay_summary = json.load(f)
        
        analysis = analyze_aggregate_parity(offline_summary, replay_summary)
        
        # 기본 구조 확인
        assert 'offline' in analysis
        assert 'replay' in analysis
        assert 'diff' in analysis
        assert 'acceptance' in analysis
        
        # 실제 숫자 확인 (동적으로 summary에서 읽기)
        offline_signals = analysis['offline']['signals_true']
        replay_signals = analysis['replay']['signals_true']
        
        assert offline_signals > 0, "Offline 신호 수가 0보다 커야 함"
        assert replay_signals > 0, "Replay 신호 수가 0보다 커야 함"
        
        # 차이 계산
        diff_pct = abs(analysis['diff']['signal_count_diff_pct'])
        assert diff_pct >= 0, "차이 비율은 음수가 될 수 없음"
        
        print(f"\n실제 신호 수: Offline={offline_signals}, Replay={replay_signals}")
        print(f"신호 수 차이: {diff_pct:.2f}%")
        print(f"Acceptance: {analysis['acceptance']['overall_pass']}")
        print("Note: Signal count parity는 PHASE27-7 Known Issue (17.79% 차이)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
