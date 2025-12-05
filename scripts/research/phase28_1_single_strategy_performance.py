#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-1: Single Strategy Performance Baseline Runner
=======================================================

목적:
- btc5m_baseline_v1 전략의 성능 기준선 측정
- 여러 시장 구간(상승/하락/박스)에 대한 백테스트 실행
- Preset별 핵심 메트릭 수집 및 문서화

사용법:
    python scripts/research/phase28_1_single_strategy_performance.py [--smoke] [--preset PRESET_NAME]

옵션:
    --smoke: 짧은 구간 테스트만 실행 (7일)
    --preset: 특정 preset만 실행 (conservative/neutral/aggressive)

출력:
    - reports/phase28_1_btc5m_performance.json
    - (선택) tuning.results 테이블에 type='baseline'으로 저장
"""
import sys
import json
import yaml
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 기존 모듈 재사용
from execution import engine
# Note: DB connection은 필요시에만 사용 (현재는 불필요)

# 메트릭 계산 함수 재사용 (tuning_core에서 import)
try:
    from tuning.tuning_core import _sharpe, _mdd_pct_from_trades, _daily_returns_from_trades
except ImportError:
    # tuning_core가 없으면 간단한 fallback
    def _sharpe(daily_returns: List[float]) -> float:
        import statistics
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        mu = statistics.mean(daily_returns)
        sigma = statistics.pstdev(daily_returns)
        return (mu / sigma) if sigma > 0 else 0.0
    
    def _mdd_pct_from_trades(rows: List[Tuple[datetime, float]], capital: float = 10000.0) -> float:
        eq = capital
        peak = capital
        worst = 0.0
        for _, pnl in sorted(rows, key=lambda x: x[0]):
            eq += float(pnl or 0.0)
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > worst:
                worst = dd
        return worst * 100.0
    
    def _daily_returns_from_trades(rows: List[Tuple[datetime, float]], capital: float = 10000.0) -> List[float]:
        from datetime import date
        by_day: Dict[date, float] = {}
        for ts_close, pnl in rows:
            d = ts_close.date()
            by_day[d] = by_day.get(d, 0.0) + float(pnl or 0.0)
        returns: List[float] = []
        for d in sorted(by_day.keys()):
            daily_pnl = by_day[d]
            returns.append(daily_pnl / capital)
        return returns

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    YAML Config 로드
    
    Args:
        config_path: Config 파일 경로
    
    Returns:
        Config dictionary
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def merge_config_for_backtest(
    common_cfg: Dict[str, Any],
    preset_name: str,
    preset_params: Dict[str, Any],
    period_name: str,
    period_cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    백테스트용 Config 병합
    
    Args:
        common_cfg: 공통 설정
        preset_name: Preset 이름
        preset_params: Preset 파라미터
        period_name: 구간 이름
        period_cfg: 구간 설정
    
    Returns:
        병합된 Config
    """
    # 공통 설정 복사
    config = common_cfg.copy()
    
    # Backtest 모드 설정
    config['mode'] = 'backtest'
    config['run_id'] = f"phase28_1_{preset_name}_{period_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 기간 설정
    config['start_date'] = period_cfg['start']
    config['end_date'] = period_cfg['end']
    
    # 전략 파라미터 병합
    if 'strategy' not in config:
        config['strategy'] = {}
    
    # Preset 파라미터 추가
    for key, value in preset_params.items():
        config[key] = value
    
    return config


def run_single_backtest(
    preset_name: str,
    preset_cfg: Dict[str, Any],
    period_name: str,
    period_cfg: Dict[str, Any],
    common_cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    단일 (preset, 기간) 조합에 대한 백테스트 실행
    
    Args:
        preset_name: Preset 이름
        preset_cfg: Preset 설정
        period_name: 구간 이름
        period_cfg: 구간 설정
        common_cfg: 공통 설정
    
    Returns:
        메트릭 dictionary
    """
    logger.info(f"🚀 백테스트 시작: Preset={preset_name}, Period={period_name}")
    
    # Config 병합
    config = merge_config_for_backtest(
        common_cfg=common_cfg,
        preset_name=preset_name,
        preset_params=preset_cfg['params'],
        period_name=period_name,
        period_cfg=period_cfg
    )
    
    try:
        # 엔진 실행 (run_v2 단일 진입점 사용)
        logger.info(f"  ↪ 엔진 호출: execution.engine.run_v2(mode='backtest')")
        result = engine.run_v2(
            mode='backtest',
            config=config,
            clean_state=True
        )
        
        # 결과에서 메트릭 추출
        metrics = extract_metrics_from_result(result, config)
        
        logger.info(f"✅ 백테스트 완료: {metrics.get('total_trades', 0)} trades")
        return metrics
        
    except Exception as e:
        logger.error(f"❌ 백테스트 실패: {e}", exc_info=True)
        return {
            'error': str(e),
            'preset': preset_name,
            'period': period_name,
            'status': 'FAILED'
        }


def extract_metrics_from_result(result: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    엔진 실행 결과에서 메트릭 추출
    
    Args:
        result: 엔진 실행 결과
        config: 백테스트 Config
    
    Returns:
        메트릭 dictionary
    """
    capital = config.get('initial_equity', 10000.0)
    
    # Result가 dict인 경우 (engine.run_v2 반환값)
    if isinstance(result, dict):
        trades = result.get('trades', [])
        equity_curve = result.get('equity_curve', [])
    else:
        # Result가 객체인 경우
        trades = getattr(result, 'trades', [])
        equity_curve = getattr(result, 'equity_curve', [])
    
    # 기본 메트릭
    total_trades = len(trades)
    
    if total_trades == 0:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'gross_pnl': 0.0,
            'net_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_like_ratio': 0.0,
            'avg_holding_minutes': 0.0,
            'long_short_ratio': 0.0,
            'long_count': 0,
            'short_count': 0
        }
    
    # Win rate 계산
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    
    # PnL 계산
    gross_pnl = sum(t.get('pnl', 0) for t in trades)
    fees = sum(t.get('fee', 0) for t in trades)
    net_pnl = gross_pnl - fees
    
    # Sharpe & MDD 계산 (tuning_core 함수 재사용)
    rows = [(t.get('ts_close', datetime.now()), t.get('pnl', 0)) for t in trades]
    daily_returns = _daily_returns_from_trades(rows, capital=capital)
    sharpe = _sharpe(daily_returns)
    mdd = _mdd_pct_from_trades(rows, capital=capital)
    
    # 평균 보유 시간
    holding_times = []
    for t in trades:
        ts_open = t.get('ts_open')
        ts_close = t.get('ts_close')
        if ts_open and ts_close:
            holding_times.append((ts_close - ts_open).total_seconds() / 60.0)
    avg_holding_minutes = sum(holding_times) / len(holding_times) if holding_times else 0.0
    
    # LONG/SHORT 비율
    long_count = sum(1 for t in trades if t.get('side', '').upper() == 'LONG')
    short_count = total_trades - long_count
    long_short_ratio = long_count / short_count if short_count > 0 else float('inf')
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'gross_pnl': gross_pnl,
        'net_pnl': net_pnl,
        'max_drawdown': mdd,
        'sharpe_like_ratio': sharpe,
        'avg_holding_minutes': avg_holding_minutes,
        'long_short_ratio': long_short_ratio,
        'long_count': long_count,
        'short_count': short_count,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades
    }


def run_performance_baseline(
    config_path: Path,
    smoke_test: bool = False,
    preset_filter: str = None
) -> Dict[str, Any]:
    """
    전체 Performance Baseline 실행
    
    Args:
        config_path: Config 파일 경로
        smoke_test: True면 짧은 구간만 테스트
        preset_filter: 특정 preset만 실행
    
    Returns:
        전체 결과 dictionary
    """
    logger.info("=" * 60)
    logger.info("PHASE28-1: Single Strategy Performance Baseline")
    logger.info("=" * 60)
    
    # Config 로드
    config = load_config(config_path)
    common_cfg = config.get('common', {})
    presets = config.get('presets', {})
    periods = config.get('market_periods', {})
    smoke_cfg = config.get('smoke_test', {})
    
    # Smoke test 모드
    if smoke_test:
        logger.info("🔥 Smoke Test 모드: 짧은 구간만 테스트")
        periods = {'smoke_test': smoke_cfg}
    
    # Preset 필터링
    if preset_filter:
        if preset_filter in presets:
            presets = {preset_filter: presets[preset_filter]}
            logger.info(f"🎯 Preset 필터: {preset_filter}")
        else:
            logger.warning(f"⚠️ Preset '{preset_filter}' 없음. 전체 실행")
    
    # 결과 수집
    results = {
        'run_timestamp': datetime.now().isoformat(),
        'config_path': str(config_path),
        'smoke_test': smoke_test,
        'preset_filter': preset_filter,
        'results_by_preset_period': {}
    }
    
    # 각 (preset, period) 조합 실행
    total_combinations = len(presets) * len(periods)
    current = 0
    
    for preset_name, preset_cfg in presets.items():
        results['results_by_preset_period'][preset_name] = {}
        
        for period_name, period_cfg in periods.items():
            current += 1
            logger.info(f"[{current}/{total_combinations}] Preset={preset_name}, Period={period_name}")
            
            # 백테스트 실행
            metrics = run_single_backtest(
                preset_name=preset_name,
                preset_cfg=preset_cfg,
                period_name=period_name,
                period_cfg=period_cfg,
                common_cfg=common_cfg
            )
            
            # 결과 저장
            results['results_by_preset_period'][preset_name][period_name] = {
                'preset_description': preset_cfg.get('description', ''),
                'period_description': period_cfg.get('description', ''),
                'metrics': metrics
            }
    
    logger.info("=" * 60)
    logger.info("✅ 전체 백테스트 완료")
    logger.info("=" * 60)
    
    return results


def save_results(results: Dict[str, Any], output_path: Path):
    """
    결과를 JSON 파일로 저장
    
    Args:
        results: 결과 dictionary
        output_path: 출력 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📊 결과 저장: {output_path}")


def print_summary(results: Dict[str, Any]):
    """
    결과 요약 출력
    
    Args:
        results: 결과 dictionary
    """
    print("\n" + "=" * 80)
    print("📊 PHASE28-1 Performance Baseline 요약")
    print("=" * 80)
    
    for preset_name, period_results in results['results_by_preset_period'].items():
        print(f"\n🎯 Preset: {preset_name}")
        print("-" * 80)
        
        for period_name, period_data in period_results.items():
            metrics = period_data['metrics']
            
            print(f"  📅 {period_name}:")
            print(f"    - Total Trades: {metrics.get('total_trades', 0)}")
            print(f"    - Win Rate: {metrics.get('win_rate', 0.0) * 100:.1f}%")
            print(f"    - Net PnL: ${metrics.get('net_pnl', 0.0):.2f}")
            print(f"    - Max Drawdown: {metrics.get('max_drawdown', 0.0):.2f}%")
            print(f"    - Sharpe-like: {metrics.get('sharpe_like_ratio', 0.0):.3f}")
            print(f"    - Long/Short: {metrics.get('long_count', 0)}/{metrics.get('short_count', 0)}")
    
    print("\n" + "=" * 80)


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='PHASE28-1: Single Strategy Performance Baseline Runner'
    )
    parser.add_argument(
        '--smoke',
        action='store_true',
        help='짧은 구간 테스트만 실행 (7일)'
    )
    parser.add_argument(
        '--preset',
        type=str,
        default=None,
        help='특정 preset만 실행 (conservative/neutral/aggressive)'
    )
    
    args = parser.parse_args()
    
    # Config 경로
    config_path = PROJECT_ROOT / 'configs' / 'backtest' / 'phase28_1_btc5m_baseline_presets.yml'
    
    if not config_path.exists():
        logger.error(f"❌ Config 파일 없음: {config_path}")
        sys.exit(1)
    
    # 실행
    results = run_performance_baseline(
        config_path=config_path,
        smoke_test=args.smoke,
        preset_filter=args.preset
    )
    
    # 저장
    output_path = PROJECT_ROOT / 'reports' / 'phase28_1_btc5m_performance.json'
    save_results(results, output_path)
    
    # 요약 출력
    print_summary(results)
    
    logger.info("✅ PHASE28-1 실행 완료")


if __name__ == '__main__':
    main()
