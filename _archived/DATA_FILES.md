# 📊 백테스트 데이터 파일 관리

## 🎯 **데이터 파일 위치**

```
data/historical/
├─ BTCUSDT_5m_2015-01-01_2025-10-19.csv   (55.7 MB) ✅
├─ BTCUSDT_15m_2015-01-01_2025-10-19.csv  (18.7 MB) ✅
├─ BTCUSDT_1h_2015-01-01_2025-10-19.csv   (4.7 MB) ✅
├─ BTCUSDT_4h_2015-01-01_2025-10-19.csv   (1.1 MB) ✅
└─ ... (ETHUSDT 동일)
```

---

## ⚙️ **설정 방법**

### 1️⃣ **.env 파일**
```bash
# 프리셋 사용 (추천)
BACKTEST_PERIOD=ten_years

# 직접 날짜 지정 (해당 파일 필요!)
# BACKTEST_START_DATE=2024-01-01
# BACKTEST_END_DATE=2024-12-31
```

### 2️⃣ **data/backtest_config.yaml**
```yaml
periods:
  ten_years:
    start_date: "2015-01-01"
    end_date: "2025-10-19"  # ⚠️ 실제 파일명과 일치!
```

---

## 📝 **새로운 데이터 다운로드**

**1개월 데이터가 필요한 경우:**

```bash
# 1. 다운로드 스크립트 실행
python scripts/download_historical_data.py

# 2. .env에서 기간 설정
BACKTEST_START_DATE=2024-10-01
BACKTEST_END_DATE=2024-10-31

# 3. 백테스트 실행
python main.py
```

---

## ⚠️ **중요**

- `.env` 설정과 실제 파일명이 **정확히 일치**해야 함
- 새로운 기간 데이터는 별도 다운로드 필요
- 기본 10년 데이터 사용 권장 (가장 빠름)
