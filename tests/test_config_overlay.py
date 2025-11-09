#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigOverlay 단위 테스트
=========================
PR13 Phase 1: ConfigOverlay 구현 검증

참조:
- docs/PHASE6/PR13_ARCHITECTURE_DESIGN.md (2.1 ConfigOverlay)
- docs/PHASE6/PR13_BUG #8_ADD.md (Unit 테스트 매트릭스 라인 75)
- .windsurfrules (Redis Namespace Policy)

테스트 항목:
- deep-merge 검증
- 스키마 검증
- Redis 네임스페이스 형식
- 오버레이 적용/롤백
"""
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, MagicMock

from tuning.config_overlay import ConfigOverlay, OverlayMetadata


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def base_config():
    """기본 설정"""
    return {
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.4,
                "beta_rr": 0.2,
                "gamma_sharpe": 0.2,
                "delta_confidence": 0.15,
                "epsilon_regime": 0.05,
                "weights": {
                    "trend": 2.0,
                    "reversion": 2.0,
                    "breakout": 2.0,
                    "scalping": 1.5,
                    "daytrade": 1.5,
                    "swing": 1.5
                }
            }
        }
    }


@pytest.fixture
def config_overlay(base_config):
    """ConfigOverlay 인스턴스"""
    return ConfigOverlay(
        base_config_path="config.yml",
        redis_client=None,
        namespace="fa",
        env="paper",
        run_id="test_run_001",
        base_config=base_config
    )


@pytest.fixture
def redis_mock():
    """Redis 클라이언트 Mock"""
    mock = MagicMock()
    mock.setex = Mock()
    mock.delete = Mock()
    return mock


# ============================================
# 테스트: 초기화 및 프로퍼티
# ============================================

def test_init_with_base_config(base_config):
    """베이스 설정으로 초기화"""
    overlay = ConfigOverlay(
        base_config_path="config.yml",
        base_config=base_config,
        namespace="fa",
        env="paper",
        run_id="test_001"
    )
    
    assert overlay.base_config == base_config
    assert overlay.namespace == "fa"
    assert overlay.env == "paper"
    assert overlay.run_id == "test_001"
    assert len(overlay.overlays) == 0


def test_redis_key_namespace_format(config_overlay):
    """Redis 키 네임스페이스 형식 검증 (.windsurfrules 라인 68-71)"""
    # {ns}:{env}:{run_id}:<domain>
    assert config_overlay.redis_key_prefix == "fa:paper:test_run_001:config"
    assert config_overlay.active_key == "fa:paper:test_run_001:config:active"
    assert config_overlay.baseline_key == "fa:paper:test_run_001:config:baseline"
    assert config_overlay.history_key == "fa:paper:test_run_001:config:history"


# ============================================
# 테스트: 오버레이 적용 (deep merge)
# ============================================

def test_apply_overlay_basic(config_overlay):
    """기본 오버레이 적용"""
    overlay = {
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.35,
                "beta_rr": 0.30
            }
        }
    }
    
    merged = config_overlay.apply_overlay(overlay, source="test")
    
    # 오버레이된 값 확인
    assert merged["strategies"]["ensemble"]["alpha_winrate"] == 0.35
    assert merged["strategies"]["ensemble"]["beta_rr"] == 0.30
    
    # 기존 값 유지 확인
    assert merged["strategies"]["ensemble"]["gamma_sharpe"] == 0.2
    assert merged["symbol"] == "BTCUSDT"
    
    # 히스토리 확인
    assert len(config_overlay.overlays) == 1
    assert config_overlay.active_overlay == overlay


def test_apply_overlay_deep_merge(config_overlay):
    """Deep merge 검증"""
    overlay = {
        "strategies": {
            "ensemble": {
                "weights": {
                    "trend": 3.0  # 2.0 → 3.0
                }
            }
        }
    }
    
    merged = config_overlay.apply_overlay(overlay)
    
    # 변경된 값
    assert merged["strategies"]["ensemble"]["weights"]["trend"] == 3.0
    
    # 유지된 값들
    assert merged["strategies"]["ensemble"]["weights"]["reversion"] == 2.0
    assert merged["strategies"]["ensemble"]["weights"]["breakout"] == 2.0


# ============================================
# 테스트: 검증
# ============================================

def test_validation_ensemble_weights_range(config_overlay):
    """앙상블 가중치 범위 검증"""
    invalid_overlay = {
        "strategies": {
            "ensemble": {
                "weights": {
                    "trend": 10.0  # 최대 5.0 초과
                }
            }
        }
    }
    
    with pytest.raises(ValueError, match="가중치 범위 오류"):
        config_overlay.apply_overlay(invalid_overlay)


def test_validation_required_keys(config_overlay):
    """필수 키 검증"""
    # 베이스 설정 제거
    config_overlay.base_config = {}
    
    overlay = {
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.5
            }
        }
    }
    
    with pytest.raises(ValueError, match="필수 키 누락"):
        config_overlay.apply_overlay(overlay)


def test_validation_invalid_timeframe(config_overlay):
    """잘못된 타임프레임 검증"""
    overlay = {
        "timeframe": "10m"  # 유효하지 않은 타임프레임
    }
    
    with pytest.raises(ValueError, match="잘못된 타임프레임"):
        config_overlay.apply_overlay(overlay)


# ============================================
# 테스트: 롤백 및 클리어
# ============================================

def test_rollback_to_baseline(config_overlay):
    """베이스라인으로 롤백"""
    # 오버레이 적용
    overlay = {
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.5
            }
        }
    }
    config_overlay.apply_overlay(overlay)
    
    # 롤백
    baseline = config_overlay.rollback_to_baseline()
    
    assert baseline["strategies"]["ensemble"]["alpha_winrate"] == 0.4
    assert len(config_overlay.overlays) == 0
    assert config_overlay.active_overlay is None


def test_clear_overlay(config_overlay, redis_mock):
    """오버레이 제거"""
    config_overlay.redis_client = redis_mock
    
    # 오버레이 적용
    overlay = {"strategies": {"ensemble": {"alpha_winrate": 0.5}}}
    config_overlay.apply_overlay(overlay)
    
    # 클리어
    baseline = config_overlay.clear_overlay()
    
    assert baseline["strategies"]["ensemble"]["alpha_winrate"] == 0.4
    assert len(config_overlay.overlays) == 0
    redis_mock.delete.assert_called_once_with(config_overlay.active_key)


# ============================================
# 테스트: 히스토리
# ============================================

def test_overlay_history(config_overlay):
    """오버레이 히스토리 추적"""
    # 여러 오버레이 적용
    overlay1 = {"strategies": {"ensemble": {"alpha_winrate": 0.35}}}
    overlay2 = {"strategies": {"ensemble": {"beta_rr": 0.25}}}
    
    config_overlay.apply_overlay(overlay1, source="test1", description="첫 번째")
    config_overlay.apply_overlay(overlay2, source="test2", description="두 번째")
    
    history = config_overlay.get_overlay_history()
    
    assert len(history) == 2
    assert history[0]["source"] == "test1"
    assert history[0]["description"] == "첫 번째"
    assert history[1]["source"] == "test2"
    assert history[1]["description"] == "두 번째"


# ============================================
# 테스트: 파일 저장/로드
# ============================================

def test_save_and_load_overlay(config_overlay):
    """오버레이 저장 및 로드"""
    overlay = {
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.35,
                "beta_rr": 0.30
            }
        }
    }
    
    # 저장
    config_overlay.save_overlay(overlay, "test_overlay")
    
    # 파일 존재 확인
    overlay_path = Path("configs/overlays/test_overlay.yml")
    assert overlay_path.exists()
    
    # 로드
    loaded = config_overlay.load_overlay(str(overlay_path))
    
    assert loaded["strategies"]["ensemble"]["alpha_winrate"] == 0.35
    assert loaded["strategies"]["ensemble"]["beta_rr"] == 0.30
    
    # 정리
    overlay_path.unlink()
    Path("configs/overlays/test_overlay_metadata.json").unlink()


# ============================================
# 테스트: Redis 저장
# ============================================

def test_redis_save(config_overlay, redis_mock):
    """Redis 저장 검증"""
    config_overlay.redis_client = redis_mock
    
    overlay = {"strategies": {"ensemble": {"alpha_winrate": 0.5}}}
    config_overlay.apply_overlay(overlay)
    
    # Redis setex 호출 확인
    assert redis_mock.setex.call_count == 2  # config + metadata
    
    # 첫 번째 호출 (config)
    call_args = redis_mock.setex.call_args_list[0]
    assert call_args[0][0] == config_overlay.active_key
    assert call_args[0][1] == 3600  # TTL


# ============================================
# 테스트: get_active_config
# ============================================

def test_get_active_config_no_overlay(config_overlay):
    """오버레이 없을 때 활성 설정"""
    active = config_overlay.get_active_config()
    
    assert active == config_overlay.base_config
    assert active["strategies"]["ensemble"]["alpha_winrate"] == 0.4


def test_get_active_config_with_overlay(config_overlay):
    """오버레이 있을 때 활성 설정"""
    overlay = {"strategies": {"ensemble": {"alpha_winrate": 0.35}}}
    config_overlay.apply_overlay(overlay)
    
    active = config_overlay.get_active_config()
    
    assert active["strategies"]["ensemble"]["alpha_winrate"] == 0.35


def test_get_active_config_multiple_overlays(config_overlay):
    """여러 오버레이 순차 적용"""
    overlay1 = {"strategies": {"ensemble": {"alpha_winrate": 0.35}}}
    overlay2 = {"strategies": {"ensemble": {"beta_rr": 0.25}}}
    
    config_overlay.apply_overlay(overlay1)
    config_overlay.apply_overlay(overlay2)
    
    active = config_overlay.get_active_config()
    
    # 두 오버레이 모두 적용됨
    assert active["strategies"]["ensemble"]["alpha_winrate"] == 0.35
    assert active["strategies"]["ensemble"]["beta_rr"] == 0.25


# ============================================
# 테스트: 엣지 케이스
# ============================================

def test_overlay_with_empty_dict(config_overlay):
    """빈 오버레이"""
    overlay = {}
    merged = config_overlay.apply_overlay(overlay)
    
    # 베이스 설정과 동일
    assert merged == config_overlay.base_config


def test_overlay_with_new_keys(config_overlay):
    """새로운 키 추가"""
    overlay = {
        "new_section": {
            "new_key": "new_value"
        }
    }
    
    merged = config_overlay.apply_overlay(overlay)
    
    assert "new_section" in merged
    assert merged["new_section"]["new_key"] == "new_value"


# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
