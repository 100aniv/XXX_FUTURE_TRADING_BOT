#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-3: btc5m_baseline_v3 Deprecation Tests
===============================================
V3 전략이 DEPRECATED 상태로 올바르게 표시되고,
자동 로딩에서 제외되는지 검증하는 테스트

테스트 항목:
1. V3 전략 클래스에 deprecated flag 존재 확인
2. V3 전략이 단일 전략 모드에서 로드 거부되는지 확인
3. V3 전략이 앙상블 모드에서 자동 제외되는지 확인
4. Deprecated reason 메시지 확인
"""
import pytest
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from strategies.btc5m_baseline_v3 import Btc5mBaselineV3
from strategies import load_strategies


def test_v3_has_deprecated_flag():
    """
    PHASE29-3: V3 전략 클래스에 deprecated flag 존재 확인
    """
    # V3 인스턴스 생성
    config = {"timeframe": "5m", "symbol": "BTCUSDT"}
    v3_instance = Btc5mBaselineV3(config=config)
    
    # deprecated flag 확인
    assert hasattr(v3_instance, 'deprecated'), "V3 전략에 deprecated 속성이 없습니다."
    assert v3_instance.deprecated is True, "V3 전략이 deprecated=True가 아닙니다."
    
    # deprecation_reason 확인
    assert hasattr(v3_instance, 'deprecation_reason'), "V3 전략에 deprecation_reason 속성이 없습니다."
    assert isinstance(v3_instance.deprecation_reason, str), "deprecation_reason이 문자열이 아닙니다."
    assert len(v3_instance.deprecation_reason) > 0, "deprecation_reason이 비어 있습니다."
    
    print(f"✅ V3 deprecated flag 확인: {v3_instance.deprecated}")
    print(f"✅ V3 deprecation reason: {v3_instance.deprecation_reason}")


def test_v3_rejected_in_single_strategy_mode():
    """
    PHASE29-3: V3 전략이 단일 전략 모드에서 로드 거부되는지 확인
    """
    config = {
        "timeframe": "5m",
        "symbol": "BTCUSDT",
        "strategy": {
            "selector": "btc5m_baseline_v3",
            "use_ensemble": False
        },
        "strategies": {
            "btc5m_baseline_v3": {
                "adx_trend_threshold": 25
            }
        }
    }
    
    # load_strategies 호출
    strategies = load_strategies(config)
    
    # V3 전략이 로드되지 않아야 함 (deprecated로 인해 빈 딕셔너리 반환)
    assert strategies == {}, f"Deprecated 전략이 로드되었습니다: {list(strategies.keys())}"
    
    print(f"✅ V3 단일 전략 모드 로드 거부 확인: {len(strategies)} 전략")


def test_v3_excluded_from_ensemble():
    """
    PHASE29-3: V3 전략이 앙상블 모드에서 자동 제외되는지 확인
    """
    config = {
        "timeframe": "5m",
        "symbol": "BTCUSDT",
        "strategy": {
            "selector": None,
            "use_ensemble": True
        },
        "strategies": {
            "btc5m_baseline_v3": {
                "enabled": True,
                "adx_trend_threshold": 25
            },
            "scalping": {
                "enabled": True,
                "rsi_oversold": 30,
                "rsi_overbought": 70
            }
        }
    }
    
    # load_strategies 호출
    strategies = load_strategies(config)
    
    # V3 전략이 포함되지 않아야 함
    assert "btc5m_baseline_v3" not in strategies, "Deprecated 전략이 앙상블에 포함되었습니다."
    
    # 다른 전략은 로드되어야 함 (scalping)
    # NOTE: scalping이 실제로 로드 가능한지는 별도 검증 필요
    print(f"✅ 앙상블 모드에서 V3 제외 확인: {list(strategies.keys())}")


def test_v3_metadata_deprecated_marker():
    """
    PHASE29-3: V3 metadata에 DEPRECATED 표시 확인
    """
    config = {"timeframe": "5m", "symbol": "BTCUSDT"}
    v3_instance = Btc5mBaselineV3(config=config)
    
    # metadata 확인
    assert hasattr(v3_instance, 'metadata'), "V3 전략에 metadata가 없습니다."
    
    metadata = v3_instance.metadata
    
    # description에 DEPRECATED 표시 확인
    assert hasattr(metadata, 'description'), "metadata에 description이 없습니다."
    assert "DEPRECATED" in metadata.description or "deprecated" in metadata.description, \
        f"metadata description에 DEPRECATED 표시가 없습니다: {metadata.description}"
    
    # version에 deprecated 표시 확인
    assert hasattr(metadata, 'version'), "metadata에 version이 없습니다."
    assert "deprecated" in metadata.version.lower(), \
        f"metadata version에 deprecated 표시가 없습니다: {metadata.version}"
    
    print(f"✅ V3 metadata deprecated 표시 확인:")
    print(f"   - description: {metadata.description}")
    print(f"   - version: {metadata.version}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
