#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-3: Stage-1 (7D) Config 생성
===================================
빠른 스크리닝을 위한 7일 백테스트 config 18개 생성

Usage:
    python scripts/phase34/generate_stage1_configs.py
"""
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 경로
TEMPLATE_PATH = project_root / "configs" / "backtest" / "phase34_template.yml"
STAGE1_DIR = project_root / "configs" / "backtest" / "phase34_stage1"
META_PATH = STAGE1_DIR / "stage1_meta.json"

# Stage-1 기간: 7일 (2024-01-01 ~ 2024-01-08)
STAGE1_START = "2024-01-01 00:00:00"
STAGE1_END = "2024-01-08 00:00:00"
STAGE1_DURATION_MIN = 7 * 24 * 60  # 10,080분

# 실험 파라미터 (PHASE34-1과 동일)
CONFIDENCE_VALUES = [0.20, 0.25, 0.30]
HYSTERESIS_VALUES = [2, 3, 5]
MTF_WEIGHT_VALUES = [(0.6, 0.4), (0.5, 0.5)]


def load_template() -> dict:
    """템플릿 로드"""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_config(template: dict, params: dict) -> dict:
    """개별 config 생성"""
    config = template.copy()
    
    # Run ID
    config['run_id'] = params['id']
    
    # Backtest 기간 (Stage-1: 7일)
    config['backtest']['start_date'] = STAGE1_START
    config['backtest']['end_date'] = STAGE1_END
    config['backtest']['duration_minutes'] = STAGE1_DURATION_MIN
    
    # Output 경로
    config['backtest']['output_file'] = f"reports/backtest/phase34/stage1/{params['id']}_summary.json"
    
    # Strategy 파라미터
    strategy_cfg = config['strategies']['btc15m_core_v2']
    regime = strategy_cfg['regime_detection']
    
    regime['min_confidence_trend'] = params['min_confidence_trend']
    regime['min_confidence_range'] = params['min_confidence_range']
    regime['hysteresis_candles'] = params['hysteresis_candles']
    regime['higher_tf_weight'] = params['higher_tf_weight']
    regime['local_tf_weight'] = params['local_tf_weight']
    
    return config


def main():
    print("=" * 80)
    print("PHASE34-3: Stage-1 (7D) Config Generator")
    print("=" * 80)
    print(f"📄 Template: {TEMPLATE_PATH.name}")
    print(f"📂 Output: {STAGE1_DIR}")
    print(f"📅 Period: {STAGE1_START} ~ {STAGE1_END} (7일)")
    print()
    
    # 템플릿 로드
    template = load_template()
    
    # 출력 디렉토리 생성
    STAGE1_DIR.mkdir(parents=True, exist_ok=True)
    
    # 실험 생성
    experiments = []
    config_count = 0
    
    for conf in CONFIDENCE_VALUES:
        for hyst in HYSTERESIS_VALUES:
            for mtf_weight in MTF_WEIGHT_VALUES:
                higher_w, local_w = mtf_weight
                
                # ID 생성 (Stage-1 prefix 추가)
                conf_str = str(int(conf * 100))
                hyst_str = str(hyst)
                weight_str = str(int(higher_w * 100))
                
                exp_id = f"s1_c{conf_str}_h{hyst_str}_w{weight_str}"
                
                # 파라미터
                params = {
                    'id': exp_id,
                    'min_confidence_trend': conf,
                    'min_confidence_range': conf + 0.05,  # Trend보다 5% 높게
                    'hysteresis_candles': hyst,
                    'higher_tf_weight': higher_w,
                    'local_tf_weight': local_w
                }
                
                # Config 생성
                config = generate_config(template, params)
                
                # 저장
                config_file = STAGE1_DIR / f"{exp_id}.yml"
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
                print(f"✅ {config_file.name}")
                
                # 메타데이터 수집
                experiments.append({
                    'id': exp_id,
                    'config_file': str(config_file.relative_to(project_root)),
                    'summary_file': f"reports/backtest/phase34/stage1/{exp_id}_summary.json",
                    'params': params
                })
                
                config_count += 1
    
    # 메타데이터 저장
    meta = {
        'stage': 'stage1',
        'period': f"{STAGE1_START} ~ {STAGE1_END}",
        'duration_days': 7,
        'generated_at': datetime.now().isoformat(),
        'total_experiments': config_count,
        'experiments': experiments
    }
    
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 80)
    print(f"✅ Total: {config_count} Stage-1 configs generated")
    print(f"📋 Meta: {META_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
