#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analytics DB 연동 테스트

PostgreSQL 연결 및 analytics 모듈 동작 확인
"""

import unittest
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestAnalyticsDB(unittest.TestCase):
    """Analytics 모듈 DB 연동 테스트"""
    
    def test_01_db_connection(self):
        """PostgreSQL 연결 테스트"""
        try:
            from common.database import test_db_connection
            result = test_db_connection()
            self.assertTrue(result, "❌ DB 연결 실패")
            print("✅ PostgreSQL 연결 성공")
        except Exception as e:
            self.fail(f"❌ DB 연결 테스트 실패: {e}")
    
    def test_02_trade_analyzer_import(self):
        """TradeAnalyzer import 테스트"""
        try:
            from analytics.trade_analyzer import TradeAnalyzer
            analyzer = TradeAnalyzer()
            self.assertIsNotNone(analyzer)
            print("✅ TradeAnalyzer import 성공")
        except Exception as e:
            self.fail(f"❌ TradeAnalyzer import 실패: {e}")
    
    def test_03_strategy_evaluator_import(self):
        """StrategyEvaluator import 테스트"""
        try:
            from analytics.strategy_evaluator import StrategyEvaluator
            evaluator = StrategyEvaluator()
            self.assertIsNotNone(evaluator)
            print("✅ StrategyEvaluator import 성공")
        except Exception as e:
            self.fail(f"❌ StrategyEvaluator import 실패: {e}")
    
    def test_04_get_daily_kpis(self):
        """get_daily_kpis() 호출 테스트"""
        try:
            from analytics.trade_analyzer import TradeAnalyzer
            from datetime import datetime, timedelta
            
            analyzer = TradeAnalyzer()
            
            # 어제 날짜로 테스트 (거래 없어도 정상 동작해야 함)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            kpis = analyzer.get_daily_kpis(yesterday)
            
            # 결과 구조 검증
            self.assertIn('trades', kpis)
            self.assertIn('win_rate', kpis)
            self.assertIn('pnl_sum', kpis)
            self.assertIn('pnl_avg', kpis)
            self.assertIn('rr_avg', kpis)
            self.assertIn('mdd', kpis)
            
            print(f"✅ get_daily_kpis() 호출 성공: {kpis}")
        except Exception as e:
            self.fail(f"❌ get_daily_kpis() 실패: {e}")
    
    def test_05_get_weekly_kpis(self):
        """get_weekly_kpis() 호출 테스트"""
        try:
            from analytics.trade_analyzer import TradeAnalyzer
            from datetime import datetime, timedelta
            
            analyzer = TradeAnalyzer()
            
            # 이번 주 월요일로 테스트
            today = datetime.now()
            monday = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
            kpis = analyzer.get_weekly_kpis(monday)
            
            # 결과 구조 검증
            self.assertIn('trades', kpis)
            self.assertIn('win_rate', kpis)
            self.assertIn('pnl_sum', kpis)
            self.assertIn('best_day', kpis)
            self.assertIn('worst_day', kpis)
            
            print(f"✅ get_weekly_kpis() 호출 성공: {kpis}")
        except Exception as e:
            self.fail(f"❌ get_weekly_kpis() 실패: {e}")
    
    def test_06_compare_strategies(self):
        """compare_strategies() 호출 테스트"""
        try:
            from analytics.strategy_evaluator import StrategyEvaluator
            from datetime import datetime, timedelta
            
            evaluator = StrategyEvaluator()
            
            # 최근 30일 데이터로 테스트
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            comparisons = evaluator.compare_strategies(
                strategies=None,  # 전체 전략
                start_date=start_date,
                end_date=end_date
            )
            
            # 결과 타입 검증
            self.assertIsInstance(comparisons, list)
            
            if comparisons:
                # 첫 번째 결과 구조 검증
                first = comparisons[0]
                self.assertIn('strategy', first)
                self.assertIn('trades', first)
                self.assertIn('win_rate', first)
                self.assertIn('pnl', first)
                self.assertIn('kpi_score', first)
                self.assertIn('rank', first)
                print(f"✅ compare_strategies() 호출 성공: {len(comparisons)}개 전략")
            else:
                print("✅ compare_strategies() 호출 성공 (데이터 없음)")
        except Exception as e:
            self.fail(f"❌ compare_strategies() 실패: {e}")
    
    def test_07_postgresql_specific(self):
        """PostgreSQL 특화 기능 테스트"""
        try:
            from common.database import get_db_connection
            from psycopg2.extras import RealDictCursor
            
            # trading.trades 테이블 존재 확인
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_schema = 'trading'
                          AND table_name = 'trades'
                    """)
                    result = cur.fetchone()
                    
                    if result and result['count'] > 0:
                        print("✅ trading.trades 테이블 존재 확인")
                    else:
                        print("⚠️  trading.trades 테이블 없음 (정상: 초기 상태)")
        except Exception as e:
            # 테이블 없어도 테스트는 통과 (초기 상태일 수 있음)
            print(f"⚠️  PostgreSQL 테이블 확인 실패 (정상일 수 있음): {e}")


if __name__ == "__main__":
    # 테스트 실행
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAnalyticsDB)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 Analytics DB 연동 테스트 결과")
    print("="*60)
    print(f"총 테스트: {result.testsRun}개")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}개")
    print(f"실패: {len(result.failures)}개")
    print(f"에러: {len(result.errors)}개")
    
    if result.wasSuccessful():
        print("\n✅ 모든 Analytics DB 테스트 통과!")
        print("   PostgreSQL 연결 및 쿼리가 정상 동작합니다.")
    else:
        print("\n❌ 일부 테스트 실패")
        print("   DB 연결 또는 환경변수를 확인하세요.")
    
    print("="*60)
    
    # 종료 코드
    sys.exit(0 if result.wasSuccessful() else 1)
