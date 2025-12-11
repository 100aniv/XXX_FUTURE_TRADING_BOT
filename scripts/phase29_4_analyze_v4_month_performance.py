"""
PHASE29-4: V4 1개월 백테스트 성능 분석 스크립트

목적: V4 1개월 백테스트 결과를 분석하여 핵심 메트릭 계산 및 리포트 생성
"""

import sys
from pathlib import Path
import json
import pandas as pd
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_summary_json(summary_path):
    """Summary JSON 로드"""
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_metrics(summary):
    """핵심 메트릭 계산 (Summary JSON만 사용)"""
    
    totals = summary.get("totals", {})
    
    metrics = {
        # 기본 정보
        "run_id": summary.get("run_id", "N/A"),
        "timestamp": summary.get("timestamp", "N/A"),
        "end_timestamp": summary.get("end_timestamp", "N/A"),
        
        # 신호 생성
        "strategy_signals_total": totals.get("strategy_signals_total", 0),
        "strategy_signals_true": totals.get("strategy_signals_true", 0),
        "signal_rate": (totals.get("strategy_signals_true", 0) / totals.get("strategy_signals_total", 1)) * 100,
        "long_signals": totals.get("long_signals", 0),
        "short_signals": totals.get("short_signals", 0),
        
        # Regime 분포
        "regime_range": totals.get("regime_range", 0),
        "regime_trend": totals.get("regime_trend", 0),
        "regime_range_pct": (totals.get("regime_range", 0) / totals.get("strategy_signals_total", 1)) * 100,
        "regime_trend_pct": (totals.get("regime_trend", 0) / totals.get("strategy_signals_total", 1)) * 100,
        
        # Guard
        "guard_blocks_total": totals.get("guard_blocks_total", 0),
        "orders_submitted": totals.get("orders_submitted", 0),
        "guard_pass_rate": (totals.get("orders_submitted", 0) / totals.get("strategy_signals_true", 1)) * 100,
        
        # Gate 판정
        "gate_1m_pass": 80 <= totals.get("orders_submitted", 0) <= 240,
    }
    
    return metrics


def generate_markdown_report(metrics, output_path):
    """Markdown 리포트 생성"""
    
    md = []
    md.append("# PHASE29-4.1: V4 1개월 백테스트 성능 분석")
    md.append("")
    md.append(f"**분석일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**run_id**: {metrics['run_id']}")
    md.append("")
    md.append("---")
    md.append("")
    
    # Executive Summary
    md.append("## 📊 Executive Summary")
    md.append("")
    gate_status = "✅ PASS" if metrics["gate_1m_pass"] else "❌ FAIL"
    md.append(f"**Gate_1M**: {gate_status} ({metrics['orders_submitted']}건, 목표 80~240건)")
    md.append("")
    
    # 신호 생성
    md.append("## 🎯 신호 생성")
    md.append("")
    md.append("| 항목 | 값 |")
    md.append("|------|-----|")
    md.append(f"| 전체 캔들 | {metrics['strategy_signals_total']:,}개 |")
    md.append(f"| 신호 발생 | {metrics['strategy_signals_true']:,}건 |")
    md.append(f"| Signal Rate | {metrics['signal_rate']:.2f}% |")
    md.append(f"| LONG 신호 | {metrics['long_signals']:,}건 |")
    md.append(f"| SHORT 신호 | {metrics['short_signals']:,}건 |")
    md.append("")
    
    # Regime 분포
    md.append("## 🌐 Regime 분포")
    md.append("")
    md.append("| Regime | 캔들 수 | 비율 |")
    md.append("|--------|---------|------|")
    md.append(f"| Trend | {metrics['regime_trend']:,}개 | {metrics['regime_trend_pct']:.2f}% |")
    md.append(f"| Range | {metrics['regime_range']:,}개 | {metrics['regime_range_pct']:.2f}% |")
    md.append("")
    
    # Guard 분석
    md.append("## 🛡️ Guard 분석")
    md.append("")
    md.append("| 항목 | 값 |")
    md.append("|------|-----|")
    md.append(f"| Guard 차단 | {metrics['guard_blocks_total']:,}건 |")
    md.append(f"| Guard 통과 | {metrics['orders_submitted']:,}건 |")
    md.append(f"| Guard 통과율 | {metrics['guard_pass_rate']:.2f}% |")
    md.append("")
    
    # Gate 판정
    md.append("## ✅ Gate 판정")
    md.append("")
    md.append("| 기준 | 목표 | 실제 | 판정 |")
    md.append("|------|------|------|------|")
    gate_status = "✅ PASS" if metrics["gate_1m_pass"] else "❌ FAIL"
    md.append(f"| 거래 건수 | 80~240건 | {metrics['orders_submitted']}건 | {gate_status} |")
    md.append("")
    
    # 다음 단계
    md.append("## 🚀 다음 단계")
    md.append("")
    if metrics["gate_1m_pass"]:
        md.append("✅ Gate_1M PASS → 경량 튜닝 진행")
        md.append("")
        md.append("**경량 튜닝 계획**:")
        md.append("- range_min_score: {2, 3, 4}")
        md.append("- trend_min_score: {2, 3}")
        md.append("- min_rr_required: {1.0, 1.2} (Guard ON 시)")
        md.append("- cooldown_candles: {0, 1} (Guard ON 시)")
    else:
        md.append("❌ Gate_1M FAIL → 전략 재평가 필요")
        md.append("")
        md.append("**권장 조치**:")
        md.append("- Score Threshold 완화 (range_min_score, trend_min_score 낮추기)")
        md.append("- 필터 완화 (min_atr_pct, min_volume_ratio)")
        md.append("- 전략 로직 재검토")
    md.append("")
    
    # 파일 저장
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    
    print(f"✅ Markdown 리포트 저장: {output_path}")


def generate_json_report(metrics, output_path):
    """JSON 리포트 생성"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON 리포트 저장: {output_path}")


def main():
    """메인 함수"""
    
    print("=" * 80)
    print("PHASE29-4: V4 1개월 백테스트 성능 분석")
    print("=" * 80)
    
    # Summary JSON 로드
    summary_path = project_root / "reports" / "backtest" / "phase29_4_0" / "btc5m_baseline_v4_month_gate_summary.json"
    
    if not summary_path.exists():
        print(f"❌ Summary JSON이 존재하지 않습니다: {summary_path}")
        return False
    
    print(f"✅ Summary JSON 로드: {summary_path.name}\n")
    
    summary = load_summary_json(summary_path)
    
    # 메트릭 계산
    print("📊 메트릭 계산 중...")
    metrics = calculate_metrics(summary)
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 핵심 메트릭")
    print("=" * 80)
    print(f"  신호 발생: {metrics['strategy_signals_true']:,}건 / {metrics['strategy_signals_total']:,}개 ({metrics['signal_rate']:.2f}%)")
    print(f"  LONG/SHORT: {metrics['long_signals']:,}건 / {metrics['short_signals']:,}건")
    print(f"  Regime: Trend {metrics['regime_trend_pct']:.1f}%, Range {metrics['regime_range_pct']:.1f}%")
    print(f"  Guard 통과: {metrics['orders_submitted']:,}건 / {metrics['strategy_signals_true']:,}건 ({metrics['guard_pass_rate']:.2f}%)")
    
    print("\n" + "=" * 80)
    print("✅ Gate_1M 판정")
    print("=" * 80)
    gate_status = "✅ PASS" if metrics["gate_1m_pass"] else "❌ FAIL"
    print(f"  거래 건수: {metrics['orders_submitted']}건 (목표: 80~240건) → {gate_status}")
    
    # 리포트 생성
    print("\n" + "=" * 80)
    print("📄 리포트 생성")
    print("=" * 80)
    
    output_dir = project_root / "reports" / "analysis" / "PHASE29"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    md_path = output_dir / "phase29_4_1_v4_month_performance.md"
    json_path = output_dir / "phase29_4_1_v4_month_performance.json"
    
    generate_markdown_report(metrics, md_path)
    generate_json_report(metrics, json_path)
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
