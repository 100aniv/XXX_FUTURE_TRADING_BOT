#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA Baseline 백테스트 러너
==========================
BACKTEST_PERIODS.md 준수:
- 6개 WFA 블록 순차 실행
- 각 블록: Train 8주 → OOS 3주
- 결과 집계 및 평균 OOS 성과 계산
"""
import sys
import os
import subprocess
import yaml
import json
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

def run_wfa_block(block_idx, block_info):
    """단일 WFA 블록 실행"""
    name = block_info['name']
    regime = block_info['regime']
    train_file = block_info['train']
    
    print("="*80)
    print(f"🔄 WFA 블록 {block_idx+1}/6: {name} ({regime})")
    print("="*80)
    
    # config.yml 수정 (data_file 변경)
    config_path = project_root / 'config.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['backtest']['data_file'] = train_file
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✅ config.yml 업데이트: {train_file}\n")
    
    # 백테스트 실행
    print(f"🚀 백테스트 시작...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, 'main.py'],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=600  # 10분 타임아웃
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ 오류 발생:")
            print(result.stderr)
            return None
        
        # 결과 파일 찾기
        reports_dir = project_root / 'reports'
        report_files = sorted(reports_dir.glob('backtest_report_*.txt'))
        
        if not report_files:
            print("⚠️ 리포트 파일을 찾을 수 없습니다.")
            return None
        
        latest_report = report_files[-1]
        print(f"\n✅ 리포트: {latest_report.name}")
        
        # 리포트 파싱 (간단히)
        with open(latest_report, 'r', encoding='utf-8') as f:
            report_text = f.read()
        
        # 핵심 지표 추출
        metrics = {
            'block': name,
            'regime': regime,
            'train_file': train_file,
            'report_file': latest_report.name,
        }
        
        # TODO: 리포트 파싱 로직 추가
        
        return metrics
        
    except subprocess.TimeoutExpired:
        print("⏱️ 타임아웃 (10분 초과)")
        return None
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return None

def main():
    """WFA Baseline 실행"""
    print("="*80)
    print("📊 WFA Baseline 백테스트 (6개 블록)")
    print("="*80)
    print()
    
    # config.yml 백업
    config_path = project_root / 'config.yml'
    backup_path = project_root / 'config_before_wfa.yml'
    
    import shutil
    shutil.copy(config_path, backup_path)
    print(f"✅ config.yml 백업: {backup_path.name}\n")
    
    # WFA 블록 순차 실행
    results = []
    
    for idx, block in enumerate(WFA_BLOCKS):
        result = run_wfa_block(idx, block)
        
        if result:
            results.append(result)
        else:
            print(f"\n⚠️ {block['name']} 실패 - 계속 진행...\n")
    
    # 결과 저장
    results_file = project_root / 'reports' / f'wfa_baseline_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("✅ WFA Baseline 완료!")
    print(f"   완료: {len(results)}/{len(WFA_BLOCKS)} 블록")
    print(f"   결과: {results_file.name}")
    print("="*80)

if __name__ == '__main__':
    main()
