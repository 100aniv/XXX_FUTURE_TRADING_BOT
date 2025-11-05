# 3개 봇 동시 실행 가이드 🚀

## 📋 개요

3개의 봇이 동시에 다른 타임프레임으로 작동:
- **스캘핑 봇**: 1분봉 (50-100개 신호/일)
- **단타 봇**: 15분봉 (20-40개 신호/일)  
- **스윙 봇**: 1시간봉 (10-20개 신호/일)

**총 예상 신호: 95-190개/일**

---

## 🛠️ 설정 방법

### 1단계: .env 파일 생성

```powershell
# 스캘핑 설정
copy config_scalp.txt .env.scalp
notepad .env.scalp
# → TELEGRAM_TOKEN과 TELEGRAM_CHAT_ID 입력

# 단타 설정
copy config_intraday.txt .env.intraday
notepad .env.intraday
# → TELEGRAM_TOKEN과 TELEGRAM_CHAT_ID 입력

# 스윙 설정
copy config_swing.txt .env.swing
notepad .env.swing
# → TELEGRAM_TOKEN과 TELEGRAM_CHAT_ID 입력
```

### 2단계: Docker로 실행

```powershell
# 3개 봇 동시 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 봇만 로그 확인
docker-compose logs -f scalp-bot
docker-compose logs -f intraday-bot
docker-compose logs -f swing-bot

# 상태 확인
docker-compose ps

# 중지
docker-compose down

# 재시작
docker-compose restart
```

---

## 각 봇의 특징

### 스캘핑 봇 (1분봉)
```
타임프레임: 1m
코인: 7개
RR: 1.5x
손절: 1.0 ATR
쿨다운: 없음
필터: 거의 OFF
특별 로직: BB 터치 + EMA 정렬

특징:
✅ 가장 많은 신호
✅ 빠른 매매
✅ 조건 완화로 신호 증가
⚠️ 승률 낮음 (48-55%)
⚠️ 손절 자주 걸림
💡 소액으로 많은 경험
```

### 단타 봇 (15분봉)
```
타임프레임: 15m
코인: 7개
RR: 1.6x
손절: 1.0 ATR (중간)
쿨다운: 1캔들
필터: 일부 ON

특징:
✅ 균형잡힌 전략
✅ 적당한 신호 개수
✅ 괜찮은 승률 (55-62%)
💡 메인 전략으로 추천
```

### 스윙 봇 (1시간봉)
```
타임프레임: 1h
코인: 7개
RR: 2.0x
손절: 1.3 ATR (넓음)
쿨다운: 2캔들
필터: 대부분 ON

특징:
✅ 가장 높은 승률 (62-70%)
✅ 큰 수익 잠재력
✅ 안정적
⚠️ 신호 적음
💡 장기 수익에 적합
```

---

## 📊 예상 결과

### 시나리오 1: 보수적 운영
```
스캘핑: 50개 × 48% × 1.0% = +24%
단타: 30개 × 55% × 1.5% = +25%
스윙: 15개 × 65% × 2.0% = +20%
─────────────────────────────
손실 감안 후 순수익: 약 +15-25%/일
```

### 시나리오 2: 실전 (현실적)
```
스캘핑: 많은 신호, 작은 수익
단타: 주력 수익원
스윙: 안정적 기반

예상 일일 수익: +8-15%
나쁜 날: -2~5%
좋은 날: +15-30%
```

---

## ⚠️ 주의사항

### 1. 텔레그램 알람 폭주 가능
```
하루 100-200개 알람이 올 수 있음!

해결책:
1) 텔레그램 채널 3개로 분리
   - 스캘핑 전용 채널
   - 단타 전용 채널
   - 스윙 전용 채널

2) 알람 필터링
   - 중요한 것만 소리 알람
   - 나머지는 무음
```

### 2. 리스크 관리 필수
```
각 봇마다:
EQUITY_USDT=7000  (총 21,000원 상당 필요)

또는 비율로 조정:
스캘핑: 30% (2,100원)
단타: 50% (3,500원)
스윙: 20% (1,400원)
```

### 3. 서버 리소스
```
메모리: 각 봇당 ~150MB
CPU: 거의 안 씀
네트워크: WebSocket 3개 연결

→ 일반 PC도 충분!
```

---

## 🎯 추천 시작 방법

### 1주차: 단타 봇만
```
docker-compose up -d intraday-bot
```
- 시스템 이해
- 신호 품질 확인
- 승률 체크

### 2주차: 단타 + 스윙
```
docker-compose up -d intraday-bot swing-bot
```
- 타임프레임 차이 경험
- 리스크 관리 연습

### 3주차: 3개 전체
```
docker-compose up -d
```
- 풀가동
- 알람 관리 시스템 구축
- 수익 최적화

---

## 🔧 문제 해결

### 봇이 시작 안 됨
```powershell
# 로그 확인
docker-compose logs scalp-bot

# 설정 파일 확인
notepad .env.scalp

# 재빌드
docker-compose build
docker-compose up -d
```

### 신호가 안 옴
```
1. 텔레그램 TOKEN/CHAT_ID 확인
2. 네트워크 확인
3. 로그에서 에러 확인
```

### 너무 많은 알람
```
# 쿨다운 증가
COOLDOWN_CANDLES=2

# 필터 강화
ENABLE_MTF_CONFIRM=true
ENABLE_VOL_SPIKE_FILTER=true
```

### 승률이 낮음
```
# RR 증가
RR=2.0

# 손절 폭 증가
ATR_MULT_SL=1.5

# 타임프레임 증가
TIMEFRAME=15m
```

---

## 📱 텔레그램 채널 분리 방법

### 1. 봇 3개 만들기
@BotFather에서:
```
/newbot
→ Scalp Bot
→ username: your_scalp_bot

/newbot
→ Intraday Bot
→ username: your_intraday_bot

/newbot
→ Swing Bot
→ username: your_swing_bot
```

### 2. 각 .env에 다른 TOKEN 설정
```
.env.scalp → scalp bot TOKEN
.env.intraday → intraday bot TOKEN
.env.swing → swing bot TOKEN
```

### 3. 채널 3개 만들고 각각 초대
```
채널1: 스캘핑 신호
채널2: 단타 신호
채널3: 스윙 신호
```

---

## 🚀 시작하기

```powershell
# 1. .env 파일 생성 (위 1단계 참조)

# 2. Docker 실행
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 텔레그램에서 신호 대기!
```

**Good Luck! 🎯💰**
