#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reversion Bayesian Tuner (Optuna)
================================
- 목적: Reversion 전략 파라미터 베이지안 최적화 (IS/OOS, WFA 지원)
- 실행: python -u scripts/tune_reversion.py --study reversion_v1 --trials 5 --use-wfa 1

주의
- 엔진/전략 소스는 수정하지 않음. 매 Trial은 overlay된 임시 YAML을 CONFIG_PATH로 주입하여 백테스트만 수행.
- Telegram 알림: S(>=80점) 달성 시 메시지 전송(토큰/채팅ID 설정 필요).
"""
from __future__ import annotations
import os
import sys
import re
import json
import yaml
import time
import shutil
from datetime import datetime
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple
import statistics
from dotenv import load_dotenv

# 프로젝트 루트 import (scripts/tuning/ → project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()
args = None

# 내부 유틸
from common.config_merge import deep_merge
from common.metrics_parser import parse_vible_metrics, objective_score, constraints_ok
from common.config_loader import load_yaml_config
from common.messaging import tg
from analytics.report_generator import generate_backtest_report

# Optuna import 가드
try:
    import optuna
    from optuna.pruners import MedianPruner
except Exception as e:
    print("[TUNER] Optuna가 필요합니다. pip install optuna 로 설치하세요.")
    raise


def _ensure_dirs(study_dir: Path, configs_dir: Path):
    """필요한 디렉토리 생성"""
    study_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)


def _run_backtest_with_config(cfg_path: Path, env_overrides: Dict[str, str] | None = None, timeout_sec: int = 900) -> str:
    env = os.environ.copy()
    env['CONFIG_PATH'] = str(cfg_path)
    env['TRADING_MODE'] = 'backtest'
    env['PYTHONIOENCODING'] = 'utf-8'  # 한글 인코딩 강제
    if env_overrides:
        env.update(env_overrides)
    
    # 실행 전 로그 파일 위치 확인
    log_file = project_root / 'logs' / 'application.log'
    log_size_before = log_file.stat().st_size if log_file.exists() else 0
    
    # 단일 명령만, 파이프 없음
    proc = subprocess.run([
        sys.executable, '-u', str(project_root / 'main.py')
    ], cwd=str(project_root), env=env, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=timeout_sec)
    
    # TUNING_VIBLE은 로그 파일에 기록되므로 파일에서 읽기
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(log_size_before)
                new_logs = f.read()
            # TUNING_VIBLE 블록만 추출
            if 'TUNING_VIBLE' in new_logs:
                return new_logs
        except Exception as e:
            print(f"⚠️ 로그 파일 읽기 실패: {e}")
    
    # Fallback: stdout/stderr (비상용)
    out = (proc.stdout or '') + '\n' + (proc.stderr or '')
    return out


def _build_overlay_from_trial(trial: 'optuna.trial.Trial') -> Dict[str, Any]:
    """Reversion 전략용 Overlay 구성"""
    overlay: Dict[str, Any] = {}
    overlay = deep_merge(overlay, {'strategy': {'selector': 'reversion'}})

    # Timeframe & Data: BACKTEST_PERIODS.md 준수 (Reversion = 15m)
    overlay = deep_merge(overlay, {
        'timeframe': '15m',
        'lookback': 400,
        'backtest': {
            'data_file': 'BTCUSDT_15m_2018_WFA01_OOS.csv'  # WFA 자동 감지용 seed
        }
    })

    # Parity flags: ensure offline MTF in backtests and daily-loss enforcement
    overlay = deep_merge(overlay, {'backtest': {'use_offline_mtf': True}})
    overlay = deep_merge(overlay, {'risk': {'enforce_daily_loss_in_backtest': True}})

    # 세션
    session_alias = trial.suggest_categorical('session_whitelist_alias', ['none', 'london', 'london_ny'])
    session_choice = None if session_alias == 'none' else (['London'] if session_alias == 'london' else ['London', 'NY-open'])
    if session_choice is not None:
        overlay = deep_merge(overlay, {
            'filters': {'session_whitelist': session_choice},
            'strategies': {'reversion': {'filters': {'session_whitelist': session_choice}}}
        })
    else:
        # Explicitly disable any default session whitelist from base config
        overlay = deep_merge(overlay, {
            'session_whitelist': [],
            'filters': {'session_whitelist': []},
            'strategies': {'reversion': {'filters': {'session_whitelist': []}}}
        })

    # 가드 (완화: cooldown 0부터 허용)
    overlay = deep_merge(overlay, {
        'cooldown_candles': trial.suggest_int('cooldown_candles', 0, 5),
        'risk': {'max_consecutive_losses': trial.suggest_int('max_consecutive_losses', 3, 6)}
    })

    # Disable global gates that can silently reject signals
    overlay = deep_merge(overlay, {'filters': {'require_trend_align': False}})
    overlay = deep_merge(overlay, {
        'strategies': {'reversion': {'filters': {
            'regime': False,
            'volume_spike': False,
            'mtf_confirm': False
        }}}
    })

    # Reversion 핵심 파라미터 (대폭 완화)
    overlay = deep_merge(overlay, {
        'strategies': {
            'reversion': {
                'rsi_threshold': float(trial.suggest_float('rsi_threshold', 20.0, 50.0)),  # 완화: 25~45 → 20~50
                'bb_lower_pct': float(trial.suggest_float('bb_lower_pct', 0.95, 1.0)),  # 완화: 0.96~1.0 → 0.95~1.0
                'bb_upper_pct': float(trial.suggest_float('bb_upper_pct', 1.0, 1.05)),  # 완화: 1.0~1.04 → 1.0~1.05
                'volume_mult': float(trial.suggest_float('volume_mult', 0.8, 2.0)),  # 완화: 1.0~2.0 → 0.8~2.0
                'filters': {
                    'volume_spike': trial.suggest_categorical('volume_spike', [False]),  # False 고정
                    'trend_context_required': trial.suggest_categorical('trend_context_required', [False]),  # False 고정
                    'allow_short': trial.suggest_categorical('allow_short', [True, False])
                }
            }
        }
    })

    # 공통 RR/Exit (완화: min_rr 1.0부터 허용)
    overlay = deep_merge(overlay, {
        'entries': {'min_rr_required': float(trial.suggest_float('min_rr_required', 1.0, 1.6))},
        'exits': {
            'trailing': {
                'k': float(trial.suggest_float('trail_k', 2.0, 4.0)),
                'move_to_break_even_at_r': float(trial.suggest_float('be_at_r', 0.5, 0.9)),
                'type': 'atr'
            },
            'take_profits': [
                {'r_multiple': 1.0, 'size_pct': 30},
                {'r_multiple': 2.0, 'size_pct': 40}
            ]
        }
    })

    return overlay


def _scan_wfa_oos_files(base_cfg: Dict[str, Any]) -> List[Path]:
    """data_dir에서 OOS 파일 리스트 추출 (15m Reversion전용)"""
    backtest = base_cfg.get('backtest', {})
    data_dir = Path(backtest.get('data_dir', 'data'))
    files: List[Path] = []

    # Reversion은 15m timeframe만 사용
    # 패턴: BTCUSDT_15m_*WFA*OOS*.csv
    search_dirs = [data_dir, data_dir / 'wfa_blocks']
    
    for search_dir in search_dirs:
        if search_dir.exists():
            files.extend(search_dir.glob("BTCUSDT_15m_*WFA*OOS*.csv"))
    
    files = sorted(set(files))  # 중복 제거 및 정렬
    return [p for p in files if p.exists()]


def _write_overlay_config(base_cfg: Dict[str, Any], overlay: Dict[str, Any], out_path: Path) -> None:
    merged = deep_merge(base_cfg, overlay)
    # 강제 백테스트 모드 안전장치
    merged['mode'] = 'backtest'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(merged, f, allow_unicode=True, sort_keys=False)


def objective_builder(base_cfg_path: Path, study_dir: Path, configs_dir: Path, study_name: str, use_wfa: bool, telegram_cfg: Dict[str, Any]):
    base_cfg = load_yaml_config(str(base_cfg_path))
    oos_files = _scan_wfa_oos_files(base_cfg) if use_wfa else []
    try:
        if use_wfa:
            print(f"[OOS] WFA OOS files detected: {len(oos_files)}", flush=True)
            if len(oos_files) < 3:
                print("[OOS][WARN] OOS 세그먼트 파일이 부족합니다. data/BTCUSDT_5m_WFA_*_OOS*.csv 커버리지를 확인하세요.", flush=True)
    except Exception:
        pass

    def objective(trial: 'optuna.trial.Trial') -> float:
        overlay = _build_overlay_from_trial(trial)
        
        # 📊 테스트 중인 파라미터 출력
        print(f"\n  🔧 테스트 파라미터:", flush=True)
        param_items = []
        for key in [
            'session_whitelist_alias', 'cooldown_candles', 'max_consecutive_losses',
            'rsi_threshold', 'bb_lower_pct', 'bb_upper_pct', 'volume_mult',
            'volume_spike', 'trend_context_required', 'allow_short',
            'min_rr_required', 'trail_k', 'be_at_r']:
            if key in trial.params:
                param_items.append(f"{key}={trial.params[key]}")
        if param_items:
            print(f"     {', '.join(param_items)}", flush=True)

        # Trial별 출력 경로 (configs/<strategy>/<study>/)
        cfg_out = configs_dir / f"trial_{trial.number:04d}.yml"
        _write_overlay_config(base_cfg, overlay, cfg_out)

        # 평가 대상 파일들 (WFA-OOS 집계 또는 단일 파일)
        eval_files = oos_files if oos_files else [Path(base_cfg.get('backtest', {}).get('data_file', ''))]
        if not eval_files or not eval_files[0]:
            # data_file 미지정 시, config의 period/custom을 그대로 사용 → 파일 override 없이 실행
            eval_files = [None]

        # 집계 점수 계산
        scores: List[float] = []
        seg_scores: List[float] = []
        seg_grades: List[str] = []
        trades_total = 0
        worst_ok = True
        last_metrics = None

        for idx, data_file in enumerate(eval_files):
            # 📄 파일 처리 시작 표시
            filename = data_file.name if data_file else 'config_default'
            print(f"  📄 [{idx+1}/{len(eval_files)}] {filename}... 백테스트 실행 중", flush=True)

            try:
                # 파일 override용 overlay 복제 (deep copy 필수!)
                cfg_eval = configs_dir / f"trial_{trial.number:04d}_seg{idx+1}.yml"
                seg_overlay = deep_merge({}, overlay)  # Deep copy via deep_merge
                if data_file is not None:
                    seg_overlay = deep_merge(seg_overlay, {'backtest': {'data_file': str(data_file.name)}})
                _write_overlay_config(base_cfg, seg_overlay, cfg_eval)

                # Per-segment SQLite path to avoid contention and prep for Docker
                work_dir = study_dir / 'work'
                work_dir.mkdir(exist_ok=True)
                db_temp = work_dir / f"trial_{trial.number:04d}_seg{idx+1}.db"

                raw = _run_backtest_with_config(cfg_eval, env_overrides={'BACKTEST_DB_PATH': str(db_temp)})
                metrics = parse_vible_metrics(raw)

                            # Fallback: 로그 파싱 실패 시 PostgreSQL에서 직접 조회
            def _metrics_from_db_snapshot() -> Dict[str, Any]:
                try:
                    # ⭐ PostgreSQL trial_id 기반 리포트 생성
                    result = generate_backtest_report(
                        trial_id=trial_id,
                        sinks=["log"]  # 로그만 출력
                    )
                    
                    if result.get('status') != 'success':
                        return metrics
                    
                    total_score = result.get('total_score', 0)
                    m = result.get('metrics', {})
                        # 점수→등급 매핑
                        grade = None
                        if total_score is not None:
                            try:
                                ts = float(total_score)
                                if ts >= 80:
                                    grade = 'S'
                                elif ts >= 70:
                                    grade = 'A'
                                elif ts >= 60:
                                    grade = 'B'
                                elif ts >= 50:
                                    grade = 'C'
                                else:
                                    grade = 'D'
                            except Exception:
                                grade = None

                            return {
                                'score_total': float(total_score) if total_score is not None else None,
                                'grade': grade,
                                'trades': int(m.get('total_trades')) if m.get('total_trades') is not None else None,
                                'win_rr': float(m.get('exp_score')) if m.get('exp_score') is not None else None,
                                'win_rate_pct': float(m.get('winrate')) if m.get('winrate') is not None else None,
                                'rr': float(m.get('rr')) if m.get('rr') is not None else None,
                                'profit_factor': float(m.get('pf')) if m.get('pf') is not None else None,
                                'roi_pct': float(m.get('roi')) if m.get('roi') is not None else None,
                                'mdd_pct': float(m.get('mdd')) if m.get('mdd') is not None else None,
                                'max_losing_streak': int(m.get('consecutive')) if m.get('consecutive') is not None else None,
                            }
                    except Exception:
                        return metrics

                # 모든 주요 키가 None 이거나 거래수가 없으면 DB 기반으로 대체
                if (
                    (metrics.get('trades') in (None, 0)) and
                    all(metrics.get(k) is None for k in ['score_total','profit_factor','roi_pct','mdd_pct','win_rr','rr','win_rate_pct'])
                ):
                    metrics = _metrics_from_db_snapshot()

                last_metrics = metrics

                # 거래수/점수 계산 및 출력 (prune 전에 먼저 출력)
                t = int(metrics.get('trades') or 0)
                trades_total += t
                seg_score = objective_score(metrics)
                win_rate = float(metrics.get('win_rate_pct') or 0.0)
                rr = float(metrics.get('rr') or 0.0)
                pf = float(metrics.get('profit_factor') or 0.0)
                roi = float(metrics.get('roi_pct') or 0.0)
                print(f"     ✅ 완료: Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)

                # Robust 모드: 세그먼트별 최소 거래수 게이트 (prune 사유 출력)
                if (str(getattr(args, 'dod_mode', '')).lower() == 'robust') and int(getattr(args, 'min_trades_oos', 0) or 0) > 0:
                    if t < int(args.min_trades_oos):
                        print(f"     ⚠️ Pruned: 거래 부족 ({t} < {args.min_trades_oos})", flush=True)
                        raise optuna.TrialPruned()
                if t < 10 and len(eval_files) == 1:
                    print(f"     ⚠️ Pruned: 거래 부족 ({t} < 10)", flush=True)
                    raise optuna.TrialPruned()

                # 제약 위반이면 약한 패널티 표시
                if not constraints_ok(metrics):
                    worst_ok = False

                scores.append(seg_score)
                seg_scores.append(seg_score)

                # derive grade if missing
                g = metrics.get('grade')
                if not g:
                    try:
                        ts = float(metrics.get('score_total')) if metrics.get('score_total') is not None else None
                        if ts is not None:
                            if ts >= 80: g = 'S'
                            elif ts >= 70: g = 'A'
                            elif ts >= 60: g = 'B'
                            elif ts >= 50: g = 'C'
                            else: g = 'D'
                    except Exception:
                        g = None
                seg_grades.append(g or '')

            except optuna.exceptions.TrialPruned:
                raise
            except Exception as e:
                print(f"     ❌ 오류: {e} (seg {idx+1}/{len(eval_files)})", flush=True)
                scores.append(0.0)
                seg_scores.append(0.0)
                continue

        # 평균 점수
        score = sum(scores) / max(1, len(scores))
        
        # 등급 계산
        if score >= 80: grade_emoji, grade = "🎉", "S"
        elif score >= 70: grade_emoji, grade = "✅", "A"
        elif score >= 60: grade_emoji, grade = "⚠️", "B"
        elif score >= 50: grade_emoji, grade = "⚠️", "C"
        elif score >= 40: grade_emoji, grade = "❌", "D"
        else: grade_emoji, grade = "❌", "FAIL"
        
        # 🎯 Trial 결과 출력 (매 trial마다)
        print(f"\n  🎯 Trial #{trial.number} 결과:", flush=True)
        print(f"     Score={score:.2f} (avg of {len(scores)} segments)", flush=True)
        print(f"     Total Trades={trades_total}", flush=True)
        print(f"     등급: {grade_emoji} {grade} ({score:.1f}/100)", flush=True)

        # Robust DoD adjustments
        try:
            if str(getattr(args, 'dod_mode', '')).lower() == 'robust' and len(seg_scores) > 0:
                # penalty variance across segments
                try:
                    if len(seg_scores) > 1:
                        var = statistics.pvariance(seg_scores)
                    else:
                        var = 0.0
                except Exception:
                    var = 0.0
                lam = float(getattr(args, 'penalty_variance', 0.0) or 0.0)
                score -= lam * var

                # regime-min grade gate (use per-segment grade minimum)
                thr = str(getattr(args, 'penalty_regime_min', '')).upper().strip()
                if thr in ('S','A','B','C','D'):
                    order = {'D':1,'C':2,'B':3,'A':4,'S':5}
                    min_g = None
                    for g in seg_grades:
                        if g in order:
                            v = order[g]
                        else:
                            v = 0
                        min_g = v if min_g is None else min(min_g, v)
                    if min_g is None:
                        raise optuna.TrialPruned()
                    if min_g < order[thr]:
                        raise optuna.TrialPruned()
        except optuna.exceptions.TrialPruned:
            raise
        except Exception:
            pass

        # S 달성 알림 (토큰/채널 유효 + enable_telegram일 때만)
        if last_metrics and (last_metrics.get('score_total') and float(last_metrics['score_total']) >= 80.0):
            if telegram_cfg.get('telegram_token') and telegram_cfg.get('telegram_chat_id') and telegram_cfg.get('enable_telegram'):
                tg(f"🎉 S 달성: {last_metrics['score_total']}점 / 거래 {last_metrics.get('trades')}건", telegram_cfg)

        # 제약 실패 시 패널티
        if not worst_ok:
            score *= 0.5

        # 너무 적은 표본은 prune
        if trades_total < 15 and len(eval_files) == 1:
            raise optuna.TrialPruned()

        # Trial 산출물 저장 (logs/tuning/trial_<study>_<trial>.json)
        try:
            logs_dir = project_root / 'logs' / 'tuning'
            logs_dir.mkdir(parents=True, exist_ok=True)
            out_json = logs_dir / f"trial_{study_name}_{trial.number:04d}.json"
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump({'metrics': last_metrics, 'score': score}, f, ensure_ascii=False)
        except Exception:
            pass

        return float(score)

    return objective


def save_best_config(study: 'optuna.Study', base_cfg_path: Path, study_dir: Path) -> Path:
    # Robust best trial selection: only COMPLETE trials
    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    if not completed_trials:
        raise ValueError("No completed trials found")
    best = max(completed_trials, key=lambda t: t.value if t.value is not None else float('-inf'))
    
    overlay = _build_overlay_from_trial(best)
    base_cfg = load_yaml_config(str(base_cfg_path))
    # configs 폴더 활용 (기존 구조 유지)
    out_path = project_root / 'configs' / f'best_reversion_{study.study_name}.yml'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_overlay_config(base_cfg, overlay, out_path)
    # 백업 복사
    shutil.copy2(out_path, study_dir / f"best_trial_{best.number:04d}.yml")
    return out_path


def append_checklist(metrics: Dict[str, Any], study_name: str, trial_num: int) -> None:
    path = project_root / 'docs' / 'PHASE3' / 'TEST_CHECKLIST.md'
    try:
        line = (
            f"- [auto] study={study_name} trial={trial_num} "
            f"score={metrics.get('score_total')} grade={metrics.get('grade')} "
            f"PF={metrics.get('profit_factor')} ROI={metrics.get('roi_pct')}% "
            f"MDD={metrics.get('mdd_pct')}% Trades={metrics.get('trades')}\n"
        )
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def main():
    print("=" * 80, flush=True)
    print("🚀 REVERSION TUNER 시작", flush=True)
    print("=" * 80, flush=True)
    
    ap = argparse.ArgumentParser()
    ap.add_argument('--study', default='reversion_v1')
    ap.add_argument('--trials', type=int, default=5)
    ap.add_argument('--use-wfa', type=int, default=1)
    ap.add_argument('--notify-progress', type=int, default=0)
    ap.add_argument('--notify-completion', type=int, default=1)
    ap.add_argument('--early-stop-grade', type=str, default='')
    ap.add_argument('--apply-best', type=int, default=0)
    ap.add_argument('--optuna-storage', type=str, default='')
    # Robust DoD options
    ap.add_argument('--dod-mode', type=str, default='', help="robust 모드 활성화")
    ap.add_argument('--min-trades-oos', type=int, default=0, help='OOS 세그먼트별 최소 거래수')
    ap.add_argument('--penalty-variance', type=float, default=0.0, help='세그먼트 간 분산 패널티')
    ap.add_argument('--penalty-regime-min', type=str, default='', help='세그먼트 최소 등급 게이트 (S/A/B/C/D)')
    ap.add_argument('--add-timestamp', type=int, default=1, help='Study 이름에 타임스탬프 추가')
    args = ap.parse_args()
    
    study_name = args.study
    if args.add_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        study_name = f"{args.study}_{timestamp}"
    
    print(f"📋 Args: study={study_name}, trials={args.trials}, wfa={args.use_wfa}", flush=True)
    study_dir = project_root / 'logs' / 'tuning' / study_name
    configs_dir = project_root / 'configs' / 'reversion' / study_name
    _ensure_dirs(study_dir, configs_dir)

    base_cfg_path = project_root / 'config.yml'
    base_cfg = load_yaml_config(str(base_cfg_path))

    # Telegram 설정 추출 (config.yml → env fallback)
    telegram_cfg = {
        'telegram_token': base_cfg.get('telegram_token') or os.getenv('TELEGRAM_TOKEN', ''),
        'telegram_chat_id': base_cfg.get('telegram_chat_id') or os.getenv('TELEGRAM_CHAT_ID', ''),
        'system_name': base_cfg.get('system_name', os.getenv('SYSTEM_NAME', 'TRADING')),
        'enable_telegram': bool(base_cfg.get('enable_telegram', os.getenv('ENABLE_TELEGRAM', 'false').lower() in ('1','true','yes'))),
    }

    # Optuna Study (allow external storage override for Docker/Postgres)
    storage = args.optuna_storage if args.optuna_storage else f"sqlite:///{study_dir / 'study.db'}"
    # Start notification (optional)
    try:
        if args.notify_progress and telegram_cfg.get('enable_telegram') and telegram_cfg.get('telegram_token') and telegram_cfg.get('telegram_chat_id'):
            from common.messaging import send_telegram
            storage_type = "Postgres" if "postgresql://" in storage else "SQLite"
            system_name = telegram_cfg.get('system_name', 'REVERSION_TUNER')
            msg = f"[{system_name}] START {args.study} | trials={args.trials} wfa={args.use_wfa} storage={storage_type}"
            send_telegram(msg, telegram_cfg['telegram_token'], telegram_cfg['telegram_chat_id'], parse_mode=None)
    except Exception:
        pass
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction='maximize',
        load_if_exists=False,  # 각 실행 독립
        pruner=MedianPruner(n_startup_trials=3, n_warmup_steps=0)
    )

    objective = objective_builder(base_cfg_path, study_dir, configs_dir, study_name, use_wfa=bool(args.use_wfa), telegram_cfg=telegram_cfg)

    start_ts = time.time()
    consecutive_low_trades = 0  # 연속 거래 부족 카운터
    last_notified_score = None  # 마지막 알림 점수
    last_notified_grade = None  # 마지막 알림 등급
    
    print(f"\n🔄 Trial 루프 시작: {args.trials}회 반복", flush=True)
    for i in range(args.trials):
        print(f"\n{'='*60}", flush=True)
        print(f"📊 Trial {i+1}/{args.trials} 시작...", flush=True)
        print(f"{'='*60}", flush=True)
        try:
            print(f"  ⏳ Optuna ask()...", flush=True)
            trial = study.ask()
            print(f"  ✅ Trial #{trial.number} 생성됨", flush=True)
            print(f"  🚀 Objective 실행 중...", flush=True)
            value = objective(trial)
            print(f"  ✅ Objective 완료: score={value:.2f}", flush=True)
            study.tell(trial, value)
            print(f"  ✅ Trial 결과 저장 완료", flush=True)
            
            # 거래 부족 체크 (자동 종료)
            try:
                logs_dir = project_root / 'logs' / 'tuning'
                meta_path = logs_dir / f"trial_{args.study}_{trial.number:04d}.json"
                if meta_path.exists():
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    trades = meta.get('metrics', {}).get('trades', 0)
                    if trades < 10:
                        consecutive_low_trades += 1
                        if consecutive_low_trades >= 5:
                            msg = f"[WARNING] 연속 5회 거래 부족(<10건). 탐색 공간 문제 가능성. 종료 권장."
                            print(msg)
                            if telegram_cfg.get('enable_telegram') and telegram_cfg.get('telegram_token'):
                                tg(msg, telegram_cfg)
                            break
                    else:
                        consecutive_low_trades = 0
            except Exception:
                pass
            # 체크리스트 업데이트 (가능할 때만)
            try:
                logs_dir = project_root / 'logs' / 'tuning'
                meta_path = logs_dir / f"trial_{args.study}_{trial.number:04d}.json"
                if meta_path.exists():
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    append_checklist(meta.get('metrics') or {}, args.study, trial.number)
            except Exception:
                pass

            # 진행 알림 (옵션 - 중요 변화시만)
            try:
                if args.notify_progress and telegram_cfg.get('enable_telegram') and telegram_cfg.get('telegram_token') and telegram_cfg.get('telegram_chat_id'):
                    logs_dir = project_root / 'logs' / 'tuning'
                    best = study.best_trial
                    best_meta = {}
                    best_meta_path = logs_dir / f"trial_{args.study}_{best.number:04d}.json"
                    if best_meta_path.exists():
                        with open(best_meta_path, 'r', encoding='utf-8') as f:
                            best_meta = json.load(f)
                    m = best_meta.get('metrics', {})
                    score_total = m.get('score_total')
                    grade = m.get('grade')
                    roi = m.get('roi_pct')
                    pf = m.get('profit_factor')
                    mdd = m.get('mdd_pct')
                    trades = m.get('trades')

                    # 알림 필터: 점수 5점 이상 개선 or 등급 변경 or S 달성
                    should_notify = False
                    if score_total is not None:
                        if last_notified_score is None:
                            should_notify = True  # 첫 알림
                        elif grade == 'S' and last_notified_grade != 'S':
                            should_notify = True  # S 달성
                        elif grade != last_notified_grade:
                            should_notify = True  # 등급 변경
                        elif abs(float(score_total) - float(last_notified_score or 0)) >= 5.0:
                            should_notify = True  # 5점 이상 개선

                    if should_notify:
                        progress_pct = int(round(((i + 1) / args.trials) * 100))
                        elapsed = max(1.0, time.time() - start_ts)
                        rate = elapsed / (i + 1)
                        remain_sec = max(0.0, (args.trials - (i + 1)) * rate)
                        eta_min = int(remain_sec // 60)
                        eta_sec = int(remain_sec % 60)
                        gap_to_S = None
                        if score_total is not None:
                            try:
                                gap_to_S = max(0.0, 80.0 - float(score_total))
                            except Exception:
                                gap_to_S = None
                        msg = (
                            f"📊 [TUNING] {args.study} {i+1}/{args.trials} ({progress_pct}%)\n"
                            f"🏆 Best: {score_total:.1f}점 ({grade}등급) | 거래 {trades}건\n"
                            f"💰 ROI {roi:.1f}% | PF {pf:.2f} | MDD {mdd:.1f}%\n"
                            f"⏱ ETA ~{eta_min}m{eta_sec}s" + (f" | S까지 {gap_to_S:.1f}점" if gap_to_S is not None and gap_to_S > 0 else "")
                        )
                        tg(msg, telegram_cfg)
                        last_notified_score = score_total
                        last_notified_grade = grade
            except Exception:
                pass

            # 조기 종료 (옵션)
            try:
                if args.early_stop_grade and args.early_stop_grade.upper() not in ('OFF','NONE','0'):
                    grade_threshold = {'S': 80.0, 'A': 70.0, 'B': 60.0, 'C': 50.0}.get(args.early_stop_grade.upper())
                    if grade_threshold is not None:
                        logs_dir = project_root / 'logs' / 'tuning'
                        best = study.best_trial
                        best_meta_path = logs_dir / f"trial_{args.study}_{best.number:04d}.json"
                        if best_meta_path.exists():
                            with open(best_meta_path, 'r', encoding='utf-8') as f:
                                best_meta = json.load(f)
                            score_total = best_meta.get('metrics', {}).get('score_total')
                            if score_total is not None and float(score_total) >= grade_threshold:
                                break
            except Exception:
                pass
        except optuna.exceptions.TrialPruned:
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
        except Exception as e:
            # 실패 Trial은 NaN으로 마킹
            study.tell(trial, state=optuna.trial.TrialState.FAIL)
        time.sleep(0.1)

    # Best 저장
    best_cfg_path = None
    try:
        if len(study.trials) > 0:
            best_cfg_path = save_best_config(study, base_cfg_path, study_dir)
            print(f"[TUNER] Best config saved -> {best_cfg_path}", flush=True)
        else:
            print(f"[TUNER] No trials completed, skipping best config save", flush=True)
    except Exception as e:
        print(f"[TUNER] Best config save failed: {e}", flush=True)

    # 베스트 자동 승격 (옵션)
    try:
        if args.apply_best:
            dest = project_root / 'configs' / 'best_reversion.yml'
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(best_cfg_path, dest)
    except Exception:
        pass

    # 완료 알림 (옵션)
    try:
        if args.notify_completion and telegram_cfg.get('enable_telegram') and telegram_cfg.get('telegram_token') and telegram_cfg.get('telegram_chat_id'):
            logs_dir = project_root / 'logs' / 'tuning'
            best = study.best_trial
            best_meta = {}
            best_meta_path = logs_dir / f"trial_{args.study}_{best.number:04d}.json"
            if best_meta_path.exists():
                with open(best_meta_path, 'r', encoding='utf-8') as f:
                    best_meta = json.load(f)
            m = best_meta.get('metrics', {})
            msg = (
                f"[DONE] {args.study} best={m.get('score_total')}({m.get('grade')}) "
                f"ROI={m.get('roi_pct')}% PF={m.get('profit_factor')} MDD={m.get('mdd_pct')}% T={m.get('trades')}\n"
                f"saved={best_cfg_path}"
            )
            if args.apply_best:
                msg += " | applied=configs/best_reversion.yml"
            tg(msg, telegram_cfg)
    except Exception:
        pass


if __name__ == '__main__':
    main()
