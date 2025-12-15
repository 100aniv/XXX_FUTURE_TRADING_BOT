#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER5.5: Config Required Dotpaths (SSOT)
===================================================

목적:
- 엔진이 요구하는 모든 필수 키를 "한 곳에" 정의
- 런타임에서 "하나씩 발견" 방식 완전 금지
- Preflight에서 "한 번에" 검증 완료

업데이트 규칙:
- 새로운 필수 키 발견 시 이 파일에 즉시 추가
- 주석으로 "어떤 모듈에서 왜 필요한지" 명시
"""

# PHASE35-2 ITER5.5 기준 필수 dotpaths
REQUIRED_DOTPATHS = [
    # === 기본 설정 ===
    "timeframe",                    # engine.py: 캔들 timeframe
    "lookback",                     # engine.py: 지표 계산용 lookback
    "equity",                       # engine.py: 초기 자본 (initial_capital과 동일)
    "mode",                         # engine.py: backtest/paper/live 모드
    
    # === 리스크 관리 ===
    "risk.per_trade",               # position_sizer.py: 거래당 리스크 비율
    "risk.max_positions",           # portfolio_manager.py: 최대 동시 포지션 수
    
    # === 자본 관리 ===
    "capital.initial",              # position_sizer.py: 초기 자본
    
    # === 포지션 사이징 ===
    "position_sizing.min_position_value",   # position_sizer.py: 최소 포지션 크기
    "position_sizing.max_position_value",   # position_sizer.py: 최대 포지션 크기
    "position_sizing.quality_weight_min",   # position_sizer.py: 품질 가중치 최소값
    "position_sizing.quality_weight_max",   # position_sizer.py: 품질 가중치 최대값
    
    # === 포트폴리오 ===
    "portfolio.max_total_exposure",         # portfolio_manager.py: 전체 노출 한도
    "portfolio.max_strategy_positions",     # portfolio_manager.py: 전략별 포지션 수
    
    # === 레버리지 ===
    "leverage.max",                 # position_sizer.py: 최대 레버리지
    
    # === 전략 ===
    "strategy",                     # engine.py: 전략 설정 (dict)
    
    # === 백테스트 ===
    "backtest.output_file",         # engine.py: 리포트 출력 경로 (Preflight에서 설정)
]

# 옵션: 경고만 출력할 권장 키 (현재는 비어있음, 필요 시 추가)
RECOMMENDED_DOTPATHS = [
    # "execution.fees_bps",         # engine.py: 수수료 (fallback 있음)
    # "execution.slippage.bps",     # engine.py: 슬리피지 (fallback 있음)
]
