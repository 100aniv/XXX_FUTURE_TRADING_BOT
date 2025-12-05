#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-7: Signal Parity Per-Bar Diff Harness Tests
====================================================
"""
import pytest
from pathlib import Path
import sys

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.research.phase27_7_btc5m_signal_parity_diff import (
    extract_offline_signals_df,
    extract_replay_signals_df,
    analyze_aggregate_diff,
    generate_summary_report
)


class TestExtractOfflineSignals:
    """Offline Scan 신호 추출 테스트"""
    
    def test_extract_basic(self):
        """기본 추출 테스트"""
        offline_summary = {
            'scan_result': {
                'total_bars': 100,
                'warmup_skipped': 10,
                'evaluated_bars': 90,
                'signals_true': 30,
                'signal_details': [
                    {'index': 10, 'time': '2024-01-01 00:00:00', 'side': 'LONG', 'regime': 'RANGE'},
                    {'index': 20, 'time': '2024-01-01 01:00:00', 'side': 'SHORT', 'regime': 'TREND'}
                ]
            }
        }
        
        df = extract_offline_signals_df(offline_summary)
        
        assert df is not None
        assert len(df) == 90  # warmup_skipped ~ total_bars
        assert 'index' in df.columns
        assert 'has_signal' in df.columns
        assert 'side' in df.columns
        assert 'regime' in df.columns
        
        # 신호 있는 bar 확인
        signal_rows = df[df['has_signal']]
        assert len(signal_rows) == 2
    
    def test_signal_mapping(self):
        """신호 매핑 테스트"""
        offline_summary = {
            'scan_result': {
                'total_bars': 60,
                'warmup_skipped': 50,
                'evaluated_bars': 10,
                'signals_true': 2,
                'signal_details': [
                    {'index': 50, 'time': '2024-01-01 00:00:00', 'side': 'LONG', 'regime': 'RANGE'},
                    {'index': 55, 'time': '2024-01-01 05:00:00', 'side': 'SHORT', 'regime': 'TREND'}
                ]
            }
        }
        
        df = extract_offline_signals_df(offline_summary)
        
        # index 50 확인
        row_50 = df[df['index'] == 50]
        assert len(row_50) == 1
        assert row_50.iloc[0]['has_signal'] == True
        assert row_50.iloc[0]['side'] == 'LONG'
        assert row_50.iloc[0]['regime'] == 'RANGE'
        
        # index 55 확인
        row_55 = df[df['index'] == 55]
        assert len(row_55) == 1
        assert row_55.iloc[0]['has_signal'] == True
        assert row_55.iloc[0]['side'] == 'SHORT'
        assert row_55.iloc[0]['regime'] == 'TREND'
        
        # 신호 없는 bar 확인
        row_51 = df[df['index'] == 51]
        assert len(row_51) == 1
        assert row_51.iloc[0]['has_signal'] == False


class TestExtractReplaySignals:
    """Engine Replay 신호 추출 테스트"""
    
    def test_extract_totals(self):
        """Replay totals 추출 테스트"""
        replay_summary = {
            'totals': {
                'strategy_signals_total': 100,
                'strategy_signals_true': 60,
                'long_signals': 30,
                'short_signals': 30,
                'regime_range': 40,
                'regime_trend': 20
            }
        }
        
        df = extract_replay_signals_df(replay_summary)
        
        assert df is not None
        assert len(df) == 1  # Aggregate 정보만
        
        row = df.iloc[0]
        assert row['total_calls'] == 100
        assert row['signals_true'] == 60
        assert row['long_signals'] == 30
        assert row['short_signals'] == 30
        assert row['regime_range'] == 40
        assert row['regime_trend'] == 20


class TestAnalyzeAggregateDiff:
    """Aggregate 차이 분석 테스트"""
    
    def test_perfect_parity(self):
        """완벽한 parity 케이스"""
        offline_summary = {
            'scan_result': {
                'evaluated_bars': 100,
                'signals_true': 50,
                'long_signals': 25,
                'short_signals': 25,
                'regime_range_signals': 30,
                'regime_trend_signals': 20
            }
        }
        
        replay_summary = {
            'totals': {
                'strategy_signals_total': 100,
                'strategy_signals_true': 50,
                'long_signals': 25,
                'short_signals': 25,
                'regime_range': 30,
                'regime_trend': 20
            }
        }
        
        analysis = analyze_aggregate_diff(offline_summary, replay_summary)
        
        assert analysis['diff']['bar_count_diff'] == 0
        assert analysis['diff']['signal_count_diff'] == 0
        assert analysis['diff']['long_diff'] == 0
        assert analysis['diff']['short_diff'] == 0
        assert analysis['acceptance']['overall_pass'] == True
    
    def test_signal_count_mismatch(self):
        """신호 수 불일치 케이스"""
        offline_summary = {
            'scan_result': {
                'evaluated_bars': 100,
                'signals_true': 50,
                'long_signals': 25,
                'short_signals': 25,
                'regime_range_signals': 30,
                'regime_trend_signals': 20
            }
        }
        
        replay_summary = {
            'totals': {
                'strategy_signals_total': 100,
                'strategy_signals_true': 65,  # +30%
                'long_signals': 32,
                'short_signals': 33,
                'regime_range': 40,
                'regime_trend': 25
            }
        }
        
        analysis = analyze_aggregate_diff(offline_summary, replay_summary)
        
        assert analysis['diff']['signal_count_diff'] == 15
        assert analysis['diff']['signal_count_diff_pct'] == 30.0
        assert analysis['acceptance']['signal_count_within_10pct'] == False
        assert analysis['acceptance']['overall_pass'] == False
    
    def test_regime_mismatch(self):
        """Regime 분류 불일치 케이스"""
        offline_summary = {
            'scan_result': {
                'evaluated_bars': 100,
                'signals_true': 100,
                'long_signals': 50,
                'short_signals': 50,
                'regime_range_signals': 70,  # 70%
                'regime_trend_signals': 30   # 30%
            }
        }
        
        replay_summary = {
            'totals': {
                'strategy_signals_total': 100,
                'strategy_signals_true': 100,
                'long_signals': 50,
                'short_signals': 50,
                'regime_range': 100,  # 100% (모든 신호가 RANGE)
                'regime_trend': 0      # 0%
            }
        }
        
        analysis = analyze_aggregate_diff(offline_summary, replay_summary)
        
        assert analysis['offline']['range_ratio'] == 70.0
        assert analysis['replay']['range_ratio'] == 100.0
        assert analysis['diff']['regime_range_ratio_diff'] == 30.0
        assert analysis['acceptance']['regime_diff_within_10pct'] == False
        assert analysis['acceptance']['overall_pass'] == False
    
    def test_within_tolerance(self):
        """허용 오차 이내 케이스"""
        offline_summary = {
            'scan_result': {
                'evaluated_bars': 100,
                'signals_true': 100,
                'long_signals': 50,
                'short_signals': 50,
                'regime_range_signals': 70,
                'regime_trend_signals': 30
            }
        }
        
        replay_summary = {
            'totals': {
                'strategy_signals_total': 105,  # +5%
                'strategy_signals_true': 108,    # +8%
                'long_signals': 54,
                'short_signals': 54,
                'regime_range': 78,  # 72.2% (차이 +2.2%p)
                'regime_trend': 30
            }
        }
        
        analysis = analyze_aggregate_diff(offline_summary, replay_summary)
        
        assert abs(analysis['diff']['bar_count_diff_pct']) <= 10.0
        assert abs(analysis['diff']['signal_count_diff_pct']) <= 10.0
        assert abs(analysis['diff']['regime_range_ratio_diff']) <= 10.0
        assert analysis['acceptance']['overall_pass'] == True


class TestGenerateSummaryReport:
    """Summary 리포트 생성 테스트"""
    
    def test_report_structure(self):
        """리포트 구조 테스트"""
        offline_summary = {
            'run_id': 'offline_test',
            'scan_result': {
                'evaluated_bars': 100,
                'signals_true': 50,
                'long_signals': 25,
                'short_signals': 25,
                'regime_range_signals': 30,
                'regime_trend_signals': 20
            }
        }
        
        replay_summary = {
            'run_id': 'replay_test',
            'totals': {
                'strategy_signals_total': 100,
                'strategy_signals_true': 50,
                'long_signals': 25,
                'short_signals': 25,
                'regime_range': 30,
                'regime_trend': 20
            }
        }
        
        analysis = analyze_aggregate_diff(offline_summary, replay_summary)
        report = generate_summary_report(analysis, offline_summary, replay_summary)
        
        assert 'metadata' in report
        assert 'aggregate_analysis' in report
        assert 'conclusion' in report
        
        assert report['metadata']['offline_summary_file'] == 'offline_test'
        assert report['metadata']['replay_summary_file'] == 'replay_test'
        
        assert report['conclusion']['overall_status'] in ['PASS', 'FAIL']
        assert 'signal_count_diff_pct' in report['conclusion']
        assert 'regime_diff' in report['conclusion']
        assert 'improvements' in report['conclusion']
        assert len(report['conclusion']['improvements']) > 0


class TestRealDataIntegration:
    """실제 데이터 통합 테스트"""
    
    def test_real_summary_files(self):
        """실제 Summary 파일 테스트 (파일이 있는 경우)"""
        offline_path = PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_4_btc5m_baseline_signal_scan_summary.json'
        replay_path = PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_5_btc5m_engine_replay_summary.json'
        
        if not offline_path.exists() or not replay_path.exists():
            pytest.skip("실제 Summary 파일 없음")
        
        import json
        
        with open(offline_path, 'r', encoding='utf-8') as f:
            offline_summary = json.load(f)
        
        with open(replay_path, 'r', encoding='utf-8') as f:
            replay_summary = json.load(f)
        
        # Aggregate 분석 실행
        analysis = analyze_aggregate_diff(offline_summary, replay_summary)
        
        assert analysis is not None
        assert 'offline' in analysis
        assert 'replay' in analysis
        assert 'diff' in analysis
        assert 'acceptance' in analysis
        
        # 리포트 생성 실행
        report = generate_summary_report(analysis, offline_summary, replay_summary)
        
        assert report is not None
        assert 'metadata' in report
        assert 'conclusion' in report
        
        # 결과 로깅
        print(f"\n실제 데이터 분석 결과:")
        print(f"  - 신호 수 차이: {analysis['diff']['signal_count_diff_pct']:.2f}%")
        print(f"  - Regime 차이: {analysis['diff']['regime_range_ratio_diff']:.2f}%p")
        print(f"  - Overall: {report['conclusion']['overall_status']}")
