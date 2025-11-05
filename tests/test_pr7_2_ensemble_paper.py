#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR7-2: 앙상블 Paper 검증 테스트

monitoring.signals 및 trading.decisions 저장 확인
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.postgres import get_db_connection


def test_signals_table():
    """monitoring.signals 테이블 확인"""
    print("\n=== monitoring.signals 테이블 확인 ===")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 최근 신호 조회
                cur.execute("""
                    SELECT strategy_id, symbol, timeframe, direction, 
                           candle_closed_at, confidence
                    FROM monitoring.signals
                    ORDER BY candle_closed_at DESC
                    LIMIT 10
                """)
                rows = cur.fetchall()
                
                if rows:
                    print(f"✅ 최근 신호 {len(rows)}개 발견:")
                    for row in rows:
                        print(f"  - {row[0]} {row[1]} {row[2]} {row[3]} @ {row[4]}")
                else:
                    print("⚠️  신호 없음 (Paper 모드 실행 필요)")
                
                # 전략별 신호 개수
                cur.execute("""
                    SELECT strategy_id, COUNT(*) as cnt
                    FROM monitoring.signals
                    WHERE candle_closed_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY strategy_id
                    ORDER BY cnt DESC
                """)
                rows = cur.fetchall()
                
                if rows:
                    print(f"\n✅ 24시간 전략별 신호:")
                    for row in rows:
                        print(f"  - {row[0]}: {row[1]}개")
                else:
                    print("\n⚠️  24시간 신호 없음")
                
                return True
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_decisions_table():
    """trading.decisions 테이블 확인"""
    print("\n=== trading.decisions 테이블 확인 ===")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 최근 결정 조회
                cur.execute("""
                    SELECT symbol, timeframe, chosen_side, score,
                           weights, from_signals, reason, candle_closed_at
                    FROM trading.decisions
                    ORDER BY candle_closed_at DESC
                    LIMIT 10
                """)
                rows = cur.fetchall()
                
                if rows:
                    print(f"✅ 최근 결정 {len(rows)}개 발견:")
                    for row in rows:
                        print(f"  - {row[0]} {row[1]} {row[2]} (score: {row[3]}) @ {row[7]}")
                        print(f"    weights: {row[4]}")
                        print(f"    from: {row[5]}")
                        print(f"    reason: {row[6]}")
                else:
                    print("⚠️  결정 없음 (앙상블 Paper 모드 실행 필요)")
                
                # 24시간 결정 개수
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM trading.decisions
                    WHERE candle_closed_at >= NOW() - INTERVAL '24 hours'
                """)
                row = cur.fetchone()
                
                if row and row[0] > 0:
                    print(f"\n✅ 24시간 결정: {row[0]}개")
                else:
                    print("\n⚠️  24시간 결정 없음")
                
                return True
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_pr7_2_acceptance():
    """PR7-2 수용 기준 확인"""
    print("\n=== PR7-2 수용 기준 확인 (24h) ===")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. 6개 전략 모두 신호 ≥1건
                cur.execute("""
                    SELECT strategy_id, COUNT(*) as cnt
                    FROM monitoring.signals
                    WHERE candle_closed_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY strategy_id
                """)
                signal_rows = cur.fetchall()
                signal_dict = {row[0]: row[1] for row in signal_rows}
                
                required_strategies = ['scalping', 'daytrade', 'swing', 'trend', 'reversion', 'breakout']
                signals_ok = all(signal_dict.get(s, 0) >= 1 for s in required_strategies)
                
                if signals_ok:
                    print("✅ 6개 전략 모두 신호 ≥1건")
                    for s in required_strategies:
                        print(f"  - {s}: {signal_dict.get(s, 0)}개")
                else:
                    print("❌ 일부 전략 신호 없음:")
                    for s in required_strategies:
                        cnt = signal_dict.get(s, 0)
                        status = "✅" if cnt >= 1 else "❌"
                        print(f"  {status} {s}: {cnt}개")
                
                # 2. trading.decisions ≥1건
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM trading.decisions
                    WHERE candle_closed_at >= NOW() - INTERVAL '24 hours'
                """)
                decision_count = cur.fetchone()[0]
                
                if decision_count >= 1:
                    print(f"\n✅ trading.decisions ≥1건 ({decision_count}개)")
                else:
                    print(f"\n❌ trading.decisions 없음 (0개)")
                
                # 3. 종합 판정
                all_ok = signals_ok and decision_count >= 1
                
                if all_ok:
                    print("\n🎉 PR7-2 수용 기준 통과!")
                else:
                    print("\n⚠️  PR7-2 수용 기준 미달 (Paper 모드 24h 실행 필요)")
                
                return all_ok
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PR7-2: 앙상블 Paper 검증")
    print("=" * 60)
    
    # 테이블 확인
    test_signals_table()
    test_decisions_table()
    
    # 수용 기준 확인
    test_pr7_2_acceptance()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
