#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA 전체 블록 순차 실행
=======================
BACKTEST_PERIODS.md 준수: 6개 블록 모두 실행 후 평균 성과 계산
"""
import sys
import os
import subprocess
import yaml
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# 프로젝트 루트
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# WFA 블록 정보
WFA_BLOCKS = [
    {'name': 'WFA_01', 'regime': 'ETF_APPROVAL', 'train': 'BTCUSDT_5m_WFA_01_TRAIN_ETF_APPROVAL.csv'},
    {'name': 'WFA_02', 'regime': 'HALVING', 'train': 'BTCUSDT_5m_WFA_02_TRAIN_HALVING.csv'},
    {'name': 'WFA_03', 'regime': 'POST_HALVING', 'train': 'BTCUSDT_5m_WFA_03_TRAIN_POST_HALVING.csv'},
    {'name': 'WFA_04', 'regime': 'SUMMER_RANGE', 'train': 'BTCUSDT_5m_WFA_04_TRAIN_SUMMER_RANGE.csv'},
    {'name': 'WFA_05', 'regime': 'Q4_VOLATILITY', 'train': 'BTCUSDT_5m_WFA_05_TRAIN_Q4_VOLATILITY.csv'},
    {'name': 'WFA_06', 'regime': 'YEAR_END', 'train': 'BTCUSDT_5m_WFA_06_TRAIN_YEAR_END.csv'},
]

def run_wfa_block(block_info):
    """단일 WFA 블록 실행"""
    name = block_info['name']
    regime = block_info['regime']
    train_file = block_info['train']
    
    print("="*80)
    print(f"🔄 {name} ({regime})")
    print("="*80)
    
    # config.yml 수정
    config_path = project_root / 'config.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['backtest']['data_file'] = train_file
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✅ config.yml: {train_file}\n")
    
    # DB 초기화
    for db_file in ['backtest.db', 'backtest_results.db']:
        db_path = project_root / db_file
        if db_path.exists():
            db_path.unlink()
    
    # 백테스트 실행
    print(f"🚀 백테스트 시작...\n")
    
    result = subprocess.run(
        [sys.executable, 'main.py'],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print(f"❌ 오류:")
        print(result.stderr)
        return None
    
    # 결과 추출 (stdout에서)
    trades = None
    equity_final = None
    
    for line in result.stdout.split('\n'):
        if '진입 거래:' in line:
            trades = int(line.split(':')[1].split('건')[0].strip())
        if 'Equity:' in line and '->' in line:
            try:
                equity_str = line.split('->')[1].split()[0].strip().replace('$', '').replace(',', '')
                equity_final = float(equity_str)
            except:
                pass
    
    return {
        'block': name,
        'regime': regime,
        'trades': trades,
        'equity_final': equity_final,
    }

def main():
    """WFA 전체 실행"""
    print("="*80)
    print("📊 WFA 전체 블록 실행 (6개)")
    print("="*80)
    print()
    
    results = []
    
    for block in WFA_BLOCKS:
        result = run_wfa_block(block)
        
        if result:
            results.append(result)
            trades_str = f"{result['trades']}건" if result['trades'] else "N/A"
            equity_str = f"${result['equity_final']:,.0f}" if result['equity_final'] else "N/A"
            print(f"\n✅ {result['block']}: {trades_str}, Equity: {equity_str}\n")
        else:
            print(f"\n⚠️ {block['name']} 실패\n")
    
    # 결과 저장
    results_file = project_root / 'reports' / f'wfa_all_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 평균 계산
    if results:
        avg_trades = sum(r['trades'] for r in results if r['trades']) / len(results)
        avg_equity = sum(r['equity_final'] for r in results if r['equity_final']) / len(results)
        
        print("\n" + "="*80)
        print("📊 WFA 전체 평균")
        print("="*80)
        print(f"평균 거래: {avg_trades:.1f}건")
        print(f"평균 Equity: ${avg_equity:,.0f}")
        print(f"평균 ROI: {(avg_equity - 10000) / 10000 * 100:.2f}%")
        print("="*80)
    
    print(f"\n✅ 결과: {results_file.name}")

if __name__ == '__main__':
    main()
