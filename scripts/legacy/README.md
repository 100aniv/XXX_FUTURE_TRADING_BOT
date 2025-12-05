# LEGACY SCRIPTS (ARCHIVED)

## ⚠️ WARNING
**이 디렉토리의 스크립트들은 과거 PHASE 실험용 런처입니다.**

현재 공식 엔진 진입점은 다음만 사용합니다:
- `scripts/run_v2.py` (공식 thin wrapper)
- `scripts/run_backtest.py` (backtest mode wrapper)
- `scripts/run_paper.py` (paper mode wrapper)

## 🚫 DO NOT USE
- 운영/테스트 용도로 사용하지 마세요
- 새로운 기능 추가 시 참고용으로만 사용하세요
- 모든 새로운 실행은 `run_v2.py`를 통해야 합니다

## 📦 Archived Scripts (PHASE23-3)
다음 스크립트들이 `scripts/` → `scripts/legacy/`로 이동되었습니다:

| 파일명 | 원래 PHASE | 용도 |
|--------|-----------|------|
| `run_all_wfa.py` | PHASE20-21 | WFA 전체 실행 |
| `run_paper_phase16.py` | PHASE16 | Paper 구버전 |
| `run_phase20_paper.py` | PHASE20 | Phase20 실험 |
| `run_phase21_1a.py` | PHASE21 | Phase21 실험 |
| `run_phase21_1a_auto.py` | PHASE21 | Phase21 자동 |
| `run_phase21_1a_simple.py` | PHASE21 | Phase21 간단 |
| `run_phase22_2_ensemble.py` | PHASE22 | Ensemble v2 |
| `run_phase22_ensemble_single_symbol.py` | PHASE22 | Ensemble 단일 심볼 |
| `run_real_paper_12h_supervised.py` | PHASE17+ | 12H Paper 감독 모드 |
| `run_tuner.py` | PHASE24-25 | Tuner 구버전 |
| `run_tuner_loop.py` | PHASE24-25 | Tuner Loop |
| `run_wfa_baseline.py` | PHASE20-21 | WFA Baseline |
| `run_wfa_blocks_sequential.py` | PHASE20-21 | WFA Blocks |

## 🔄 Migration Guide
과거 스크립트를 사용하던 경우:

### Before
```bash
python scripts/run_phase21_1a.py --strategy scalping --symbol BTCUSDT
```

### After (PHASE23-3)
```bash
python scripts/run_v2.py --mode paper --config configs/paper/phase21_1a.yml
```

---

**Last Updated**: 2025-12-05 (PHASE23-3: Legacy Engine Decommission)
