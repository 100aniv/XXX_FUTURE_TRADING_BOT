#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analytics Scorecard Module (PHASE8)
====================================
단일 전략 성과 측정 및 리포트 생성

폴더 구조:
- metrics.py: 6가지 지표 계산
- generator.py: Scorecard 생성기
- writer_csv.py: CSV 저장
- writer_md.py: Markdown 저장
"""

from .metrics import calculate_metrics
from .generator import ScorecardGenerator
from .writer_csv import save_scorecard_csv
from .writer_md import save_scorecard_md

__all__ = [
    'calculate_metrics',
    'ScorecardGenerator',
    'save_scorecard_csv',
    'save_scorecard_md',
]
