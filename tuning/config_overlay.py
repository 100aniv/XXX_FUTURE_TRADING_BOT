#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigOverlay - 설정 오버레이 시스템
=====================================
PR13 Phase 1: 베이스 설정에 튜닝 파라미터를 오버레이하는 시스템

참조:
- docs/PHASE6/PR13_ARCHITECTURE_DESIGN.md (2.1 ConfigOverlay)
- .windsurfrules (Redis Namespace Policy)

역할:
- 베이스 설정 로드 (config.yml)
- 오버레이 적용 및 검증 (deep merge)
- 히스토리 추적
- Redis 네임스페이스 준수
"""
import os
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from copy import deepcopy

from common.config_loader import load_config, deep_merge
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ============================================
# 메타데이터
# ============================================

@dataclass
class OverlayMetadata:
    """오버레이 메타데이터"""
    overlay_id: str
    created_at: datetime
    source: str  # "file" | "api" | "tuner"
    description: str
    version: str = "1.0"


# ============================================
# ConfigOverlay
# ============================================

class ConfigOverlay:
    """
    설정 오버레이 시스템
    
    역할:
    - 베이스 설정 로드
    - 오버레이 적용 및 검증 (deep merge)
    - 히스토리 추적
    
    참조:
    - PR13_ARCHITECTURE_DESIGN.md 라인 93-143
    - .windsurfrules Redis Namespace Policy 라인 68-71
    """
    
    def __init__(
        self,
        base_config_path: str = "config.yml",
        redis_client = None,
        namespace: str = "fa",
        env: str = "paper",
        run_id: str = None,
        base_config: Optional[Dict[str, Any]] = None
    ):
        """
        ConfigOverlay 초기화
        
        Args:
            base_config_path: 베이스 설정 파일 경로
            redis_client: Redis 클라이언트 (선택)
            namespace: Redis 네임스페이스 (기본: "fa")
            env: 환경 (paper|live|tuner)
            run_id: 실행 ID (UUID)
            base_config: 직접 제공된 베이스 설정 (테스트용)
        """
        self.base_config_path = base_config_path
        self.redis_client = redis_client
        self.namespace = namespace
        self.env = env
        self.run_id = run_id or self._generate_run_id()
        
        # 베이스 설정 로드
        if base_config:
            self.base_config = deepcopy(base_config)
        else:
            self.base_config = self._load_base_config(base_config_path)
        
        # 오버레이 히스토리
        self.overlays: List[Dict[str, Any]] = []
        self.overlay_metadata: List[OverlayMetadata] = []
        self.active_overlay: Optional[Dict[str, Any]] = None
        
        # 디렉토리 생성
        self._ensure_directories()
        
        logger.info(f"ConfigOverlay 초기화 - base: {base_config_path}, ns: {namespace}, env: {env}, run_id: {self.run_id}")
    
    @property
    def redis_key_prefix(self) -> str:
        """Redis 키 접두사 (.windsurfrules Redis Namespace Policy)"""
        return f"{self.namespace}:{self.env}:{self.run_id}:config"
    
    @property
    def active_key(self) -> str:
        """활성 설정 Redis 키"""
        return f"{self.redis_key_prefix}:active"
    
    @property
    def baseline_key(self) -> str:
        """베이스라인 설정 Redis 키"""
        return f"{self.redis_key_prefix}:baseline"
    
    @property
    def history_key(self) -> str:
        """히스토리 Redis 키"""
        return f"{self.redis_key_prefix}:history"
    
    def _generate_run_id(self) -> str:
        """Run ID 생성"""
        from uuid import uuid4
        return str(uuid4())
    
    def _load_base_config(self, config_path: str) -> Dict[str, Any]:
        """베이스 설정 로드"""
        try:
            if Path(config_path).exists():
                return load_config(config_path)
            else:
                logger.warning(f"베이스 설정 파일 없음: {config_path}, 기본값 사용")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"베이스 설정 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
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
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        Path("configs/overlays").mkdir(parents=True, exist_ok=True)
        Path("configs/active").mkdir(parents=True, exist_ok=True)
        Path("configs/base").mkdir(parents=True, exist_ok=True)
    
    def load_overlay(self, overlay_path: str) -> Dict[str, Any]:
        """
        오버레이 파일 로드 및 검증
        
        Args:
            overlay_path: 오버레이 파일 경로
        
        Returns:
            오버레이 딕셔너리
        """
        path = Path(overlay_path)
        
        if not path.exists():
            raise FileNotFoundError(f"오버레이 파일 없음: {overlay_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            overlay = yaml.safe_load(f)
        
        # 검증
        self._validate_overlay(overlay)
        
        logger.info(f"오버레이 로드: {overlay_path}")
        return overlay
    
    def apply_overlay(
        self,
        overlay: Dict[str, Any],
        source: str = "manual",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        오버레이 적용 (deep merge)
        
        Args:
            overlay: 오버레이 데이터
            source: 출처 (manual|tuner|api)
            description: 설명
        
        Returns:
            병합된 설정
        """
        # 메타데이터 생성
        from uuid import uuid4
        metadata = OverlayMetadata(
            overlay_id=str(uuid4()),
            created_at=datetime.utcnow(),
            source=source,
            description=description or f"Overlay from {source}"
        )
        
        # 오버레이 검증
        self._validate_overlay(overlay)
        
        # Deep merge 수행
        merged_config = deep_merge(self.base_config, overlay)
        
        # 최종 설정 검증
        self._validate_config(merged_config)
        
        # 히스토리에 추가
        self.overlays.append(overlay)
        self.overlay_metadata.append(metadata)
        self.active_overlay = overlay
        
        # Redis에 저장 (선택)
        if self.redis_client:
            self._save_to_redis(merged_config, metadata)
        
        # 파일로 저장
        self._save_active_config(merged_config)
        
        logger.info(f"오버레이 적용 완료: {metadata.overlay_id}")
        return merged_config
    
    def _validate_overlay(self, overlay: Dict[str, Any]):
        """오버레이 데이터 검증"""
        if not isinstance(overlay, dict):
            raise ValueError("오버레이는 딕셔너리여야 함")
        
        # 위험한 키 체크
        dangerous_keys = ['database', 'redis', 'telegram']
        for key in dangerous_keys:
            if key in overlay:
                logger.warning(f"위험한 키 감지: {key}")
        
        # 앙상블 가중치 검증
        if 'strategies' in overlay and 'ensemble' in overlay['strategies']:
            ensemble = overlay['strategies']['ensemble']
            if 'weights' in ensemble:
                self._validate_ensemble_weights(ensemble['weights'])
    
    def _validate_ensemble_weights(self, weights: Dict[str, float]):
        """앙상블 가중치 검증"""
        # 개별 가중치 범위 체크
        for name, weight in weights.items():
            if not (0.0 <= weight <= 5.0):  # 최대 5.0
                raise ValueError(f"가중치 범위 오류 {name}: {weight} (0.0~5.0)")
        
        # 총합 체크 (참고용, 필수 아님)
        total = sum(weights.values())
        logger.info(f"앙상블 가중치 총합: {total:.3f}")
    
    def _validate_config(self, config: Dict[str, Any]):
        """최종 설정 검증"""
        # 필수 키 검증 (베이스 설정에 있어야 함)
        required_keys = ['symbol', 'timeframe']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"필수 키 누락: {key}")
        
        # 심볼 검증
        if not isinstance(config['symbol'], str) or len(config['symbol']) < 3:
            raise ValueError(f"잘못된 심볼: {config['symbol']}")
        
        # 타임프레임 검증
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
        if config['timeframe'] not in valid_timeframes:
            raise ValueError(f"잘못된 타임프레임: {config['timeframe']}")
    
    def save_overlay(self, overlay: Dict[str, Any], name: str):
        """
        오버레이 파일로 저장
        
        Args:
            overlay: 오버레이 데이터
            name: 저장할 파일명 (확장자 제외)
        """
        overlay_path = Path(f"configs/overlays/{name}.yml")
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(overlay_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(overlay, f, default_flow_style=False, allow_unicode=True)
        
        # 메타데이터 저장
        metadata_path = Path(f"configs/overlays/{name}_metadata.json")
        metadata = {
            "created_at": datetime.utcnow().isoformat(),
            "source": "save_overlay",
            "description": f"Saved overlay: {name}"
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"오버레이 저장: {overlay_path}")
    
    def _save_active_config(self, config: Dict[str, Any]):
        """현재 활성 설정 저장"""
        active_path = Path("configs/active/current.yml")
        active_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(active_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
    
    def _save_to_redis(self, config: Dict[str, Any], metadata: OverlayMetadata):
        """Redis에 설정 저장"""
        if not self.redis_client:
            return
        
        try:
            # 설정 저장 (네임스페이스 준수)
            self.redis_client.setex(
                self.active_key,
                3600,  # 1시간 TTL
                json.dumps(config, ensure_ascii=False)
            )
            
            # 메타데이터 저장
            metadata_key = f"{self.redis_key_prefix}:metadata"
            self.redis_client.setex(
                metadata_key,
                3600,
                json.dumps(asdict(metadata), default=str, ensure_ascii=False)
            )
            
            logger.info(f"Redis 저장 완료: {self.active_key}")
        except Exception as e:
            logger.warning(f"Redis 저장 실패: {e}")
    
    def rollback_to_baseline(self) -> Dict[str, Any]:
        """베이스라인으로 롤백"""
        self.overlays.clear()
        self.overlay_metadata.clear()
        self.active_overlay = None
        
        # 베이스 설정으로 활성 설정 업데이트
        self._save_active_config(self.base_config)
        
        logger.info("베이스라인으로 롤백 완료")
        return deepcopy(self.base_config)
    
    def clear_overlay(self) -> Dict[str, Any]:
        """
        모든 오버레이 제거 및 베이스 설정 반환
        
        Returns:
            베이스 설정
        """
        # 오버레이 제거
        self.overlays.clear()
        self.overlay_metadata.clear()
        self.active_overlay = None
        
        # Redis 키 삭제
        if self.redis_client:
            try:
                self.redis_client.delete(self.active_key)
                logger.info(f"Redis 키 삭제: {self.active_key}")
            except Exception as e:
                logger.warning(f"Redis 키 삭제 실패: {e}")
        
        logger.info("모든 오버레이 제거 완료")
        return deepcopy(self.base_config)
    
    def get_active_config(self) -> Dict[str, Any]:
        """현재 활성 설정 조회"""
        if not self.overlays:
            return deepcopy(self.base_config)
        
        # 모든 오버레이를 순차적으로 적용
        final_config = deepcopy(self.base_config)
        for overlay in self.overlays:
            final_config = deep_merge(final_config, overlay)
        
        return final_config
    
    def get_overlay_history(self) -> List[Dict[str, Any]]:
        """오버레이 히스토리 조회"""
        history = []
        for i, metadata in enumerate(self.overlay_metadata):
            history.append({
                "index": i,
                "overlay_id": metadata.overlay_id,
                "created_at": metadata.created_at.isoformat(),
                "source": metadata.source,
                "description": metadata.description,
                "version": metadata.version
            })
        
        return history
    
    def export_current_as_base(self, output_path: str = "config_new_base.yml"):
        """현재 설정을 새로운 베이스로 내보내기"""
        current_config = self.get_active_config()
        
        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(current_config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"현재 설정을 베이스로 내보내기: {output_path}")


# ============================================
# 팩토리 함수
# ============================================

def create_config_overlay(
    base_config_path: str = "config.yml",
    **kwargs
) -> ConfigOverlay:
    """ConfigOverlay 팩토리 함수"""
    return ConfigOverlay(base_config_path=base_config_path, **kwargs)


# ============================================
# 사용 예시 (테스트용)
# ============================================

if __name__ == "__main__":
    # ConfigOverlay 생성
    overlay = create_config_overlay()
    
    # 테스트 오버레이
    test_overlay = {
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.35,
                "beta_rr": 0.30,
                "gamma_sharpe": 0.20,
                "delta_confidence": 0.10,
                "epsilon_regime": 0.05
            }
        }
    }
    
    # 오버레이 적용
    final_config = overlay.apply_overlay(test_overlay, source="test", description="테스트 오버레이")
    print(f"최종 설정: {final_config['strategies']['ensemble']}")
    
    # 히스토리 조회
    history = overlay.get_overlay_history()
    print(f"오버레이 히스토리: {len(history)}개")
    
    print("✅ ConfigOverlay 테스트 완료")
