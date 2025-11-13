# PHASE7-5 마스터 플랜: Live 전환 준비 (실전 운영)

**최종 업데이트**: 2025-11-13  
**현행 코드(b84c03c)**: Paper/Live 파리티 일부 미흡, TP 거래소 등록 미구현, Manager 상태 DB 미구현  
**상태**: ⚠️ PHASE7-2/3/4 선행 필요. 본 문서 내용은 TO-BE(미구현)
 
## ⚠️ 현재 상태 스냅샷 (최근 30/60분 · Paper)

- **60분**: closed=394, win_rate=31.2%, >8% 손실=20건  
  - Exit breakdown: SL 201건(avg -3.83%, min -16.65%), TP1 196건(avg +2.28%, min -4.86%), ONE_WAY_MODE 2건
- **30분**: closed=151, win_rate=26.5%, avg_pnl=-0.84%, min=-12.05%, max=+25.30%  
- **무결성**: 중복 진입 0, 양방향 OPEN 0, OPEN=13

---

## ✅ 수용 기준 (게이트)

- Paper/Live 파리티 100%: 주요 로직/체결/수수료/슬리피지/종료사유 diff=0
- Live 소액 테스트(≥1h, ≥30건):
  - 승률 ≥ Paper 승률 - 3%p 이내
  - >8% 손실 0건, extreme_loss_cutoff 위반 0건
  - 주문 거부/실패/취소율 ≤ 5%
- 무결성: 중복 진입 0, 양방향 동시 0, 미결 주문 유실 0
- ✅ 운영 안정성 (Dashboard/Healthcheck)
- ✅ 전략 검증 (백테스트, 성과 기반 가중치)

이제 **Live 모드 전환** 준비 및 안전한 실전 운영.

**참고**: [PHASE7_ALGORITHM_BEST.md](PHASE7_ALGORITHM_BEST.md) - 앙상블 시스템 알고리즘 종합 개선안

## 목표 (Goals)

- **Paper/Live 파리티 100%** 검증
- **Live 소액 테스트** ($100, 1-2 심볼)
- **단계적 확장** ($100 → $1,000 → Full)
- **Live 성과 = Paper 성과** (±3% 이내)
- **안전 운영 체계** 확립

## 범위 (Scope, In)

### 1. Paper/Live 파리티 검증 (2일)

**검증 항목**:
- 모든 로직 동일성 (Strategy/Risk/Engine)
- 수수료 정확 반영
- 슬리피지 예측 정확도
- SL/TP 주문 실행
- State Recovery 동작

**테스트**:
- Paper vs Live 로직 diff
- API 연결 테스트
- 주문 실행 테스트 (1회)

**영향 파일**:
- `execution/adapters/brokers.py` (LiveBroker)
- `config.yml::live.*`

### 2. Live 소액 테스트 (3일)

**단계**:
1. API 키 설정 및 검증
2. 최소 자본 ($100)
3. 1-2개 심볼만 (BTC/ETH)
4. 레버리지 1x (안전)
5. 24시간 모니터링

**목표**:
- 주문 실행 성공률 100%
- SL/TP 정확 체결
- 수수료/펀딩피 정확 반영
- 승률 Paper와 ±3% 이내

**영향 파일**:
- `config.yml::mode: live`
- `.env` (API 키)

### 3. 단계적 확장 (2일)

**확장 계획**:
- 1단계: $100, 2 심볼, 3일
- 2단계: $500, 5 심볼, 1주
- 3단계: $1,000, 10 심볼, 2주
- 4단계: Full (사용자 결정)

**모니터링**:
- 각 단계별 성과 비교
- 슬리피지/수수료 실측
- 이상 징후 즉시 중단

## 제외 (Out-of-Scope)

- 전략 변경 (검증된 전략만 사용)
- API 키 자동 생성 (수동 설정)
- 레버리지 증가 (초기 1x 고정)

## 설정 키

```yaml
mode: live  # paper → live

live:
  enabled: true
  api_key_env: "BINANCE_API_KEY"
  api_secret_env: "BINANCE_API_SECRET"
  
  # 안전 설정
  max_capital: 100.0              # 최대 $100
  allowed_symbols: ["BTCUSDT", "ETHUSDT"]
  max_leverage: 1                 # 레버리지 1x
  max_positions: 2                # 최대 2개
  
  # 모니터링
  alert_on_every_trade: true      # 모든 거래 알림
  alert_on_sl_trigger: true       # SL 도달 알림
  alert_on_error: true            # 오류 즉시 알림
  
  # 비상 정지
  emergency_stop_loss_pct: -5.0   # 일일 -5% 시 정지
  emergency_contact: "+82-10-xxxx-xxxx"

fees:
  taker: 0.0004                   # 실제 수수료
  funding_rate_check: true        # 펀딩피 체크
```

## 구현 상세

### 1. Paper/Live 파리티 체크

```python
# scripts/check_parity.py
def check_paper_live_parity():
    """Paper/Live 로직 동일성 검증"""
    checks = [
        ('calculate_pnl', verify_pnl_logic),
        ('check_tpsl', verify_tpsl_logic),
        ('position_sizer', verify_sizing_logic),
        ('risk_guards', verify_risk_logic),
    ]
    
    failed = []
    for name, check_fn in checks:
        if not check_fn():
            failed.append(name)
    
    if failed:
        print(f"❌ 파리티 실패: {failed}")
        return False
    
    print("✅ Paper/Live 파리티 검증 완료")
    return True
```

### 2. Live API 연결 테스트

```python
# scripts/test_live_api.py
def test_binance_connection():
    """Binance API 연결 테스트"""
    client = Client(api_key, api_secret)
    
    # 1. Ping
    client.ping()
    print("✅ API Ping 성공")
    
    # 2. 계좌 정보
    account = client.futures_account()
    balance = float(account['totalWalletBalance'])
    print(f"✅ 잔고: ${balance:.2f}")
    
    # 3. 포지션 확인
    positions = client.futures_position_information()
    print(f"✅ 현재 포지션: {len(positions)}개")
    
    # 4. 테스트 주문 (DRY RUN)
    test_order = client.futures_create_test_order(
        symbol='BTCUSDT',
        side='BUY',
        type='LIMIT',
        quantity=0.001,
        price=30000
    )
    print("✅ 테스트 주문 성공")
    
    return True
```

### 3. Live 소액 실행

```python
# main.py
def main():
    mode = config.get('mode', 'paper')
    
    if mode == 'live':
        # 안전 확인
        if not confirm_live_mode():
            logger.error("❌ Live 모드 실행 취소")
            sys.exit(1)
        
        # 제한 확인
        check_live_limits(config)
        
        logger.warning("🔴 Live 모드 시작 - 실제 자본 사용!")
    
    engine = Engine(mode=mode, config=config)
    engine.run()

def confirm_live_mode():
    """Live 모드 확인"""
    print("⚠️ Live 모드로 실행하시겠습니까?")
    print("   실제 자본이 사용됩니다!")
    response = input("   'YES'를 입력하여 확인: ")
    return response == 'YES'

def check_live_limits(config):
    """Live 제한 확인"""
    live_config = config.get('live', {})
    
    max_capital = live_config.get('max_capital', 0)
    allowed_symbols = live_config.get('allowed_symbols', [])
    max_positions = live_config.get('max_positions', 0)
    
    logger.info(f"📊 Live 제한:")
    logger.info(f"   최대 자본: ${max_capital}")
    logger.info(f"   허용 심볼: {allowed_symbols}")
    logger.info(f"   최대 포지션: {max_positions}")
    
    assert max_capital > 0, "max_capital 설정 필요"
    assert len(allowed_symbols) > 0, "allowed_symbols 설정 필요"
```

## 수용 기준

### 필수

- [ ] Paper/Live 파리티: **100%**
- [ ] API 연결: **성공**
- [ ] 소액 테스트 ($100): 주문 실행 **100%**
- [ ] Live 승률: Paper 대비 **±3% 이내**
- [ ] 수수료/슬리피지: 예측 **±10% 이내**

### 선택

- [ ] 펀딩피 정확 반영
- [ ] 네트워크 지연 < 500ms
- [ ] API Rate Limit 초과 0회

## 테스트 플랜

### 사전 테스트

```bash
# 1. 파리티 체크
python scripts/check_parity.py

# 2. API 연결 테스트
python scripts/test_live_api.py

# 3. 설정 검증
python scripts/validate_config.py --mode live
```

### 소액 테스트

```bash
# 1. Live 시작 ($100, BTCUSDT only)
docker-compose -f docker-compose.live.yml up -d trading_bot_live

# 2. 24시간 모니터링
watch -n 60 "docker logs trading_bot_live --tail 20"

# 3. 성과 확인
docker exec trading_db_postgres psql -U trading_user -d trading_db -c "
SELECT 
  COUNT(*) as total,
  ROUND((COUNT(CASE WHEN pnl_pct > 0 THEN 1 END)::float / COUNT(*)) * 100, 1) as win_rate,
  ROUND(SUM(pnl), 2) as total_pnl
FROM trading.trades 
WHERE mode='live' AND ts_open >= NOW() - INTERVAL '24 hours';
"
```

### 비교 분석

```sql
-- Paper vs Live 비교
SELECT 
  mode,
  COUNT(*) as total,
  ROUND((COUNT(CASE WHEN pnl_pct > 0 THEN 1 END)::float / COUNT(*)) * 100, 1) as win_rate,
  ROUND(AVG(pnl_pct), 2) as avg_pnl,
  ROUND(SUM(pnl), 2) as total_pnl
FROM trading.trades 
WHERE ts_open >= NOW() - INTERVAL '7 days'
GROUP BY mode;
```

## 체크리스트

### 준비

- [ ] API 키 발급 (Binance Futures)
- [ ] 계좌 자금 입금 ($100+)
- [ ] Paper 2주 안정 운영 확인
- [ ] 승률 50% 이상 유지

### 검증

- [ ] Paper/Live 파리티 100%
- [ ] API 연결 테스트
- [ ] 테스트 주문 (DRY RUN)
- [ ] 설정 파일 검증

### 실행

- [ ] Live 소액 시작 ($100)
- [ ] 24시간 모니터링
- [ ] 성과 비교 (Paper vs Live)
- [ ] 이상 없으면 확장

### 확장

- [ ] 1단계: $100 → $500
- [ ] 2단계: $500 → $1,000
- [ ] 3단계: Full (사용자 결정)

## 안전 수칙

### 🔴 즉시 중단 조건

1. **일일 손실 -5% 초과**
2. **API 연결 10분 이상 끊김**
3. **SL 주문 등록 실패 2회**
4. **예상치 못한 포지션/주문**
5. **승률 30% 미만 (1주)**

### ✅ 운영 수칙

1. **매일 아침 점검** (포지션/잔고/로그)
2. **주간 성과 리뷰** (승률/PnL)
3. **비상 연락망 유지** (텔레그램)
4. **수동 개입 최소화** (시스템 신뢰)
5. **이상 시 즉시 중단** (Paper로 복귀)

## 배포/롤백

### 배포 순서

1. Paper 2주 안정 운영 확인
2. 파리티 검증 100%
3. API 연결 테스트
4. Live $100 시작
5. 24h 모니터링
6. 단계적 확장

### 롤백 조건

- 승률 Paper 대비 -5% 이상
- 일일 손실 -10% 이상
- API/시스템 오류 빈발
- 사용자 판단

## 리스크/완화

- API 키 유출? → 환경 변수만 사용, Git 제외
- 과도한 손실? → 일일 -5% 비상 정지
- 네트워크 장애? → Healthcheck 자동 재시작
- 예상치 못한 주문? → 즉시 수동 개입

## 연관 문서

- **PHASE7_ALGORITHM_BEST.md**: 상용 프로그램 알고리즘 비교 및 앙상블 개선안
- **GUARD_EXECUTION_ORDER_ANALYSIS.md**: 가드/차단 기능 실행 순서 분석
  - **Live 모드 필수 검증**: 가드 순서 준수 확인
- **SLIPPAGE_PERFORMANCE_COMPARISON.md**: 슬리피지 성능 비교
  - **Live 예상 슬리피지**: 0.5% ~ 2% (정상 시장)
- **체크리스트**: [PHASE7-2_MASTER_PLAN.md 항목 4](PHASE7-2_MASTER_PLAN.md) 참조

## 릴리즈 노트

PHASE7-5: Live 모드 전환 준비 완료. Paper/Live 파리티 100%, 소액 테스트 → 단계적 확장. 안전한 실전 운영 체계 확립.

## 최종 체크리스트

### Live 전환 전 필수 확인

- [ ] ✅ PHASE 7-1: 수수료 반영 + OHLC SL
- [ ] ✅ PHASE 7-2: 승률 45% 이상
- [ ] ✅ PHASE 7-3: Shutdown + Recovery
- [ ] ✅ PHASE 7-4: 승률 50% 이상
- [ ] ✅ Paper 2주 안정 운영
- [ ] ✅ 8% 초과 손실 0건
- [ ] ✅ 재시작 안전 검증
- [ ] ✅ Dashboard 정상 작동
- [ ] ✅ API 키 발급
- [ ] ✅ 자금 입금 ($100+)

**모두 완료 시 Live 시작 가능! 🚀**
