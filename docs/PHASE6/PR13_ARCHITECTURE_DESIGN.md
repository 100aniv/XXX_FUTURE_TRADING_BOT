# PR13 — 아키텍처 설계

> **작성일**: 2025-11-06 18:45  
> **목적**: 상용급 베이시안 튜닝 & 롤아웃 아키텍처 설계  
> **참조**: MLflow, Optuna, LaunchDarkly (Feature Flag)

---

## 🏗️ 1. 전체 아키텍처

### 1.1 시스템 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                   Trading Bot System                         │
│                   (main.py → engine.py)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼────────┐             ┌─────▼──────────┐
   │   CONFIG    │             │    ENSEMBLE    │
   │  MANAGER    │◄────────────│    ENGINE      │
   │  (오버레이)  │             │ (strategies/)  │
   └────┬────────┘             └────────────────┘
        │
        │  ┌────────────────────────────────────┐
        │  │         TUNING SYSTEM              │
        │  ├────────────────────────────────────┤
        └──►  ConfigOverlay                     │
           │  EnsembleTuner (Optuna)            │
           │  RolloutManager                     │
           │  GuardrailEngine                   │
           └────────┬───────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
   ┌────▼─────────┐      ┌─────▼──────────┐
   │  ANALYTICS   │      │   DATABASE     │
   │  (AB Report) │      │  (Postgres)    │
   └──────────────┘      └────────────────┘
```

---

## 🔧 2. 핵심 컴포넌트

### 2.1 ConfigOverlay

**책임**: 설정 오버레이 및 머지

```python
# tuning/config_overlay.py
class ConfigOverlay:
    """
    설정 오버레이 시스템
    
    역할:
    - 베이스 설정 로드
    - 오버레이 적용 및 검증
    - 히스토리 추적
    """
    
    def __init__(self, base_config_path: str = "config.yml"):
        self.base_config = self._load_base(base_config_path)
        self.overlays: List[Dict] = []
        self.active_overlay: Optional[Dict] = None
    
    def load_overlay(self, overlay_path: str) -> Dict:
        """오버레이 파일 로드 및 검증"""
        overlay = yaml.safe_load(Path(overlay_path).read_text())
        self._validate_overlay(overlay)
        return overlay
    
    def apply_overlay(self, overlay: Dict) -> Dict:
        """오버레이 적용 (deep merge)"""
        merged = deep_merge(self.base_config, overlay)
        self._validate_config(merged)
        self.active_overlay = overlay
        return merged
    
    def save_overlay(self, overlay: Dict, name: str):
        """오버레이 저장"""
        path = Path(f"configs/overlays/{name}.yml")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(overlay))
        
        # 메타데이터 저장
        self._save_metadata(name, overlay)
```

**파일 구조**:
```
configs/
├── base/
│   └── config.yml                    # 베이스 설정 (불변)
├── overlays/
│   ├── tuning_baseline.yml           # 베이스라인
│   ├── tuning_trial_001.yml          # 실험 1
│   ├── tuning_trial_002.yml          # 실험 2
│   └── tuning_best.yml               # 최적 파라미터
└── active/
    └── current.yml                    # 현재 활성화
```

---

### 2.2 EnsembleTuner

**책임**: Ensemble 파라미터 베이시안 튜닝

```python
# tuning/ensemble_tuner.py
class EnsembleTuner:
    """
    Ensemble 파라미터 튜닝
    
    기존 TunerCore를 확장하여 ensemble 전용
    """
    
    def __init__(
        self,
        study_name: str,
        storage: str,
        window_hours: int = 24,
        config_overlay: ConfigOverlay,
    ):
        self.config_overlay = config_overlay
        self.window_hours = window_hours
        
        # Optuna Study 생성
        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            direction="maximize",
            load_if_exists=True,
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=0),
        )
    
    def _sample_params(self, trial: Trial) -> Dict:
        """파라미터 샘플링"""
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
        """목표 함수"""
        # 1) 파라미터 샘플링
        overlay = self._sample_params(trial)
        
        # 2) 설정 적용
        config = self.config_overlay.apply_overlay(overlay)
        
        # 3) 페이퍼 실험 실행 (24시간)
        metrics = self._run_paper_experiment(config, hours=self.window_hours)
        
        # 4) 스코어 계산
        score = self._calculate_score(metrics)
        
        # 5) 로깅
        logger.info(
            f"Trial {trial.number}: "
            f"score={score:.3f}, "
            f"trades={metrics['trades']}, "
            f"sharpe={metrics['sharpe']:.2f}, "
            f"mdd={metrics['mdd_pct']:.1f}%"
        )
        
        return score
    
    def _calculate_score(self, metrics: Dict) -> float:
        """
        종합 스코어 계산
        
        score = score_total(40%) + sharpe(30%) + (1-mdd/10)(20%) + trade_term(10%)
        """
        score_total = metrics.get('score_total', 0.5)
        sharpe = metrics.get('sharpe', 0.0)
        mdd_pct = metrics.get('mdd_pct', 0.0)
        trades = metrics.get('trades', 0)
        
        # 정규화
        sharpe_norm = min(1.0, max(0.0, sharpe / 2.0))  # Sharpe 2.0 = 만점
        mdd_norm = max(0.0, 1.0 - mdd_pct / 10.0)       # MDD 10% = 0점
        trade_term = min(1.0, trades / 60.0)             # 60건 = 만점
        
        score = (
            score_total * 0.4 +
            sharpe_norm * 0.3 +
            mdd_norm * 0.2 +
            trade_term * 0.1
        )
        
        return score
    
    def optimize(self, n_trials: int = 10):
        """최적화 실행"""
        self.study.optimize(self._objective, n_trials=n_trials)
        
        # 최적 파라미터 저장
        best_params = self.study.best_params
        best_overlay = self._build_overlay(best_params)
        self.config_overlay.save_overlay(best_overlay, f"tuning_best_{self.study.study_name}")
        
        return best_params
```

---

### 2.3 RolloutManager

**책임**: 롤아웃 단계 관리 및 트래픽 분할

```python
# tuning/rollout_manager.py
class RolloutManager:
    """
    롤아웃 관리자
    
    모드:
    - none: 튜닝 비활성화
    - shadow: 계산만 (실제 사용 안 함)
    - canary: 단계적 트래픽 분할 (10%→30%→50%→100%)
    - full: 전체 적용
    """
    
    def __init__(
        self,
        config: Dict,
        guardrail_engine: GuardrailEngine,
        config_overlay: ConfigOverlay,
    ):
        self.mode = config['tuning']['mode']
        self.guardrail = guardrail_engine
        self.config_overlay = config_overlay
        
        # 카나리 설정
        self.canary_stages = config['tuning']['rollout']['canary']['stages']
        self.current_stage_idx = 0
        self.stage_started_at = None
        
        # 히스토리
        self.stage_history: List[RolloutStage] = []
    
    def should_use_tuned_config(self, decision_id: str) -> bool:
        """
        튜닝된 설정 사용 여부 결정
        
        Args:
            decision_id: 의사결정 고유 ID (해시 기반 분할용)
        
        Returns:
            True: 튜닝된 설정 사용
            False: 베이스라인 설정 사용
        """
        if self.mode == 'none':
            return False
        
        if self.mode == 'shadow':
            # 섀도우 모드: 계산만 하고 실제 사용 안 함
            # (별도 로직에서 A/B 비교용 메트릭 수집)
            return False
        
        if self.mode == 'canary':
            # 카나리 모드: 단계별 트래픽 분할
            traffic_pct = self._get_current_traffic_pct()
            hash_val = self._hash_decision(decision_id)
            return hash_val < traffic_pct
        
        if self.mode == 'full':
            return True
        
        return False
    
    def _get_current_traffic_pct(self) -> float:
        """현재 트래픽 비율 조회"""
        if self.current_stage_idx >= len(self.canary_stages):
            return 100.0
        return self.canary_stages[self.current_stage_idx] / 100.0
    
    def _hash_decision(self, decision_id: str) -> float:
        """의사결정 ID 해시 (0.0~1.0)"""
        import hashlib
        hash_bytes = hashlib.md5(decision_id.encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:4], 'big')
        return hash_int / (2**32)
    
    def check_and_advance_stage(self):
        """
        단계 체크 및 진행
        
        가드레일 통과 시 다음 단계로 진행
        실패 시 롤백
        """
        if self.mode != 'canary':
            return
        
        # 단계 시작 후 최소 대기 시간
        if self.stage_started_at:
            elapsed_hours = (datetime.now() - self.stage_started_at).total_seconds() / 3600
            min_hours = self.config['tuning']['rollout']['canary']['stage_duration_hours']
            
            if elapsed_hours < min_hours:
                logger.info(f"⏳ 단계 {self.current_stage_idx} 대기 중 ({elapsed_hours:.1f}h / {min_hours}h)")
                return
        
        # 가드레일 체크
        ok, reason = self.guardrail.check()
        
        if ok:
            # 다음 단계로
            self._advance_stage()
        else:
            # 롤백
            self._rollback(reason)
    
    def _advance_stage(self):
        """다음 단계로 진행"""
        if self.current_stage_idx >= len(self.canary_stages) - 1:
            # 마지막 단계 → full 모드로
            self.mode = 'full'
            logger.info("✅ 카나리 롤아웃 완료 → full 모드 전환")
            return
        
        self.current_stage_idx += 1
        self.stage_started_at = datetime.now()
        
        traffic_pct = self.canary_stages[self.current_stage_idx]
        logger.info(f"📈 단계 {self.current_stage_idx} 진행: {traffic_pct}% 트래픽")
        
        # 히스토리 기록
        self._record_stage_success()
    
    def _rollback(self, reason: str):
        """롤백"""
        logger.error(f"🔴 롤백 실행: {reason}")
        
        # 이전 단계로
        if self.current_stage_idx > 0:
            self.current_stage_idx -= 1
        else:
            # 베이스라인으로
            self.mode = 'none'
        
        # 히스토리 기록
        self._record_stage_failure(reason)
        
        # 알림
        self._notify_rollback(reason)
```

---

### 2.4 GuardrailEngine

**책임**: 가드레일 체크 및 위반 감지

```python
# tuning/guardrail_engine.py
class GuardrailEngine:
    """
    가드레일 엔진
    
    체크 항목:
    1. DD 증가 (max_dd_delta_pct)
    2. 최소 거래수 (min_trades)
    3. 변동성 증가 (max_vol_increase_pct)
    4. 에러율 (max_error_rate)
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.guardrails = config['tuning']['rollout']['canary']['guardrails']
        
        self.max_dd_delta_pct = self.guardrails['max_dd_delta_pct']
        self.min_trades = self.guardrails['min_trades']
        self.max_vol_increase_pct = self.guardrails['max_vol_increase_pct']
    
    def check(self) -> Tuple[bool, str]:
        """
        가드레일 체크
        
        Returns:
            (통과 여부, 사유)
        """
        baseline_metrics = self._fetch_baseline_metrics()
        tuned_metrics = self._fetch_tuned_metrics()
        
        # 1) DD 증가 체크
        dd_delta = tuned_metrics['mdd_pct'] - baseline_metrics['mdd_pct']
        if dd_delta > self.max_dd_delta_pct:
            return False, f"DD increased: {dd_delta:.2f}% > {self.max_dd_delta_pct}%"
        
        # 2) 최소 거래수 체크
        if tuned_metrics['trades'] < self.min_trades:
            return False, f"Insufficient trades: {tuned_metrics['trades']} < {self.min_trades}"
        
        # 3) 변동성 증가 체크
        if baseline_metrics['volatility'] > 0:
            vol_increase = (tuned_metrics['volatility'] / baseline_metrics['volatility'] - 1) * 100
            if vol_increase > self.max_vol_increase_pct:
                return False, f"Volatility increased: {vol_increase:.1f}% > {self.max_vol_increase_pct}%"
        
        # 4) 에러율 체크 (선택)
        if 'error_rate' in tuned_metrics:
            if tuned_metrics['error_rate'] > 0.01:  # 1% 초과
                return False, f"Error rate too high: {tuned_metrics['error_rate']:.2%}"
        
        return True, "OK"
    
    def _fetch_baseline_metrics(self) -> Dict:
        """베이스라인 메트릭 조회 (최근 24시간)"""
        # Postgres에서 조회
        with get_db_connection() as conn:
            query = """
                SELECT 
                    COUNT(*) as trades,
                    AVG(pnl) as avg_pnl,
                    STDDEV(pnl) as volatility
                FROM trading.trades
                WHERE created_at > NOW() - INTERVAL '24 hours'
                  AND status = 'CLOSED'
                  AND config_mode = 'baseline'
            """
            # ... (실제 쿼리 및 MDD 계산)
        
        return metrics
    
    def _fetch_tuned_metrics(self) -> Dict:
        """튜닝 메트릭 조회 (최근 24시간)"""
        # 동일하지만 config_mode = 'tuned'
        return metrics
```

---

### 2.5 ABComparisonReport

**책임**: A/B 비교 리포트 생성

```python
# analytics/ab_comparison.py
class ABComparisonReport:
    """
    A/B 비교 리포트
    
    출력:
    - JSON (메트릭 데이터)
    - HTML (웹 리포트)
    - Markdown (문서)
    - 차트 (PNG)
    """
    
    def __init__(
        self,
        baseline_metrics: Dict,
        tuned_metrics: Dict,
        config_diff: Dict,
    ):
        self.baseline = baseline_metrics
        self.tuned = tuned_metrics
        self.config_diff = config_diff
    
    def generate(
        self,
        formats: List[str] = ['json', 'markdown'],
        output_dir: str = 'logs/ab_comparison/'
    ):
        """리포트 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"ensemble_{timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1) 메트릭 비교 테이블
        comparison = self._build_comparison_table()
        
        # 2) 차트 생성
        if 'charts' in formats:
            self._generate_charts(output_path / 'charts')
        
        # 3) JSON
        if 'json' in formats:
            self._save_json(output_path / 'comparison.json', comparison)
        
        # 4) Markdown
        if 'markdown' in formats:
            self._save_markdown(output_path / 'report.md', comparison)
        
        logger.info(f"📊 A/B 리포트 생성: {output_path}")
    
    def _build_comparison_table(self) -> Dict:
        """비교 테이블 구축"""
        return {
            'baseline': self.baseline,
            'tuned': self.tuned,
            'delta': {
                'score_total': self.tuned['score_total'] - self.baseline['score_total'],
                'sharpe': self.tuned['sharpe'] - self.baseline['sharpe'],
                'mdd_pct': self.tuned['mdd_pct'] - self.baseline['mdd_pct'],
                'trades': self.tuned['trades'] - self.baseline['trades'],
            },
            'config_diff': self.config_diff,
        }
```

---

## 🔄 3. 데이터 플로우

### 3.1 튜닝 실험 플로우

```
1. EnsembleTuner.optimize(n_trials=10)
   ↓
2. For each trial:
   - sample_params() → overlay 생성
   - ConfigOverlay.apply_overlay()
   - run_paper_experiment(24h)
   - calculate_score()
   ↓
3. 최적 파라미터 선택
   ↓
4. configs/overlays/tuning_best_<study>.yml 저장
```

### 3.2 롤아웃 플로우

```
1. tuning.mode = "shadow"
   → 섀도우 모드 (8시간)
   → A/B 메트릭 수집
   ↓
2. 가드레일 체크
   OK → tuning.mode = "canary"
   NG → 중단
   ↓
3. 카나리 단계별:
   - 10% 트래픽 (6시간)
   - 가드레일 체크 → 30%
   - 가드레일 체크 → 50%
   - 가드레일 체크 → 100%
   ↓
4. tuning.mode = "full"
```

### 3.3 의사결정 플로우

```
ensemble.py::generate_decision()
   ↓
RolloutManager.should_use_tuned_config(decision_id)?
   Yes → ConfigOverlay.get_active_config()
   No  → config.yml (baseline)
   ↓
calculate_weights() with config
   ↓
final decision
```

---

## 📝 4. 설정 스키마

```yaml
# config.yml (베이스)
tuning:
  enabled: false
  mode: "none"  # none|shadow|canary|full
  
  experiment:
    study_name: "ensemble_tuning_001"
    storage: "sqlite:///optuna.db"
    window_hours: 24
    n_trials: 10
  
  rollout:
    shadow:
      duration_hours: 8
    
    canary:
      stages: [10, 30, 50, 100]
      stage_duration_hours: 6
      guardrails:
        max_dd_delta_pct: 0.5
        min_trades: 20
        max_vol_increase_pct: 20.0
```

---

## ✅ 다음 단계

1. **상세 구현 설계** 작성
2. **데이터 모델** 정의
3. **API 설계** 명세
4. **테스트 전략** 수립
