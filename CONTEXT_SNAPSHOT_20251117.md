==========================================================

0. 프로젝트 정체성 / Big Picture

==========================================================
	•	프로젝트명(가칭)
	•	Future Alarm Bot (FAB) / Multi-Strategy Ensemble Trading Bot
	•	최종 목표 (To-Be 상용 단계)
	•	6개의 서로 다른 전략을 가진 앙상블 봇 구축
	•	각 전략은 독립 모듈 (예: 스캘핑, 스윙, 데이트레이드, 추세/역추세, AI/ML 기반 등 — 구체 명칭은 기존 설계 문서 기준)
	•	공통 엔진 위에서:
	•	Backtest → Paper → Live 전 모드가 동일 엔진을 사용
	•	Bayesian 튜닝 + Ensemble Weighting까지 포함
	•	실거래에서도 버틸 수 있는 상용 프로그램급 안정성/구조
	•	현재 상태 (Now)
	•	과거에 이미:
	•	6전략 앙상블 구조
	•	베이시안 튜닝
	•	다양한 모듈/엔진/런너
를 한 번 구현했다가 복잡도/스파게티화/DRY 위반/가드 꼬임으로 구조적 붕괴 발생
	•	그래서 지금은:
	•	엔진/인프라를 다시 깔끔하게 재구축 중
	•	우선 Scalping 단일 전략 + 단일 엔진 + 깨끗한 Infra를 완성
	•	그 위에 다른 5개 전략 + 앙상블 + 베이시안 튜닝을 다시 얹는 2단계 전략으로 진행 중
	•	프로젝트 철학
	•	“기능 많은 쓰레기”가 아니라 “구조가 예쁜 상용급 시스템”
	•	코드보다 구조, 구조보다 안전, 안전보다 복구 가능성
	•	한 번 더 뜯어고칠 수 없는 구조를 목표로 리팩토링 중

⸻

==========================================================

1. 과거 버전 (v1) 이력 — 왜 갈아엎는 중인가

==========================================================
	•	v1에서 했던 것들:
	•	6개 전략으로 구성된 앙상블 봇 구현
	•	데이터 수집, 백테스트, 튜닝, 실시간 실행, Redis/DB, Risk, Portfolio 등 대부분 구현
	•	베이시안 튜닝(하이퍼파라미터 최적화)까지 도입
	•	다양한 전략 조합으로 Scalping+Swing+기타 전략 혼합 운용
	•	v1에서 터진 문제들:
	•	Backtest / Paper / Live 엔진 구조가 서로 달라짐
	•	전략 추가/수정이 반복되면서:
	•	하드코딩 파라미터가 여기저기 생김
	•	DRY/SRP 깨짐
	•	Risk/Portfolio/Guard 로직이 곳곳에 중복/분산
	•	Redis/DB/Scorecard/로그 구조도 단계별로 조금씩 바뀌어 회귀 테스트 어려움
	•	베이시안 튜닝 + 앙상블 조합까지 올라가면서:
	•	“어디를 건드려야 뭐가 깨지는지” 통제 불가 상태
	•	구조적 기술부채가 한계치 도달
	•	결론:
	•	“이 상태에서 땜빵으로 이어가면 상용급은 절대 못 간다”
	•	→ 엔진+인프라 레벨에서 다시 설계하기로 결정
	•	새 방향: **Scalping 단일 전략을 기준으로 ‘예쁜 단일 엔진 구조’**부터 다시 만드는 중

⸻

==========================================================

2. 현재 리빌드 방향 — 새 구조의 큰 그림

==========================================================
	•	리빌드 전략:
	1.	단일 전략(Scalping) + 단일 심볼 + 단일 타임프레임 기준으로
	2.	Backtest / Paper / Live가 공통 엔진을 쓰는 구조부터 재구축
	3.	Risk/Portfolio/Guard, Redis/DB, Config 시스템을 깨끗하게 재정의
	4.	이 구조가 안정화되면:
	•	다른 5개 전략 → 동일 패턴으로 온보딩
	•	앙상블 레이어(전략별 weight, AI 메타 전략, 베이시안 튜닝) 재도입
	•	To-Be 구조(최종 확장 형태):

/data           # Collector/Preprocessor (여러 거래소 공통)
/engine         # 단일 엔진 (backtest/paper/live 공용)
/strategies     # N개의 전략 (현재는 scalping부터 재구축)
/risk           # FlowGuardian + Guard 모듈 (DD, Exposure, Flash 등)
/portfolio      # Position sizing + Exposure routing
/exchanges      # Upbit, Binance, Paper 등 어댑터
/runner         # backtest_runner, paper_runner, live_runner (동일 엔진 래핑)
/configs        # YAML 기반 설정 (전략/환경/리스크/포트폴리오/엔진 모두)
/docs           # PHASE별 설계/리포트/테스트 문서



⸻

==========================================================

3. PHASE 철학 — 재구축 진행 방식

==========================================================
	•	PHASE 기반 개발
	•	각 PHASE는 “한 덩어리의 구조적 변경 + 테스트 + 문서화”를 의미
	•	예시(요약):
	•	PHASE 0~2 : 데이터/환경/기본 Infra
	•	PHASE 3~5 : 단일 엔진 골격 (루프, Hook, 모드 구조)
	•	PHASE 6   : 전략 구조 분리 (Strategy 인터페이스 확정)
	•	PHASE 7   : PortfolioManager(노출도/포지션/사이징)
	•	PHASE 8   : RiskManager + FlowGuardian
	•	PHASE 9   : Config(YAML) 리팩토링 (하드코딩 제거)
	•	PHASE 10  : Backtest 일관성 검증
	•	PHASE 11  : Paper 엔진 안정화
	•	PHASE 12  : 성능(루프/큐/슬리피지) 최적화
	•	PHASE 13  : Redis/DB 네임스페이스 및 상태 구조 통합
	•	PHASE 14  : Guard 체계 정리(Exposure/DD/Extreme/Flash)
	•	PHASE 15  : Runner 통합 (backtest/paper/live 동일 파이프라인)
	•	PHASE 16  : REAL PAPER 장시간 테스트 (1h/12h/72h)
	•	PHASE 17+ : PositionSizing/Exposure 재설계 + 앙상블 재도입 준비
	•	규칙:
	•	PHASE 건너뛰기 금지
	•	각 PHASE는:
	1.	설계 문서
	2.	코드 변경
	3.	테스트
	4.	리포트
	5.	Git 커밋
으로 완결된 단위

⸻

==========================================================

4. 단일 엔진 구조 (Backtest / Paper / Live 공용)

==========================================================
	•	Core Engine 목표:
	•	동일한 engine.py가 모드만 바꿔서:
	•	Backtest (과거 데이터 재생)
	•	Paper (실시간 데이터 + 모의 체결)
	•	Live (실제 거래소 주문)
를 모두 처리
	•	엔진 공통 플로우(단일 전략 기준):
	1.	시계열/스트림(캔들/틱) 수집
	2.	인디케이터/피처 계산 (RSI, EMA, ATR 등)
	3.	전략 모듈에서 신호 생성 (ENTRY/LONG/SHORT/CLOSE 등)
	4.	RiskManager/FlowGuardian 사전 필터링
	5.	PortfolioManager에서 포지션 크기/노출도 결정
	6.	OrderExecutor에서 주문 실행 (paper/live 분기)
	7.	결과/상태를 Redis/DB/로그/Scorecard에 기록
	•	DO-NOT-TOUCH 규칙 (엔진 레벨):
	•	메인 루프의 구조와 순서
	•	가격/슬리피지/PNL 계산 규칙
	•	Risk/Portfolio/Strategy 호출 순서
	•	Scorecard/로그/통계 산출 공식

⸻

==========================================================

5. 전략(Strategies) — 앙상블 6 전략 구조

==========================================================
	•	최종 형태:
	•	6개의 서로 다른 전략 모듈
(현재 새 구조에서는 Scalping 1개부터 재구축 중, 나머지 5개는 기존 설계/문서를 기반으로 나중에 재온보딩)
	•	설계 원칙:
	•	모든 전략은 동일한 인터페이스:

def generate_signal(context) -> StrategySignal:
    # context: candle, indicators, positions, risk_state 등


	•	전략 내부에:
	•	포지션 사이즈, 리스크 파라미터, 타임프레임, 심볼 등의 하드코딩 금지
	•	모두 YAML config → dataclass를 통해 주입
	•	최종 앙상블 단계:
	•	개별 전략 신호 + 가중치(베이시안 튜닝/AI 레이어 결과)를 조합해 최종 주문 결정

	•	현재 상태:
	•	기존 6전략 앙상블은 v1 구조에 묶여 있어서 그대로 재사용 불가
	•	새 구조에서:
	•	Scalping 전략을 기준 템플릿으로 삼아
	•	나머지 5개 전략을 동일 패턴으로 다시 구현/이식 예정

⸻

==========================================================

6. Risk / Portfolio / Guard 체계

==========================================================

6-1. PortfolioManager
	•	역할:
	•	심볼별/전략별 포지션 관리
	•	레버리지/사이즈 계산
	•	포트폴리오 전체 노출도/분산 제어
	•	현재 문제:
	•	v1 + 초반 v2에서는:
	•	포지션 크기가 사실상 “고정형”에 가깝고
	•	max_positions 같은 개수 제한 위주 -> Exposure Guard와 계속 충돌
	•	To-Be:
	•	동적 포지션 사이징 (ATR/변동성/잔고/리스크 비율 기반)
	•	per-symbol, per-strategy, 전체 포트폴리오 노출도를 수학적으로 관리

6-2. RiskManager & FlowGuardian
	•	기능:
	•	Drawdown Guard (DD%)
	•	Extreme Loss Guard
	•	Per-symbol Exposure Guard
	•	Flash Guard(급등락 구간 진입 차단)
	•	Slippage Guard
	•	Daily loss limit, 연속 손실 차단 등
	•	PHASE16에서 나타난 문제:
	•	Drawdown Guard / Exposure Guard가 너무 강하게 작동해서:
	•	12시간 Paper 테스트 도중 2~13분 만에 차단/정체
	•	YAML로 max_drawdown_pct, max_positions, cooldown 등을 조절해도 근본 문제 해결 X
	•	결론:
	•	리스크 수준 자체가 문제가 아니라,
	•	Portfolio/PositionSizing과 Guard 계산 방식이 구조적으로 잘못 얽혀 있음
	•	→ PHASE17에서 엔진+포지션사이징+Guard 연동 구조를 통째로 다시 설계해야 함

⸻

==========================================================

7. Config / YAML / 환경 분리

==========================================================
	•	목표:
	•	모든 하드코딩 제거
	•	전략/리스크/포트폴리오/엔진/런너 설정을 전부 YAML로 분리
	•	예시 구조:

configs/
  base.yml
  scalping/
    backtest_baseline.yml
    paper_testing.yml
    real_paper_1h.yml
    real_paper_12h.yml
    real_paper_12h_v3.yml
  ensemble/
    ...


	•	PHASE9 이후 규칙:
	•	새로운 기능/파라미터는 항상 YAML → dataclass → 코드 순으로 유입
	•	엔진/전략은 “설정이 어떤 값인지 모른다”는 가정으로 설계

⸻

==========================================================

8. REAL PAPER 장시간 테스트 (PHASE16) 이슈 정리

==========================================================
	•	새 엔진 구조 검증을 위해:
	•	1시간, 12시간, 72시간 Paper 테스트를 계획
	•	duration_mode:
	•	market_time: 빠른 기능 테스트용 (실제 1h <-> 몇 분)
	•	wall_clock: 실제 시간 기준 soak test (실제 1h/12h 그대로)
	•	1시간 테스트:
	•	1h wall_clock 테스트 1회 성공
	•	엔진의 기본 안정성 및 신호/체결/Scorecard까지 정상
	•	12시간 테스트들:
	•	1차: Drawdown Guard (DD 17.55% > 10%)로 2분 59초 만에 종료
	•	2차: Exposure Guard로 11분대에 종료
	•	3차: Exposure Guard 지속 발동 → Entry가 막혀 사실상 멈춤 상태
	•	여러 번 YAML 튜닝(max_drawdown, max_positions, cooldown 조정 등)을 했지만:
	•	장시간 테스트를 통과할 수 있는 구조가 아님이 명확해짐
	•	교훈:
	•	문제는 설정값이 아니라 구조
	•	포지션 크기/노출도/Guard 상호작용이 잘못 설계된 상태
	•	이 상태에서 아무리 튜닝해도,
	•	실운영에서 “어느 날 갑자기 Guard만 난사되고 거래가 멈추는 시스템”이 될 위험

⸻

==========================================================

9. 지금 이 채팅이 끝나고, 새 채팅에서 이어갈 때 기준선

==========================================================
	•	이 스냅샷이 말해주는 현재 결론:
	1.	우리는 원래부터 앙상블 6전략 봇을 만들고 있었다.
	2.	이미 베이시안 튜닝+여러 전략까지 구현했지만,
구조가 꼬여서 전체를 다시 짜야 하는 상황이다.
	3.	그래서 지금은:
	•	Scalping 단일 전략 + 단일 엔진 + 깨끗한 Infra를 기준으로
	•	Backtest/Paper/Live를 통합하는 엔진/인프라 구조를 재구축 중이다.
	4.	PHASE16에서 REAL PAPER 1h/12h 테스트를 하면서:
	•	Drawdown/Exposure Guard가 구조적으로 문제를 드러냈고,
	•	YAML 튜닝만으로는 해결 불가능하다는 결론을 내렸다.
	5.	다음 단계(PHASE17)는:
	•	PositionSizing/Exposure/Risk 연동을 엔진 레벨에서 다시 설계
	•	이게 끝나야 다시 나머지 5전략 + 앙상블 + 베이시안 튜닝을 되살릴 수 있다.

⸻

==========================================================

10. 새 채팅에서 이 문맥을 불러오는 한 줄 매크로

==========================================================

새 채팅에서 이렇게 시작하면 된다:

“Future Alarm Bot / 6전략 앙상블 프로젝트의 Context Snapshot을 불러온다.
기존 v1 앙상블+베이시안 튜닝 구조가 꼬여서,
지금은 Scalp 단일 전략 기준으로 엔진/인프라를 다시 설계 중인 상태다.
PHASE16 REAL PAPER 테스트에서 Drawdown/Exposure Guard 구조적 문제가 드러났고,
PHASE17에서 PositionSizing/Exposure/Risk를 재설계해야 한다.
이 전체 문맥을 바탕으로 다음 작업을 설계/구현하라.”

⸻

==========================================================

END OF CONTEXT SNAPSHOT (ENSEMBLE 6전략 / 리빌드 버전)

==========================================================


좋아. 지금 네가 원하는 건 단 하나 — “Context Snapshot의 추가 섹션” 맞지?
즉, 이미 내가 만들어둔 SECTION 0~9 말고,
앙상블 전체 로드맵 + 우리가 프로젝트를 시작한 최초 기획부터 지금까지의 변천사 + 최종 상용 버전 TO-BE
이걸 추가 섹션으로 “더 뽑아내라”는 의미지?

그래서 아래는 Context Snapshot의 추가 섹션 1개를 완성 형태로 제공한다.
너가 원하는 앙상블 기반 최종 상용 시스템 전체 그림 +
지금 왜 스캘핑 엔진부터 다시 만드는지 +
최종 시스템 아키텍처 흐름까지 전부 넣었다.

⸻

==========================================================

11. 앙상블 기반 FINAL BOT SYSTEM — 전체 변천사 & TO-BE

==========================================================

이 섹션은 지금까지 모든 채팅을 기반으로
우리 프로젝트가 처음 무엇을 만들려고 했는지 → 왜 꼬였는지 → 왜 다시 백테스트/스캘핑부터 만드는지 → 최종 상용 시스템은 어떤 모습인지
전체 히스토리를 복원한 것이다.

이 섹션은 새 채팅으로 이관할 때 반드시 포함해야 하는 핵심 컨텍스트.

⸻

==========================================================

11-1. 프로젝트의 최초 목표 (처음 시작점)

==========================================================
	•	최종 목표:
단일 전략이 아니라,
여러 전략을 합쳐서 분산·보완·안정성을 극대화한 “앙상블 자율 트레이딩 시스템(Ensemble Trading System)” 구축.
	•	핵심 구성 전략 (초기 설계 6종)

1) Scalping (초단타)
2) Swing
3) Trend-following
4) Reversion
5) Breakout
6) Volume/Volatility model
─→ 마지막에 Ensemble Meta-Model로 통합


	•	토대 철학:
	•	전략은 독립적
	•	엔진은 공통
	•	거래소 Adapter는 공통
	•	리스크 관리(RiskManager)는 통합
	•	포트폴리오 매니저는 전체 계좌 기준의 Allocation
	•	Meta-Layer(앙상블)는 신호 조합과 가중치 최적화만 담당

⸻

==========================================================

11-2. 왜 ‘앙상블 → 베이시안 튜닝 → 백테스트부터 재구축’ 흐름이 되었는가

==========================================================

🔥 초기 단계에서 벌어진 문제들

1) 전략 6개가 전부 개별 구조로 따로 만들어짐
→ 공통 엔진 미정 → 모듈 간 중복 & 충돌 증가

2) 베이시안 튜닝(Bayesian Optimization) 도입,
그러나:
	•	백테스트 엔진 자체가 고정적이지 않음
	•	전략마다 데이터 구조가 다름
	•	리스크/포트폴리오/브로커가 일관성이 없음

3) 결국 Ensemble Meta-model이 먹히지 못함
	•	전략 A는 OK / B는 실패 / C는 데이터 불일치
	•	스코어/메트릭이 서로 비교 불가능

4) 백테스트 ↔ 페이퍼 ↔ 라이브 엔진이 서로 달랐음
	•	계산식 불일치
	•	브로커 계층 불일치
	•	리스크 모듈 중 일부만 적용됨

👉 우리 둘 다 느낀 결론:
“이 상태로는 앙상블을 아무리 튜닝해도 정확한 엔진 위에 서 있지 않는다.”

⸻

==========================================================

11-3. 그래서 지금 우리는 무엇을 하는가? (현재 단계)

==========================================================

✨ “엔진/브로커/리스크/포트폴리오 기반 전체 트레이딩 엔진 리빌딩 중”

현재 우리는:

✔ 백테스트 엔진부터 정확하게 다시 제작
	•	Candle → Signal → Entry → Risk → Exit
	•	PnL, DD, Winrate, Exposure
	•	1ms 단위 단일 루프
	•	모든 전략 유형이 공통 엔진을 사용하도록 통합

✔ 스캘핑 전략을 하나의 “레퍼런스 전략”으로 삼아 엔진을 검증
	•	스캘핑은 거래 빈도 높아 테스트하기 적합
	•	RiskGuard/Exposure/Drawdown 테스트에 가장 효과적
	•	흐름 제어, Redis 저장, Scorecard 생성 등 “엔진 전체 파이프라인”을 검증하는 데 최적

✔ Paper Engine → Real-time Duration Mode까지 안정화
	•	market_time (빠른 테스트)
	•	wall_clock (현실 세계와 동일한 시간 흐름)
	•	Long duration test (1h / 12h / 24h soak test)

✔ FlowGuardian 완성
	•	Exposure guard
	•	Drawdown guard
	•	Flash guard
	•	Slippage guard
	•	Cooldown guard
	•	Per-symbol allocation
	•	per-trade risk

→ 이게 완성되어야 다른 전략 5개를 얹을 수 있음.

⸻

==========================================================

11-4. 최종 상용 시스템(THE FINAL SYSTEM) — TO-BE 구조

==========================================================

이제 우리가 최종 목표로 삼는 시스템을 정리한다.

⸻

🔥 (1) 단일 엔진과 공통 파이프라인

Raw Market Data
        ↓
Data Collector (Realtime)
        ↓
Common Engine (Backtest/Paper/Live 동일)
        ↓
Signal Generator (각 전략 6종 독립)
        ↓
Risk Manager (공통)
        ↓
Portfolio Manager (공통)
        ↓
Broker Adapter (Upbit/Binance 공통 인터페이스)
        ↓
Execution Layer


⸻

🔥 (2) 앙상블 Meta-Layer (가장 중요한 최종 목표)

Strategy A → Weight_A
Strategy B → Weight_B
Strategy C → Weight_C
…
Strategy F → Weight_F

Ensemble Meta Model:
  - 신호 조합
  - 가중치 동적 업데이트
  - Bayesian / RL 기반 Weight Tuner
  - Portfolio 레벨 노출 최적화

👉 결과:
각 전략은 “독립된 원자 모듈”이지만
최종 트레이드는 앙상블이 결정.

⸻

🔥 (3) Trade Orchestration Layer (배포 버전)
	•	Redis: 실시간 상태/메트릭 저장
	•	Postgres: 거래/포지션 기록
	•	FlowGuardian: 안전 장치
	•	Monitoring CLI: 실시간 진단
	•	Slack/Telegram: 알림

⸻

🔥 (4) UI/UX (완성 단계)
	•	FastAPI 기반 로컬 서버
	•	Dashboard (PnL, DD, Position, Exposure, Strategy Metrics)
	•	Ensemble Weight 조절
	•	Backtest/Paper 결과 시각화
	•	알림 설정
	•	Config Editor

⸻

✔ (5) Developer Experience (DX)
	•	Windsurf 자동 생성
	•	PHASE 문서 자동화
	•	Git 커밋/회귀 테스트 자동
	•	DIFF 기반 코드 관리
	•	구간별 테스트 스위트 구성
	•	PHASE별 문서화 시스템

⸻

==========================================================

11-5. 전체 타임라인 — 지금까지와 앞으로

==========================================================

과거
	1.	전략 6개 구현
	2.	앙상블 시도
	3.	베이시안 튜닝 도입
	4.	엔진 불일치/중복 구조로 인해 전체 붕괴
	5.	코드를 다시 “제로에서 엔진 중심으로” 재구성하기로 결정
	6.	스캘핑 전략부터 기준선 엔진 검증 시작
	7.	Paper Engine 안정화 (market_time)
	8.	Duration Mode(wall_clock) 구현 → 장시간 테스트 시작
	9.	FlowGuardian 고도화
	10.	Redis/Psql 기반 실시간 저장 기반 완성

⸻

현재

PHASE16
	•	Paper Engine SOAK Test (1h/12h/24h)
	•	Exposure/Drawdown 문제 디버깅
	•	Portfolio Manager 크기/노출 제어 고도화
	•	Risk Manager position sizing 정교화 필요
	•	엔진 안정성 확립 중

⸻

미래 (최종 로드맵)

PHASE17: Position sizing 개선
PHASE18: Strategy abstraction 6종 재도입
PHASE19: Ensemble Meta-model 복구
PHASE20: Bayesian/RL 기반 Weight Tuning
PHASE21: Live Runner Pre-flight
PHASE22: 실거래 모드 안전 테스트
PHASE23: UI/UX 구축
PHASE24: 배포 패키징
PHASE25: 상용 버전 (Future Alarm Bot Ensemble Edition)


⸻

==========================================================

11-6. 결론 — 왜 이 섹션이 중요한가

==========================================================

새 채팅에서 이 정보를 읽으면 다음을 즉시 이해할 수 있다:
	•	우리는 단순 스캘핑 엔진을 만드는 게 아니다.
	•	최종 목표는 6전략 + 앙상블 + 메타모델 기반 상용 트레이딩 시스템.
	•	그런데 기반 엔진이 흔들렸기에
정확한 백테스트/페이퍼/라이브 공통 엔진부터 다시 쌓는 중.
	•	스캘핑은 그 “기준선 전략” 역할.
	•	Paper Engine 안정화가 끝나면
다른 전략을 차례로 코드화하고
마지막에 앙상블 복구한다.