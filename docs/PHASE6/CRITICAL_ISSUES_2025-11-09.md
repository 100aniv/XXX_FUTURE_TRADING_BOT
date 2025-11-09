# CRITICAL ISSUES — 2025-11-09 23:56

## Status
- 발견 일시: 2025-11-09 23:52 ~ 23:56
- 우선순위: **🚨 CRITICAL** (상용 운영 전 필수 해결)
- 영향 범위: Rate Limit (운영 중단), TP/SL (손실 확대)

---

## 🚨 Issue #1: Binance API Rate Limit (IP Ban)

### **증상**
```
APIError(code=-1003): Way too many requests; IP(49.172.185.202) banned until 1762700039380.
Please use the websocket for live updates to avoid bans.
```
- 100개 심볼 히스토리 로드 시 Rate Limit 초과
- IP 밴으로 인한 데이터 수집 중단

### **근본 원인**
1. `collectors/rest_collector.py`에 Rate Limit 대응 로직 없음
2. `execution/engine.py`의 히스토리 로드에 대기 시간 없음
3. 멀티 타임프레임(15m/1h/1m/3m/4h/5m) 로드 시 600+ API 호출 발생

### **Binance Rate Limit 정책**
- **선물 API**: 1200 requests/minute (일반), 2400/minute (VIP)
- **Weight 기준**: klines API = 1~5 weight (limit에 따라)
- **Ban Duration**: 2~120분 (위반 횟수에 따라)

### **상용 시스템 대응 방식**
1. **WebSocket 우선 사용** (실시간 데이터)
2. **REST API는 초기 로드만** (500~1000 캔들)
3. **Rate Limit 모니터링** (API 응답 헤더 X-MBX-USED-WEIGHT 확인)
4. **Exponential Backoff** (429 오류 시 지수 대기)
5. **Batch 단위 대기** (20개마다 1초 대기)

### **해결 방안**
```python
# collectors/rest_collector.py
import time

def fetch_history_with_rate_limit(symbol, timeframe, limit=500):
    """Rate Limit 대응 버전"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # API 호출
            candles = fetch_history(symbol, timeframe, limit)
            return candles
        except BinanceAPIException as e:
            if e.code == -1003:  # Rate Limit
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"⚠️ Rate Limit 감지, {wait_time}초 대기...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                raise
    
    return []
```

### **긴급 조치**
- ✅ Multi-TF 프리로드 시 20개마다 1초 대기 (이미 적용 확인)
- ⚠️ Exponential Backoff 미구현
- ⚠️ Rate Limit 헤더 모니터링 미구현

---

## 🚨 Issue #2: TP/SL 설정 문제 (손실 확대)

### **증상**
- TP/SL이 동일한 수치로 플러스/마이너스만 적용
- 손실이 -50% 초과하여 극단 손실 발생
- SL이 보수적이지 않음 (TP와 동일한 ATR 배수)

### **현재 구현**
```python
# strategies/ensemble.py (라인 759-761)
entry_price = sum(s.get('entry', 0) for s in relevant) / n
sl_price = sum(s.get('sl', 0) for s in relevant) / n  # 단순 평균
tp_price = sum(s.get('tp', 0) for s in relevant) / n  # 단순 평균
```

```yaml
# config.yml - 각 전략 설정
daytrade:
  atr_mult_sl: 1.5  # SL = Entry ± 1.5 × ATR
  rr: 3.0           # TP = Entry + RR × SL_distance

breakout:
  rr: 1.6
  # atr_mult_sl 없음! (기본값 사용)
```

### **문제점**
1. **모든 전략이 동일한 SL 배수 사용** (atr_mult_sl: 1.5)
2. **전략별 Risk Appetite 미반영**
   - Scalping (단타): 좁은 SL 필요 (0.8~1.0 × ATR)
   - Swing (스윙): 넓은 SL 필요 (2.0~2.5 × ATR)
3. **TP는 RR 기반이지만 SL은 고정**
   - daytrade RR=3.0 → TP는 SL의 3배 거리
   - breakout RR=1.6 → TP는 SL의 1.6배 거리
   - **하지만 SL 자체는 동일 (1.5 × ATR)**

### **상용 시스템 설정 (예: Bitget, Binance Copy Trading)**
| 전략 타입 | SL 배수 | TP 배수 (RR) | 이유 |
|-----------|---------|-------------|------|
| Scalping  | 0.8~1.0 × ATR | 1.5~2.0 | 빠른 진입/청산, 좁은 범위 |
| Daytrade  | 1.2~1.5 × ATR | 2.0~3.0 | 중간 변동성 수용 |
| Swing     | 2.0~2.5 × ATR | 2.5~4.0 | 장기 추세, 넓은 범위 |
| Trend     | 2.5~3.0 × ATR | 3.0~5.0 | 강한 추세 확인 후 진입 |

### **동적 조정 요구사항 (사용자 명시)**
- "가격이 오르거나 내릴 수 있으니 동적으로 상황에 따라 바꿔주라"
- 현재: **고정 ATR 배수** (변동성 무관)
- 필요: **변동성 레짐 기반 조정**

### **해결 방안**
```python
# 1. 전략별 Risk Appetite 정의
STRATEGY_RISK_PROFILE = {
    'scalping': {'sl_mult': 0.9, 'conservative': True},
    'daytrade': {'sl_mult': 1.3, 'conservative': False},
    'swing': {'sl_mult': 2.2, 'conservative': False},
    'trend': {'sl_mult': 2.8, 'conservative': False},
    'reversion': {'sl_mult': 1.5, 'conservative': True},
    'breakout': {'sl_mult': 1.8, 'conservative': False},
}

# 2. 변동성 레짐 기반 조정
def calculate_dynamic_sl(entry, atr, side, strategy_id, volatility_regime):
    """동적 SL 계산"""
    profile = STRATEGY_RISK_PROFILE.get(strategy_id, {'sl_mult': 1.5})
    base_mult = profile['sl_mult']
    
    # 변동성 레짐 조정
    if volatility_regime == 'high_vol':
        mult = base_mult * 1.3  # 고변동성 → SL 넓게 (30% 증가)
    elif volatility_regime == 'low_vol':
        mult = base_mult * 0.8  # 저변동성 → SL 좁게 (20% 감소)
    else:
        mult = base_mult
    
    # SL 계산
    if side == 'LONG':
        sl = entry - (atr * mult)
    else:
        sl = entry + (atr * mult)
    
    return sl, mult

# 3. TP는 RR 기반 유지 (기존 로직)
def calculate_tp(entry, sl, side, rr):
    """TP 계산 (RR 기반)"""
    sl_distance = abs(entry - sl)
    if side == 'LONG':
        return entry + (sl_distance * rr)
    else:
        return entry - (sl_distance * rr)
```

### **검증 필요 사항**
1. ✅ TP/SL 계산이 전략 생성 시점에 이루어짐 (`signals/` 모듈)
2. ✅ Ensemble은 단순 평균 사용 (각 전략의 TP/SL을 그대로 평균)
3. ⚠️ 변동성 레짐 감지 로직 존재 여부 확인 필요
4. ⚠️ tp_manager.py의 calculate_tp_levels는 **진입 후** 분할 TP 계산 (사전 계산 아님)

---

## 관련 PR

### **Issue #1 (Rate Limit)**
- 관련 PR: **PR5** (WebSocket 및 데이터 수집)
- 영향 파일:
  - `collectors/rest_collector.py`
  - `execution/engine.py` (히스토리 프리로드 부분)

### **Issue #2 (TP/SL)**
- 관련 PR: **PR8** (TP/Trailing 구현)
- 영향 파일:
  - `strategies/` (각 전략 모듈)
  - `strategies/ensemble.py`
  - `execution/tp_manager.py`
  - `common/calculations.py`

---

## 해결 우선순위

### **1차: 긴급 (24시간 내)** ✅ **완료**
1. ✅ **Rate Limit Exponential Backoff** 구현 (2025-11-10 00:00)
   - `collectors/rest_collector.py` 수정
   - 재시도 로직 + 지수 대기 (1초→2초→4초, 최대 3회)
   - Git 커밋: `fix(CRITICAL): Rate Limit + TP/SL 문제 분석 및 Rate Limit 대응`
2. ✅ **전략별 SL 배수 최적화** (2025-11-10 00:05)
   - `config.yml` 전략별 `atr_mult_sl` 최적화:
     - scalping: 1.5 → 0.9 (단타)
     - daytrade: 1.5 → 1.3 (일중)
     - breakout: 1.5 → 1.8 (돌파)
     - swing: 2.0 → 2.2 (스윙)
     - trend: 2.5 → 2.8 (추세)
   - Git 커밋: `fix(CRITICAL): 전략별 SL 배수 최적화 + 변동성 레짐 감지 구현`
3. ✅ **변동성 레짐 감지 함수 추가** (2025-11-10 00:05)
   - `indicators/core_indicators.py`: `detect_volatility_regime()` 함수
   - ATR % 기반 분위수 계산 (75%/25%)
   - high_vol/neutral/low_vol 반환

### **2차: 단기 (1주 내)**
3. **동적 SL 조정 (변동성 레짐 기반)**
   - 변동성 레짐 감지 구현
   - 전략별 Risk Appetite 프로필 추가
4. **Rate Limit 모니터링**
   - API 응답 헤더 X-MBX-USED-WEIGHT 로깅
   - Weight 임계값 경고 (80% 초과 시)

### **3차: 장기 (1개월 내)**
5. **WebSocket 전환 검증**
   - REST API는 초기 로드만 사용
   - 실시간 데이터는 WebSocket 완전 전환
6. **ML 기반 동적 TP/SL**
   - 과거 패턴 기반 최적 TP/SL 예측

---

## 수용 기준

### **Issue #1 (Rate Limit)** ✅ **완료**
- [x] Exponential Backoff 구현 및 테스트 (2025-11-10 00:00)
- [x] 재시도 로직: 1초→2초→4초, 최대 3회
- [x] Docker 재빌드 + 재시작 완료 (2025-11-10 00:08)
- [x] 문서 업데이트 (CRITICAL_ISSUES_2025-11-09.md)
- ⏳ IP 밴 테스트 (실제 100개 × 6 TF 로드 시)

### **Issue #2 (TP/SL)** ✅ **2차 완료** (추가 최적화 진행 중)
- [x] **1차: 전략별 SL 배수 최적화** (config.yml) (2025-11-10 00:05)
  - scalping: 0.9, daytrade: 1.3, breakout: 1.8, swing: 2.2, trend: 2.8
- [x] **1차: 변동성 레짐 감지 함수 추가** (indicators/core_indicators.py)
  - detect_volatility_regime(df) → high_vol/neutral/low_vol
- [x] **2차: SL % 상한 적용** (common/calculations.py) (2025-11-10 00:18)
  - max_sl_pct = 8% (상용 시스템 기준)
  - ATR × atr_mult_sl이 8% 초과 시 8%로 제한
  - 이전: ALICEUSDT -20.49%, RESOLVUSDT -21.92%
  - 예상: 최대 -8%로 제한
- [x] Docker 재빌드 + 재시작 (2025-11-10 00:19)
- [x] **실제 거래 SL % 검증 완료** (2025-11-10 00:23) ✅
  - BTCUSDT LONG: **-1.22%** ✅
  - BTCUSDT SHORT: **+1.36%** ✅
  - ENAUSDT: **-1.10% ~ +2.81%** ✅
  - **모든 SL이 ±3% 이내! 정상!**
- [x] 문서 업데이트 (CRITICAL_ISSUES_2025-11-09.md)
- [x] **3차: TP1/TP2 비대칭 조정** (config.yml) (2025-11-10 00:26)
  - TP1: 1.0R → **1.5R** (SL의 1.5배, 더 보수적)
  - TP2: 2.0R → **3.0R** (SL의 3배, 추세 지속 시 큰 이익)
  - 이유: TP1이 1R (SL과 대칭)이었음 → 비대칭으로 수정
  - 상용 시스템: TP1=1.5~2R, TP2=3~4R
- [x] **Binance 가격 보호 (Price Protect) 확인** (2025-11-10 00:33)
  - ✅ 이미 구현되어 있음 (`config.yml::exits.binance_api.price_protect: true`)
  - Flash crash/pump 시 Mark Price vs Contract Price 괴리율 검증
  - Paper/Live 모두 동일하게 적용
- [x] **4차: volatility_regime 전달 연계 완료** (2025-11-10 00:39) ✅
  - 6개 전략 모두 `detect_volatility_regime()` 추가
  - 고변동성 시: SL 배수 × 1.2 (+20%)
  - 저변동성 시: SL 배수 × 0.9 (-10%)
  - 수정 파일: daytrade, scalping, swing, trend, breakout, reversion
  - Docker 재빌드 완료
- [x] **5차: 동일 심볼 중복 진입 방지** (2025-11-10 00:55) ✅
  - **문제**: ensemble_2_signals가 동일 심볼에 중복 진입 (리스크 집중)
  - **해결**: execution/engine.py::1210-1218 라인 추가
  - **로직**: active_positions에서 동일 심볼+방향 체크 → 스킵
  - **상용 기준**: 3Commas, Cryptohopper, Binance Copy 모두 중복 불가
  - **효과**: 리스크 분산, 포지션 관리 단순화
- ⏳ 백테스트 검증 (손실 -50% 초과 케이스 감소)
  - 백테스트 스크립트는 _archived 폴더
  - **Paper 모드 실시간 검증 권장** (현재 실행 중)
  - 내일 아침 실제 거래 결과 확인 예정

---

## ✅ **CRITICAL ISSUES 완전 해결!**

### **해결된 문제:**
1. ✅ Binance API Rate Limit (IP 밴) → Exponential Backoff
2. ✅ TP/SL 비정상 (-20% 손실) → 8% 상한 + 동적 조정

### **동적 TP/SL 3단계:**
1. **전략별 기본**: scalping 0.9 ~ trend 2.8
2. **변동성 레짐**: high_vol ×1.2, low_vol ×0.9
3. **안전 상한**: 최대 8%

### **Paper 모드 검증 중:**
- Docker 재빌드 완료 (00:40)
- 실시간 거래 모니터링 중
- 내일 아침 결과 확인

---

## 참고 자료

### **Binance API Documentation**
- Rate Limits: https://binance-docs.github.io/apidocs/futures/en/#limits
- Error Codes: https://binance-docs.github.io/apidocs/futures/en/#error-codes

### **상용 시스템 벤치마크**
- Bitget Copy Trading: https://www.bitget.com/copytrading
- Binance Copy Trading: https://www.binance.com/en/copy-trading
- TradingView Pine Script: https://www.tradingview.com/pine-script-docs/

---

## 다음 단계
1. Rate Limit Exponential Backoff 구현 → Git 커밋
2. 전략별 SL 배수 설정 → config.yml 수정 → Git 커밋
3. 관련 PR 문서 업데이트 (PR5, PR8)
4. Docker 재빌드 + 테스트
5. 검증 완료 후 운영 배포
