#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Validation Module (PHASE8)
==================================
설정 검증 및 충돌 감지

병합 순서: base.yml → modes/{mode}.yml → active/current.yml → CLI/ENV
"""
from typing import Dict, Any, List
from .logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class ConfigValidationError(Exception):
    """설정 검증 오류"""
    pass


def validate_config(cfg: Dict[str, Any]) -> bool:
    """
    설정 검증
    
    Args:
        cfg: 병합된 설정 딕셔너리
    
    Returns:
        bool: 검증 성공 여부
    
    Raises:
        ConfigValidationError: 검증 실패 시
    """
    errors = []
    warnings = []
    
    # ============================================
    # 1. 필수 섹션 존재 확인
    # ============================================
    required_sections = ['execution', 'risk', 'strategies']
    for section in required_sections:
        if section not in cfg:
            errors.append(f"필수 섹션 누락: '{section}'")
    
    # ============================================
    # 2. execution 섹션 검증
    # ============================================
    if 'execution' in cfg:
        exec_cfg = cfg['execution']
        
        # fill_policy 검증
        if 'fill_policy' in exec_cfg:
            valid_policies = ['market', 'limit', 'next_open', 'aggressive']
            if exec_cfg['fill_policy'] not in valid_policies:
                errors.append(f"유효하지 않은 fill_policy: '{exec_cfg['fill_policy']}' (허용: {valid_policies})")
        
        # fees_bps 검증
        if 'fees_bps' in exec_cfg:
            fees = exec_cfg['fees_bps']
            if not isinstance(fees, (int, float)) or fees < 0:
                errors.append(f"fees_bps는 0 이상이어야 함: {fees}")
        
        # slippage 검증
        if 'slippage' in exec_cfg:
            slip_cfg = exec_cfg['slippage']
            if isinstance(slip_cfg, dict):
                if 'type' in slip_cfg:
                    valid_types = ['fixed', 'dynamic', 'none']
                    if slip_cfg['type'] not in valid_types:
                        errors.append(f"유효하지 않은 slippage.type: '{slip_cfg['type']}' (허용: {valid_types})")
                
                if 'bps' in slip_cfg:
                    bps = slip_cfg['bps']
                    if not isinstance(bps, (int, float)) or bps < 0:
                        errors.append(f"slippage.bps는 0 이상이어야 함: {bps}")
        
        # cooldown_minutes 검증
        if 'cooldown_minutes' in exec_cfg:
            cd = exec_cfg['cooldown_minutes']
            if not isinstance(cd, (int, float)) or cd < 0:
                errors.append(f"cooldown_minutes는 0 이상이어야 함: {cd}")
    
    # ============================================
    # 3. risk 섹션 검증
    # ============================================
    if 'risk' in cfg:
        risk_cfg = cfg['risk']
        
        # flash_guard 검증
        if 'flash_guard' in risk_cfg:
            if not isinstance(risk_cfg['flash_guard'], bool):
                errors.append(f"flash_guard는 boolean이어야 함: {risk_cfg['flash_guard']}")
        
        # stop_outlier 검증
        if 'stop_outlier' in risk_cfg:
            if not isinstance(risk_cfg['stop_outlier'], bool):
                errors.append(f"stop_outlier는 boolean이어야 함: {risk_cfg['stop_outlier']}")
    
    # ============================================
    # 4. strategies 섹션 검증
    # ============================================
    if 'strategies' in cfg:
        strategies = cfg['strategies']
        if not isinstance(strategies, dict):
            errors.append("strategies는 딕셔너리여야 함")
        elif len(strategies) == 0:
            warnings.append("strategies가 비어있음")
    
    # ============================================
    # 5. ensemble.* vs strategies.ensemble.* 충돌 검사
    # ============================================
    has_ensemble_top = 'ensemble' in cfg
    has_ensemble_in_strategies = 'strategies' in cfg and 'ensemble' in cfg.get('strategies', {})
    
    if has_ensemble_top and has_ensemble_in_strategies:
        errors.append(
            "충돌: 'ensemble' 키가 최상위와 'strategies.ensemble'에 동시 존재. "
            "하나만 사용해야 함."
        )
    
    # ============================================
    # 6. mode 검증
    # ============================================
    if 'mode' in cfg:
        valid_modes = ['backtest', 'backtest_clean', 'paper', 'live']
        if cfg['mode'] not in valid_modes:
            warnings.append(f"알 수 없는 mode: '{cfg['mode']}' (권장: {valid_modes})")
    
    # ============================================
    # 결과 처리
    # ============================================
    
    # 경고 출력
    for warning in warnings:
        logger.warning(f"⚠️  [CONFIG] {warning}")
    
    # 오류 처리
    if errors:
        error_msg = "\n".join([f"  - {e}" for e in errors])
        logger.error(f"❌ [CONFIG] 검증 실패:\n{error_msg}")
        raise ConfigValidationError(f"설정 검증 실패 ({len(errors)}개 오류)")
    
    logger.info(f"✅ [CONFIG] 검증 성공 ({len(warnings)}개 경고)")
    return True


def check_required_keys(cfg: Dict[str, Any], keys: List[str], section: str = "") -> List[str]:
    """
    필수 키 존재 확인
    
    Args:
        cfg: 설정 딕셔너리
        keys: 필수 키 목록
        section: 섹션 이름 (로그용)
    
    Returns:
        List[str]: 누락된 키 목록
    """
    missing = []
    for key in keys:
        if key not in cfg:
            missing.append(key)
    
    if missing:
        section_str = f" ({section})" if section else ""
        logger.warning(f"⚠️  [CONFIG] 누락된 키{section_str}: {', '.join(missing)}")
    
    return missing
