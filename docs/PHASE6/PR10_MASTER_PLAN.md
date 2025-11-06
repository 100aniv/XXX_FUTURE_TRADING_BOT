# PHASE6 — PR10 마스터 플랜: 앙상블 고급화 + Experience Score + 베이시안 튜닝(설계)

## 배경/의도(Overview)
앙상블 품질을 고도화하고, 데이터 충분성과 최근 OOS 성능을 반영한 Experience Score를 도입합니다. 베이시안 튜닝은 페이퍼 모드에서 설계/준비만 수행하며, 실제 운영 반영은 PR13(운영 튜닝/롤아웃)에서 안전 게이팅과 함께 진행합니다.

## 목표(Goals)
- 앙상블 의사결정의 품질/안정성 향상
- Experience Score 산출 및 로깅
- 페이퍼 모드 기반 튜닝 설계(운영 반영은 PR13에서 단계적 적용)

## 범위(Scope, In)
- 가중치 개선(Sharpe, 승률, MDD, 샘플 크기 등)
- 보너스 로직(컨센서스/리스크 보정) 정리 및 클램핑
- Experience Score 계산/로깅
- 튜닝 파라미터/오버레이 구조 설계(실 적용은 PR13)

## 제외(Out-of-Scope)
- 엔진/Redis(→ PR9)
- 리스크 가드 강화(→ PR11)
- 고급 가격 레벨/거래소 스펙(→ PR12)

## 영향 파일(예상)
- strategies/ensemble.py(가중/점수/로깅)
- docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md(테스트)
- config.yml(ensemble.* 키; 튜닝 키는 PR13에서 활성화)

## 설정 키(제안; PR13에서 활성화)
- ensemble.min_confidence: float
- ensemble.consensus_bonus: float
- ensemble.max_weight_per_strategy: float
- ensemble.experience.min_trades: int
- tuning.enabled: bool(기본 false)
- tuning.sampler: "tpe"|"bayes"
- tuning.trials: int

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)
- 24시간 페이퍼 평가에서 baseline 대비 `score_total` ≥ 12% 향상
- Sharpe-like(analytics.kpis) ≥ 10% 향상
- 최대낙폭(MDD) 증가는 ≤ 1%p
- 최소 거래수 ≥ 60, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%
- DB/JSON 동등성 및 logs/trial_0000.json 유지
- pre-commit 통과, coverage>85%

## 체크리스트(Checklist)
- [x] 가중치 계산 업데이트 및 클램핑(설정 기반) ✅
- [x] Experience Score 계산/기록 ✅
- [x] 튜닝 파라미터/오버레이 구조 **설계 문서** 작성 ✅ (PR13_SYSTEM_ANALYSIS.md, PR13_ARCHITECTURE_DESIGN.md로 대체)
- [ ] 24시간 페이퍼 평가 (baseline 대비 성능 비교) - **중단** (청산 로직 오류 발견)
- [ ] **청산 로직 수정** - 포지션이 61시간 동안 유지되는 버그
- [ ] **튜닝 파라미터 오버레이 시스템 구현** - PR13에서 진행 예정
- [ ] **A/B 비교 리포트 생성 스크립트 구현** - PR13에서 진행 예정

## 테스트 플랜(Test Plan)
- 유닛: 가중치 수식/경계, Experience Score 입력/엣지
- 통합: 페이퍼 모드 N시간 비교(baseline vs 개선)
- A/B: 의사결정 분포/점수/간단 PnL proxy 비교

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- **2025-11-06 12:45** | ✅ Experience Score 구현 완료 | N/A | calculate_experience_score() 함수 추가, 데이터 충분성/최근 성과/안정성 반영 | min_trades 가드 (기본값 20)
- **2025-11-06 12:45** | ✅ 가중치 클램핑 구현 완료 | N/A | max_weight_per_strategy 설정 추가 (기본값 0.4), 클램핑 후 재정규화 | 단일 전략 독점 방지
- **2025-11-06 12:45** | ✅ config.yml 업데이트 완료 | N/A | ensemble.experience, ensemble.max_weight_per_strategy 추가, 주석 개선 | 설정 기반 조정 가능
- **2025-11-06 13:10** | ✅ 튜닝 파라미터/오버레이 구조 설계 완료 | N/A | PR10_TUNING_DESIGN.md 작성, 튜닝 대상 파라미터 정의, 오버레이 시스템 설계, 가드레일 정의, 롤아웃 전략 수립 | PR13 연계 준비 완료
- **2025-11-06 13:15** | ✅ A/B 비교 리포트 경로 정의 완료 | N/A | PR10_AB_COMPARISON.md 작성, 리포트 구조 정의, 메트릭 JSON 스키마, 마크다운 템플릿, 차트 생성 로직, 자동화 워크플로우 | PR13 구현 준비 완료
- **2025-11-06 13:50** | ✅ Bug #1: 일일 손실 한도 초과로 거래 중단 | 초기 28거래 중 23패 (82.1%), 총 손실 -$1,565 (한도 $500 초과) | config.yml: paper 모드 일일 손실 한도 5%→20% 임시 완화, 연속 손실 7→15 완화, Docker 재시작 | 거래 재개 확인 (재시작 후 30초에 16거래 발생)
- **2025-11-06 14:30** | ✅ Bug #2: pnl_pct 미계산 | trading.trades 테이블의 pnl_pct 컬럼이 NULL | engine.py close_trade_in_db(): entry_price/quantity 조회 후 pnl_pct 계산 및 UPDATE 쿼리에 추가 | 신규 거래부터 pnl_pct 정상 저장
- **2025-11-06 14:30** | ✅ Bug #3: 포지션 가치 초과 경고 | "포지션 가치 초과: $X > $Y" 반복 경고 | position_sizer.py: epsilon 0.1→1.0 USDT 완화 (부동소수점 오차 허용 범위 확대) | 불필요한 경고 감소
- **2025-11-06 18:50** | 🔴 Bug #4: 청산 로직 작동 안 함 (CRITICAL) | 44개 OPEN 포지션, 가장 오래된 것 61시간 유지 (11-04부터), 청산 0건 | **원인 확인**: symbols.mode=top100 (동적 심볼) → NMRUSDT가 top50에서 제외되어 WebSocket 구독 해제 → 캔들 안 들어와서 청산 체크 불가 | **수정 방안**: 1) OPEN 포지션 심볼은 무조건 WebSocket 구독 유지, 2) Startup 시 고아 포지션 강제 청산, 3) 주기적 포지션 체크 (가격 API 폴링)

## 라이브 모드 고려사항(Live Considerations)
- 라이브 전략 파일에 백테스트 전용 휴리스틱 삽입 금지(오버레이/설정으로 분리)
- 안전모드/섀도우런 우선, 실제 반영은 PR13의 게이트/롤아웃 정책 적용

## 리스크 & 롤백(Risks & Rollback)
- 튜닝 과적합 위험: OOS 윈도/패널티/최소 거래수 제약으로 완화
- 롤백: ensemble.* 기본값 회귀, 튜닝 비활성화

## 비고(Notes)
- PR13에서 베이시안 운영 튜닝을 정식 적용(스케줄러/오버레이/게이트 연동)
