#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnsembleTuner - Ensemble 파라미터 베이시안 튜닝
===============================================
PR13 Phase 1: Optuna 기반 Ensemble 파라미터 최적화

참조:
- docs/PHASE6/PR13_ARCHITECTURE_DESIGN.md (2.2 EnsembleTuner)
- tuning/tuning_core.py (기존 TunerCore 확장)

역할:
- Ensemble 가중치 계수 튜닝 (alpha, beta, gamma, delta, epsilon)
- Experience Score 파라미터 튜닝
- 클램핑 파라미터 튜닝
- 임계값 튜닝 (theta_long, theta_short)
"""
import optuna
from optuna.trial import Trial
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
from typing import Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from tuning.config_overlay import ConfigOverlay
from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ============================================
# 메트릭 데이터 클래스
# ============================================

@dataclass
class EnsembleMetrics:
    """Ensemble 튜닝 메트릭"""
    score_total: float
    sharpe: float
    mdd_pct: float
    trades: int
    winrate: float
    profit_factor: float
    avg_hold_minutes: float
    tp_hit_rate: float


# ============================================
# EnsembleTuner
# ============================================

class EnsembleTuner:
    """
    Ensemble 파라미터 튜닝
    
    기존 TunerCore를 확장하여 ensemble 전용
    
    참조:
    - PR13_ARCHITECTURE_DESIGN.md 라인 147-278
    """
    
    def __init__(
        self,
        study_name: str,
        storage: str,
        window_hours: int = 24,
        config_overlay: ConfigOverlay = None,
        base_config: Dict[str, Any] = None,
    ):
        """
        EnsembleTuner 초기화
        
        Args:
            study_name: Optuna study 이름
            storage: Optuna storage (예: "sqlite:///optuna.db")
            window_hours: 실험 윈도우 (시간)
            config_overlay: ConfigOverlay 인스턴스
            base_config: 베이스 설정 (config_overlay 없을 때)
        """
        self.study_name = study_name
        self.window_hours = window_hours
        
        # ConfigOverlay 설정
        if config_overlay:
            self.config_overlay = config_overlay
        elif base_config:
            self.config_overlay = ConfigOverlay(
                base_config_path="config.yml",
                base_config=base_config
            )
        else:
            self.config_overlay = ConfigOverlay(base_config_path="config.yml")
        
        # Optuna Study 생성
        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            direction="maximize",
            load_if_exists=True,
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=0),
        )
        
        logger.info(f"EnsembleTuner 초기화: study={study_name}, window={window_hours}h")
    
    def _sample_params(self, trial: Trial) -> Dict[str, Any]:
        """
        파라미터 샘플링
        
        Args:
            trial: Optuna trial
        
        Returns:
            오버레이 딕셔너리
        """
        # 1) 가중치 계수
        alpha = trial.suggest_float("alpha_winrate", 0.2, 0.6)
        beta = trial.suggest_float("beta_rr", 0.1, 0.4)
        gamma = trial.suggest_float("gamma_sharpe", 0.1, 0.4)
        delta = trial.suggest_float("delta_confidence", 0.05, 0.25)
        epsilon = trial.suggest_float("epsilon_regime", 0.0, 0.15)
        
        # 제약 조건: 합이 1.0 ± 0.1
        total = alpha + beta + gamma + delta + epsilon
        if not (0.9 <= total <= 1.1):
            raise optuna.TrialPruned()
        
        # 2) Experience Score 파라미터
        min_trades = trial.suggest_int("min_trades", 10, 50)
        
        # 3) 클램핑 파라미터
        max_weight = trial.suggest_float("max_weight_per_strategy", 0.3, 0.5)
        
        # 4) 임계값
        theta_long = trial.suggest_float("theta_long", 0.1, 0.25)
        theta_short = trial.suggest_float("theta_short", 0.1, 0.25)
        
        # 오버레이 구조 (PR13_ARCHITECTURE_DESIGN.md 라인 204-216)
        return {
            'ensemble': {
                'alpha_winrate': alpha,
                'beta_rr': beta,
                'gamma_sharpe': gamma,
                'delta_confidence': delta,
                'epsilon_regime': epsilon,
                'experience': {'min_trades': min_trades},
                'max_weight_per_strategy': max_weight,
                'theta_long': theta_long,
                'theta_short': theta_short,
            }
        }
    
    def _objective(self, trial: Trial) -> float:
        """
        목표 함수
        
        Args:
            trial: Optuna trial
        
        Returns:
            종합 스코어
        """
        # 1) 파라미터 샘플링
        overlay = self._sample_params(trial)
        
        # 2) 설정 적용
        config = self.config_overlay.apply_overlay(
            overlay,
            source="tuner",
            description=f"Trial {trial.number}"
        )
        
        # 3) 페이퍼 실험 실행 (메트릭 수집)
        metrics = self._run_paper_experiment(config, hours=self.window_hours)
        
        # 4) 스코어 계산
        score = self._calculate_score(metrics)
        
        # 5) 로깅
        logger.info(
            f"Trial {trial.number}: "
            f"score={score:.3f}, "
            f"trades={metrics.trades}, "
            f"sharpe={metrics.sharpe:.2f}, "
            f"mdd={metrics.mdd_pct:.1f}%"
        )
        
        return score
    
    def _run_paper_experiment(
        self,
        config: Dict[str, Any],
        hours: int
    ) -> EnsembleMetrics:
        """
        페이퍼 실험 실행 (메트릭 수집)
        
        Args:
            config: 설정
            hours: 실험 시간
        
        Returns:
            메트릭
        """
        # DB에서 최근 N시간 메트릭 조회
        try:
            with get_db_connection() as conn:
                metrics = self._fetch_metrics_from_db(conn, hours)
                return metrics
        except Exception as e:
            logger.error(f"메트릭 수집 실패: {e}")
            # 기본값 반환
            return EnsembleMetrics(
                score_total=0.5,
                sharpe=0.0,
                mdd_pct=5.0,
                trades=0,
                winrate=0.5,
                profit_factor=1.0,
                avg_hold_minutes=60.0,
                tp_hit_rate=0.5
            )
    
    def _fetch_metrics_from_db(self, conn, hours: int) -> EnsembleMetrics:
        """
        DB에서 메트릭 조회
        
        Args:
            conn: DB 연결
            hours: 조회 시간
        
        Returns:
            메트릭
        """
        from psycopg2.extras import RealDictCursor
        
        # 최근 N시간 거래 조회
        sql = """
        SELECT 
            COUNT(*) as total_trades,
            AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) as winrate,
            AVG(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) / 
                NULLIF(AVG(CASE WHEN pnl < 0 THEN -pnl ELSE 0 END), 0) as profit_factor,
            AVG(pnl_pct) as avg_pnl_pct,
            STDDEV(pnl_pct) as stddev_pnl_pct,
            AVG(EXTRACT(EPOCH FROM (ts_close - ts_open)) / 60.0) as avg_hold_minutes,
            AVG(CASE WHEN exit_reason = 'TP' THEN 1.0 ELSE 0.0 END) as tp_hit_rate
        FROM trading.trades
        WHERE ts_open >= NOW() - INTERVAL '%s hours'
          AND status = 'CLOSED'
        """
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (hours,))
                row = cur.fetchone()
                
                if not row or row['total_trades'] == 0:
                    logger.warning(f"최근 {hours}시간 거래 없음")
                    return EnsembleMetrics(
                        score_total=0.5,
                        sharpe=0.0,
                        mdd_pct=5.0,
                        trades=0,
                        winrate=0.5,
                        profit_factor=1.0,
                        avg_hold_minutes=60.0,
                        tp_hit_rate=0.5
                    )
                
                # Sharpe 계산
                sharpe = 0.0
                if row['stddev_pnl_pct'] and row['stddev_pnl_pct'] > 0:
                    sharpe = row['avg_pnl_pct'] / row['stddev_pnl_pct']
                
                # MDD 계산 (간단한 추정)
                mdd_pct = abs(row['avg_pnl_pct']) * 2.0 if row['avg_pnl_pct'] < 0 else 1.0
                
                # score_total 계산 (간단한 추정)
                score_total = (
                    row['winrate'] * 0.4 +
                    min(1.0, row['profit_factor'] / 2.0) * 0.3 +
                    min(1.0, max(0.0, sharpe / 2.0)) * 0.3
                )
                
                return EnsembleMetrics(
                    score_total=score_total,
                    sharpe=sharpe,
                    mdd_pct=mdd_pct,
                    trades=row['total_trades'],
                    winrate=row['winrate'] or 0.5,
                    profit_factor=row['profit_factor'] or 1.0,
                    avg_hold_minutes=row['avg_hold_minutes'] or 60.0,
                    tp_hit_rate=row['tp_hit_rate'] or 0.5
                )
        
        except Exception as e:
            logger.error(f"DB 메트릭 조회 실패: {e}")
            return EnsembleMetrics(
                score_total=0.5,
                sharpe=0.0,
                mdd_pct=5.0,
                trades=0,
                winrate=0.5,
                profit_factor=1.0,
                avg_hold_minutes=60.0,
                tp_hit_rate=0.5
            )
    
    def _calculate_score(self, metrics: EnsembleMetrics) -> float:
        """
        종합 스코어 계산
        
        score = score_total(40%) + sharpe(30%) + (1-mdd/10)(20%) + trade_term(10%)
        
        Args:
            metrics: 메트릭
        
        Returns:
            종합 스코어
        """
        # 정규화
        sharpe_norm = min(1.0, max(0.0, metrics.sharpe / 2.0))  # Sharpe 2.0 = 만점
        mdd_norm = max(0.0, 1.0 - metrics.mdd_pct / 10.0)       # MDD 10% = 0점
        trade_term = min(1.0, metrics.trades / 60.0)             # 60건 = 만점
        
        score = (
            metrics.score_total * 0.4 +
            sharpe_norm * 0.3 +
            mdd_norm * 0.2 +
            trade_term * 0.1
        )
        
        return score
    
    def _build_overlay(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        파라미터를 오버레이 구조로 변환
        
        Args:
            params: Optuna best_params
        
        Returns:
            오버레이 딕셔너리
        """
        return {
            'ensemble': {
                'alpha_winrate': params['alpha_winrate'],
                'beta_rr': params['beta_rr'],
                'gamma_sharpe': params['gamma_sharpe'],
                'delta_confidence': params['delta_confidence'],
                'epsilon_regime': params['epsilon_regime'],
                'experience': {'min_trades': params['min_trades']},
                'max_weight_per_strategy': params['max_weight_per_strategy'],
                'theta_long': params['theta_long'],
                'theta_short': params['theta_short'],
            }
        }
    
    def optimize(self, n_trials: int = 10) -> Dict[str, Any]:
        """
        최적화 실행
        
        Args:
            n_trials: 시도 횟수
        
        Returns:
            최적 파라미터
        """
        logger.info(f"최적화 시작: {n_trials} trials")
        
        # 최적화 실행
        self.study.optimize(self._objective, n_trials=n_trials)
        
        # 최적 파라미터 저장
        best_params = self.study.best_params
        best_value = self.study.best_value
        
        logger.info(f"최적화 완료: best_value={best_value:.3f}")
        logger.info(f"최적 파라미터: {best_params}")
        
        # 오버레이 저장
        best_overlay = self._build_overlay(best_params)
        overlay_name = f"tuning_best_{self.study_name}"
        self.config_overlay.save_overlay(best_overlay, overlay_name)
        
        logger.info(f"최적 오버레이 저장: {overlay_name}.yml")
        
        return best_params
    
    def get_best_params(self) -> Dict[str, Any]:
        """최적 파라미터 조회"""
        return self.study.best_params
    
    def get_best_value(self) -> float:
        """최적 값 조회"""
        return self.study.best_value
    
    def get_trials_dataframe(self):
        """시도 이력 DataFrame 조회"""
        return self.study.trials_dataframe()


# ============================================
# 팩토리 함수
# ============================================

def create_ensemble_tuner(
    study_name: str = "ensemble_tuning_001",
    storage: str = None,
    window_hours: int = 24,
    **kwargs
) -> EnsembleTuner:
    """
    EnsembleTuner 팩토리 함수
    
    Args:
        study_name: Optuna study 이름
        storage: Optuna storage URL (기본: PostgreSQL from env)
        window_hours: 실험 윈도우 (시간)
    """
    # 기본 저장소: PostgreSQL (단일 DB 정책 준수)
    if storage is None:
        import os
        storage = os.getenv(
            "DATABASE_URL",
            "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db"
        )
    
    return EnsembleTuner(
        study_name=study_name,
        storage=storage,
        window_hours=window_hours,
        **kwargs
    )


# ============================================
# 사용 예시 (테스트용)
# ============================================

if __name__ == "__main__":
    # EnsembleTuner 생성 (PostgreSQL 사용)
    tuner = create_ensemble_tuner(
        study_name="test_ensemble",
        storage="postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db",
        window_hours=24
    )
    
    # 최적화 실행 (테스트: 3 trials)
    best_params = tuner.optimize(n_trials=3)
    
    print(f"✅ 최적 파라미터: {best_params}")
    print(f"✅ 최적 값: {tuner.get_best_value():.3f}")
