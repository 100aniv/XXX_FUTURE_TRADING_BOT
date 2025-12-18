#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER25: DB Introspection Script
==========================================
DB 상태를 정확히 파악하여 "relation 'trades' does not exist" 원인 확정

목표:
- search_path 확인
- trades 테이블 존재 여부 (unqualified vs qualified)
- 스키마별 테이블 목록
- 결과를 artifacts/phase35/iter25/db_introspection.json에 저장
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 PYTHONPATH에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def introspect_db() -> dict:
    """
    DB 상태를 종합적으로 조사
    
    Returns:
        dict: introspection 결과
    """
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "success": False,
        "error": None,
        "introspection": {}
    }
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. current_database
                cur.execute("SELECT current_database();")
                current_db = cur.fetchone()[0]
                result["introspection"]["current_database"] = current_db
                
                # 2. search_path
                cur.execute("SHOW search_path;")
                search_path = cur.fetchone()[0]
                result["introspection"]["search_path"] = search_path
                
                # 3. current_schema
                cur.execute("SELECT current_schema();")
                current_schema = cur.fetchone()[0]
                result["introspection"]["current_schema"] = current_schema
                
                # 4. to_regclass('trades') - unqualified
                cur.execute("SELECT to_regclass('trades') AS trades_unqualified;")
                trades_unqualified = cur.fetchone()[0]
                result["introspection"]["trades_unqualified"] = str(trades_unqualified) if trades_unqualified else None
                
                # 5. to_regclass('trading.trades') - qualified
                cur.execute("SELECT to_regclass('trading.trades') AS trades_trading_schema;")
                trades_qualified = cur.fetchone()[0]
                result["introspection"]["trades_trading_schema"] = str(trades_qualified) if trades_qualified else None
                
                # 6. information_schema.tables (trades 테이블 검색)
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_name = 'trades'
                    ORDER BY table_schema, table_name;
                """)
                trades_tables = [{"schema": row[0], "table": row[1]} for row in cur.fetchall()]
                result["introspection"]["trades_tables_in_schemas"] = trades_tables
                
                # 7. 모든 스키마 목록
                cur.execute("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY schema_name;
                """)
                all_schemas = [row[0] for row in cur.fetchall()]
                result["introspection"]["all_schemas"] = all_schemas
                
                # 8. trading 스키마의 모든 테이블
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'trading'
                    ORDER BY table_name;
                """)
                trading_tables = [row[0] for row in cur.fetchall()]
                result["introspection"]["trading_schema_tables"] = trading_tables
                
                # 9. public 스키마의 모든 테이블
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)
                public_tables = [row[0] for row in cur.fetchall()]
                result["introspection"]["public_schema_tables"] = public_tables
                
                # 10. 실제 trades count 시도 (테이블이 있다면)
                if trades_qualified:
                    try:
                        cur.execute("SELECT COUNT(*) FROM trading.trades;")
                        count = cur.fetchone()[0]
                        result["introspection"]["trading_trades_count"] = count
                    except Exception as e:
                        result["introspection"]["trading_trades_count_error"] = str(e)
                
                result["success"] = True
                
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ DB Introspection 실패: {e}")
    
    return result


def main():
    """Main 실행"""
    logger.info("=" * 80)
    logger.info("🔍 PHASE35-4 ITER25: DB Introspection")
    logger.info("=" * 80)
    
    # Introspection 실행
    result = introspect_db()
    
    # 결과 출력
    logger.info("\n📊 Introspection 결과:")
    logger.info(f"  - Success: {result['success']}")
    if result["error"]:
        logger.error(f"  - Error: {result['error']}")
    
    if result["success"]:
        intro = result["introspection"]
        logger.info(f"  - Current DB: {intro.get('current_database')}")
        logger.info(f"  - Search Path: {intro.get('search_path')}")
        logger.info(f"  - Current Schema: {intro.get('current_schema')}")
        logger.info(f"  - trades (unqualified): {intro.get('trades_unqualified')}")
        logger.info(f"  - trading.trades (qualified): {intro.get('trades_trading_schema')}")
        logger.info(f"  - All Schemas: {intro.get('all_schemas')}")
        logger.info(f"  - trading.* Tables: {intro.get('trading_schema_tables')}")
        logger.info(f"  - public.* Tables: {intro.get('public_schema_tables')}")
        
        if intro.get("trading_trades_count") is not None:
            logger.info(f"  - trading.trades count: {intro.get('trading_trades_count')}")
    
    # JSON 저장
    output_dir = PROJECT_ROOT / "artifacts" / "phase35" / "iter25"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "db_introspection.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✅ 결과 저장: {output_path}")
    
    # 판정
    if not result["success"]:
        logger.error("❌ FAIL: DB 연결 실패")
        sys.exit(1)
    
    intro = result["introspection"]
    if not intro.get("trades_trading_schema"):
        logger.error("❌ FAIL: trading.trades 테이블이 존재하지 않음")
        sys.exit(1)
    
    logger.info("✅ PASS: DB Introspection 완료")


if __name__ == "__main__":
    main()
