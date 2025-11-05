#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA 결과 분석
=============
backtest.db에서 결과 읽어서 분석
"""
import sys
import sqlite3
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# WFA 블록 정보
WFA_BLOCKS = [
    # 2018 약세 (4개)
    {'name': '2018_WFA01', 'regime': 'bear_2018', 'desc': '2018 약세장'},
    {'name': '2018_WFA02', 'regime': 'bear_2018', 'desc': '2018 약세장'},
    {'name': '2018_WFA03', 'regime': 'bear_2018', 'desc': '2018 약세장'},
    {'name': '2018_WFA04', 'regime': 'bear_2018', 'desc': '2018 약세장'},
    
    # 2020 코로나 (1개)
    {'name': '2020_WFA01', 'regime': 'covid_2020', 'desc': '2020 코로나'},
    
    # 2020-2021 반감기 강세 (4개)
    {'name': 'bull_WFA01', 'regime': 'halving20_bull', 'desc': '2020-2021 반감기 강세'},
    {'name': 'bull_WFA02', 'regime': 'halving20_bull', 'desc': '2020-2021 반감기 강세'},
    {'name': 'bull_WFA03', 'regime': 'halving20_bull', 'desc': '2020-2021 반감기 강세'},
    {'name': 'bull_WFA04', 'regime': 'halving20_bull', 'desc': '2020-2021 반감기 강세'},
    
    # 2022 루나/FTX (3개)
    {'name': '2022_WFA01', 'regime': 'luna_ftx_2022', 'desc': '2022 루나/FTX'},
    {'name': '2022_WFA02', 'regime': 'luna_ftx_2022', 'desc': '2022 루나/FTX'},
    {'name': '2022_WFA03', 'regime': 'luna_ftx_2022', 'desc': '2022 루나/FTX'},
    
    # 2023-2024 ETF (2개)
    {'name': '24_WFA01', 'regime': 'etf_anticip_24', 'desc': '2023-2024 ETF'},
    {'name': '24_WFA02', 'regime': 'etf_anticip_24', 'desc': '2023-2024 ETF'},
    
    # 2024 반감기 직후 (2개)
    {'name': 'post_WFA01', 'regime': 'halving24_post', 'desc': '2024 반감기 직후'},
    {'name': 'post_WFA02', 'regime': 'halving24_post', 'desc': '2024 반감기 직후'},
]


def analyze_db(db_path: Path):
    """DB에서 결과 분석"""
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(db_path)
    
    try:
        # 거래 수
        cursor = conn.execute("SELECT COUNT(*) FROM trades")
        trades = cursor.fetchone()[0]
        
        # 승률
        cursor = conn.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
        wins = cursor.fetchone()[0]
        win_rate = (wins / trades * 100) if trades > 0 else 0
        
        # ROI
        cursor = conn.execute("SELECT SUM(pnl) FROM trades")
        total_pnl = cursor.fetchone()[0] or 0
        roi = (total_pnl / 10000 * 100)  # 초기 자본 $10,000
        
        return {
            'trades': trades,
            'wins': wins,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2),
            'roi': round(roi, 1),
        }
    finally:
        conn.close()


def main():
    """각 블록별 DB 분석"""
    print("\n" + "="*70)
    print("📊 WFA 결과 분석 (DB 기반)")
    print("="*70)
    
    # 현재는 마지막 실행된 post_WFA02만 있음
    # 각 블록마다 DB를 저장해야 함
    
    db_path = project_root / 'backtest.db'
    
    if not db_path.exists():
        print("❌ backtest.db 없음")
        return
    
    result = analyze_db(db_path)
    
    if result:
        print(f"\n마지막 블록 (post_WFA02) 결과:")
        print(f"  거래: {result['trades']}건")
        print(f"  승률: {result['win_rate']}%")
        print(f"  ROI: {result['roi']}%")
        print(f"  총 PnL: ${result['total_pnl']:,.2f}")
    
    print("\n" + "="*70)
    print("⚠️  전체 결과 분석을 위해서는")
    print("   각 블록 실행 후 DB를 별도 저장해야 함")
    print("="*70)


if __name__ == '__main__':
    main()
