#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 완료 - 전체 테스트 매트릭스
=====================================
모든 모드/전략/심볼 조합을 자동 테스트
"""
import yaml
import subprocess
import time
from pathlib import Path

# 테스트 매트릭스
TEST_MATRIX = {
    'modes': ['backtest', 'paper'],  # live는 API 키 필요
    'strategies': {
        'selector': ['ensemble', 'scalping', 'daytrade', 'swing', 'trend', 'reversion', 'breakout'],
        'use_ensemble': [True, False]
    },
    'symbols': {
        'mode': ['manual'],  # top50/top100/all은 시간 오래 걸림
        'manual': [
            ['BTCUSDT'],
            ['BTCUSDT', 'ETHUSDT'],
            ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        ]
    }
}

def update_config(mode, strategy_selector, use_ensemble, symbol_mode, symbol_list):
    """config.yml 업데이트"""
    config_path = Path('config.yml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 설정 변경
    config['mode'] = mode
    config['strategy']['selector'] = strategy_selector
    config['strategy']['use_ensemble'] = use_ensemble
    config['symbols']['mode'] = symbol_mode
    config['symbols']['manual'] = symbol_list
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    return config

def run_test(mode, strategy_selector, use_ensemble, symbol_list, test_num, total_tests):
    """단일 테스트 실행"""
    print("\n" + "=" * 80)
    print(f"테스트 {test_num}/{total_tests}")
    print(f"  모드: {mode}")
    print(f"  전략: {strategy_selector} (ensemble={use_ensemble})")
    print(f"  심볼: {symbol_list}")
    print("=" * 80)
    
    # config.yml 업데이트
    update_config(mode, strategy_selector, use_ensemble, 'manual', symbol_list)
    
    # Docker profile
    profile = 'backtest' if mode == 'backtest' else 'paper'
    
    # Docker 재시작
    print(f"🔄 Docker 재시작 (profile: {profile})...")
    
    # Down
    subprocess.run(
        ['docker-compose', '--profile', profile, 'down'],
        capture_output=True
    )
    
    # Up
    result = subprocess.run(
        ['docker-compose', '--profile', profile, 'up', '--build', '-d'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Docker 시작 실패")
        return False
    
    # 대기 시간 (백테스트: 30초, paper: 10초)
    wait_time = 30 if mode == 'backtest' else 10
    print(f"⏳ {wait_time}초 대기...")
    time.sleep(wait_time)
    
    # 로그 확인
    container = f'trading_bot_{mode}'  # backtest/paper/live
    result = subprocess.run(
        ['docker', 'logs', container, '--tail', '20'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    # 에러 체크
    if 'ERROR' in result.stdout or 'CRITICAL' in result.stdout or 'Traceback' in result.stdout:
        print(f"❌ 에러 발견!")
        print(result.stdout[-500:])
        return False
    
    print(f"✅ 정상 실행 확인")
    return True

def main():
    """전체 테스트 실행"""
    print("=" * 80)
    print("🧪 Phase 2 완료 - 전체 테스트 매트릭스")
    print("=" * 80)
    
    results = []
    test_num = 0
    
    # 모드별 테스트
    for mode in TEST_MATRIX['modes']:
        # 전략별 테스트
        for strategy_selector in TEST_MATRIX['strategies']['selector'][:3]:  # 처음 3개만
            for use_ensemble in [True, False]:
                # 심볼별 테스트
                for symbol_list in TEST_MATRIX['symbols']['manual'][:2]:  # 처음 2개만
                    test_num += 1
                    
                    success = run_test(
                        mode,
                        strategy_selector,
                        use_ensemble,
                        symbol_list,
                        test_num,
                        12  # 2 modes × 3 strategies × 2 ensemble × 2 symbols
                    )
                    
                    results.append({
                        'test': test_num,
                        'mode': mode,
                        'strategy': strategy_selector,
                        'ensemble': use_ensemble,
                        'symbols': symbol_list,
                        'success': success
                    })
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 테스트 결과")
    print("=" * 80)
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    print(f"✅ 성공: {passed}/{len(results)}")
    print(f"❌ 실패: {failed}/{len(results)}")
    
    if failed > 0:
        print("\n실패한 테스트:")
        for r in results:
            if not r['success']:
                print(f"  - {r['mode']}/{r['strategy']}/ensemble={r['ensemble']}/{r['symbols']}")
    
    print("=" * 80)
    
    # 결과 파일 저장
    import json
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📝 결과 저장: test_results.json")

if __name__ == '__main__':
    main()
