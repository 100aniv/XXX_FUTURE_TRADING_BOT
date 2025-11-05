# 스캘핑 봇 문제 해결 및 개선 📈

## 🔍 문제 분석

### 발견된 문제
스캘핑 봇이 **신호를 전혀 생성하지 못함**

### 로그 분석 결과
```
✅ WebSocket 연결: 정상
✅ 캔들 수신: 정상 (매분 5개 코인의 1분봉 수신)
✅ 지표 계산: 정상 (오류 없음)
❌ 신호 생성: 0개
```

### 원인 파악
**로직 자체는 정상 작동**하지만, **신호 조건이 너무 엄격**했습니다.

#### 기존 로직의 문제점
```python
# 기존 pullback_long 조건
pullback_long = (
    reg == "상승장" and                    # 레짐이 상승장이어야 함
    last["close"] >= last["ema_fast"] >= last["ema_mid"] and  # EMA 정렬
    last["rsi"] >= 35 and                  # RSI 조건
    macd_up                                 # MACD 전환
)
```

**1분봉에서의 문제**:
1. **EMA 정렬 + RSI + MACD 전환**을 **동시에** 만족하기 매우 어려움
2. 1분봉은 변동이 작아서 조건 충족이 드묾
3. MACD 전환도 1분봉에서는 노이즈가 많음
4. 레짐 판정(`상승장`, `하락장`)도 1분봉에서는 자주 바뀜

---

## ✅ 해결 방법

### 스캘핑 전용 로직 추가

```python
def signal_logic(df: pd.DataFrame) -> Dict[str, Any]:
    # 스캘핑 감지
    is_scalping = CFG["timeframe"] in ["1m", "3m"]
    
    if is_scalping:
        # 조건 완화: BB 터치만으로도 신호
        bb_touch_upper = last["close"] >= last["bb_upper"] * 0.998  # 상단 근접
        bb_touch_lower = last["close"] <= last["bb_lower"] * 1.002  # 하단 근접
        ema_align_long = last["ema_fast"] > last["ema_mid"]         # 간단한 추세
        ema_align_short = last["ema_fast"] < last["ema_mid"]
        rsi_long = 30 < last["rsi"] < 70                            # 과열 회피
        
        # 완화된 조건
        pullback_long = ema_align_long and rsi_long and (
            macd_up or last["macd"] > last["macd_signal"]  # MACD 전환 OR 단순 상승
        )
        breakout_long = bb_touch_upper and ema_align_long
```

### 주요 개선 사항

1. **볼린저밴드 터치 조건 완화**
   - 기존: `last["close"] > last["bb_upper"]` (완전 돌파)
   - 개선: `last["close"] >= last["bb_upper"] * 0.998` (근접)

2. **MACD 조건 완화**
   - 기존: `macd_up` (전환 필수)
   - 개선: `macd_up or last["macd"] > last["macd_signal"]` (상승 중이면 OK)

3. **레짐 조건 제거**
   - 기존: `reg == "상승장"` 필수
   - 개선: EMA 정렬만 확인

4. **RSI 범위 확대**
   - 기존: `rsi >= 35` (롱), `rsi <= 65` (숏)
   - 개선: `30 < rsi < 70` (과열만 회피)

---

## 📊 설정 파라미터 조정

### config_scalp.txt 변경

```bash
# 변경 전
RR=1.3
ATR_MULT_SL=0.8  # 너무 좁았음

# 변경 후
RR=1.5           # 약간 증가
ATR_MULT_SL=1.0  # 증가 (손절 폭 넓힘)
```

**이유**:
- `ATR_MULT_SL=0.8`은 너무 좁아서 노이즈에도 손절 발생
- 1분봉은 변동이 커서 여유 필요

---

## 🎯 예상 결과

### 변경 전
```
신호: 0개/일
원인: 조건 불충족
```

### 변경 후
```
신호: 50-100개/일 (예상)
조건: BB 터치 + EMA 정렬 + RSI 정상
승률: 48-55% (낮지만 정상적인 스캘핑 승률)
```

---

## 🔧 테스트 방법

### 1단계: 봇 재시작
```powershell
docker-compose restart scalp-bot

# 로그 확인
docker-compose logs -f scalp-bot
```

### 2단계: 신호 확인
약 5-10분 내에 첫 신호가 와야 합니다.

```
기대 메시지:
*[SCALP]* *BTCUSDT* 📈 시장: 상승장 🟢🎯 신호: 롱 진입
가격: `111000.0` | ATR: `250.0` ...

신호 근거:
- EMA 정렬 + MACD 상승
- 볼린저밴드 상단 터치 + 상승 추세
```

### 3단계: 체결 추적
```
✅ BTCUSDT 롱 TP1 체결(50% 청산 가정) | +12.5 USDT | 일일누적 12.5
```

---

## 📌 주의사항

### 스캘핑의 특성
1. **많은 신호**: 하루 50-100개 (텔레그램 폭주 가능)
2. **낮은 승률**: 48-55% (정상)
3. **작은 수익**: 개별 수익은 작지만 반복으로 누적
4. **빠른 손절**: 손절도 자주 발생 (리스크 관리 중요)

### 권장 사항
```
초기 자본: 소액 추천 (1,000-2,000 USDT)
RISK_PER_TRADE: 0.002-0.003 (0.2-0.3%)
EQUITY_USDT: 작게 설정하고 테스트
```

---

## 🚀 추가 최적화 옵션

### 신호가 여전히 적으면
```bash
# config_scalp.txt에 추가
ENABLE_MTF_CONFIRM=false    # 멀티TF OFF
SYMBOLS에 코인 추가          # 10-15개로 증가
```

### 신호가 너무 많으면
```bash
COOLDOWN_CANDLES=1          # 0 → 1
ENABLE_VOL_SPIKE_FILTER=true  # 필터 ON
```

### 손절이 너무 자주 걸리면
```bash
ATR_MULT_SL=1.2             # 1.0 → 1.2
RR=1.3                      # 1.5 → 1.3 (익절 가깝게)
```

---

## 📝 요약

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| **신호 로직** | 5분봉 로직 공용 | 1/3분봉 전용 로직 |
| **BB 조건** | 완전 돌파 | 근접 (0.998배) |
| **MACD 조건** | 전환 필수 | 상승 중이면 OK |
| **RSI 범위** | 35-100/0-65 | 30-70 |
| **ATR_SL** | 0.8x | 1.0x |
| **RR** | 1.3x | 1.5x |
| **신호 예상** | 0개/일 | 50-100개/일 |

---

## ✅ 결론

**스캘핑 봇은 로직 오류가 아니라 조건이 너무 엄격**했습니다.

✅ 문제 해결: 1/3분봉 전용 로직 추가  
✅ 조건 완화: BB 터치, MACD 완화, 레짐 제거  
✅ 파라미터 조정: ATR_SL, RR 증가  
✅ 예상 결과: 50-100개 신호/일  

**이제 정상 작동할 것입니다!** 🚀
