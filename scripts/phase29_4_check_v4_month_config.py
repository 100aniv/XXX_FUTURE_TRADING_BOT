"""
PHASE29-4: V4 1개월 백테스트 Config 검증 스크립트

목적: phase29_4_0_btc5m_baseline_v4_month_baseline.yml 파싱 및 주요 설정 확인
"""

import sys
from pathlib import Path
import yaml

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_v4_month_config():
    """V4 1개월 백테스트 Config 검증"""
    
    config_path = project_root / "configs" / "backtest" / "phase29_4_0_btc5m_baseline_v4_month_baseline.yml"
    
    print("=" * 80)
    print("PHASE29-4: V4 1개월 백테스트 Config 검증")
    print("=" * 80)
    
    if not config_path.exists():
        print(f"❌ Config 파일이 존재하지 않습니다: {config_path}")
        return False
    
    print(f"✅ Config 파일 찾음: {config_path.name}\n")
    
    # YAML 파싱
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAML 파싱 실패: {e}")
        return False
    
    print("✅ YAML 파싱 성공\n")
    
    # 1. 기본 설정 확인
    print("=" * 80)
    print("1. 기본 설정")
    print("=" * 80)
    print(f"  mode: {config.get('mode')}")
    print(f"  run_id: {config.get('run_id')}")
    print(f"  symbol: {config.get('symbol')}")
    print(f"  timeframe: {config.get('timeframe')}")
    
    # 2. Backtest 설정 확인
    print("\n" + "=" * 80)
    print("2. Backtest 설정")
    print("=" * 80)
    backtest = config.get("backtest", {})
    print(f"  data_file: {backtest.get('data_file')}")
    print(f"  start_date: {backtest.get('start_date')}")
    print(f"  end_date: {backtest.get('end_date')}")
    print(f"  duration_minutes: {backtest.get('duration_minutes')} (30일 = 43200분)")
    print(f"  output_file: {backtest.get('output_file')}")
    
    # 3. 전략 설정 확인
    print("\n" + "=" * 80)
    print("3. 전략 설정")
    print("=" * 80)
    strategy = config.get("strategy", {})
    print(f"  selector: {strategy.get('selector')}")
    print(f"  use_ensemble: {strategy.get('use_ensemble')}")
    
    # 4. Guard 설정 확인
    print("\n" + "=" * 80)
    print("4. Guard 설정 (실전 수준)")
    print("=" * 80)
    entries = config.get("entries", {})
    print(f"  cooldown_candles: {entries.get('cooldown_candles')} (1캔들 = 5분)")
    print(f"  min_rr_required: {entries.get('min_rr_required')} (1.2 = 실전 수준)")
    
    risk = config.get("risk", {})
    print(f"  max_drawdown: {risk.get('max_drawdown')} (0.15 = 15%)")
    
    flow_guardian = config.get("flow_guardian", {})
    print(f"  flow_guardian.enabled: {flow_guardian.get('enabled')}")
    
    # 5. V4 전략 파라미터 확인
    print("\n" + "=" * 80)
    print("5. V4 전략 파라미터")
    print("=" * 80)
    strategies = config.get("strategies", {})
    v4_params = strategies.get("btc5m_baseline_v4", {})
    
    print(f"  [Regime Detection]")
    print(f"    adx_trend_threshold: {v4_params.get('adx_trend_threshold')}")
    print(f"    adx_range_threshold: {v4_params.get('adx_range_threshold')}")
    
    print(f"\n  [Trend Mode]")
    print(f"    trend_min_score: {v4_params.get('trend_min_score')}")
    print(f"    trend_rsi_threshold: {v4_params.get('trend_rsi_threshold')}")
    print(f"    trend_weight_rsi: {v4_params.get('trend_weight_rsi')}")
    print(f"    trend_weight_bb: {v4_params.get('trend_weight_bb')}")
    print(f"    trend_weight_ema: {v4_params.get('trend_weight_ema')}")
    print(f"    trend_weight_di: {v4_params.get('trend_weight_di')}")
    
    print(f"\n  [Range Mode]")
    print(f"    range_min_score: {v4_params.get('range_min_score')}")
    print(f"    range_rsi_threshold: {v4_params.get('range_rsi_threshold')}")
    print(f"    range_weight_rsi: {v4_params.get('range_weight_rsi')}")
    print(f"    range_weight_bb: {v4_params.get('range_weight_bb')}")
    print(f"    range_weight_adx: {v4_params.get('range_weight_adx')}")
    
    filters = v4_params.get("filters", {})
    print(f"\n  [Filters]")
    print(f"    min_atr_pct: {filters.get('min_atr_pct')}")
    print(f"    min_volume_ratio: {filters.get('min_volume_ratio')}")
    print(f"    allow_short: {filters.get('allow_short')}")
    
    # 6. Indicators 확인
    print("\n" + "=" * 80)
    print("6. Indicators 설정")
    print("=" * 80)
    indicators = config.get("indicators", {})
    print(f"  ema: fast={indicators.get('ema', {}).get('fast')}, mid={indicators.get('ema', {}).get('mid')}, slow={indicators.get('ema', {}).get('slow')}")
    print(f"  rsi: length={indicators.get('rsi', {}).get('length')}")
    print(f"  bollinger: length={indicators.get('bollinger', {}).get('length')}, std={indicators.get('bollinger', {}).get('std')}")
    print(f"  atr: length={indicators.get('atr', {}).get('length')}")
    print(f"  adx: period={indicators.get('adx', {}).get('period')}")
    
    # 7. 최종 검증
    print("\n" + "=" * 80)
    print("7. 검증 결과")
    print("=" * 80)
    
    issues = []
    
    # 필수 필드 체크
    if config.get("mode") != "backtest":
        issues.append("mode가 'backtest'가 아님")
    
    if strategy.get("selector") != "btc5m_baseline_v4":
        issues.append("strategy.selector가 'btc5m_baseline_v4'가 아님")
    
    if backtest.get("start_date") != "2024-11-01 00:00:00":
        issues.append("start_date가 2024-11-01이 아님 (V3와 다른 구간)")
    
    if backtest.get("end_date") != "2024-12-01 00:00:00":
        issues.append("end_date가 2024-12-01이 아님 (V3와 다른 구간)")
    
    if backtest.get("duration_minutes") != 43200:
        issues.append("duration_minutes가 43200(30일)이 아님")
    
    if entries.get("cooldown_candles") != 1:
        issues.append("cooldown_candles가 1이 아님 (실전 수준)")
    
    if entries.get("min_rr_required") != 1.2:
        issues.append("min_rr_required가 1.2가 아님 (실전 수준)")
    
    if risk.get("max_drawdown") != 0.15:
        issues.append("max_drawdown이 0.15(15%)가 아님")
    
    if v4_params.get("range_min_score") != 3:
        issues.append("range_min_score가 3이 아님 (Baseline)")
    
    if v4_params.get("trend_min_score") != 3:
        issues.append("trend_min_score가 3이 아님 (Baseline)")
    
    if issues:
        print("❌ 검증 실패:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ 모든 검증 통과!")
        print("\n📊 기대 결과:")
        print("  - 거래 건수: 80~240건 (Gate_1M)")
        print("  - Win Rate: ≥ 45%")
        print("  - Max DD: ≤ 15%")
        print("  - 1주일 35건 → 1개월 약 140건 예상")
        return True


if __name__ == "__main__":
    success = check_v4_month_config()
    sys.exit(0 if success else 1)
