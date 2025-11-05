# 텔레그램 채팅방 분리 가이드 🤖

## 현재 상태 (옵션 1)

✅ **이미 적용됨!**

모든 메시지에 봇 이름이 자동으로 붙습니다:
```
*[SCALP]* 🟢 BTCUSDT LONG 진입...
*[INTRA]* 🔴 ETHUSDT SHORT 진입...
*[SWING]* 📈 BTCUSDT 시장 상태...
```

### 장점
- ✅ 한 채팅방에서 모든 신호 확인
- ✅ 전체 흐름 파악 쉬움
- ✅ 설정 간단 (지금 바로 사용 가능!)

### 단점
- ⚠️ 메시지 많으면 혼란스러움
- ⚠️ 알람 소리 구분 불가

---

## 옵션 2: 채팅방 완전 분리 (더 깔끔함!)

3개의 텔레그램 봇을 만들어서 각각 다른 채팅방 사용

### 📱 Step 1: 텔레그램 봇 3개 만들기

**@BotFather와 대화:**

```
/newbot
→ 이름: My Scalping Bot
→ username: my_scalp_signal_bot

TOKEN 받음: 123456789:AAxxxxx (저장!)

/newbot
→ 이름: My Intraday Bot
→ username: my_intra_signal_bot

TOKEN 받음: 987654321:BBxxxxx (저장!)

/newbot
→ 이름: My Swing Bot
→ username: my_swing_signal_bot

TOKEN 받음: 555666777:CCxxxxx (저장!)
```

### 📋 Step 2: CHAT_ID 3개 얻기

각 봇과 대화 시작 후:
```
https://api.telegram.org/bot[TOKEN]/getUpdates
```

각 봇의 CHAT_ID 3개를 얻습니다.

### 🔧 Step 3: .env 파일 수정

```bash
# .env.scalp
BOT_NAME=scalp
TELEGRAM_TOKEN=8155399036:AAGx2Ve-hEtzXyFogFoXpR_U701GQWhZBTk  # 스캘핑 봇 TOKEN
TELEGRAM_CHAT_ID=453694961        # 스캘핑 봇 CHAT_ID
...

# .env.intraday
BOT_NAME=intra
TELEGRAM_TOKEN=8275234688:AAFSpYAqgU0dZE-KS6zcOO_B550f6YnwhsA  # 단타 봇 TOKEN
TELEGRAM_CHAT_ID=453694961        # 단타 봇 CHAT_ID
...

# .env.swing
BOT_NAME=swing
TELEGRAM_TOKEN=8249468785:AAGtAnzSE6GL1mqXpmbOSlhztp-bOk4fLJs  # 스윙 봇 TOKEN
TELEGRAM_CHAT_ID=453694961       # 스윙 봇 CHAT_ID
...
```

### 🚀 Step 4: 봇 재시작

```powershell
docker-compose down
docker-compose up -d
```

---

## 🎯 비교표

| 항목 | 옵션 1 (Prefix) | 옵션 2 (분리) |
|------|-----------------|---------------|
| **설정 난이도** | ✅ 쉬움 (이미 완료!) | ⚠️ 중간 (봇 3개 만들기) |
| **메시지 구분** | ✅ Prefix로 구분 | ✅✅ 채팅방으로 완벽 구분 |
| **알림 설정** | ❌ 전체 동일 | ✅✅ 봇별 다르게 설정 가능 |
| **전체 흐름 파악** | ✅✅ 한눈에 보임 | ⚠️ 3개 방 확인 필요 |
| **메시지 혼잡도** | ⚠️ 많으면 혼란 | ✅✅ 깔끔 |
| **추천 사용자** | 신호 적을 때 | 신호 많을 때 (권장!) |

---

## 💡 추천 시나리오

### 처음 시작 → 옵션 1 (현재)
```
이미 적용되어 있음!
모든 메시지에 [SCALP], [INTRA], [SWING] 표시됨
```

### 며칠 써보고 메시지 너무 많으면 → 옵션 2
```
1. 텔레그램 봇 3개 만들기 (5분)
2. .env 파일 수정 (2분)
3. 재시작 (1분)
```

---

## 🔥 옵션 2의 추가 장점

### 1. 알림 차별화
```
스캘핑 채팅방: 무음 (많으니까)
단타 채팅방: 진동
스윙 채팅방: 소리 (중요하니까!)
```

### 2. 선택적 모니터링
```
장 초반: 스윙 봇만 확인
장 중반: 단타 봇 집중
급한 상황: 스캘핑까지 확인
```

### 3. 팀 공유 가능
```
스윙 채팅방: 팀원들과 공유
스캘핑 채팅방: 나만 확인
```

---

## 🎯 결론

**지금 당장:** 옵션 1이 이미 적용되어 있으니 **그대로 사용해보세요!**

**며칠 후:** 메시지가 너무 많다면 → **옵션 2로 전환** (가이드 참조)

---

## 📱 현재 메시지 예시 (옵션 1)

```
*[SCALP]* 🟢 BTCUSDT LONG 진입
가격: 67245.3
손절: 66831.0
목표: 67865.0

*[INTRA]* 📈 ETHUSDT 시장 상태: RANGE → UP

*[SWING]* 🔴 SOLUSDT SHORT 진입
가격: 145.8
손절: 147.2
목표: 143.5

*[SCALP]* ✅ BTCUSDT TP1 체결 +12.50 USDT
```

**보기 좋죠?** 👍

---

## ⚡ 빠른 전환 명령

### 옵션 2로 바꾸고 싶다면:

```powershell
# 1. 봇 3개 만들고 TOKEN/CHAT_ID 얻기

# 2. .env 파일 수정
notepad .env.scalp    # TOKEN & CHAT_ID 변경
notepad .env.intraday # TOKEN & CHAT_ID 변경
notepad .env.swing    # TOKEN & CHAT_ID 변경

# 3. 재시작
docker-compose down
docker-compose up -d
```

**끝!** 🎉

---

**지금은 옵션 1로 써보고, 불편하면 언제든 옵션 2로 전환하세요!**
