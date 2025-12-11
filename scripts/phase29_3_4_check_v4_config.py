"""
PHASE29-3.4: V4 Config 파일 파싱 검증
"""
import yaml
from pathlib import Path

def check_v4_config():
    config_path = Path("configs/backtest/phase29_3_1_btc5m_baseline_v4_week.yml")
    
    if not config_path.exists():
        print(f"❌ Config 파일 없음: {config_path}")
        return False
    
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("✅ Config 파싱 성공")
    print(f"\n[기본 설정]")
    print(f"  Symbol: {config['symbol']}")
    print(f"  Timeframe: {config['timeframe']}")
    print(f"  Mode: {config.get('mode', 'N/A')}")
    print(f"  Start Date: {config.get('start_date', 'N/A')}")
    print(f"  End Date: {config.get('end_date', 'N/A')}")
    
    print(f"\n[전략 설정]")
    print(f"  Selector: {config['strategy']['selector']}")
    
    # V4 파라미터는 strategies 섹션에 있음
    v4_params = config.get('strategies', {}).get('btc5m_baseline_v4', {})
    
    if not v4_params:
        print("\n⚠️  V4 파라미터 없음 (strategies.btc5m_baseline_v4)")
        return False
    
    print(f"\n[V4 파라미터]")
    print(f"  Range min score: {v4_params.get('range_min_score', 'N/A')}")
    print(f"  Trend min score: {v4_params.get('trend_min_score', 'N/A')}")
    print(f"  Min bars for signal: {v4_params.get('min_bars_for_signal', 'N/A')}")
    
    print(f"\n[V4 필터]")
    filters = v4_params.get('filters', {})
    print(f"  Min ATR pct: {filters.get('min_atr_pct', 'N/A')}")
    print(f"  Min volume ratio: {filters.get('min_volume_ratio', 'N/A')}")
    print(f"  Enable min ATR: {filters.get('enable_min_atr', 'N/A')}")
    print(f"  Enable volume filter: {filters.get('enable_volume_filter', 'N/A')}")
    
    print(f"\n[Indicators]")
    inds = config.get('indicators', {})
    print(f"  EMA fast: {inds.get('ema', {}).get('fast', 'N/A')}")
    print(f"  EMA mid: {inds.get('ema', {}).get('mid', 'N/A')}")
    print(f"  EMA slow: {inds.get('ema', {}).get('slow', 'N/A')}")
    print(f"  RSI length: {inds.get('rsi', {}).get('length', 'N/A')}")
    print(f"  ADX period: {inds.get('adx', {}).get('period', 'N/A')}")
    print(f"  ATR length: {inds.get('atr', {}).get('length', 'N/A')}")
    print(f"  Volume MA length: {inds.get('volume', {}).get('ma_length', 'N/A')}")
    
    return True

if __name__ == "__main__":
    check_v4_config()
