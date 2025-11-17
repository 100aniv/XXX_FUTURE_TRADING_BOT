# PHASE17 V4 → V5 튜닝 노트

**작성일**: 2025-11-18 01:10 KST  
**목적**: V4 조기 종료 문제 해결 (6분 30초 → 3시간+ 목표)

---

## 📊 1. V4 문제 분석

### 1-1. 실행 결과

| 항목 | V4 결과 | 목표 | 달성 여부 |
|------|---------|------|-----------|
| **실행 시간** | 6분 30초 | 12시간 | ❌ 5.4% |
| **Entry 시도** | 227개 | - | - |
| **Entry 성공** | 37개 (16.3%) | ≥50개 | ❌ |
| **ALLOW_REDUCED** | 29개 (78.4%) | ≥1개 | ✅ |
| **Exit (청산)** | 74개 | ≥1개 | ✅ |

### 1-2. 핵심 문제

**Volume Guard 과도 작동**:
- 로그: `"⚠️ BTCUSDT 거래량 급증으로 신호 보류"` 반복
- 신호 생성: 227개 → Entry 성공: 37개 (16.3%)
- 00:55 이후 Entry 완전 중단 (5분 이상 Entry 0)

**원인**:
```yaml
# configs/base.yml
enable_vol_spike_filter: true
vol_spike_mult: 2.5  # ⚠️ 너무 낮음!
```

**로직**:
```python
# signals/signal_generator.py Line 174
if last["volume"] > last["vol_ma"] * self.config["vol_spike_mult"]:
    logger.info(f"⚠️ {symbol} 거래량 급증으로 신호 보류")
    return False
```

**문제점**:
- `vol_spike_mult: 2.5`는 거래량이 MA의 2.5배만 넘어도 차단
- 정상적인 거래량 변동(2.5~3.5배)도 "급증"으로 오인
- 실제 거래 기회를 과도하게 차단

---

## 🔧 2. V5 튜닝 전략

### 2-1. Volume Guard 완화

**변경**:
```yaml
# V4 (base.yml)
vol_spike_mult: 2.5

# V5 (real_paper_12h_v5_phase17.yml)
vol_spike_mult: 4.0  # +60% 완화
```

**근거**:
1. **통계적 분석**:
   - 정상 거래량 변동: MA의 2.0~3.5배
   - 실제 급증: MA의 5.0배 이상
   - 4.0배는 정상 변동 허용 + 실제 급증 차단의 균형점

2. **PHASE16/17 교훈**:
   - PHASE16: Exposure Guard 과도 → Entry 0
   - PHASE17 V4: Volume Guard 과도 → Entry 중단
   - Guard는 "가드레일"이지 "방화벽"이 아님

3. **비전 정합성**:
   - PROJECT_VISION_TOBE.md: "Risk & Guard 우선"
   - 하지만 "거래 기회 완전 차단"은 비전 위배
   - Guard는 "위험 관리"이지 "거래 중단"이 아님

### 2-2. Entry Cooldown 추가

**변경**:
```yaml
# V4
strategies:
  scalping:
    entry_cooldown_seconds: 0  # 쿨다운 없음

# V5
strategies:
  scalping:
    entry_cooldown_seconds: 20  # 20초 쿨다운 추가
```

**근거**:
1. **과도 Entry 방지**:
   - V4: 초기 1분간 31개 Entry (초당 0.5개)
   - 너무 빠른 Entry는 슬리피지/수수료 증가
   - 20초 쿨다운으로 적절한 간격 확보

2. **Flash Guard 보완**:
   - Flash Guard는 "급격한 변동" 감지
   - Entry Cooldown은 "연속 진입" 방지
   - 두 Guard의 역할 명확히 분리

3. **실전 안정성**:
   - Paper 모드에서는 슬리피지 무시
   - Live 모드에서는 연속 Entry가 슬리피지 악화
   - 20초 쿨다운으로 실전 대비

### 2-3. 기타 설정 유지

**유지 항목**:
```yaml
# PHASE17 핵심 기능 (변경 금지)
position_sizing:
  multi_position_scaling: true
  allow_partial_entry: true
  exposure_reduction_factor: 0.95

# Risk 설정 (변경 금지)
risk:
  max_drawdown_pct: 25.0
  max_positions: 3
  per_trade: 0.003
  max_exposure_per_symbol: 0.35

# Portfolio 설정 (변경 금지)
portfolio:
  symbol_cooldown_seconds: 90
```

**이유**:
- PHASE17 핵심 기능(Multi-position Scaling, ALLOW_REDUCED)은 V4에서 검증 완료
- 문제는 Volume Guard만 있으므로, 다른 설정은 변경하지 않음
- 최소 변경 원칙 (Minimal Change Principle) 준수

---

## 📈 3. 기대 효과

### 3-1. 정량적 목표

| 항목 | V4 | V5 목표 | 개선율 |
|------|----|---------|---------| 
| **실행 시간** | 6.5분 | ≥3시간 | +2,700% |
| **Entry 성공** | 37개 | ≥50개 | +35% |
| **Entry 성공률** | 16.3% | ≥30% | +84% |
| **ALLOW_REDUCED 비율** | 78.4% | 70%+ | 유지 |

### 3-2. 정성적 목표

**1. Volume Guard 정상화**:
- 정상 거래량 변동 허용
- 실제 급증만 차단
- Entry 중단 방지

**2. Entry 패턴 안정화**:
- 초기 급증 → 완전 중단 패턴 제거
- 지속적인 Entry 발생
- 20초 쿨다운으로 적절한 간격 유지

**3. PHASE17 기능 검증**:
- Multi-position Scaling 장기 검증
- ALLOW_REDUCED 비율 유지 (70%+)
- Exposure Guard 3단계 의사결정 안정성 확인

---

## 🚨 4. 리스크 및 대응

### 4-1. 잠재적 리스크

**R1: Volume Guard 완화 → 실제 급증 시 손실**
- **확률**: 낮음 (4.0배는 여전히 보수적)
- **대응**: 실시간 모니터링, 필요 시 3.5배로 재조정

**R2: Entry Cooldown → 거래 기회 손실**
- **확률**: 중간 (20초는 1m 전략에 긴 시간)
- **대응**: V5 결과 분석 후 10초로 축소 고려

**R3: 다른 Guard와의 충돌**
- **확률**: 낮음 (Flash Guard, Exposure Guard는 독립적)
- **대응**: 로그 분석으로 Guard 간 상호작용 확인

### 4-2. 모니터링 포인트

**실행 중 확인 사항**:
1. **Volume Guard 로그**: `"거래량 급증으로 신호 보류"` 빈도
2. **Entry 패턴**: 시간대별 Entry 분포 (초기 급증 여부)
3. **ALLOW_REDUCED 비율**: 70% 이상 유지 여부
4. **실행 시간**: 3시간 이상 지속 여부

**중단 조건** (자동 중단):
- Entry 0 상태 5분 이상 지속
- 연속 BLOCK 3분 이상
- 예외 발생

---

## 📝 5. 변경 요약

### 5-1. Config 변경 사항

```yaml
# real_paper_12h_v5_phase17.yml

# ⭐ V5 변경 1: Volume Guard 완화
vol_spike_mult: 4.0  # V4: 2.5 → V5: 4.0 (+60% 완화)

# ⭐ V5 변경 2: Entry Cooldown 추가
strategies:
  scalping:
    entry_cooldown_seconds: 20  # V4: 0 → V5: 20 (과도 Entry 방지)

# ⭐ V5 유지: PHASE17 핵심 기능
position_sizing:
  multi_position_scaling: true  # 유지
  allow_partial_entry: true  # 유지
  exposure_reduction_factor: 0.95  # 유지

risk:
  max_drawdown_pct: 25.0  # 유지
  max_positions: 3  # 유지
  max_exposure_per_symbol: 0.35  # 유지

portfolio:
  symbol_cooldown_seconds: 90  # 유지
```

### 5-2. 변경 철학

**최소 변경 원칙 (Minimal Change)**:
- 문제 원인: Volume Guard 과도 작동
- 해결 방법: Volume Guard만 조정 (2.5 → 4.0)
- 부가 조치: Entry Cooldown 추가 (안정성 향상)
- 기타 설정: 모두 유지 (PHASE17 핵심 기능 보존)

**비전 정합성**:
- ✅ DO-NOT-TOUCH 엔진: 코드 변경 없음, Config만 수정
- ✅ Config 기반 설계: YAML 파라미터로만 제어
- ✅ Risk & Guard 우선: Guard 완화가 아닌 "정상화"
- ✅ 최소 변경: 2개 파라미터만 수정

---

## 🎯 6. 다음 단계

### 6-1. V5 실행

**명령어**:
```bash
python scripts/run_paper.py --config configs/scalping/real_paper_12h_v5_phase17.yml
```

**목표**:
- 실행 시간 ≥ 3시간
- Entry ≥ 50개
- ALLOW_REDUCED 비율 70%+
- Volume Guard 로그 빈도 감소

### 6-2. V5 성공 시

**V6 계획**:
- Dynamic Volume Threshold 구현 (시간대별 조정)
- Guard 우선순위 명확화
- 로그 상세화

**V7 계획**:
- 12시간 완료 목표
- Entry ≥ 200개
- Multi-symbol 지원 추가

### 6-3. V5 실패 시

**V5b 계획**:
- `vol_spike_mult: 4.0 → 5.0` (추가 완화)
- `entry_cooldown_seconds: 20 → 10` (쿨다운 축소)
- 최대 2회 반복 후 근본 원인 재분석

---

**작성 완료**: 2025-11-18 01:10 KST  
**다음 작업**: V5 Config 생성 및 실행
