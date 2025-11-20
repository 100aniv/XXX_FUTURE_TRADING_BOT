"""PHASE20-1 Config 테스트"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import load_config_with_mode

config_path = "configs/paper/ensemble_paper_smoke.yml"
cfg = load_config_with_mode(base_path=config_path)

print("=" * 60)
print("PHASE20-1 Config 검증")
print("=" * 60)
print(f"✅ Config 로드 성공: {config_path}")
print(f"✅ ensemble.enabled: {cfg.get('ensemble', {}).get('enabled')}")
print(f"✅ mode: {cfg.get('mode')}")
print(f"✅ symbol: {cfg.get('symbol')}")
print(f"✅ timeframe: {cfg.get('timeframe')}")
print(f"✅ duration_mode: {cfg.get('paper', {}).get('duration_mode')}")
print(f"✅ duration_hours: {cfg.get('paper', {}).get('duration_hours')}")
print(f"✅ strategies: {cfg.get('ensemble', {}).get('strategies', [])}")
print("=" * 60)
