# 📝 환경변수 설정 가이드

**작성일**: 2025-10-18  
**버전**: v2.0

---

## 📋 목차

1. [개요](#개요)
2. [전략별 Config 파일](#전략별-config-파일)
3. [새로 추가된 환경변수](#새로-추가된-환경변수)
4. [전략별 권장 설정](#전략별-권장-설정)
5. [사용 방법](#사용-방법)

---

## 개요

### Config 파일 구조

```
📁 future_alarm_bot/
├─ env.example              # 템플릿 (Trading Manager용)
├─ config_scalp.txt         # 스캘핑 (1분)
├─ config_intraday.txt      # 단타 (5분)
├─ config_swing.txt         # 스윙 (15분)
├─ config_trend.txt         # 트렌드 (1시간)
├─ config_reversion.txt     # 평균회귀 (5분)
└─ config_breakout.txt      # 브레이크아웃 (15분)
```

---

## 새로 추가된 환경변수

### ⭐ PositionSizer (포지션 사이징)

```bash
# 품질 가중치 범위
QUALITY_WEIGHT_MIN=0.7        # 최소 가중치 (confidence 낮을 때)
QUALITY_WEIGHT_MAX=1.3        # 최대 가중치 (confidence 높을 때)

# 포지션 가치 한도
MAX_POSITION_VALUE=5000       # 한 포지션 최대 달러 가치
MIN_POSITION_VALUE=10         # 한 포지션 최소 달러 가치
```

### ⭐ RiskManager (리스크 관리)

```bash
# 심볼별 노출 한도
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3    # 자산의 30%까지

# 동시 포지션 수
MAX_CONCURRENT_POSITIONS=5         # 최대 5개 동시

# 일일 손실 한도
DAILY_LOSS_LIMIT_PCT=0.03          # 자산의 3%까지 손실 허용
```

---

## 전략별 권장 설정

### 1. Scalping (스캘핑) - 보수적

```bash
# 포지션: 작은 크기
QUALITY_WEIGHT_MIN=0.8
QUALITY_WEIGHT_MAX=1.2
MAX_POSITION_VALUE=2000
MIN_POSITION_VALUE=20

# 리스크: 엄격
MAX_EXPOSURE_PER_SYMBOL_PCT=0.2
MAX_CONCURRENT_POSITIONS=3
DAILY_LOSS_LIMIT_PCT=0.05
```

**특징:**
- ✅ 작은 포지션 (빠른 매매)
- ✅ 적은 동시 포지션 (3개)
- ✅ 높은 손실 한도 (5%, 많은 거래)

---

### 2. Intraday (단타) - 균형

```bash
# 포지션: 중간 크기
QUALITY_WEIGHT_MIN=0.7
QUALITY_WEIGHT_MAX=1.3
MAX_POSITION_VALUE=3500
MIN_POSITION_VALUE=30

# 리스크: 표준
MAX_EXPOSURE_PER_SYMBOL_PCT=0.25
MAX_CONCURRENT_POSITIONS=5
DAILY_LOSS_LIMIT_PCT=0.05
```

**특징:**
- ✅ 중간 포지션
- ✅ 표준 동시 포지션 (5개)
- ✅ 표준 손실 한도 (5%)

---

### 3. Swing (스윙) - 표준

```bash
# 포지션: 중대형
QUALITY_WEIGHT_MIN=0.7
QUALITY_WEIGHT_MAX=1.3
MAX_POSITION_VALUE=4000
MIN_POSITION_VALUE=50

# 리스크: 중간
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3
MAX_CONCURRENT_POSITIONS=5
DAILY_LOSS_LIMIT_PCT=0.04
```

**특징:**
- ✅ 중대형 포지션
- ✅ 많은 동시 포지션 (5개)
- ✅ 중간 손실 한도 (4%)

---

### 4. Trend (트렌드) - 공격적

```bash
# 포지션: 큰 크기
QUALITY_WEIGHT_MIN=0.6
QUALITY_WEIGHT_MAX=1.5
MAX_POSITION_VALUE=6000
MIN_POSITION_VALUE=100

# 리스크: 공격적
MAX_EXPOSURE_PER_SYMBOL_PCT=0.4
MAX_CONCURRENT_POSITIONS=3
DAILY_LOSS_LIMIT_PCT=0.03
```

**특징:**
- ✅ 큰 포지션 (강한 추세)
- ✅ 적은 동시 포지션 (3개, 집중)
- ✅ 낮은 손실 한도 (3%, 보수적)

---

### 5. Reversion (평균회귀) - 표준

```bash
# 포지션: 중간 크기
QUALITY_WEIGHT_MIN=0.75
QUALITY_WEIGHT_MAX=1.25
MAX_POSITION_VALUE=3000
MIN_POSITION_VALUE=30

# 리스크: 표준
MAX_EXPOSURE_PER_SYMBOL_PCT=0.25
MAX_CONCURRENT_POSITIONS=4
DAILY_LOSS_LIMIT_PCT=0.04
```

**특징:**
- ✅ 중간 포지션
- ✅ 보수적 가중치 (0.75-1.25)
- ✅ 중간 리스크

---

### 6. Breakout (브레이크아웃) - 공격적

```bash
# 포지션: 중대형
QUALITY_WEIGHT_MIN=0.6
QUALITY_WEIGHT_MAX=1.4
MAX_POSITION_VALUE=5000
MIN_POSITION_VALUE=100

# 리스크: 공격적
MAX_EXPOSURE_PER_SYMBOL_PCT=0.35
MAX_CONCURRENT_POSITIONS=4
DAILY_LOSS_LIMIT_PCT=0.035
```

**특징:**
- ✅ 중대형 포지션
- ✅ 공격적 가중치 (0.6-1.4)
- ✅ 높은 심볼 노출 (35%)

---

## 사용 방법

### 1. Signal Bot 실행 (전략별 config 사용)

```bash
# 스캘핑 봇
python telegram_signal_bot.py
# 내부에서 config_scalp.txt 읽음

# 트렌드 봇
python signal_bot_trend.py
# 내부에서 config_trend.txt 읽음
```

### 2. Trading Manager 실행 (env.example 기반)

```bash
# .env 파일 생성
cp env.example .env

# 값 수정
nano .env

# Trading Manager 실행
python trading_manager.py
```

### 3. Docker 실행

```bash
# docker-compose.yml에서 환경변수 주입
docker-compose up trading-manager
```

---

## 마이그레이션 가이드

### 기존 config 파일에 추가할 내용

모든 config_*.txt 파일 끝에 추가:

```bash
# ========================================
# 포지션 사이징 & 리스크 관리 ⭐ 신규
# ========================================
# 품질 가중치
QUALITY_WEIGHT_MIN=0.7
QUALITY_WEIGHT_MAX=1.3

# 포지션 한도
MAX_POSITION_VALUE=5000
MIN_POSITION_VALUE=10

# 심볼별 최대 노출
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3

# 동시 포지션 수
MAX_CONCURRENT_POSITIONS=5

# 일일 손실 한도
DAILY_LOSS_LIMIT_PCT=0.03
```

---

## 참고 문서

- [Position Sizing Guide](./POSITION_SIZING.md)
- [Trading Executor](./TRADING_EXECUTOR.md)
- [Refactoring Guide](./REFACTORING.md)

---

**Last Updated:** 2025-10-18  
**Status:** ✅ 모든 config 파일 업데이트 완료
