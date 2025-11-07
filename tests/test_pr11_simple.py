#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR11 Risk Guards Simple Tests
=============================
RiskManager 강화 가드들의 간단한 테스트

테스트 대상:
- Drawdown Guard
- Slippage Guard  
- Extreme Loss Guard
- Paper/Live 파리티
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.risk_manager import RiskManager


def test_pr11_guards():
    """PR11 가드 기본 동작 테스트"""
    print("🧪 PR11 Risk Guards 테스트 시작...")
    
    # 테스트용 config
    config = {
        'mode': 'paper',
        'capital': {'initial': 10000},
        'risk': {
            'max_positions': 5,
            'max_exposure_per_symbol': 0.15,
            'max_drawdown_pct': 10.0,  # 10%
            'max_slippage_pct': 0.5,   # 0.5%
            'extreme_loss_cutoff_pct': -30.0,  # -30%
        }
    }
    
    risk_manager = RiskManager(config)
    
    # 1. Drawdown Guard 테스트
    print("\n1️⃣ Drawdown Guard 테스트")
    
    # 정상 범위 (5% 손실)
    result = risk_manager.check_drawdown_guard(9500)
    print(f"   ✅ 5% 손실: {result} (통과 예상)")
    assert result is True
    
    # 임계값 초과 (15% 손실 > 10% 임계값)
    risk_manager.peak_equity = 10000  # 리셋
    result = risk_manager.check_drawdown_guard(8500)
    print(f"   ❌ 15% 손실: {result} (차단 예상)")
    assert result is False
    
    # 2. Slippage Guard 테스트
    print("\n2️⃣ Slippage Guard 테스트")
    
    # 정상 범위 (0.3% 슬리피지)
    result = risk_manager.check_slippage_guard(100.0, 100.3)
    print(f"   ✅ 0.3% 슬리피지: {result} (통과 예상)")
    assert result is True
    
    # 임계값 초과 (1.0% 슬리피지 > 0.5% 임계값)
    result = risk_manager.check_slippage_guard(100.0, 101.0)
    print(f"   ❌ 1.0% 슬리피지: {result} (차단 예상)")
    assert result is False
    
    # 3. Extreme Loss Guard 테스트
    print("\n3️⃣ Extreme Loss Guard 테스트")
    
    # 정상 범위 (-20% 손실)
    result = risk_manager.check_extreme_loss_guard(-0.2)
    print(f"   ✅ -20% 손실: {result} (통과 예상)")
    assert result is True
    
    # 임계값 초과 (-35% 손실 < -30% 임계값)
    result = risk_manager.check_extreme_loss_guard(-0.35)
    print(f"   ❌ -35% 손실: {result} (차단 예상)")
    assert result is False
    
    # 4. Paper/Live 파리티 테스트
    print("\n4️⃣ Paper/Live 파리티 테스트")
    
    # Live 모드 config
    live_config = config.copy()
    live_config['mode'] = 'live'
    live_risk = RiskManager(live_config)
    
    # 동일 입력에 대해 동일 결과 (가드 로직 파리티)
    paper_dd = risk_manager.check_drawdown_guard(8500)
    live_dd = live_risk.check_drawdown_guard(8500)
    print(f"   🔄 Drawdown 파리티: Paper={paper_dd}, Live={live_dd}")
    assert paper_dd == live_dd
    
    paper_slip = risk_manager.check_slippage_guard(100.0, 101.0)
    live_slip = live_risk.check_slippage_guard(100.0, 101.0)
    print(f"   🔄 Slippage 파리티: Paper={paper_slip}, Live={live_slip}")
    assert paper_slip == live_slip
    
    paper_loss = risk_manager.check_extreme_loss_guard(-0.35)
    live_loss = live_risk.check_extreme_loss_guard(-0.35)
    print(f"   🔄 Extreme Loss 파리티: Paper={paper_loss}, Live={live_loss}")
    assert paper_loss == live_loss
    
    print("\n✅ 모든 테스트 통과!")
    return True


def test_config_validation():
    """Config 검증 테스트"""
    print("\n🔧 Config 검증 테스트...")
    
    # 최소 config (기본값 적용 확인)
    minimal_config = {
        'mode': 'paper',
        'capital': {'initial': 10000},
        'risk': {
            'max_positions': 5,
            'max_exposure_per_symbol': 0.15
        }
    }
    
    risk_manager = RiskManager(minimal_config)
    
    # 기본값 적용 확인
    assert risk_manager.max_drawdown_pct == 0.1  # 10%
    assert risk_manager.max_slippage_pct == 0.005  # 0.5%
    assert risk_manager.extreme_loss_cutoff_pct == -0.3  # -30%
    
    print("   ✅ 기본값 적용 확인")
    return True


def test_guard_integration():
    """가드 통합 테스트"""
    print("\n🔗 가드 통합 테스트...")
    
    config = {
        'mode': 'paper',
        'capital': {'initial': 10000},
        'risk': {
            'max_positions': 5,
            'max_exposure_per_symbol': 0.15,
            'max_drawdown_pct': 10.0,
            'max_slippage_pct': 0.5,
            'extreme_loss_cutoff_pct': -30.0,
        }
    }
    
    risk_manager = RiskManager(config)
    
    # 독립성 테스트: 하나의 가드 실패가 다른 가드에 영향 없음
    risk_manager.peak_equity = 10000
    dd_result = risk_manager.check_drawdown_guard(8000)  # DD 실패
    slip_result = risk_manager.check_slippage_guard(100.0, 100.2)  # Slippage 성공
    
    assert dd_result is False
    assert slip_result is True
    print("   ✅ 가드 독립성 확인")
    
    # 멱등성 테스트: 동일 입력에 동일 결과
    result1 = risk_manager.check_slippage_guard(100.0, 100.3)
    result2 = risk_manager.check_slippage_guard(100.0, 100.3)
    assert result1 == result2
    print("   ✅ 가드 멱등성 확인")
    
    return True


if __name__ == "__main__":
    try:
        print("🎯 PR11 Phase 3 프로퍼티 테스트 실행")
        print("=" * 50)
        
        # 기본 가드 테스트
        test_pr11_guards()
        
        # Config 검증 테스트
        test_config_validation()
        
        # 가드 통합 테스트
        test_guard_integration()
        
        print("\n" + "=" * 50)
        print("🎉 PR11 Phase 3 테스트 완료!")
        print("📊 테스트 결과:")
        print("   - Drawdown Guard: ✅ 정상")
        print("   - Slippage Guard: ✅ 정상")
        print("   - Extreme Loss Guard: ✅ 정상")
        print("   - Paper/Live 파리티: ✅ 정상")
        print("   - Config 검증: ✅ 정상")
        print("   - 가드 통합: ✅ 정상")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
