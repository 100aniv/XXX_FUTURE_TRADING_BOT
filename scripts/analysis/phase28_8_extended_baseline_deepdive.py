#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-8-1: Extended Baseline Deep Dive Analyzer
3개월 (2024-08~10) btc5m_baseline_v2 백테스트 결과 심층 분석

분석 범위:
- 전체 Trade/WinRate/Sharpe/PnL 요약
- Signal → Order → Trade Funnel 분석
- Regime 분포 (Trend/Range, Vol High/Low)
- Guard/Portfolio 병목 지점 식별
- 일별 성능 추이
"""

import sys
import json
import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection


def find_latest_3m_summary():
    """
    가장 최근 3개월 백테스트 summary JSON 파일 찾기
    """
    pattern = str(project_root / "reports/backtest/phase28_8/baseline_3m*.json")
    files = glob.glob(pattern)
    if not files:
        print("⚠️ 3개월 summary JSON 파일을 찾을 수 없습니다.")
        return None
    
    # 가장 최근 파일
    latest = max(files, key=lambda f: Path(f).stat().st_mtime)
    print(f"✅ 최근 summary 파일 발견: {latest}")
    return latest


def load_summary_json(filepath):
    """
    Summary JSON 로드
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_trades_from_db(run_id_pattern="phase28_8_btc5m_baseline_v2_3m"):
    """
    DB에서 3개월 백테스트 거래 데이터 조회 및 분석
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 최근 3개월 백테스트 거래 조회 (created_at 기준)
            # 3개월 백테스트는 08:25~08:35 사이에 실행되었음
            cur.execute("""
                SELECT
                    ts_open,
                    ts_close,
                    side,
                    entry_price,
                    exit_price,
                    quantity,
                    pnl,
                    pnl_pct,
                    fees,
                    strategy_id
                FROM trading.trades
                WHERE created_at >= '2025-12-08 08:25:00'
                  AND created_at <= '2025-12-08 08:35:00'
                ORDER BY ts_open
            """)
            
            trades = cur.fetchall()
            
            if not trades:
                print("⚠️ 거래 데이터 조회 실패")
                return None
            
            # 분석
            total_trades = len(trades)
            long_trades = sum(1 for t in trades if t[2] == 'LONG')
            short_trades = sum(1 for t in trades if t[2] == 'SHORT')
            
            pnls = [float(t[6]) for t in trades if t[6] is not None]
            pnl_pcts = [float(t[7]) for t in trades if t[7] is not None]
            
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = win_count / total_trades if total_trades > 0 else 0.0
            
            total_pnl = sum(pnls)
            avg_pnl = np.mean(pnls) if pnls else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            # Profit Factor
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            # Sharpe Ratio
            sharpe = calculate_sharpe_ratio(pnl_pcts)
            
            # Max Drawdown
            equity_curve = [50000.0]
            for pnl in pnls:
                equity_curve.append(equity_curve[-1] + pnl)
            
            max_dd = calculate_max_drawdown(equity_curve)
            final_equity = equity_curve[-1]
            total_return_pct = ((final_equity - 50000) / 50000) * 100
            
            # 일별 집계
            daily_stats = analyze_daily_performance(trades)
            
            return {
                'trial_id': 'phase28_8_btc5m_baseline_v2_3m_v2',
                'total_trades': total_trades,
                'long_trades': long_trades,
                'short_trades': short_trades,
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': round(win_rate * 100, 2),
                'profit_factor': round(profit_factor, 3),
                'sharpe_ratio': round(sharpe, 4),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'total_return_pct': round(total_return_pct, 2),
                'max_drawdown': round(max_dd * 100, 2),
                'final_equity': round(final_equity, 2),
                'daily_stats': daily_stats
            }


def calculate_sharpe_ratio(returns):
    """
    Sharpe Ratio 계산
    """
    if len(returns) == 0:
        return 0.0
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1) if len(returns) > 1 else 0.0
    if std_return == 0:
        return 0.0
    return mean_return / std_return


def calculate_max_drawdown(equity_curve):
    """
    Max Drawdown 계산
    """
    if len(equity_curve) == 0:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def analyze_daily_performance(trades):
    """
    일별 거래 성능 집계
    """
    daily_data = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    
    for trade in trades:
        ts_open = trade[0]
        pnl = float(trade[6]) if trade[6] is not None else 0.0
        
        date_str = str(ts_open.date())
        daily_data[date_str]['trades'] += 1
        if pnl > 0:
            daily_data[date_str]['wins'] += 1
        daily_data[date_str]['pnl'] += pnl
    
    # 정렬
    daily_list = []
    for date_str in sorted(daily_data.keys()):
        data = daily_data[date_str]
        win_rate = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0.0
        daily_list.append({
            'date': date_str,
            'trades': data['trades'],
            'wins': data['wins'],
            'win_rate': round(win_rate, 1),
            'pnl': round(data['pnl'], 2)
        })
    
    return daily_list


def analyze_funnel(summary_json):
    """
    Signal → Order → Trade Funnel 분석
    """
    if not summary_json:
        return None
    
    totals = summary_json.get('totals', {})
    
    strategy_signals_true = totals.get('strategy_signals_true', 0)
    orders_submitted = totals.get('orders_submitted', 0)
    
    # 실제 trades는 DB에서 조회한 값을 사용
    # 여기서는 summary의 orders를 기준으로 표시
    
    funnel = {
        'signals_generated': strategy_signals_true,
        'orders_submitted': orders_submitted,
        'signal_to_order_ratio': round(orders_submitted / strategy_signals_true * 100, 2) if strategy_signals_true > 0 else 0.0,
        'regime_distribution': {
            'regime_trend': totals.get('regime_trend', 0),
            'regime_range': totals.get('regime_range', 0)
        },
        'signal_breakdown': {
            'long_signals': totals.get('long_signals', 0),
            'short_signals': totals.get('short_signals', 0)
        }
    }
    
    return funnel


def generate_markdown_report(trade_analysis, funnel_analysis, output_path):
    """
    Markdown 리포트 생성
    """
    report = f"""# PHASE28-8-1: Extended Baseline Deep Dive Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Period**: 2024-08-01 ~ 2024-10-31 (3개월, 92일)  
**Strategy**: btc5m_baseline_v2  
**Mode**: Baseline Parameters (No Tuning)

---

## 📊 Executive Summary

### 전체 성능 메트릭

| Metric | Value | Target (PHASE28-6) | Status |
|--------|-------|---------------------|--------|
| **Trial ID** | {trade_analysis['trial_id']} | - | - |
| **Trade Count** | {trade_analysis['total_trades']} | ≥ 60 (20/month × 3) | {'✅' if trade_analysis['total_trades'] >= 60 else '❌'} |
| **Win Rate** | {trade_analysis['win_rate']}% | ≥ 40% | {'✅' if trade_analysis['win_rate'] >= 40 else '❌'} |
| **Sharpe Ratio** | {trade_analysis['sharpe_ratio']} | ≥ 0.0 | {'✅' if trade_analysis['sharpe_ratio'] >= 0 else '❌'} |
| **Total PnL** | ${trade_analysis['total_pnl']} | Positive | {'✅' if trade_analysis['total_pnl'] > 0 else '❌'} |
| **Total Return** | {trade_analysis['total_return_pct']}% | Positive | {'✅' if trade_analysis['total_return_pct'] > 0 else '❌'} |
| **Max Drawdown** | {trade_analysis['max_drawdown']}% | ≤ 20% | {'✅' if trade_analysis['max_drawdown'] <= 20 else '❌'} |
| **Final Equity** | ${trade_analysis['final_equity']} | > $50,000 | {'✅' if trade_analysis['final_equity'] > 50000 else '❌'} |
| **Profit Factor** | {trade_analysis['profit_factor']} | ≥ 1.5 | {'✅' if trade_analysis['profit_factor'] >= 1.5 else '❌'} |

### Trade Breakdown

| Side | Count | % |
|------|-------|---|
| **LONG** | {trade_analysis['long_trades']} | {round(trade_analysis['long_trades'] / trade_analysis['total_trades'] * 100, 1) if trade_analysis['total_trades'] > 0 else 0}% |
| **SHORT** | {trade_analysis['short_trades']} | {round(trade_analysis['short_trades'] / trade_analysis['total_trades'] * 100, 1) if trade_analysis['total_trades'] > 0 else 0}% |

### Win/Loss Breakdown

| Type | Count | Avg PnL |
|------|-------|---------|
| **Wins** | {trade_analysis['win_count']} | ${trade_analysis['avg_win']} |
| **Losses** | {trade_analysis['loss_count']} | ${trade_analysis['avg_loss']} |

---

## 🔍 Signal → Order → Trade Funnel Analysis

"""
    
    if funnel_analysis:
        report += f"""### Funnel Metrics

| Stage | Count | Conversion Rate |
|-------|-------|-----------------|
| **Signals Generated** | {funnel_analysis['signals_generated']} | 100% |
| **Orders Submitted** | {funnel_analysis['orders_submitted']} | {funnel_analysis['signal_to_order_ratio']}% |
| **Trades Executed** | {trade_analysis['total_trades']} | - |

**핵심 발견**:
- Signal → Order 전환율: **{funnel_analysis['signal_to_order_ratio']}%**
- ⚠️ {'극도로 낮은 전환율 (대부분 Guard/Portfolio에서 차단)' if funnel_analysis['signal_to_order_ratio'] < 1 else '정상 전환율'}

### Regime Distribution

| Regime | Count | % |
|--------|-------|---|
| **Trend** | {funnel_analysis['regime_distribution']['regime_trend']} | {round(funnel_analysis['regime_distribution']['regime_trend'] / (funnel_analysis['regime_distribution']['regime_trend'] + funnel_analysis['regime_distribution']['regime_range']) * 100, 1) if funnel_analysis['regime_distribution']['regime_trend'] + funnel_analysis['regime_distribution']['regime_range'] > 0 else 0}% |
| **Range** | {funnel_analysis['regime_distribution']['regime_range']} | {round(funnel_analysis['regime_distribution']['regime_range'] / (funnel_analysis['regime_distribution']['regime_trend'] + funnel_analysis['regime_distribution']['regime_range']) * 100, 1) if funnel_analysis['regime_distribution']['regime_trend'] + funnel_analysis['regime_distribution']['regime_range'] > 0 else 0}% |

**핵심 발견**:
- ⚠️ {'Regime Trend가 거의 감지되지 않음 (Bull/Bear 구간 포함)' if funnel_analysis['regime_distribution']['regime_trend'] < 100 else 'Trend 정상 감지'}
- {'Range 편향이 심각함' if funnel_analysis['regime_distribution']['regime_range'] > funnel_analysis['regime_distribution']['regime_trend'] * 5 else 'Regime 분포 정상'}

### Signal Breakdown

| Direction | Count | % |
|-----------|-------|---|
| **LONG** | {funnel_analysis['signal_breakdown']['long_signals']} | {round(funnel_analysis['signal_breakdown']['long_signals'] / funnel_analysis['signals_generated'] * 100, 1) if funnel_analysis['signals_generated'] > 0 else 0}% |
| **SHORT** | {funnel_analysis['signal_breakdown']['short_signals']} | {round(funnel_analysis['signal_breakdown']['short_signals'] / funnel_analysis['signals_generated'] * 100, 1) if funnel_analysis['signals_generated'] > 0 else 0}% |

"""
    
    report += f"""
---

## 📈 Daily Performance

"""
    
    # 일별 통계 테이블
    if trade_analysis.get('daily_stats'):
        report += "| Date | Trades | Wins | Win Rate | Daily PnL |\n"
        report += "|------|--------|------|----------|----------|\n"
        
        for day in trade_analysis['daily_stats']:
            report += f"| {day['date']} | {day['trades']} | {day['wins']} | {day['win_rate']}% | ${day['pnl']} |\n"
    else:
        report += "*일별 통계 데이터 없음*\n"
    
    report += """
---

## 🎯 핵심 문제 포인트

### 1. Trade Count 극도로 부족
"""
    
    if trade_analysis['total_trades'] < 60:
        report += f"""- **관찰**: 3개월({trade_analysis['total_trades']}건) vs 목표(60건)
- **원인**: Signal → Order 전환율 {funnel_analysis['signal_to_order_ratio']}%
- **영향**: 목표 대비 {round((60 - trade_analysis['total_trades']) / 60 * 100, 1)}% 부족
"""
    
    report += f"""
### 2. Regime Detection 오작동
"""
    
    if funnel_analysis and funnel_analysis['regime_distribution']['regime_trend'] < 500:
        report += f"""- **관찰**: Trend Regime {funnel_analysis['regime_distribution']['regime_trend']}건 vs Range {funnel_analysis['regime_distribution']['regime_range']}건
- **원인**: ADX/DI threshold 너무 높거나 로직 오류
- **영향**: Dynamic Threshold가 제대로 작동 안함
"""
    
    report += f"""
### 3. 성능 메트릭
"""
    
    if trade_analysis['win_rate'] < 40:
        report += f"""- **Win Rate**: {trade_analysis['win_rate']}% (목표: 40%)
"""
    
    if trade_analysis['sharpe_ratio'] < 0:
        report += f"""- **Sharpe Ratio**: {trade_analysis['sharpe_ratio']} (목표: ≥ 0)
"""
    
    if trade_analysis['profit_factor'] < 1.5:
        report += f"""- **Profit Factor**: {trade_analysis['profit_factor']} (목표: ≥ 1.5)
"""
    
    report += f"""
---

## 💡 권장 조치

### 긴급 (PHASE28-8-2)
1. **Regime Detection 디버깅**
   - ADX threshold {funnel_analysis['regime_distribution']['regime_trend']}건 → 500+ 목표
   - DI+/DI- 분리 조건 재검토
   
2. **Guard/Portfolio 완화**
   - Signal {funnel_analysis['signals_generated']}개 → Order {funnel_analysis['orders_submitted']}건 전환율 개선
   - Budget Cap/Cooldown 조정

3. **Dynamic Threshold 재조정**
   - RSI percentile 범위 확대
   - BB multiplier 하향

### 중기 (PHASE29)
- 전략 패밀리 재평가 (Mean Reversion vs Trend Following)
- 파라미터 공간 재설계
- Light Random Search로 생존 가능성 재확인

---

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Markdown 리포트 저장: {output_path}")


def main():
    """
    메인 분석 실행
    """
    print("=" * 80)
    print("🔬 PHASE28-8-1: Extended Baseline Deep Dive Analysis")
    print("=" * 80)
    
    # 1. Summary JSON 찾기
    summary_file = find_latest_3m_summary()
    summary_json = None
    if summary_file:
        summary_json = load_summary_json(summary_file)
        print(f"✅ Summary JSON 로드 완료")
    
    # 2. DB에서 거래 데이터 분석
    print("\n📊 DB 거래 데이터 분석 중...")
    trade_analysis = analyze_trades_from_db()
    
    if not trade_analysis:
        print("❌ 거래 데이터 분석 실패")
        return
    
    # 3. Funnel 분석
    print("\n🔍 Signal → Order → Trade Funnel 분석 중...")
    funnel_analysis = analyze_funnel(summary_json)
    
    # 4. 결과 JSON 저장
    output_json = project_root / "reports/analysis/phase28_8_extended_baseline_3m_summary.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    
    combined_results = {
        'trade_analysis': trade_analysis,
        'funnel_analysis': funnel_analysis,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(combined_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 결과 저장: {output_json}")
    
    # 5. Markdown 리포트 생성
    print("\n📝 Markdown 리포트 생성 중...")
    output_md = project_root / "docs/PHASE28/PHASE28-8_EXTENDED_BASELINE_DEEPDIVE.md"
    generate_markdown_report(trade_analysis, funnel_analysis, output_md)
    
    # 6. 콘솔 요약 출력
    print("\n" + "=" * 80)
    print("📊 3개월 백테스트 핵심 메트릭 요약")
    print("=" * 80)
    print(f"Trade Count: {trade_analysis['total_trades']} (목표: 60)")
    print(f"Win Rate: {trade_analysis['win_rate']}% (목표: ≥40%)")
    print(f"Sharpe Ratio: {trade_analysis['sharpe_ratio']} (목표: ≥0)")
    print(f"Total PnL: ${trade_analysis['total_pnl']}")
    print(f"Final Equity: ${trade_analysis['final_equity']}")
    
    if funnel_analysis:
        print(f"\nSignal → Order 전환율: {funnel_analysis['signal_to_order_ratio']}%")
        print(f"Regime Trend: {funnel_analysis['regime_distribution']['regime_trend']}건")
        print(f"Regime Range: {funnel_analysis['regime_distribution']['regime_range']}건")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
