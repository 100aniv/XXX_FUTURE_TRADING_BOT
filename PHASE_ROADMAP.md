📌 Future Alarm Bot – 최종 상용 버전까지 전체 로드맵

목표 한 줄 요약
“단일 엔진(backtest/paper/live 공용)에 기반한,
자동 리스크 관리 + Guard + 포트폴리오 + 모니터링까지 포함된
실제 운용 가능한 상용급 앙상블 트레이딩 시스템”

0. 전체 구조 개요
🔹 로드맵 큰 축

INFRA / ENGINE 안정화 (지금 ~ PHASE20 전후)

엔진, 포지션/포트폴리오, Budget, Guard, 데이터, 테스트 인프라

“수익”이 아니라 “망가지지 않는 구조”에 집중

STRATEGY / PERFORMANCE (PHASE20~PHASE30)

단일 전략(스캘핑) → 여러 전략 → 앙상블

백테스트/페이퍼 기반으로 승률·PnL·MDD 검증

PRODUCTION / OPERATIONS (PHASE30~PHASE40)

Live 구조, 실계좌 연결, 장애 대응, 모니터링, 알람, Runbook

“내가 안 보고 있어도 돌아가는 시스템”

1. 공통 규칙 (모든 Phase에 공통 적용)

이제부터 어떤 Phase든 무조건 아래 5개 규칙 깔고 간다.

✅ 진입 조건(Entry Criteria)

“이 Phase를 시작해도 되는지”를 정의

이전 Phase에서 최소한 무엇이 완료되어야 하는지 명시

✅ 퇴출 조건(Exit / Acceptance Criteria)

이 Phase를 “완료”라고 말하려면 반드시 충족해야 하는 구체적인 조건

조건 만족 못하면 다음 Phase로 못 넘어감

✅ 산출물(Deliverables)

코드 / 설정 / 문서 / 테스트 결과 정리

최소 1개 이상 MD 문서로 남김

✅ Out-of-Scope(이번 Phase에서 일부러 안 하는 것)

“중간에 욕심 내서 새로 벌릴 것들”을 미리 차단

예: 이 Phase는 승률 튜닝 안 함, 전략 추가 안 함 등

✅ 문제 발생 시 원칙

Acceptance 조건 만족 못하면
→ “버그/이슈 목록 MD + 원인/해결 계획” 작성
→ 해결 후에만 Phase 완료 선언

2. 현재 위치 기준: PHASE17 재정의

지금은 이미 PHASE0~16 + D단계를 거쳐서,
PHASE17 = Portfolio Budget / Position Sizing 인프라 단계에 와 있다고 보면 된다.

그래서 로드맵은 **“지금 이후”**를 중심으로 정의할게.

3. 상세 로드맵 (PHASE17 이후)
🧩 PHASE17 – Portfolio Budget & Position Infra 안정화 (현재 Phase)

목적

Budget SSOT 구조 확립

PortfolioManager / PositionSizer / Engine 간 데이터 플로우 안정화

REAL PAPER 12H 기준으로도 Budget/Guard가 정상 동작하는지 검증

진입 조건

엔진 단일 구조 (backtest/paper/live 공용) 이미 존재

Redis/Postgres/FlowGuardian 기본 구조 동작

기본 스캘핑 전략으로 Paper 모드 최소 15분~1시간 실행 경험 있음

주요 작업

PortfolioManager

_get_used_budget(), get_available_budget()

포지션 딕셔너리 키 통일 (position_value, status='OPEN' 등)

PositionSizer

리스크 기반 사이징 (RPT, SL, 레버리지 고려)

available_budget 파라미터 기반 Budget Cap

Cap 적용 시 로깅

Engine

포지션 생성 / 추가 / Scaling 시 Budget 플로우 일관성

Budget Cap 반영 후 다시 깨지지 않도록 값 재계산 방식 정리

테스트 인프라

단위 테스트 (Sizer / Portfolio / Budget 계산)

통합 테스트 스크립트 (Budget 시나리오)

REAL PAPER 1H & 12H 실행 테스트

퇴출(완료) 조건 – 반드시 통과해야 다음 Phase로 진행 가능

Budget 기능 Acceptance

통합 테스트에서 아래 시나리오 전부 통과:

Budget 내 Entry → Cap 없음

Budget 초과 Entry → Cap 적용

Budget 완전 소진 → Entry Block

REAL PAPER 12H Acceptance (아까 말한 그거)

모드: REAL PAPER

Config: real_paper_12h_v6_1_phase17.yml

최소 12시간 연속 실행 (중간 재시작 포함해 총 12H 이상)

기준:

Entry SUCCESS ≥ 100

Budget Cap Applied ≥ 1회 (실제로 여러 번)

Portfolio Budget BLOCK 비율 < 30%

ERROR/CRITICAL 0건

엔진 비정상 종료 0회

문서 / 리포트

PHASE17_PORTFOLIO_BUDGET_FINAL_REPORT.md

V4/V5/V6/V6.1/V6.1 12H 비교

문제 → 원인 → 해결 → 검증 결과

“PHASE17 인프라 Acceptance: PASS/FAIL” 명기

Out-of-Scope

승률 튜닝 / 전략 파라미터 최적화

새로운 전략 추가

앙상블 구현

Live 모드

🧩 PHASE18 – Strategy Correctness & Baseline Performance (단일 스캘핑 전략)

목적

“엔진이 안 망가진다”에서 한 단계 더 나가서,
단일 스캘핑 전략이 논리적으로 말이 되게 동작하는지 + 기본 성능이 괜찮은지 확인

진입 조건

PHASE17 Acceptance 통과 (Budget/Portfolio 안정)

REAL PAPER 12H 결과 리포트 완료

주요 작업

전략 로직 검증

진입 조건 / 청산 조건 / SL/TP / Trailing / Re-entry 로직을 문서화

코드와 문서의 내용이 일치하는지 점검

백테스트 인프라 정리

동일 엔진으로 backtest/paper/live 모드 동작

백테스트용 데이터 범위 정의 (예: 최근 6~12개월 BTC/ETH/KRW 등)

기본 성능 측정

최소 3개 구간에서 backtest 실행:

상승장, 하락장, 박스장 비슷한 구간

측정:

Win Rate, Expectancy, PnL, MDD, Trade 수, Avg holding time 등

퇴출(완료) 조건

백테스트 리포트 최소 3개

각 리포트에:

기간, 심볼, 파라미터, 결과 지표

장단점 / 비정상 구간 코멘트

“전략 논리 검증” 완료

명백히 말도 안 되는 버그(예: SL 안 걸리거나, TP가 음수인 수준)는 모두 제거

전략 설명 문서와 코드가 서로 못 알아보게 다른 상황은 제거

REAL PAPER 단기 검증

REAL PAPER 모드 4~6시간 테스트 1회 이상

백테스트 성향과 전혀 다른 이상 행동 없을 것

Out-of-Scope

Bayesian 튜닝, Grid Search 등 본격 Optimization

앙상블 / 다전략

실제 계좌 Live

🧩 PHASE19 – Risk & Guard 튜닝 (실전 레벨 리스크 모델링)

목적

DD, 포지션 수, 노출 한도, 슬리피지 등 리스크 관련 파라미터를 체계적으로 정리

상용 시스템 수준의 Risk/Governor 레이어 완성

진입 조건

PHASE18에서 기본 전략 성능/동작이 검증됨

엔진, Budget, Portfolio 쪽 치명 버그 없음

주요 작업

Risk 모델 정의

1회 손실 한도 (퍼센트 or R 기준)

1일/1주 DD 한도

동시에 열 수 있는 포지션 수, 심볼당 노출, 전체 노출

레버리지 상한

Guard/FlowGuardian 룰 재정리

DD Guard, Slippage Guard, Spread Guard, Volume Guard, Cooldown 등

각 Guard의 트리거 조건 / 해제 조건 / 로그 형식

테스트

극단 시나리오 백테스트:

연속 손실

급락 캔들

슬리피지 과한 상황 가정

퇴출 조건

Risk Policy 문서화

RISK_POLICY.md

수학적/논리적인 기준 + 운영 기준 정리

Guard 행동 검증

시나리오별 테스트 로그/리포트

Guard 때문에 “무조건 멈춤/영구 봉인”같은 상태가 아닌지 확인

Out-of-Scope

전략 로직 자체 변경 (엔트리/청산 구조 바꾸는 것)

앙상블

🧩 PHASE20 – 백테스트/데이터 인프라 확정 (신뢰할 수 있는 성능 측정 기준)

목적

“백테스트 결과 = 믿을만한 숫자” 상태 만들기

나중에 튜닝/앙상블 할 때 기초 데이터로 사용

진입 조건

PHASE19까지 엔진/리스크 구조 안정

기본 스캘핑 전략 정상 동작

주요 작업

데이터 품질

각 거래소 데이터 수집 모듈 / 이상치 처리 / 공휴일 / 서버 다운 구간 대응

타임존, 캔들 정렬 문제 해결

백테스트 실행 환경

같은 설정으로 여러 번 돌려도 동일 결과 보장 (멱등성)

Seed / 랜덤 요소 관리

리포트 포맷 통일

CSV/JSON/MD 등 결과 구조 표준화

나중에 통계/시각화 모듈 재사용 가능하게 설계

퇴출 조건

“참조 백테스트 세트” 결정

예: 최근 1년간 3개 이상 시나리오

이 세트를 기준으로 이후 모든 전략/튜닝/앙상블 검증

🧩 PHASE21 – 멀티 전략 & 앙상블 Infra

목적

여러 전략(스캘핑, 스윙, 트렌드 등)을 동시에 운용 가능한 구조 만들기

아직 “전략 다양화”가 아니라 “틀” 준비 단계

진입 조건

단일 전략 스캘핑이 안정 + 리스크/데이터 인프라 정리됨

주요 작업

Strategy Registry / Strategy Map

strategy_id → config, params, priority, weight 구조 설계

엔진에서 여러 전략을 동시에 불러와도 중복/충돌 안 나게 설계

Portfolio/Budget Multi-Strategy

전략별 Budget 할당 (예: scalping 50%, swing 30%, trend 20%)

전략 간 DD / 노출 제어

백테스트 & Paper 멀티 전략 실행 테스트

퇴출 조건

2개 이상의 전략을 동시에 백테스트 + Paper로 돌려보고,

Crash 없음

Budget/Guard/Portfolio가 정상 동작

ENSEMBLE_INFRA_REPORT.md 작성

🧩 PHASE22 – 멀티 전략 Paper 장기 실행 (3~7일)

목적

앙상블 구조가 실제로 “몇 시간”이 아니라 “며칠” 동안 돌아가도 안 망가지는지 확인

진입 조건

PHASE21에서 멀티 전략 인프라 PASS

작업

REAL PAPER 모드로 3~7일 실전 실행

전체 로그/통계/Equity 추적

Guard/Portfolio/Budget 이상 동작 없는지 확인

퇴출 조건

치명적인 구조적 문제 없을 것

“1일 이상 Entry 0” 같은 상태 지속 X

1회 이상 “정상적인 dd → 회복” 패턴 관측

🧩 PHASE23 – Live Shadow Mode (실계좌 미체결 모니터링)

목적

실 계좌/실 거래 환경과 완전히 같은 조건에서
**“신호만 발생시키는 Live”**를 돌려본다 (주문은 안 넣거나, 모의로만 기록)

진입 조건

Paper 멀티 전략이 3~7일 안정 실행

작업

실 계좌 연결

실제 호가/체결/슬리피지/수수료 환경 반영

하지만 주문은 실제로 안 나가고 DB에만 기록 (Shadow)

퇴출 조건

Shadow Trade와 Exchange 데이터 간 동기화 문제 없음

주문/포지션 트래킹, 슬리피지 계산, 수수료 반영 등이 논리적으로 맞음

🧩 PHASE24 – 제한된 자본 Live (소액 / 하나의 전략 / 낮은 레버리지)

목적

진짜 돈으로 돌려보되, 리스크를 극히 제한한 Pilot 운영

진입 조건

Shadow Mode에서 구조 문제 없음

작업

심볼/전략/레버리지/자본 제한 (예: BTCUSDT, 1전략, 1~3x, 자본 일부)

1~2주 정도 실제로 돌려보고

모든 체결/실현 PnL/Log를 분석

퇴출 조건

시스템적 문제(중복주문, SL 미작동, 포지션 꼬임 등) 0건

리스크 정책대로 손실 제한이 실제로 작동

🧩 PHASE25 – 상용 버전 정식 런칭 (Full Production)

목적

“한 번 만들어 놓고, 사람 손 안 타도 돌아가는” 상용 구조 완성

진입 조건

제한된 자본 Live에서 치명적 문제 없음

운영/알람/장애 대응 절차 어느 정도 정립

작업

운영 구조

Docker/K8s/Systemd 등으로 서비스화

재시작 정책, 버전 롤백, 파라미터 배포 방식 설계

모니터링 / 알람

Slack/Telegram 등으로 실시간 알람

PnL/Equity/에러/Guard 동작 상태 대시보드

Runbook / 운영 문서

장애 났을 때 누구(=당신)가 뭘 보면 되는지

어떤 경우엔 시스템 중지 / 어떤 경우엔 재시작

퇴출 조건

“나 혼자 1~2주간 크게 신경 안 써도, 최소한 시스템이 자기 선에서 리스크 컨트롤하면서 도는 상태”

그 상태를 문서로 정의하고, 나중에 봐도 이해 가능

4. 앞으로의 진행 방식 (이제부터 약속)

항상 “지금 Phase가 어디인지”를 먼저 정리

새로 뭐 하고 싶다 / 문제 생겼다 =
→ 이게 어느 Phase에 속하는 작업인지 먼저 매핑
→ 해당 Phase의 Scope/Out-of-Scope 확인
→ 벗어나면 “지금은 그 Phase가 아니다”라고 내가 먼저 말해줄 거야.

Acceptance 못 채우면 Phase++ 금지

“일단 넘기자” 식으로 안 감.

예: PHASE17에서 12H REAL PAPER Acceptance 못 통과하면
→ PHASE18 이야기 자체를 안 꺼냄.

네가 중간에 의심/질문할 때의 처리

“그건 사실 PHASE19에서 다루는 영역인데, 지금 PHASE17이라 여기선 이 정도까지만 본다” 식으로
내 계획이 더 맞다면 그걸 그대로 유지

반대로, 네 질문이 “로드맵에 진짜 빠져 있다”면
→ 로드맵 자체를 업데이트하고, 그걸 다시 스펙으로 삼음.

5. 지금 당장 상태 요약

현재: PHASE17 (Portfolio Budget & Position Infra) 중

해야 하는 핵심:

V6.1 Budget Fix 검증은 1H 수준에서 끝났고

이제 반드시 REAL PAPER 12H Acceptance를 통과해야 PHASE17을 닫을 수 있음

그 다음부터는 위 로드맵 Phase 순서대로만 갈 거고,
중간에 내가 “상용급”이란 말을 쓸 때도
반드시 이 로드맵 상에서 어느 Acceptance를 통과했는지 기준을 같이 말할게.

이제 이걸
docs/ROADMAP/FUTURE_ALARM_BOT_PHASE_ROADMAP.md
같은 이름으로 프로젝트 폴더에 저장해두면 좋겠다.

그 다음부터는

“지금 이거 무슨 Phase냐?”
라고 물으면, 난 항상 이 문서 기준으로 “우린 지금 PHASE17이고, Acceptance 중이다”
이렇게 대답하고 거기에 맞춰 다음 작업/프롬프트 짜줄게.