#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE24-1: DB Schema Inspector
===============================
trading.trades 테이블의 실제 스키마 및 샘플 데이터 조사
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()


def inspect_trades_table():
    """trading.trades 테이블 스키마 및 샘플 데이터 조사"""
    print("=" * 80)
    print("PHASE24-1: DB Schema Inspector - trading.trades")
    print("=" * 80)
    
    try:
        # DB 연결
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5433')),
            database=os.getenv('DB_NAME', 'trading_db'),
            user=os.getenv('DB_USER', 'trading_user'),
            password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
        )
        
        print("\n[OK] DB 연결 성공")
        print(f"  Host: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
        print(f"  Database: {os.getenv('DB_NAME')}")
        
        # 1. 테이블 존재 확인
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'trading' AND table_name = 'trades'
                );
                """
            )
            exists = cur.fetchone()[0]
            
            if not exists:
                print("\n[ERROR] trading.trades 테이블이 존재하지 않습니다.")
                conn.close()
                return
            
            print("\n[OK] trading.trades 테이블 존재 확인")
        
        # 2. 컬럼 정보 조회
        print("\n" + "=" * 80)
        print("테이블 컬럼 정보")
        print("=" * 80)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'trading' AND table_name = 'trades'
                ORDER BY ordinal_position;
                """
            )
            
            columns = cur.fetchall()
            print(f"\n총 {len(columns)}개 컬럼:")
            print("-" * 80)
            print(f"{'컬럼명':<20} {'타입':<25} {'NULL?':<8} {'기본값'}")
            print("-" * 80)
            
            for col in columns:
                print(
                    f"{col['column_name']:<20} "
                    f"{col['data_type']:<25} "
                    f"{col['is_nullable']:<8} "
                    f"{str(col['column_default'])[:30]}"
                )
        
        # 3. 전체 레코드 수
        print("\n" + "=" * 80)
        print("전체 레코드 통계")
        print("=" * 80)
        
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trading.trades;")
            total_count = cur.fetchone()[0]
            print(f"\n전체 trades: {total_count}건")
            
            # mode 컬럼이 있는지 확인
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'trading' AND table_name = 'trades'
                AND column_name = 'mode';
                """
            )
            has_mode = cur.fetchone() is not None
            
            if has_mode:
                # mode별 분포
                cur.execute(
                    """
                    SELECT mode, COUNT(*) as count
                    FROM trading.trades
                    GROUP BY mode
                    ORDER BY count DESC;
                    """
                )
                mode_dist = cur.fetchall()
                print("\nmode별 분포:")
                for row in mode_dist:
                    print(f"  {row[0]}: {row[1]}건")
            else:
                print("\n[INFO] 'mode' 컬럼이 존재하지 않습니다.")
            
            # run_id 컬럼이 있는지 확인
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'trading' AND table_name = 'trades'
                AND column_name = 'run_id';
                """
            )
            has_run_id = cur.fetchone() is not None
            
            if has_run_id:
                # run_id별 분포 (상위 10개)
                cur.execute(
                    """
                    SELECT run_id, COUNT(*) as count
                    FROM trading.trades
                    GROUP BY run_id
                    ORDER BY count DESC
                    LIMIT 10;
                    """
                )
                run_dist = cur.fetchall()
                print("\nrun_id별 분포 (상위 10개):")
                for row in run_dist:
                    print(f"  {row[0]}: {row[1]}건")
            else:
                print("\n[INFO] 'run_id' 컬럼이 존재하지 않습니다.")
            
            # environment 컬럼이 있는지 확인
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'trading' AND table_name = 'trades'
                AND column_name = 'environment';
                """
            )
            has_environment = cur.fetchone() is not None
            
            if has_environment:
                # environment별 분포
                cur.execute(
                    """
                    SELECT environment, COUNT(*) as count
                    FROM trading.trades
                    GROUP BY environment
                    ORDER BY count DESC;
                    """
                )
                env_dist = cur.fetchall()
                print("\nenvironment별 분포:")
                for row in env_dist:
                    print(f"  {row[0]}: {row[1]}건")
            else:
                print("\n[INFO] 'environment' 컬럼이 존재하지 않습니다.")
        
        # 4. 샘플 데이터 (최근 10건)
        print("\n" + "=" * 80)
        print("샘플 데이터 (최근 10건)")
        print("=" * 80)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # id 또는 created_at 또는 ts_open으로 정렬
            # 먼저 어떤 컬럼이 있는지 확인
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'trading' AND table_name = 'trades'
                AND column_name IN ('id', 'created_at', 'ts_open')
                ORDER BY 
                    CASE column_name
                        WHEN 'id' THEN 1
                        WHEN 'created_at' THEN 2
                        WHEN 'ts_open' THEN 3
                    END
                LIMIT 1;
                """
            )
            order_col_row = cur.fetchone()
            order_col = order_col_row[0] if order_col_row else 'trade_id'
            
            cur.execute(f"SELECT * FROM trading.trades ORDER BY {order_col} DESC LIMIT 10;")
            samples = cur.fetchall()
            
            if samples:
                print(f"\n최근 {len(samples)}건 ({order_col} 기준 내림차순):")
                print("-" * 80)
                for i, sample in enumerate(samples, 1):
                    print(f"\n[{i}] trade_id: {sample.get('trade_id', 'N/A')}")
                    # 주요 컬럼만 출력
                    key_cols = ['mode', 'run_id', 'environment', 'symbol', 'side', 'entry_price', 'ts_open']
                    for col in key_cols:
                        if col in sample:
                            print(f"    {col}: {sample[col]}")
            else:
                print("\n[INFO] 샘플 데이터 없음 (테이블이 비어있습니다)")
        
        conn.close()
        print("\n" + "=" * 80)
        print("✅ DB 스키마 조사 완료")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n[ERROR] DB 스키마 조사 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    inspect_trades_table()
