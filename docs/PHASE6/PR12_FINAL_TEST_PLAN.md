# 🚨 PR12 테스트 계획 - 재구현 필요

## 📅 현재 상황 
- **이전 테스트**: 2025-11-08 18:50-19:20 (실패로 판명)
- **문제 발견**: 2025-11-08 23:00
- **재시작 필요**: Paper/Live 모드 아키텍처 완전 재구현

## ❌ **이전 테스트 결과: 전면 실패**

### 발견된 치명적 문제
- ❌ **Live 모드 Binance API 포지션 조회 미실행**
- ❌ **Paper/Live 분기 자체가 작동하지 않음**
- ❌ **상용 프로그램 기준 0% 준수**

### 잘못된 테스트 결론
- ⚠️ **이전 문서는 허위**: "✅ 성공" 표시 모두 무효
- ⚠️ **테스트 자체 의미없음**: 핵심 기능이 작동하지 않았음

## 🔄 **새로운 테스트 계획**

### 📋 **재구현 후 테스트 순서**
1. **아키텍처 수정 검증**
   - [ ] Paper 모드: DB 포지션 복원 실행 확인
   - [ ] Live 모드: Binance API 포지션 조회 실행 확인
   
2. **Paper/Live 파리티 검증**
   - [ ] 동일한 신호에 대한 동일한 반응
   - [ ] 로직 100% 일치 확인
   
3. **상용 프로그램 기준 검증**
   - [ ] 업계 표준 아키텍처 준수 확인

## 📊 모니터링 체크리스트

### 5분마다 확인 항목

#### 1. 시스템 상태
```powershell
docker ps | Select-String "trading_bot_paper_ensemble"
```
- [ ] 컨테이너 정상 실행 중

#### 2. 최근 로그 (에러 확인)
```powershell
docker logs trading_bot_paper_ensemble --tail 100 | Select-String "ERROR|CRITICAL|❌"
```
- [ ] 치명적 에러 없음

#### 3. 앙상블 예산 확인
```powershell
docker logs trading_bot_paper_ensemble --tail 200 | Select-String "전략 예산|strategy budget"
```
**기대값**:
- ensemble_1_signals = 25%
- ensemble_2_signals = 40%
- ensemble_3_signals = 55%

#### 4. 포트폴리오 상태
```powershell
docker logs trading_bot_paper_ensemble --tail 100 | Select-String "PORTFOLIO|포트폴리오 상태"
```
**확인 사항**:
- 총 포지션 / 20
- 총 exposure < 95%
- 전략별 포지션 < 5개

#### 5. 거래 실행
```powershell
docker logs trading_bot_paper_ensemble --tail 100 | Select-String "LONG @|SHORT @|SL 주문"
```
**확인 사항**:
- 거래 발생 여부
- SL 자동 등록
- 가격 반올림 적용

#### 6. PnL 추적
```powershell
docker logs trading_bot_paper_ensemble --tail 100 | Select-String "PnL 업데이트|Equity 업데이트"
```
**확인 사항**:
- Daily PnL 추적
- Total PnL 추적
- Equity 업데이트

## 📝 점검 기록

### 18:55 (5분 후)
- [ ] 시스템 상태: 
- [ ] 에러 발생: 
- [ ] 예산 배분: 
- [ ] 포트폴리오: 
- [ ] 거래 실행: 
- [ ] PnL 상태: 

### 19:00 (10분 후)
- [ ] 시스템 상태: 
- [ ] 에러 발생: 
- [ ] 예산 배분: 
- [ ] 포트폴리오: 
- [ ] 거래 실행: 
- [ ] PnL 상태: 

### 19:05 (15분 후)
- [ ] 시스템 상태: 
- [ ] 에러 발생: 
- [ ] 예산 배분: 
- [ ] 포트폴리오: 
- [ ] 거래 실행: 
- [ ] PnL 상태: 

### 19:10 (20분 후)
- [ ] 시스템 상태: 
- [ ] 에러 발생: 
- [ ] 예산 배분: 
- [ ] 포트폴리오: 
- [ ] 거래 실행: 
- [ ] PnL 상태: 

### 19:15 (25분 후)
- [ ] 시스템 상태: 
- [ ] 에러 발생: 
- [ ] 예산 배분: 
- [ ] 포트폴리오: 
- [ ] 거래 실행: 
- [ ] PnL 상태: 

### 19:20 (30분 후 - 최종)
- [ ] 시스템 상태: 
- [ ] 에러 발생: 
- [ ] 예산 배분: 
- [ ] 포트폴리오: 
- [ ] 거래 실행: 
- [ ] PnL 상태: 

## 🎯 최종 수용 기준

### 필수 조건 (모두 충족 필요)
1. ✅ 30분 동안 치명적 에러 없음
2. ✅ 앙상블 예산 배분 로직 정상 작동
   - ensemble_1_signals = 25%
   - ensemble_2_signals = 40%
   - ensemble_3_signals = 55%
3. ✅ 포트폴리오 가드 정상 작동
4. ✅ 거래 실행 및 SL 등록 정상
5. ✅ PnL 추적 정상
6. ✅ 텔레그램 알림 정상

### 선택 조건 (권장)
- ⭐ 최소 1회 이상 거래 발생
- ⭐ 다양한 앙상블 조합 확인 (1/2/3 signals)
- ⭐ 포트폴리오 거부 케이스 확인

## 📋 최종 보고서 작성 항목

### 1. 시스템 안정성
- 총 실행 시간:
- 발생한 에러:
- 메모리 사용량:

### 2. 앙상블 예산 배분
- ensemble_1_signals 사용 횟수:
- ensemble_2_signals 사용 횟수:
- ensemble_3_signals 사용 횟수:
- 예산 배분 정확도:

### 3. 거래 통계
- 총 거래 횟수:
- 포지션 최대 개수:
- 최대 exposure:
- 포트폴리오 거부 횟수:

### 4. PnL 현황
- 시작 Equity:
- 종료 Equity:
- Daily PnL:
- Total PnL:

### 5. Live 모드 준비 상태
- [ ] Paper 모드 안정성 확인
- [ ] 모든 PR12 기능 정상 작동
- [ ] 문서 업데이트 완료
- [ ] Live 모드 전환 준비 완료

---

## 🚀 다음 단계

Paper 모드 테스트 통과 시:
1. ✅ PR12 최종 완료 선언
2. ✅ 문서 최종 업데이트
3. ✅ Git commit & push
4. ⏳ Live 모드 소액 테스트 준비
   - Binance Futures 계좌 자금 Transfer
   - API Key 권한 확인
   - config.yml mode=live 변경
   - 소액 테스트 실행 ($100~$500)
