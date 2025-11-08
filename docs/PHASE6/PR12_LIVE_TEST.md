# 🚨 PR12 Live 모드 테스트 - 현재 실행 불가

## ❌ **치명적 문제: Live 모드 자체가 작동하지 않음**

**현재 상태**: Live 모드에서 Binance API 포지션 조회가 전혀 실행되지 않아 Live 모드 테스트 자체가 불가능

**문제점**:
- Live 모드 분기 로직이 실행되지 않음
- Binance API 포지션 조회 코드 도달 불가
- 상용 프로그램 기준과 완전히 다른 잘못된 구조

## 🔄 **재구현 완료 후 Live 테스트 계획**

### Live 모드 정상 작동 시 필수 사항:

### 1. Binance 계정 준비
- Binance 계정에 Futures 계좌 활성화
- Spot 계좌 → Futures 계좌로 소액 자금 Transfer (예: $100~$500)
- USDT-M 계좌로 전송해야 함 (주의: COIN-M이 아님)

### 2. API 키 권한 설정 (필수)
- **Enable Futures**: ✅ 반드시 필요 (선물 거래 권한)
- **Enable Spot & Margin Trading**: ✅ 선택사항 (자산 조회용)
- **Enable Withdrawals**: ❌ 번역: 절대 활성화 금지

### 3. IP 제한 설정 (중요)
- **오류 발생 시 확인**: IP 제한이 있는 경우 API 연결 거부 (-2015 오류)
- **권장 설정**: 로컬 개발 시 ✅ Unrestricted 또는 현재 IP 추가

### 4. .env 파일 갱신
- BINANCE_API_KEY=유효한_API_키
- BINANCE_SECRET=유효한_시크릿

## 📘 Live 모드 설정 가이드

### 1. Binance Futures 계좌 준비

#### 1.1 Futures 계좌 활성화
1. Binance 웹사이트 또는 앱에 로그인
2. **Derivatives** → **USDⓈ-M Futures** 메뉴 선택
3. 처음 접속 시 Futures 계좌 활성화 동의 필요
4. 계좌 활성화 완료 후 Futures 지갑 생성됨

#### 1.2 자금 Transfer (Spot → Futures)
**⚠️ 중요**: Futures 거래는 **Futures 지갑**의 자금만 사용 가능합니다.

**Transfer 방법**:
1. Binance 앱/웹에서 **Wallet** → **Fiat and Spot** 선택
2. **Transfer** 버튼 클릭
3. From: **Spot Wallet** → To: **USDⓈ-M Futures**
4. 금액 입력 (예: $100~$500 소액 테스트 권장)
5. **Confirm Transfer** 클릭

**또는 Futures 화면에서 직접**:
1. Futures 거래 화면 우측 상단 **Transfer** 버튼
2. From Spot → To Futures 선택
3. 금액 입력 및 전송

#### 1.3 API Key 권한 확인
1. Binance 웹사이트 → **API Management**
2. 사용 중인 API Key 선택
3. **Enable Futures** 권한이 체크되어 있는지 확인
4. 없다면 체크 후 저장 (2FA 인증 필요)

### 2. config.yml 설정

```yaml
# Live 모드 설정
mode: live  # paper → live로 변경

capital:
  initial: 100  # Futures 계좌에 Transfer한 금액과 일치시킬 것 (선택사항, LiveBroker는 실제 잔액 조회)

# API 키는 환경변수 또는 .env 파일에서 로드
# BINANCE_API_KEY=your_api_key
# BINANCE_SECRET=your_secret_key
```

### 3. Live 모드 실행

```powershell
# Docker Compose로 실행
docker-compose up -d trading_bot_live_ensemble

# 또는 로컬 실행 (trading_bot_env 활성화 필요)
python main.py
```

### 4. 모니터링

```powershell
# 로그 확인
docker logs trading_bot_live_ensemble -f

# 텔레그램 알림 확인
# - 시스템 시작 메시지
# - 거래 실행 알림
# - 포지션 상태 업데이트
```

### 5. 주의사항

⚠️ **Live 모드 실행 전 반드시 확인**:
1. ✅ Paper 모드에서 충분한 테스트 완료
2. ✅ Futures 계좌에 소액 자금만 입금 (처음엔 $100~$500 권장)
3. ✅ API Key의 Futures 권한 활성화
4. ✅ config.yml의 리스크 설정 확인 (max_positions, max_exposure 등)
5. ✅ 텔레그램 알림 설정 확인

⚠️ **자금 관리**:
- Spot 지갑과 Futures 지갑은 **완전히 분리**되어 있습니다
- Futures 거래는 **Futures 지갑의 자금만** 사용합니다
- Spot에 자금이 있어도 Futures로 Transfer하지 않으면 거래 불가
- Transfer는 언제든지 양방향으로 가능 (Spot ↔ Futures)

---
