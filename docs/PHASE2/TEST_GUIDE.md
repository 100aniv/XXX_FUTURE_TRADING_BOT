# 🧪 Phase 1 테스트 가이드

**작성일:** 2025-10-21  
**목적:** Phase 1 완료 후 기능 검증  
**테스트 모드:** Backtest + Paper + Live (3개 모두)

---

## 📋 **설정 파일 차이점**

### **config.yml vs common/config.py vs .env**

#### **1. config.yml (데이터 파일)**
```yaml
# 역할: 설정 값 저장
mode: paper
symbols:
  mode: manual
  manual:
    - BTCUSDT
```

#### **2. common/config.py (로더 코드)**
```python
# 역할: config.yml 읽어서 딕셔너리로 변환
def load_yaml_config():
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)  # ← config.yml 읽기
```

#### **3. .env (비밀 정보)**
```bash
# 역할: API 키, DB 비밀번호 등
BINANCE_API_KEY=xxx
DB_PASSWORD=xxx
```

**관계:**
```
config.yml (설정)  ←읽음← common/config.py (로더)
.env (비밀)        ←읽음← (둘 다 사용)
```

**중복 없음! 완전히 다른 역할!** ✅

---

### **config.yml vs .env (원래 질문)**

| 파일 | 역할 | 내용 | Git 추적 |
|-----|------|------|---------|
| **config.yml** | 거래 설정 | 심볼, 전략, 리스크, 지표 등 | ✅ 추적 (공유) |
| **.env** | 비밀 정보 | DB, API 키, 텔레그램 토큰 | ❌ 무시 (비밀) |

**중요: 중복 없음!**
- config.yml: 모든 거래 로직 설정
- .env: 민감한 정보만

### **설정 우선순위**
```
config.yml (최우선)
  ↓
.env (비밀 정보만)
  ↓
환경변수 (fallback, deprecated)
  ↓
하드코딩 기본값 (최후)
```

---

## ✅ **테스트 체크리스트 (3개 모드 필수)**

**테스트 순서:**
1. ✅ Backtest (단일 심볼)
2. ✅ Paper (멀티 심볼)
3. ✅ Live (멀티 심볼, API 필요)

---

### **0. 사전 준비**

```bash
# config.yml 존재 확인
ls config.yml

# .env 존재 확인
ls .env

# 중복 없음 확인
# ✅ config.yml: 1개
# ✅ .env: 1개
# ✅ backtest_config.yaml: _archived/ (사용 안 함)
```

---

### **TEST 1: Backtest 모드** (단일 심볼)

#### **목적**
- HistoricalFeed 동작 확인
- config.yml 로드 확인
- 단일 심볼 버퍼 관리

#### **config.yml 설정**
```yaml
# mode는 환경변수로 제어
symbols:
  mode: manual
  manual:
    - BTCUSDT  # 백테스트는 첫 번째만 사용
```

#### **실행**
```bash
TRADING_MODE=backtest python main.py
```

#### **예상 출력**
```
✅ config.yml 로드 완료
✅ 설정 로드 (config.yml): mode=backtest
✅ Manual 모드: 1개 심볼
📊 백테스트 모드: BTCUSDT
⚠️ 백테스트는 단일 심볼만 지원 (멀티 심볼: paper/live 사용)
🚀 Trading Engine 시작
   Symbol: BTCUSDT
   Timeframe: 5m
⭐ BTCUSDT 버퍼 초기화 (maxlen=400)
```

#### **검증 항목**
- [ ] config.yml 로드 성공
- [ ] CSV 파일 읽기 성공
- [ ] BTCUSDT 버퍼 초기화
- [ ] 캔들 스트리밍 시작
- [ ] 신호 생성 확인

---

### **TEST 2: Paper 모드** (멀티 심볼 - Manual)

#### **config.yml 설정**
```yaml
symbols:
  mode: manual
  manual:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    - SOLUSDT
    - XRPUSDT
```

#### **실행**
```bash
# Paper Trading
TRADING_MODE=paper python main.py
```

#### **예상 출력**
```
✅ config.yml 로드 완료
✅ 설정 로드 (config.yml): mode=paper
✅ Manual 모드: 5개 심볼
📊 최종 심볼: 5개 (예: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT)
🚀 Trading Engine 시작
⭐ BTCUSDT 버퍼 초기화 (maxlen=400)
⭐ ETHUSDT 버퍼 초기화 (maxlen=400)
...
```

#### **검증 항목**
- [ ] 5개 심볼 모두 로드됨
- [ ] 각 심볼별 버퍼 초기화
- [ ] WebSocket 연결 성공
- [ ] 캔들 수신 확인

---

---

### **TEST 3: Live 모드** (멀티 심볼 - 실거래)

#### **⚠️ 주의사항**
- **실제 자금 사용!**
- API 키 필수
- 소액으로 테스트 권장

#### **config.yml 설정**
```yaml
symbols:
  mode: manual
  manual:
    - BTCUSDT  # 처음엔 1개만
```

#### **.env 설정**
```bash
BINANCE_API_KEY=your_key_here
BINANCE_SECRET=your_secret_here
```

#### **실행**
```bash
TRADING_MODE=live python main.py
```

#### **예상 출력**
```
✅ config.yml 로드 완료
✅ Manual 모드: 1개 심볼
🔴 라이브 모드: 1개 심볼 실거래
⭐ BTCUSDT 버퍼 초기화
```

#### **검증 항목**
- [ ] API 키 인증 성공
- [ ] WebSocket 연결 성공
- [ ] 멀티 심볼 구독
- [ ] 실시간 캔들 수신
- [ ] LiveBroker 초기화

#### **안전 체크**
- [ ] 소액 (예: $100) 테스트
- [ ] max_positions 제한 확인
- [ ] daily_loss_limit 확인
- [ ] 수동 종료 가능 (Ctrl+C)

---

### **TEST 4: Top50 모드** (Paper)

#### **config.yml 설정**
```yaml
symbols:
  mode: top50
  core:
    - BTCUSDT
    - ETHUSDT
  topN:
    n: 50
    min_volume_24h: 30000000
```

#### **실행**
```bash
TRADING_MODE=paper python main.py
```

#### **예상 출력**
```
🔍 거래량 상위 50개 심볼 조회 중...
✅ 거래량 상위 50개 심볼 로드 완료
   상위 10: BTCUSDT, ETHUSDT, SOLUSDT, ...
✅ Top50 모드: 52개 심볼
📊 최종 심볼: 52개 (예: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT...)
```

#### **검증 항목**
- [ ] Binance API 호출 성공
- [ ] 거래량 기준 정렬
- [ ] core 심볼 포함 (중복 제거)
- [ ] 50+α개 심볼 로드

---

### **4. 가드레일 테스트**

#### **config.yml 설정**
```yaml
symbols:
  mode: all  # 전체 심볼 (150+개)
  max_streams: 120  # 가드레일
```

#### **실행**
```bash
TRADING_MODE=paper python main.py
```

#### **예상 출력**
```
✅ All 모드: 157개 심볼
⚠️ 심볼 157개 → 120개로 제한
📊 최종 심볼: 120개 (예: ...)
```

#### **검증 항목**
- [ ] max_streams 제한 동작
- [ ] 120개로 캡핑
- [ ] 메모리 안정성

---

### **5. Config 전달 검증**

#### **확인 방법**
```bash
# 로그에서 확인
python main.py 2>&1 | grep "초기화"
```

#### **예상 출력**
```
✅ PositionSizer 초기화: Equity=10000, RPT=0.01
✅ RiskManager 초기화: Daily limit=300.00
```

#### **검증 항목**
- [ ] PositionSizer: config에서 읽음
- [ ] RiskManager: config에서 읽음
- [ ] os.getenv() 호출 없음

---

### **6. Ensemble Config 검증**

#### **확인 방법**
```python
# strategies/ensemble.py 확인
# CFG 딕셔너리 없어야 함
# config 파라미터 받아야 함
```

#### **검증 항목**
- [ ] CFG 딕셔너리 제거됨
- [ ] combine_signals(signals, conn, config)
- [ ] config['strategy']['ensemble'] 사용

---

## 🐛 **예상 오류 & 해결**

### **1. "config.yml 없음"**
```
⚠️ config.yml 없음, 환경변수 사용
```

**해결:**
```bash
# 루트에 config.yml이 있는지 확인
ls config.yml

# 없으면 git pull
git pull origin main
```

### **2. "SymbolManager 임포트 오류"**
```
ImportError: cannot import name 'SymbolManager'
```

**해결:**
```bash
# common/symbol_manager.py 존재 확인
ls common/symbol_manager.py

# 없으면 이미 있어야 함 (기존 파일)
```

### **3. "Binance API 타임아웃"**
```
❌ Binance API 요청 실패: Timeout
```

**해결:**
- 인터넷 연결 확인
- VPN 사용 시 해제
- 기본 심볼로 fallback됨 (정상)

### **4. "config 파라미터 없음"**
```
TypeError: __init__() missing 1 required positional argument: 'config'
```

**해결:**
- PositionSizer(config) 호출 확인
- RiskManager(config) 호출 확인
- engine.py에서 config 전달 확인

---

## 📊 **테스트 결과 기록**

### **TEST 0: Config 로드** ✅
- 날짜: 2025-10-21 18:10
- 결과: ✅ 성공
- config.yml: 로드 완료
- common/config.py: load_yaml_config() 정상 동작
- symbols.mode: manual
- symbols.manual: 5개 (BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT)
- 이슈: 없음

### **TEST 1: Backtest** ✅
- 날짜: 2025-10-21 18:11
- 결과: ✅ 동작 확인
- 심볼: BTCUSDT (단일)
- HistoricalFeed: 정상 동작
- 버퍼 초기화: 성공
- 이슈: strategy_params.yaml 없음 (무시 가능, config.yml 사용)

### **TEST 2: Paper (Manual)** ✅
- 날짜: 2025-10-21 18:12
- 결과: ✅ 성공
- 심볼 수: 5개 (BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT)
- 버퍼 초기화: 5개 모두 성공 ⭐
- WebSocket: 멀티 심볼 구독 성공
- SymbolManager: 정상 동작
- 이슈: 없음 

### **TEST 3: Live** ⏳
- 날짜: 
- 결과: ⏳ 대기 중 (API 필요)
- 이슈: 

### **TEST 4: Top50** ✅
- 날짜: 2025-10-21 18:17
- 결과: ✅ 성공
- 심볼 수: 50개
- Binance API: 정상 호출
- WebSocket: 50개 심볼 동시 구독 성공
- 버퍼 초기화: TAOUSDT, PUMPUSDT, ENAUSDT, XPLUSDT, BNBUSDT, SUIUSDT, WLDUSDT, ALPACAUSDT, ALPHAUSDT, BNXUSDT 등
- 이슈: 없음 

### **TEST 5: Top100** ✅
- 날짜: 2025-10-21 22:53
- 결과: ✅ 성공
- 심볼 수: 100개
- Binance API: 정상 호출
- WebSocket: 100개 심볼 동시 구독 성공
- 이슈: 없음

### **TEST 6: All 모드 + 가드레일** ✅
- 날짜: 2025-10-21 22:54
- 결과: ✅ 성공
- 전체 심볼: 150+개
- **가드레일 동작**: ✅ max_streams=120으로 제한
- 실제 구독: 120개 (TAGUSDT, KAIAUSDT, UMAUSDT, etc.)
- 이슈: 없음 

---

## 🚀 **다음 단계**

테스트 완료 후:

1. **포트폴리오 매니저 구현**
   - execution/portfolio_manager.py
   - 심볼별 exposure 제한
   
2. **거래 빈도 증가**
   - 전략 필터 완화
   - 멀티 타임프레임

3. **성과 모니터링**
   - 멀티 심볼 리포트
   - 심볼별 성과 비교

---

**작성:** Cascade AI  
**업데이트:** 2025-10-21 18:15 KST
