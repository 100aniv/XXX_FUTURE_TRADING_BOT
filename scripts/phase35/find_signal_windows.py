#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-3 ITER13: Signal Window Finder + DecisionTrace Analyzer
================================================================

목표:
1. 2024년 기준 7D/14D 단위로 복수 구간 샘플링
2. trades>0 나오는 1M window 후보 확보
3. trades=0 구간의 DecisionTrace reason 분포 정량화
4. Light Profile 단계적 완화 로직 내장

출력:
- artifacts/phase35/iter13/window_scan.json

Usage:
    python scripts/phase35/find_signal_windows.py [--year 2024] [--max-windows 30]
"""
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from collections import defaultdict

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from common.decision_trace import DecisionTraceAnalyzer

logger = setup_logger("find_signal_windows")


def generate_window_candidates(year: int = 2024, window_days: int = 30, step_days: int = 7, max_windows: int = 30) -> List[Tuple[str, str]]:
    """
    Window 후보 생성 (7D 단위로 샘플링)
    
    Args:
        year: 대상 연도
        window_days: Window 크기 (일)
        step_days: 샘플링 간격 (일)
        max_windows: 최대 샘플 수
    
    Returns:
        [(start_date, end_date), ...]
    """
    start_date = datetime(year, 1, 1)
    end_of_year = datetime(year, 12, 31)
    
    windows = []
    current = start_date
    
    while current <= end_of_year and len(windows) < max_windows:
        window_end = current + timedelta(days=window_days)
        
        if window_end > end_of_year:
            break
        
        windows.append((
            current.strftime('%Y-%m-%d'),
            window_end.strftime('%Y-%m-%d')
        ))
        
        current += timedelta(days=step_days)
    
    logger.info(f"Generated {len(windows)} window candidates (window={window_days}d, step={step_days}d)")
    return windows


def run_quick_scan(start_date: str, end_date: str, config_path: Path) -> Dict[str, Any]:
    """
    빠른 백테스트 실행 (trades, runtime, DecisionTrace 수집)
    
    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        config_path: Config 파일 경로
    
    Returns:
        {
            'start_date': str,
            'end_date': str,
            'trades': int,
            'runtime_ms': float,
            'decision_trace_summary': {...},
            'error': str | None
        }
    """
    import subprocess
    import time
    
    logger.info(f"[Scan] {start_date} → {end_date}")
    
    # Config 임시 수정 (날짜 범위)
    temp_config = config_path.parent / f"temp_scan_{start_date}_{end_date}.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 날짜 범위 설정
        if 'backtest' not in config:
            config['backtest'] = {}
        config['backtest']['start_date'] = start_date
        config['backtest']['end_date'] = end_date
        
        # DecisionTrace 활성화
        if 'decision_trace' not in config:
            config['decision_trace'] = {}
        config['decision_trace']['enabled'] = True
        
        with open(temp_config, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        
        # 백테스트 실행 (간단한 runner)
        start_time = time.time()
        
        result = subprocess.run(
            [
                sys.executable,
                str(project_root / "execution" / "engine.py"),
                "--config", str(temp_config),
                "--mode", "backtest"
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        runtime_ms = (time.time() - start_time) * 1000
        
        # 결과 파싱
        trades = 0
        decision_trace_summary = {}
        
        # stdout에서 trades 추출
        for line in result.stdout.splitlines():
            if "Trades:" in line or "trades:" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        trades = int(parts[1].strip())
                    except ValueError:
                        pass
        
        # DecisionTrace 로드 (있으면)
        trace_file = project_root / "reports" / "backtest" / "phase35" / "traces" / "decision_trace.json"
        if trace_file.exists():
            analyzer = DecisionTraceAnalyzer(str(trace_file))
            analysis = analyzer.analyze()
            decision_trace_summary = analysis.get('block_reason_analysis', {})
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'trades': trades,
            'runtime_ms': runtime_ms,
            'decision_trace_summary': decision_trace_summary,
            'error': None if result.returncode == 0 else result.stderr[:500]
        }
    
    except subprocess.TimeoutExpired:
        return {
            'start_date': start_date,
            'end_date': end_date,
            'trades': 0,
            'runtime_ms': 120000,
            'decision_trace_summary': {},
            'error': 'TIMEOUT (120s)'
        }
    
    except Exception as e:
        logger.error(f"[Scan Error] {start_date} → {end_date}: {e}")
        return {
            'start_date': start_date,
            'end_date': end_date,
            'trades': 0,
            'runtime_ms': 0,
            'decision_trace_summary': {},
            'error': str(e)
        }
    
    finally:
        # 임시 config 삭제
        if temp_config.exists():
            temp_config.unlink()


def analyze_blocked_reasons(scan_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    전체 스캔 결과에서 차단 reason 집계
    
    Returns:
        {
            'total_windows': int,
            'trades_gt0_windows': int,
            'trades_eq0_windows': int,
            'blocked_reasons_topN': [{'reason': str, 'count': int, 'pct': float}, ...],
            'avg_runtime_ms': float
        }
    """
    total_windows = len(scan_results)
    trades_gt0 = sum(1 for r in scan_results if r['trades'] > 0)
    trades_eq0 = total_windows - trades_gt0
    
    # Blocked reasons 집계
    reason_counts = defaultdict(int)
    
    for result in scan_results:
        trace_summary = result.get('decision_trace_summary', {})
        all_reasons = trace_summary.get('all_reasons', {})
        for reason, count in all_reasons.items():
            reason_counts[reason] += count
    
    total_blocks = sum(reason_counts.values())
    
    sorted_reasons = sorted(
        reason_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    blocked_reasons_topN = [
        {
            'reason': reason,
            'count': count,
            'pct': count / total_blocks if total_blocks > 0 else 0.0
        }
        for reason, count in sorted_reasons[:10]
    ]
    
    avg_runtime = sum(r['runtime_ms'] for r in scan_results) / total_windows if total_windows > 0 else 0.0
    
    return {
        'total_windows': total_windows,
        'trades_gt0_windows': trades_gt0,
        'trades_eq0_windows': trades_eq0,
        'blocked_reasons_topN': blocked_reasons_topN,
        'avg_runtime_ms': avg_runtime,
        'total_blocks': total_blocks
    }


def select_best_window(scan_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    trades>0 윈도우 중 최선 후보 선정
    
    우선순위:
    1. trades가 가장 많은 윈도우
    2. 동점이면 runtime이 짧은 윈도우
    
    Returns:
        Best window dict or None
    """
    valid_windows = [r for r in scan_results if r['trades'] > 0]
    
    if not valid_windows:
        return None
    
    best = max(
        valid_windows,
        key=lambda x: (x['trades'], -x['runtime_ms'])
    )
    
    return best


def apply_light_profile(config_path: Path, stage: int = 1) -> Path:
    """
    Light Profile 완화 적용 (Config 생성)
    
    Stage:
    1: confidence 0.70 → 0.65
    2: confidence 0.65 → 0.60
    3: confidence 0.60 → 0.55
    4: confidence 0.55 + min_votes 2 → 1 (최후 수단)
    
    Returns:
        새 Config 경로
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Ensemble 설정
    ensemble = config.get('ensemble', {})
    
    if stage == 1:
        ensemble['confidence_threshold'] = 0.65
        logger.info("[Light Profile] Stage 1: confidence 0.70 → 0.65")
    elif stage == 2:
        ensemble['confidence_threshold'] = 0.60
        logger.info("[Light Profile] Stage 2: confidence 0.65 → 0.60")
    elif stage == 3:
        ensemble['confidence_threshold'] = 0.55
        logger.info("[Light Profile] Stage 3: confidence 0.60 → 0.55")
    elif stage == 4:
        ensemble['confidence_threshold'] = 0.55
        ensemble['min_votes'] = 1
        logger.warning("[Light Profile] Stage 4 (최후 수단): confidence 0.55 + min_votes 2→1")
    
    config['ensemble'] = ensemble
    
    # 새 config 저장
    light_config = config_path.parent / f"phase35_3_iter13_light_stage{stage}.yaml"
    with open(light_config, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
    
    logger.info(f"✅ Light Profile Stage {stage} saved: {light_config}")
    return light_config


def main():
    parser = argparse.ArgumentParser(description="PHASE35-3 ITER13: Signal Window Finder")
    parser.add_argument("--year", type=int, default=2024, help="Target year")
    parser.add_argument("--max-windows", type=int, default=30, help="Max number of windows to scan")
    parser.add_argument("--window-days", type=int, default=30, help="Window size in days")
    parser.add_argument("--step-days", type=int, default=7, help="Sampling step in days")
    parser.add_argument("--config", type=str, default="configs/phase35/phase35_2_iter3_ssot.yaml", help="Base config path")
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("PHASE35-3 ITER13: Signal Window Finder + DecisionTrace Analyzer")
    logger.info("=" * 80)
    logger.info(f"Target Year: {args.year}")
    logger.info(f"Max Windows: {args.max_windows}")
    logger.info(f"Window Size: {args.window_days} days")
    logger.info(f"Step: {args.step_days} days")
    logger.info(f"Base Config: {args.config}")
    
    # Output 디렉토리 생성
    output_dir = project_root / "artifacts" / "phase35" / "iter13"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Config 경로
    config_path = project_root / args.config
    if not config_path.exists():
        logger.error(f"❌ Config not found: {config_path}")
        return 1
    
    # 1. Window 후보 생성
    windows = generate_window_candidates(
        year=args.year,
        window_days=args.window_days,
        step_days=args.step_days,
        max_windows=args.max_windows
    )
    
    # 2. 빠른 스캔 실행
    logger.info("=" * 80)
    logger.info("🔄 Quick Scan 실행 중...")
    logger.info("=" * 80)
    
    scan_results = []
    for i, (start_date, end_date) in enumerate(windows, 1):
        logger.info(f"[{i}/{len(windows)}] Scanning {start_date} → {end_date}")
        result = run_quick_scan(start_date, end_date, config_path)
        scan_results.append(result)
        logger.info(f"  → Trades: {result['trades']}, Runtime: {result['runtime_ms']:.0f}ms")
    
    # 3. DecisionTrace 분석
    logger.info("=" * 80)
    logger.info("📊 DecisionTrace Analysis")
    logger.info("=" * 80)
    
    analysis = analyze_blocked_reasons(scan_results)
    
    logger.info(f"Total Windows: {analysis['total_windows']}")
    logger.info(f"  - trades>0: {analysis['trades_gt0_windows']}")
    logger.info(f"  - trades=0: {analysis['trades_eq0_windows']}")
    logger.info(f"Total Blocks: {analysis['total_blocks']}")
    logger.info(f"Avg Runtime: {analysis['avg_runtime_ms']:.0f}ms")
    logger.info("")
    logger.info("Top Blocked Reasons:")
    for i, reason_info in enumerate(analysis['blocked_reasons_topN'][:5], 1):
        logger.info(f"  {i}. {reason_info['reason']}: {reason_info['count']} ({reason_info['pct']*100:.1f}%)")
    
    # 4. Best Window 선정
    best_window = select_best_window(scan_results)
    
    if best_window:
        logger.info("=" * 80)
        logger.info("✅ Best Window Found")
        logger.info("=" * 80)
        logger.info(f"Date Range: {best_window['start_date']} → {best_window['end_date']}")
        logger.info(f"Trades: {best_window['trades']}")
        logger.info(f"Runtime: {best_window['runtime_ms']:.0f}ms")
    else:
        logger.warning("=" * 80)
        logger.warning("⚠️  No trades>0 window found - Light Profile 적용 필요")
        logger.warning("=" * 80)
        
        # Light Profile 단계 적용 (Stage 1부터)
        for stage in range(1, 5):
            logger.info(f"Trying Light Profile Stage {stage}...")
            light_config = apply_light_profile(config_path, stage)
            
            # 재스캔 (샘플 5개)
            rescan_windows = windows[:5]
            rescan_results = []
            
            for start_date, end_date in rescan_windows:
                result = run_quick_scan(start_date, end_date, light_config)
                rescan_results.append(result)
                if result['trades'] > 0:
                    logger.info(f"✅ Stage {stage}: trades={result['trades']} found in {start_date}")
                    best_window = result
                    break
            
            if best_window and best_window['trades'] > 0:
                break
    
    # 5. 결과 저장
    output = {
        'scan_metadata': {
            'year': args.year,
            'total_windows': len(windows),
            'window_days': args.window_days,
            'step_days': args.step_days,
            'scan_timestamp': datetime.now().isoformat()
        },
        'scan_results': scan_results,
        'analysis': analysis,
        'best_window': best_window,
        'recommendation': {
            'selected_start_date': best_window['start_date'] if best_window else None,
            'selected_end_date': best_window['end_date'] if best_window else None,
            'expected_trades': best_window['trades'] if best_window else 0
        }
    }
    
    output_file = output_dir / "window_scan.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 80)
    logger.info(f"✅ Output saved: {output_file}")
    logger.info("=" * 80)
    
    if best_window:
        logger.info("✅ SUCCESS: trades>0 window 확보")
        return 0
    else:
        logger.error("❌ FAIL: trades>0 window을 찾지 못함 (Light Profile Stage 4까지 시도했으나 실패)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
