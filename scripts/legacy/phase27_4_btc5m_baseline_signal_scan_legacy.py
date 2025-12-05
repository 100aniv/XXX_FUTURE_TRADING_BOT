#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️⚠️⚠️ DEPRECATED - LEGACY OFFLINE SCAN (PHASE27-8 격리) ⚠️⚠️⚠️
================================================================

⛔ **이 스크립트는 SSOT(Single Source of Truth) 원칙에 위배되어 격리되었습니다.**

**문제점**:
- ❌ 엔진을 우회하여 신호를 직접 계산 (`signal_logic()` 직접 호출)
- ❌ 지표를 엔진 외부에서 계산 (`add_indicators()` 직접 호출)
- ❌ Feed 어댑터 우회 (CSV 직접 로드)
- ❌ "두 번째 신호 경로" 생성 → Parity 불일치 원인

**현재 상태**:
- 프로덕션/튜닝/백테스트에서 사용되지 않음
- Offline Scan 방식은 PHASE27-8부터 사용 금지

**공식 신호 계산 경로**:
```
execution/engine.py::run_v2()
    ↓
BaseStrategy.compute_signal(df, config)
    ↓
metrics/trade_activity_tracker.py
```

**보관 이유**:
- PHASE27-4~7 parity 디버깅 과거 히스토리 참고용
- 엔진 밖에서 신호를 직접 계산하는 안티패턴 예시

**대안**:
- 신호 분석이 필요하면: `TradeActivityTracker` Summary JSON 사용
- 백테스트 필요하면: `scripts/run_backtest.py --config xxx.yml`
- 연구용 하네스: `phase27_5_btc5m_baseline_engine_replay.py` (run_v2 호출)

---

PHASE27-4: Offline Signal Scan Harness (연구/분석용)
======================================================
⚠️ 이 스크립트는 엔진이 아니라 오프라인 분석 도구입니다.
⚠️ 엔진 루프는 execution.engine.run_v2()가 단일 소스입니다.

Baseline+ADX 전략의 역사 데이터 신호 발생 검증

목표:
- 실제 시장 데이터에서 전략이 얼마나 많은 신호를 생성하는지 검증
- ADX Regime별 신호 분포 확인
- Auto-Calibration을 위한 파라미터 탐색

Usage (DEPRECATED):
    python scripts/legacy/phase27_4_btc5m_baseline_signal_scan_legacy.py \\
        --data-file data/BTCUSDT_5m_2024-01-01_2024-12-31.csv \\
        --days 30 \\
        --output docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json
"""
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from indicators.core_indicators import add_indicators
from strategies.btc5m_baseline_v1 import signal_logic


def log(msg: str):
    """간단한 로그 출력"""
    print(f"[PHASE27-4 SIGNAL SCAN] {msg}")


def load_data(data_file: Path, days: int = None) -> pd.DataFrame:
    """
    데이터 로드 및 기간 필터링
    
    Args:
        data_file: CSV 파일 경로
        days: 최근 N일만 사용 (None이면 전체)
    
    Returns:
        DataFrame with OHLCV data
    """
    log(f"데이터 로드 중: {data_file}")
    
    if not data_file.exists():
        raise FileNotFoundError(f"데이터 파일 없음: {data_file}")
    
    df = pd.read_csv(data_file)
    
    # 컬럼 확인 및 정규화
    if 'timestamp' in df.columns and 'time' not in df.columns:
        df = df.rename(columns={'timestamp': 'time'})
    
    required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")
    
    # time을 datetime으로 변환
    if df['time'].dtype == 'int64':
        df['time'] = pd.to_datetime(df['time'], unit='ms')
    else:
        df['time'] = pd.to_datetime(df['time'])
    
    # 정렬
    df = df.sort_values('time').reset_index(drop=True)
    
    log(f"전체 데이터: {len(df):,}개 캔들 ({df['time'].min()} ~ {df['time'].max()})")
    
    # 최근 N일 필터링
    if days is not None:
        cutoff_date = df['time'].max() - timedelta(days=days)
        df = df[df['time'] >= cutoff_date].reset_index(drop=True)
        log(f"최근 {days}일 필터링: {len(df):,}개 캔들 ({df['time'].min()} ~ {df['time'].max()})")
    
    return df


def prepare_indicators(df: pd.DataFrame, use_adx: bool = True, adx_period: int = 14) -> pd.DataFrame:
    """
    지표 계산 (PHASE27-7: NaN 유지, Warmup은 호출자가 처리)
    
    Args:
        df: OHLCV DataFrame
        use_adx: ADX 사용 여부
        adx_period: ADX 계산 기간
    
    Returns:
        지표가 추가된 DataFrame (NaN 유지, 인덱스 유지)
    """
    log("지표 계산 중...")
    
    # PHASE27-7: drop_nan=False로 명시하여 NaN 유지
    # Warmup 처리는 scan_signals()의 min_bars로 제어
    df_with_indicators = add_indicators(
        df,
        use_adx=use_adx,
        adx_period=adx_period,
        drop_nan=False  # PHASE27-7: NaN 유지
    )
    
    log(f"지표 계산 완료: {len(df_with_indicators.columns)}개 컬럼 (NaN 유지, bars={len(df_with_indicators)})")
    
    return df_with_indicators


def scan_signals(
    df: pd.DataFrame,
    config: Dict[str, Any],
    min_bars: int = 50
) -> Dict[str, Any]:
    """
    전체 데이터에서 신호 스캔
    
    Args:
        df: 지표가 포함된 DataFrame
        config: 전략 설정
        min_bars: 최소 warmup 캔들 수
    
    Returns:
        스캔 결과 딕셔너리
    """
    log(f"신호 스캔 시작 (warmup: {min_bars}개 캔들)")
    
    results = {
        "total_bars": len(df),
        "warmup_skipped": min_bars,
        "evaluated_bars": 0,
        "signals_true": 0,
        "signals_false": 0,
        "long_signals": 0,
        "short_signals": 0,
        "regime_range_signals": 0,
        "regime_trend_signals": 0,
        "regime_range_total": 0,
        "regime_trend_total": 0,
        "signal_details": []  # 각 신호의 상세 정보 (샘플링)
    }
    
    # Warmup 이후부터 평가
    for i in range(min_bars, len(df)):
        # 현재까지의 데이터 슬라이스
        df_slice = df.iloc[:i+1].copy()
        
        # 신호 생성
        signal = signal_logic(df_slice, config)
        
        results["evaluated_bars"] += 1
        
        # 신호 여부 판정
        has_signal = signal.get("side") is not None
        
        if has_signal:
            results["signals_true"] += 1
            
            side = signal["side"]
            if side == "LONG":
                results["long_signals"] += 1
            elif side == "SHORT":
                results["short_signals"] += 1
            
            # Regime 정보
            metadata = signal.get("metadata", {})
            regime = metadata.get("regime", "UNKNOWN")
            
            if "RANGE" in regime:
                results["regime_range_signals"] += 1
            elif "TREND" in regime:
                results["regime_trend_signals"] += 1
            
            # 샘플 저장 (처음 100개만)
            if len(results["signal_details"]) < 100:
                results["signal_details"].append({
                    "index": i,
                    "time": str(df.iloc[i]["time"]),
                    "side": side,
                    "regime": regime,
                    "reason": signal.get("reason", ""),
                    "price": float(df.iloc[i]["close"]),
                    "rsi": float(df.iloc[i].get("rsi", 0)),
                    "adx": float(metadata.get("adx", 0)) if metadata.get("adx") is not None else None
                })
        else:
            results["signals_false"] += 1
        
        # Regime 카운트 (신호 여부와 무관)
        # ADX 컬럼 확인
        adx_col = f"adx_{config.get('adx_period', 14)}"
        if config.get('use_adx') and adx_col in df.columns:
            adx_val = df.iloc[i].get(adx_col)
            if pd.notna(adx_val):
                if adx_val >= config.get('adx_trend_threshold', 25):
                    results["regime_trend_total"] += 1
                else:
                    results["regime_range_total"] += 1
        
        # 진행률 로그 (10% 단위)
        if (i - min_bars + 1) % max(1, (len(df) - min_bars) // 10) == 0:
            progress = (i - min_bars + 1) / (len(df) - min_bars) * 100
            log(f"진행률: {progress:.1f}% ({i - min_bars + 1}/{len(df) - min_bars})")
    
    log(f"신호 스캔 완료: {results['signals_true']}/{results['evaluated_bars']} ({results['signals_true']/results['evaluated_bars']*100:.2f}%)")
    
    return results


def grid_search_parameters(
    df: pd.DataFrame,
    param_grid: Dict[str, List],
    base_config: Dict[str, Any],
    days_for_search: int = 7,
    min_bars: int = 50
) -> List[Dict[str, Any]]:
    """
    파라미터 그리드 탐색
    
    Args:
        df: 지표가 포함된 DataFrame
        param_grid: 탐색할 파라미터 그리드
        base_config: 기본 설정
        days_for_search: 탐색에 사용할 최근 N일
        min_bars: 최소 warmup 캔들 수
    
    Returns:
        파라미터 조합별 결과 리스트
    """
    log("=" * 60)
    log("파라미터 그리드 탐색 시작")
    log("=" * 60)
    
    # 최근 N일 데이터만 사용
    cutoff_date = df['time'].max() - timedelta(days=days_for_search)
    df_search = df[df['time'] >= cutoff_date].reset_index(drop=True)
    
    log(f"탐색 데이터: {len(df_search):,}개 캔들 (최근 {days_for_search}일)")
    
    # 파라미터 조합 생성
    from itertools import product
    
    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]
    combinations = list(product(*param_values))
    
    log(f"총 {len(combinations)}개 조합 탐색")
    
    results = []
    
    for idx, combo in enumerate(combinations):
        # Config 생성
        config = base_config.copy()
        for param_name, param_value in zip(param_names, combo):
            config[param_name] = param_value
        
        # 신호 스캔
        scan_result = scan_signals(df_search, config, min_bars=min_bars)
        
        # 하루 평균 신호 수
        signals_per_day = scan_result["signals_true"] / days_for_search if days_for_search > 0 else 0
        
        # Long/Short 비율
        total_directional = scan_result["long_signals"] + scan_result["short_signals"]
        long_ratio = scan_result["long_signals"] / total_directional if total_directional > 0 else 0
        
        # 결과 저장
        result = {
            "set_name": f"set_{idx+1:02d}",
            "parameters": dict(zip(param_names, combo)),
            "signals_true": scan_result["signals_true"],
            "signals_per_day": signals_per_day,
            "long_signals": scan_result["long_signals"],
            "short_signals": scan_result["short_signals"],
            "long_ratio": long_ratio,
            "regime_range_signals": scan_result["regime_range_signals"],
            "regime_trend_signals": scan_result["regime_trend_signals"],
            "evaluated_bars": scan_result["evaluated_bars"]
        }
        
        results.append(result)
        
        log(f"[{idx+1}/{len(combinations)}] {result['set_name']}: {signals_per_day:.1f} signals/day, Long {long_ratio*100:.1f}%")
    
    # 결과 정렬 (하루 신호 수 기준)
    results.sort(key=lambda x: abs(x["signals_per_day"] - 30), reverse=False)  # 하루 30개 신호 목표
    
    log("=" * 60)
    log(f"그리드 탐색 완료: {len(results)}개 조합")
    log("=" * 60)
    
    return results


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description='PHASE27-4: Offline Signal Scan')
    parser.add_argument('--data-file', type=str, default='data/BTCUSDT_5m_2024-01-01_2024-12-31.csv',
                        help='데이터 파일 경로')
    parser.add_argument('--days', type=int, default=30,
                        help='최근 N일 데이터 사용')
    parser.add_argument('--output', type=str, default='docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json',
                        help='출력 JSON 파일 경로')
    parser.add_argument('--grid-search', action='store_true',
                        help='파라미터 그리드 탐색 실행')
    parser.add_argument('--grid-days', type=int, default=7,
                        help='그리드 탐색에 사용할 최근 N일')
    
    args = parser.parse_args()
    
    log("=" * 60)
    log("PHASE27-4: Offline Signal Scan Harness")
    log("=" * 60)
    
    # 데이터 로드
    data_file = PROJECT_ROOT / args.data_file
    df = load_data(data_file, days=args.days)
    
    # 지표 계산
    df = prepare_indicators(df, use_adx=True, adx_period=14)
    
    # 기본 Config
    base_config = {
        'rsi_long_threshold': 45,
        'rsi_short_threshold': 55,
        'bb_std_main': 1.0,
        'bb_std_strong': 1.5,
        'momentum_lookback': 5,
        'momentum_threshold': 0.001,
        'use_adx': True,
        'adx_period': 14,
        'adx_trend_threshold': 20,  # PHASE27-7: Replay와 통일 (기존 25 → 20)
        'rr': 1.5,
        'atr_mult_sl': 1.5,
        'max_hold_minutes': 60,
        'min_bars_for_signal': 50,
        'filters': {'allow_short': True},
        'leverage': {'min': 1, 'max': 5, 'default': 3}
    }
    
    # 기본 신호 스캔
    log("=" * 60)
    log("기본 파라미터 신호 스캔")
    log("=" * 60)
    scan_result = scan_signals(df, base_config, min_bars=50)
    
    # 그리드 탐색 (옵션)
    grid_results = []
    if args.grid_search:
        param_grid = {
            'rsi_long_threshold': [42, 45, 48],
            'rsi_short_threshold': [52, 55, 58],
            'bb_std_main': [0.8, 1.0, 1.2],
            'bb_std_strong': [1.2, 1.5],
            'adx_trend_threshold': [20, 25, 30]
        }
        
        grid_results = grid_search_parameters(
            df, param_grid, base_config,
            days_for_search=args.grid_days,
            min_bars=50
        )
    
    # 결과 저장
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "run_id": "phase27_4_btc5m_baseline_signal_scan",
        "timestamp": datetime.now().isoformat(),
        "data_file": str(data_file),
        "data_period": {
            "start": str(df['time'].min()),
            "end": str(df['time'].max()),
            "days": args.days
        },
        "base_config": base_config,
        "scan_result": scan_result,
        "grid_search": {
            "enabled": args.grid_search,
            "results": grid_results[:10] if grid_results else []  # Top 10만 저장
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    log("=" * 60)
    log(f"결과 저장 완료: {output_path}")
    log("=" * 60)
    
    # 요약 출력
    log("\n📊 기본 파라미터 스캔 결과:")
    log(f"  - 총 캔들: {scan_result['total_bars']:,}개")
    log(f"  - 평가 캔들: {scan_result['evaluated_bars']:,}개")
    log(f"  - 신호 발생: {scan_result['signals_true']:,}개 ({scan_result['signals_true']/scan_result['evaluated_bars']*100:.2f}%)")
    log(f"  - LONG: {scan_result['long_signals']:,}개")
    log(f"  - SHORT: {scan_result['short_signals']:,}개")
    log(f"  - RANGE Regime 신호: {scan_result['regime_range_signals']:,}개")
    log(f"  - TREND Regime 신호: {scan_result['regime_trend_signals']:,}개")
    
    if args.days:
        signals_per_day = scan_result['signals_true'] / args.days
        log(f"  - 하루 평균 신호: {signals_per_day:.1f}개")
    
    if grid_results:
        log("\n🔍 그리드 탐색 Top 3:")
        for i, result in enumerate(grid_results[:3], 1):
            log(f"  {i}. {result['set_name']}: {result['signals_per_day']:.1f} signals/day")
            log(f"     파라미터: {result['parameters']}")
    
    log("=" * 60)
    log("PHASE27-4 Signal Scan 완료")
    log("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
