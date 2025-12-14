#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER3: Fast Gate Test (30~90초)
==========================================

Config 로드 + 전략 Init 검증
- Import 정상
- Config 로드 성공
- Strategy 초기화 성공
- 핵심 파라미터 반영 확인

Exit Code:
    0: PASS
    1: FAIL
"""
import sys
from pathlib import Path
from datetime import datetime

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("fast_gate")


def main():
    """Fast Gate 실행"""
    logger.info("=" * 80)
    logger.info("PHASE35-2 ITER3: Fast Gate Test")
    logger.info("=" * 80)
    logger.info(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. Import 테스트
        logger.info("\n[1/3] Import 테스트...")
        import yaml
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1

        logger.info("   ✅ Import 성공")

        # 2. Config 로드
        logger.info("\n[2/3] Config 로드...")
        config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"

        if not config_path.exists():
            logger.error(f"   ❌ Config 없음: {config_path}")
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f"   ✅ Config 로드 성공: {config_path.name}")

        # 3. 전략 초기화
        logger.info("\n[3/3] 전략 초기화...")

        # Config merge (엔진 방식과 동일)
        strategy_name = config.get("strategy", {}).get(
            "selector", "phase35_ensemble_v1"
        )
        strategy_params = (
            config.get("strategies", {}).get(strategy_name, {}).get("params", {})
        )

        # Deep merge
        def deep_merge(base, custom):
            merged = base.copy()
            for key, value in custom.items():
                if (
                    key in merged
                    and isinstance(merged[key], dict)
                    and isinstance(value, dict)
                ):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged

        merged_config = deep_merge(config, strategy_params)

        strategy = Phase35EnsembleV1(merged_config)

        # 파라미터 검증
        expected = {
            "_cooldown_bars": 3,
            "_min_votes": 2,
            "_confidence_threshold": 0.70,
        }

        all_pass = True
        for param, expected_value in expected.items():
            actual_value = getattr(strategy, param, None)
            match = actual_value == expected_value
            status = "✅" if match else "❌"
            logger.info(
                f"   {status} {param}: {actual_value} (expected: {expected_value})"
            )
            if not match:
                all_pass = False

        if not all_pass:
            logger.error("   ❌ 파라미터 불일치")
            return 1

        logger.info("   ✅ 전략 초기화 성공")

        # 최종 판정
        logger.info("\n" + "=" * 80)
        logger.info("✅ Fast Gate PASS")
        logger.info("=" * 80)
        logger.info(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return 0

    except Exception as e:
        logger.error(f"\n❌ Fast Gate FAIL: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
