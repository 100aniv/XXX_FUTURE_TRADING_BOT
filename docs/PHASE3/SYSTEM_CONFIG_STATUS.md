# 시스템 설정 현황 및 개선 방향

> **작성일**: 2025-10-23  
> **목적**: 현재 설정 상태 분석 및 멀티 심볼/전략 활용 방안 정리

---

## 📊 **1. 현재 설정 상태**

### **1.1 심볼 설정**

| 항목 | 현재 설정 | 가능한 옵션 | 상태 |
|------|-----------|------------|------|
| **모드** | `manual` | `manual` / `top50` / `top100` / `all` | ⚠️ 제한적 |
| **심볼 수** | 5개 | 최대 120개 (max_streams) | ⚠️ 미활용 |
| **설정 위치** | config.yml line 18-37 | - | - |

**현재 수동 심볼 (5개)**
- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- XRPUSDT

**활용 가능한 모드**
```yaml
symbols:
  mode: manual      # 수동 선택 (5개)
  # mode: top50    # 거래량 상위 50개
  # mode: top100   # 거래량 상위 100개
  # mode: all      # 모든 USDT 선물
```

---

### **1.2 전략 설정**

| 전략 | enabled | timeframe | RR | filters | 현재 사용 |
|------|---------|-----------|----|---------|-----------| 
| **scalping** | ✅ true | 5m | 2.5 | regime ✅, volume ❌, mtf ❌ | ❌ |
| **daytrade** | ✅ true | 15m | 3.0 | regime ✅, volume ✅, mtf ✅ | ✅ **사용 중** |
| **swing** | ✅ true | 1h | 2.2 | regime ✅, volume ✅, mtf ✅ | ❌ |
| **trend** | ✅ true | 4h | 2.5 | regime ❌, volume ❌, mtf ❌ | ❌ |
| **reversion** | ✅ true | 15m | 1.5 | regime ✅, volume ✅, mtf ❌ | ❌ |
| **breakout** | ✅ true | 1h | 2.0 | regime ❌, volume ❌, mtf ❌ | ❌ |

**앙상블 설정**
```yaml
strategy:
  use_ensemble: false  # ⚠️ 비활성화
  selector: daytrade   # ⚠️ 1개만 선택
```

---

### **1.3 실제 동작 방식**

#### **문제: 타임프레임별 단일 전략 선택**

**코드 분석** (`signals/signal_generator.py` line 137-142)
```python
def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    # 타임프레임에 따라 전략 선택
    tf = self.config["timeframe"]  # "5m"
    strategy = self.strategy_modules.get(tf, ...)  # daytrade만 선택
    
    # 전략 실행
    return strategy.signal_logic(df, self.config)
```

**현재 동작**
1. `config.yml`에서 `timeframe: 5m` 설정
2. `SignalGenerator`가 5m → daytrade 매핑
3. **daytrade 전략만 실행**
4. 나머지 5개 전략은 **enabled: true여도 사용 안됨**

---

## ❌ **2. 주요 문제점**

### **2.1 심볼 제한**
- ✅ **기능 존재**: top50/top100/all 모드
- ❌ **현재**: manual 5개만 사용
- 📉 **영향**: 
  - 거래 기회 제한
  - 다양성 부족
  - 시장 전체 커버리지 낮음

### **2.2 전략 제한**
- ✅ **기능 존재**: 6개 전략 + 앙상블
- ❌ **현재**: daytrade 1개만 사용
- 📉 **영향**:
  - 시장 상황별 대응 불가
  - 다양한 스타일 미활용
  - 거래 빈도 매우 낮음 (1건/일)

### **2.3 앙상블 비활성화**
- ✅ **기능 존재**: 가중치 기반 앙상블
- ❌ **현재**: use_ensemble: false
- 📉 **영향**:
  - 전략 간 시너지 없음
  - 신호 품질 검증 부족
  - 승률 향상 기회 상실

---

## ✅ **3. 개선 방향**

### **3.1 멀티 심볼 활성화**

#### **옵션 A: Top50 (권장)**
```yaml
symbols:
  mode: top50  # 거래량 상위 50개
```

**장점**
- 🎯 유동성 높은 심볼
- 📊 다양한 거래 기회
- ⚡ 적정 수량 (50개)

**예상 효과**
- 거래 빈도: 1건/일 → **30-50건/일**
- 심볼 다양성: 5개 → 50개

#### **옵션 B: Top100**
```yaml
symbols:
  mode: top100  # 거래량 상위 100개
```

**주의사항**
- ⚠️ 데이터 부하 증가
- ⚠️ max_streams: 120 제한

#### **옵션 C: Manual 확장**
```yaml
symbols:
  mode: manual
  manual:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    - SOLUSDT
    - XRPUSDT
    - ADAUSDT
    - DOGEUSDT
    - DOTUSDT
    - MATICUSDT
    - AVAXUSDT
    # ... 최대 20개 정도
```

---

### **3.2 멀티 전략 활성화**

#### **방법 1: 앙상블 활성화 (권장)**
```yaml
strategy:
  use_ensemble: true  # ✅ 활성화
  # selector: daytrade  # 제거
```

**장점**
- ✅ 6개 전략 동시 실행
- ✅ 가중치 기반 신호 통합
- ✅ 품질 높은 신호만 선택

**앙상블 가중치** (config.yml line 349-355)
```yaml
weights:
  reversion: 3.0   # 승률 47.2% (최고)
  daytrade: 2.5    # 승률 27.8%
  scalping: 2.0    # 승률 31.7%
  swing: 2.2
  trend: 1.5       # 거래 6건만
  breakout: 2.0
```

#### **방법 2: 타임프레임별 전략 매핑 개선**

**현재 방식** (signal_generator.py)
```python
# ❌ 하드코딩된 매핑
self.strategy_modules = {
    "1m": scalping,
    "5m": daytrade,  # ⚠️ 5m = daytrade만
    "15m": swing
}
```

**개선 방안**
```python
# ✅ config.yml에서 매핑 정의
strategy_mapping:
  5m:
    - scalping     # 5m에서 scalping도 실행
    - daytrade     # 5m에서 daytrade도 실행
  15m:
    - daytrade
    - swing
    - reversion
```

---

### **3.3 권장 설정 조합**

#### **조합 1: 보수적 (테스트용)**
```yaml
symbols:
  mode: manual  # 5개 유지
  
strategy:
  use_ensemble: true  # 앙상블 활성화
```

**예상 효과**
- 거래 빈도: 1건/일 → **5-10건/일**
- 승률: 26% → **30-35%** (앙상블 효과)

#### **조합 2: 공격적 (목표 달성용)**
```yaml
symbols:
  mode: top50  # 50개 심볼
  
strategy:
  use_ensemble: true  # 앙상블 활성화
```

**예상 효과**
- 거래 빈도: 1건/일 → **50-100건/일**
- 승률: 26% → **35-40%** (앙상블 + 다양성)
- **목표 10%/일 달성 가능성 높음**

#### **조합 3: 균형 (권장)**
```yaml
symbols:
  mode: manual  # 시작은 5개
  manual:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    - SOLUSDT
    - XRPUSDT
    - ADAUSDT   # +6개 추가
    - DOGEUSDT
    - DOTUSDT
    - MATICUSDT
    - AVAXUSDT
    - LINKUSDT
  
strategy:
  use_ensemble: true  # 앙상블 활성화
```

**예상 효과**
- 거래 빈도: 1건/일 → **20-30건/일**
- 승률: 26% → **30-35%**
- MDD: -771% → **-20% 이내** (필터 강화 필요)

---

## 📋 **4. 실행 계획**

### **Phase 1: 앙상블 활성화 (즉시 가능)**

**변경사항**
```yaml
# config.yml line 237-238
strategy:
  use_ensemble: true   # false → true
  # selector: daytrade  # 주석 처리
```

**검증 방법**
```bash
docker-compose run --rm backtester python main.py
```

**예상 로그**
```
✅ 전략 활성화: scalping
✅ 전략 활성화: daytrade
✅ 전략 활성화: swing
✅ 전략 활성화: trend
✅ 전략 활성화: reversion
✅ 전략 활성화: breakout
✅ 앙상블 모드 활성화
```

---

### **Phase 2: 심볼 확장 (단계적)**

#### **Step 1: Manual 확장 (안전)**
```yaml
symbols:
  mode: manual
  manual:
    # 기존 5개
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    - SOLUSDT
    - XRPUSDT
    # 추가 5개 (높은 유동성)
    - ADAUSDT
    - DOGEUSDT
    - DOTUSDT
    - MATICUSDT
    - AVAXUSDT
```

#### **Step 2: Top50 (공격적)**
```yaml
symbols:
  mode: top50  # 50개로 확장
```

---

### **Phase 3: 엔트리 필터 강화 (필수)**

현재 MDD -771%의 주요 원인: **엔트리 타이밍**

**추가 필터 적용**
```yaml
filters:
  htf: "4h"                    # 1h → 4h (더 강한 추세)
  require_trend_align: true    # HTF 정렬 필수
  
  # ⭐ 추가 필터
  min_atr_multiplier: 1.5      # ATR 최소 배수
  volume_confirmation: true     # 거래량 확인
  session_filter: true          # 세션 필터
  
  session_whitelist:
    - "London"                  # 런던 (08:00-16:00 GMT)
    - "NY-open"                 # 뉴욕 오픈 (13:00-17:00 GMT)
```

---

## 📊 **5. 기대 효과 (Before/After)**

### **Before (현재)**
| 지표 | 현재 값 | 상태 |
|------|---------|------|
| 심볼 수 | 5개 | ⚠️ 제한적 |
| 활성 전략 | 1개 (daytrade) | ⚠️ 단일 |
| 거래 빈도 | 1건/일 | ❌ 매우 낮음 |
| 승률 | 26.0% | ❌ 낮음 |
| MDD | -771% | ❌ 위험 |
| 총점 | 29.9/100 | ❌ D등급 |

### **After (Phase 1: 앙상블만)**
| 지표 | 예상 값 | 개선 |
|------|---------|------|
| 심볼 수 | 5개 | - |
| 활성 전략 | 6개 (앙상블) | ✅ +500% |
| 거래 빈도 | 5-10건/일 | ✅ +500% |
| 승률 | 30-35% | ✅ +15% |
| MDD | -400% | ⚠️ 개선 필요 |
| 총점 | 40-50/100 | ⚠️ C등급 |

### **After (Phase 2: 앙상블 + Top50)**
| 지표 | 예상 값 | 개선 |
|------|---------|------|
| 심볼 수 | 50개 | ✅ +900% |
| 활성 전략 | 6개 (앙상블) | ✅ +500% |
| 거래 빈도 | 50-100건/일 | ✅ +5000% |
| 승률 | 35-40% | ✅ +35% |
| MDD | -100% | ⚠️ 여전히 높음 |
| 총점 | 50-60/100 | ⚠️ C등급 |

### **After (Phase 3: 앙상블 + Top50 + 필터)**
| 지표 | 목표 값 | 개선 |
|------|---------|------|
| 심볼 수 | 50개 | ✅ +900% |
| 활성 전략 | 6개 (앙상블) | ✅ +500% |
| 거래 빈도 | 30-50건/일 | ✅ +3000% |
| 승률 | 40-50% | ✅ +77% |
| MDD | -15% ~ -20% | ✅ **목표 달성** |
| 총점 | 70-80/100 | ✅ B등급 |

---

## 🎯 **6. 즉시 실행 가능한 액션**

### **Action 1: 앙상블 활성화**
```bash
# config.yml 수정
sed -i 's/use_ensemble: false/use_ensemble: true/' config.yml

# 백테스트 재실행
docker-compose run --rm backtester python main.py
```

### **Action 2: 심볼 확장 (Manual 10개)**
```yaml
# config.yml 수정
symbols:
  mode: manual
  manual:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    - SOLUSDT
    - XRPUSDT
    - ADAUSDT
    - DOGEUSDT
    - DOTUSDT
    - MATICUSDT
    - AVAXUSDT
```

### **Action 3: Top50 전환 (공격적)**
```yaml
# config.yml 수정
symbols:
  mode: top50
```

---

## 📝 **7. 검증 체크리스트**

### **변경 전 확인사항**
- [ ] config.yml 백업 생성
- [ ] 현재 설정 스크린샷 저장
- [ ] 최근 백테스트 결과 저장

### **변경 후 확인사항**
- [ ] 로그에서 활성 전략 개수 확인
- [ ] 심볼 리스트 확인
- [ ] 거래 빈도 증가 확인
- [ ] 승률 변화 확인
- [ ] MDD 변화 확인
- [ ] 총점 변화 확인

### **성공 기준**
- ✅ 활성 전략: 6개
- ✅ 거래 빈도: 20건/일 이상
- ✅ 승률: 35% 이상
- ✅ MDD: -50% 이내 (단계별 개선)
- ✅ 총점: 50점 이상

---

## 📚 **8. 참고 문서**

### 📝 **생성된 파일**

1. `config_backup_before_ensemble.yml` - 설정 백업
2. `docs/PHASE3/SYSTEM_CONFIG_STATUS.md` - 시스템 설정 현황
3. `docs/PHASE3/ENSEMBLE_BACKTEST_RESULTS.md` - 앙상블 백테스트 결과
4. `docs/PHASE3/TEST_CHECKLIST.md` - 체계적 테스트 체크리스트 
5. `check_config.py` - 설정 검증 스크립트
6. `check_log.py`, `check_log2.py` - 로그 분석 스크립트

## ⚠️ **체계적 테스트 필요성**

### **문제점 발견**
현재 방식(모든 전략 + 9개 심볼 동시 테스트)은 **TEST_SCENARIO.md 원칙 위반**:
- ❌ 원인-결과 추적 불가
- ❌ 어떤 전략이 효과적인지 모름
- ❌ 어떤 파라미터가 중요한지 모름

### **올바른 접근 (TEST_SCENARIO.md 기반)**
1. **단일 전략 × BTCUSDT** (scalping부터)
2. **Exits 그리드 테스트** → 손익비 구조 확보
3. **Entries 필터 테스트** → 허수 제거
4. 합격 후 → 다음 전략
5. 모든 전략 완료 후 → 앙상블로직

### **관련 메모리**
- PHASE1: 설정 중복 제거, 멀티 심볼 지원 완료
- PHASE2: TP 분할 시스템 구현 완료
- TUNING_VIBLE: 7단계 최적화 가이드

---

## 📝 **9. 참고 문서**

### **관련 파일**
- `config.yml`: 전체 설정
- `main.py`: 심볼/전략 로드 로직
- `signals/signal_generator.py`: 신호 생성 로직
- `strategies/ensemble.py`: 앙상블 로직

### **관련 메모리**
- PHASE1: 설정 중복 제거, 멀티 심볼 지원 완료
- PHASE2: TP 분할 시스템 구현 완료
- TUNING_VIBLE: 7단계 최적화 가이드

### **다음 문서**
- `ENTRY_FILTER_DESIGN.md`: 엔트리 필터 강화 계획
- `STRATEGY_TUNING.md`: 전략별 파라미터 최적화
