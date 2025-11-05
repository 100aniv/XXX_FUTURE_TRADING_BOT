# 📊 백테스트 시스템 사용 가이드

**작성일**: 2025-10-19  
**버전**: v1.0

---

## 🎯 완료된 작업

### ✅ **1. backtest_engine.py strategies 연동**
- strategies 모듈 (trend, reversion, breakout, scalping, daytrade, swing) import
- indicators 모듈 연동 (지표 계산)
- `run_strategy_backtest()` 메서드 구현
  - 실제 전략 로직 사용
  - 실시간과 동일한 신호 생성
  - TP/SL 체크
  - 성과 지표 계산

### ✅ **2. run_backtest.py 실행 스크립트**
- BacktestEngine과 완전 연동
- 6개 전략 + ensemble 지원
- JSON 결과 저장
- 전략 비교 리포트

---

## 🚀 사용법

### **Step 1: 데이터 다운로드 (필요 시)**

```bash
# 과거 데이터 다운로드 (7월~10월)
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17

# CSV 병합
python backtest/data_downloader.py --merge
```

**데이터 위치**: `data/` 폴더

---

### **Step 2: 개별 전략 백테스트**

```bash
# 가상환경 활성화
trading_bot_env\Scripts\activate

# scalping 전략
python run_backtest.py --strategy scalping

# daytrade 전략
python run_backtest.py --strategy daytrade

# swing 전략
python run_backtest.py --strategy swing

# trend 전략
python run_backtest.py --strategy trend

# reversion 전략
python run_backtest.py --strategy reversion

# breakout 전략
python run_backtest.py --strategy breakout

# ensemble (6개 통합)
python run_backtest.py --strategy ensemble
```

---

### **Step 3: 전체 전략 비교**

```bash
# 모든 전략 백테스트 + 비교 리포트
python run_backtest.py --strategy all
```

**출력 예시**:
```
전략          거래수      승률       수익률        샤프
------------------------------------------------------------
SCALPING        45    62.22%      12.50%      1.85
DAYTRADE        38    60.53%      15.30%      2.10
SWING           28    64.29%      18.20%      2.35
TREND           22    68.18%      22.50%      2.80
REVERSION       40    55.00%       8.50%      1.45
BREAKOUT        32    59.38%      14.80%      2.05
ENSEMBLE        42    65.00%      20.10%      2.60
------------------------------------------------------------
```

---

### **Step 4: 옵션**

```bash
# 기간 지정
python run_backtest.py --strategy scalping --start 2024-08-01 --end 2024-09-30

# 초기 자본 변경
python run_backtest.py --strategy scalping --capital 50000

# 리포트 생성 스킵
python run_backtest.py --strategy scalping --no-report
```

---

## 📁 결과 파일

### **1. JSON 결과** (`results/`)
```json
{
  "strategy": "scalping",
  "config": {...},
  "metrics": {
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": 0.6222,
    "avg_win": 85.50,
    "avg_loss": -45.30,
    "profit_factor": 1.89,
    "total_return": 1250.00,
    "total_return_pct": 12.50,
    "max_drawdown": 350.00,
    "max_drawdown_pct": 3.50,
    "sharpe_ratio": 1.85
  },
  "trades": [...]
}
```

### **2. 비교 리포트** (`reports/`)
- `strategy_comparison_YYYYMMDD_HHMMSS.json`
- 모든 전략의 성과 비교

---

## 🎨 다음 단계: 리포트 시스템

### **현재**:
- ✅ JSON 결과 저장
- ✅ 콘솔 요약 출력

### **향후 개선**:
```
reports/
├── __init__.py
├── base_reporter.py (HTML/PDF 공통)
├── backtest_reporter.py (백테스트용)
├── paper_reporter.py (Paper Trading용)
└── live_reporter.py (Live Trading용)
```

**기능**:
- 📊 HTML 리포트 (차트, 표)
- 📄 PDF 다운로드
- 📈 에퀴티 커브 그래프
- 📉 드로우다운 차트
- 🎯 거래 분석 (승패 분포, 시간대별 성과)

---

## 📋 파라미터 튜닝 워크플로우

### **1. 기본 백테스트**
```bash
python run_backtest.py --strategy scalping
```

### **2. 결과 분석**
- 승률 확인
- Profit Factor 확인
- MDD (최대 낙폭) 확인
- 샤프 비율 확인

### **3. 파라미터 조정**
- `strategies/scalping.py` 수정
- TP/SL 배율 조정
- 필터 조건 조정
- 지표 파라미터 조정

### **4. 재검증**
```bash
python run_backtest.py --strategy scalping
```

### **5. 반복**
최적의 파라미터 발견까지 반복

---

## 🔄 전략 튜닝 예시

### **Scalping 전략 개선**

**현재 설정** (`strategies/scalping.py`):
```python
RR = 1.5
ATR_MULT_SL = 1.0
COOLDOWN = 3
```

**튜닝 방향**:
1. 승률 낮으면 → 필터 강화 (RSI 범위 좁히기)
2. 수익 낮으면 → RR 증가 (1.5 → 2.0)
3. MDD 크면 → ATR_MULT_SL 감소 (손절 가까이)
4. 거래 너무 많으면 → COOLDOWN 증가

---

## 📊 성과 지표 해석

### **승률 (Win Rate)**
- **60% 이상**: 우수
- **50-60%**: 양호
- **50% 이하**: 개선 필요

### **Profit Factor**
- **2.0 이상**: 우수
- **1.5-2.0**: 양호
- **1.0-1.5**: 개선 필요
- **1.0 이하**: 손실

### **샤프 비율 (Sharpe Ratio)**
- **2.0 이상**: 우수
- **1.0-2.0**: 양호
- **1.0 이하**: 높은 변동성

### **MDD (Max Drawdown)**
- **5% 이하**: 우수
- **5-10%**: 양호
- **10% 이상**: 높은 리스크

---

## ⚠️  주의사항

1. **과최적화 주의**
   - 백테스트 성과가 너무 좋으면 의심
   - Walk-forward 검증 필요

2. **거래 비용**
   - 슬리피지 반영 (0.05%)
   - 수수료 반영 (Maker 0.02%, Taker 0.04%)

3. **리스크 관리**
   - 일일 손실 한도 (5%)
   - 최대 포지션 수 제한

4. **실전 차이**
   - 백테스트는 이상적 환경
   - 실전은 슬리피지, 지연 등 변수 多

---

## 🎯 다음 할 일

### **1. 데이터 다운로드**
```bash
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17
```

### **2. 첫 백테스트**
```bash
python run_backtest.py --strategy scalping
```

### **3. 전략 비교**
```bash
python run_backtest.py --strategy all
```

### **4. 파라미터 튜닝**
- 가장 좋은 전략 선택
- 파라미터 조정
- 재검증

### **5. Paper Trading**
- 백테스트 통과 후
- `.env`에서 `TRADING_MODE=paper`
- 1주일 실시간 테스트

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-10-19
