#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티 심볼 백테스트
==================
9개 심볼, 3개월 데이터로 전략 테스트
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime

# 9개 심볼 (MATICUSDT 제외)
SYMBOLS = [
    'BTCUSDT',
    'ETHUSDT',
    'BNBUSDT',
    'SOLUSDT',
    'XRPUSDT',
    'ADAUSDT',
    'AVAXUSDT',
    'DOGEUSDT',
    'DOTUSDT',
]

# 데이터 파일 확인
DATA_DIR = Path('data')
START_DATE = '2025-07-24'
END_DATE = '2025-10-22'

def run_backtest_for_symbol(symbol: str):
    """단일 심볼 백테스트 실행"""
    print(f"\n{'='*60}")
    print(f"📊 백테스트: {symbol}")
    print(f"{'='*60}")
    
    # 데이터 파일 확인
    data_file = DATA_DIR / f"{symbol}_5m_{START_DATE}_{END_DATE}.csv"
    if not data_file.exists():
        print(f"❌ 데이터 파일 없음: {data_file}")
        return None
    
    # config.yml 임시 수정 (심볼 변경)
    import yaml
    
    with open('config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 백업
    original_symbol = config['backtest']['symbol']
    
    # 심볼 변경
    config['backtest']['symbol'] = symbol
    
    with open('config.yml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    try:
        # 백테스트 실행
        result = subprocess.run(
            ['python', 'main.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5분 제한
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ 백테스트 실패: {symbol}")
            print(result.stderr)
            return None
        
        # 결과 파일 읽기
        result_file = Path('backtest_results') / 'latest_summary.json'
        if result_file.exists():
            with open(result_file, 'r') as f:
                return json.load(f)
        
        return None
        
    except subprocess.TimeoutExpired:
        print(f"⏰ 타임아웃: {symbol}")
        return None
    
    finally:
        # 원래 설정 복구
        config['backtest']['symbol'] = original_symbol
        with open('config.yml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def main():
    print("="*60)
    print("📊 멀티 심볼 백테스트")
    print("="*60)
    print(f"기간: {START_DATE} ~ {END_DATE} (3개월)")
    print(f"심볼: {len(SYMBOLS)}개")
    print(f"예상 시간: 약 {len(SYMBOLS) * 5}분")
    print("="*60)
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n[{i}/{len(SYMBOLS)}] {symbol}")
        result = run_backtest_for_symbol(symbol)
        if result:
            results[symbol] = result
    
    # 결과 저장
    output_file = Path('backtest_results') / f'multi_symbol_{datetime.now():%Y%m%d_%H%M%S}.json'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print(f"✅ 백테스트 완료: {len(results)}/{len(SYMBOLS)}")
    print(f"결과 파일: {output_file}")
    print("="*60)


if __name__ == '__main__':
    main()
