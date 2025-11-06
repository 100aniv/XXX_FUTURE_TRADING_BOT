#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensemble Strategy (Portfolio Manager)
======================================
여러 전략 신호를 통합하여 최종 거래 결정 생성

핵심 기능:
- 전략별 성과 메트릭 기반 가중치 계산
- 레짐 적합도 평가  
- 신호 통합 및 최종 결정
- DB 저장 (trading.decisions)

참고: docs/strategy/ENSEMBLE_ARCHITECTURE.md
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from psycopg2.extras import Json, RealDictCursor
from uuid import uuid4


# ============================================
# CONFIG 제거 (config.yml 사용)
# ============================================
# 모든 설정은 config['strategy']['ensemble']에서 읽음


# ============================================
# PERFORMANCE METRICS (성과 메트릭 로드)
# ============================================

def load_strategy_performance(conn, window_days: int = 30) -> Dict[str, Dict[str, float]]:
    """
    최근 N일 전략별 성과 메트릭 로드
    
    Args:
        conn: DB 연결
        window_days: 성과 추적 기간 (일)
    
    Returns:
        { 'trend': {'winrate': 0.55, 'rr_mean': 1.2, 'sharpe': 0.8, ...}, ... }
    """
    sql = """
    SELECT 
        strategy_id,
        COUNT(*) as total_trades,
        AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) as winrate,
        AVG(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) / NULLIF(AVG(CASE WHEN pnl < 0 THEN -pnl ELSE 0 END), 0) as profit_factor,
        AVG(pnl_pct) as avg_pnl_pct,
        STDDEV(pnl_pct) as stddev_pnl_pct,
        SUM(pnl) as total_pnl
    FROM trading.trades
    WHERE ts_open >= NOW() - INTERVAL '%s days'
      AND status = 'CLOSED'
    GROUP BY strategy_id
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (window_days,))
            rows = cur.fetchall()
            
            perf = {}
            for row in rows:
                strategy_id = row['strategy_id']
                
                # 샤프 비율 계산
                sharpe = 0.0
                if row['stddev_pnl_pct'] and row['stddev_pnl_pct'] > 0:
                    sharpe = row['avg_pnl_pct'] / row['stddev_pnl_pct']
                
                perf[strategy_id] = {
                    'winrate': row['winrate'] or 0.0,
                    'profit_factor': row['profit_factor'] or 1.0,
                    'rr_mean': row['profit_factor'] or 1.0,
                    'sharpe': sharpe,
                    'total_trades': row['total_trades'] or 0,
                    'total_pnl': row['total_pnl'] or 0.0,
                }
            
            # 초기값 (거래 없는 전략) - 하드코딩 제거
            from . import get_all_strategies
            all_strats = get_all_strategies()
            
            for strategy_id in all_strats.keys():
                if strategy_id not in perf:
                    perf[strategy_id] = {
                        'winrate': 0.5,
                        'profit_factor': 1.0,
                        'rr_mean': 1.0,
                        'sharpe': 0.0,
                        'total_trades': 0,
                        'total_pnl': 0.0,
                    }
            
            return perf
    
    except Exception as e:
        # 기본값 반환 - 하드코딩 제거
        from . import get_all_strategies
        all_strats = get_all_strategies()
        
        default_perf = {'winrate': 0.5, 'rr_mean': 1.0, 'sharpe': 0.0, 'total_trades': 0, 'total_pnl': 0.0}
        return {strategy_id: default_perf.copy() for strategy_id in all_strats.keys()}


# ============================================
# SIGNAL COLLECTION (신호 수집)
# ============================================

def collect_signals(conn, symbol: str, timeframe: str, candle_closed_at: datetime, window_sec: int = 10) -> List[Dict]:
    """
    특정 캔들 시각 기준 ±window 내 신호 수집
    
    Args:
        conn: DB 연결
        symbol: 심볼
        timeframe: 타임프레임
        candle_closed_at: 캔들 종가 시각
        window_sec: 신호 수집 윈도우 (초)
    """
    window = timedelta(seconds=window_sec)
    start_time = candle_closed_at - window
    end_time = candle_closed_at + window
    
    sql = """
    SELECT 
        signal_id, strategy_id, symbol, timeframe, direction,
        entry_price, sl_price, tp_price, confidence, features,
        candle_closed_at, created_at
    FROM monitoring.signals
    WHERE symbol = %s
      AND timeframe = %s
      AND candle_closed_at BETWEEN %s AND %s
    ORDER BY created_at DESC
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (symbol, timeframe, start_time, end_time))
            rows = cur.fetchall()
            
            signals = []
            for row in rows:
                sig = dict(row)
                # JSONB 파싱
                if sig['features']:
                    sig['features'] = dict(sig['features'])
                signals.append(sig)
            
            return signals
    
    except Exception as e:
        return []


# ============================================
# STANDARDIZATION (표준화)
# ============================================

def standardize(values: List[float]) -> List[float]:
    """
    Z-score 표준화 (평균 0, 표준편차 1)
    """
    if len(values) == 0:
        return []
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    stddev = variance ** 0.5
    
    if stddev == 0:
        return [0.0] * len(values)
    
    return [(x - mean) / stddev for x in values]


# ============================================
# REGIME FIT (레짐 적합도)
# ============================================

def calc_regime_fit(strategy_id: str, features: Dict) -> float:
    """
    시장 레짐에 대한 전략 적합도 (0~1)
    """
    if not features:
        return 0.5
    
    regime = features.get('regime', '중립')
    atr_pct = features.get('atr_pct', 0.0)
    
    # 변동성 기준
    volatility_score = min(atr_pct / 0.03, 1.0)
    
    # 전략별 적합도
    if strategy_id == 'trend':
        if regime in ('상승장', '하락장'):
            return 0.8 * (1.0 - volatility_score * 0.5)
        return 0.4
    
    elif strategy_id == 'reversion':
        if regime == '횡보장':
            return 0.8
        elif regime in ('상승장', '하락장'):
            return 0.6
        return 0.5
    
    elif strategy_id == 'breakout':
        return volatility_score
    
    elif strategy_id == 'scalping':
        if regime == '횡보장':
            return 0.7 * (1.0 - volatility_score * 0.3)
        return 0.5 * (1.0 - volatility_score * 0.5)
    
    elif strategy_id == 'daytrade':
        mid_vol = 1.0 - abs(volatility_score - 0.5) * 2
        return 0.6 + 0.2 * mid_vol
    
    elif strategy_id == 'swing':
        if regime in ('상승장', '하락장'):
            return 0.75 * (0.5 + volatility_score * 0.5)
        return 0.4
    
    return 0.5


# ============================================
# EXPERIENCE SCORE (경험 점수)
# ============================================

def calculate_experience_score(strategy_id: str, perf: Dict[str, Dict], config: dict) -> float:
    """
    전략의 Experience Score 계산
    
    Experience Score = 데이터 충분성 * 최근 성과 * 안정성
    
    Args:
        strategy_id: 전략 ID
        perf: 성과 메트릭
        config: 설정 (ensemble.experience 파라미터)
    
    Returns:
        Experience Score (0~1)
    """
    if strategy_id not in perf:
        return 0.3  # 기본값 (낮은 신뢰도)
    
    p = perf[strategy_id]
    ens_cfg = config.get('ensemble', {})
    exp_cfg = ens_cfg.get('experience', {})
    
    # 1. 데이터 충분성 (Sample Size Factor)
    min_trades = exp_cfg.get('min_trades', 20)
    total_trades = p.get('total_trades', 0)
    
    if total_trades < min_trades:
        # 부족한 경우 페널티
        data_sufficiency = total_trades / min_trades
    else:
        # 충분한 경우 포화
        data_sufficiency = min(1.0, 1.0 + 0.1 * ((total_trades - min_trades) / min_trades))
    
    # 2. 최근 성과 (Recent Performance)
    winrate = p.get('winrate', 0.5)
    profit_factor = p.get('profit_factor', 1.0)
    
    # 승률 기반 점수 (0.5 기준)
    winrate_score = (winrate - 0.5) * 2  # -1 ~ 1
    winrate_score = max(0, min(1, 0.5 + winrate_score * 0.5))  # 0 ~ 1
    
    # Profit Factor 기반 점수 (1.0 기준)
    pf_score = min(1.0, profit_factor / 2.0)  # 2.0 이상이면 1.0
    
    recent_performance = (winrate_score + pf_score) / 2
    
    # 3. 안정성 (Stability)
    sharpe = p.get('sharpe', 0.0)
    
    # Sharpe 기반 안정성 (0.5 이상이면 좋음)
    if sharpe >= 0.5:
        stability = min(1.0, sharpe / 1.5)
    else:
        stability = max(0.3, sharpe / 0.5 * 0.7 + 0.3)
    
    # 최종 Experience Score
    exp_score = (
        data_sufficiency * 0.4 +
        recent_performance * 0.4 +
        stability * 0.2
    )
    
    # 0.1 ~ 1.0 범위로 클램핑
    exp_score = max(0.1, min(1.0, exp_score))
    
    return exp_score


# ============================================
# WEIGHT CALCULATION (가중치 계산)
# ============================================

def calculate_weights(signals: List[Dict], perf: Dict[str, Dict], config: dict) -> Dict[str, float]:
    """
    각 전략의 가중치 계산
    
    Args:
        signals: 신호 리스트
        perf: 성과 메트릭
        config: 설정 (ensemble 파라미터)
    
    Returns:
        전략별 가중치
    
    공식: α*승률 + β*RR + γ*샤프 + δ*신뢰도 + ε*레짐 + 기본가중치*0.1
    """
    if not signals:
        return {}
    
    # 전략 목록
    strategy_ids = list(set(s['strategy_id'] for s in signals))
    
    # 성과 메트릭 추출
    winrates = [perf.get(sid, {}).get('winrate', 0.5) for sid in strategy_ids]
    rr_means = [perf.get(sid, {}).get('rr_mean', 1.0) for sid in strategy_ids]
    sharpes = [perf.get(sid, {}).get('sharpe', 0.0) for sid in strategy_ids]
    
    # 표준화
    z_winrates = standardize(winrates)
    z_rr_means = standardize(rr_means)
    z_sharpes = standardize(sharpes)
    
    # 신호별 가중치 계산
    weights = {}
    raw_weights = []
    
    ens_cfg = config.get('ensemble', {})
    max_weight_per_strategy = ens_cfg.get('max_weight_per_strategy', 0.4)
    
    for i, sid in enumerate(strategy_ids):
        # 해당 전략의 신호 찾기
        sig = next((s for s in signals if s['strategy_id'] == sid), None)
        
        if not sig:
            weights[sid] = 0.0
            raw_weights.append(0.0)
            continue
        
        # ⭐ PR10: Experience Score 적용
        exp_score = calculate_experience_score(sid, perf, config)
        
        # 신뢰도
        confidence = float(sig.get('confidence', 0.5))
        
        # 레짐 적합도
        regime_fit = calc_regime_fit(sid, sig.get('features', {}))
        
        # 점수 계산 (기존 공식)
        raw_weight = (
            ens_cfg.get('alpha_winrate', 0.4) * z_winrates[i] +
            ens_cfg.get('beta_rr', 0.2) * z_rr_means[i] +
            ens_cfg.get('gamma_sharpe', 0.2) * z_sharpes[i] +
            ens_cfg.get('delta_confidence', 0.15) * confidence +
            ens_cfg.get('epsilon_regime', 0.05) * regime_fit
        )
        
        # 기본 가중치 추가
        weights_cfg = ens_cfg.get('weights', {})
        base_weight = weights_cfg.get(sid, 2.0)
        raw_weight += base_weight * 0.1
        
        # ⭐ PR10: Experience Score 곱하기 (데이터 부족 시 페널티)
        raw_weight = raw_weight * exp_score
        
        raw_weights.append(max(0.0, raw_weight))
    
    # 정규화
    total = sum(raw_weights)
    if total > 0:
        for i, sid in enumerate(strategy_ids):
            normalized_weight = raw_weights[i] / total
            
            # ⭐ PR10: 클램핑 (max_weight_per_strategy)
            weights[sid] = min(normalized_weight, max_weight_per_strategy)
    else:
        for sid in strategy_ids:
            weights[sid] = 1.0 / len(strategy_ids)
    
    # ⭐ PR10: 클램핑 후 재정규화
    total_after_clamp = sum(weights.values())
    if total_after_clamp > 0 and total_after_clamp != 1.0:
        for sid in weights:
            weights[sid] = weights[sid] / total_after_clamp
    
    return weights


# ============================================
# ENSEMBLE SCORE (통합 점수 계산)
# ============================================

def calculate_ensemble_score(signals: List[Dict], weights: Dict[str, float], config: dict) -> Tuple[str, float, Dict]:
    """
    통합 점수 계산
    
    Args:
        signals: 신호 리스트
        weights: 전략별 가중치
        config: 설정 (ensemble 파라미터)
    
    Returns:
        (chosen_side, score, details)
    """
    side_scores = {'LONG': 0.0, 'SHORT': 0.0, 'FLAT': 0.0}
    
    for sig in signals:
        strategy_id = sig['strategy_id']
        side = sig.get('side', 'FLAT')
        weight = weights.get(strategy_id, 0.0)
        
        if side in side_scores:
            side_scores[side] += weight
    
    # 최종 점수 = LONG - SHORT
    score = side_scores['LONG'] - side_scores['SHORT']
    
    # 의사결정
    ens_cfg = config.get('ensemble', {})
    theta_long = ens_cfg.get('theta_long', 0.15)
    theta_short = ens_cfg.get('theta_short', 0.15)
    
    if score >= theta_long:
        chosen_side = 'LONG'
    elif score <= -theta_short:
        chosen_side = 'SHORT'
    else:
        chosen_side = 'FLAT'
    
    details = {
        'side_scores': side_scores,
        'final_score': score,
        'theta_long': theta_long,
        'theta_short': theta_short,
    }
    
    return chosen_side, score, details


# ============================================
# BONUSES/PENALTIES (보너스/패널티)
# ============================================

def apply_bonuses(signals: List[Dict], score: float, chosen_side: str, config: dict) -> float:
    """
    추가 보너스/패널티 적용
    
    Args:
        signals: 신호 리스트
        score: 현재 점수
        chosen_side: 선택된 방향
        config: 설정 (ensemble 파라미터)
    
    Returns:
        보정된 점수
    """
    adjusted_score = score
    ens_cfg = config.get('ensemble', {})
    
    # 1. 합의 보너스
    same_direction_count = sum(1 for s in signals if s.get('side') == chosen_side)
    if same_direction_count >= 2:
        consensus_adjustment = ens_cfg.get('consensus_bonus', 0.2)
        adjusted_score += consensus_adjustment if chosen_side == 'LONG' else -consensus_adjustment
    
    # 2. RR 보너스
    rr_bonus_threshold = ens_cfg.get('rr_bonus_threshold', 1.6)
    high_rr_count = sum(1 for s in signals 
                        if s.get('side') == chosen_side 
                        and s.get('tp', 0) > 0 
                        and s.get('sl', 0) > 0
                        and s.get('entry', 0) != s.get('sl', 0)
                        and abs(s['tp'] - s['entry']) / abs(s['entry'] - s['sl']) >= rr_bonus_threshold)
    
    if high_rr_count > 0:
        rr_adjustment = ens_cfg.get('rr_bonus', 0.2) * high_rr_count
        adjusted_score += rr_adjustment if chosen_side == 'LONG' else -rr_adjustment
    
    return adjusted_score


# ============================================
# SAVE DECISION (결정 저장)
# ============================================

def save_decision(conn, symbol: str, timeframe: str, candle_closed_at: datetime,
                  chosen_side: str, score: float, weights: Dict, from_signals: List[str], reason: str,
                  entry_price: float = None, sl_price: float = None, tp_price: float = None) -> bool:
    """
    통합 결정 저장 (멱등성 보장)
    """
    decision_id = str(uuid4())
    chosen_size = abs(score)
    
    sql = """
    INSERT INTO trading.decisions (
        decision_id, symbol, timeframe, candle_closed_at,
        chosen_side, chosen_size, score, weights, from_signals, reason,
        entry_price, sl_price, tp_price
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (symbol, timeframe, candle_closed_at)
    DO NOTHING
    RETURNING decision_id;
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                decision_id, symbol, timeframe, candle_closed_at,
                chosen_side, chosen_size, score,
                Json(weights), Json(from_signals), reason,
                entry_price, sl_price, tp_price
            ))
            result = cur.fetchone()
            conn.commit()
            
            return result is not None
    
    except Exception as e:
        conn.rollback()
        return False


# ============================================
# MAIN PROCESSING (메인 처리 함수)
# ============================================

def process_pending_signals(conn, logger=None):
    """
    미처리 신호 처리
    
    Args:
        conn: DB 연결
        logger: 로거 (선택)
    """
    # 1. 성과 메트릭 로드
    perf = load_strategy_performance(conn)
    
    # 2. 최근 신호 조회
    sql = """
    SELECT DISTINCT symbol, timeframe, candle_closed_at
    FROM monitoring.signals
    WHERE created_at >= NOW() - INTERVAL '1 minute'
      AND NOT EXISTS (
          SELECT 1 FROM trading.decisions d
          WHERE d.symbol = monitoring.signals.symbol
            AND d.timeframe = monitoring.signals.timeframe
            AND d.candle_closed_at = monitoring.signals.candle_closed_at
      )
    ORDER BY candle_closed_at DESC
    LIMIT 10
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            pending = cur.fetchall()
            
            if not pending:
                return
            
            if logger:
                logger.info(f"📥 미처리 신호 {len(pending)}건 발견")
            
            for row in pending:
                symbol = row['symbol']
                timeframe = row['timeframe']
                candle_closed_at = row['candle_closed_at']
                
                # 3. 신호 수집
                signals = fetch_recent_signals(conn, symbol, timeframe, candle_closed_at)
                
                if not signals:
                    continue
                
                # 4. 가중치 계산
                weights = calculate_weights(signals, perf)
                
                # 5. 통합 점수 계산
                chosen_side, score, details = calculate_ensemble_score(signals, weights)
                
                # 6. 보너스 적용
                adjusted_score = apply_bonuses(signals, score, chosen_side)
                
                # 7. entry/sl/tp 계산 (chosen_side와 일치하는 신호들의 가중 평균)
                relevant_signals = [s for s in signals if s.get('direction') == chosen_side]
                
                if relevant_signals:
                    # 가중치 합
                    total_weight = sum(weights.get(s['strategy_id'], 0) for s in relevant_signals)
                    
                    if total_weight > 0:
                        # 가중 평균
                        entry_price = sum(
                            float(s.get('entry_price', 0)) * weights.get(s['strategy_id'], 0) 
                            for s in relevant_signals
                        ) / total_weight
                        
                        sl_price = sum(
                            float(s.get('sl_price', 0)) * weights.get(s['strategy_id'], 0) 
                            for s in relevant_signals
                        ) / total_weight
                        
                        tp_price = sum(
                            float(s.get('tp_price', 0)) * weights.get(s['strategy_id'], 0) 
                            for s in relevant_signals
                        ) / total_weight
                    else:
                        # 가중치가 없으면 단순 평균
                        entry_price = sum(float(s.get('entry_price', 0)) for s in relevant_signals) / len(relevant_signals)
                        sl_price = sum(float(s.get('sl_price', 0)) for s in relevant_signals) / len(relevant_signals)
                        tp_price = sum(float(s.get('tp_price', 0)) for s in relevant_signals) / len(relevant_signals)
                else:
                    entry_price = sl_price = tp_price = None
                
                # 8. 결정 저장
                from_signals = [s['signal_id'] for s in signals]
                reason = f"Ensemble: {len(signals)}개 신호 통합"
                
                save_decision(conn, symbol, timeframe, candle_closed_at,
                            chosen_side, adjusted_score, weights, from_signals, reason,
                            entry_price, sl_price, tp_price)
                
                if logger:
                    logger.info(f"✅ Decision 저장: {symbol} {chosen_side} (score={adjusted_score:.2f})")
    
    except Exception as e:
        if logger:
            logger.error(f"❌ 미처리 신호 처리 오류: {e}")
        import traceback
        traceback.print_exc()


def combine_signals(signals: List[Dict], conn, config: dict = None) -> Dict:
    """
    신호 리스트를 통합하여 최종 결정 생성
    
    Args:
        signals: 전략 신호 리스트
        conn: DB 연결
        config: 설정 (config.yml 전체, ensemble 섹션 포함)
    
    Returns:
        통합된 결정 dict
    
    Note:
        PR7-2: trading.decisions 테이블에 앙상블 결정 저장
    """
    # config 기본값 (하위 호환성)
    if config is None:
        config = {'strategy': {'ensemble': {}}}
    if not signals:
        return None
    
    # ⭐ 로깅: 받은 신호 목록
    import logging
    logger = logging.getLogger(__name__)
    
    signal_summary = []
    for s in signals:
        signal_summary.append(f"{s.get('strategy_id', 'unknown')}:{s.get('side', 'FLAT')}")
    
    logger.info(f"📊 [ENSEMBLE] 신호 수신: {len(signals)}개 - {', '.join(signal_summary)}")
    
    # ⭐ PR9: 고급 버전 활성화 (성과 기반 가중치)
    
    # 1. 전략 성과 로드 (최근 30일)
    try:
        perf = load_strategy_performance(conn, window_days=30)
        logger.debug(f"📈 [ENSEMBLE] 전략 성과 로드 완료: {len(perf)}개 전략")
    except Exception as e:
        logger.warning(f"⚠️ [ENSEMBLE] 성과 로드 실패, 기본값 사용: {e}")
        perf = {}
        for s in signals:
            sid = s.get('strategy_id', 'unknown')
            if sid not in perf:
                perf[sid] = {'winrate': 0.5, 'rr_mean': 1.0, 'sharpe': 0.0, 'total_trades': 0}
    
    # 2. 가중치 계산 (성과 기반)
    try:
        weights = calculate_weights(signals, perf, config)
        logger.debug(f"⚖️  [ENSEMBLE] 가중치 계산 완료")
    except Exception as e:
        logger.warning(f"⚠️ [ENSEMBLE] 가중치 계산 실패, 동일 가중치 사용: {e}")
        n = len(signals)
        weights = {s.get('strategy_id', 'unknown'): 1.0 / n for s in signals}
    
    # 3. 통합 점수 계산
    try:
        chosen_side, score, details = calculate_ensemble_score(signals, weights, config)
        logger.debug(f"📊 [ENSEMBLE] 통합 점수: {score:.3f}")
    except Exception as e:
        logger.warning(f"⚠️ [ENSEMBLE] 점수 계산 실패, 다수결 사용: {e}")
        # Fallback: 다수결
        long_count = sum(1 for s in signals if s.get('side') == 'LONG')
        short_count = sum(1 for s in signals if s.get('side') == 'SHORT')
        if long_count > short_count:
            chosen_side = 'LONG'
        elif short_count > long_count:
            chosen_side = 'SHORT'
        else:
            logger.info(f"⚖️  [ENSEMBLE] 동점으로 거래 보류")
            return None
        score = long_count - short_count
        details = {}
    
    # 4. 보너스/패널티 적용
    try:
        final_score = apply_bonuses(signals, score, chosen_side, config)
        logger.debug(f"🎁 [ENSEMBLE] 보너스 적용 후: {final_score:.3f}")
    except Exception as e:
        logger.warning(f"⚠️ [ENSEMBLE] 보너스 적용 실패: {e}")
        final_score = score
    
    # 5. 선택된 방향의 신호 필터링
    relevant = [s for s in signals if s.get('side') == chosen_side]
    
    if not relevant:
        logger.warning(f"⚠️ [ENSEMBLE] 선택된 방향 ({chosen_side}) 신호 없음")
        return None
    
    # 6. 로깅: 투표 결과 및 가중치
    long_count = sum(1 for s in signals if s.get('side') == 'LONG')
    short_count = sum(1 for s in signals if s.get('side') == 'SHORT')
    flat_count = len(signals) - long_count - short_count
    
    logger.info(f"🗳️  [ENSEMBLE] 투표 결과: LONG {long_count}표, SHORT {short_count}표, FLAT {flat_count}표")
    
    n = len(relevant)
    strategy_names = [s.get('strategy_id', 'unknown') for s in relevant]
    
    logger.info(f"🎯 [ENSEMBLE] 선택된 방향: {chosen_side} (점수: {final_score:.3f})")
    logger.info(f"📌 [ENSEMBLE] 참여 전략 ({n}개): {', '.join(strategy_names)}")
    
    # ⭐ 실제 가중치 및 성과 로깅
    weight_info = []
    for sid in strategy_names:
        w = weights.get(sid, 0)
        p = perf.get(sid, {})
        wr = p.get('winrate', 0.5)
        weight_info.append(f"{sid}={w:.2f}(승률{wr:.1%})")
    
    logger.info(f"⚖️  [ENSEMBLE] 가중치 (성과기반): {', '.join(weight_info)}")
    
    # 가중 평균
    entry_price = sum(s.get('entry', 0) for s in relevant) / n
    sl_price = sum(s.get('sl', 0) for s in relevant) / n
    tp_price = sum(s.get('tp', 0) for s in relevant) / n
    avg_confidence = sum(s.get('confidence', 0.75) for s in relevant) / n
    
    # ⭐ 레버리지 가중 평균 (PR8: 다차원 레버리지)
    avg_leverage = sum(s.get('lev', 2) for s in relevant) / n
    avg_leverage = max(2, min(50, int(avg_leverage)))  # 2-50 범위 제한
    
    # RR 계산
    rr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if sl_price != entry_price else 0
    
    logger.info(f"💰 [ENSEMBLE] Entry: ${entry_price:.4f}, SL: ${sl_price:.4f}, TP: ${tp_price:.4f}")
    logger.info(f"📊 [ENSEMBLE] RR: {rr:.2f}R, 신뢰도: {avg_confidence:.2%}, 레버리지: {avg_leverage}x")
    
    decision = {
        'side': chosen_side,
        'entry': entry_price,
        'sl': sl_price,
        'tp': tp_price,
        'confidence': avg_confidence,
        'lev': avg_leverage,  # ⭐ 레버리지 추가
        'strategy_id': f"ensemble_{n}_signals",
        'symbol': relevant[0].get('symbol', 'UNKNOWN')
    }
    
    # ⭐ PR7-2: trading.decisions 테이블에 저장
    try:
        symbol = relevant[0].get('symbol')
        timeframe = relevant[0].get('timeframe')
        ts = relevant[0].get('ts')
        
        if symbol and timeframe and ts:
            candle_closed_at = datetime.fromtimestamp(ts / 1000)
            
            # 가중치 계산 (간단 버전: 동일 가중치)
            weights = {s['strategy_id']: 1.0 / n for s in relevant}
            
            # 참여 전략 ID 목록
            from_signals = [s['strategy_id'] for s in relevant]
            
            # 점수 계산 (신호 개수 기반)
            score = n * (1.0 if chosen_side == 'LONG' else -1.0)
            
            # 사유
            reason = f"{n}개 전략 합의 ({long_count}L/{short_count}S)"
            
            # DB 저장
            save_decision(
                conn=conn,
                symbol=symbol,
                timeframe=timeframe,
                candle_closed_at=candle_closed_at,
                chosen_side=chosen_side,
                score=score,
                weights=weights,
                from_signals=from_signals,
                reason=reason,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price
            )
    except Exception as e:
        # DB 저장 실패해도 decision은 반환 (로깅만 진행)
        import logging
        logging.warning(f"⚠️  Ensemble decision 저장 실패: {e}")
    
    return decision
