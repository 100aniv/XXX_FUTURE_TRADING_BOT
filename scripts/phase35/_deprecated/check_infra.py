#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35: Infrastructure Check
==============================

Docker/DB/Redis 상태 확인 및 초기화

Usage:
    python scripts/phase35/check_infra.py
"""
import sys
import subprocess
import socket
import time
from pathlib import Path

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("check_infra")


def check_port(host: str, port: int, timeout: int = 2) -> bool:
    """포트 연결 확인"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.warning(f"Port check failed: {host}:{port} - {e}")
        return False


def check_docker_compose() -> bool:
    """Docker Compose 상태 확인"""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            logger.info("✅ Docker Compose: 정상")
            return True
        else:
            logger.warning(f"⚠️  Docker Compose: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Docker Compose 확인 실패: {e}")
        return False


def check_postgres(host: str = "localhost", port: int = 5432) -> bool:
    """PostgreSQL 연결 확인"""
    if not check_port(host, port):
        logger.warning(f"⚠️  PostgreSQL: 포트 {port} 응답 없음")
        return False
    
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            user="postgres",
            password="postgres",
            database="postgres",
            connect_timeout=2
        )
        conn.close()
        logger.info("✅ PostgreSQL: 정상")
        return True
    except Exception as e:
        logger.warning(f"⚠️  PostgreSQL 연결 실패: {e}")
        return False


def check_redis(host: str = "localhost", port: int = 6379) -> bool:
    """Redis 연결 확인"""
    if not check_port(host, port):
        logger.warning(f"⚠️  Redis: 포트 {port} 응답 없음")
        return False
    
    try:
        import redis
        r = redis.Redis(host=host, port=port, socket_connect_timeout=2)
        r.ping()
        logger.info("✅ Redis: 정상")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Redis 연결 실패: {e}")
        return False


def start_docker_compose() -> bool:
    """Docker Compose 시작"""
    try:
        logger.info("🔄 Docker Compose 시작 중...")
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.info("✅ Docker Compose 시작 완료")
            time.sleep(3)  # 서비스 안정화 대기
            return True
        else:
            logger.error(f"❌ Docker Compose 시작 실패: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Docker Compose 시작 중 오류: {e}")
        return False


def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("PHASE35: Infrastructure Check")
    logger.info("=" * 80)
    
    # Docker Compose 확인
    docker_ok = check_docker_compose()
    
    if not docker_ok:
        logger.info("🔄 Docker Compose 시작 시도...")
        docker_ok = start_docker_compose()
    
    # PostgreSQL 확인
    time.sleep(1)
    postgres_ok = check_postgres()
    
    # Redis 확인
    time.sleep(1)
    redis_ok = check_redis()
    
    # 결과 요약
    logger.info("=" * 80)
    logger.info("Infrastructure Status:")
    logger.info(f"  Docker Compose: {'✅ OK' if docker_ok else '❌ FAIL'}")
    logger.info(f"  PostgreSQL:     {'✅ OK' if postgres_ok else '❌ FAIL'}")
    logger.info(f"  Redis:          {'✅ OK' if redis_ok else '❌ FAIL'}")
    logger.info("=" * 80)
    
    # 모두 정상이면 0, 하나라도 실패하면 1
    if docker_ok and postgres_ok and redis_ok:
        logger.info("✅ 모든 인프라 정상")
        return 0
    else:
        logger.warning("⚠️  일부 인프라 문제 감지")
        return 1


if __name__ == "__main__":
    sys.exit(main())
