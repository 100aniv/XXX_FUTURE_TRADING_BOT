#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy Files Cleanup
====================
레거시 파일들을 _archived/로 이동
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
ARCHIVED = ROOT / "_archived"

# 이동할 파일 목록
FILES_TO_MOVE = [
    # 옛날 Bot 파일들
    "ensemble_bot.py",
    "signal_bot_breakout.py",
    "signal_bot_reversion.py",
    "signal_bot_trend.py",
    "telegram_signal_bot.py",
    
    # 옛날 Config 파일들
    "config_breakout.txt",
    "config_intraday.txt",
    "config_reversion.txt",
    "config_scalp.txt",
    "config_swing.txt",
    "config_trend.txt",
    "env_presets.txt",
    
    # 옛날 .env 파일들
    ".env.breakout",
    ".env.intraday",
    ".env.reversion",
    ".env.scalp",
    ".env.swing",
    ".env.trend",
    ".env.backup",
    
    # 옛날 .bat 파일들
    "start_3bots.bat",
    "start_4bots.bat",
    "start_bot.bat",
    "setup_env.bat",
    
    # 옛날 테스트 파일들
    "test_collector_quick.py",
    "test_collector_websocket.py",
    "test_import_all.py",
    "test_signals_module.py",
    
    # 임시 MD 파일들
    "FILE_COMPARISON_REPORT.md",
    "PHASE7_COLLECTOR_COMPLETE.md",
    
    # 임시 스크립트
    "create_signals_table.py",
    "init_database.py",
]

def main():
    """파일 이동 실행"""
    print("="*60)
    print("레거시 파일 정리 시작")
    print("="*60)
    
    # _archived 폴더 확인
    ARCHIVED.mkdir(exist_ok=True)
    
    moved_count = 0
    skipped_count = 0
    
    for filename in FILES_TO_MOVE:
        src = ROOT / filename
        
        if not src.exists():
            skipped_count += 1
            continue
        
        dst = ARCHIVED / filename
        
        try:
            # 대상 파일이 이미 있으면 덮어쓰기
            if dst.exists():
                dst.unlink()
            
            shutil.move(str(src), str(dst))
            print(f"✅ {filename} → _archived/")
            moved_count += 1
            
        except Exception as e:
            print(f"❌ {filename} 이동 실패: {e}")
    
    print("\n" + "="*60)
    print(f"✅ 완료: {moved_count}개 이동, {skipped_count}개 없음")
    print("="*60)

if __name__ == "__main__":
    main()
