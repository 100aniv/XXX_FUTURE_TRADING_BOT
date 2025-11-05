#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUNING_VIBLE 로그 파서
=======================
- main.py 실행 로그의 TUNING_VIBLE 블록을 파싱하여 핵심 지표를 반환
- 한국어 레이블과 레이아웃 변형(줄바꿈/공백/구분선)에도 견고하게 동작

반환 필드 예시:
{
    'score_total': 79.0,
    'grade': 'A',
    'trades': 6,
    'win_rr': 1.26,
    'win_rate_pct': 33.3,
    'rr': 3.78,
    'profit_factor': 1.89,
    'roi_pct': 0.1,
    'mdd_pct': -0.2,
    'max_losing_streak': 4,
}
"""
from __future__ import annotations
import re
from typing import Dict, Any


def _norm(text: str) -> str:
    # 공백/개행/구분선 정규화
    t = re.sub(r"[\u2500-\u257F=\-\|]+", " ", text)  # 박스선/==== 제거
    t = re.sub(r"\s+", " ", t)
    return t


def parse_vible_metrics(log_text: str) -> Dict[str, Any]:
    t = _norm(log_text)

    # 기본 스켈레톤
    res: Dict[str, Any] = {
        'score_total': None,
        'grade': None,
        'trades': None,
        'win_rr': None,
        'win_rate_pct': None,
        'rr': None,
        'profit_factor': None,
        'roi_pct': None,
        'mdd_pct': None,
        'max_losing_streak': None,
    }

    # 총 거래
    m = re.search(r"총\s*거래\s*[:\s]+(\d+)\s*건", t)
    if m:
        res['trades'] = int(m.group(1))

    # 총점 (가장 마지막 '점' 숫자 캡처)
    # 예: "총점 ... 100 점 | 79.0점"
    m = None
    for mm in re.finditer(r"총점[^0-9]*(\d+(?:\.\d+)?)\s*점", t):
        m = mm
    if m:
        try:
            res['score_total'] = float(m.group(1))
        except Exception:
            pass

    # 최종 등급: 'A등급', 'S등급', 등
    m = re.search(r"최종\s*등급\s*[:\s]+[^A-Z가-힣]*([SABCDE])등급", t)
    if m:
        res['grade'] = m.group(1)

    # Profit Factor
    m = re.search(r"Profit\s*Factor[^0-9]*([0-9]+(?:\.[0-9]+)?)", t, re.IGNORECASE)
    if m:
        res['profit_factor'] = float(m.group(1))

    # ROI (% 기호 포함/부호 가능)
    m = re.search(r"ROI[^\-0-9]*([\-]?[0-9]+(?:\.[0-9]+)?)%", t, re.IGNORECASE)
    if m:
        res['roi_pct'] = float(m.group(1))

    # MDD (% 기호 포함/부호 가능)
    m = re.search(r"MDD[^\-0-9]*([\-]?[0-9]+(?:\.[0-9]+)?)%", t, re.IGNORECASE)
    if m:
        res['mdd_pct'] = float(m.group(1))

    # 연속 손실 Max
    m = re.search(r"연속\s*손실\s*Max[^0-9]*([0-9]+)", t)
    if m:
        res['max_losing_streak'] = int(m.group(1))

    # 승률 × RR (현재값)
    m = re.search(r"승률\s*[×xX]\s*RR[^0-9]*([0-9]+(?:\.[0-9]+)?)", t)
    if m:
        res['win_rr'] = float(m.group(1))

    # 승률 (%)
    # 표 형식에 따라 '승률 ... 33.3%' 가 마지막에 등장하는 경우가 많음 → 마지막 match 사용
    m_last = None
    for mm in re.finditer(r"승률[^%]*([0-9]+(?:\.[0-9]+)?)%", t):
        m_last = mm
    if m_last:
        try:
            res['win_rate_pct'] = float(m_last.group(1))
        except Exception:
            pass

    # 손익비 (RR)
    m = re.search(r"손익비\s*\(RR\)[^0-9]*([0-9]+(?:\.[0-9]+)?)", t)
    if m:
        res['rr'] = float(m.group(1))

    return res


def constraints_ok(metrics: Dict[str, Any]) -> bool:
    """하드 제약 충족 여부.
    - MDD ≥ -20%
    - Max Losing Streak ≤ 6
    - Win×RR ≥ 2.0
    - Trades ∈ [30, 80]
    값이 None이면 유효성 판단 보류(=False)
    """
    try:
        mdd = metrics.get('mdd_pct')
        streak = metrics.get('max_losing_streak')
        win_rr = metrics.get('win_rr')
        trades = metrics.get('trades')
        if None in (mdd, streak, win_rr, trades):
            return False
        if mdd < -20.0:
            return False
        if streak is not None and streak > 6:
            return False
        if win_rr < 2.0:
            return False
        if not (30 <= int(trades) <= 80):
            return False
        return True
    except Exception:
        return False


def objective_score(metrics: Dict[str, Any]) -> float:
    """목적함수 기본값: TUNING_VIBLE 총점, 없으면 대체 스코어.
    대체: profit_factor * max(0, win_rr) 를 기반으로 근사.
    """
    if metrics.get('score_total') is not None:
        return float(metrics['score_total'])
    pf = float(metrics.get('profit_factor') or 0.0)
    win_rr = float(metrics.get('win_rr') or 0.0)
    return pf * max(win_rr, 0.0) * 10.0
