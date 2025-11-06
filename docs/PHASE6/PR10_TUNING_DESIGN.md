# PR10 — 튜닝 파라미터 및 오버레이 구조 설계

## 개요
PR13에서 베이시안 운영 튜닝을 안전하게 적용하기 위한 파라미터 구조와 오버레이 시스템 설계 문서

## 1. 튜닝 대상 파라미터

### 1.1 앙상블 가중치 계산 파라미터
```yaml
ensemble:
  # 가중치 계산 계수
  alpha_winrate: 0.4      # 승률 가중치 (범위: 0.2~0.6)
  beta_rr: 0.2            # RR 가중치 (범위: 0.1~0.4)
  gamma_sharpe: 0.2       # Sharpe 가중치 (범위: 0.1~0.4)
  delta_confidence: 0.15  # 신뢰도 가중치 (범위: 0.05~0.25)
  epsilon_regime: 0.05    # 레짐 가중치 (범위: 0.0~0.15)
```

**튜닝 전략**:
- Optuna TPE Sampler 사용
- 제약 조건: alpha + beta + gamma + delta + epsilon ≈ 1.0 (±0.1)
- 목표: score_total 최대화

### 1.2 Experience Score 파라미터
```yaml
ensemble:
  experience:
    min_trades: 20        # 최소 거래 수 (범위: 10~50)
    data_weight: 0.4      # 데이터 충분성 가중치 (범위: 0.3~0.5)
    perf_weight: 0.4      # 최근 성과 가중치 (범위: 0.3~0.5)
    stability_weight: 0.2 # 안정성 가중치 (범위: 0.1~0.3)
```

**튜닝 전략**:
- min_trades: 정수형 파라미터
- 가중치 합: data_weight + perf_weight + stability_weight = 1.0

### 1.3 클램핑 및 임계값
```yaml
ensemble:
  max_weight_per_strategy: 0.4  # 단일 전략 최대 가중치 (범위: 0.3~0.5)
  min_confidence: 0.6           # 최소 신뢰도 (범위: 0.5~0.7)
  theta_long: 0.15              # LONG 진입 임계값 (범위: 0.1~0.25)
  theta_short: 0.15             # SHORT 진입 임계값 (범위: 0.1~0.25)
```

### 1.4 보너스 로직
```yaml
ensemble:
  consensus_bonus: 0.2          # 합의 보너스 (범위: 0.1~0.3)
  rr_bonus: 0.2                 # RR 보너스 (범위: 0.1~0.3)
  rr_bonus_threshold: 1.6       # RR 보너스 임계값 (범위: 1.4~2.0)
```

---

## 2. 오버레이 구조 설계

### 2.1 설정 계층 구조
```
config.yml (기본값)
  ↓
tuning_overlay.yml (튜닝된 값)
  ↓
runtime_config (최종 적용값)
```

### 2.2 오버레이 파일 구조
```yaml
# tuning_overlay.yml
version: "1.0"
study_id: "ensemble_optimization_001"
trial_id: "trial_0042"
timestamp: "2025-11-06T13:00:00"
mode: "shadow"  # shadow | canary | full

# 튜닝된 파라미터 (config.yml 덮어쓰기)
ensemble:
  alpha_winrate: 0.45
  beta_rr: 0.18
  gamma_sharpe: 0.22
  delta_confidence: 0.12
  epsilon_regime: 0.03
  
  experience:
    min_trades: 25
  
  max_weight_per_strategy: 0.38
  theta_long: 0.18
  theta_short: 0.16

# 성과 메트릭 (참고용)
metrics:
  score_total: 78.5
  sharpe: 1.25
  mdd: -0.08
  winrate: 0.58
  total_trades: 120
```

### 2.3 오버레이 로드 로직
```python
def load_config_with_overlay(base_config_path, overlay_path=None):
    """
    기본 설정 + 오버레이 병합
    
    Args:
        base_config_path: config.yml 경로
        overlay_path: tuning_overlay.yml 경로 (선택)
    
    Returns:
        병합된 설정 dict
    """
    # 1. 기본 설정 로드
    config = load_yaml(base_config_path)
    
    # 2. 오버레이 존재 시 병합
    if overlay_path and os.path.exists(overlay_path):
        overlay = load_yaml(overlay_path)
        
        # 모드 확인
        mode = overlay.get('mode', 'shadow')
        
        if mode in ['shadow', 'canary', 'full']:
            # 앙상블 파라미터만 덮어쓰기
            if 'ensemble' in overlay:
                config['ensemble'].update(overlay['ensemble'])
            
            logger.info(f"✅ 튜닝 오버레이 적용: {overlay_path} (모드: {mode})")
        else:
            logger.warning(f"⚠️ 알 수 없는 오버레이 모드: {mode}")
    
    return config
```

---

## 3. 튜닝 실험 구조

### 3.1 Study 디렉토리 구조
```
logs/tuning/
├── ensemble_optimization_001/
│   ├── study.db                    # Optuna study DB
│   ├── config/
│   │   ├── trial_0001.yml          # Trial 설정
│   │   ├── trial_0002.yml
│   │   └── ...
│   ├── results/
│   │   ├── trial_0001_result.json  # Trial 결과
│   │   ├── trial_0002_result.json
│   │   └── ...
│   └── best_params.yml             # 최적 파라미터
```

### 3.2 Trial 결과 JSON 구조
```json
{
  "trial_id": "trial_0042",
  "study_id": "ensemble_optimization_001",
  "timestamp": "2025-11-06T13:00:00",
  "params": {
    "alpha_winrate": 0.45,
    "beta_rr": 0.18,
    "gamma_sharpe": 0.22,
    "delta_confidence": 0.12,
    "epsilon_regime": 0.03,
    "min_trades": 25,
    "max_weight_per_strategy": 0.38,
    "theta_long": 0.18,
    "theta_short": 0.16
  },
  "metrics": {
    "score_total": 78.5,
    "sharpe": 1.25,
    "mdd": -0.08,
    "winrate": 0.58,
    "profit_factor": 1.85,
    "total_trades": 120,
    "wins": 70,
    "losses": 50
  },
  "constraints": {
    "min_trades_met": true,
    "mdd_within_limit": true,
    "winrate_acceptable": true
  },
  "status": "completed"
}
```

---

## 4. 가드레일 (Guardrails)

### 4.1 실험 중단 조건
```yaml
guardrails:
  max_dd_delta_pct: 2.0       # MDD 증가 한계 (2%p)
  min_trades: 80              # 최소 거래 수
  max_vol_increase_pct: 30.0  # 변동성 증가 한계 (30%)
  min_winrate: 0.45           # 최소 승률 (45%)
  max_error_rate_pct: 5.0     # 최대 에러율 (5%)
```

### 4.2 가드레일 체크 로직
```python
def check_guardrails(metrics, baseline_metrics, guardrails):
    """
    가드레일 위반 여부 체크
    
    Returns:
        (passed: bool, violations: List[str])
    """
    violations = []
    
    # 1. MDD 증가 체크
    mdd_delta = metrics['mdd'] - baseline_metrics['mdd']
    if mdd_delta > guardrails['max_dd_delta_pct'] / 100:
        violations.append(f"MDD 증가 한계 초과: {mdd_delta:.2%}")
    
    # 2. 최소 거래 수 체크
    if metrics['total_trades'] < guardrails['min_trades']:
        violations.append(f"거래 수 부족: {metrics['total_trades']}")
    
    # 3. 변동성 증가 체크
    vol_increase = (metrics['volatility'] - baseline_metrics['volatility']) / baseline_metrics['volatility']
    if vol_increase > guardrails['max_vol_increase_pct'] / 100:
        violations.append(f"변동성 증가 한계 초과: {vol_increase:.2%}")
    
    # 4. 최소 승률 체크
    if metrics['winrate'] < guardrails['min_winrate']:
        violations.append(f"승률 미달: {metrics['winrate']:.2%}")
    
    return len(violations) == 0, violations
```

---

## 5. 롤아웃 전략 (PR13)

### 5.1 단계별 롤아웃
```
Phase 1: Shadow Mode (8시간)
  - 실제 거래 미반영
  - 로그/메트릭만 수집
  - 가드레일 위반 시 중단

Phase 2: Canary 10% (6시간)
  - 10% 심볼에만 적용
  - 가드레일 모니터링
  - 통과 시 30%로 승격

Phase 3: Canary 30% (6시간)
  - 30% 심볼에 적용
  - 통과 시 50%로 승격

Phase 4: Canary 50% (6시간)
  - 50% 심볼에 적용
  - 통과 시 100%로 승격

Phase 5: Full Rollout
  - 전체 심볼에 적용
  - 지속적 모니터링
```

### 5.2 롤백 조건
- 가드레일 위반 발생 시 즉시 이전 단계로 롤백
- 3회 연속 실패 시 baseline으로 완전 롤백
- 롤백 시 `tuning_overlay.yml` 비활성화

---

## 6. A/B 비교 구조

### 6.1 비교 대상
- **Baseline**: 현재 config.yml 기본값
- **Tuned**: 튜닝된 오버레이 적용값

### 6.2 비교 메트릭
```yaml
comparison_metrics:
  primary:
    - score_total      # 주 목표
    - sharpe           # 샤프 비율
    - mdd              # 최대낙폭
  
  secondary:
    - winrate          # 승률
    - profit_factor    # Profit Factor
    - total_trades     # 거래 수
    - avg_win          # 평균 수익
    - avg_loss         # 평균 손실
  
  constraints:
    - mdd_delta        # MDD 증가폭
    - trade_count_delta # 거래 수 변화
    - volatility_delta  # 변동성 변화
```

### 6.3 리포트 구조
```json
{
  "comparison_id": "baseline_vs_tuned_001",
  "timestamp": "2025-11-06T13:00:00",
  "period": {
    "start": "2025-11-05T13:00:00",
    "end": "2025-11-06T13:00:00",
    "duration_hours": 24
  },
  "baseline": {
    "score_total": 65.2,
    "sharpe": 1.05,
    "mdd": -0.12,
    "winrate": 0.52,
    "total_trades": 95
  },
  "tuned": {
    "score_total": 78.5,
    "sharpe": 1.25,
    "mdd": -0.08,
    "winrate": 0.58,
    "total_trades": 120
  },
  "delta": {
    "score_total": "+20.4%",
    "sharpe": "+19.0%",
    "mdd": "+4.0%p (개선)",
    "winrate": "+6.0%p",
    "total_trades": "+26.3%"
  },
  "verdict": "PASS",
  "guardrails_passed": true
}
```

---

## 7. 구현 우선순위 (PR13)

### Phase 1: 오버레이 시스템
1. `load_config_with_overlay()` 함수 구현
2. `tuning_overlay.yml` 로드 로직 추가
3. 오버레이 적용 로깅

### Phase 2: 튜닝 스크립트
1. Optuna study 생성
2. 파라미터 탐색 공간 정의
3. Objective 함수 구현 (score_total 최대화)

### Phase 3: 가드레일
1. `check_guardrails()` 함수 구현
2. 실시간 모니터링 추가
3. 자동 중단/롤백 로직

### Phase 4: 롤아웃
1. Shadow 모드 구현
2. Canary 단계별 적용
3. A/B 비교 리포트 생성

---

## 8. 테스트 계획

### 8.1 유닛 테스트
- `load_config_with_overlay()` 테스트
- `check_guardrails()` 테스트
- 오버레이 병합 로직 테스트

### 8.2 통합 테스트
- Shadow 모드 24시간 실행
- 가드레일 위반 시나리오 테스트
- 롤백 시나리오 테스트

### 8.3 수용 테스트
- Baseline 대비 score_total ≥12% 향상
- Sharpe ≥10% 향상
- MDD 증가 ≤1%p
- 최소 거래수 ≥60

---

## 9. 리스크 및 완화

### 9.1 과적합 리스크
**리스크**: 백테스트에서는 좋지만 실제는 나쁨
**완화**: 
- OOS 윈도 사용 (최근 30일)
- 최소 거래수 제약 (min_trades ≥80)
- 변동성 증가 한계 (≤30%)

### 9.2 가드레일 오작동
**리스크**: 정상 상황에서 중단
**완화**:
- 가드레일 임계값 보수적 설정
- 3회 연속 위반 시에만 롤백
- 수동 오버라이드 옵션

### 9.3 롤아웃 실패
**리스크**: Canary 단계에서 문제 발생
**완화**:
- 각 단계 최소 6시간 모니터링
- 자동 롤백 메커니즘
- 텔레그램 알림

---

## 10. 다음 단계

### PR10 (현재)
- [x] Experience Score 구현
- [x] 가중치 클램핑 구현
- [x] 튜닝 파라미터 설계 완료
- [ ] A/B 비교 리포트 경로 정의
- [ ] 24시간 페이퍼 평가

### PR13 (향후)
- [ ] 오버레이 시스템 구현
- [ ] Optuna 튜닝 스크립트
- [ ] 가드레일 구현
- [ ] Shadow/Canary 롤아웃
- [ ] A/B 비교 리포트 생성

---

## 참고 문서
- `docs/PHASE6/PR10_MASTER_PLAN.md`: PR10 마스터 플랜
- `docs/PHASE6/PR13_MASTER_PLAN.md`: PR13 마스터 플랜
- `config.yml`: 기본 설정 파일
- `strategies/ensemble.py`: 앙상블 로직
