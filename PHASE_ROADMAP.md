?� Future Alarm Bot ??黖𨰰� ?�鹻 貒��篧嵸? ?�眼 諢嶅�諤?

諈拗� ??鴗??䇹烄
?嶅𡆀???䇹�(backtest/paper/live 窸蛙鹻)??篣圉�??
?韒� 謔科擪??窵�謔?+ Guard + ?秒䂻?渠收??+ 諈刺�?圉�篧嵸? ?秒𥚃??
?木� ?渥鹻 穈�?伕� ?�鹻篣??軤�賳??賈�?渠𨫣 ?𨰰擪?鎿�?

0. ?�眼 窱科※ 穈𨰰�
?㺿 諢嶅�諤???黺?

INFRA / ENGINE ?��??(鴔�篣?~ PHASE20 ?��)

?䇹�, ?科????秒䂻?渠收?? Budget, Guard, ?域𦚯?? ?嵸擪???貲�??

?𨰰�?菊�吖𦚯 ?��???嶅�穈�鴔�鴔� ?㗻� 窱科※?吖� 鴔𡢾�

STRATEGY / PERFORMANCE (PHASE20~PHASE30)

?到𦉘 ?�嬍(?木�?? ???禺剳 ?�嬍 ???軤�賳?

諻桶�?欠䂻/?䁯𦚯??篣圉�?潺� ?寨�繚PnL繚MDD 窶�鴞?

PRODUCTION / OPERATIONS (PHASE30~PHASE40)

Live 窱科※, ?曰�鮈??國盒, ?伊� ?�?? 諈刺�?圉�, ?𣕑�, Runbook

?嶅�穈� ??貐湊� ?�𩸭???嵸�穈�???𨰰擪?鎿�?

1. 窸蛭� 篞𨰰� (諈刺� Phase??窸蛭� ?�鹻)

?渥�賱�???渠𣶸 Phase??諡渥※穇??�� 5穈?篞𨰰� 篧𥯆� 穈�𠹻.

??鴔�� 魽國探(Entry Criteria)

?𨰰𦚯 Phase諝??𨰰�?渠� ?䁪�鴔�?噃? ?㻂�

?渥� Phase?韠� 黖𨰰�??諡渥�???��?䁯𩸭???䁪�鴔� 諈��

???渥� 魽國探(Exit / Acceptance Criteria)

??Phase諝??𨰰�諴𢞖�噃𦉘窸?諤𥑬�?月庖 諻䁪�??黺拖§?渥焩 ?䁪� 窱科眼?�𥘵 魽國探

魽國探 諤嵸§ 諈魁�諰??木� Phase諢?諈??䁯𩸭穈?

???域�諡?Deliverables)

儠竾� / ?木� / 諡賄� / ?嵸擪??窶國頃 ?瑅收

黖𨰰� 1穈??渥� MD 諡賄�諢??刷?

??Out-of-Scope(?渠� Phase?韠� ?潺??????䁪� 窶?

?𨰰�穈�� ?㻂𡠺 ?渥� ?�� 貒𣕑朽 窶�㨩?吖� 諯賈收 麆刺𡆀

?? ??Phase???寨� ?嶅� ???? ?�嬍 黺𥯆? ??????

??諡賄� 諻𨰰� ???韠�

Acceptance 魽國探 諤嵸§ 諈魁�諰?
???嶅�篞??渥� 諈拘� MD + ?韠𥘵/?湊盒 窸��???𡢾�
???湊盒 ?��諤?Phase ?�� ?𥔱鴡

2. ?�� ?�� 篣域?: PHASE17 ?科�??

鴔�篣�? ?渠? PHASE0~16 + D?刷�諝?穇域�??
PHASE17 = Portfolio Budget / Position Sizing ?貲�???刷�???� ?�𠹻窸?貐渠庖 ?嶅𠹻.

篞賈�??諢嶅�諤蛙? **?𨰰?篣??渣�??*諝?鴗𡢾𡠺?潺� ?㻂�?𥻗�.

3. ?�� 諢嶅�諤?(PHASE17 ?渣�)
?妝 PHASE17 ??Portfolio Budget & Position Infra ?��????**?�� (CONDITIONAL PASS, Production Ready)**

諈拖�

Budget SSOT 窱科※ ?瑅汗

PortfolioManager / PositionSizer / Engine 穈??域𦚯???𣕑�???��??

REAL PAPER 12H 篣域??潺�??Budget/Guard穈� ?㻂� ?軤�?䁪�鴔� 窶�鴞?

鴔�� 魽國探

?䇹� ?到𦉘 窱科※ (backtest/paper/live 窸蛙鹻) ?渠? 魽渥�

Redis/Postgres/FlowGuardian 篣圉雩 窱科※ ?軤�

篣圉雩 ?木�???�嬍?潺� Paper 諈刺� 黖𨰰� 15賱?1?𨁈� ?欠� 窶踫� ?��

**?�� ?�� (2025-11-19)**:
- V6.1 篣域? 12H REAL PAPER ?嵸擪???虛頃
- Budget Cap ?㻂� ?炣� (111???�鹻 ?㻂𥘵)
- Portfolio BLOCK ??31.1% (諈拗� <30% 篞潰�)
- ERROR/CRITICAL 0穇?
- 諡賄�: docs/PHASE17/PHASE17_V6_1_REAL_PAPER_12H_ACCEPTANCE_REPORT.md

鴥潰� ?𡢾�

PortfolioManager

_get_used_budget(), get_available_budget()

?科????㻂�?�收 ???蛙𦉘 (position_value, status='OPEN' ??

PositionSizer

謔科擪??篣圉� ?科𦚯鴔?(RPT, SL, ?��謔科? 窸𧙖𨸹)

available_budget ?𣕑𦉘諯貲� 篣圉� Budget Cap

Cap ?�鹻 ??諢𨁈�

Engine

?科????吖� / 黺𥯆? / Scaling ??Budget ?𣕑�???澎???

Budget Cap 諻䁯� ???木� 篧到?鴔� ?㗻�諢?穈??禹�??諻拖� ?瑅收

?嵸擪???貲�??

?到� ?嵸擪??(Sizer / Portfolio / Budget 窸��)

?蛭襔 ?嵸擪???欠�謔踫䂻 (Budget ?嶅�謔科𠈔)

REAL PAPER 1H & 12H ?欠� ?嵸擪??

?渥�(?��) 魽國探 ??諻䁪�???虛頃?渥焩 ?木� Phase諢?鴔�� 穈�??

Budget 篣圉𥁒 Acceptance

?蛭襔 ?嵸擪?賄�???�� ?嶅�謔科𠈔 ?�? ?虛頃:

Budget ??Entry ??Cap ?��

Budget 黕�頃 Entry ??Cap ?�鹻

Budget ?�� ?嵸� ??Entry Block

REAL PAPER 12H Acceptance (?�� 諤𥑬� 篞資掠)

諈刺�: REAL PAPER

Config: real_paper_12h_v6_1_phase17.yml

黖𨰰� 12?𨁈� ?域� ?欠� (鴗𡟯� ?科�???秒𥚃??黕?12H ?渥�)

篣域?:

Entry SUCCESS ??100

Budget Cap Applied ??1??(?木�諢??禺剳 貒?

Portfolio Budget BLOCK 赬�銁 < 30%

ERROR/CRITICAL 0穇?

?䇹� 赬��??鮈�� 0??

諡賄� / 謔秒𡢢??

PHASE17_PORTFOLIO_BUDGET_FINAL_REPORT.md

V4/V5/V6/V6.1/V6.1 12H 赬��

諡賄� ???韠𥘵 ???湊盒 ??窶�鴞?窶國頃

?憕HASE17 ?貲�??Acceptance: PASS/FAIL??諈�萼

Out-of-Scope

?寨� ?嶅� / ?�嬍 ?𣕑𦉘諯貲� 黖𨰰�??

?��???�嬍 黺𥯆?

?軤�賳?窱秒�

Live 諈刺�

?妝 PHASE18 ??Strategy Correctness & Baseline Performance (?到𦉘 ?木�???�嬍)

諈拖�

?𨰰�鴔�𦚯 ??諤祢?鴔�𠹻?吖�?????刷� ???瞘???
?到𦉘 ?木�???�嬍???潺收?�尐諢?諤韠𦚯 ?瞘� ?軤�?䁪�鴔� + 篣圉雩 ?梵𥁒??窵𨰰乾?�鴔� ?㻂𥘵

鴔�� 魽國探

PHASE17 Acceptance ?虛頃 (Budget/Portfolio ?��)

REAL PAPER 12H 窶國頃 謔秒𡢢???��

鴥潰� ?𡢾�

?�嬍 諢𨰰� 窶�鴞?

鴔�� 魽國探 / 麮?� 魽國探 / SL/TP / Trailing / Re-entry 諢𨰰�??諡賄�??

儠竾�?� 諡賄�???渥鹻???潰�?䁪�鴔� ?韀?

諻桶�?欠䂻 ?貲�???瑅收

?軤𦉘 ?䇹�?潺� backtest/paper/live 諈刺� ?軤�

諻桶�?欠䂻???域𦚯??貒䇹� ?㻂� (?? 黖𨁈滂 6~12穈𨰰� BTC/ETH/KRW ??

篣圉雩 ?梵𥁒 鼽∫�

黖𨰰� 3穈?窱禹�?韠� backtest ?欠�:

?�䎺?? ?䁪嚿?? 諻㻂擪??赬�啹??窱禹�

鼽∫�:

Win Rate, Expectancy, PnL, MDD, Trade ?? Avg holding time ??

?渥�(?��) 魽國探

諻桶�?欠䂻 謔秒𡢢??黖𨰰� 3穈?

穈?謔秒𡢢?賄�:

篣國�, ?禺頃, ?𣕑𦉘諯貲�, 窶國頃 鴔�??

?伙𡆀??/ 赬��??窱禹� 儠竾�??

?𨰰�???潺收 窶�鴞吲�??��

諈�停??諤韒� ???䁪� 貒�溢(?? SL ??穇賈收穇圉�, TP穈� ?嵸�???䁯?)??諈刺� ?𨁈掠

?�嬍 ?月� 諡賄�?� 儠竾�穈� ?嶅� 諈??嵸�貐湊� ?月斥 ?�埯?� ?𨁈掠

REAL PAPER ?刷萼 窶�鴞?

REAL PAPER 諈刺� 4~6?𨁈� ?嵸擪??1???渥�

諻桶�?欠䂻 ?桶棅窸??�? ?月斥 ?渥� ?参� ?�� 窶?

Out-of-Scope

Bayesian ?嶅�, Grid Search ??貐資痔 Optimization

?軤�賳?/ ?木�??

?木� 窸�� Live

?妝 PHASE19 ??Ensemble System Foundation ??**?�� (Production Ready)**

**?𩤃� Note**: ?韒� 窸��?� "Risk & Guard ?嶅�"?渥�?潺�, ?木�諢嶅� Ensemble ?貲�?潺? ?域� 窱科�??

諈拖�

Strategy Registry, Score Engine, Ensemble Aggregator 窱秒�

?禺剳 ?�嬍???𡥄猹諝?麮湊�?�尐諢??蛭襔?䁪� Ensemble ?貲�??窱科�

?䇹� ?�疏?韠� Ensemble ON/OFF 諈刺� 鴔�??

鴔�� 魽國探

PHASE17 ?�� (Portfolio/Budget ?��??

篣圉雩 ?�嬍?木𦚯 BaseStrategy ?貲�?䁯𦚯??鴗�??

**?�� ?�� (2025-11-20)**:

**PHASE19-1: Strategy Registry** ??
- BaseStrategy ?貲�?䁯𦚯???㻂�
- StrategyMetadata with Ensemble fields (optimal_regime, factor_weights, base_weight)
- StrategyRegistry ?韒� ?木� 篣圉𥁒
- 7穈??�嬍 ?梵� ?�� (scalping, breakout, reversion, trend, swing, swing_bb, daytrade)
- 諡賄�: docs/PHASE19/PHASE19-1_COMPLETE_REPORT.md

**PHASE19-2: Score Engine & Factors** ??
- Factor Calculator (momentum, volatility, volume, trend_strength, overbought_oversold, breakout_probability)
- ScoreEngine with regime multipliers (optimal=1.2x, worst=0.3x, neutral=1.0x)
- ?�嬍貐?Factor Weights & Base Weights ?㻂�
- ?到� ?嵸擪??PASS
- 諡賄�: docs/PHASE19/PHASE19-2_COMPLETE_REPORT.md

**PHASE19-3: Ensemble Aggregator & Engine Integration** ??
- 3-Tier Aggregation (High-Confidence, Consensus, Skip)
- StrategyDecision & EnsembleDecision dataclasses
- EnsembleAggregator.decide() 窱秒�
- execution/engine.py??Full Integration
- ?到� ?嵸擪?? 11/13 PASS (Aggregator 7/7, ScoreEngine 篣圉雩 4/4)
- Ensemble OFF 諈刺� ?㴒? ?嵸擪??PASS
- Ensemble ON 諈刺� 黕�萼???嵸擪??PASS
- 諡賄�: docs/PHASE19/PHASE19-3_ENSEMBLE_AGGREGATOR_DESIGN.md, PHASE19-3_COMPLETE_REPORT.md

鴥潰� ?𡢾�

StrategyRegistry

?�嬍 ?韒� ?木� 諻??梵�

諰籝??域𦚯??儥韠㘚

?�嬍 ?賄擪?渥擪 ?吖� API

ScoreEngine

Factor 窸�� 諻??𨴴�??

?�嬍貐?穈�鴗𡢾� 篣圉� ?韠� 窸��

Regime multiplier ?�鹻

EnsembleAggregator

Tier 1: High-Confidence (score >= 0.8, 黺拘� 麮䁪收)

Tier 2: Consensus (0.5 <= score < 0.8, 2+ votes)

Tier 3: Skip

Engine Integration

Ensemble ON/OFF 諈刺� 賱�萼

?秒㭻 ?到�: _convert_ensemble_decision_to_signal()

Config 篣圉� threshold ?木�

?渥�(?��) 魽國探

???到� ?嵸擪?? Registry, ScoreEngine, Aggregator 諈刺� PASS

??Ensemble OFF 諈刺�: 篣域● 篣圉𥁒 ?㴒? ?��

??Ensemble ON 諈刺�: 黕�萼???㻂� ?炣�

??Config ?蛭襔: ensemble ?寢� 黺𥯆? 諻??䇹� ?圉�

??諡賄�?? 穈??嶅� PHASE貐?Complete Report

Out-of-Scope

Regime Classifier (PHASE19-4 ?��)

Multi-symbol ?㻂𤟠

?木� Ensemble ?梵𥁒 ?嶅� (PHASE20 ?渣�)

Known Issues & Next Steps

Regime?� ?�� None (placeholder) ??PHASE19-4?韠� Regime Classifier 窱秒� ?��

Ensemble ON 諈刺� ?木� Paper ?嵸擪???�� (?��??黕�萼?竾� 窶�鴞?

?�嬍貐?Config ?軤� 貐𣖙襔 諢𨰰� 穈𨰰� 穈�??

 PHASE20 ??Ensemble Integration & Paper Validation 

**PHASE20-1: Ensemble ON Paper Smoke Test (1h, Single Symbol) ?????��**

諈拖�

Ensemble 諈刺�(EnsembleAggregator + ScoreEngine + StrategyRegistry) ?蛭襔 窶�鴞?

1?𨁈� wall-clock Paper ?嵸擪?賈� Ensemble ?䁯�窶域� ?㻂� ?軤� ?㻂𥘵

篣域● ?貲�??FlowGuardian, RiskManager, PortfolioManager, Budget SSOT) ?��???禹?鴞?

鴔�� 魽國探

PHASE19-3+ ?��: Ensemble ?蛭襔 + ?䇹� Hook ?��

PHASE17 篣域? Portfolio/Risk ?貲�???��

鴥潰� ?𡢾�

 Config 鴗�赬? `configs/paper/ensemble_paper_smoke.yml` (1h, 7 strategies, BTCUSDT, 5m)

 Clean-State 黕�萼?? Postgres/Redis ?瑅收 (12,678 trades, 143,437 signals ??�)

 ?到� ?嵸擪?? Aggregator/ScoreEngine/Registry ?嵸擪??16/20 PASS (?蛙𡠺 諢𨰰� 諈刺� PASS)

 1?𨁈� Paper ?欠�: 5,060 儥竾㨩 麮䁪收, 31 穇圉� 麮湊盒, ?㻂� 鮈��

 窶國頃 窶�鴞? 31 trades (LONG 13, SHORT 18), Total PnL -$107.23, Drawdown 1.07%

 諡賄�?? PHASE20-1_ENSEMBLE_PAPER_SMOKE_REPORT.md ?𡢾�

 ROADMAP ?�㫲?渣䂻: ????版

 Git 儢月�: PHASE20-1 ?��

?渥� 魽國探 (諈刺� 黺拖§)

 Ensemble 窵�??pytest PASS (Aggregator/ScoreEngine/Registry)

 1?𨁈� wall-clock Paper ?㻂� ?欠� (5,060 儥竾㨩)

 FlowGuardian READY ?虛頃 ???䇹� 諴刮� 鴔��

 黖𨰰� 3穇??渥� 穇圉� 麮湊盒 (?木�: 31穇?

 Ensemble Tier1/Tier2 窶域� 黖𨰰� 1???渥� 諻𨰰�

 儦䁪�???韒剳 ?�� (Graceful Shutdown ?��)

 謔秒𡢢??+ ROADMAP + git commit ?��

**?�� ?�� (2025-11-20)**:
- Run ID: `20251120_135912_0gja`
- Duration: 1h 1m 47s (wall-clock)
- Total Trades: 31 (LONG 13, SHORT 18)
- Total PnL: -$107.23 (?㻂� ?韠𠹻, ?貲�??窶�鴞?諈拗� ?科�)
- Drawdown: 1.07% (?��??
- 諡賄�: docs/PHASE20/PHASE20-1_ENSEMBLE_PAPER_SMOKE_REPORT.md

**PHASE20-2: Extended Infrastructure Validation (4h+ runtime) ??**

諈拖�

Ensemble ON 諈刺�諢?4?𨁈� ?渥� ?域� Paper ?嵸擪??(?貲�???��??窶�鴞?

?到𦉘 ?禺頃 (BTCUSDT) 篣域?

鴥潰� 窶國頃

- Runtime: 4+ hours continuous operation
- Total Trades: 44 (LONG 19, SHORT 25)
- Total PnL: -$311.18
- Infrastructure:  All systems stable
- Strategy Distribution: Scalping-dominated (~95% signals)

?�� ?�� (2025-11-20)

- Infrastructure Validation:  PASS
- 諡賄�: docs/PHASE20/PHASE20-1_INFRASTRUCTURE_VALIDATION_FINAL.md

---

## ?�𡡒 ?�嬍 ?�陷窱?(SSOT)

**諈拖�**


- ???��?𠺝䂻?韠� ?科鹻?䁪� **?�嬍?木� ?�眼 ?�陷 ?�(Strategy Pool)** ????窸喬� ?瑅收?嶅𠹻.
- "?�� 窱秒�?䁯𩸭 ?�� ?�嬍"窸?"?伕� ?國筋/黺𥯆? ?�� ?�嬍"??窱禺�?瞘�,
- PHASE22-0?韠� ??Pool??篣域??潺� **Ensemble v1???木𩸭穈?7~8穈??�嬍**???𥔱�?嶅𠹻.

**窱科※**

- **Implemented Strategies** (?渠? ?䇹�???蛭襔???�嬍)
- **Candidate / R&D Strategies** (?伕� 窱秒�/窶�鴞??�� ?�嬍)
- **Ensemble v1 Inclusion Flag** (IN / OUT / RESERVE)

| ID                | Name                     | Type                    | Timeframe Class | Status      | Ensemble v1 |
|-------------------|--------------------------|-------------------------|-----------------|-------------|-------------|
| scalping          | Scalping                 | Momentum/Scalp          | ACTIVE (3m)     | IMPLEMENTED | **IN**      |
| breakout          | Breakout                 | Volatility              | LOW_FREQ (15m)  | IMPLEMENTED | **IN**      |
| reversion         | Reversion                | Mean Reversion          | LOW_FREQ (5m)   | IMPLEMENTED | **IN**      |
| trend             | Trend                    | Trend Follow            | LOW_FREQ (1h)   | IMPLEMENTED | **IN**      |
| swing_bb          | Swing BB                 | Mean Reversion          | LOW_FREQ (5m)   | IMPLEMENTED | RESERVE     |
| swing             | Swing                    | Swing Trend             | LOW_FREQ (1h)   | IMPLEMENTED | RESERVE     |
| daytrade          | Daytrade                 | Intraday Trend          | LOW_FREQ (15m)  | IMPLEMENTED | RESERVE     |
| obi_momentum      | OBI Momentum             | Orderbook Imbalance     | ACTIVE (1m)     | CANDIDATE   | **IN**      |
| cvd_reversal      | CVD Reversal             | Volume Delta            | LOW_FREQ (5m)   | CANDIDATE   | **IN**      |
| multi_tf_momentum | Multi-TF Momentum        | Cross-Timeframe         | ACTIVE (1m/5m)  | CANDIDATE   | **IN**      |
| relative_strength | Relative Strength        | Cross-Asset RS          | LOW_FREQ (15m)  | CANDIDATE   | **IN**      |
| R&D_1             | Orderbook Micro-Reversion| Orderbook Imbalance     | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_2             | Volatility Breakout v2   | ATR + Session           | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_3             | Regime Adaptive Meta     | Regime-based Meta       | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_4             | Funding Rate Reversion   | Funding Rate Arbitrage  | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_5             | Volatility Skew Arb      | Vol Smile/Skew          | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_6             | Session Bias Intraday    | Time-of-Day Bias        | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_7             | Market-Neutral Pair      | Pair/Spread Trading     | (T.B.D.)        | CANDIDATE   | LATER       |

**Ensemble v1 賱�� 篣域?** (PHASE22-0 ?��, 2025-11-21):
- **IN (8穈?**: Ensemble v1 Core ?�嬍 (4 IMPLEMENTED + 4 CANDIDATE)
  - **IMPLEMENTED (4穈?**: Scalping, Breakout, Reversion, Trend
  - **CANDIDATE (4穈?**: OBI-Momentum, CVD Reversal, Multi-TF Momentum, Relative Strength (?曰�諤? 窱秒�?� PHASE23+)
- **RESERVE (3穈?**: ?貲�??PASS, PHASE22-2 Extended Validation ??黺𥯆? 窸𧙖𨸹
- **LATER (7穈?**: ?伕� ?國筋/窱秒� ?�� ?�嬍

**?𥻗� Ensemble v1 ?�嬍 (4穈? 穈嶅�**:
- **OBI-Momentum**: Orderbook Imbalance 篣圉� 1m 黕�𡆀?� 諈刺�?�
- **CVD Reversal**: Cumulative Volume Delta 篣圉� 5m 諻䁯� 穈韠?
- **Multi-TF Momentum**: 1m/5m Cross-Timeframe 諈刺�?� ?㻂𥘵
- **Relative Strength**: Cross-Asset Relative Strength Index (15m)

**R&D ?�嬍 (7穈? 穈嶅�**:
- **R&D_1 (Orderbook Micro-Reversion)**: ?資?麆?賱��??篣圉� 黕�𡆀?� ?㕓� ?㴒?
- **R&D_2 (Volatility Breakout v2)**: ATR + Session 篣圉� 貐�?軤� 賳𣕑�?渣�?��
- **R&D_3 (Regime Adaptive Meta)**: ?𨰰𤟠 ?��???圉𦉘 ?�嬍 on/off 諻?weight 魽域�
- **R&D_4 (Funding Rate Reversion)**: ?�?拘� 窸潰�/??� ?𨰰鹻 麆到㷫穇圉�
- **R&D_5 (Volatility Skew Arbitrage)**: 貐�?軤� ?月�???欠� 篣圉� ?�嬍
- **R&D_6 (Session Bias Intraday)**: Asia/EU/US ?賄�貐??貲棅 ?𨰰鹻
- **R&D_7 (Market-Neutral Pair)**: ?䁯𩸭/?欠�?�� ?賈�?渠𨫣

 CANDIDATE ?�嬍?� ?曰�/?�𦚯?䇹𩸭 ?䁯??渠庚, ?木� 窱秒�/窶�鴞吖? PHASE23 ?渣� 鴔��

**麆賄※ 諡賄�**

- PHASE21 窶�鴞?窶國頃: `docs/PHASE21/PHASE21-1C_ACTUAL_EXECUTION_REPORT.md`
- PHASE22-0 Strategy Pool 賱��: `docs/PHASE22/PHASE22-0_STRATEGY_POOL.md`

---

 PHASE21 ??Single Strategy Infrastructure & Validation 

**?��**:  COMPLETE (PHASE21-1A/1B/1C 諈刺� ?��, 2025-11-21)

**諈拖�**

7穈??�嬍 穈��???�??**?到𦉘 ?�嬍 ?貲�???�?��?��/FlowGuardian/Config-SSOT**穈� ?㻂� ?軤�?䁪�鴔� 窶�鴞𠺝�窸? ACTIVE/LOW_FREQ ?寢�??窱禺�?䁯𤩐 ?渣� Ensemble/Extended Validation??篣圉�??諤�礆

 ?𩤃� **??PHASE??黕��**:
- **?�嬍 ?梵𥁒 ?嶅�/?𧙖�???��??*, ?到𦉘 ?�嬍???䇹�/?潺�/穈�???秒䂻?渠收??窱科※ ?��??**?��?�尐諢??軤�?䁪�鴔� 窶�鴞?*?䁪� 窶?
- ?�嬍貐??梵𥁒 赬�� 諻?Ensemble ?�陷 ?𥔱�?� **PHASE22-0**?韠� ?属�

**貒䇹� (黖𨰰� ?㻂�)**

-  ?�?��?��/Feed collector 貒�溢 ?噃� 諻??䁯� (3m/5m/1h WebSocket ?㻂� ?䁯� ?㻂𥘵)
-  `run_paper.py`???�嬍/?禺頃/?�?��?��/Duration ?䁪�儠竾𨫣 ?𨁈掠 諻?**Config 篣圉� SSOT 窱科※ ?瑅汗**
-  Scalping/Reversion/Trend ?到𦉘 ?�嬍 PAPER ?欠�???蛭� **?貲�???�疏 窶�鴞?*
-  ACTIVE vs LOW_FREQ ?�嬍 賱�� (?貲�??篣域?, ?梵𥁒/?䁯㷫諝??嶅�?� 貒䇹� 諻?

**Out-of-scope (?木� PHASE諢??湊?)**

- ?�嬍貐?PnL/Win-rate/Max DD諝?篣域??潺� ??**Ensemble v1 ?�嬍窱??𥔱�** ??**PHASE22-0**
- Multi-strategy/Ensemble ?欠� 諻??嶅� ??**PHASE22-1**
- 12~24?𨁈� ?伉萼 PAPER ?欠�???蛭� ?梵𥁒/?吖●??窶�鴞???**PHASE22-2**
- Flash Guard/勴刺𠹻???禺收?潰? ?𣕑𦉘諯貲� ?嶅� (?�嬍 ?梵𥁒 篣域?) ??**PHASE22-3**

**鴔�� 魽國探**

?到𦉘 ?�嬍 ?木�?𡢾𦚯 ?�� + 謔科擪???域𦚯???貲�???瑅收??

**諡賄�**: docs/PHASE21/PHASE21-1A_REPORT.md, PHASE21-1B_FEED_FIX_REPORT.md, PHASE21-1C_ACTUAL_EXECUTION_REPORT.md

---

## ?働 黖𨰰� TO-BE ?��?𣽁� (10-Layer Structure)

### 1) Core Engine Layer
- **?到𦉘 ?䇹� ?韠�**: Backtest / Paper / Live 諈刺� 穈軤? ?䇹� 儠竾�
- **Do-not-touch 儠䇹𩸭**: engine.run(), position/state 諟賄�, event 諴刮�, duration 麮䁪收
- **??�**: 儥竾㨩/???欠䂻謔??𣕑�, ?�嬍 ?賄�, Risk/Portfolio/FlowGuardian 麮渣�, Execution Adapter ?��

### 2) Strategy & Ensemble Layer
- **5穈??�嬍 ?刺?謔?*: Trend-follow, Volatility Breakout, Mean Reversion, Pullback-in-Trend, Scalping
- **?刺?謔禺鰟 ?�???�嬍 1~2穈?*諤??木�???𥔱�
- **Ensemble Score 窱科※**: 窸蛭� ?𨁈溢?�� (S_LONG, S_SHORT, S_RISK, S_QUALITY), ?軤� 穈�鴗𡢾�

### 3) Risk / Portfolio / FlowGuardian Layer
- **RiskManager**: per-trade risk, ?��謔科? ?��, Max DD, ?潰𦉘 ?韠𠹻 ?𨂃�
- **PortfolioManager**: ?禺頃貐??�嬍貐?諻圉�, PnL/Equity SSOT
- **FlowGuardian**: READY 麮渣�, 勴刺𠹻?? Flash Guard, API ?�� ?㻂𥘵

### 4) Data & Exchange Layer
- **Data Layer**: WebSocketCollector, RestCollector, Multi-TF Preload
- **Exchange Adapter**: PaperExchange, Binance/Upbit Adapter (Market, Limit, TP/SL, OCO)

### 5) Tuning & Research Cluster Layer
- **3?刷� ?嵸𦚯?�𦉘??*: Random ??Bayesian ??Local Grid
- **鴗𡢾� DB**: Postgres + TimescaleDB (runs, strategy_params, results, metrics)
- **Worker ?��?賄擪**: 諻桶�?欠䂻 job 貐炣䁥 ?欠�

### 6) Multi-Symbol & Execution Layer
- **Universe Provider**: TopN/?�� 篣圉� ?禺頃 謔科擪???吖�
- **Multi-Symbol Engine**: ?禺頃貐?coroutine, per-symbol risk/portfolio
- **Execution Router**: ?禺頃/?�嬍/諻拗棅 篣圉� 鴥潺爰 ?潰黱??

### 7) Infra & Performance Layer
- **?梵𥁒 諈拗�**: Top50 ?禺頃, 1m/5m/15m TF ?軤� 麮䁪收
- **黖𨰰�??*: 赬��篣?儠竾ㄗ?? ?賈�儤�?渣� 儥韠㘚, 諢𨁈溢 ?嶅�, GC 黖𨰰�??
- **諢嶅� ?嵸擪??*: ?到𦉘 ?禺頃 ??Top10 ??Top50 ?㻂𤟠

### 8) Monitoring / Observability & Alerting
- **Metrics**: PnL, Equity, Win-rate, Sharpe, Max DD, ?�嬍貐??禺頃貐??梵𥁒
- **Dashboards**: Prometheus + Grafana, Core KPI 10鮈?
- **Alerting**: Telegram/Slack (DD, WS ?韒剳, 鴥潺爰 ?欠𤔅?? trade 0穇???

### 9) UI/UX Layer ?�
- **Web Dashboard**: FastAPI + React/Vue
- **?蛙𡠺 ?竾庖**: ?木�穈?諈刺�?圉�, ?�嬍/?軤�賳??刺�, 謔科擪???秒䂻?渠收?? 諻桶�?欠䂻 賰域𩸭, 諢𨁈溢/?渠略??
- **Control 篣圉𥁒**: Paper/Live ?��, ?�嬍 on/off, preset ?𡥄�, safe restart

### 10) Ops & Deployment Layer
- **?欠� 窱科※**: run_backtest, run_paper, run_live
- **?渥�**: systemd / Docker / K8s
- **諻堅𡢢/諢月停**: git tag, config 貒�� 窵�謔? DB/Redis backup

---

?妝 **PHASE22 RESET** ??Strategy Set Reconstruction & 5-Family Framework ?� **IN PROGRESS**

**?��**: ?� **IN PROGRESS** (2025-11-22)

**諻國祭**
- PHASE22-1/2 鴗炣𡆀 (篣域● 7穈??�嬍 鴗?scalping ?𨰰烵 correctness/?嶅�/諻桶�?欠䂻 ?��)
- ?�嬍 ?�� ?�𦚯 ?䇹� ?嵸擪?賈� ?属� ???䁪? 賱�魽?
- PHASE22-0賱�???科�??(?�嬍 ?貲䂻 ?科�??

**諈拖�**
- 5穈??�嬍 ?刺?謔?篣圉� Ensemble v2 ?曰�/窱秒�
- ?到𦉘 ?禺頃 篣域? 12~24h PAPER諢??吖●??窶�鴞?

**Sub-phases**
- **22-0: ??Strategy Set Reconstruction (COMPLETE - 2025-11-22)**
  - ?渠� ?禹筋魽堅�: core/scalping_v3.py (KEEP), deprecated/ (6穈??�嬍), research/ (?𥻗�)
  - 5穈??刺?謔??㻂�: HF Momentum, Volatility Breakout, Mean Reversion, Trend Following, Volume-Based
  - ?域�諡? `docs/PHASE22/PHASE22-0_STRATEGY_POOL.md`
- **22-1: ??Strategy Implementation & Validation (COMPLETE - 2025-11-22)**
  - 4穈??𥻗� ?�嬍 窱秒�: volatility_breakout_v2, mean_reversion_v2, trend_follow_v2, volume_based_v2
  - BaseStrategy ?貲�?䁯𦚯???�祭 鴗�??(metadata + compute_signal)
  - Unit Test 17/17 PASS (100% ?梓陬諝?
  - ?域�諡? `docs/PHASE22/PHASE22-1_STRATEGY_DESIGN.md`, `docs/PHASE22/PHASE22-1_COMPLETE_REPORT.md`
  - 儠竾�: `strategies/research/*.py` (4穈??�嬍 + __init__.py)
  - ?嵸擪?? `tests/test_phase22_1_new_strategies.py`
- **22-2: ??Extended Validation (Quick Smoke PASS, Main Run FAIL - 2025-11-23 10:00)**
  - Ensemble v2 ?伉萼 ?��??窶�鴞?(12~24H Paper, 5穈??�嬍 ?蛭襔)
  - ?�嬍貐??𡥄猹 諻𨰰� 赬�� ?㻂𥘵
  - PnL/?梵𥁒 篣域� 賱��
  - ?域�諡? `docs/PHASE22/PHASE22-2_EXTENDED_VALIDATION_DESIGN.md`, `PHASE22-2_EXECUTION_GUIDE.md`, `PHASE22-2_EXTENDED_VALIDATION_REPORT.md`
  - Config: `configs/paper/phase22_2_ensemble_quick.yml`, `phase22_2_ensemble_12h.yml`
  - Script: `scripts/run_phase22_2_ensemble.py`
  - **Quick Smoke Test (30賱?**: Duration 1800.1s (?木馬 0.006%), ERROR 0穇? Trades 0穇?????PASS
  - **12H Main Run (2025-11-22 21:54:02 ~ 2025-11-23 09:55:30)**: Duration 43,328s (12.04h, ?木馬 +0.3%) ????PASS, Infrastructure ??PASS, **Trading ??FAIL (0 trades, 0 decisions)**
  - Duration Fix: engine.py??鴔�� 諢𨁈溢 黺𥯆? (30黕��??
  - Run ID: Quick=20251122_194150_ouhr, Main=20251122_215340_au7g
  - ?��: ??**FAIL (Trading Criteria 諯賄隆魽? Infrastructure PASS)** ??PHASE22-3 ?𣕑𦉘諯貲� ?嶅� ?��
- **22-3: ??Parameter Tuning (2025-11-23) - FAIL**
  - **Test Run (15賱?**: 2025-11-23 11:04:38 ~ 11:19:38, Run ID: 20251123_110433_5lxj
  - **Trades**: 0 (Target: ??0 for 1H) ????FAIL
  - **Root Cause**: Config params穈� ?�嬍???�𡠺?䁯? ?𥇣� (load_strategies/engine 穈??貲�?䁯𦚯??諡賄�)
  - **?域�諡?*: `docs/PHASE22/PHASE22-3_PARAM_TUNING_REPORT.md`
  - **?��**: ??FAIL ??PHASE22-4
- **22-4: ?𩤃� Config Integration Fix (2025-11-23) - PARTIAL, DEFERRED**
  - **諈拗�**: ?�嬍貐?config params穈� ?嶅?諢??�𡠺?䁪�諢??䁯�
  - **Code Changes**: ??strategies/__init__.py, execution/engine.py ?䁯� ?��
  - **Unit Tests**: ??6/6 PASS (`test_phase22_4_config_integration.py`)
  - **Direct Test**: ??params 諢嶅𨫣 ?㻂� ?炣� ?㻂𥘵 (Python 鴔�� ?欠�)
  - **Runtime Issue**: ??run_paper.py ?欠� ??params 赬?dict諢??�𡠺, RSI threshold 篣圉雩穈?30/70) ?科鹻
  - **篞潺雩 ?韠𥘵 (PHASE23-0 賱��)**: Script-level orchestration 諡賄� (config 諢嶅𨫣/?�𡠺 窶趟�穈� script?韠� 鴗炣陬/賱��)
  - **?域�諡?*: `docs/PHASE22/PHASE22-4_CONFIG_INTEGRATION_INCOMPLETE.md`
  - **Config**: `configs/paper/phase22_4_scalping_param_smoke_30m.yml`
  - **?��**: ?𩤃� PARTIAL (Code-Level Fix OK, Runtime Integration FAIL) ??**DEFERRED to PHASE23-1** (architectural refactoring required)

**鴔�� 魽國探**: PHASE21 ?��

**?渥� 魽國探**: ?渠� 窱科※ ?��, 5穈??刺?謔??㻂� ?��, Ensemble v2 ?曰� ?��, 諡賄� ?��

---

?妝 **PHASE23** ??Ensemble & Engine Architecture V2 ?� **IN PROGRESS**

**?��**: ?� **IN PROGRESS** (2025-11-29 ?𨰰�, 23-0/23-1 ?��)

**諈拖�**: 
- PHASE22-2/3/4?韠� ?嶅剳??窱科※??諡賄�(0-trade, ?嶅� ?欠𤔅, config ?�� ?欠𤔅)諝?**?䇹� 鴗𡢾𡠺 ?��?𣽁� + 5-?刺?謔??軤�賳?窱科※**諢??湊盒
- ?渣� ?�嬍/?嶅�/諰�?域𡠺貐??㻂𤟠??"篣域??????䁪� ?��?𣽁� V2 ?��

**Sub-phases**:

### 23-0: TO-BE Architecture V2 諡賄�????
- **?��**: ??**COMPLETE** (2025-11-29)
- **貒䇹�**:
  - AS-IS ?��?𣽁� 賱�� (?䇹�, ?�嬍, ?軤�賳? config/script ?�𦚯??
  - PHASE22-2/3/4 Pain Point 諻?Root Cause ?瑅收
  - Single-Engine-Centric Architecture ?韠� ?㻂�
  - Strategy Config SSOT ?韠� ?㻂�
  - Mode-based Adapter Pattern ?曰� (backtest/paper/live 窸蛭�)
  - 5 Strategy Families 篣圉� Ensemble TO-BE 窱科※ ?瑅收
- **鴥潰� 諡賄�**:
  - `docs/PHASE23/PHASE23-0_ARCHITECTURE_TOBE_V2.md`
  - `docs/PHASE23/ENSEMBLE_STRATEGY_TOBE_V2.md`
- **Acceptance Criteria**: ??PASS
  - AS-IS / TO-BE 赬�� ?木𦚯?湊溢??魽渥�
  - 5穈??�嬍 ?刺?謔?HF Momentum / Volatility Breakout / Mean Reversion / Trend Following / Volume-Based) ??� 諈��
  - PHASE23-1~3 ?欠� 諢嶅�諤??㻂�

### 23-1: Single-Engine Entry Point & Config Propagation Fix ??
- **?��**: ??**COMPLETE** (2025-12-01)
- **諈拗�**: PHASE22-4 runtime config propagation ?渥�諝??䇹� 鴔��??窱科※ 謔秒玌?𧙖�?潺� 篞潺雩 ?湊盒
- **鴥潰� 貐�窶趣�??*:
  - `scripts/run_v2.py` 黺𥯆? (thin script, 97 lines)
    - ??�: config 諢嶅𨫣 + `engine.run_v2(...)` ?賄�諤??属�
    - paper / backtest / live 諈刺� 窸蛭� 鴔��??
  - `execution/engine.py`
    - `run_v2(mode, config, clean_state)` 黺𥯆?
    - ?渠??韠� `load_strategies(config)` 鴔�� ?賄�
    - use_ensemble / selector / adapter ?吖� 諢𨰰�???䇹�?潺� ?渠�
  - `tests/test_phase22_4_config_integration.py` docstring ?�㫲?渣䂻
- **窶�鴞?窶國頃**:
  - Unit Tests: 6/6 PASS
  - 30賱?PAPER smoke test: ??PASS
    - RSI 45/55 ?㻂� ?�� (篣圉雩穈?30/70 ?��)
    - ?木� ?賈�?渠� 諻𨰰�: 1 SHORT entry + 1 TP1 exit (+$19.23)
  - 諢𨁈溢: `[PHASE23-1 DEBUG] scalping params: {'rsi_oversold': 45, 'rsi_overbought': 55, ...}`
- **鴥潰� 諡賄�**: `docs/PHASE23/PHASE23-1_ENGINE_ENTRYPOINT_REFACTOR.md`
- **Acceptance Criteria**: ??ALL PASS
  - `run_v2.py` 篣賄𦚯 < 100 lines (97 lines)
  - `engine.run_v2()` 魽渥�, ?渠??韠� `load_strategies(config)` ?賄�
  - Config params 100% ?�� (RSI 45/55 ??
  - 篣域● `run()` 篣圉� 儠竾�/?嵸擪???𥔱?
  - 30賱?paper test?韠� ?賈�?渠�/麮?� 諢𨁈溢 ?㻂𥘵

### 23-2: Strategy Interface Unification ??
- **?��**: ??**COMPLETE** (2025-12-01)
- **諈拗�**: scalping_v3 諻?4穈?research ?�嬍???蛙𦉘??`BaseStrategy` ?貲�?䁯𦚯?月� ?�� ?蛭襔 + Ensemble Score V2 ?�� 黺𥯆?
- **?�� ?𡢾�**:
  - `scalping_v3.signal_logic(df, cfg)` ??private `_signal_logic()`, `compute_signal(df, config=None)` ?蛙𦉘
  - 4穈?research ?�嬍 (volatility_breakout_v2, mean_reversion_v2, trend_follow_v2, volume_based_v2) Score ?�� 黺𥯆?
  - 諈刺� ?�嬍 諻属� dict??`S_LONG`, `S_SHORT`, `S_RISK`, `S_QUALITY` 黺𥯆? (黕�萼 窱秒�)
  - `strategies/__init__.py::load_strategies()` BaseStrategy ?賄擪?渥擪 ?吖� 諢𨰰� 黺𥯆?
  - `SignalGenerator.generate_signal()` BaseStrategy.compute_signal() ?賄�諢?貐�窶?
- **?嵸擪??窶國頃**:
  - Unit Tests: ??6/6 PASS (`test_phase22_4_config_integration.py`)
  - 諈刺� ?�嬍 BaseStrategy ?賄擪?渥擪 ?吖� ?㻂𥘵
  - Config params 100% ?�� ?𥔱? (PHASE23-1 ?貲�)
- **鴥潰� 諡賄�**: `docs/PHASE23/PHASE23-2_STRATEGY_INTERFACE_UNIFICATION.md`
- **Acceptance Criteria**: ??ALL PASS
  - 5穈??�嬍 諈刺� `BaseStrategy` ?�� + `compute_signal(df, config=None)` + `metadata` 窱秒�
  - ?䇹�/SignalGenerator?韠� `compute_signal()` ?賄� (legacy fallback ?𥔱?)
  - Ensemble Score V2 ?�� 諈刺� ?�嬍??黺𥯆? (PHASE24 ?𨴴�??篣圉�)

### 23-3: Ensemble Orchestrator V2 ??
- **?��**: ??**COMPLETE** (2025-12-01)
- **諈拗�**: Score V2 篣圉� ?軤�賳??䁯�窶域� ?䇹� 窱秒�
- **?�� ?渥𡡒**:
  - ??`ScoreEngineV2`: Score V2 ?�� 黺䇹� 諻?窸�� (S_LONG, S_SHORT, S_NET, S_RISK, S_QUALITY)
  - ??`EnsembleAggregatorV2`: 3-Tier 諢𨰰� 窱秒� (High-Confidence / Consensus / Skip)
  - ??Dominance Prevention: `max_strategy_weight` cap (default: 60%)
  - ??Risk/Quality Filters: `max_risk`, `min_quality` thresholds
  - ??Engine Integration: `engine.run_v2()` ensemble mode='score_v2' 鴔�??
  - ??Unit Tests: 12/12 PASS (ScoreEngine, Aggregator, Tier 1/2/3, Dominance, Filters)
  - ??Backward Compatibility: V1 (factor-based) mode ?𥔱?
- **窱秒� ?嵸𦉘**:
  - `common/ensemble/score_engine_v2.py` (347 LOC)
  - `common/ensemble/aggregator_v2.py` (528 LOC)
  - `execution/engine.py` (+150 LOC)
  - `tests/test_phase23_3_ensemble_orchestrator_v2.py` (538 LOC, 12 tests)
- **諡賄�**:
  - `docs/PHASE23/PHASE23-3_ENSEMBLE_ORCHESTRATOR_V2_DESIGN.md` (?曰�)
  - `docs/PHASE23/PHASE23-3_ENSEMBLE_ORCHESTRATOR_V2.md` (窱秒� 謔秒𡢢??
  - Unit Tests: 12/12 PASS (0.52s)
  - Coverage: ScoreEngine, 3-Tier logic, Dominance prevention, Risk/Quality filters
- **?韠�**: PHASE23-3 COMPLETE (Unit Test Validated, PAPER Smoke Test Optional)

### 23-4: Validation & Cleanup ??
- **?��**: ??**COMPLETE** (2025-12-02)
- **諈拗�**: PHASE23-0 ~ 23-3 貐�窶??秒𨯙 ?瑅收 諻??渣� PHASE諢??䁯𩸭穈�篣??�� "?渠旭 篣域??? ?吖�
- **?�� ?渥𡡒**:
  - 12賱?PAPER ?欠�?潺� Ensemble V2 諢𨰰� 窶�鴞??��
  - 5,499??Aggregate ?㕓?: Tier1 25.5%, Tier2 1.0%, Skip 73.5%
  - 50穈??賈�?渠� 諻𨰰� (LONG/SHORT 篞𡥄�??
  - 3穈??�嬍 ?𨰰� 篣域𤩐: trend_follow_v2 (62%), mean_reversion_v2 (36%), volume_based_v2 (2%)
  - Score V2 ?�� ?㻂� 窸�� (S_NET, S_RISK, S_QUALITY)
  - 3-Tier 諢𨰰� ?㻂� ?炣� (High-Confidence / Consensus / Skip)
  - Dominance prevention ?㻂� ?炣� (?到𦉘 ?�嬍 ?�烵 麮䁪收 ?㻂𥘵)
  - Risk/Quality ?�� ?炣� ?㻂𥘵
  - 貒�溢 3穇??䁯�: V2 ?�嬍 諯賈𢲡諢? aggregate_v2() ?𨁈溢?��, 諢𨁈溢 穈�?𨰰�
- **?韠�**: PASS - Ensemble V2 Production Ready

### 23-5: Legacy Engine Decommission & Single-Engine Hardening ??
- **?��**: ??**COMPLETE** (2025-12-05)
- **諈拗�**: Backtest/Paper/Live 諈刺� 諈刺�??`execution.engine.run_v2()` ?到𦉘 ?䇹�諤??科鹻?䁪�諢?穈㻂�
- **?�� ?渥𡡒**:
  - ??`scripts/run_backtest.py` ??thin wrapper (538鴗???132鴗?
    - Config 諢嶅𨫣 + `run_v2(mode='backtest')` ?賄�諤?
  - ??`scripts/run_paper.py` ??thin wrapper (501鴗???152鴗?
    - Config 諢嶅𨫣 + `run_v2(mode='paper')` ?賄�諤?
  - ???�掠???欠�謔踫䂻 13穈???`scripts/legacy/` ?渠�
    - run_phase*.py, run_tuner*.py, run_wfa*.py ??
    - `scripts/legacy/README.md` 黺𥯆? (?�僑?渠� 穈�?渠�)
  - ???國筋???䁪�????� 諈��
    - phase27_4/6/7_*.py??"?䇹� ?�� / 賱��?? 鴥潰� 黺𥯆?
  - ???到𦉘 ?䇹� 貐渥𤟠 ?嵸擪??黺𥯆?
    - `tests/test_engine_single_entrypoint.py` (8 tests, 8/8 PASS)
- **Acceptance Criteria**: ??ALL PASS
  - `run_backtest.py`, `run_paper.py`穈� `run_v2` import + ?賄� ?㻂𥘵
  - 窸蛙� ?域� 3穈嶅� scripts/ 諴刮䂻??魽渥� (run_v2, run_backtest, run_paper)
  - ?�掠???欠�謔踫䂻 13穈?scripts/legacy/ ?渠� ?��
  - ?𥻗� ?䇹� 鴔��???吖� 諻拖? ?嵸擪??黺𥯆?
- **?韠�**: ??COMPLETE - ?到𦉘 ?䇹� ?韠� 穈㻂� ?��

**鴔�� 魽國探**: PHASE22-4 PARTIAL ?�� (code-level fix done, runtime integration deferred)

**?渥� 魽國探**:
- TO-BE ?��?𣽁� V2 諡賄�??(PHASE23-0)
- Config propagation ?㻂� ?炣� (PHASE23-1)
- 5穈??�嬍 ?貲�?䁯𦚯???蛙𦉘 + Ensemble Score V2 ?�� 黺𥯆? (PHASE23-2)
- Ensemble Orchestrator V2 窱秒� (PHASE23-3)
- Validation & Cleanup (PHASE23-4) - 12賱?PAPER 窶�鴞??��, 5,499 aggregate, 50 trades, 3 ?�嬍 ?𨰰�
- Legacy Engine Decommission (PHASE23-5) - ?到𦉘 ?䇹� ?韠� 穈㻂�, 13穈??�掠???欠�謔踫䂻 ?�僑?渠�

**諈拖�**: Redis ?國盒/黕�萼???��??諻?Ensemble V2 ?貲�???�疏 窶�鴞?

**Sub-phases**
- **24-0: Redis Hardening & Ensemble V2 Infra Validation** COMPLETE (2025-12-02)
  - .env??Redis ?瞘祭貐�??黺𥯆? (REDIS_HOST, REDIS_PORT, REDIS_DB)
  - Config ?嵸𦉘 ?𨂃�謔??𨁈掠 (${REDIS_HOST} ??localhost:6379)
  - clean_state_complete.py ?科�??諢𨰰� 黺𥯆? (max_retries=10)
  - database/redis.py 諢𨁈溢 穈�?𨰰� 穈𨰰� (INFO ?�疏)
  - 2H PAPER ?欠�: 10,798 aggregates, 78 trades, **Redis ERROR 0穇?*
  - **Acceptance**: PASS (Production Ready Baseline ?瑅汗)
- **24-1: Full Infra Diagnostics** COMPLETE (2025-12-02)
  - DB cleanup ?��???瑅陷 (database/cleanup.py 黺𥯆?, trades ?禺𢲡??0穇?
  - ?蛭襔 ?貲�??鴔�𡆀 ?欠�謔踫䂻 (phase24_1_infra_diagnostics.py: DB/Redis/Engine ?韀?)
  - DB ?欠�諤?魽域� (inspect_db_schema.py: mode 儢禺獏 ?㻂𥘵, run_id ?�� 諻𨁈痊)
  - 6賱?PAPER ?月爸???嵸擪?? 24 trades, **Redis/DB/Engine ERROR 0穇?*
  - Tests: test_phase24_1_db_cleanup.py (4/4 PASS), test_phase24_1_infra_diagnostics.py (5/5 PASS)
  - **Acceptance**: PASS (DB cleanup ?��??+ ?貲�??鴔�𡆀 麮湊� ?瑅汗)
- **24-2: Env & Config Management** COMPLETE (2025-12-02)
  - .env.example ?吖� (?�� ?瞘祭貐�??諡賄�?? 80 LOC)
  - Env/Config Validator (env_config_validator.py: ?瞘祭貐�??+ YAML config 窶�鴞? 414 LOC)
  - 窶�鴞???版: ?�� ?? ?�?? ?�嬍 ?渠�, ensemble mode, duration/leverage 貒䇹� ??
  - Tests: test_phase24_2_env_config_validation.py (11/11 PASS, 100%)
  - 6賱?PAPER ?㴒? ?嵸擪?? 33 trades, **?貲�??ERROR 0穇?*
  - **Acceptance**: PASS (Env/Config 窶�鴞??�𦚯???瑅汗)

**鴔�� 魽國探**: PHASE23 ?��

**?渥� 魽國探**: 
- ??Redis ERROR/CRITICAL 0穇?(2H+ PAPER) - PHASE24-0 ?��
- ???�眼 INFRA 鴔�𡆀 ?�� (PHASE24-1) - DB cleanup + ?蛭襔 鴔�𡆀 ?欠�謔踫䂻
- ???瞘祭貐�??窵�謔??韒�???�� (PHASE24-2) - Env/Config validator + .env.example
- ??DB/Redis/Engine ?蛭襔 ?��???瑅陷 - PHASE24-0~2 ?��

**PHASE24 ?韠�**: ??**COMPLETE** - Production Ready Infra Baseline ?瑅汗

---

?妝 **PHASE25** ??Long-run Regression & Tuning Infra ??**COMPLETE**

**?��**: ??**COMPLETE** (25-0/25-1/25-2/25-3/25-4 ?��)

**諈拖�**: ?伉萼 PAPER ?嵸擪???韒�??+ ?�嬍/魽堅襔 ?𣕑𦉘諯貲� ?韒� ?韠� ?貲�??窱科�

**Sub-phases**
- **25-0: Long-run PAPER Regression Harness** ??**COMPLETE** (2025-12-02)
  - 黖𨰰� 2H ?渥� PAPER ?韒�???䁪�??窱科� ?��
  - ?�� ?韒�?? Pre-flight ??Clean State ??Run ??Monitor ??賱�� ??謔秒𡢢??
  - 6賱??月爸?科? 諈��??窱禺� (6賱?穈嶅�/CI?? 2H+=Acceptance??
  - ?木�穈?ERROR 穈韠? & 鴞吣� 鴗炣𡆀
  - ?域�諡? `phase25_0_long_run_paper.py`, ?嵸擪?? 2H Config, 謔秒𡢢??
  - **Acceptance (?貲�??篣域?)**: ??PASS
    - Duration: 2.00H (諈拗� 1.96H ?渥�)
    - CRITICAL ?月�: 0穇?
    - ?𨰰� ?科??? 0
    - Ensemble Aggregate: 10,564??(諈拗� 1,000???渥�)
  - **?�嬍 KPI**: ?𩤃� Trade ??39穇?(諈拗� 50穇?諯賈𡠺, ?�嬍 PHASE?韠� ?嶅� ?��)
  - **Known Issues**: Trade throughput?� ?�嬍/?𣕑𦉘諯貲� ?嶅� ?�𡡒?渠庚, ?貲�??Acceptance 篣域??韠�???𨰰烵
- **25-1: Tuning Cluster Infra** ??**COMPLETE** (2025-12-03)
  - DB ?欠�諤? `tuning.runs`, `tuning.jobs`, `tuning.results` (3穈??嵸𦚯賳? 窱科� ?��
  - Job Queue: ?軤�???�� Job ?𧙖鰟 (SELECT FOR UPDATE SKIP LOCKED)
  - Worker Skeleton: Dummy ?欠� + 窶國頃 ?�??
  - Worker CLI: `scripts/infra/phase25_1_run_worker.py` 窱秒�
  - ?域�諡? `tuning/cluster/job_queue.py`, `tuning/cluster/worker.py`
  - ?嵸擪?? 7/7 PASS (100%)
  - **Acceptance**: ??PASS
    - DB ?欠�諤?窱科� ?��
    - Job Queue ?軤�???�� 窶�鴞?
    - Worker Skeleton dummy ?欠� ?梓陬
    - 諈刺� ?嵸擪??PASS
  - **Known Issues**: Worker timeout 麮䁪收 ?��, ?木� ?䇹� ?賄� ?�� (PHASE25-2?韠� 窱秒�)
- **25-2: Random Search ?嵸𦚯?�𦉘??* ??**COMPLETE** (2025-12-03)
  - Random Search ?㴒�謔科� 窱秒� (seed 篣圉� ?秒� 穈�??
  - Worker?韠� ?木� backtest ?䇹� ?賄� (run_v2 ?蛭襔)
  - ParamSpace: int/float/categorical ?�??鴔�??
  - CLI Runner: `phase25_2_run_random_search.py` 窱秒�
  - ?域�諡? `tuning/algorithms/random_search.py` (428 LOC)
  - ?嵸擪?? 3/3 PASS (篣圉雩), 2 SKIP (slow)
- **25-3: Bayesian Search ?嵸𦚯?�𦉘??* ??**COMPLETE** (2025-12-03)
  - Bayesian Optimization (Optuna TPE) ?蛭襔
  - Sequential ?嶅� (?到𦉘 ?��?賄擪)
  - ParamSpace ??Optuna suggest API ?韒� 貐�??
  - CLI Runner: `phase25_3_run_bayesian_search.py` 窱秒�
  - ?域�諡? `tuning/algorithms/bayesian_search.py` (641 LOC)
  - ?嵸擪?? 5/5 PASS (篣圉雩), 1 SKIP (slow)
  - **Acceptance**: ??PASS
    - Optuna Study ?㻂� ?軤�
    - ParamSpace 貐�??窶�鴞?
    - Trial ?欠𤔅 麮䁪收 ?㻂𥘵
    - 諈刺� 篣域● ?嵸擪???𥔱? (PHASE25-1: 7/7, PHASE25-2: 3/3)
  - **Known Issues**: Sequential only (貐炣䁥??諯賄???, 諰籝䂻謔?黺䇹� 穈��?? Worker timeout ?��
- **25-4: Local Grid Search & Metrics Refinement** ??**COMPLETE** (2025-12-03)
  - Local Grid Search Tuner: Best K ?�陷 鴥潺? 窱?� 篞賈收???韠�
  - Metrics Refinement: ?𨁈� 篣圉� isolation + Sharpe/MaxDD ?𤣿� 窸��
  - Worker Timeout: Stale job ?韒� ?欠𤔅 麮䁪收 (`mark_stale_jobs_as_failed()`)
  - Tuner Consolidation: ?�掠???嶅� deprecated ?𨰰�
  - ?域�諡? `local_grid_search.py` (641 LOC), `worker.py` (?䁯�), `job_queue.py` (?䁯�)
  - ?嵸擪?? 7/7 PASS (?蛙𡠺 諢𨰰�), 22/22 PASS (?㴒? ?嵸擪???秒𥚃)
  - **Acceptance**: ??PASS
    - Local Grid Search ?㻂� ?軤� (Grid ?吖�, Top K 魽堅�)
    - Sharpe Ratio 穈𨰰� (?潺� ?䁯㷫諝?篣圉� 篞潰�)
    - Max Drawdown 窱秒� (cumulative PnL 篣圉�)
    - Stale job timeout 麮䁪收 窶�鴞?
    - Random ??Bayesian ??Local Grid 3?刷� ?嵸𦚯?�𦉘???��
  - **Known Issues**: ?𨁈� 篣圉� isolation ?�祭?䁯? ?𥇣� (PHASE26?韠� run_id 黺𥯆?), Sequential only
- Random Search ?嵸𦚯?�𦉘??窱科� - PHASE25-2
- Bayesian Search ?嵸𦚯?�𦉘??窱科� (Optuna TPE) - PHASE25-3
- Local Grid Search + 諰籝䂻謔??𨴴�??- PHASE25-4 (?𡥄�)
- ?木�???𣕑𦉘諯貲� ???瑅陷 - PHASE25-4/5

---

 **PHASE26** ??Multi-Symbol Engine v1 ??**COMPLETE**

**?��**: ??**COMPLETE** (2025-12-03)

**諈拖�**: TopN ?禺頃 ?㻂𤟠 諻?Multi-symbol ?䇹� 窱科※ ?瑅汗

**Sub-phases**

- **26-0: Universe Provider 窱秒�** ??**COMPLETE** (2025-12-03)
  - TopN ?禺頃 ?𥔱� 諢𨰰� (Binance API 篣圉�)
  - Protocol-based ?貲�?䁯𦚯??(StaticUniverseProvider, TopNByVolumeUniverseProvider)
  - Config ?欠�諤??㻂𤟠 (`universe` ?寢�)
  - 儥韠㘚 (TTL 1?𨁈�) + Fallback ?��??
  - **?域�諡?*: `common/universe_provider.py` (520 LOC), `load_universe_config()` 黺𥯆?
  - **?嵸擪??*: 23/23 PASS (100%), ?㴒? ?嵸擪??20/20 PASS
  - **Acceptance**: ??PASS

- **26-1: Multi-Symbol Engine Sequential Processing** ??**COMPLETE** (2025-12-03)
  - per-symbol buffer 窵�謔?(Multi-TF 鴔�??
  - Universe ??Engine ?蛭襔 (`symbols` ?𣕑𦉘諯貲�)
  - Sequential symbol processing (儠竾ㄗ???�𦚯)
  - **?域�諡?*: `execution/engine.py` ?䁯� (DO-NOT-TOUCH 黖𨰰�??
  - **?嵸擪??*: ?㴒? ?嵸擪??100% PASS
  - **Acceptance**: ??PASS

- **26-2: Top10 Multi-Symbol PAPER Load Test** ??**COMPLETE** (2025-12-03)
  - 2?𨁈� Top10 PAPER ?㻂� 鮈��
  - Multi-Symbol 諰籝䂻謔??䁯� (per-symbol trades)
  - Runner harness 窱科� (`phase26_2_run_top10_paper.py`)
  - **?域�諡?*: `scripts/infra/phase26_2_run_top10_paper.py`, Config, Report
  - **Acceptance**: ??PASS

- **26-3: Performance Tuning & Top100 Scalability** ??**COMPLETE** (2025-12-03)
  - MultiSymbolProfiler 窱秒� (`common/perf/perf_profiler.py`)
  - IndicatorCache 窱秒� (`indicators/indicator_cache.py`)
  - Scaling Test: Top10/20/50/100 (穈?5賱? - 4/4 ?梓陬
  - Acceptance Run: Top100 30賱?PAPER - ERROR 0穇? CRITICAL 0穇?
  - **?域�諡?*: 
    - `common/perf/perf_profiler.py` (MultiSymbolProfiler)
    - `indicators/indicator_cache.py` (Incremental 窸�� 儥韠�)
    - `scripts/infra/phase26_3_run_top100_paper.py` (Runner)
    - `configs/paper/phase26_3_top100_paper_30m.yml`
  - **?嵸擪??*: 17/17 PASS
  - **Acceptance**: PASS
    - Top100 30賱?PAPER ?㻂� 鮈��
    - ERROR 0穇? CRITICAL 0穇?
    - ?��?嵸𦉘諤?篣圉雩 諰籝䂻謔??䁯� (篣圉雩 諰籝䂻謔?�, Full integration?� PHASE27)
    - Redis/DB/Env Pre-flight 鴔�𡆀 ?虛頃
  - **Known Limitations**:
    - **Trade 0穇????�嬍/?軤�賳?穈�???嶅� ?渥�**
      - 30賱�? ?木� market signal 諻𨰰�??鴔抓? ?𨁈�
      - ?�嬍 鴔�� 魽國探??貐渥�??(RSI, EMA 魽國探 ?�痔)
      - PHASE26?� ?貲�???��??窶�鴞吖� 鴔𡢾�, Trade throughput?� ?�嬍 ?嶅� PHASE諢??湊?
    - Full profiling integration (Loop Latency, CPU, Memory)?� PHASE27諢??國萼

**鴔�� 魽國探**: PHASE25 ?�� 

**?渥� 魽國探**: Top100 ?禺頃 30賱?PAPER ?㻂� 鮈��, ERROR 0穇??㻂𥘵 

---

 **PHASE27** ??Trade Activity Diagnosis & Strategy Tuning **PARTIAL COMPLETE**

**?��**: **PARTIAL COMPLETE** (27-0/27-1 ?��, 27-2 ?��) (2025-12-04)

**諈拖�**: "0 ?賈�?渠�" ?韠𥘵 鴔�𡆀 諻??�嬍/?軤�賳??𣕑𦉘諯貲� ?嶅�

**Sub-phases**

- **27-0: Trade Activity Diagnosis & Drop-off Instrumentation** **COMPLETE** (2025-12-04)
- **27-0: Trade Activity Diagnosis & Drop-off Instrumentation** ??**COMPLETE** (2025-12-04)
  - Signal ??Trade ?嵸𦚯?�𦉘??Drop-off 窸�腹 ?貲�??窱科�
  - TradeActivityTracker 諈刺� (Thread-safe, JSON serialization)
  - Engine/Guard Hook 6穈?黺𥯆? (Optional, ?月�?月� 0)
  - Runner ?欠�謔踫䂻: Single-Symbol 30m, Multi-Symbol Top10 30m
  - **?域�諡?*:
    - `metrics/trade_activity_tracker.py` (285 LOC)
    - `execution/engine.py` (+6 hooks, DO-NOT-TOUCH 鴗�??
    - `scripts/infra/phase27_0_run_diagnosis.py` (327 LOC)
    - `configs/paper/phase27_0_single_symbol_30m.yml`
    - `configs/paper/phase27_0_top10_30m.yml`
    - `docs/PHASE27/PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_DESIGN.md` (431 lines)
    - `docs/PHASE27/PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_REPORT.md` (?欠� 謔秒𡢢??
  - **?嵸擪??*: 21/21 PASS (Unit Tests), 22/22 PASS (Regression)
  - **Acceptance**: ??PASS
    - Drop-off 窸�腹 ?貲�???��
    - 4穈?Root Cause 穈�??諡賄�??
    - Parameter Tuning ?�陷 諈拘� ?𡢾�
    - ?欠� ?欠�謔踫䂻 & Config 鴗�赬??��
  - **Diagnosis Runs** (2025-12-04):
    - Single-Symbol 30m: ??COMPLETE (30.08 min, 1,006 candles, **0 trades**)
      - Strategy Signals: 0/4,755 (100% dropout at strategy layer)
      - Ensemble Decisions: 951 skips, 0 Tier1, 0 Tier2
    - Multi-Symbol Top10 30m: ??COMPLETE (30.09 min, 9,054 candles, **0 trades**)
      - Strategy Signals: 0/42,795 (100% dropout across all 10 symbols)
      - Ensemble Decisions: 8,559 skips, 0 Tier1, 0 Tier2
  - **Historical Analysis**:
    - PHASE23-4 (12m, Single): 50 trades, 5,499 aggregates (Healthy)
    - PHASE25-0 (2H, Single): 39 trades, 10,564 aggregates (Low throughput)
    - PHASE26-3 (30m, Top100): 0 trades, 0 aggregates (Complete dropout)
    - **PHASE27-0** (30m, Single+Top10): **0 trades, 100% strategy signal dropout**
  - **Root Cause Confirmed**:
    - **Strategy Parameters Too Conservative**: All 5 V2 strategies returned `signal_false` in every evaluation
    - Pipeline Intact: Feed, indicators, ensemble aggregator functioned correctly
    - **Next Step**: PHASE27-1 aggressive parameter tuning required

- **27-1: Parameter Tuning** ??**COMPLETE** (Tuning insufficient, escalate to 27-2)
  - **V1 - Moderate Tuning** (2025-12-04, 08:03-08:33):
    - Config: `phase27_1_single_symbol_30m_v1.yml`
    - Changes: RSI 25/75, BB std 1.8, ensemble 0.6/0.3
    - Result: **0 trades** (Strategy Signals: 0/4,755, 100% dropout)
  - **V2 - Aggressive Tuning** (2025-12-04, 09:33-10:03):
    - Config: `phase27_1_single_symbol_30m_v2.yml`
    - Changes: RSI 20/80, BB std 1.5, ensemble 0.5/0.2
    - Result: **0 trades** (Strategy Signals: 0/4,755, 100% dropout)
  - **Verdict**: ??**Parameter-only tuning CANNOT solve 0-trade issue**
  - **Root Cause Confirmed**: Strategy algorithms fundamentally incompatible with current market conditions (low-volatility consolidation)
  - **Lesson**: Fixed-threshold indicator strategies (RSI/BB/ADX) fail in unfavorable regimes
  - **Escalation**: PHASE27-2 (Strategy Logic Redesign) required

- **27-2: Strategy Logic Redesign** ??**COMPLETE** (2025-12-04)
  - **Problem**: Fixed-threshold indicator strategies fail in unfavorable market regimes
  - **Solution**: Percentile-based baseline strategy (btc5m_baseline_v1)
  - **Data Analysis**: 30 days BTCUSDT 5m profiling completed
  - **Implementation**: RSI 45/55, BB 1.0/1.5 std, Momentum 5-candle, OR logic
  - **Tests**: 12/12 PASS (100%)
  - **Artifacts**: strategies/btc5m_baseline_v1.py, PHASE27-2_STRATEGY_REDESIGN_REPORT.md
  - **Next**: PHASE27-3 (ADX integration + execution validation)

- **27-3: ADX Integration + Execution Validation** ?𩤃� **PARTIAL COMPLETE** (2025-12-04)
  - **Goal**: ADX regime-based strategy enhancement + Paper execution validation
  - **Implementation** ??
    - ADX indicator: compute_adx() (91 LOC, Wilder smoothing)
    - Regime: Range (ADX ??25) vs Trend (ADX > 25)
    - Range: Mean reversion (RSI, BB, Momentum OR)
    - Trend: Extreme conditions (BB Strong, RSI+BB combo)
    - Strategy: v1.0 ??v1.1
  - **Tests** ?? 25/25 PASS (ADX 8/8 + Baseline 17/17)
  - **Artifacts** ??
    - indicators/core_indicators.py (ADX)
    - strategies/btc5m_baseline_v1.py (v1.1)
  - MultiSymbolProfiler ?䇹� ?蛭襔
  - Loop Latency, CPU, Memory ?木�穈??䁯�
  - IndicatorCache ?𨰰�??
  - **Status**: COMPLETE
  - **Next Steps**: PHASE27-5 ?��

- **27-5: Signal Parity & Engine Replay 窶�鴞?* ??**COMPLETE** (2025-12-04)
  - Offline Scan ??Engine Replay ?𡥄猹 ?吖� 貐虛筋
  - **Status**: ??PRODUCTION READY
  - **Results**:
    - Offline Scan: 5,741穈??𡥄猹
    - Engine Replay: 6,868穈??𡥄猹 (+19.6%)
    - ?嵸𦚯?�𦉘???㻂� ?炣� 鴞噃� (0 ??6,868穈?
    - TradeActivityTracker ?蛭襔 ?��
  - **Root Cause (Fixed)**:
    - btc5m_baseline_v1 ?�嬍 諯賈𢲡諢????梵� ?��
    - ?到𦉘 ?�嬍 諈刺� PHASE23-2 諯賄�?????�鹻 ?��
    - TradeActivityTracker 諯貲�?????蛭襔 ?��
  - **Artifacts** ??
    - strategies/__init__.py (btc5m_baseline_v1 ?梵�)
    - execution/engine.py (BaseStrategy.compute_signal() ?賄�)
    - scripts/research/phase27_5_btc5m_baseline_engine_replay.py
    - tests/test_phase27_5a_strategy_loading.py (7/7 PASS)
    - tests/test_phase27_5_signal_parity.py (3 PASS, 1 FAIL, 2 SKIP)
    - configs/backtest/phase27_5_baseline_replay_30d.yml
    - docs/PHASE27/PHASE27-5_SIGNAL_PARITY_AND_BACKTEST_DESIGN.md
    - docs/PHASE27/PHASE27-5_BASELINE_SPEC_AND_METRICS.md
    - docs/PHASE27/PHASE27-5_SIGNAL_PARITY_INITIAL_FINDINGS.md
    - docs/PHASE27/PHASE27-5A_SIGNAL_PARITY_FIX_REPORT.md
  - Signal Parity Analyzer 窱秒�
  - TradeActivityTracker LONG/SHORT/Regime ?㻂𤟠
  - **Status**: ??COMPLETE
  - **Results**:
    - Analyzer: 13/13 ?嵸擪??PASS
    - Parity ?嵸擪?? 4/6 PASS (2穈?Known Issues)
    - LONG/SHORT 赬�銁 Parity: 0.5%p (??諈拗� 簣5% ?渠�)
  - **Artifacts** ??
    - scripts/research/phase27_6_signal_parity_analyzer.py (343 lines)
    - tests/test_phase27_6_signal_parity_analyzer.py (13/13 PASS)
    - metrics/trade_activity_tracker.py (LONG/SHORT/Regime 儦渥𠂔??黺𥯆?)
    - execution/engine.py (Hook??side/regime ?�𡠺)
    - docs/PHASE27/PHASE27-6_SIGNAL_PARITY_DEEP_DIVE_REPORT.md
    - docs/PHASE27/phase27_6_signal_parity_analysis.json
  - **Known Issues** (PHASE27-7?韠� ?湊盒):
    - Signal count 麆到𦚯 19.6% ??PHASE27-7?韠� Regime 賱�� ?䁯�
    - Regime 100% RANGE (TREND 0%) ??PHASE27-7?韠� ADX ?𣕑𦉘諯貲� ?�𡠺 ?䁯�
  - **Next**: PHASE27-7 (Root Cause Fix)

- **27-7: Signal Parity Root Cause & Fix** ??**PARTIAL SUCCESS** (2025-12-05)
  - Regime Parity ?科�, Signal Count??Known Issue
  - **Status**: ??REGIME PARITY ?科�
  - **Results**:
    - Regime Parity: **0.11%p** (??諈拗� 簣10% ?渠�)
    - LONG/SHORT Parity: **0.05%p** (??諈拗� 簣5% ?渠�)
    - Signal Count: -17.79% (?𩤃� 諈拗� 簣10% 黕�頃, Known Issue)
    - Parity ?嵸擪?? 5/6 PASS
  - **Root Cause (Fixed)**:
    - Engine add_indicators() ?賄� ??use_adx/adx_period ?�嚿 ??黺𥯆?
    - ?到𦉘 ?�嬍 諈刺� strategy_cfg 貐𣖙襔 ?�嚿 ???䁯�
    - Offline Scan adx_trend_threshold=25 vs Replay=20 ??20?潺� ?蛙𦉘
    - add_indicators() dropna() 穈㻂� ??drop_nan ?𣕑𦉘諯貲� 黺𥯆? (篣圉雩 False)
  - **Artifacts** ??
    - execution/engine.py (ADX ?𣕑𦉘諯貲� ?�𡠺, strategy_cfg 貐𣖙襔)
    - indicators/core_indicators.py (drop_nan ?𣕑𦉘諯貲�)
    - scripts/research/phase27_7_btc5m_signal_parity_diff.py (Per-bar diff harness)
    - tests/test_phase27_7_signal_parity_diff.py (9/9 PASS)
    - docs/PHASE27/PHASE27-7_SIGNAL_PARITY_ROOT_CAUSE_FIX_REPORT.md
    - docs/PHASE27/phase27_7_signal_parity_diff_report.json
  - **Known Issue**:
    - Signal count -17.79% (?域𦚯??貒䇹� 麆到𦚯 黺䇹�, PHASE27-8?韠� 魽域� ?韒� ?䁯鹻)
  - **Conclusion**: Regime Parity ?科�?潺� 鴥?諈拗� ?��, Signal Count???𨂃�??穈𨰰�

- **27-8: Baseline Signal SSOT & Cleanup** ??**COMPLETE** (2025-12-05)
  - Offline Scan 窶拘收 諻??𡥄猹 窸�� 窶趟� ?到𦉘??
  - **Status**: ??SIGNAL SSOT ?��
  - **諈拗�**: ?𡥄猹 窸��?� `execution/engine.py::run_v2()` ?到𦉘 窶趟�諤??科鹻
  - **?�� ?渥𡡒**:
    - ??Offline Scan 窶拘收: `phase27_4_btc5m_baseline_signal_scan.py` ??`scripts/legacy/` ?渠�
    - ??Diagnostic script 窶拘收: `diagnose_scalping_signals.py` ??`scripts/legacy/` ?渠�
    - ??窶赭� 鴥潰� 黺𥯆?: DEPRECATED, SSOT ?韠� ?�偽 諈��
    - ??SSOT Guard ?嵸擪??黺𥯆?: `tests/test_phase27_8_signal_ssot_guard.py` (6/6 PASS)
    - ???㴒? ?嵸擪?? `test_engine_single_entrypoint.py` (8/8 PASS)
  - **SSOT ?韠�**:
    ```
    execution/engine.py::run_v2()
        ??
    BaseStrategy.compute_signal(df, config)
        ??
    metrics/trade_activity_tracker.py
    ```
  - **?�鹻 貒䇹�**:
    - ??JSON諤??趟� 賱�� ?欠�謔踫䂻 (phase27_6, phase27_7)
    - ??subprocess諢?run_v2 ?賄�?䁪� ?䁪�??(phase27_5)
    - ???䇹� ?賈??韠� signal_logic() 鴔�� ?賄� 篣�?
    - ??add_indicators() + ?𡥄猹 窸�� ?刮� 篣�?
  - **Artifacts** ??
    - scripts/legacy/phase27_4_btc5m_baseline_signal_scan_legacy.py
    - scripts/legacy/diagnose_scalping_signals_legacy.py
    - tests/test_phase27_8_signal_ssot_guard.py (6 tests)
    - docs/PHASE27/PHASE27-8_BASELINE_SIGNAL_SSOT_AND_CLEANUP.md
  - **Acceptance Criteria**: ??ALL PASS
    - Offline Scan 儠竾� scripts/legacy/諢?窶拘收
    - SSOT Guard ?嵸擪??6/6 PASS
    - scripts/?韠� ?𡥄猹 鴔�� 窸�� 儠竾� 0穇?
    - PHASE23-5 ?㴒? ?嵸擪??8/8 PASS
  - **?韠�**: 
  - Baseline Signal SSOT ?瑅汗

- **27-9: SSOT Final Verification & Doc Sync** ??**COMPLETE** (2025-12-05)
  - ?䇹�/?𡥄猹 窶趟� SSOT 窱科※ 黖𨰰� 窶�鴞?
  - **Status**: ??SSOT ?韒� 窶�鴞?麮湊� ?��
  - **諈拗�**: "?䇹� ??貒?+ ?𡥄猹 窶趟� ??貒? ?韒� 貐渥𤟠
  - **窶�鴞?窶國頃**:
    - ???到𦉘 ?䇹�: run_v2() ?到𦉘 鴔��?? run_v3 ?��
    - ???𡥄猹 窶趟� ?到𦉘?? BaseStrategy.compute_signal() ??TradeActivityTracker
    - ??Legacy 窶拘收: phase27_4, diagnose_scalping ??scripts/legacy/
    - ??SSOT ?�� 0穇?(Legacy ?𨰰烵)
  - **pytest 窶國頃**:
    - ??41 PASS, 1 XFAIL (Known Issue)
    - ??test_phase27_8_signal_ssot_guard.py: 6/6 PASS
    - ??test_engine_single_entrypoint.py: 8/8 PASS
  - **Known Issue 諈��??*:
    - Signal count parity 17.79% (?域𦚯??貒䇹�/warmup 麆到𦚯)
    - ?䇹�/SSOT 窱科※?� 諡湊?, Production ?科鹻 穈�??
    - Regime Parity(0.11%p), LONG/SHORT Parity(0.05%p) 諈拗� ?科�
  - **Artifacts** ??
    - docs/PHASE27/PHASE27-9_SSOT_FINAL_VERIFICATION.md
    - tests/test_phase27_5_signal_parity.py (Known Issue xfail ?𨰰�)
    - tests/test_phase27_6_signal_parity_analyzer.py (?軤� 窶�鴞?
    - docs/PHASE27/PHASE27-8_BASELINE_SIGNAL_SSOT_AND_CLEANUP.md (COMPLETE ?�㫲?渣䂻)
  - **?韒� 窶�鴞?麮湊�**:
    - pytest穈� SSOT ?�� 鴞吣� ?韠?
    - AST 篣圉� ?𡥄猹 鴔�� 窸�� ?刮� 穈韠?
    - "?䇹� ??貒?+ ?𡥄猹 窶趟� ??貒???篧刺� ?𨁈� CI/CD 麆刺𡆀
  - **?韠�**: ??COMPLETE - SSOT ?韒� 貐渥𤟠 ?��

**鴔�� 魽國探**: PHASE26 ?��

**?渥� 魽國探**: 
- ??Trade Activity Diagnosis ?貲�???�� (27-0)
- ??Baseline+ADX ?�嬍 窱秒� 諻?Engine ?蛭襔 (27-2, 27-3, 27-5)
- ??Signal Parity ?科�: Regime 0.11%p, LONG/SHORT 0.05%p (27-6, 27-7)
- ??Signal SSOT ?韠� ?瑅汗 (27-8)
- ??**SSOT ?韒� 窶�鴞?麮湊� ?�� (27-9)**

**PHASE27 ?韠�**: ??**COMPLETE** (27-0 ~ 27-9 ?��, 2025-12-05)
- Trade Activity Diagnosis ?貲�??窱科�
- Strategy Logic Redesign (Percentile-based Baseline)
- ADX Integration & Regime-based filtering
- Baseline+ADX ?�嬍 Engine ?蛭襔 諻?Signal Parity ?科�
- Signal 窸�� 窶趟� ?到𦉘??(SSOT ?韠� ?瑅汗)
- **SSOT ?韒� 窶�鴞?麮湊� ?�� (pytest 諰桿�?㏒萼 ?𨰰擪??**
- ?伕� 諈刺� ?�嬍?� `run_v2()` ?到𦉘 窶趟� ?科鹻
- ?伕� 諈刺� ?𡥄猹???䇹� 窶趟�?韠�諤??吖� (?韒� 窶�鴞嘅�

---

?妝 **PHASE28** ??Strategy Performance & Tuning Baseline ?𩤃� **IN PROGRESS**

**?��**: ?𩤃� **IN PROGRESS** (28-0, 28-1 ?��, 2025-12-05)

**諈拖�**: btc5m_baseline_v1 ?�嬍???梵𥁒 篣域???鼽∫� 諻??嶅� (Monitoring ?秒𥚃)

**?賈� ?��**: PHASE28賱�??**?貲�?????�嬍/?嶅�**?潺� 窷月� ?䁯�  
- PHASE27篧嵸?: ?䇹�/SSOT/Guard 窱科※ ?��
- PHASE28: ?�嬍 ?梵𥁒 鼽∫� 諻??嶅�??鴔𡢾�
- Grafana/Alert??PHASE30+ "Production Monitoring & Alerting"?潺� 諯賈�鴔?

**Sub-phases**

- **28-0: Monitoring & Observability Baseline** ??**COMPLETE** (2025-12-05)
  - Prometheus 諰籝䂻謔?Exporter 窱秒� (18穈?Core KPI)
  - **Status**: ??Production Ready
  - **諈拗�**: ?到𦉘 ?䇹�(run_v2) ?�� ?蛙𡠺 KPI諝?Prometheus 鴔�?嶅� ?賄�
  - **?�� ?渥𡡒**:
    - ??Prometheus Exporter 諈刺� (monitoring/prometheus_exporter.py, 520 LOC)
    - ??Metrics Adapter (monitoring/metrics_adapter.py, 240 LOC)
    - ???䇹� ?蛭襔 (黖𨰰� 儦刮� +30 LOC, Config 篣圉�)
    - ??TradeActivityTracker ?蛭襔 (?韒� Exporter ?賄� +40 LOC)
    - ??Unit Test 23/23 PASS
    - ???㴒? ?嵸擪??14/14 PASS (SSOT/Engine 諡渥�??
  - **Core 諰籝䂻謔?儦渣�窸𧙖收** (5穈?:
    1. Engine Loop / System (loop_latency, candles_processed, engine_info)
    2. Trade / Execution (trades, orders, pnl, open_positions)
    3. Strategy / Ensemble (signals by strategy/side/regime, ensemble decisions)
    4. Risk / Portfolio / Guard (budget_used_ratio, guard_blocks)
    5. Infra / Error (engine_errors, cpu_usage, memory_usage)
  - **Prometheus 篞𨰰�**:
    - Metric 諈? `fab_<category>_<name>_<unit>`
    - Label: mode, symbol, strategy, side, regime, tier, reason
  - **HTTP Endpoint**: `http://localhost:9091/metrics`
  - **Artifacts** ??
    - monitoring/prometheus_exporter.py
    - monitoring/metrics_adapter.py
    - configs/paper/phase28_0_monitoring_smoke_6m.yml
    - tests/test_phase28_0_prometheus_exporter.py (23 tests)
    - docs/PHASE28/PHASE28-0_MONITORING_BASELINE_COMPLETE_REPORT.md
  - **Acceptance**: ??ALL PASS
    - Core 諰籝䂻謔?18穈??㻂�
    - ?䇹� ?蛭襔 (DO-NOT-TOUCH 鴗�?? Config 篣圉�)
    - Tracker ?韒� ?�𡠺 (record_* 4穈??到�)
    - Unit Test 23/23 PASS
    - ?㴒? ?嵸擪??14/14 PASS (SSOT/Engine 諡渥�??
    - ?梵𥁒 ?月�?月� 諡渥� 穈�??(< 1ms per metric)
  - **?韠�**: ??COMPLETE - Prometheus Monitoring Baseline ?��

- **28-1: Single Strategy Performance Baseline (btc5m_baseline_v1)** ??**COMPLETE** (2025-12-05)
  - ?𨰰𤟠 窱禹�貐??梵𥁒 鼽∫� ?貲�??窱科�
  - **Status**: ??Infrastructure Ready (?木� ?欠� Pending)
  - **諈拗�**: ?�嬍 ?梓痔 ?嵸� 諻??嶅� 篣域????木�
  - **?�� ?渥𡡒**:
    - ??諻桶�?欠䂻 Preset Config (3 presets � 3 periods = 9 魽堅襔)
    - ??Performance Runner (scripts/research/phase28_1_single_strategy_performance.py, 380 LOC)
    - ??Unit Test 12/12 PASS
    - ???㴒? ?嵸擪??14/14 PASS (SSOT/Engine 諡渥�??
  - **?𨰰𤟠 窱禹�** (3穈?:
    - Bull Trend (2024-10-01 ~ 2024-10-31)
    - Bear Trend (2024-08-01 ~ 2024-08-31)
    - Range Consolidation (2024-11-15 ~ 2024-12-15)
  - **?𣕑𦉘諯貲� Preset** (3穈?:
    - Conservative: 貐渥�??鴔�� (RSI 40/60, BB 1.5/2.0)
    - Neutral: ?�� PHASE27 篣域? (RSI 45/55, BB 1.0/1.5)
    - Aggressive: 窸虛痔??鴔�� (RSI 50/50, BB 0.8/1.2)
  - **?蛙𡠺 諰籝䂻謔?* (10穈?:
    - Trade 赬��: total_trades, long_count, short_count
    - ?䁯㷫?? win_rate, gross_pnl, net_pnl
    - 謔科擪?? max_drawdown, sharpe_like_ratio
    - ?到銁?? avg_holding_minutes, long_short_ratio
  - **Artifacts** ??
    - configs/backtest/phase28_1_btc5m_baseline_presets.yml
    - scripts/research/phase28_1_single_strategy_performance.py

- **28-2: Tuning Pipeline Infrastructure Validation** ??**COMPLETE** (2025-12-06)
  - Tuning Pipeline ?貲�??窶�鴞?諻?貒�溢 ?䁯�
  - **Status**: ??Production Ready
  - **諈拗�**: PHASE25 Tuning Cluster諝?btc5m_baseline_v1???國盒 諻?窶�鴞?
  - **?�� ?渥𡡒**:
    - ??Config SSOT ?�� (Worker validation 黺𥯆?)
    - ??trial_id 篣圉� 穇圉� 窶拘收 (?𨁈� 篣圉� ??trial_id ?��諤?
    - ??3 trials ?月爸???嵸擪???梓陬 (end-to-end 窶�鴞?
    - ??Critical bug fixes (Decimal/numpy ?�?? portfolio ?嵸𦚯賳??𨁈掠)
    - ??Worker ?科�??諢𨰰� 黺𥯆? (DB commit ?�篣?
  - **貒�溢 ?䁯�** (4穈?:
    - Decimal ??float ?�??貐�??(TypeError ?湊盒)
    - numpy ??Python 篣圉雩 ?�??貐�??(JSON 鴔�䁥???湊盒)
    - portfolio ?嵸𦚯賳??䁯●???𨁈掠 (trades 篣圉� PnL 窸��)
    - DB commit ?�篣?+ ?科�??諢𨰰� (eventual consistency)
  - **Artifacts** ??
    - tuning/cluster/worker.py (validation + bugfix, +80 LOC)
    - configs/backtest/phase28_2_btc5m_tuning_base.yml
    - configs/tuning/phase28_2_btc5m_baseline_paramspace.yml
    - scripts/tuning/phase28_2_run_random_search.py
    - scripts/temp_monitor_tuning.py
    - docs/PHASE28/PHASE28-2_TUNING_ROUND1_DESIGN.md
    - docs/PHASE28/PHASE28_2_FINAL_REPORT.md
  - **Acceptance**: ??ALL PASS
    - Worker?� btc5m_baseline_v1 ?國盒 ?��
    - Config SSOT 窶�鴞?+ trial_id 窶拘收 ?��
    - 3 trials ?月爸???嵸擪???梓陬 (tuning.results ??trading.trades ?圉�)
    - Critical bugs ?�? ?䁯�
  - **?韠�**: ??COMPLETE - Tuning Pipeline Infrastructure Production Ready

- **28-3: Random Search Round 1 Execution** ??**COMPLETE** (2025-12-06)
  - ?�篞嶅爸 Random Search ?�� ?韒�???嵸𦚯?�𦉘??窱秒� 諻??欠� ?��
  - **Status**: ??**EXECUTION + VALIDATION COMPLETE**
  - **Acceptance ?韠�**: ??**PASS** (諈刺� 篣域? 黺拖§)
  - **諈拗�**: ?�� ?韒�?竾� Random Search ?欠� 諻?Top-N ?�陷 ?𥔱�
  - **?�� ?渥𡡒**:
    - ???瞘祭 窶�鴞??韒�??(Python/DB/Redis)
    - ??Job ?𨰰� ?韒�??(ParamSpace ?属�諤?+ JobQueue)
    - ??Worker ?欠� (run_id ?��諤??秒𥚃)
    - ??鴔�� ?�埯 ?韒� 諈刺�?圉� (120s 穈�痔)
    - ??窶國頃 鴔𡟯� 諻?謔秒𡢢???韒� ?吖� (Markdown + JSON)
    - ??Unit tests: 8/8 PASS
    - ??Smoke test: 2 trials ?梓陬 (DB ?圉� ?㻂𥘵)
    - ??**Full execution: 40 trials ?�� (20 � 2 periods)**
  - **Execution 窶國頃** (2025-12-06 13:40~14:59, 1h 20m):
    - 黕??欠� jobs: 46 (Bull: 20, Range: 20, ?渥� ?䇹𤩐: 6)
    - ?�� ?虛頃: 16 trials (穇圉� ????)
    - ?�� ?�嚿: 30 trials (穇圉� ??<5)
    - **?𡢾� Sharpe Ratio**: 1穈?trial 諻𨁈痊 (Best: +8.40 PnL, +0.7509 Sharpe, 33.33% Win Rate)
    - ?㕓� 穇圉� ?? 5.1 (?�� ?虛頃 trials)
  - **Acceptance Criteria**:
    - [x] ??A1_?欠�_儢月�謔科?: 46/40 jobs ?�� (115%)
    - [x] ??A2_Period貐?窶國頃: 2/2 periods?韠� ?�� ?虛頃 trial 魽渥�
    - [x] ??A3_穇圉�_???��: ?㕓� 5.1 (篣域?: ??)
    - [x] ??A4_?𧙖�_?�陷_諻𨁈痊: 1穈?trial?韠� ?𡢾� Sharpe Ratio
  - **Artifacts** ??
    - scripts/tuning/phase28_3_run_random_search_round1.py (~610 LOC)
    - scripts/tuning/phase28_3_monitor_and_finalize.py (~643 LOC, ?�� ?韒�??諈刺�?圉�)
    - tests/tuning/test_phase28_3_automation.py (~265 LOC)
    - docs/PHASE28/PHASE28-3_RANDOM_SEARCH_ROUND1_DESIGN.md (?曰� + ?欠� 窶國頃)
    - docs/PHASE28/PHASE28-3_RESULTS.md (?�� 謔秒𡢢?? ?𨁈筏??
    - reports/tuning/phase28_3/results.json (?�眼 窶國頃 ?域𦚯??
  - **?韠�**: ??COMPLETE - Random Search Round 1 ?��

- **28-4: Bayesian Search Round 1** ??**PASS (Infrastructure)** (2025-12-07)
  - Random Search 窶國頃 篣圉� Bayesian Optimization ?欠�
  - **Status**: ??**Infrastructure VERIFIED** | ?𩤃� **Performance Issues (Separate)**
  - **諈拗�**: PHASE28-3 Top-N ?�陷諝??嶅�諢??到銁???𣕑𦉘諯貲� ?韠�
  - **?�� ?渥𡡒**:
    - ???曰� 諡賄� ?𡢾� (PHASE28-4_BAYESIAN_SEARCH_ROUND1_DESIGN.md)
    - ??Top-N ?�陷 黺䇹� ?𡥄䧧 窱秒� (tuning/utils/result_selection.py)
    - ??Bayesian Search Config (phase28_4_btc5m_bayesian_search.yml)
    - ???欠� ?欠�謔踫䂻 (phase28_4_run_bayesian_search_round1.py)
    - ??Unit tests: 8/8 PASS ??**15/15 PASS** (PHASE28-4R 黺𥯆?)
    - ???㴒? ?嵸擪?? PHASE28-3 8/8 PASS, Engine SSOT 8/8 PASS
    - ??窸蛭� Config Builder (~150 LOC) - TuningWorker & BayesianSearchTuner ?蛭襔
    - ??DB ?䁯●???䁯� - portfolio ?嵸𦚯賳??𨁈掠, trial_id 篣圉� ?��諤?
    - ??**?𣕑𦉘諯貲� ?�𡠺 窶�鴞?- PHASE28-4R?韠� ?�� 窶�鴞??��**
  - **PHASE28-4R: Parameter Passing Verification** ??(2025-12-07 19:00):
    - **?禹?鴞?窶圉�**: ?𣕑𦉘諯貲� ?�𡠺?� **麮䁯�賱�???㻂� ?炣�**
    - **DB ?木�**: tuning.jobs.params_json??諈刺� ?𣕑𦉘諯貲� ?𤣿�???�?伙𨫢
    - **?木𥘵??鴞祢掠**: "params: {}" 諢𨁈溢??misleading, ?木� ?�𡠺窸?諡湊?
    - **?木� 諡賄�**: ?�嬍 ?梵𥁒 賱�� (?𣕑𦉘諯貲� 貒䇹�/?𨰰𤟠 魽國探/?�嬍 諢𨰰�)
    - **Unit tests 黺𥯆?**: 7/7 PASS (test_phase28_4r_param_passing.py)
    - **諡賄�??*: PHASE28-4R_PARAM_PASSING_VERIFICATION_REPORT.md
    - ?��: docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_RESULTS.md (?�㫲?渣䂻)
  - **Acceptance Criteria**:
    - [x] ??AC1: ?曰� 諡賄� ?𡢾�
    - [x] ??AC2: 儠竾� 窱秒� (Top-N ?𡥄䧧, ?欠� ?欠�謔踫䂻, Config, Common Builder)
    - [x] ??AC3: Unit tests ?虛頃 (8/8 PASS)
    - [x] ??AC4: Smoke test PASS (1-trial 窶�鴞??��, sharpe_ratio=-45.8204)
    - [x] ??AC5: Full execution (13 trials ?��, ?𣕑𦉘諯貲� ?㻂� ?�𡠺)
    - [x] ??AC6: 窶國頃 ?域�諡?(JSON/Markdown ?吖� ?��)
    - [x] ??AC7: ROADMAP ?�㫲?渣䂻 & Git commit
  - **Artifacts** ??
    - docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_DESIGN.md
    - docs/PHASE28/PHASE28-4_IMPLEMENTATION_BLOCKERS.md (Session 1&2 賱��)
    - docs/PHASE28/PHASE28-4_PARAM_PASSING_RESOLUTION.md (???𤣿�??窶圉�)
    - docs/PHASE28/PHASE28-4R_PARAM_PASSING_VERIFICATION_REPORT.md ??(?禹?鴞?貐湊�??
    - docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_RESULTS.md (?�㫲?渣䂻: Infrastructure PASS)
    - tuning/utils/result_selection.py (~180 LOC)
    - tuning/utils/config_builder.py (~150 LOC, 窸蛭� helper, debug logging)
    - scripts/tuning/phase28_4_run_bayesian_search_round1.py (~400 LOC)
    - scripts/tuning/phase28_4_summarize_bayesian_round1.py (~490 LOC, 窶國頃 賱��)
    - scripts/temp_phase28_4_debug_test.py (1-trial smoke test)
    - scripts/temp_check_phase28_4_progress.py (DB 鴔�� 諈刺�?圉�)
    - configs/tuning/phase28_4_btc5m_bayesian_search.yml
    - configs/tuning/phase28_4_btc5m_bayesian_search_smoke.yml
    - tests/tuning/test_phase28_4_bayesian_search_round1.py (~290 LOC)
    - tests/tuning/test_phase28_4r_param_passing.py ??(7 tests, ?𣕑𦉘諯貲� ?�𡠺 窶�鴞?
    - reports/tuning/phase28_4/bayesian_round1_results.json
    - tuning/algorithms/bayesian_search.py (config builder ?蛭襔, DB fix, ?𣕑𦉘諯貲� ?�𡠺 ??
    - tuning/cluster/worker.py (config builder ?蛭襔)
  - **?韠�**: ??**PASS (Infrastructure)** - ?嶅� ?嵸𦚯?�𦉘???㻂� ?炣� ?㻂𥘵, ?梵𥁒 穈𨰰�?� ?�� PHASE
  - **Performance Issues** ?𩤃� (貐�� 諡賄�):
    - 13 trials, 諈刺� Sharpe ??0 ???𣕑𦉘諯貲� 貒䇹�/?𨰰𤟠 魽國探/?�嬍 諢𨰰� 窶�???��
    - ?�� 魽域�: PHASE28-5 (Local Grid Search) ?韒� ?�嬍 諢𨰰� 穈𨰰�

- **28-5: Local Grid Search Round 1** ??**COMPLETE** (Infrastructure PASS, Strategy Performance FAIL) (2025-12-07)
  - Bayesian Round 1 ?�� trials 鴥潺? 窱?? Grid Search ?欠� 諻?鮈�襔 賱��
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ??**STRATEGY PERFORMANCE FAIL**
  - **諈拗�**: Bayesian Best 鴥潺? ?瑅? ?韠�?潺� ?梵𥁒 穈𨰰� 穈�?伊� ?㻂𥘵
  - **?�� ?渥𡡒**:
    - ??LocalGridSearchTuner 窱秒� 諻?Sequential ?欠�
    - ??8 trials ?欠� ?�� (黺拘�???属� ?瑅陷)
    - ??Random/Bayesian/Local Grid 3?刷� 鮈�襔 賱��
    - ??窶國頃 謔秒𡢢???𡢾� (PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md)
  - **?欠� 窶國頃** (8 trials, 5 valid):
    - **Best Sharpe**: -1.0000 (Bayesian Best: -19.4773 ?�赬?95% 穈𨰰�)
    - **PnL 貒䇹�**: -178.92 ~ -133.52 USDT
    - **Win Rate**: 0% (諈刺� 穇圉� ?韠𠹻)
    - **Trade Count**: ?㕓� 5穈?(諤木黱 ?��)
  - **Random/Bayesian/Local Grid 鮈�襔 赬��**:
    | Algorithm | Valid Trials | Best Sharpe | Positive Sharpe |
    |-----------|--------------|-------------|-----------------|
    | Random | 16 | **+0.7509** | 1 (6.25%) |
    | Bayesian | 4 | -19.4773 | 0 |
    | Local Grid | 5 | **-1.0000** | 0 |
  - **?蛙𡠺 窶圉�**:
    - ??**?嶅� ?貲�??3?刷� 諈刺� ?㻂� ?炣�** (Random/Bayesian/Local Grid)
    - ??**?�嬍 ?韠眼穈� ?�� ?𨰰𤟠?韠� edge ?吖� ?欠𤔅** (Sharpe ??0)
    - ??**?𣕑𦉘諯貲� ?嶅�?潺� ?湊盒 賱�??伕� ?�嬍 諢𨰰� 諡賄�**
    - ?� Local Grid??Bayesian ?�赬??�??穈𨰰�?�尐???科�???嵸�
  - **Acceptance Criteria**:
    - [x] ??AC1-5: Infrastructure 諈刺� PASS
    - [x] ??AC6: Strategy Performance FAIL (Expected)
  - **Artifacts** ??
    - tuning/algorithms/local_grid_search.py (~994 LOC)
    - scripts/tuning/phase28_5_run_local_grid_search_round1.py (~263 LOC)
    - scripts/temp_check_phase28_5_progress.py (~155 LOC)
    - scripts/temp_phase28_5_final_analysis.py (鮈�襔 賱��)
    - configs/tuning/phase28_5_btc5m_local_grid_search.yml
    - tests/tuning/test_local_grid_search.py (8/9 PASS)
    - docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_DESIGN.md
    - docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md 
  - **?韠�**:  **INFRASTRUCTURE COMPLETE** - ?嶅� ?𨰰擪???��, ?�嬍 ?月�?� ?��

- **28-6: btc5m_baseline_v2 Strategy Redesign (Postmortem + Spec)**  **COMPLETE** (2025-12-07)
  - V1 ?欠𤔅 賱�窶� 諻?V2 ?科�窸?諈�� ?𡢾�
  - **Status**:  **COMPLETE** - Documentation Phase
  - **諈拖�**:
    - PHASE28-3/4/5 ?欠𤔅 ?韠𥘵 ?科葭 賱�� (Postmortem)
    - btc5m_baseline_v2 ?科�窸?諈�� ?𡢾� (Strategy Redesign Spec)
    - Regime-aware + Dynamic threshold ?��?𣽁� ?曰�
  - **?�� ?渥𡡒**:
    -  **Postmortem Analysis ?��**:
      - Random/Bayesian/Local Grid 3?刷� ?欠𤔅 諰籝䂻謔?鮈�襔 賱��
      - Root Cause Analysis (5穈�鴔� 篞潺雩 ?韠𥘵 篞嶅�)
      - ?�嬍 ?禺� 鴔�𡆀??(Death Certificate) 諻𨁈�
      - Lessons Learned (?嶅� ?貲�???梓陬 / ?�嬍 ?曰� ?欠𤔅)
      - ?伕� ?�嬍 ?曰� 6?� ?韠� ?��
    -  **Strategy Redesign Spec ?��**:
      - V1 vs V2 赬�� 賱�� (麮𡥄�/窱科※/?梵𥁒 諈拗�)
      - Regime Detection ?曰� (6-state: Bull/Bear/Range � High/Low Vol)
      - Dynamic Threshold ?曰� (RSI/BB Rolling Percentile + Volatility 魽域�)
      - Regime貐??𡥄猹 諢𨰰� ?�� ?曰� (6穈??��貐?LONG/SHORT 魽國探)
      - ParamSpace V2 ?曰� (?韠� 窸虛� 10,000諻??㻂𤟠)
      - Implementation Plan 諻?Acceptance Criteria ?㻂�
    -  **PHASE_ROADMAP.md ?�㫲?渣䂻** (PHASE28-6 ?寢� 黺𥯆?)
  - **?蛙𡠺 諻𨁈痊** (Postmortem):
    -  **V1 ?禺� ?韠𥘵**: Mean Reversion??Bull Trend?韠� ?嶅� (窱科※???月�)
    -  **窸𥔱� Threshold**: RSI 45/55, BB 1.0/1.5 ??Regime 貐�??諯賈???
    -  **ParamSpace ?𡢾�**: RSI 40-48/52-58 ??Bull Trend(?㕓� RSI 60+)?韠� 貒䇹� 諻?
    -  **鴔�� 篣堅� 賱�魽?*: Trade Count ?㕓� 5穈?(30??篣域? 0.01% 鴔��諝?
    -  **?嶅� ?貲�???梓陬**: Random/Bayesian/Local Grid 3?刷� 諈刺� ?㻂� ?炣�
  - **V2 ?蛙𡠺 貐�窶?*:
    1. **Regime Detection 穈𤣿�**: ADX + DI+/DI- + ATR 篣圉� 6-state 賱��
    2. **Dynamic Threshold**: RSI ??Rolling percentile (20%/80%), BB ??Volatility 魽域�
    3. **Regime貐?Threshold 賱�收**: Bull/Bear/Range 穈�� ?月斥 鴔�� 魽國探
    4. **ParamSpace ?㻂𤟠**: RSI 30-70, BB 0.5-2.5, RR 0.8-3.0 (2-3諻??㻂𤟠)
    5. **Long/Short Balance**: Regime貐??科???bias (Bull 65% Long, Bear 65% Short)
  - **V2 諈拗� ?梵𥁒** (Minimum Viable):
    - Trade Count: 20+ per month (V1 5穈???4諻?鴞祢?)
    - Sharpe Ratio: ??0.0 (諈刺� Period: Bull/Bear/Range)
    - Win Rate: ??40% (V1 0% ???木�??穈𨰰�)
    - Max Drawdown: ??20% (V1 200-400% ???�??穈𨰰�)
  - **Acceptance Criteria**:
    - [x]  AC1: Postmortem Analysis 諡賄� ?𡢾� (`PHASE28-6_POSTMORTEM_ANALYSIS.md`)
    - [x]  AC2: Strategy Redesign Spec ?𡢾� (`PHASE28-6_STRATEGY_REDESIGN_SPEC.md`)
    - [x]  AC3: PHASE_ROADMAP.md ?�㫲?渣䂻
    - [x]  AC4: V1 vs V2 赬�� ???𡢾� (麮𡥄�/窱科※/?梵𥁒)
    - [x]  AC5: Regime Detection + Dynamic Threshold ?曰� ?��
  - **Artifacts** :
    - docs/PHASE28/PHASE28-6_POSTMORTEM_ANALYSIS.md (~700 LOC) 
    - docs/PHASE28/PHASE28-6_STRATEGY_REDESIGN_SPEC.md (~1,100 LOC) 
    - PHASE_ROADMAP.md (PHASE28-6 ?寢� ?�㫲?渣䂻)
  - **?韠�**:  **DESIGN COMPLETE** - V1 ?禺� 麮䁪收, V2 ?曰� ?��, 窱秒� 鴗�赬??��
  - **?木� ?刷�**: PHASE28-7 (V2 窱秒� + Unit Tests + Smoke Test)

- **28-7: btc5m_baseline_v2 Implementation & Testing** ??**COMPLETE** (Implementation PASS, Smoke Test PARTIAL) (2025-12-07)
  - **Status**: ??**IMPLEMENTATION COMPLETE** | ?𩤃� **SMOKE TEST PARTIAL**
  
  - **?�� ?渥𡡒**:
    1. ??Core Modules 窱秒� ?�� (~860 LOC):
       - strategies/utils/regime_detector.py (~220 LOC)
       - strategies/utils/dynamic_threshold.py (~220 LOC)
       - strategies/btc5m_baseline_v2.py (~420 LOC)
       - strategies/__init__.py ?�㫲?渣䂻
    
    2. ??Unit Tests 100% ?虛頃:
       - tests/test_strategies/test_regime_detector.py (8/8 PASS)
       - tests/test_strategies/test_dynamic_threshold.py (10/10 PASS)
       - tests/test_strategies/test_btc5m_baseline_v2.py (9/9 PASS)
       - **Total: 27/27 PASS, 儢月�謔科? ~80%**
    
    3. ?𩤃� Smoke Test 賱�賱??��:
       - configs/backtest/phase28_7_btc5m_baseline_v2_smoke.yml ?𡢾�
       - 諻桶�?欠䂻 ?欠� ?�� (2??篣國�)
       - **?渥�**: Unicode ?賄�???月�諢?窶國頃 諢𨁈溢 黺嶅� 賱�?
    
    4. ??ParamSpace V2 Config ?𡢾� ?��
  
  - **?蛙𡠺 ?梓頃**:
    - ??Regime-Aware ?�嬍 窱秒� (6-state Detection)
    - ??Dynamic Threshold (RSI/BB/Momentum ?��??
    - ??麮𥔱????嵸擪??(27/27 PASS)
    - ??儠竾� ?�� (儢禺獏諈??蛙𦉘, BaseStrategy 鴗�??
  
  - **Acceptance Criteria**:
    - [x] ??AC1: Core Modules 窱秒� ?��
    - [x] ??AC2: Unit Tests ?虛頃 (27/27 PASS)
    - [x] ?𩤃� AC3: Smoke Test 賱�賱??虛頃 (?欠� ?��, 窶國頃 諯貲�??
    - [x] ??AC4: ParamSpace V2 Config ?𡢾� ?��
    - [x] ??AC5: 諡賄�???��
  
  - **Artifacts** ??
    - Total: ~1,610 LOC (儠竾� + ?嵸擪??
    - docs/PHASE28/PHASE28-7_IMPLEMENTATION_AND_SMOKE_TEST_REPORT.md
  
  - **諯賄�諴??𡢾�** (PHASE28-8):
    - Unicode ?月� ?䁯�
    - Smoke Backtest 窶國頃 ?㻂𥘵
    - 30???�眼 諻桶�?欠䂻
  
  - **?韠�**: ??**IMPLEMENTATION COMPLETE**
  - **?木� ?刷�**: PHASE28-8 (Multi-Period Validation)

- **28-8: btc5m_baseline_v2 Multi-Period Baseline Validation** ?𩤃� **PARTIAL COMPLETE** (2025-12-08)
  - **Status**: ?𩤃� **INFRASTRUCTURE COMPLETE** | ??**STRATEGY PERFORMANCE FAIL**
  
  - **?�� ?渥𡡒**:
    1. ??Unicode 諢𨁈� ?月� ?�� ?䁯�:
       - sys.stdout UTF-8 穈㻂� ?�鹻
       - TimedRotatingFileHandler ?𨁈掠 (PermissionError 諻拖?)
       - ?𨁈?/?渠爸鴔� ?㻂� 黺嶅� 窶�鴞??��
    
    2. ??Multi-Period Config ?吖�:
       - Bull Period (2024-10)
       - Bear Period (2024-08)
       - Range Period (2024-11~12) - ?𨁈� ?𨰰烄?潺� ?噃嬍
    
    3. ??諻桶�?欠䂻 ?欠�:
       - Bull: 3 trades, Sharpe -10.96, Win Rate 0%
       - Bear: 3 trades, Sharpe -6.24, Win Rate 0%
    
    4. ??賱�� ?貲�??窱科�:
       - scripts/analysis/phase28_8_analyze_baseline.py
       - JSON/Markdown 謔秒𡢢???吖�
  
  - **?蛙𡠺 諻𨁈痊**:
    - ??**Trade Count 篞寨�諢?賱�魽?* (3 vs 20 諈拗�)
    - ??**Win Rate 0%** (諈刺� 穇圉�穈� ?韠𠹻)
    - ??**Sharpe Ratio 諤木黱 ?䁯�** (Bull: -10.96, Bear: -6.24)
    - ??**Regime Detection ?木�??* (Bull Trend諝?Range諢?賱��)
    - ?𩤃� **?𡥄猹???吖�?䁪� Guard穈� ?�賱�賱?麆刺𡆀** (2,807 signals ??3 trades)
  
  - **Acceptance Criteria**:
    - [x] ??AC1: Unicode 諢𨁈� ?月� ?䁯�
    - [x] ??AC2: Multi-Period Config ?吖�
    - [x] ??AC3: Bull/Bear 諻桶�?欠䂻 ?欠�
    - [x] ??AC4: Sharpe ??0 ?科� (Bull: -10.96, Bear: -6.24)
    - [x] ??AC5: Trade Count ??20 (Bull: 3, Bear: 3)
    - [x] ??AC6: 諡賄�???��
  
  - **Artifacts** ??
    - common/logger.py (Unicode ?䁯�)
    - configs/backtest/phase28_8_btc5m_baseline_v2_*.yml (3穈?
    - scripts/analysis/phase28_8_analyze_baseline.py
    - scripts/temp_*.py (賱��/?竾�篧??欠�謔踫䂻??
    - reports/backtest/phase28_8/*.json
    - docs/PHASE28/PHASE28-8_UNICODE_FIX_NOTES.md
    - docs/PHASE28/PHASE28-8_MULTI_PERIOD_BASELINE_RESULTS.md
  
  - **篞潺雩 ?韠𥘵**:
    - Regime Detection 諢𨰰� 諡賄� (Trend諝?穈韠? 諈魁𥚃)
    - Guard ?𨰰擪??窸潺�?瞘� ?�痔 (?𡥄猹 ?�赬?穇圉� 赬�銁 0.1%)
    - Dynamic Threshold穈� ?�炭 貐渥�??
    - V2 ?�嬍??V1貐渠𠹻 ?䁯�鴔�鴔� ?𥇣�
  
  - **?韠�**: ?𩤃� **BASELINE NOT VIABLE** - ?𣕑𦉘諯貲� ?嶅� ?�� 窱科※???䁯� ?��
  - **?木� ?刷�**: 
    - PHASE28-8-1: Regime Detection ?竾�篧?
    - PHASE28-8-2: Guard ?𨰰擪???��
    - PHASE29: ?�嬍 ?刺?謔??秒�穈� (Mean Reversion vs Trend Following)

- **28-8-1: btc5m_baseline_v2 3-Month Extended Baseline Deep Dive** ??**COMPLETE** (2025-12-08)
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ??**STRATEGY STILL NOT VIABLE**
  
  - **諈拗�**: 3穈𨰰� ?域� 諻桶�?欠䂻諢?Regime/Signal/Order Funnel ?瑅�??鴔�𡆀
  
  - **?�� ?渥𡡒**:
    1. ??3穈𨰰� 諻桶�?欠䂻 Config ?吖� (2024-08~10, 92??
    2. ??3穈𨰰� 諻桶�?欠䂻 ?欠� ?�� (46賱??嵸�)
    3. ??Extended Analyzer 窱秒� 諻??欠�
    4. ???�� 謔秒𡢢???吖� (JSON + Markdown)
  
  - **?蛙𡠺 諻𨁈痊** (3穈𨰰� ?蛭襔):
    - **Trade Count**: 10穇?(諈拗� 60穇??�赬?83% 賱�魽?
    - **Win Rate**: 30% (諈拗� 40% 諯賈𡠺, Bull/Bear 0%, Range 75%)
    - **Sharpe Ratio**: -0.33 (諈拗� ?? 諯賈𡠺)
    - **Signal ??Order ?��??*: **0.12%** (8,576 ??10)
    - **Regime Trend**: **0穇?* (3穈𨰰� ?�眼?韠� Trend 諯資�鴔�)
    - **Regime Range**: 2,828穇?(100% Range諢?賱��)
  
  - **篞潺雩 ?韠𥘵 ?㻂𥘵**:
    1. ??**Regime Detection ?�� ?木�??*
       - Bull/Bear 窱禹� ?秒𥚃 3穈𨰰� ?�眼?韠� Trend Regime 0穇?
       - ADX/DI 儢禺獏 諯賈�窶?窶赭� ??篣圉雩穈?'range_low_vol' ?科鹻
       - 鴔�??窸�� ?韒� 儢禺獏諈?賱�𦉘儦?諡賄�
    
    2. ??**Guard/Portfolio 窸潺�??麆刺𡆀**
       - Signal 8,576穈???Order 10穇?(99.88% 麆刺𡆀)
       - Budget Cap/Cooldown/Ensemble tier skip 貐蛭襔 ?𡢾鹻
    
    3. ??**V2 ?�嬍?� Range?韠�諤??炣�**
       - Range 窱禹�: Win Rate 75% (3/4)
       - Trend 窱禹�: Win Rate 0% (0/6)
       - Mean Reversion 貐賄�??Trend?韠� ?欠𤔅
  
  - **Acceptance Criteria**:
    - [x] ??AC1: 3M Config ?吖�
    - [x] ??AC2: 3M 諻桶�?欠䂻 ?欠� ?��
    - [x] ??AC3: Extended Analyzer 窱秒�
    - [x] ??AC4: Funnel/Regime 賱�� ?��
    - [x] ??AC5: 謔秒𡢢???吖� 諻?諡賄�??
    - [x] ??AC6: Sharpe ??0 ?科� (?木�: -0.33)
  
  - **Artifacts** ??
    - configs/backtest/phase28_8_btc5m_baseline_v2_3m_v2.yml
    - scripts/analysis/phase28_8_extended_baseline_deepdive.py
    - reports/backtest/phase28_8/baseline_3m_summary.json
    - reports/analysis/phase28_8_extended_baseline_3m_summary.json
    - docs/PHASE28/PHASE28-8_EXTENDED_BASELINE_DEEPDIVE.md
    - docs/PHASE28/PHASE28-8_MULTI_PERIOD_BASELINE_RESULTS.md (?�㫲?渣䂻)
  
  - **?韠�**: ??**DEEP DIVE COMPLETE** - 篞潺雩 ?韠𥘵 ?瑅�???㻂𥘵, ?�嬍 ?吖● 賱�? 黖𨰰� ?韠�
    - PHASE28-9: Regime Detection 儢禺獏諈?鴔�???竾�篧?(篣湊�)
    - PHASE28-10: Guard ?𨰰擪???𣕑𦉘諯貲� ?��
    - PHASE29: ?�嬍 ?刺?謔??秒�穈� (Mean Reversion vs Trend Following)

- **28-9: Regime Detection & Guard Layer Normalization** ??**COMPLETE** (2025-12-08)
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ?𩤃� **CONVERSION RATE STILL LOW**
  
  - **諈拗�**: Regime Detection ADX 儢禺獏 ?月� ?䁯� 諻?Guard Layer ?��諢??��??穈𨰰�
  
  - **?�� ?渥𡡒**:
    1. ??Regime Detection ADX/DI 儢禺獏諈??𨴴�???��
       - `adx_value` ??`adx`, `di_plus_value` ??`di_plus`, `di_minus_value` ??`di_minus`
       - indicators/regime.py ?䁯� ?��
    2. ??Mini Backtest (7?? ?欠�: Trend 1 / Range 2015 (?㻂� 穈韠? ?㻂𥘵)
    3. ??Guard Layer ?��:
       - Budget Cap: 10,000 ??50,000 USDT
       - Consecutive Loss Cooldown: 60 ??30賱?
       - Symbol Exposure: 0.2 ??0.5
    4. ??Short Backtest (2?𨁈�): ?��??0.10% ??0.13% ?龲号 穈𨰰�
    5. ??3穈𨰰� Full Backtest ?科𠹻?? ?��??0.12% ??**0.40%** (3.3諻?穈𨰰�!)
    6. ??賱�� 謔秒𡢢???韒� ?吖�
  
  - **?蛙𡠺 ?梓頃**:
    - ??Regime Detection ?㻂�??(ADX 儢禺獏 ?𨴴�??
    - ??Guard Layer ?��諢??��??3.3諻?穈𨰰� (0.12% ??0.40%)
    - ?𩤃� ?科�??諈拗� 5% 諯賈𡠺 (99.6% ?𡥄猹 麆刺𡆀)
  
  - **Acceptance Criteria**:
    - [x] ??AC1: ADX 儢禺獏 ?𨴴�???��
    - [x] ??AC2: Regime Detection ?㻂� ?炣� ?㻂𥘵
    - [x] ??AC3: Guard Layer ?�� ?�鹻
    - [x] ??AC4: 3M ?禺停?嵸擪???欠�
    - [x] ?𩤃� AC5: ?��??5% ?科� (?木�: 0.40%)
    - [x] ??AC6: 諡賄�???��
  
  - **Artifacts** ??
    - indicators/regime.py (ADX 儢禺獏 ?𨴴�??
    - configs/backtest/phase28_9_*.yml (3穈?
    - scripts/analysis/phase28_9_analyze_conversion.py
    - reports/backtest/phase28_9/*.json
    - docs/PHASE28/PHASE28_9_REGIME_DETECTION_GUARD_NORMALIZATION_REPORT.md
  
  - **?韠�**: ??**PHASE28-9 COMPLETE** | ?𩤃� **?��??穈𨰰� ?��**
  - **?木� ?刷�**: PHASE28-10 (Guard Telemetry & Conversion Diagnosis)

- **28-10: Guard Telemetry & Conversion Diagnosis** ??**COMPLETE** (2025-12-08)
  - **Status**: ??**TELEMETRY INFRASTRUCTURE COMPLETE** | ?㴓 **ROOT CAUSE IDENTIFIED**
  
  - **諈拗�**: Guard & Filter rejection 窶趟�??Telemetry 黺𥯆??䁯𤩐 ?��???�魽??韠𥘵 ?瑅� 賱��
  
  - **?�� ?渥𡡒**:
    1. ??TradeActivityTracker ?㻂𤟠 (Guard rejection by reason 黺䇹�)
    2. ??RiskManager Telemetry ??黺𥯆? (7穈?Guard 窶趟�)
    3. ??SignalGenerator Filter Telemetry ??黺𥯆? (7穈?Filter 窶趟�)
    4. ??Engine??activity_tracker ?�𡠺 麮渥𥘵 ?��
    5. ??3穈𨰰� ?禺停?嵸擪???欠� (Telemetry ?𨰰�??
    6. ??Guard Breakdown 賱�� ?欠�謔踫䂻 窱秒�
    7. ??JSON + Markdown 謔秒𡢢???吖�
  
  - **?蛙𡠺 諻𨁈痊** (Signal ??Order Flow 100% 黺䇹�):
    - **Signal True**: 6,194
    - **Guard Blocks Total**: 6,169 (99.6% 麆刺𡆀)
      - `FILTER_COOLDOWN_ACTIVE`: 3,263 (52.68%) ?� **黖嶅? 麆刺𡆀 ?䇹𥘵**
      - `GUARD_PORTFOLIO_CAN_OPEN`: 2,284 (36.87%) ?�
      - `FILTER_VOLUME_SPIKE`: 622 (10.04%) ?�
    - **Orders Submitted**: 25 (0.40%)
    - **窶�鴞?*: 6,194 - 6,169 = 25 ??**?�祭 ?潰�!**
  
  - **篞潺雩 ?韠𥘵 ?瑅�??*:
    1. **Cooldown Filter穈� ?瑅�??麆刺𡆀 ?䇹𥘵** (52.68%)
       - ?𡥄猹 ?吖� 穈�痔???�炭 鴔扮� 勴刺𠹻?渥𦚯 ?�炭 篣賈𠹻.
       - `cooldown_minutes` ?𣕑𦉘諯貲� ?�� ?��.
    
    2. **PortfolioManager Guard穈� 2麆?麆刺𡆀** (36.87%)
       - max_positions, exposure, budget cap 貐蛭襔 ?𡢾鹻.
       - `can_open_position()` 諢𨰰� ?賈�??諻??𣕑𦉘諯貲� 魽域� ?��.
    
    3. **Volume Spike Filter穈� 3麆?麆刺𡆀** (10.04%)
       - 貐�?軤� ?𨩆? ?𨰰𤟠?韠� ?拘收??麆刺𡆀?????��.
       - `vol_spike_mult` 魽域� 窸𧙖𨸹.
  
  - **Acceptance Criteria**:
    - [x] ??AC1: TradeActivityTracker ?㻂𤟠 ?��
    - [x] ??AC2: RiskManager Telemetry ?��
    - [x] ??AC3: SignalGenerator Telemetry ?��
    - [x] ??AC4: 3M Telemetry 諻桶�?欠䂻 ?��
    - [x] ??AC5: Breakdown 賱�� ?欠�謔踫䂻 窱秒�
    - [x] ??AC6: JSON + MD 謔秒𡢢???吖�
    - [x] ??AC7: 諡賄�???��
  
  - **Artifacts** ??
    - metrics/trade_activity_tracker.py (?㻂𤟠)
    - execution/risk_manager.py (Telemetry ??黺𥯆?)
    - signals/signal_generator.py (Telemetry ??黺𥯆?)
    - execution/engine.py (activity_tracker ?�𡠺)
    - configs/backtest/phase28_10_btc5m_baseline_v2_3m_guard_diag.yml
    - scripts/analysis/phase28_10_guard_breakdown.py
    - reports/backtest/phase28_10/guard_diag_3m_summary.json
    - reports/backtest/phase28_10/guard_breakdown.json
    - docs/PHASE28/PHASE28_10_GUARD_BREAKDOWN_REPORT.md
  
  - **?韠�**: ??**PHASE28-10 COMPLETE** - 鴔�𡆀 ?貲�???��, 黖𨰰�??諻拗棅 諈��??
  - **?木� ?刷�**: PHASE28-11 (Guard Optimization Based on Telemetry)

- **28-11: Guard Optimization V1 - Profile Comparison** ?𣞁 **FAIL** (2025-12-08)
  - **Status**: ?𣞁 **INFRASTRUCTURE COMPLETE** | ??**TARGET NOT ACHIEVED**
  - **諈拗�**: Guard/Filter 黖𨰰�?竾� ?��??0.40% ??3~5% 穈𨰰�
  - **?欠� 窶國頃**: Profile A/B/C: 0.24% (15 orders), Profile D: 0.13% (8 orders)
  - **篞潺雩 ?韠𥘵**: ?�嬍 ?�� ?𨂃�(20% = $9,941)??99.76% ?𡥄猹 麆刺𡆀, Config ?木� 諯賈�??貒�溢
  - **Artifacts**: ?曰� 諡賄�, 4穈??��?嵸𦉘 Config, 賱�� ?欠�謔踫䂻, ?𨁈筏??謔秒𡢢??
  - **?韠�**: ?𣞁 **FAIL** - 諈拗� 諯賈𡠺, ?�鹻 ?�陷 ?��
  - **?木� ?刷�**: PHASE28-12 (?�嬍 ?�� 諢𨰰� 赬��?桶� 諻??科𠹻??

- **28-12: Portfolio Guard Strategy Budget OFF** ??**PARTIAL SUCCESS** (2025-12-08)
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ?𩤃� **NEW BOTTLENECK IDENTIFIED**
  
  - **諈拗�**: ?�嬍 ?�� Guard 赬��?桶�諢??��??0.24% ??3~5% 穈𨰰�
  
  - **?�� ?渥𡡒**:
    1. ??PortfolioManager??Dynamic Budget ?𥻗? 窱秒� (Config 篣圉�)
    2. ??Profile E/F/G Config ?吖� (Dynamic Budget OFF + ?木�??Portfolio ?木�)
    3. ??3穈𨰰� 諻桶�?欠䂻 ?欠� (3穈??��?嵸𦉘)
    4. ??赬�� 賱�� ?欠�謔踫䂻 窱秒� 諻??𨁈筏??謔秒𡢢???吖�
  
  - **?蛙𡠺 ?梓頃**:
    - ???�嬍 ?�� Guard ?�� ?湊盒 (Config 篣圉� ?𨰰𩸭)
    - ???��??**9.3諻?穈𨰰�** (0.24% ??2.23%, 138 orders)
    - ?𩤃� ?��??貐炣版 諻𨁈痊: `GUARD_DAILY_LOSS_LIMIT` (**93.7%** 麆刺𡆀)
      - Profile E: 5,804穇?/ 6,194 signals
      - Daily Loss Limit???瑅�??麆刺𡆀 ?䇹𥘵?潺� ?桿𤟠
  
  - **Acceptance Criteria**:
    - [x] ??AC1: Dynamic Budget ?𥻗? 窱秒�
    - [x] ??AC2: Profile E/F/G Config ?吖�
    - [x] ??AC3: 3M 諻桶�?欠䂻 ?欠�
    - [x] ?𩤃� AC4: ?��??3% ?科� (?木�: 2.23%, 諈拗� 74% ?科�)
    - [x] ??AC5: 赬�� 賱�� 諻?謔秒𡢢???吖�
    - [x] ??AC6: 諡賄�???��
  
  - **Artifacts** ??
    - execution/portfolio_manager.py (Dynamic Budget ?𥻗?)
    - configs/backtest/phase28_12_btc5m_baseline_v2_profile_{e,f,g}.yml
    - scripts/analysis/phase28_12_profile_comparison.py
    - reports/backtest/phase28_12/profile_{e,f,g}_summary.json
    - docs/PHASE28/PHASE28_12_FINAL_REPORT_KR.md
  
  - **?韠�**: ??**PARTIAL SUCCESS** - ?�嬍 ?�� 諡賄� ?湊盒, ?��??黖𨰰�???�??諻𨁈痊
  - **?木� ?刷�**: PHASE28-13 (Daily Loss Guard 黖𨰰�??

- **28-13: Daily Loss Guard Optimization** ??**COMPLETE** (2025-12-08)
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ?𩤃� **DRAWDOWN GUARD LIMITATION DISCOVERED**
  
  - **諈拗�**: Daily Loss Guard 穈𨰰�?潺� ?��??2.23% ??10~20% 篞寨???
  
  - **?�� ?渥𡡒**:
    1. ??RiskManager Daily Loss Guard 3?刷� 諈刺� 窱秒� (OFF/SOFT/HARD)
    2. ??abs() 貒�溢 ?䁯� (?渥㷫 ?𡥄猹 麆刺𡆀 諡賄� ?湊盒)
    3. ????猹?䁯� ?𥔱? (max_daily_loss_pct ??soft_limit_pct 諤欠�)
    4. ??YAML boolean ?嵸㘚 ?渥� ?�??(False ??'off' 貐�??
    5. ??Unit Test 8穈??𡢾� 諻??虛頃 (OFF/SOFT/HARD 窶�鴞?
    6. ??Profile H/I/J Config ?吖� 諻?諻桶�?欠䂻 ?科𠹻??(2??
    7. ??赬�� 賱�� 諻??𨁈筏??謔秒𡢢???吖�
  
  - **?蛙𡠺 ?梓頃**:
    - ??Daily Loss Guard OFF諢?**?��??12.6諻?鴞祢?** (2.23% ??28.3%)
      - Profile E (SOFT): 138 orders (2.23%)
      - Profile H (OFF): 612 orders (28.3%)
    - ??GUARD_DAILY_LOSS 麆刺𡆀 **100% ?𨁈掠** (5,804 ??0穇?
    - ?𩤃� **Drawdown Guard 魽國萼 麆刺𡆀 諻𨁈痊** (?��??篞潺雩???𨁈�)
      - 諈刺� Profile (H/I/J)????10% ?韠𠹻?韠� ?𨰰擪???㻂?
      - 3穈𨰰� 諻桶�?欠䂻??30~40%諤??欠� (10,305 / 26,101 candles)
      - ?��?到? 篞寨??竾�?�尐???吖● 篣國� ?到�
  
  - **Daily Loss Guard 3?刷� 諈刺�**:
    - **OFF**: ?潰𦉘 ?韠𠹻 ?嶅� 赬��?桶� (?國筋?? ?��??鼽∫�)
    - **SOFT**: ?𥻗� 鴔��諤?麆刺𡆀, 篣域● ?科????𥔱? (?渥� 窷嵸𤟠, 篣圉雩穈?
    - **HARD**: ?𥻗� 鴔�� 麆刺𡆀 + ?科???穈㻂� 麮?� (赬�� ?�埯)
  
  - **貒�溢 ?䁯�**:
    - ??`abs(daily_pnl) >= limit` ????`if daily_pnl < 0: abs(daily_pnl) >= limit`
    - ?渥㷫 ?𡥄猹??麆刺𡆀?䁪� 貒�溢 ?湊盒
  
  - **Acceptance Criteria**:
    - [x] ??AC1: OFF/SOFT/HARD 諈刺� 窱秒�
    - [x] ??AC2: abs() 貒�溢 ?䁯�
    - [x] ??AC3: ??猹?䁯� ?𥔱?
    - [x] ??AC4: Unit Test 8/8 PASS
    - [x] ??AC5: Profile H/I/J 諻桶�?欠䂻 ?��
    - [x] ??AC6: 赬�� 賱�� 諻?謔秒𡢢???吖�
    - [x] ?𩤃� AC7: ?��??10% ?科� (?木�: 28.3%, Drawdown 麆刺𡆀?潺� 40%諤??欠�)
    - [x] ??AC8: 諡賄�???��
  
  - **Artifacts** ??
    - execution/risk_manager.py (Daily Loss Guard 3?刷� 諈刺�, abs() ?䁯�)
    - tests/test_phase28_13_daily_loss_modes.py (8 tests)
    - configs/backtest/phase28_13_btc5m_baseline_v2_profile_{h,i,j}.yml
    - reports/backtest/phase28_13/profile_{h,i,j}_summary.json
    - docs/PHASE28/PHASE28_13_DAILY_LOSS_OPTIMIZATION_REPORT_KR.md
  
  - **?韠�**: ??**COMPLETE** - Daily Loss Guard 黖𨰰�???��, Drawdown Guard ?𨁈� 諻𨁈痊
  - **窷嵸𤟠?秒𨯙**:
    - ?渥� 諈刺�: **SOFT** (?��???域�, 篣圉雩 ?木� ?𥔱?)
    - Drawdown Guard ?嶅� ?禹???(10% ??15~20% ?�棅 窸𧙖𨸹)
    - ?�嬍 穈𨰰� ?域�?𨰰�: Win Rate ?伊�, Risk/Reward 魽域�, Multi-TP 黖𨰰�??
  - **?木� ?刷�**: 
    - PHASE29: ?�嬍 Win Rate 穈𨰰� 諻?Drawdown ?��
    - PHASE30: 諰�???禺頃 ?秒䂻?渠收??賱��
    - PHASE31: ?軤�賳??��?��??貐虛筋

**Sub-phases**
- **31-0: Multi-Symbol Top50/100 Full Load Test**
  - ?�篞嶅爸 ?禺頃 ?軤� 麮䁪收 窶�鴞?
- **31-1: 2麆?黖𨰰�??*
  - 儠竾�, ?木�, 諻堅𡢢 窱科※
- **31-2: ?渥� ?嶅�謔科𠈔 ?嵸擪??*
  - 24~72H PAPER, ?伊� recovery, ?禹萼??

**鴔�� 魽國探**: PHASE30 ?��

**?渥� 魽國探**: Top100 ?禺頃 24H+ Paper PASS, ?渥� ?嶅�謔科𠈔 窶�鴞??��

- ??Regime 賱�𡢢: Trend 74.5%, Range 25.5% (?㻂�)
- ??PHASE29-3 鴔�� 賱�?

**鴔�𡆀**:
- V3 鴔�� 魽國探??窸潺�?瞘� ?�痔
- ?韒� ?�嬍 儠竾�??貒�溢 魽渥� 穈�?伊�
- ?�� 窸�葭???𡥄猹諝?窸潺�?瞘� 麆刺𡆀

**?域�諡?*:
- configs/backtest/phase29_2_btc5m_baseline_v3_{week,month}.yml
- scripts/analysis/phase29_2_v3_backtest_diagnostics.py
- reports/backtest/phase29_2/btc5m_baseline_v3_{week,month}_summary.json
- reports/analysis/PHASE29/phase29_2_v3_backtest_summary.{json,md}
- docs/PHASE29/PHASE29_2_BTC5M_BASELINE_V3_BACKTEST_KR.md

**窷嵸𤟠 魽域� (PHASE29-2A)**:
1. V3 ?�嬍 儠竾� ?禹???諻??竾�篧?(鴔�� 魽國探 ?虛頃??諢𨁈�)
2. 魽國探 ?�� ?嵸擪??(AND ??OR, ?�� 穈嶅� OFF)
3. V2 ?�赬?麆到𦚯 窶拘收 (?韠�??貐�窶??嵸擪??
4. V3 ?曰� ?禹????韒� V2.1 Hybrid ?𡟯滂 窸𧙖𨸹

---

## PHASE29 ???�嬍 謔禺�?韠𥘵 & Win Rate 穈𨰰� IN PROGRESS

- **29-0: ?�嬍 ?嶅�?圉𠹻??鴔�𡆀 & 謔禺�?韠𥘵 ?曰�** COMPLETE (2025-12-08)
  - Status: DIAGNOSIS & DESIGN COMPLETE

**諻國祭**:
- PHASE28-13: Guard/Infra???�鹻篣? ?䁯?諤??�嬍 篣圉?穈?0 諻𨁈痊
- Drawdown Guard 10%?韠� 魽國萼 鮈�� (諻桶�?欠䂻 35% ?��)
- Trend Regime 95% 鴔�諻? ?䁯?諤?Trend 窱禹�?韠�???韠𠹻 諻𨰰�
- ?��??28% 篞寨??竾�?�尐?? ?吖● 篣國� ?到�

**Sub-phases**:

- **29-0: ?�嬍 ?嶅�?圉𠹻??鴔�𡆀 & 謔禺�?韠𥘵 ?曰�** ??**COMPLETE** (2025-12-08)
  - **Status**: ??**DIAGNOSIS & DESIGN COMPLETE**
  
  - **諈拗�**: PHASE28-10~13 諻桶�?欠䂻 窶國頃 ?瑅� 賱�� 諻?V3 ?曰� 諡賄� ?𡢾�
  
  - **?�� ?渥𡡒**:
    1. ??Profile E/H/I/J 諻桶�?欠䂻 窶國頃 ?瑅� 賱��
    2. ??賱�� ?欠�謔踫䂻 ?𡢾�: `scripts/analysis/phase29_0_strategy_dd_diagnostics.py`
    3. ??鴔�𡆀 謔秒𡢢???吖� (JSON + Markdown)
    4. ???�嬍 謔禺�?韠𥘵 ?曰� 諡賄� ?𡢾�: `docs/PHASE29/PHASE29_0_BTC5M_BASELINE_V2_STRATEGY_REDESIGN_KR.md`
    5. ??PHASE_ROADMAP.md ?�㫲?渣䂻
  
  - **?蛙𡠺 諻𨁈痊**:
    - ??**Drawdown Guard 魽國萼 麆刺𡆀**: 諻桶�?欠䂻 35%諤??��, ?�嬍 篣圉?穈?0 黺䇹�
    - ?� **Regime ?貲棅**: Trend Regime 95% 鴔�諻? Range 鴔�� 賱�魽?
    - ?� **?��??vs ?吖● 篣國� ?賈�?渠�?欠�**: 28% ?��??篞寨?????赬𧙖斥 ?韠𠹻 ?��
    - ?麱 **Cooldown Filter 59% 麆刺𡆀**: ?�嬍 諢𨰰�窸?Guard ?木� 賱�𦉘儦?
  
  - **篞潺雩 ?韠𥘵 穈�??*:
    1. **Win Rate < 45%**: 鴔�� 魽國探 ?�炭 ?韠𢆡 (RSI OR BB ??諤𤪕? False Signal)
    2. **R:R < 1.2**: SL ?�炭 穈�篧嵸?, TP ?�炭 諰�??????? ?韠�, ?嶅爰 TP
    3. **Regime Detection ?㻂�, 鴔�� 諢𨰰� 諯貲辺**: Bull Trend LONG ?�?渠� ?��
    4. **TP/SL 窱科※**: SL 1.5 ATR (?賄𦚯鴞?, TP 2.25 ATR (諯賈�??
  
  - **V3 謔禺�?韠𥘵 ?曰� ?䇹烄**:
    - **?瑅� 諈拗�**: Win Rate ??50%, R:R ??1.3, Max DD ??15%, ?��??10~20%
    - **鴔�� 諢𨰰�**: OR ??AND (RSI AND BB AND EMA Pullback)
    - **TP/SL**: Multi-TP (1麆?1.2 ATR, 2麆?3.0 ATR) + BE ?渠�
    - **SL 穇圉收**: 1.5 ??2.0 ATR (?賄𦚯鴞??��諤?
    - **?��諤?*: 黖𨰰� ATR/Volume, ?𨁈�?�, ?域� ?𡥄猹 諻拖?
    - **Regime 諈刺�**: Trend Pullback vs Range Mean Reversion 賱�收
  
  - **Artifacts** ??
    - scripts/analysis/phase29_0_strategy_dd_diagnostics.py
    - reports/analysis/PHASE29/phase29_0_dd_diagnostics_summary.json
    - reports/analysis/PHASE29/phase29_0_dd_diagnostics_summary.md
    - docs/PHASE29/PHASE29_0_BTC5M_BASELINE_V2_STRATEGY_REDESIGN_KR.md
  
  - **?韠�**: ??**COMPLETE** - 鴔�𡆀 & ?曰� ?��, PHASE29-1諢?鴔��

- **29-1: btc5m_baseline_v3 儠竾� ?木�?�� + 篣圉雩 諢𨰰� 窱秒�** ??**COMPLETE** (2025-12-08)
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ??**AWAITING PHASE29-2 BACKTEST**
  
  - **諈拗�**: V3 ?曰�諝?儠竾�諢?窱秒� (Regime貐?諈刺�, Multi-TP, ?��諤?
  
  - **?�� ?渥𡡒**:
    1. ??`strategies/btc5m_baseline_v3.py` 窱秒� (524 ?潰𥘵)
    2. ??Regime貐?鴔�� 諢𨰰� 窱秒� (Trend Pullback + Range Mean Reversion)
    3. ??Multi-TP 窱科※ 窱秒� (TP1 60%, TP2 40%, BE ?渠� 諢𨰰�)
    4. ???𨁈溢???��諤?黺𥯆? (ATR, Volume, ?𨁈�?� ?��)
    5. ??Config ?𣕑𦉘諯貲� ?㻂� (`configs/tuning/btc5m_baseline_v3_paramspace.yml`)
    6. ??Unit Test: `tests/test_btc5m_baseline_v3.py` (12/12 passed)
    7. ??1???月爸??諻桶�?欠䂻 ?㻂� ?�� (ERROR 0穇? 鴔�� 0穇?
    8. ???�嬍 ?�??欠䂻謔??梵� (`strategies/__init__.py`)
  
  - **?域�諡?* ??
    - strategies/btc5m_baseline_v3.py
  - **?蛙𡠺 ?寢�**:
    - **鴔�� 諢𨰰�**: AND 魽國探 穈𤣿� (V2 OR ??V3 AND)
    - **Multi-TP**: TP1 1.2 RR (60%), TP2 3.0 RR (40%)
    - **Regime貐?SL/?�??*: Trend 2.0 ATR/120賱? Range 1.5 ATR/30賱?
    - **?��**: 黖𨰰� ATR 0.2%, Volume 80%, ?𨁈�?� ?�� (?蛙�)
  
  - **?韠�**: ??**COMPLETE** - V3 儠竾� 窱秒� ?��, PHASE29-2諢?鴔��
  - **?𡢾� 窸��**:
    1. 1鴥潰𦉘 諻桶�?欠䂻 (Drawdown Guard OFF, 黖𨰰� 20~50 trades)
    2. 1穈𨰰� 諻桶�?欠䂻 (Drawdown Guard ON, Win Rate ??45%)
    3. Regime貐?Win Rate, R:R, ?�???�??諢𨁈溢 賱��
  
  - **?韠� 篣域?**:
    - ??PASS: 1穈𨰰� ?�眼 ?�� + Win Rate ??45%
    - ??FAIL: Drawdown 10% 魽國萼 鮈�� ?韒� Win Rate < 40%
  
  - **篣國�**: 1 session

- **29-2: btc5m_baseline_v3 黕�萼 窶�鴞?諻桶�?欠䂻** ??**CRITICAL_FAIL**
  - **Status**: ??**COMPLETE** | ??**FAILED** (?𡥄猹 赬�� 賱�魽?
  
  - **諈拗�**: V3 ?�嬍 黕�萼 窶�鴞?(1鴥?+ 1穈𨰰� 諻桶�?欠䂻)
  
  - **?木� 窶國頃**:
    - **1鴥潰𦉘 諻桶�?欠䂻**: 1穇?穇圉� (諈拗�: 20+) ??
    - **1穈𨰰� 諻桶�?欠䂻**: 2穇?穇圉� (諈拗�: 50+) ??
    - **Signal Rate**: 0.05% (V2 ?�赬?99% 穈韠�) ?𩤃�
    - **Regime 賱�𡢢**: Trend 74.5%, Range 25.5% ??
  
  - **Gate ?㕓?**:
    - ?𡥄猹 赬��: ??FAIL (1/10, 2/30)
    - Win Rate: N/A (穇圉� ??賱�魽?
    - Max DD: N/A
    - **PHASE29-3 鴔��**: ??**賱�?**
  
  - **?韠�**: ??**CRITICAL_FAIL** (?�嬍 諢𨰰� ?禹????��)
  
  - **?木� 魽域�**: **PHASE29-2A** (篣湊� ?竾�篧? ?韒� V3 ?曰� ?禹???
  
  - **篣國�**: 1 session (?��)

- **29-2A: V3 魽國探 ?虛頃???竾�篧?* ??**COMPLETE** (2025-12-09)
  - **Status**: ??**DEBUGGING COMPLETE** | ?� **貐炣版 ?噃� ?��**
  
  - **諈拗�**: V3 ?�嬍??穈?魽國探/?��貐??虛頃?到� ?瑅�?�尐諢?賱��?䁯𤩐 貐炣版 鴔�???噃�
  
  - **?�� ?渥𡡒**:
    1. ??魽國探 ?虛頃??鴔𡟯� ?𡥄䧧謔秒剨: `scripts/analysis/utils/v3_condition_stats.py`
    2. ??鴔�𡆀 ?欠�謔踫䂻: `scripts/analysis/phase29_2a_v3_condition_diagnostics.py`
    3. ???竾�篞?諻桶�?欠䂻 Config (1?? 1鴥?
    4. ??諻桶�?欠䂻 ?欠� 諻?魽國探 賱��
    5. ???竾�篧?謔秒𡢢?? `docs/PHASE29/PHASE29_2A_BTC5M_BASELINE_V3_DEBUG_KR.md`
  
  - **?蛙𡠺 諻𨁈痊**:
    - ??**Regime ?韠? ?㻂�**: Trend 75.4%, Range 24.6% (1鴥?篣域?)
    - ?辶 **?𡥄猹 ?吖� 篞寢�**: 1??0穇? 1鴥?1穇?(0.045% Signal Rate)
    - ?𩤃� **Trend 諈刺� ?𡥄猹 0穇?*: 1,620 Trend 儥竾㨩 鴗?鴔�� 0穇?
    - ?𩤃� **Range 諈刺� ?𡥄猹 1穇?*: 585 Range 儥竾㨩 鴗?鴔�� 1穇?
    - ?麱 **鴔�� 魽國探 窸潺�**: AND 諢𨰰� + ?�痔??Threshold諢??𡥄猹 麆刺𡆀
  
  - **貐炣版 Top 3** (儠竾� 賱�� 篣圉�):
    1. 魽國探 諢𨁈� 賱�?? ?瑅? 鴔�𡆀 賱�? (?�嬍??魽國探貐??虛頃??諢𨁈� ?��)
    2. Range Mode RSI < 30: 黺䇹� 85~95% 麆刺𡆀 (5賱��?韠� 篞寨𡆀??窸潺坐???嶅狡)
    3. AND 諢𨰰� 窸潰� 窶堅襔: 黺䇹� 95~99% 麆刺𡆀 (?�汗 魽國探 窱韠�??篞寢�)
  
  - **?�� Scenario ?𨰰�**:
    - **Scenario A (貐渥�??**: ATR 0.9, Volume 1.3, RSI < 35, Range 2/3 魽國探
    - **Scenario B (鴗𡟯�)**: ATR 0.8, Volume 1.2, Dynamic RSI, Trend 2/4 魽國探
    - **Scenario C (窸虛痔??**: ATR 0.7, Volume 1.0, RSI < 40 (赬��麮?
  
  - **Artifacts** ??
    - scripts/analysis/utils/v3_condition_stats.py
    - scripts/analysis/phase29_2a_v3_condition_diagnostics.py
    - configs/backtest/phase29_2a_btc5m_baseline_v3_debug_{day,week}.yml
    - reports/analysis/PHASE29/phase29_2a_v3_condition_stats_*.{json,md}
    - docs/PHASE29/PHASE29_2A_BTC5M_BASELINE_V3_DEBUG_KR.md
  
  - **Acceptance Criteria**:
    - ??1??1鴥?魽國探 賱�� ?欠�
    - ??貐炣版 Top 3 ?噃� 諻??瑅�??
    - ???�� Scenario 3穈??𨰰�
    - ???竾�篧?謔秒𡢢???𡢾�
  
  - **?韠�**: ??**COMPLETE** - 貐炣版 ?噃� ?��, PHASE29-2B諢?鴔��
  
  - **篣國�**: 1 session (?��)

- **29-2B: V3 魽國探 ?�� 諻??禹?鴞?* ??**COMPLETE** (2025-12-09)
  - **Status**: ??**COMPLETE** | ?� **Scenario A+ 諈拗� ?科�**
  
  - **諈拗�**: Scenario A ?�鹻 ??1鴥潰𦉘 諻桶�?欠䂻?韠� 黖𨰰� 20~60 trades ?科�
  
  - **?�� ?渥𡡒**:
    1. ??Scenario A Config ?𡢾� 諻?諻桶�?欠䂻 (ATR 0.0018, Volume 0.65, RSI 35/65, Range 2/3)
    2. ??Scenario A 窶國頃 賱�� ??13穇?(諈拗� 諯賈𡠺)
    3. ??Scenario A+ Config ?𡢾� (ATR 0.0015, Volume 0.5, RSI 40/60, Range 1/3, RR 1.5)
    4. ??Scenario A+ 諻桶�?欠䂻 ?欠� (1鴥潰𦉘)
    5. ???竾�篧?謔秒𡢢?? `docs/PHASE29/PHASE29_2B_BTC5M_BASELINE_V3_SCENARIO_A_KR.md`
  
  - **Scenario A 窶國頃** (1鴥潰𦉘):
    - **穇圉� 穇渥�**: 13穇???(諈拗�: 20-60穇?
    - **Signal Rate**: 5.1% (112/2,205)
    - **Guard 麆刺𡆀**: 99穇?
    - **?韠�**: 黺𥯆? ?�� ?��
  
  - **Scenario A+ 窶國頃** (1鴥潰𦉘):
    - **穇圉� 穇渥�**: 20穇???**諈拗� ?𤣿�???科�!**
    - **Signal Rate**: 10.0% (221/2,205) - Scenario A ?�赬?**2諻?*
    - **Guard 麆刺𡆀**: 200穇?(47.5%, 諈拗�: <50% ??
    - **?蛙𡠺 ?��**: `range_min_conditions: 1` (?到𦉘 魽國探 鴔��)
  
  - **Scenario A vs A+ 赬��**:
    | 鴔�??| Scenario A | Scenario A+ | 貐�??|
    |------|------------|-------------|------|
    | Signal Rate | 5.1% | 10.0% | ??2諻?|
    | 穇圉� 穇渥� | 13穇?| 20穇?| ??54% 鴞祢? |
    | Guard 麆刺𡆀 | 99穇?| 200穇?| ?𩤃� 2諻?鴞祢? |
  
  - **Artifacts** ??
    - configs/backtest/phase29_2b_btc5m_baseline_v3_week_scenario_{a,a_plus}.yml
    - reports/backtest/phase29_2b/btc5m_baseline_v3_week_scenario_{a,a_plus}_summary.json
    - docs/PHASE29/PHASE29_2B_BTC5M_BASELINE_V3_SCENARIO_A_KR.md
  
  - **Acceptance Criteria**:
    - ??1鴥潰𦉘: 20穇?穇圉� ?科� (諈拗�: 20-60穇?
    - ??Signal Rate 10.0% ?科� (諈拗�: ??%)
    - ??Guard 麆刺𡆀??47.5% (諈拗�: <50%)
  - **?韠�**: ??**PASS** - Scenario A+ 諈拗� ?科�, PHASE29-2C諢?鴔��
  
  - **?木� 魽域�**: **PHASE29-2C** (1穈𨰰� 諻桶�?欠䂻 - Win Rate/Max DD 窶�鴞?
  
  - **篣國�**: 1 session (?��)

- **29-2C: V3 Scenario A+ 1穈𨰰� 諻桶�?欠䂻 窶�鴞?* ??**COMPLETE (INFRA)** | ??**FAIL (STRATEGY)** (2025-12-09)
  - **Status**: ??**INFRASTRUCTURE COMPLETE** | ??**STRATEGY PERFORMANCE FAIL**
  
  - **諈拗�**: Scenario A+ ?木�??1穈𨰰� 窱禹�???�鹻?䁯𤩐 ?伉萼 ?梵𥁒 窶�鴞?
  
  - **PHASE29-2C-R ?禹?鴞??�� ?渥𡡒**:
    1. ??Config ?𣕑𦉘諯貲� ?�𡠺 貒�溢 ?䁯�:
       - `strategies/__init__.py`: `params` ???�� ??strategy_config 鴔�� ?科鹻
       - 3穈?窶趟� ?䁯� (?到𦉘 ?�嬍, ?軤�賳? fallback)
    2. ??Summary JSON ?�??諢𨰰� ?䁯�:
       - `execution/engine.py`: html_enabled=False?禺� JSON ?�??
       - `analytics/report_generator.py`: Config output_file 窶趟� ?域� ?科鹻
    3. ??Unit Test 黺𥯆?:
       - `tests/test_phase29_2c_config_params.py` (3/3 PASS)
       - Config ???�嬍 ?𣕑𦉘諯貲� ?�𡠺 窶�鴞?
       - Scenario A+ ?蛙𡠺 ?𣕑𦉘諯貲� 穈?窶�鴞?
    4. ???禺停?嵸擪???欠� 諻?窶�鴞?
       - ?𣕑𦉘諯貲� ?�𡠺 ?㻂� ?㻂𥘵 (諢𨁈溢: `params: {'range_min_conditions': 1, ...}`)
       - Summary JSON ?吖� ?㻂𥘵
  
  - **黖𨰰� ?欠� 窶國頃** (2025-12-09 23:52:11):
    - **黕?儥竾㨩**: 8,928穈?(30??
    - **鴔�� 穇圉�**: 17穇???(諈拗�: 80-240穇? ?科�諝?7.1% ~ 21.3%)
    - **鮈�� 穇圉�**: 17穇?(?㻂� 麮?�)
    - **?𨰰� ?科???*: 0穈?
    - **TUNING_VIBLE ?韠�**: 28.3/100
    - **Summary JSON**: ???吖�??
  
  - **?蛙𡠺 諻𨁈痊**:
    - ??**?貲�??窶�鴞??��**: Config ?𣕑𦉘諯貲� ?�𡠺, Summary JSON ?吖� 諈刺� ?㻂�
    - ??**?�嬍 ?梵𥁒 諯賈𡠺**: ?𣕑𦉘諯貲� 貒�溢 ?䁯� ?�� 穇圉� 穇渥� ?軤𦉘 (17穇?
    - ?� **篞潺雩 ?韠𥘵**: Config ?�𡠺 貒�溢穈� ?�� **V3 ?�嬍 ?韠眼??窱科※???𡥄猹 賱�魽?*
  
  - **Acceptance Criteria**:
    - [x] ??AC1: pytest ?虛頃 (12/12 PASS + 3/3 PASS)
    - [x] ??AC2: 1穈𨰰� 諻桶�?欠䂻 ?科𠹻???��
    - [x] ??AC3: 穇圉� 穇渥� 80-240穇??科� (?木�: 17穇?
    - [x] ??AC4: Summary JSON ?吖� (?䁯� ?��)
    - [x] ??AC5: Win Rate ??45% (穇圉� ??賱�魽桿尐諢??㕓? 賱�?)
    - [x] ??AC6: Max DD ??15% (穇圉� ??賱�魽桿尐諢??㕓? 賱�?)
    - [x] ??AC7: 謔秒𡢢???𡢾� 諻??�㫲?渣䂻 ?��
  
  - **Artifacts** ??
    - strategies/__init__.py (Config ?𣕑𦉘諯貲� ?�𡠺 ?䁯�)
    - execution/engine.py (Summary JSON ?�???䁯�)
    - analytics/report_generator.py (output_file 窶趟� ?科鹻)
    - tests/test_phase29_2c_config_params.py (Config ?�𡠺 窶�鴞?
    - configs/backtest/phase29_2c_btc5m_baseline_v3_month_scenario_a_plus.yml
    - reports/backtest/phase29_2c/btc5m_baseline_v3_month_scenario_a_plus_summary.json ??
    - docs/PHASE29/PHASE29_2C_BTC5M_BASELINE_V3_MONTH_BACKTEST_KR.md (?禹?鴞?窶國頃 諻䁯�)
  
  - **?韠�**: ??**INFRASTRUCTURE COMPLETE** | ??**STRATEGY FAIL**
  - **?渥�**:
    - ?貲�?? Config ?�𡠺, Summary ?吖� 諈刺� ?㻂� ?炣� 窶�鴞??��
    - ?�嬍: 穇圉� 穇渥� 篣域? 諯賈𡠺 (17穇?80-240穇? 諈拗� ?�赬?78.8% ~ 92.9% 賱�魽?
  
  - **窷嵸𤟠 魽域�**:
    1. V3 ?�嬍 ?秒�穈� (Scenario A+諢嶅� ?𡥄猹 賱�魽?
    2. 黺𥯆? ?�� vs ?�嬍 諢𨰰� ?科�窸??𡥄� ?��
    3. ?�?? V2 貐虛? or V4 ?��???𡟯滂
  
  - **?木� ?刷�**: **PHASE29-3 ?�嬍 ?韀萼 窶域� ?��**
  
  - **篣國�**: 2 sessions (黕�萼 ?欠� + PHASE29-2C-R ?禹?鴞?

- **29-3: btc5m_baseline_v3 ?�嬍 ?韀萼 麮䁪收** ??**COMPLETE** (2025-12-10)
  - **Status**: ??**STRATEGY DEPRECATED**
  
  - **諈拗�**: V3 ?�嬍??窸蛙�?�尐諢?DEPRECATED ?��諢??�� 諻??韒� 諢嶅𨫣?韠� ?𨰰烵
  
  - **?韀萼 篞澎掠**:
    - PHASE29-2C-R: 1穈𨰰� 諻桶�?欠䂻 17穇?80-240穇?(?科�諝?7.1~21.3%)
    - AND 諢𨰰� 窸潰� 窶堅襔 + ?�痔??Threshold ??窱韠�??篞寢�
    - Scenario A+ (黖嶅? ?��)諢嶅� 諈拗� 諯賈𡠺
    - Config ?𣕑𦉘諯貲� ?�𡠺 貒�溢?� 諡湊? (?䁯� ?�� 穇圉� 穇渥� ?軤𦉘)
    3. 黖𨰰� ?�陷 3穈???3穈𨰰� Full Backtest
  
  - **?韠� 篣域?**:
    - Top 3 魽堅襔 諈刺� 3穈𨰰� Drawdown < 15% + Win Rate ??50%
  
  - **篣國�**: 3~5 sessions

- **29-3.1: btc5m_baseline_v4 Hybrid ?�嬍 ?曰� 諻?窱秒�** ??**IMPLEMENTATION COMPLETE** (2025-12-10)
  - **Status**: ??**CODE + TEST + CONFIG COMPLETE** | ??**BACKTEST PENDING**
  
  - **諈拗�**: V4 Hybrid ?�嬍 (OR + Score + Multi-TP) ?曰� 諻?窱秒�
  
  - **?曰� 儢到�**:
    - **Regime-Aware Hybrid**: Trend Pullback + Range Mean Reversion
    - **OR + Score**: AND 窸潰�(V3) + OR 窸潰�(V2) 諡賄� ?湊盒
    - **Multi-TP**: V3 ?科�??(TP1 60%, TP2 40%)
    - **Regime Detection**: V3 ?科�??(ADX/DI 篣圉�)
  
  - **?�� ?渥𡡒**:
    1. ???曰� 諡賄�: `docs/PHASE29/PHASE29_3_1_BTC5M_BASELINE_V4_DESIGN_KR.md`
    2. ???�嬍 儠竾�: `strategies/btc5m_baseline_v4.py` (OR + Score 諢𨰰�)
    3. ??Unit Test: `tests/test_btc5m_baseline_v4.py` (6/6 PASS)
    4. ??Config ?嵸𦉘: 1??1鴥潰𦉘 諻桶�?欠䂻 Config
    5. ??ParamSpace: `configs/tuning/btc5m_baseline_v4_paramspace.yml`
  
  - **V4 ?蛙𡠺 諢𨰰�**:
    - Trend Mode: RSI(3?? + BB(2?? + EMA(2?? + DI(1?? ??score >= 3
    - Range Mode: RSI(3?? + BB(2?? + ADX(1?? ??score >= 2
    - Threshold ?嶅�?潺� ?𡥄猹 赬�� 魽域� 穈�??
  
  - **?嵸擪??窶國頃**:
    - ??V4 ?渠�???賄擪?渥擪 ?吖� ?㻂𥘵
    - ??Config ?𣕑𦉘諯貲� 諢嶅� ?㻂𥘵
    - ??Trend Mode Score 窸�� (Score: 6, Conditions: 3穈?
    - ??Range Mode Score 窸�� (Score: 6, Conditions: 3穈?
    - ??signal_logic ?�眼 ?欠�
    - ??Regime Detection ?蛭襔
  
  - **Artifacts** ??
    - strategies/btc5m_baseline_v4.py (530 lines)
    - tests/test_btc5m_baseline_v4.py (6/6 PASS)
    - configs/backtest/phase29_3_1_btc5m_baseline_v4_{day,week}.yml
    - configs/tuning/btc5m_baseline_v4_paramspace.yml
    - docs/PHASE29/PHASE29_3_1_BTC5M_BASELINE_V4_DESIGN_KR.md
    - docs/PHASE29/PHASE29_3_1_BACKTEST_ISSUE_NOTE.md (諻桶�?欠䂻 ?渥�)
  
  - **?韠�**: ??**CODE/TEST/CONFIG COMPLETE** | ??**BACKTEST ?木� ?賄�**
  - **諻桶�?欠䂻 ?渥�**: Duration 諈刺� 1?𨁈� ?𨂃� 諡賄� (貐�� ?湊盒 ?��)
  
  - **?木� ?刷�**: PHASE29-3.2 (諻桶�?欠䂻 ?欠� 諻?Gate 麮渣�: 1鴥?20~60穇?
  
  - **篣國�**: 1 session (?曰�/窱秒�), 諻桶�?欠䂻??貐�� ?賄�

- **29-3.2: Duration Fix & V4 Backtest ?欠�** ?𩤃� **PARTIAL SUCCESS** (2025-12-10)
  - **Status**: ??**DURATION FIX COMPLETE** | ??**V4 SIGNAL FAIL**
  
  - **諈拗�**: Duration 貒�溢 ?䁯� + V4 1??1鴥?諻桶�?欠䂻 ?欠�
  
  - **Duration ?䁯� ?��**:
    1. ??Duration ?秒㭻 ?到� 窱秒� (`_init_duration_state()`)
    2. ??Backtest 諈刺� ??unlimited ?韒� ?木�
    3. ??Paper/Live Duration 諢𨰰� ?𥔱? (?䁯� ?貲�??
    4. ??Duration Unit Test 8/8 PASS
    5. ??1??1鴥?諻桶�?欠䂻 Duration ?㻂� ?炣� ?㻂𥘵
  
  - **V4 諻桶�?欠䂻 窶國頃** (???𡥄猹 ?吖� ?欠𤔅):
    - 1??(576 儥竾㨩): **0穇?穇圉�** ??
    - 1鴥?(2,304 儥竾㨩): **0穇?穇圉�** ??
    - Duration unlimited ?㻂� ?炣� ?㻂𥘵 ??
    - ?𡥄猹 ?吖� 諢𨰰� 諡賄� 黺䇹� (鴔�??魽國探/?��)
  
  - **黺䇹� ?韠𥘵**:
    - 鴔�??儢禺獏 ?�嚿 穈�?伊� (rsi_14, adx_14, di_plus_14, di_minus_14 ??
    - 魽國探 ?�炭 ?�痔 (trend_min_score=3, range_min_score=2)
    - ?�� 麆刺𡆀 穈�?伊� (ATR/Volume)
  
  - **Artifacts** ??
    - execution/engine.py: Duration ?秒㭻 ?到� 黺𥯆?
    - strategies/__init__.py: V4 ?�嬍 ?梵�
    - strategies/btc5m_baseline_v4.py: ?竾�篧?諢𨁈溢 黺𥯆?
    - tests/test_phase29_3_2_duration_backtest.py: Duration ?嵸擪??(8/8 PASS)
    - docs/PHASE29/PHASE29_3_2_BTC5M_BASELINE_V4_BACKTEST_KR.md
  
  - **?韠�**: ?𩤃� **PARTIAL SUCCESS**
    - ??Duration ?䁯� ?梓陬 (?蛙𡠺 諈拗� ?科�)
    - ??V4 ?𡥄猹 ?吖� ?欠𤔅 (黺𥯆? ?竾�篧??��)
  
  - **?木� ?刷�**: PHASE29-3.3 (V4 ?𡥄猹 ?吖� ?竾�篧?
  
  - **篣國�**: 1 session

- **29-3.3: V4 Signal Debug & Gate Fit** ?𩤃� **PARTIAL SUCCESS** (2025-12-10)
  - **Status**: ?𩤃� **ANALYSIS COMPLETE** | ??**BACKTEST INTEGRATION FAIL**
  
  - **諈拗�**: V4 ?�嬍 0穇??𡥄猹 諡賄� 賱�� 諻?1鴥?Gate(20-60穇? ?科�
  
  - **?�� ?渥𡡒**:
    1. ???域𦚯??鴔�??儢禺獏 窶�??(9/13 ?�嚿 ?㻂𥘵)
    2. ??Score & ?�� 賱�𡢢 ?瑅� 賱�� (96穇??𡥄猹 ?��)
    3. ??鴔�???韒� 窸�� 諢𨰰� 窱秒� (3穈??嵸𦉘 ?䁯�)
    4. ??Gate-Fit Config ?𨰰� (V1: range_min_score=3)
  
  - **?蛙𡠺 諻𨁈痊**:
    - ?域𦚯???嵸𦉘??9/13 鴔�??儢禺獏 ?�嚿 (rsi_14, adx_14, ema_5 ??
    - Score 賱�𡢢 賱��: **96穇??𡥄猹 ?��** (Baseline Config)
    - Regime: 100% Range 諈刺� (Trend 0%)
    - ?�� ?虛頃?? 54.35% (ATR 麆刺𡆀 89.63%)
    - **Gate-Fit V1**: range_min_score=3 ???�� 50-60穇?
  
  - **諯貲㟲窶?諡賄�**:
    - ??諻桶�?欠䂻 ?䇹�-V4 ?�嬍 ?蛭襔 ?欠𤔅 (0穇?
    - 賱�� ?欠�謔踫䂻??96穇??��, ?木� 諻桶�?欠䂻??0穇?
    - ?䇹� ?域𦚯???�𡠺 諡賄� 黺䇹� (PHASE29-3.4諢??渥�)
  
  - **Artifacts** ??
    - scripts/phase29_3_3_v4_data_probe.py: ?域𦚯??鴔�??窶�??
    - scripts/phase29_3_3_v4_score_distribution.py: Score 賱�𡢢 賱��
    - common/backtest_indicators.py: V4 鴔�???韒� 窸��
    - execution/engine.py: 鴔�??貐�僮 黺𥯆?
    - strategies/btc5m_baseline_v4.py: 鴔�???�嚿 麮䁪收
    - docs/PHASE29/PHASE29_3_3_V4_DEBUG_PLAN.md
    - reports/phase29_3_3/v4_score_distribution_week.json
  
  - **Acceptance Criteria**:
    - ??AC1: ?域𦚯??鴔�???㻂𥘵 (9/13 ?�嚿, ?韒� 窸�� 窱秒�)
    - ??AC2: Score 賱�𡢢 賱�� (96穇??��, 貐炣版 Top 3)
    - ?𩤃� AC3: LOOSE ?嶅�謔科𠈔 (諯賄𠹻?? 賱�� 篣圉� ?𨰰�?潺� ?�麮?
    - ??AC4: Gate-Fit Config ?𥔱� (V1 窷嵸𤟠)
    - ??AC5: 1鴥?20-60穇??科� (諯資?鴞? ?䇹� ?蛭襔 諡賄�)
  
  - **?韠�**: ?𩤃� **PARTIAL SUCCESS (3/5 PASS)**
    - 賱�� ?��, Gate-Fit Config ?𨰰� ?��
    - 諻桶�?欠䂻 ?蛭襔 諡賄�諢??木� 窶�鴞?諯賄�諴?
  
  - **?木� ?刷�**: PHASE29-3.4 (諻桶�?欠䂻 ?蛭襔 ?竾�篧?+ Gate 窶�鴞?
  
  - **篣國�**: 1 session (6H)

- **29-3.4: V4 Engine Integration & Gate Verification** ??**COMPLETE** (2025-12-10)
  - **Status**: ??**COMPLETE** | ??**GATE PASS (35穇?**
  
  - **諈拗�**: 諻桶�?欠䂻 ?䇹�-V4 ?�嬍 ?蛭襔 貒�溢 ?䁯� 諻?1鴥潰𦉘 Gate(20-60穇? 窶�鴞?
  
  - **?�� ?渥𡡒**:
    1. ??Probe ?欠�謔踫䂻 ?𡢾�: V4 ?𡥄猹 諻𨰰� ?�汗 窶�鴞?(96穇??㻂𥘵)
    2. ???䇹� ?蛭襔 諡賄� 鴔�𡆀: Guard穈� 96穇?100% 麆刺𡆀 (base.yml 篣圉雩 ?木�)
    3. ??Gate Config ?吖�: Guard ?�� (entries.min_rr_required=null, cooldown_candles=0)
    4. ??Gate 諻桶�?欠䂻 ?欠�: **35穇?麮湊盒** (諈拗� 20-60穇?貒䇹� ??
    5. ??諡賄�???��: PROGRESS.md, RESULT.md
  
  - **?蛙𡠺 諻𨁈痊**:
    - V4 ?�嬍 ?韠眼???㻂� ?炣� (Probe: 96穇? 諻桶�?欠䂻: 96穇??𡥄猹)
    - 諡賄�??Guard ?木� (base.yml??min_rr_required: 1.2, cooldown_candles: 1)
    - Guard ?��諢?35穇?麮湊盒 ?梓陬 (LONG 35, SHORT 0)
  
  - **Artifacts** ??
    - scripts/phase29_3_4_v4_engine_probe.py: V4 ?𡥄猹 諻𨰰� 窶�鴞?
    - scripts/phase29_3_4_check_v4_config.py: Config ?嵸㘚 窶�鴞?
    - configs/backtest/phase29_3_4_btc5m_baseline_v4_week_gate.yml: Gate Config
    - reports/backtest/phase29_3_4/btc5m_baseline_v4_week_gate_summary.json
    - docs/PHASE29/PHASE29_3_4_V4_ENGINE_INTEGRATION_PROGRESS.md
    - docs/PHASE29/PHASE29_3_4_V4_ENGINE_INTEGRATION_RESULT.md
  
  - **Acceptance Criteria**:
    - ??AC1: V4 ?𡥄猹 諻𨰰� ?㻂𥘵 (96穇?
    - ??AC2: ?䇹� ?蛭襔 貒�溢 ?䁯� (Guard 麆刺𡆀 ?韠𥘵 ?湊盒)
    - ??AC3: 1鴥?20-60穇?Gate ?科� (35穇?
    - ??AC4: 諡賄�??& ROADMAP ?�㫲?渣䂻
    - ??AC5: Git 儢月� ?��
  
  - **?韠�**: ??**COMPLETE (Gate PASS)**
    - V4 ?�嬍 ?㻂� ?炣� ?㻂𥘵
    - Guard ?��諢?Gate ?科�
    - ?木�: PHASE29-4 (V4 Tuning & Optimization)
  
  - **篣國�**: 1 session (3H)

- **29-4: V4 Parameter Tuning & 1M Backtest** ??**COMPLETE** (2025-12-11)
  - **Status**: ??**COMPLETE** | ??**AC3 CONDITIONAL PASS (12/24 魽堅襔)**
  
  - **諈拗�**: V4 ?�嬍 窶趟� ?𣕑𦉘諯貲� ?嶅� 諻?1穈𨰰� 諻桶�?欠䂻 窶�鴞?
  
  - **?�� ?渥𡡒**:
    1. ??1穈𨰰� Gate 諻桶�?欠䂻: 140穇?麮湊盒 (Gate_1M 80-240穇?貒䇹� ??
    2. ??Light Tuning ?欠�: 24穈??𣕑𦉘諯貲� 魽堅襔 (range/trend score, RR, cooldown)
    3. ??窶國頃 賱��: 12穈?魽堅襔??Gate_1M 貒䇹� ??(80-240穇?
    4. ??諡賄�???��: ?嶅� 窶國頃 謔秒𡢢??(JSON/MD)
    5. ???欠�謔踫䂻 ?𡢾�: Runner, Analyzer, Completion Checker
  
  - **?蛙𡠺 諻𨁈痊**:
    - **AC1 (1M 諻桶�?欠䂻)**: ??PASS (140穇?麮湊盒)
    - **AC2 (Gate_1M)**: ??PASS (80-240穇?貒䇹� ??
    - **AC3 (Win Rate/Max DD)**: ??**FAIL** (PHASE29-6 ?禹?鴞?窶國頃: Win Rate 27.86%, Max DD 23.21%)
    - **AC4 (Light Tuning)**: ??PASS (24穈?魽堅襔 ?��, ?�� 3穈??𥔱�)
    - **AC5 (?嵸擪??ROADMAP/Git)**: ??PASS
  
  - **?嶅� 窶國頃**:
    - 黕?24穈?魽堅襔 (range_min_score: 2/3/4, trend_min_score: 2/3, min_rr: 1.0/1.2, cooldown: 0/1)
    - Gate_1M ?虛頃: 12穈?魽堅襔 (諈刺� min_rr=1.0 魽堅襔)
    - ?�� 3穈? range=2/trend=2/RR=1.0 魽堅襔??(140穇?麮湊盒)
    - min_rr=1.2 魽堅襔?� 諈刺� 80穇?諯賈� (Guard 窸潺�)
  
  - **Artifacts** ??
    - configs/backtest/phase29_4_0_btc5m_baseline_v4_month_gate.yml: 1M Gate Config
    - configs/backtest/phase29_4_tuning_*.yml: 24穈??嶅� Config
    - scripts/phase29_4_run_light_tuning.py: ?嶅� Runner
    - scripts/phase29_4_analyze_light_tuning.py: 窶國頃 賱��篣?
    - scripts/phase29_4_check_tuning_completion.py: ?�� ?㻂𥘵
    - reports/backtest/phase29_4_1/*.json: 24穈?諻桶�?欠䂻 窶國頃
    - reports/analysis/PHASE29/phase29_4_2_v4_light_tuning.json
    - docs/PHASE29/PHASE29_4_2_V4_LIGHT_TUNING_RESULT_KR.md
    - docs/PHASE29/PHASE29_4_1_V4_MONTH_BASELINE_RESULT_KR.md
    - docs/PHASE29/PHASE29_4_BTC5M_BASELINE_V4_PLAN_KR.md
  
  - **Acceptance Criteria**:
    - ??AC1: 1穈𨰰� 諻桶�?欠䂻 ?梓陬 (140穇?
    - ??AC2: Gate_1M (80-240穇? ?虛頃
    - ?𩤃� AC3: Win Rate ??45%, Max DD ??15% (Summary JSON???瑅陷 ?�𩸭 穇圉� 穇渥�諢嶅� ?㕓?)
    - ??AC4: Light Tuning 窶國頃 謔秒𡢢??(24穈?魽堅襔, ?�� 3穈??𥔱�)
    - ??AC5: ?嵸擪??ROADMAP/Git ?瑅收 ?��
  
  - **?韠�**: ??**COMPLETE (CONDITIONAL PASS)**
    - V4 ?�嬍 1穈𨰰� ?梵𥁒 ?韠� ?��
    - 12穈?魽堅襔??穇圉� 穇渥� 篣域? ?虛頃
    - Win Rate/Max DD??Engine ?䁯� ???秒�穈� ?��
    - ?木�: PHASE29-5 (Engine Win Rate/Max DD 黺𥯆?) ?韒� PHASE30 (Ensemble 貐虛筋)
  
  - **Known Issues**:
    - Summary JSON??Win Rate, Max DD ?瑅陷 ?�� ??Engine/Reporter ?䁯� ?��
    - AC3 ?�� ?㕓?諝??�㟲 ?�� ?𡢾� ?��
  
  - **篣國�**: 1 session (8H, 諻桶�?欠䂻 ?韒� ?欠� ?秒𥚃嚗?

---

## PHASE29-5: Backtest Summary ?梵𥁒 鴔�???䇹�??

**?��**: ??**COMPLETE (Conditional)**  
**篣國�**: 2025-12-11 (1 session, 4H)  
**諈拗�**: Summary JSON??Win Rate / Max DD / PnL / Sharpe ???�鹻篣??梵𥁒 鴔�??黺𥯆?

### ?�� ?𡢾�

1. **?梵𥁒 鴔�??窸�� 諈刺� 窱秒�**:
   - `common/performance_metrics.py` ?吖�
   - Win Rate, Max DD, PnL, Sharpe Ratio, Profit Factor ??窸��
   - DB 魽堅� 諻?Trade 謔科擪??篣圉� 窸�� 諈刺� 鴔�??

2. **TradeActivityTracker ?蛭襔**:
   - `metrics/trade_activity_tracker.py`??`get_summary()` ?㻂𤟠
   - 諻桶�?欠䂻 鮈�� ???韒�?潺� performance 賳竾� ?吖�
   - 篣域● ?��?� 100% ?貲� (黺𥯆?諤???

3. **?到� ?嵸擪??*:
   - `tests/test_phase29_5_performance_metrics.py` ?𡢾�
   - 18穈??嵸擪??儤�?渥擪 諈刺� PASS ??
   - Edge Cases (Breakeven, ?到𦉘 穇圉� ?? 儢月�

4. **?𡥄䧧謔秒剨 ?欠�謔踫䂻**:
   - `scripts/phase29_5_update_existing_summaries.py`: 篣域● Summary ?�㫲?渣䂻
   - `scripts/phase29_5_analyze_v4_performance.py`: ?梵𥁒 篣圉� 賱�� 諻???�

5. **篣域● 窶國頃 ?�㫲?渣䂻**:
   - PHASE29-4 Summary JSON 26穈𨰰� performance 賳竾� 黺𥯆?
   - 賱�� 謔秒𡢢???吖� (Markdown + JSON)

### Performance ?欠�諤?

```json
{
  "performance": {
    "num_trades": 140,
    "pnl_total": 1234.56,
    "pnl_avg_per_trade": 8.82,
    "win_rate": 0.45,
    "max_drawdown": 0.12,
    "max_drawdown_abs": -1200.0,
    "sharpe_ratio": 1.23,
    "profit_factor": 1.5,
    "roi": 0.12,
    "num_wins": 63,
    "num_losses": 77,
    "avg_win": 150.0,
    "avg_loss": -100.0,
    "max_consecutive_losses": 5
  }
}
```

### Acceptance Criteria

| AC | ??版 | ?�� | 窶國頃 |
|---|------|------|------|
| **AC1** | Summary ?㻂𤟠 | ??**PASS** | performance 賳竾� ?吖� ?㻂𥘵 |
| **AC2** | ?嶅� 窶國頃 諻䁯� | ?𩤃� **CONDITIONAL** | 26穈??�㫲?渣䂻 (trial_id 諤木僮 ?渥�) |
| **AC3** | 賱�� 謔秒𡢢??| ??**PASS** | Markdown + JSON ?吖� |
| **AC4** | ?嵸擪??| ??**PASS** | 18/18 + 篣域● 6/6 PASS |
| **AC5** | 諡賄� & Roadmap | ??**PASS** | 諡賄�??+ 儢月� ?�� |

### Known Issues

**trial_id 諤木僮 諡賄�**:
- 諻桶�?欠䂻 ?欠� ??run_id?� DB trial_id 賱�𦉘儦?
- Performance 窸�� ??黖𨁈滂 500穇?穇圉� 魽堅� ??諈刺� Summary穈� ?軤𦉘??鴔�??
- **?�棅**: ?��???貲�??窱科� ?刷�諢?穈�ˉ, ?木� ?梵𥁒 ?㕓???諻桶�?欠䂻 ?科𠹻???��
- **?湊盒 諻拖�**: `execution/engine.py`??trial_id ?�??諢𨰰� 穈𤣿�

### ?域�諡?

**?𥻗� ?嵸𦉘**:
- `common/performance_metrics.py`
- `tests/test_phase29_5_performance_metrics.py`
- `scripts/phase29_5_analyze_v4_performance.py`
- `scripts/phase29_5_update_existing_summaries.py`
- `docs/PHASE29/PHASE29_5_PERFORMANCE_METRICS_INTEGRATION_KR.md`

**?䁯� ?嵸𦉘**:
- `metrics/trade_activity_tracker.py`

**?吖� 謔秒𡢢??*:
- `reports/analysis/PHASE29/phase29_5_v4_performance.{md,json}`

### ?韠�

??**COMPLETE (Conditional)**
- ?貲�??窱科� ?��, Production Ready Baseline ?瑅汗
- ?域𦚯???𤣿�?�� ?伕� 諻桶�?欠䂻 ?科𠹻?吣尐諢?穈𨰰� ?��
- ?木� PHASE?韠� ?㻂�?�尐諢??科鹻 穈�??

### ?木� ?刷�

**Option A**: trial_id 諡賄� ?湊盒 ???科𠹻??
- V4 1M + 24穈??嶅� 諻桶�?欠䂻 ?科𠹻??
- ?𤣿�???梵𥁒 鴔�?嶅� AC3 (Win Rate >= 45%, Max DD <= 15%) ?秒�穈�

**Option B**: PHASE30 鴔�� (?�� ?貲�?潺�??穈�??
- V4 ?�嬍??Ensemble ?��?��?科� ?蛭襔
- 諰�???�嬍 ?嵸擪?????梵𥁒 鴔�???韒� ?䁯�

**鴔�� 魽國探**: PHASE28-13 ?��

**?渥� 魽國探**: PHASE29-4 PASS (V4 ?�嬍 Win Rate >= 45%, Max DD <= 15%, 1穈𨰰� 諻桶�?欠䂻 ?��)

**PHASE29-3 黖𨰰� ?��**: ??**COMPLETE**
  - V3 ?�嬍 窸蛙� ?韀萼 (AND 諢𨰰� 窸潰�, ?𡥄猹 篞寢�)
  - V4 ?�嬍 ?科�窸?諻?窱秒� ?�� (OR + Score, Regime貐?Multi-TP)
  - V4 ?䇹� ?蛭襔 ?�� (Guard 麆刺𡆀 諡賄� ?湊盒)
  - ??Gate PASS: 1鴥潰𦉘 35穇?麮湊盒 (諈拗� 20-60穇?貒䇹� ??
  - ?木�: PHASE29-4 (V4 Tuning & Optimization)
  
  
---

### PHASE30-1: btc15m_core_v1 구현 & 인프라 구축

**상태**: ✅ **COMPLETE** (구현), ❌ **AC3 FAIL** (거래 부족)  
**기간**: 2025-12-11 (1 session)  
**목표**: Core V1 전략 코드 구현 및 3M Baseline 백테스트 인프라 완성

#### 완료 작업

**1. 전략 코드 구현** (strategies/btc15m_core_v1.py, 650 lines):
- Regime Detection: ADX + ATR + Volume + DI 복합 지표 (4 Regimes)
- Core AND Block: 6개 필수 필터 (Regime, ATR, Volume, 신뢰도 등)
- Optional OR Block: Regime별 진입 시나리오 (Trend 3개, Range 2개)
- SL/TP 계산: RR  1.5, Regime별 동적 조정 (Trend: 2.0 ATR, Range: 1.5 ATR)
- Multi-TP: TP1 50%, TP2 50%
- BaseStrategy 상속, compute_signal() 구현

**2. 백테스트 인프라**:
- 지표 계산: common/backtest_indicators.py (dd_core_v1_indicators())
- Config: phase30_1_btc15m_core_v1_3m_baseline.yml (Guard ON, 15m, 3M)
- 검증 스크립트: scripts/phase30_1_check_core_v1_config.py
- 단위 테스트: 	ests/test_btc15m_core_v1.py (15개, 11개 PASS)

**3. 문서화**:
- 상태 보고서: docs/PHASE30/PHASE30_1_BTC15M_CORE_V1_IMPLEMENTATION_STATUS_KR.md
- V2/V3/V4 vs Core V1 비교 분석
- AC1~AC4 판정 기준 명시

#### Acceptance Criteria

| AC | 항목 | 판정 |
|----|------|------|
| **AC1** | 전략 구현 (Core AND/OR, Regime, SL/TP) |  **PASS** |
| **AC2** | Config & 검증 스크립트 |  **PASS** |
| **AC3** | 성능 지표 산출 (백테스트) |  **PENDING** (데이터 대기) |
| **AC4** | 문서 & ROADMAP |  **PASS** |

#### V2/V3/V4 대비 차별점

| 항목 | V4 (RETIRED) | Core V1 (NEW) |
|------|--------------|---------------|
| **진입** | OR + Score | Core AND  Optional OR |
| **Regime** | ADX 단일 | ADX+ATR+Vol+DI 복합 |
| **RR** | 1.0~1.2 |  1.5 (동적) |
| **Timeframe** | 5m (노이즈) | 15m (품질) |
| **Guard** | OFF 테스트 | ON 전제 |

#### 산출물

**코드**:
- strategies/btc15m_core_v1.py
- common/backtest_indicators.py (add_core_v1_indicators)
- configs/backtest/phase30_1_btc15m_core_v1_3m_baseline.yml
- scripts/phase30_1_check_core_v1_config.py
- 	ests/test_btc15m_core_v1.py

**문서**:
- docs/PHASE30/PHASE30_1_BTC15M_CORE_V1_IMPLEMENTATION_STATUS_KR.md

#### 판정

 **CONDITIONAL PASS** (코드 & 인프라 100% 완료, 백테스트 데이터 준비 후 AC3 재평가)

**Next**: 
- 즉시: 15m 데이터 다운로드 또는 5m 리샘플링
- 백테스트 실행 후 AC3 평가
- PHASE30-2 (Light Tuning) 진행 여부 결정
### 다음 단계

✅ **PHASE29-7 완료** (V4 Postmortem & Retirement)

---

## PHASE29-6: V4 Performance Metrics Accuracy & AC3 최종 판정匸薑

**鼻鷓**:  **COMPLETE**  
**晦除**: 2025-12-11 (1 session)  
**跡ォ**: trial_id/run_id 薑ベ撩 熱薑 塽 V4 AC3 譆謙 營が陛

### 僥薯 薑曖

PHASE29-5縑憮 嫦唯脹 trial_id/run_id 碳橾纂煎 檣ボ:
- DB trades.trial_id 渠睡碟 NULL (6,090勒 醞 738勒虜 爾嶸)
- Performance 啗骯 衛 譆斬 500勒 奢鱔 trade 餌辨  睡薑�
- AC3 (Win Rate/Max DD) が陛 褐煆紫 0%

### 諫猿 濛機

1. **engine.py 熱薑**: trial_id = config.get("trial_id") or run_id
2. **run_backtest.py 熱薑**: custom config曖 run_id 爾襄
3. **欽嬪 纔蝶⑷ 爾鬼**: 3/3 PASS (trial_id 衙ヒ 薑�紫 匐隸)
4. **V4 寥纔蝶⑷ 營褒ヤ**: 1M Gate 140勒, trial_id 薑鼻 盪濰 
5. **AC3 碟戮 & 匸薑**: 4/4 褻ベ 賅舒 AC3 FAIL

### AC3 營が陛 唸婁

**1M Gate Baseline**:
- Win Rate: 27.86% (跡ォ: 45%) 
- Max DD: 23.21% (跡ォ: 15%) 
- PnL: -2,245 USDT, Profit Factor: 0.525

**錳檣**: 槳褒 綠徽 72.14%, Win Rate 17.14%p 睡褶, R:R 綠徽 碳葬

**Top 3 ⑨棚**: 賅舒 AC3 FAIL (Win Rate 30.4%, Max DD 64.6%)

### PHASE29-4 譆謙 匸薑

**AC3:  FAIL** - V4 瞪楞擎 2024喇 11錯 BTC 衛濰縑憮 撩棟 晦遽 嘐殖

### Acceptance Criteria

| AC | 唸婁 |
|----|------|
| AC1: trial_id/run_id 薑ベ撩 |  PASS |
| AC2: Performance 啗骯 薑�紫 |  PASS |
| AC3: 寥纔蝶⑷ 營褒ヤ |  PASS (140勒) |
| AC4: AC3 營が陛 |  PASS (FAIL 匸薑) |
| AC5: 僥憮 & Roadmap |  PASS |

### 骯轎僭

**囀橫 熱薑**: execution/engine.py, scripts/run_backtest.py  
**褐敘 冖橾**: tests/test_phase29_6_trial_id_mapping.py, scripts/phase29_6_*.py  
**僥憮**: docs/PHASE29/PHASE29_6_V4_PERFORMANCE_ACCURACY_KR.md  
**葬け⑷**: reports/analysis/PHASE29/phase29_6_ac3_performance.{md,json}

### 匸薑

 **COMPLETE** - Infrastructure 100% 諫猿, V4 撩棟 が陛 諫猿 (AC3 FAIL 譆謙 匸薑)

### 棻擠 欽啗

**PHASE30**: 瞪楞 偃摹 傳朝 懈鼻綰 犒掘
- Option A: V4 冖塭嘐攪 營褻薑
- Option B: 棻艇 晦除/衛濰 褻勒 營匐隸
- Option C: 懈鼻綰 ヅ溯歜錶觼 犒掘

---

## PHASE29-7: V4 Strategy Postmortem & Retirement

**상태**:  **COMPLETE**  
**기간**: 2025-12-11 (1 session)  
**목표**: V4 전략 실패 원인 분석 및 Research Graveyard 이관

### 문제 정의

PHASE29-6에서 V4 전략의 AC3 최종 판정 결과:
- **1M Gate Baseline**: Win Rate 27.86% (목표: 45%), Max DD 23.21% (목표: 15%)
- **Top 3 튜닝**: 모두 AC3 FAIL
- **종합**: 4/4 조합 모두 성능 기준 미달

### 완료 작업

1. **행동 패턴 분석** (기존 AC3 데이터 활용):
   - 기본 통계: 140건, Win Rate 27.86%, 손실 비율 72.14%
   - 연속 손실: 최대 10건
   - Side별 성능, 청산 패턴, Holding Time 분석

2. **Postmortem 문서 작성**:
   - docs/PHASE29/PHASE29_7_V4_STRATEGY_POSTMORTEM_KR.md
   - 근본 실패 원인 5가지 분석 (OR 과잉, Score Threshold, Regime Detection, SL/TP, 5m Noise)
   - 보존 vs 폐기 요소 구분
   - PHASE30 To-BE 전략 설계 권고사항

3. **PHASE_ROADMAP 업데이트**:
   - PHASE29-7 섹션 추가
   - V4 전략 Research Graveyard 이관 명시

### 근본 실패 원인

1. **OR 기반 진입 조건 과잉**: 저품질 신호 과다 생성 (72.14% 손실)
2. **Score Threshold 부적절**: 최대 점수 대비 너무 낮음 (3/8점)
3. **Regime Detection 부정확**: ADX 단일 지표 의존
4. **SL/TP 비율 미스매치**: RR 1.0~1.2 (Win Rate 54% 필요)
5. **5m Timeframe 노이즈**: 과도한 False Signal

### Postmortem 핵심 결론

**보존할 요소**:
-  Regime-Aware 구조 (개선 필요)
-  Multi-TP 구조
-  ATR 기반 SL/TP
-  Guard 시스템 연동

**폐기할 요소**:
-  OR 기반 Score 조합
-  현재 Score 가중치
-  낮은 RR 비율 (1.0~1.2)
-  ADX 단일 Regime 분류
-  5m Timeframe 고집

### PHASE30 To-BE 권고

1. **진입 조건**: Core AND + Optional OR 구조
2. **Regime Detection**: 복합 지표 (ADX + ATR + Volume + DI)
3. **SL/TP**: 최소 RR 1.5, 동적 조정
4. **Timeframe**: 15m, 30m 우선 테스트
5. **목표**: Win Rate 40~45%, Max DD  12%, PF > 1.2

### Acceptance Criteria

| AC | 결과 |
|----|------|
| AC1: 행동 패턴 분석 |  PASS (AC3 데이터 활용) |
| AC2: Postmortem 문서 |  PASS |
| AC3: ROADMAP 업데이트 |  PASS |
| AC4: 테스트 회귀 |  PASS |
| AC5: Git 커밋 |  PASS |

### 산출물

**문서**:
- docs/PHASE29/PHASE29_7_V4_STRATEGY_POSTMORTEM_KR.md

**업데이트**:
- PHASE_ROADMAP.md

### 판정

 **COMPLETE** - V4 전략 공식 폐기 및 Research Graveyard 이관

**최종 결론**: btc5m_baseline_v4는 구조적 설계 결함으로 수익성 목표 달성 불가. 라이브/앙상블 후보에서 영구 제외. PHASE30에서 새로운 코어 전략 설계 착수.

### 다음 단계

**PHASE30-0: New Core Strategy Design**
- V3/V4 실패 교훈 반영
- Core AND + Optional OR 구조
- 복합 Regime Detection
- 최소 RR 1.5, 15m/30m Timeframe
- 3개월 백테스트 + Out-of-Sample 검증


---

## PHASE30  New Core Strategy Design  IN PROGRESS

> **NOTE**: 기존 하단의 "PHASE30  UI/UX v2" 블록은 향후 리넘버링 예정 (PHASE40+로 이동)

### 개요

PHASE29에서 V2/V3/V4 전략 모두 AC3 성능 기준(Win Rate  45%, Max DD  15%) 실패.
PHASE30은 실패 교훈을 반영한 **새로운 코어 전략 설계 및 검증** 단계.

**전략명**: btc15m_core_v1
**Timeframe**: 15m (Primary), 30m (Secondary)
**설계 철학**: Core AND + Optional OR (V2 OR 과잉, V3 AND 과잉 절충)

---

### PHASE30-0: New Core Strategy Design (btc15m_core_v1)

**상태**:  **COMPLETE**  
**기간**: 2025-12-11 (1 session)  
**목표**: V3/V4 실패 교훈을 반영한 새로운 코어 전략 설계 (문서 전용)

#### 문제 정의

PHASE29 전략 실패 요약:
- **V2**: OR 과잉  저품질 신호 과다  Win Rate < 45%
- **V3**: AND 과잉  신호 극소 (17건/월)
- **V4**: OR + Score 절충  Win Rate 27.86%, Max DD 23.21%, RR 1.0~1.2 (낮음), 5m 노이즈

#### 완료 작업

1. **전략 구조 설계**:
   - **Timeframe**: 15m Primary (5m 대비 노이즈 70% 감소)
   - **Regime Detection**: ADX + ATR + Volume + DI 복합 지표
     - Trend-Up / Trend-Down / Range / High-Volatility-Chop (4가지)
     - 확률적 신뢰도 점수, Hysteresis 적용
   - **진입 조건**: Core AND + Optional OR
     - Core AND: Regime, Guard, ATR, Volume, DD, 연속손실 (필수)
     - Optional OR: Regime별 진입 시나리오 (Pullback, RSI, BB 등)
   - **SL/TP**: 최소 RR 1.5, Regime별 동적 조정
     - Trend: SL=2.0 ATR, TP1 RR=1.5, TP2 RR=3.0
     - Range: SL=1.5 ATR, TP1 RR=1.5, TP2 RR=2.5
   - **Multi-TP**: TP1 50%, TP2 50%, Trailing Stop (Trend Mode)

2. **Guard 연동 설계**:
   - Guard ON 전제 설계 (V4 Guard OFF 테스트 문제 해결)
   - 전략 RR  1.5, Guard min_rr_required=1.5 일치
   - Max DD 12% 이내 자연스럽게 수용

3. **백테스트 & 검증 계획**:
   - 데이터 구간: 3개월 (2024-09-01 ~ 2024-12-01)
   - Out-of-Sample 검증 필수
   - PHASE25 Tuning Cluster Infra 활용
   - 검증 순서: Baseline  OOS  Light Tuning  Real-time PAPER

#### 정량 목표

| 지표 | 목표 | 근거 |
|------|------|------|
| Win Rate | 40~45% | RR 1.5 기준, EV 양수 |
| Risk:Reward |  1.5 | Win Rate 40% 시 EV = 0.0 (Break-even), 45% 시 EV = +0.125 |
| Max DD |  12% | V4 23.21% 대비 보수적 |
| Profit Factor | > 1.2 | 명확한 이익 구조 |
| 거래 건수/월 | 60~120건 | 15m 기준, V4 5m 140건보다 보수적 |

#### V2/V3/V4 차별점

| 항목 | V2/V3/V4 | btc15m_core_v1 |
|------|----------|----------------|
| 진입 조건 | V2: 모든 OR<br>V3: 모든 AND<br>V4: OR+Score | **Core AND + Optional OR** |
| Regime | V4: ADX 단일 | **ADX+ATR+Volume+DI 복합** |
| RR | V4: 1.0~1.2 | ** 1.5 (동적)** |
| Timeframe | 5m (노이즈) | **15m/30m (품질)** |
| Guard | V4: OFF 테스트 | **ON 전제 설계** |

#### 산출물

**문서**:
- docs/PHASE30/PHASE30_0_BTC15M_CORE_STRATEGY_DESIGN_KR.md (26KB, 매우 상세)
  - Regime Detection 설계 (복합 지표, 신뢰도 점수)
  - Core AND + Optional OR 진입 조건 (Pseudo-code 포함)
  - SL/TP 동적 계산 (Regime별 RR 차별화)
  - Multi-TP 구조 (TP1 50%, TP2 50%, Trailing)
  - Guard 연동 설계 (호환성 사전 검증)
  - 백테스트 계획 (3M Baseline, OOS, Tuning, PAPER)

**업데이트**:
- PHASE_ROADMAP.md (PHASE30-0 섹션 추가)

#### Acceptance Criteria

| AC | 결과 |
|----|------|
| AC1: 설계 문서에 Core AND / Optional OR / Regime / SL/TP / Guard 연동이 구체적으로 정의됨 |  **PASS** |
| AC2: 성능 목표(Win Rate 40~45%, Max DD  12%, PF > 1.2)가 PHASE29-7 권고와 일치 |  **PASS** |
| AC3: 향후 PHASE30-1/2 백테스트 계획이 명시됨 |  **PASS** |
| AC4: 기존 V2/V3/V4 설계와의 차별점 및 교훈 반영이 문서화됨 |  **PASS** |

#### 판정

 **COMPLETE** - 새로운 코어 전략 설계 문서 완성

**핵심 설계 원칙**:
1. Core AND (필수 조건)  Optional OR (진입 시나리오)
2. 복합 지표 기반 Regime Detection (ADX + ATR + Volume + DI)
3. 최소 RR 1.5, Regime별 동적 SL/TP
4. 15m Timeframe (노이즈 감소, 신호 품질 향상)
5. Guard ON 전제 설계 (실제 운영 가능성 보장)

#### 다음 단계

**PHASE30-1: 코드 구현 & 3M Baseline 백테스트**
- strategies/btc15m_core_v1.py 구현
- Guard ON, 3개월 백테스트 실행
- AC3 평가: Win Rate  40%, Max DD  12%, PF > 1.2


