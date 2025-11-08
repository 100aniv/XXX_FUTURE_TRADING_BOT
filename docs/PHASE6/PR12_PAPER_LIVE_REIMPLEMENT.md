# PR12 Paper/Live 모드 완전 재구현 계획

## 🚨 **긴급 상황**

**현재 상태**: Live 모드에서 Binance API 포지션 조회가 전혀 실행되지 않음
**근본 원인**: PR10 구조를 무시한 잘못된 아키텍처 구현
**해결책**: PR12 완전 재구현

## 🎯 **재구현 목표**

### 상용 프로그램 기준 Paper/Live 모드 구현
```
Paper 모드: DB에서 가상 포지션 복원 → 거래 시작
Live 모드: Binance API에서 실제 포지션 조회 → 거래 시작
```

## 📋 **재구현 계획**

### 1단계: 아키텍처 수정 (CRITICAL)
**문제**: 데이터 피드가 `engine.run()` 호출을 차단
**해결**: 포지션 복원을 데이터 피드 시작 전에 실행

```python
# 현재 (잘못된 구조)
main() → feed 설정 → 무한 루프 → engine.run() 도달 불가

# 올바른 구조
main() → feed 설정 → engine.run() → 포지션 복원 → 거래 루프
```

### 2단계: Paper/Live 분기 구현
```python
def engine.run():
    # 1. 포지션 복원 (모드별 분기)
    if mode == "paper":
        # DB에서 가상 포지션 복원
        restore_positions_from_db()
    elif mode == "live":
        # Binance API에서 실제 포지션 조회
        restore_positions_from_binance()
    
    # 2. 거래 루프 시작 (공통)
    start_trading_loop()
```

### 3단계: 검증 및 테스트
- [ ] Paper 모드: DB 포지션 복원 확인
- [ ] Live 모드: Binance API 포지션 조회 확인
- [ ] 로그를 통한 분기 실행 검증
- [ ] 실제 거래 테스트

## 🔧 **구현 상세**

### core 수정 포인트
1. **main.py**: 실행 순서 수정
2. **engine.py**: 포지션 복원 로직 재배치
3. **brokers.py**: Paper/Live 브로커 파리티 보장

### 검증 기준
✅ **Paper 모드 로그**:
```
[PAPER] DB에서 가상 포지션 복원 중...
[PAPER] X개 포지션 복원 완료
```

✅ **Live 모드 로그**:
```
[LIVE] Binance API에서 실제 포지션 조회 중...
[LIVE] X개 포지션 조회 완료
```

## 📅 **타임라인**

- **Phase 1**: 아키텍처 수정 (즉시)
- **Phase 2**: Paper/Live 분기 구현 (30분)
- **Phase 3**: 검증 및 테스트 (30분)
- **Phase 4**: 문서 업데이트 (15분)

## 🎯 **성공 기준**

1. **Live 모드에서 Binance API 포지션 조회 실행 확인**
2. **Paper 모드에서 DB 포지션 복원 실행 확인**
3. **로직 파리티 100% 보장**
4. **상용 프로그램 기준 100% 준수**

---

**최종 목표**: 업계 표준에 부합하는 올바른 Paper/Live 모드 구현
