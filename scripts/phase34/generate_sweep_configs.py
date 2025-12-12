#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-1: Config Generator for Parameter Sweep
================================================
3축 18조합 자동 생성

실험 축:
1. Confidence Threshold: 0.20 / 0.25 / 0.30
2. Hysteresis Candles: 2 / 3 / 5
3. MTF Weight: (0.6/0.4) AS-IS / (0.5/0.5) Relaxed

Usage:
    python scripts/phase34/generate_sweep_configs.py
"""
import sys
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 실험 축 정의
CONFIDENCE_VALUES = [0.20, 0.25, 0.30]
HYSTERESIS_VALUES = [2, 3, 5]
MTF_WEIGHT_VALUES = [
    {"higher": 0.6, "local": 0.4, "label": "w60"},  # AS-IS
    {"higher": 0.5, "local": 0.5, "label": "w50"},  # Relaxed
]

# 경로
TEMPLATE_PATH = project_root / "configs" / "backtest" / "phase34_template.yml"
OUTPUT_DIR = project_root / "configs" / "backtest" / "phase34_sweep"
META_PATH = project_root / "configs" / "backtest" / "phase34_sweep" / "sweep_meta.json"


def load_template() -> dict:
    """템플릿 로드"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_experiment_id(conf: float, hyst: int, weight_label: str) -> str:
    """실험 ID 생성"""
    conf_str = str(int(conf * 100))
    return f"p34_c{conf_str}_h{hyst}_{weight_label}"


def create_config(
    template: dict,
    exp_id: str,
    confidence: float,
    hysteresis: int,
    mtf_weight: Dict[str, Any]
) -> dict:
    """단일 config 생성"""
    cfg = template.copy()
    
    # Run ID 및 Output 경로 수정
    cfg["run_id"] = exp_id
    cfg["backtest"]["output_file"] = f"reports/backtest/phase34/sweep/{exp_id}_summary.json"
    
    # 파라미터 수정
    strategy_cfg = cfg["strategies"]["btc15m_core_v2"]
    regime = strategy_cfg["regime_detection"]
    
    # Confidence (Trend/Range 동시 조정)
    regime["min_confidence_trend"] = confidence
    regime["min_confidence_range"] = confidence + 0.05  # Range는 +0.05 오프셋 유지
    
    # Hysteresis
    regime["hysteresis_candles"] = hysteresis
    
    # MTF Weight
    regime["higher_tf_weight"] = mtf_weight["higher"]
    regime["local_tf_weight"] = mtf_weight["local"]
    
    return cfg


def save_config(cfg: dict, exp_id: str):
    """Config 파일 저장"""
    output_path = OUTPUT_DIR / f"{exp_id}.yml"
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"✅ {output_path.name}")


def generate_all_configs():
    """모든 조합 생성"""
    print("=" * 60)
    print("PHASE34-1: Config Generator")
    print("=" * 60)
    
    # 템플릿 로드
    template = load_template()
    print(f"📄 Template: {TEMPLATE_PATH}")
    print(f"📂 Output: {OUTPUT_DIR}")
    print()
    
    # 메타 정보
    meta = {
        "generated_at": datetime.now().isoformat(),
        "total_experiments": len(CONFIDENCE_VALUES) * len(HYSTERESIS_VALUES) * len(MTF_WEIGHT_VALUES),
        "axes": {
            "confidence": CONFIDENCE_VALUES,
            "hysteresis": HYSTERESIS_VALUES,
            "mtf_weight": [w["label"] for w in MTF_WEIGHT_VALUES]
        },
        "experiments": []
    }
    
    # 조합 생성
    exp_count = 0
    for conf in CONFIDENCE_VALUES:
        for hyst in HYSTERESIS_VALUES:
            for mtf in MTF_WEIGHT_VALUES:
                exp_id = generate_experiment_id(conf, hyst, mtf["label"])
                
                # Config 생성 및 저장
                cfg = create_config(template, exp_id, conf, hyst, mtf)
                save_config(cfg, exp_id)
                
                # 메타 정보 추가
                meta["experiments"].append({
                    "id": exp_id,
                    "params": {
                        "confidence_trend": conf,
                        "confidence_range": conf + 0.05,
                        "hysteresis": hyst,
                        "higher_tf_weight": mtf["higher"],
                        "local_tf_weight": mtf["local"]
                    },
                    "config_file": f"configs/backtest/phase34_sweep/{exp_id}.yml",
                    "summary_file": f"reports/backtest/phase34/sweep/{exp_id}_summary.json"
                })
                
                exp_count += 1
    
    # 메타 파일 저장
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    
    print()
    print("=" * 60)
    print(f"✅ Total: {exp_count} configs generated")
    print(f"📋 Meta: {META_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    generate_all_configs()
