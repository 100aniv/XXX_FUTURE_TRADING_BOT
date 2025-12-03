#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 로깅 모듈 (개선판)
=======================
실무 표준 로깅 구조:
- 타입별 분류: signals, trading, errors, application
- 일자별 로테이션: YYYY-MM-DD.log
- 자동 정리: 30일 이상 로그 삭제

PHASE26-3 추가:
- TRACE 레벨 추가 (DEBUG보다 낮음, 개발용)
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
import glob

# ============================================
# PHASE26-3: TRACE 레벨 추가
# ============================================
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kwargs):
    """
    TRACE 레벨 로그 (DEBUG보다 낮음)
    
    Usage:
        logger.trace("상세 디버그 메시지")
    """
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


# Logger 클래스에 trace 메서드 추가
logging.Logger.trace = trace


def cleanup_old_logs(log_dir: str, days: int = 30):
    """
    오래된 로그 파일 정리
    
    Args:
        log_dir: 로그 디렉토리
        days: 보관 기간 (일)
    """
    cutoff = datetime.now() - timedelta(days=days)
    
    for log_file in glob.glob(f"{log_dir}/**/*.log", recursive=True):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            if mtime < cutoff:
                os.remove(log_file)
                # Unicode 인코딩 오류 방지
                try:
                    print(f"오래된 로그 삭제: {log_file}")
                except:
                    pass
        except Exception as e:
            # Unicode 인코딩 오류 방지
            try:
                print(f"로그 삭제 실패: {log_file} - {e}")
            except:
                pass


def setup_logger(name: str, log_type: str = "application", level=logging.INFO):
    """
    타입별 + 일자별 로거 설정
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
        log_type: 로그 타입 (application, signals, trading, errors, performance)
        level: 로그 레벨
    
    Returns:
        logger: 설정된 로거
        
    Examples:
        >>> # 신호 봇
        >>> logger = setup_logger(__name__, log_type="signals")
        >>> 
        >>> # 거래 봇
        >>> logger = setup_logger(__name__, log_type="trading")
        >>> 
        >>> # 백테스트
        >>> logger = setup_logger(__name__, log_type="performance")
    """
    # 로그 디렉토리 구조
    base_dir = "./logs"
    log_dir = os.path.join(base_dir, log_type)
    os.makedirs(log_dir, exist_ok=True)
    
    # 오래된 로그 정리 (매번 호출 시 체크)
    cleanup_old_logs(base_dir, days=30)
    
    # 로거 생성 (이미 존재하면 재사용)
    logger = logging.getLogger(name)
    
    # 핸들러가 이미 있으면 추가 안함 (중복 방지)
    if logger.handlers:
        return logger  # ⭐ 로그 설정 완료 메시지 출력 안함 (중복 방지)
    
    logger.setLevel(level)
    
    # 포맷터 (telegram_signal_bot.py 양식 유지)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    
    # 1. 콘솔 핸들러 (실시간 확인)
    # PHASE22-1-FIX: 콘솔도 UTF-8 인코딩 명시 (Windows 환경 대응)
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    # StreamHandler는 encoding을 직접 설정할 수 없으므로 sys.stdout이 UTF-8인지 확인
    # Python 3.7+ 에서는 sys.stdout.reconfigure(encoding='utf-8') 가능하지만,
    # 이미 초기화된 stdout을 변경하는 것은 권장되지 않으므로 그대로 유지
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 2. 날짜별 파일 핸들러 (logs/{log_type}/{today}.log)
    # PHASE22-1: delay=True 추가 (PermissionError 방지)
    today = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{today}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8', delay=True)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 3. 에러만 별도 저장
    # PHASE22-1: delay=True 추가 (PermissionError 방지)
    if level <= logging.ERROR:
        error_dir = os.path.join(base_dir, "errors")
        os.makedirs(error_dir, exist_ok=True)
        error_log_file = os.path.join(error_dir, f"{today}.log")
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8', delay=True)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    # 4. 전체 통합 로그 (application.log, 최근 7일 로테이션)
    # PHASE22-1: delay=True 추가로 파일 열림 시점을 실제 기록 순간으로 미룸 (PermissionError 방지)
    app_log_file = os.path.join(base_dir, "application.log")
    app_handler = TimedRotatingFileHandler(
        app_log_file, 
        when='midnight', 
        interval=1, 
        backupCount=7,
        encoding='utf-8',
        delay=True
    )
    app_handler.setFormatter(formatter)
    logger.addHandler(app_handler)
    
    # ⭐ 로그 설정 완료 메시지 제거 (중복 출력 방지)
    # logger.info(f"📝 로그 설정 완료: {log_type}/{today}.log")
    
    return logger


# 전역 로거 (backward compatibility)
logger = setup_logger(__name__)
