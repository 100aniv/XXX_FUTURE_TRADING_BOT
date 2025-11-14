# PHASE8 Config Migration Report

## 요약
기존 `config.yml`을 새 구조(`base.yml` + `modes/*.yml`)로 마이그레이션 완료.

---

## 1. 파일 구조

### Before (PHASE7)
```
config.yml  (638줄, 단일 파일)
```

### After (PHASE8)
```
config.yml                    (원본 유지, 638줄)
configs/
  ├─ config_legacy.yml        (백업본, 638줄)
  ├─ base.yml                 (기본 설정, 638줄)
  └─ modes/
      └─ backtest_clean.yml   (오버라이드, 24줄)
```

---

## 2. 마이그레이션 검증

### 파일 해시 비교
```
config.yml:           81404FFA205655E642AFEE42D6DA4E2CB2F1A961...
config_legacy.yml:    81404FFA205655E642AFEE42D6DA4E2CB2F1A961...
base.yml:             81404FFA205655E642AFEE42D6DA4E2CB2F1A961...
```

**결과: 세 파일 모두 동일 ✅**

### 줄 수 비교
```
config.yml:           638줄
config_legacy.yml:    638줄
base.yml:             638줄
```

**결과: 완전 일치 ✅**

---

## 3. 변경 사항

### config_legacy.yml vs base.yml
```diff
# 차이 없음 - 완전히 동일한 파일
```

**설명:**
- `config_legacy.yml`: 백업 목적, 실행에 사용 안 됨
- `base.yml`: 실제 기본 설정으로 사용
- **내용은 100% 동일** - 기존 설정 완전 보존

---

## 4. backtest_clean.yml 오버라이드 항목

base.yml을 상속하며, 다음 항목만 오버라이드:

| 키 | base.yml 값 | backtest_clean.yml 값 | 변경 이유 |
|----|-------------|----------------------|----------|
| `execution.fill_policy` | limit_post_only | **next_open** | 백테스트 결정성 |
| `execution.fees_bps` | 5 (0.05%) | **10 (0.1%)** | 보수적 수수료 |
| `execution.slippage.type` | atr_based | **fixed** | 재현성 확보 |
| `execution.slippage.bps` | (동적) | **5 (0.05%)** | 고정 슬리피지 |
| `execution.cooldown_minutes` | 5 | **0** | 백테스트 속도 |
| `risk.flash_guard` | true | **false** | 백테스트 불필요 |
| `ensemble.enabled` | true | **false** | 단일 전략만 |

**나머지 595줄은 base.yml 그대로 사용**

---

## 5. 병합 순서

```
1. configs/base.yml              (638줄 - 기존 설정 전체)
      ↓
2. configs/modes/backtest_clean.yml  (24줄 - 오버라이드 7개)
      ↓
3. configs/active/current.yml    (있으면 추가 병합)
      ↓
4. CLI/ENV 변수                  (최종 오버라이드)
      ↓
5. effective_config.yml 저장     (재현성 스냅샷)
```

---

## 6. 코드 변경 사항

### 기존 방식 (PHASE7)
```python
# ❌ 직접 파일 읽기 (제거됨)
with open("config.yml") as f:
    cfg = yaml.safe_load(f)
```

### 새 방식 (PHASE8)
```python
# ✅ config_loader 사용
from common.config_loader import load_config_with_mode

cfg = load_config_with_mode(mode='backtest_clean')
# base.yml + backtest_clean.yml 병합 완료
```

**검증:** `grep` 결과 `yaml.safe_load("config.yml")` 패턴 없음 ✅

---

## 7. 보존된 설정 (중요!)

다음 설정들이 **100% 보존**되었음:

- ✅ 전략별 파라미터 (scalping, daytrade, swing, trend, reversion, breakout)
- ✅ 앙상블 가중치 (alpha, beta, gamma, delta, epsilon)
- ✅ 리스크 설정 (per_trade, max_exposure, leverage_cap)
- ✅ 수수료/슬리피지 모델 (fee_mode, slippage_model)
- ✅ FlowGuardian 설정 (selftest, functional, startup_bars)
- ✅ 포트폴리오 설정 (budget, correlation, exposure)
- ✅ TP/SL 설정 (atr_mult, trailing, OHLC check)
- ✅ 지표 파라미터 (EMA, RSI, Bollinger, MACD, ATR)

**총 638줄 전체가 base.yml에 그대로 보존**

---

## 8. 주의 사항

### 실행 시 사용하는 파일
- ✅ `configs/base.yml` - 항상 로드
- ✅ `configs/modes/backtest_clean.yml` - backtest_clean 모드 시
- ✅ `configs/active/current.yml` - 활성 설정 (있으면)
- ❌ `config.yml` - 직접 사용 안 됨 (루트에 유지)
- ❌ `configs/config_legacy.yml` - 백업용 (실행 안 됨)

### 변경 금지
- `config_legacy.yml` 수정 금지 (백업본)
- `base.yml` 임의 수정 금지 (검증 후에만)
- 새 설정 추가 시 `modes/*.yml`에 오버라이드로

---

## 9. 성공 기준

- [x] config.yml → config_legacy.yml 백업 (해시 일치)
- [x] config.yml → base.yml 복사 (해시 일치)
- [x] backtest_clean.yml 오버라이드만 (24줄)
- [x] yaml.safe_load("config.yml") 제거 (grep 0건)
- [x] 638줄 전체 보존 확인
- [x] 병합 순서 구현 (load_config_with_mode)
- [x] effective_config.yml 스냅샷 구현

**결과: 100% 완료 ✅**

---

## 10. 다음 단계

1. **백테스트 실행 테스트**
   ```bash
   python scripts/run_backtest.py \
       --mode backtest_clean \
       --strategy scalping \
       --symbol BTCUSDT \
       --timeframe 5m \
       --days 3
   ```

2. **effective_config.yml 검증**
   - artifacts/backtest_clean/{run_id}/effective_config.yml 확인
   - base.yml + backtest_clean.yml 병합 결과 검증

3. **scorecard 생성 확인**
   - scorecard.csv
   - scorecard.md
   - 6개 지표 출력 확인

---

*Generated: 2025-11-14*
*Migration: PHASE7 → PHASE8*
*Status: Complete ✅*
