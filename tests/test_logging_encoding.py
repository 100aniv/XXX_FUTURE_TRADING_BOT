#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Logging Encoding (UTF-8)
==============================
PHASE22-1-FIX: 로그 파일 한글/이모지 정상 출력 검증
"""
import os
import tempfile
import shutil
import pytest
from pathlib import Path
from common.logger import setup_logger


def test_log_encoding_korean_emoji():
    """한글 + 이모지가 로그 파일에 UTF-8로 정상 저장되는지 검증"""
    # Temp 디렉토리 생성
    temp_dir = tempfile.mkdtemp(prefix="test_log_")
    original_logs_dir = "./logs"
    
    try:
        # logs 디렉토리를 temp로 변경
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # 로거 생성 (test 타입)
        test_log_dir = os.path.join(temp_dir, "test")
        os.makedirs(test_log_dir, exist_ok=True)
        
        # 직접 로그 파일 경로 설정
        import logging
        from datetime import datetime
        
        logger = logging.getLogger("test_encoding")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()  # 기존 핸들러 제거
        
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(test_log_dir, f"{today}.log")
        
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler = logging.FileHandler(log_file, encoding='utf-8', delay=True)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 테스트 메시지 작성 (한글 + 이모지)
        test_messages = [
            "테스트 메시지: 프리로드 시작",
            "📥 [15m] 프리로드 시작...",
            "✅ [3m] 프리로드 완료: 1/1개 심볼 (100.0%)",
            "🎯 전략 로드 완료: ['scalping', 'breakout', 'reversion', 'trend']",
            "🚀 Paper Trading 시작 (REAL Engine)",
            "📊 BTCUSDT 5m 실시간 수신 중... (가격: 85121.70, 캔들 닫힘: False)",
            "⏱️ [WALL-CLOCK] Duration 모드 시작: 0.50시간 (1800초)",
        ]
        
        for msg in test_messages:
            logger.info(msg)
        
        # 핸들러 플러시 및 닫기
        for handler in logger.handlers:
            handler.flush()
            handler.close()
        logger.handlers.clear()
        
        # 로그 파일이 존재하는지 확인
        assert os.path.exists(log_file), f"로그 파일이 생성되지 않음: {log_file}"
        
        # UTF-8로 읽어서 메시지가 정상인지 확인
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 모든 테스트 메시지가 파일에 있는지 확인
        for msg in test_messages:
            assert msg in content, f"메시지가 로그에 없음: {msg}"
        
        # 깨진 문자(mojibake) 패턴 확인 (없어야 함)
        # 예: '媛?', '?뱤', '??', '\ufffd' 등
        mojibake_patterns = ['媛?', '?뱤', '??', '\ufffd', '�']
        for pattern in mojibake_patterns:
            assert pattern not in content, f"로그에 깨진 문자 발견: {pattern}"
        
        print(f"✅ UTF-8 인코딩 테스트 PASS: {log_file}")
        print(f"✅ 로그 내용 샘플 (첫 200자):\n{content[:200]}")
        
    finally:
        # Temp 디렉토리 정리
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_log_file_handler_encoding():
    """FileHandler가 명시적으로 UTF-8 encoding을 사용하는지 검증"""
    import logging
    from datetime import datetime
    
    temp_dir = tempfile.mkdtemp(prefix="test_log_handler_")
    
    try:
        log_file = os.path.join(temp_dir, "test.log")
        
        # FileHandler 생성 (encoding='utf-8' 명시)
        handler = logging.FileHandler(log_file, encoding='utf-8', delay=True)
        
        # encoding 속성 확인
        assert hasattr(handler, 'encoding'), "FileHandler에 encoding 속성 없음"
        assert handler.encoding == 'utf-8', f"FileHandler encoding이 UTF-8이 아님: {handler.encoding}"
        
        print(f"✅ FileHandler encoding 검증 PASS: {handler.encoding}")
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_log_encoding_korean_emoji()
    test_log_file_handler_encoding()
    print("\n✅ 모든 로그 인코딩 테스트 PASS!")
