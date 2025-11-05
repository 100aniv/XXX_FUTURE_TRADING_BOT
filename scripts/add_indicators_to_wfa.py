#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA 블록에 지표 추가
===================
RSI, MACD, BB, EMA, ATR, Volume MA
"""
import sys
import pandas as pd
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators import add_indicators


def process_wfa_file(filepath: Path):
    """WFA 파일 처리"""
    # 로드
    df = pd.read_csv(filepath)
    
    # time 컬럼 확인
    if 'time' not in df.columns:
        df.rename(columns={'timestamp': 'time'}, inplace=True)
    
    df['time'] = pd.to_datetime(df['time'])
    
    # 지표 추가 (기존 모듈)
    df = add_indicators(df)
    
    # 저장
    df.to_csv(filepath, index=False)
    
    return len(df)


def main():
    """전체 WFA 블록 처리"""
    wfa_dir = project_root / 'data' / 'wfa_blocks'
    
    # Train 파일만 (OOS는 나중에)
    files = list(wfa_dir.glob('BTCUSDT_15m_*_TRAIN.csv'))
    
    print("\n" + "="*70)
    print("📊 WFA 블록 지표 추가")
    print("="*70)
    print(f"파일: {len(files)}개")
    print("="*70)
    
    for i, filepath in enumerate(files, 1):
        try:
            print(f"\n[{i}/{len(files)}] 처리 중: {filepath.name}")
            count = process_wfa_file(filepath)
            print(f"  ✅ {count:,}개 캔들")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    
    print("\n" + "="*70)
    print("✅ 지표 추가 완료!")
    print("="*70)
    print(f"\n다음 단계:")
    print(f"  1. config.yml 타임프레임 변경 (5m → 15m)")
    print(f"  2. 첫 번째 WFA 블록 백테스트")


if __name__ == '__main__':
    main()
