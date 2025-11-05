#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 심볼 백테스트 실행기
=========================
9개 심볼을 순차적으로 백테스트
"""
import yaml
import subprocess
import time
from pathlib import Path

# 9개 심볼
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

def update_config_symbol(symbol: str):
    """config.yml의 심볼 업데이트"""
    with open('config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['backtest']['symbol'] = symbol
    
    with open('config.yml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✅ config.yml 업데이트: {symbol}")


def run_backtest():
    """백테스트 실행"""
    print("🚀 백테스트 시작...")
    result = subprocess.run(['python', 'main.py'], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 백테스트 완료")
        return True
    else:
        print(f"❌ 백테스트 실패")
        print(result.stderr[-500:] if result.stderr else "")  # 마지막 500자만
        return False


def extract_results():
    """결과 추출"""
    print("📊 결과 추출...")
    result = subprocess.run(['python', 'extract_backtest_result.py'], 
                          capture_output=True, text=True)
    print(result.stdout)


def main():
    print("="*60)
    print("📊 멀티 심볼 백테스트")
    print("="*60)
    print(f"심볼: {len(SYMBOLS)}개")
    print(f"기간: 2025-07-24 ~ 2025-10-22 (3개월)")
    print(f"예상 시간: 약 {len(SYMBOLS) * 3}분")
    print("="*60)
    print()
    
    # 원본 백업
    subprocess.run(['Copy-Item', 'config.yml', 'config_backup_before_multi.yml'], 
                   shell=True)
    
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(SYMBOLS)}] {symbol}")
        print(f"{'='*60}")
        
        # 1. config 업데이트
        update_config_symbol(symbol)
        
        # 2. 백테스트 실행
        if run_backtest():
            success_count += 1
            
            # 3. 결과 추출
            extract_results()
        else:
            fail_count += 1
        
        time.sleep(2)  # 잠시 대기
    
    print("\n" + "="*60)
    print(f"✅ 전체 완료: {success_count}개 성공, {fail_count}개 실패")
    print("="*60)
    print()
    print("📊 결과 확인:")
    print("  - logs/backtest.log - 상세 로그")
    print("  - backtest_results.db - 거래 내역 DB")
    print()
    print("💡 다음 단계:")
    print("  python analyze_multi_symbol_results.py")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
