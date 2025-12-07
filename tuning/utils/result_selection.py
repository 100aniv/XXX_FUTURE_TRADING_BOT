#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top-N Result Selection Utility
===============================
PHASE28-4: Bayesian Search에서 사용할 Top-N 후보 추출 로직

주요 기능:
1. PHASE28-3 results.json에서 trials 로드
2. 필터링 (최소 거래 수, MaxDD 임계)
3. 스코어링 (Sharpe Ratio, PnL, 거래 수, MaxDD 종합)
4. 디듀플리케이션 (유사 파라미터 제거)
5. Top-N 선정
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


def calculate_score(trial: Dict[str, Any], min_trades: int = 10) -> float:
    """
    Trial 점수 계산
    
    Args:
        trial: Trial 데이터 (trade_count, pnl, sharpe_ratio, max_drawdown 포함)
        min_trades: 최소 거래 수 기준
    
    Returns:
        float: 종합 점수 (높을수록 좋음)
    """
    # Base score: Sharpe Ratio (Primary)
    base_score = trial.get('sharpe_ratio', 0.0) * 10.0
    
    # Bonus: Positive PnL
    pnl = trial.get('pnl', 0.0)
    if pnl > 0:
        base_score += pnl * 0.1
    
    # Penalty: 거래 수 부족
    trade_count = trial.get('trade_count', 0)
    if trade_count < min_trades:
        base_score -= (min_trades - trade_count) * 0.5
    
    # Penalty: 과도한 MaxDD
    max_dd = trial.get('max_drawdown', 0.0)
    if max_dd < -15.0:  # MaxDD % 기준 (예: -15% 이하)
        base_score -= (abs(max_dd) - 15.0) * 0.2
    
    return base_score


def is_similar_params(params1: Dict[str, Any], params2: Dict[str, Any]) -> bool:
    """
    두 파라미터 세트가 유사한지 판단
    
    핵심 파라미터 기준:
    - int: ±2 이내
    - float: ±0.2 이내
    
    Args:
        params1: 파라미터 세트 1
        params2: 파라미터 세트 2
    
    Returns:
        bool: 유사하면 True
    """
    # 핵심 파라미터 (RSI, BB, Risk)
    key_params = [
        'rsi_long_threshold',
        'rsi_short_threshold',
        'bb_std_main',
        'bb_std_strong',
        'atr_mult_sl',
        'rr'
    ]
    
    for param_name in key_params:
        val1 = params1.get(param_name)
        val2 = params2.get(param_name)
        
        if val1 is None or val2 is None:
            continue
        
        # Int 파라미터
        if isinstance(val1, int) and isinstance(val2, int):
            if abs(val1 - val2) > 2:
                return False
        
        # Float 파라미터
        if isinstance(val1, float) and isinstance(val2, float):
            if abs(val1 - val2) > 0.2:
                return False
    
    return True


def deduplicate_trials(trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    유사한 파라미터 세트 제거 (각 클러스터에서 최고 점수만 유지)
    
    Args:
        trials: Trial 리스트 (score 필드 포함)
    
    Returns:
        List[Dict[str, Any]]: 디듀플리케이션된 trial 리스트
    """
    if not trials:
        return []
    
    # Score 기준 내림차순 정렬
    sorted_trials = sorted(trials, key=lambda t: t['score'], reverse=True)
    
    unique_trials = []
    for trial in sorted_trials:
        # 이미 선택된 trial과 유사한지 확인
        is_duplicate = False
        for selected in unique_trials:
            if is_similar_params(trial.get('params', {}), selected.get('params', {})):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_trials.append(trial)
    
    return unique_trials


def select_top_n_candidates(
    results_json_path: str,
    top_n: int = 5,
    min_trades: int = 5,
    max_drawdown_threshold: float = -20.0
) -> List[Dict[str, Any]]:
    """
    PHASE28-3 results.json에서 Top-N 후보 추출
    
    Args:
        results_json_path: results.json 파일 경로
        top_n: 상위 N개 선정
        min_trades: 최소 거래 수 필터
        max_drawdown_threshold: MaxDD 임계 (% 단위, 예: -20.0 = -20%)
    
    Returns:
        List[Dict[str, Any]]: Top-N 후보 리스트
    
    Raises:
        FileNotFoundError: JSON 파일이 없을 경우
        ValueError: JSON 형식이 잘못된 경우
    """
    # JSON 로드
    json_path = Path(results_json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Results JSON not found: {results_json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Trials 추출
    trials = data.get('passed_trials', [])
    if not trials:
        return []
    
    # 1단계: 필터링
    filtered_trials = []
    for trial in trials:
        # 최소 거래 수
        if trial.get('trade_count', 0) < min_trades:
            continue
        
        # MaxDD 임계
        if trial.get('max_drawdown', 0.0) < max_drawdown_threshold:
            continue
        
        filtered_trials.append(trial)
    
    if not filtered_trials:
        return []
    
    # 2단계: 스코어링
    for trial in filtered_trials:
        trial['score'] = calculate_score(trial, min_trades=10)  # 내부적으로 더 높은 기준 사용
    
    # 3단계: 디듀플리케이션
    unique_trials = deduplicate_trials(filtered_trials)
    
    # 4단계: Top-N 선정
    top_n_trials = unique_trials[:top_n]
    
    return top_n_trials


if __name__ == '__main__':
    # Quick test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python result_selection.py <results_json_path>")
        sys.exit(1)
    
    results_path = sys.argv[1]
    candidates = select_top_n_candidates(results_path, top_n=5)
    
    print(f"\n{'='*80}")
    print(f"Top-{len(candidates)} Candidates")
    print(f"{'='*80}")
    for i, candidate in enumerate(candidates, 1):
        print(f"\n[{i}] Job: {candidate.get('job_id', 'N/A')}")
        print(f"    Sharpe: {candidate.get('sharpe_ratio', 0.0):.4f}")
        print(f"    PnL: {candidate.get('pnl', 0.0):.2f}")
        print(f"    Trades: {candidate.get('trade_count', 0)}")
        print(f"    Score: {candidate.get('score', 0.0):.2f}")
