# 🔄 설정 통합 마이그레이션

**날짜:** 2025-10-21  
**목적:** .env + 3개 yaml → 통합 config.yml

---

## 🎯 **변경 사항**

### **Before (기존)**

```
.env (179줄)              ← 전략, 리스크, API 키 모두 섞임
strategy_params.yaml      ← 전략 파라미터
data/backtest_config.yaml ← 백테스트 설정
```

**문제:**
- ❌ 역할 불명확
- ❌ 설정 분산 (3개 파일)
- ❌ API 키 노출 위험
- ❌ 수정 불편

### **After (개선)**

```
.env                      ← 비밀만 (API 키, DB 접속)
config.yml                ← 모든 거래 설정
common/config.py          ← 통합 로더
```

**장점:**
- ✅ 역할 명확
- ✅ 한 파일 관리
- ✅ 비밀 분리
- ✅ 수정 편리

---

## 📝 **마이그레이션 가이드**

### **STEP 1: 백업**

```bash
# 기존 파일 백업
cp .env .env.backup
cp strategy_params.yaml strategy_params.yaml.backup
cp data/backtest_config.yaml data/backtest_config.yaml.backup
```

### **STEP 2: 새 파일 생성**

```bash
# .env.new → .env (비밀 정보만)
cp .env.new .env

# 실제 값 입력
nano .env
```

**`.env` (비밀 정보만):**
```bash
# Database
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db
DB_HOST=localhost
DB_PORT=5433
DB_NAME=trading_db
DB_USER=trading_user
DB_PASSWORD=trading_pw_2024

# Binance API
BINANCE_API_KEY=your_key_here
BINANCE_SECRET=your_secret_here

# Telegram
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### **STEP 3: config.yml 수정**

```yaml
# config.yml (거래 설정)

# 실행 모드
mode: paper  # backtest | paper | live

# 전략 선택
strategy:
  selector: ensemble

# 심볼
symbols:
  mode: manual
  list:
    - BTCUSDT

# 타임프레임
timeframe: 5m

# ... (나머지는 기본값 유지)
```

### **STEP 4: common/config.py 교체**

```bash
# 새 로더로 교체
cp common/config_new.py common/config.py
```

### **STEP 5: 코드 수정 (필요시)**

**Before:**
```python
from common.config import load_config

CFG = load_config()  # dict 반환
print(CFG['trading_mode'])  # 'paper'
```

**After:**
```python
from common.config import CFG

# 자동 로드됨!
print(CFG['mode'])  # 'paper'
print(CFG['capital']['initial'])  # 10000
print(CFG['strategy']['selector'])  # 'ensemble'
```

---

## 🔍 **설정 파일 구조**

### **config.yml (통합 설정)**

```yaml
# 실행 모드
mode: paper | backtest | live

# 전략
strategy:
  selector: ensemble | scalping | ...
  weights: {...}

# 심볼 & 타임프레임
symbols:
  mode: manual | top50 | ...
  list: [BTCUSDT, ...]
timeframe: 5m
lookback: 400

# 자본 & 리스크
capital:
  initial: 10000
risk:
  per_trade: 0.01
  daily_loss_limit: 0.03
  max_positions: 5
  max_exposure_per_symbol: 0.3

# 레버리지
leverage:
  min: 2
  max: 10
  default: 5

# 포지션 사이징
position_sizing:
  quality_weight_min: 0.7
  quality_weight_max: 1.3
  max_position_value: 5000
  min_position_value: 10

# 수수료 & 슬리피지
fees:
  maker: 0.0002
  taker: 0.0004
  slippage: 0.0005

# TP/SL
tp_sl:
  enable_trailing: true
  trail_after_tp1: true
  tp1_rr: 1.0
  tp2_rr: 2.0

# Flash Guard
flash_guard:
  enabled: true
  window_sec: 60
  threshold_pct: 0.03
  pause_candles: 3

# 필터
filters:
  cooldown_candles: 3
  volume_spike: true
  regime_filter: true
  mtf_confirm: true

# 알림
notifications:
  telegram:
    enabled: true
    system_name: TRADING

# 전략별 파라미터
strategies:
  scalping:
    timeframe: 5m
    rr: 2.5
    atr_mult_sl: 1.5
    risk_per_trade: 0.01
    cooldown_candles: 3
    filters:
      regime: false
      volume_spike: false
      mtf_confirm: false
  
  # ... (다른 전략들)

# 백테스트
backtest:
  period: ten_years
  periods:
    ten_years:
      start_date: "2015-01-01"
      end_date: "2025-10-19"
  data_dir: data/historical

# 지표
indicators:
  ema: {fast: 9, mid: 21, slow: 50}
  rsi: {length: 14}
  macd: {fast: 12, slow: 26, signal: 9}
  bollinger: {length: 20, std: 2.0}
  atr: {length: 14}
  volume: {ma_length: 30}

# 성능
performance:
  poll_interval_sec: 5
  enable_profiling: false
  log_level: INFO
```

---

## 🚀 **사용 방법**

### **Python 코드에서**

```python
from common.config import CFG

# 모드 확인
if CFG['mode'] == 'backtest':
    print("백테스트 모드")

# 전략 확인
strategy = CFG['strategy']['selector']
print(f"전략: {strategy}")

# 심볼 가져오기
symbols = CFG['symbols']['list']
print(f"심볼: {symbols}")

# 리스크 파라미터
risk_per_trade = CFG['risk']['per_trade']
daily_loss = CFG['risk']['daily_loss_limit']

# 전략별 파라미터
scalping_rr = CFG['strategies']['scalping']['rr']
scalping_filters = CFG['strategies']['scalping']['filters']

# 백테스트 기간
if CFG['mode'] == 'backtest':
    period = CFG['backtest']['period']
    start = CFG['backtest']['periods'][period]['start_date']
    end = CFG['backtest']['periods'][period]['end_date']
```

### **설정 수정**

```bash
# config.yml 수정
nano config.yml

# 재시작
python main.py
```

---

## ✅ **체크리스트**

- [ ] 기존 파일 백업
- [ ] `.env` 생성 (비밀 정보만)
- [ ] `config.yml` 수정 (거래 설정)
- [ ] `common/config.py` 교체
- [ ] 코드 수정 (필요시)
- [ ] 테스트 실행
- [ ] 기존 파일 삭제 (선택)

---

## 🔧 **문제 해결**

### **Q1: 기존 코드가 안 돌아가요**

**A:** 하위 호환성 유지됨. 기존 `load_config()` 사용 가능.

```python
# Before (여전히 동작)
from common.config import load_config
CFG = load_config()

# After (권장)
from common.config import CFG
```

### **Q2: .env 값이 안 읽혀요**

**A:** `.env` 파일 확인
```bash
# .env 파일 존재 확인
ls -la .env

# 권한 확인
chmod 600 .env

# 내용 확인
cat .env
```

### **Q3: config.yml이 없다는 에러**

**A:** 루트 디렉토리에 `config.yml` 생성
```bash
# 샘플 복사
cp config.yml.example config.yml

# 또는 직접 생성
nano config.yml
```

---

## 📚 **관련 문서**

- `config.yml` - 통합 설정 파일
- `.env` - 환경 변수 (비밀)
- `common/config.py` - 설정 로더
- `README.md` - 프로젝트 소개

---

## 🎉 **완료!**

**설정 통합 완료! 이제 한 파일로 모든 설정 관리!** 🚀

- ✅ 역할 명확
- ✅ 관리 편리
- ✅ 보안 강화
- ✅ 버전 관리 쉬움

**config.yml 수정 → 재시작 → 즉시 반영!**
