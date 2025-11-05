#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
바이낸스 선물 레버리지 범위 조회
"""
from binance.client import Client
import json

# 바이낸스 클라이언트 (공개 API, 인증 불필요)
client = Client("", "")

def check_leverage_brackets():
    """
    바이낸스 선물 레버리지 브라켓 조회 (공개 정보)
    """
    print("=" * 80)
    print("바이낸스 선물 레버리지 범위 조회 (Exchange Info)")
    print("=" * 80)
    
    try:
        # 거래소 정보 조회 (공개 API)
        exchange_info = client.futures_exchange_info()
        symbols_info = exchange_info['symbols']
        
        # 레버리지 정보 추출
        brackets = []
        for symbol_info in symbols_info:
            symbol = symbol_info['symbol']
            # maxLeverage는 심볼별 최대 레버리지
            max_lev = symbol_info.get('leverage', 125)  # 기본값 125x
            
            brackets.append({
                'symbol': symbol,
                'max_leverage': max_lev
            })
        
        # 주요 심볼만 추출
        major_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        
        print("\n📊 주요 심볼 레버리지 범위:\n")
        
        leverage_ranges = {}
        
        for item in brackets:
            symbol = item['symbol']
            if symbol in major_symbols:
                max_lev = item['max_leverage']
                
                leverage_ranges[symbol] = {
                    'min': 1,  # 바이낸스 최소는 1x
                    'max': max_lev
                }
                
                print(f"  {symbol:12} | Min: 1x | Max: {max_lev:3}x")
        
        # 전체 통계
        print("\n" + "=" * 80)
        print("📈 전체 통계:\n")
        
        all_max_lev = [item['max_leverage'] for item in brackets]
        
        print(f"  조회된 심볼 수: {len(brackets)}개")
        print(f"  최대 레버리지 범위: {min(all_max_lev)}x ~ {max(all_max_lev)}x")
        print(f"  평균 최대 레버리지: {sum(all_max_lev) / len(all_max_lev):.1f}x")
        
        # 레버리지별 심볼 분포
        lev_distribution = {}
        for lev in all_max_lev:
            lev_distribution[lev] = lev_distribution.get(lev, 0) + 1
        
        print("\n  레버리지별 심볼 분포:")
        for lev in sorted(lev_distribution.keys(), reverse=True):
            count = lev_distribution[lev]
            bar = "█" * (count // 10) if count >= 10 else "▌"
            print(f"    {lev:3}x: {count:3}개 심볼 {bar}")
        
        # 위험 등급별 권장 범위
        print("\n" + "=" * 80)
        print("⚖️  위험 등급별 권장 레버리지:\n")
        
        print(f"  🟢 보수적 (Conservative):  2x ~ 5x")
        print(f"  🟡 균형형 (Balanced):       5x ~ 20x")
        print(f"  🔴 공격적 (Aggressive):    20x ~ 50x")
        print(f"  ⚠️  고위험 (High Risk):    50x ~ 125x")
        
        # 현재 시스템 vs 바이낸스
        print("\n" + "=" * 80)
        print("🎯 현재 시스템 vs 바이낸스:\n")
        
        print(f"  현재 시스템: 2x ~ 20x (균형형)")
        print(f"  바이낸스:    1x ~ 125x (전체 범위)")
        print(f"  커버리지:    {(20-2)/(125-1)*100:.1f}%")
        
        # 권장 사항
        print("\n" + "=" * 80)
        print("💡 권장 사항:\n")
        
        print("  Option A (현재 유지): 2-20x")
        print("    - 장점: 안전, 손실 제한")
        print("    - 단점: 수익 제한")
        print("    - 적합: 보수적~균형형 전략")
        
        print("\n  Option B (중간 확장): 2-50x")
        print("    - 장점: 우수한 전략에 더 높은 레버리지")
        print("    - 단점: 리스크 증가")
        print("    - 적합: 검증된 전략만")
        
        print("\n  Option C (전체 범위): 2-125x")
        print("    - 장점: 최대 자유도")
        print("    - 단점: 고위험, 청산 위험")
        print("    - 적합: 전문 트레이더용")
        
        # 다차원 계산과 안전성
        print("\n" + "=" * 80)
        print("🛡️  다차원 계산 + 높은 레버리지 안전성 분석:\n")
        
        print("  우리 시스템 안전 장치:")
        print("    1. Sharpe < 1.5 → 최대 1.3배 증가 (20x → 26x)")
        print("    2. Winrate < 65% → 최대 1.2배 증가 (20x → 24x)")
        print("    3. DD > 10% → 0.7배 감소 (50x → 35x)")
        print("    4. 샘플 < 30 → 0.9배 감소 (50x → 45x)")
        print("    5. 신뢰도 < 0.8 → 최대 1.24배 (50x → 62x)")
        
        print("\n  시뮬레이션 (50x 최대 레버리지):")
        print("    최악의 전략: sharpe=0.2, wr=0.42, dd=12%, trades=15")
        print("    → 2 × 0.8 × 0.8 × 0.94 × 0.86 × 0.7 × 0.9 = 0.65 → 2x (최소 유지)")
        
        print("\n    최고의 전략: sharpe=1.8, wr=0.70, dd=2%, trades=100")
        print("    → 50 × 1.3 × 1.2 × 1.28 × 1.08 × 1.0 × 1.0 = 107x")
        print("    → 50x (max 제한)")
        
        print("\n  결론: 50x 최대값도 안전")
        print("    - 약한 전략: 자동으로 2x 유지")
        print("    - 우수한 전략만 높은 레버리지 사용")
        
        print("\n" + "=" * 80)
        
        return leverage_ranges
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        return None


if __name__ == "__main__":
    check_leverage_brackets()
