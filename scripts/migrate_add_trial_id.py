#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 마이그레이션: trial_id 컬럼 추가
===========================================
실행: python scripts/migrate_add_trial_id.py
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from common.database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """trial_id 컬럼 추가 마이그레이션 실행"""
    migration_file = project_root / 'db' / 'migrations' / 'add_trial_id_column.sql'
    
    if not migration_file.exists():
        logger.error(f"❌ 마이그레이션 파일 없음: {migration_file}")
        return False
    
    logger.info("=" * 80)
    logger.info("🚀 PostgreSQL 마이그레이션 시작: trial_id 컬럼 추가")
    logger.info("=" * 80)
    
    try:
        # SQL 파일 읽기
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # PostgreSQL 연결
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 마이그레이션 실행
                logger.info("📝 SQL 실행 중...")
                cur.execute(sql)
                
                # 결과 확인
                cur.execute("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns 
                    WHERE table_schema = 'trading' 
                      AND table_name = 'trades' 
                      AND column_name = 'trial_id'
                """)
                result = cur.fetchone()
                
                if result:
                    logger.info("✅ trial_id 컬럼 추가 완료")
                    logger.info(f"   - 타입: {result[1]}")
                    logger.info(f"   - 길이: {result[2]}")
                    logger.info(f"   - NULL 허용: {result[3]}")
                else:
                    logger.error("❌ trial_id 컬럼 확인 실패")
                    return False
                
                # 인덱스 확인
                cur.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'trading'
                      AND tablename = 'trades'
                      AND indexname LIKE '%trial%'
                """)
                indexes = cur.fetchall()
                
                if indexes:
                    logger.info(f"✅ 인덱스 생성 완료 ({len(indexes)}개)")
                    for idx in indexes:
                        logger.info(f"   - {idx[0]}")
                else:
                    logger.warning("⚠️  인덱스 없음")
        
        logger.info("=" * 80)
        logger.info("✅ 마이그레이션 완료")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
