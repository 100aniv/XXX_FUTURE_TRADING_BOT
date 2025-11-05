# 🚀 백테스트 빠른 시작 가이드

**목적**: 첫 백테스트를 10분 안에 실행하기

---

## ⚡ **빠른 시작 (3단계)**

### **Step 1: 데이터 다운로드**

```bash
# 백테스트 폴더로 이동
cd c:/Users/bback/OneDrive/Documents/future_alarm_bot/backtest

# 최근 3개월 데이터 다운로드 (빠른 테스트)
python data_downloader.py --start 2024-07-01 --end 2024-10-17

# 예상 소요 시간: 10-20분
# 다운로드 위치: ./data/historical/
```

**다운로드 진행 상황:**
```
📅 다운로드 기간: 2024-07-01 ~ 2024-10-17
📊 심볼: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, DOGEUSDT
⏰ 타임프레임: 1m, 5m, 15m, 1h
🎯 예상 파일 수: 1008
────────────────────────────────────────────────────────
📈 BTCUSDT - 1m
⬇️  다운로드 중: BTCUSDT-1m-2024-07.zip
✅ 완료: BTCUSDT-1m-2024-07.csv
...
```

---

### **Step 2: CSV 파일 병합**

```bash
# 월별 CSV를 하나로 병합
python data_downloader.py --start 2024-07-01 --end 2024-10-17 --merge

# 결과:
# data/BTCUSDT_1m_2024-07-01_2024-10-17.csv
# data/BTCUSDT_5m_2024-07-01_2024-10-17.csv
# data/BTCUSDT_15m_2024-07-01_2024-10-17.csv
# data/BTCUSDT_1h_2024-07-01_2024-10-17.csv
```

---

### **Step 3: 백테스트 실행**

```bash
# SCALPING 전략 백테스트
python backtest_engine.py \
  --strategy scalping \
  --start 2024-07-01 \
  --end 2024-10-17 \
  --capital 10000 \
  --output ../results/scalping_bt.json

# 결과 확인
python backtest_reporter.py \
  --input ../results/scalping_bt.json \
  --output ../reports/
```

**완료!** 🎉  
브라우저에서 `reports/backtest_report_xxxxxx.html` 파일을 열어보세요.

---

## 📋 **전체 워크플로우**

```
1️⃣ 데이터 다운로드
   └─> python data_downloader.py --start 2024-07-01 --end 2024-10-17

2️⃣ 데이터 병합
   └─> python data_downloader.py --merge

3️⃣ 개별 전략 백테스트 (6개)
   ├─> python backtest_scalping.py
   ├─> python backtest_daytrade.py
   ├─> python backtest_swing.py
   ├─> python backtest_trend.py
   ├─> python backtest_reversion.py
   └─> python backtest_breakout.py

4️⃣ 앙상블 백테스트
   └─> python backtest_ensemble.py

5️⃣ 리포트 생성
   └─> python backtest_reporter.py

6️⃣ 파라미터 튜닝
   └─> python param_optimizer.py
```

---

## 🔧 **각 전략별 백테스트 스크립트**

프로젝트 루트에 생성할 간편 스크립트들:

### **backtest_scalping.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCALPING 전략 백테스트"""

from backtest.backtest_engine import BacktestEngine, BacktestConfig

# 설정
config = BacktestConfig(
    strategy="scalping",
    start_date="2024-07-01",
    end_date="2024-10-17",
    initial_capital=10000,
    risk_per_trade=0.015,  # 1.5%
    max_positions=5,
    daily_loss_limit=0.05,  # 5%
    fixed_rr=1.5,  # 스캘핑: RR 1.5
    atr_mult_sl=1.0,
    atr_mult_tp=1.5
)

# 엔진 생성
engine = BacktestEngine(config)

# TODO: 시그널 생성 로직 구현
print("✅ SCALPING 백테스트 준비 완료")
print(f"   기간: {config.start_date} ~ {config.end_date}")
print(f"   자본: {config.initial_capital:,} USDT")
print(f"   RR: {config.fixed_rr}")
```

### **backtest_trend.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TREND 전략 백테스트"""

from backtest.backtest_engine import BacktestEngine, BacktestConfig

config = BacktestConfig(
    strategy="trend",
    start_date="2024-07-01",
    end_date="2024-10-17",
    initial_capital=10000,
    risk_per_trade=0.02,  # 2%
    max_positions=3,
    daily_loss_limit=0.05,
    fixed_rr=2.5,  # 트렌드: RR 2.5
    atr_mult_sl=1.5,
    atr_mult_tp=3.75
)

engine = BacktestEngine(config)
print("✅ TREND 백테스트 준비 완료")
```

---

## 📊 **예상 결과 예시**

백테스트 완료 후 나타나는 결과:

```
================================================================================
백테스트 결과 요약
================================================================================

📋 기본 정보
  전략: SCALPING
  기간: 2024-07-01 ~ 2024-10-17
  초기 자본: 10,000 USDT

📊 성과 지표
  총 거래 수: 450
  승리 거래: 247 (54.89%)
  손실 거래: 203

  평균 승리: 45.20 USDT
  평균 손실: -32.10 USDT
  Profit Factor: 1.75

  총 수익: 2,850 USDT (28.50%)
  최대 낙폭: -420 USDT (-4.20%)
  샤프 비율: 2.15
  소르티노 비율: 2.85

  평균 일일 수익: 26.85 USDT
  최대 연속 승리: 8
  최대 연속 손실: 5

⚠️  리스크 평가
  리스크 수준: 낮음 ✅

🎯 전략 평가
  종합 평가: 우수 ⭐⭐⭐

================================================================================
```

---

## 🎯 **주요 성과 지표 해석**

### **승률 (Win Rate)**
- **50-55%**: 보통 (스캘핑)
- **55-60%**: 좋음 (단타)
- **60%+**: 우수 (스윙/트렌드)

### **Profit Factor**
- **< 1.0**: 손실 전략 ❌
- **1.0-1.5**: 보통
- **1.5-2.0**: 좋음 ✅
- **> 2.0**: 우수 ⭐

### **Sharpe Ratio**
- **< 1.0**: 보통
- **1.0-2.0**: 좋음 ✅
- **> 2.0**: 우수 ⭐

### **Max Drawdown**
- **< 5%**: 매우 안전 ✅
- **5-10%**: 안전
- **10-20%**: 주의 ⚠️
- **> 20%**: 위험 ❌

---

## 🔍 **트러블슈팅**

### **문제 1: 데이터 파일 없음**

```
❌ 에러: 데이터 파일 없음: data/BTCUSDT_1m_2024-07-01_2024-10-17.csv
```

**해결:**
```bash
# 데이터 다운로드 확인
ls -la data/historical/BTCUSDT/1m/

# 병합 재실행
python data_downloader.py --merge --start 2024-07-01 --end 2024-10-17
```

---

### **문제 2: 모듈 import 에러**

```
❌ 에러: ModuleNotFoundError: No module named 'pandas'
```

**해결:**
```bash
# 필요한 패키지 설치
pip install pandas numpy matplotlib seaborn
```

---

### **문제 3: 메모리 부족**

```
❌ 에러: MemoryError
```

**해결:**
```python
# 데이터 청크로 나눠서 처리
# backtest_engine.py에서 chunk 단위로 로드
df = pd.read_csv(csv_file, chunksize=100000)
```

---

## 📈 **다음 단계**

### **1주차: 개별 전략 백테스트**
```bash
# 각 전략 순차 실행
python backtest_scalping.py   # Day 1-2
python backtest_daytrade.py   # Day 2-3
python backtest_swing.py      # Day 3-4
python backtest_trend.py      # Day 4-5
python backtest_reversion.py  # Day 5-6
python backtest_breakout.py   # Day 6-7
```

### **2주차: 파라미터 튜닝**
```bash
# 각 전략의 최적 파라미터 찾기
python param_optimizer.py --strategy scalping --param risk_per_trade --range 0.01,0.03
python param_optimizer.py --strategy scalping --param rr --range 1.5,2.5
```

### **3주차: 앙상블 최적화**
```bash
# 6개 전략 가중치 최적화
python optimize_ensemble_weights.py
```

---

## ⚡ **빠른 명령어 모음**

```bash
# 📥 데이터 다운로드 (3개월)
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17

# 🔗 CSV 병합
python backtest/data_downloader.py --merge

# 🧪 백테스트 실행 (SCALPING)
python backtest/backtest_engine.py --strategy scalping --capital 10000

# 📊 리포트 생성
python backtest/backtest_reporter.py --input results/scalping_bt.json

# 🔍 전체 워크플로우 (한 번에)
python run_full_backtest.py --strategy scalping
```

---

## 📦 **필요한 패키지**

```bash
# requirements.txt에 추가
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
psycopg2-binary>=2.9.0
requests>=2.31.0
```

**설치:**
```bash
pip install -r requirements.txt
```

---

## ✅ **체크리스트**

백테스트 시작 전 확인:

- [ ] Python 3.11 설치됨
- [ ] 필요한 패키지 설치됨 (`pip install -r requirements.txt`)
- [ ] 데이터 다운로드 완료 (최소 3개월)
- [ ] CSV 파일 병합 완료
- [ ] `backtest_engine.py` 테스트 성공
- [ ] `backtest_reporter.py` 테스트 성공
- [ ] PostgreSQL 실행 중 (선택사항)

---

## 🎓 **학습 자료**

### **백테스트 개념**
- `docs/BACKTEST_STRATEGY.md` - 백테스트 전략
- `docs/DAILY_TARGET_GUIDE.md` - 일일 목표 설정
- `docs/IMPLEMENTATION_ROADMAP.md` - 전체 로드맵

### **전략별 가이드**
- `docs/ENSEMBLE_6_STRATEGIES.md` - 6개 전략 설명
- `docs/POSITION_SIZING.md` - 포지션 사이징
- `docs/ENV_SETUP_GUIDE.md` - 환경 설정

---

## 💡 **팁**

### **빠른 테스트를 위해:**
```bash
# 1주일 데이터로 빠르게 테스트
python backtest_engine.py --start 2024-10-01 --end 2024-10-07
```

### **여러 전략 동시 실행:**
```bash
# PowerShell (병렬 실행)
Start-Job { python backtest_scalping.py }
Start-Job { python backtest_trend.py }
Start-Job { python backtest_reversion.py }
```

### **결과 비교:**
```bash
# 모든 결과 한 번에 비교
python compare_strategies.py --input results/*.json
```

---

## 🚀 **지금 바로 시작하기!**

```bash
# 1. 프로젝트 폴더로 이동
cd c:/Users/bback/OneDrive/Documents/future_alarm_bot

# 2. 데이터 다운로드 (10-20분)
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17

# 3. 병합
python backtest/data_downloader.py --merge

# 4. 첫 백테스트!
python backtest/backtest_engine.py --strategy scalping

# 5. 리포트 확인
explorer reports\  # Windows
```

---

**Last Updated:** 2024-10-18  
**Estimated Time:** 30분 (데이터 다운로드 포함)

**다음 문서**: `docs/BACKTEST_STRATEGY.md` (파라미터 튜닝)
