#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA 블록 순차 실행
==================
16개 블록 (2018~2024) 순차 실행 및 결과 집계
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

# WFA 블록 목록 (CSV 파일 기준)
WFA_BLOCKS = [
    # 2018 약세 (4개)
    {'name': '2018_WFA01', 'regime': 'bear_2018', 'file': 'BTCUSDT_15m_2018_WFA01_TRAIN.csv'},
    {'name': '2018_WFA02', 'regime': 'bear_2018', 'file': 'BTCUSDT_15m_2018_WFA02_TRAIN.csv'},
    {'name': '2018_WFA03', 'regime': 'bear_2018', 'file': 'BTCUSDT_15m_2018_WFA03_TRAIN.csv'},
    {'name': '2018_WFA04', 'regime': 'bear_2018', 'file': 'BTCUSDT_15m_2018_WFA04_TRAIN.csv'},
    
    # 2020 코로나 (1개)
    {'name': '2020_WFA01', 'regime': 'covid_2020', 'file': 'BTCUSDT_15m_2020_WFA01_TRAIN.csv'},
    
    # 2020-2021 반감기 강세 (4개)
    {'name': 'bull_WFA01', 'regime': 'halving20_bull', 'file': 'BTCUSDT_15m_bull_WFA01_TRAIN.csv'},
    {'name': 'bull_WFA02', 'regime': 'halving20_bull', 'file': 'BTCUSDT_15m_bull_WFA02_TRAIN.csv'},
    {'name': 'bull_WFA03', 'regime': 'halving20_bull', 'file': 'BTCUSDT_15m_bull_WFA03_TRAIN.csv'},
    {'name': 'bull_WFA04', 'regime': 'halving20_bull', 'file': 'BTCUSDT_15m_bull_WFA04_TRAIN.csv'},
    
    # 2022 루나/FTX (3개)
    {'name': '2022_WFA01', 'regime': 'luna_ftx_2022', 'file': 'BTCUSDT_15m_2022_WFA01_TRAIN.csv'},
    {'name': '2022_WFA02', 'regime': 'luna_ftx_2022', 'file': 'BTCUSDT_15m_2022_WFA02_TRAIN.csv'},
    {'name': '2022_WFA03', 'regime': 'luna_ftx_2022', 'file': 'BTCUSDT_15m_2022_WFA03_TRAIN.csv'},
    
    # 2023-2024 ETF (2개)
    {'name': '24_WFA01', 'regime': 'etf_anticip_24', 'file': 'BTCUSDT_15m_24_WFA01_TRAIN.csv'},
    {'name': '24_WFA02', 'regime': 'etf_anticip_24', 'file': 'BTCUSDT_15m_24_WFA02_TRAIN.csv'},
    
    # 2024 반감기 직후 (2개)
    {'name': 'post_WFA01', 'regime': 'halving24_post', 'file': 'BTCUSDT_15m_post_WFA01_TRAIN.csv'},
    {'name': 'post_WFA02', 'regime': 'halving24_post', 'file': 'BTCUSDT_15m_post_WFA02_TRAIN.csv'},
]


def run_wfa_block(block_info):
    """단일 WFA 블록 실행"""
    name = block_info['name']
    regime = block_info['regime']
    train_file = block_info['file']
    
    print("\n" + "="*70)
    print(f"🔄 {name} ({regime})")
    print("="*70)
    
    # config.yml 수정
    config_path = project_root / 'config.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['backtest']['data_file'] = f'wfa_blocks/{train_file}'
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✅ config.yml: {train_file}")
    
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
    
    if result.returncode != 0:
        print(f"❌ 오류:")
        print(result.stderr)
        return None
    
    # 결과 추출
    trades = None
    equity_final = None
    win_rate = None
    roi = None
    
    for line in result.stdout.split('\n'):
        if '진입 거래:' in line:
            try:
                trades = int(line.split(':')[1].split('건')[0].strip())
            except:
                pass
        if '승률' in line and '%' in line:
            try:
                win_rate = float(line.split('%')[0].split()[-1])
            except:
                pass
        if 'ROI' in line and '%' in line:
            try:
                roi_str = line.split('%')[0].split()[-1].replace(',', '')
                roi = float(roi_str)
            except:
                pass
    
    print(f"\n✅ {name}: {trades}건, 승률 {win_rate}%, ROI {roi}%")
    
    return {
        'block': name,
        'regime': regime,
        'file': train_file,
        'trades': trades,
        'win_rate': win_rate,
        'roi': roi,
    }


def main():
    """WFA 전체 실행"""
    print("\n" + "="*70)
    print("📊 WFA 블록 순차 실행 (16개)")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    start_time = datetime.now()
    
    for i, block in enumerate(WFA_BLOCKS, 1):
        print(f"\n진행: {i}/{len(WFA_BLOCKS)}")
        
        try:
            result = run_wfa_block(block)
            if result:
                results.append(result)
        except Exception as e:
            print(f"\n❌ {block['name']} 실패: {e}")
    
    # 결과 저장
    results_dir = project_root / 'reports' / 'wfa_results'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / f'wfa_all_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 레짐별 평균 계산
    if results:
        df = pd.DataFrame(results)
        
        print("\n" + "="*70)
        print("📊 레짐별 평균 성과")
        print("="*70)
        
        regime_summary = df.groupby('regime').agg({
            'trades': 'mean',
            'win_rate': 'mean',
            'roi': 'mean'
        }).round(1)
        
        print(regime_summary.to_string())
        
        # 전체 평균
        print("\n" + "="*70)
        print("📊 전체 평균")
        print("="*70)
        print(f"평균 거래: {df['trades'].mean():.1f}건")
        print(f"평균 승률: {df['win_rate'].mean():.1f}%")
        print(f"평균 ROI: {df['roi'].mean():.1f}%")
        
        # CSV 저장
        csv_file = results_dir / f'wfa_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(csv_file, index=False)
        print(f"\n✅ 요약: {csv_file.name}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "="*70)
    print("✅ 전체 WFA 블록 실행 완료!")
    print("="*70)
    print(f"완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {duration:.1f}분")
    print(f"결과: {results_file.name}")


if __name__ == '__main__':
    main()
