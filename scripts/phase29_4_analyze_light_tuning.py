"""
PHASE29-4: V4 경량 튜닝 결과 분석 스크립트

목적: 24개 튜닝 결과를 집계하고 AC3 기준 평가, 상위 3개 조합 선정
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_tuning_results():
    """튜닝 결과 JSON 로드"""
    
    tuning_json_path = project_root / "tuning_results" / "phase29_4_v4_light_tuning.json"
    
    if not tuning_json_path.exists():
        print(f"❌ 튜닝 결과 JSON이 존재하지 않습니다: {tuning_json_path}")
        return None
    
    with open(tuning_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_ac3(result):
    """AC3 평가: Win Rate ≥ 45%, Max DD ≤ 15%
    
    주의: 현재 Summary JSON에는 Win Rate/Max DD 정보가 없음
    → 거래 건수와 Guard 통과율로 간접 평가
    """
    
    # 현재 가능한 평가: 거래 건수 기준
    trades = result.get("orders_submitted", 0)
    
    # Gate_1M 기준: 80~240건
    gate_1m_pass = 80 <= trades <= 240
    
    # AC3는 Win Rate/Max DD가 필요하지만 현재는 불가
    # 임시로 거래 건수만 체크
    ac3_pass = gate_1m_pass
    
    return {
        "ac3_pass": ac3_pass,
        "gate_1m_pass": gate_1m_pass,
        "trades": trades,
        "note": "Win Rate/Max DD는 Summary JSON에 없어 평가 불가, 거래 건수로만 판정"
    }


def rank_results(results):
    """결과 순위 매기기
    
    우선순위:
    1. AC3 만족 (거래 건수 기준)
    2. 거래 건수 (많을수록 좋음, 단 240건 초과는 오버트레이딩)
    3. Guard 통과율 (높을수록 좋음)
    """
    
    # AC3 평가 추가
    for result in results:
        if result["status"] == "SUCCESS":
            ac3_eval = evaluate_ac3(result)
            result.update(ac3_eval)
        else:
            result["ac3_pass"] = False
            result["gate_1m_pass"] = False
            result["note"] = "백테스트 실패"
    
    # 정렬: AC3 PASS → 거래 건수 (80~240 범위 선호) → Guard 통과율
    def sort_key(r):
        if r["status"] != "SUCCESS":
            return (0, 0, 0)
        
        ac3 = 1 if r.get("ac3_pass", False) else 0
        trades = r.get("orders_submitted", 0)
        
        # 거래 건수 점수: 80~240 범위 내가 최고, 범위 밖은 페널티
        if 80 <= trades <= 240:
            trades_score = trades
        elif trades < 80:
            trades_score = trades * 0.5  # 부족한 것은 50% 페널티
        else:
            trades_score = 240 - (trades - 240) * 0.5  # 초과는 페널티
        
        guard_pass_rate = r.get("guard_pass_rate", 0)
        
        return (ac3, trades_score, guard_pass_rate)
    
    sorted_results = sorted(results, key=sort_key, reverse=True)
    
    return sorted_results


def generate_markdown_report(tuning_data, ranked_results):
    """Markdown 리포트 생성"""
    
    md = []
    md.append("# PHASE29-4.2: V4 경량 튜닝 결과")
    md.append("")
    md.append(f"**분석일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**튜닝 실행**: {tuning_data.get('timestamp', 'N/A')}")
    md.append(f"**총 조합**: {tuning_data.get('total_configs', 0)}개")
    md.append("")
    md.append("---")
    md.append("")
    
    # Executive Summary
    md.append("## 📊 Executive Summary")
    md.append("")
    
    success_count = len([r for r in ranked_results if r["status"] == "SUCCESS"])
    ac3_pass_count = len([r for r in ranked_results if r.get("ac3_pass", False)])
    
    md.append(f"- **성공**: {success_count}/{tuning_data.get('total_configs', 0)}개")
    md.append(f"- **AC3 PASS**: {ac3_pass_count}개 (거래 건수 80~240건 기준)")
    md.append("")
    md.append("**주의**: 현재 Summary JSON에는 Win Rate/Max DD 정보가 없어 AC3 완전 평가 불가")
    md.append("")
    
    # 튜닝 그리드
    md.append("## 🎯 튜닝 그리드")
    md.append("")
    md.append("| 파라미터 | 값 |")
    md.append("|----------|-----|")
    md.append("| range_min_score | {2, 3, 4} (3개) |")
    md.append("| trend_min_score | {2, 3} (2개) |")
    md.append("| min_rr_required | {1.0, 1.2} (2개) |")
    md.append("| cooldown_candles | {0, 1} (2개) |")
    md.append("| **총 조합** | **24개** |")
    md.append("")
    
    # 상위 3개 조합
    md.append("## 🏆 상위 3개 조합")
    md.append("")
    
    top3 = ranked_results[:3]
    
    for i, r in enumerate(top3, 1):
        md.append(f"### {i}. {r['run_id']}")
        md.append("")
        md.append("| 항목 | 값 |")
        md.append("|------|-----|")
        md.append(f"| **range_min_score** | {r.get('range_min_score', 'N/A')} |")
        md.append(f"| **trend_min_score** | {r.get('trend_min_score', 'N/A')} |")
        md.append(f"| **min_rr_required** | {r.get('min_rr_required', 'N/A')} |")
        md.append(f"| **cooldown_candles** | {r.get('cooldown_candles', 'N/A')} |")
        md.append(f"| 체결 건수 | {r.get('orders_submitted', 0)}건 |")
        md.append(f"| 신호 발생 | {r.get('signal_true', 0)}건 |")
        md.append(f"| Guard 통과율 | {r.get('guard_pass_rate', 0):.1f}% |")
        md.append(f"| LONG 신호 | {r.get('long_signals', 0)}건 |")
        md.append(f"| SHORT 신호 | {r.get('short_signals', 0)}건 |")
        md.append(f"| AC3 판정 | {'✅ PASS' if r.get('ac3_pass', False) else '❌ FAIL'} (거래 건수 기준) |")
        md.append("")
    
    # 전체 결과 테이블
    md.append("## 📋 전체 결과 (상위 10개)")
    md.append("")
    md.append("| 순위 | run_id | Range | Trend | RR | CD | 체결 | AC3 |")
    md.append("|------|--------|-------|-------|----|----|------|-----|")
    
    for i, r in enumerate(ranked_results[:10], 1):
        ac3_status = "✅" if r.get("ac3_pass", False) else "❌"
        md.append(f"| {i} | {r['run_id']} | {r.get('range_min_score', '-')} | {r.get('trend_min_score', '-')} | {r.get('min_rr_required', '-')} | {r.get('cooldown_candles', '-')} | {r.get('orders_submitted', 0)} | {ac3_status} |")
    
    md.append("")
    
    # 실패 조합
    failed = [r for r in ranked_results if r["status"] != "SUCCESS"]
    if failed:
        md.append("## ❌ 실패 조합")
        md.append("")
        for r in failed:
            md.append(f"- {r['run_id']}: {r.get('note', 'Unknown error')}")
        md.append("")
    
    # 분석 코멘트
    md.append("## 💡 분석 코멘트")
    md.append("")
    md.append("### 거래 건수 분포")
    md.append("")
    
    trades_80_240 = len([r for r in ranked_results if r["status"] == "SUCCESS" and 80 <= r.get("orders_submitted", 0) <= 240])
    trades_below_80 = len([r for r in ranked_results if r["status"] == "SUCCESS" and r.get("orders_submitted", 0) < 80])
    trades_above_240 = len([r for r in ranked_results if r["status"] == "SUCCESS" and r.get("orders_submitted", 0) > 240])
    
    md.append(f"- **80~240건 (Gate_1M 범위)**: {trades_80_240}개")
    md.append(f"- **80건 미만 (신호 부족)**: {trades_below_80}개")
    md.append(f"- **240건 초과 (오버트레이딩)**: {trades_above_240}개")
    md.append("")
    
    ### Score Threshold 영향
    md.append("### Score Threshold 영향")
    md.append("")
    
    avg_trades_by_range_score = {}
    for score in [2, 3, 4]:
        score_results = [r for r in ranked_results if r["status"] == "SUCCESS" and r.get("range_min_score") == score]
        if score_results:
            avg_trades = sum(r.get("orders_submitted", 0) for r in score_results) / len(score_results)
            avg_trades_by_range_score[score] = avg_trades
    
    for score, avg in sorted(avg_trades_by_range_score.items()):
        md.append(f"- **range_min_score={score}**: 평균 {avg:.1f}건 체결")
    
    md.append("")
    
    # 다음 단계
    md.append("## 🚀 다음 단계")
    md.append("")
    md.append("### AC3 완전 평가를 위한 추가 작업")
    md.append("")
    md.append("현재 Summary JSON에는 **Win Rate, Max DD 정보가 없습니다.**")
    md.append("")
    md.append("**옵션 A**: Engine 또는 Reporter를 수정하여 Summary JSON에 Win Rate/Max DD 추가")
    md.append("- 장점: 향후 모든 백테스트에서 자동 수집")
    md.append("- 단점: 코어 엔진 수정 필요")
    md.append("")
    md.append("**옵션 B**: 별도 분석 스크립트로 거래 로그에서 Win Rate/Max DD 계산")
    md.append("- 장점: 엔진 수정 불필요")
    md.append("- 단점: 거래 로그가 필요, 추가 스크립트 작성")
    md.append("")
    md.append("**권장**: 옵션 A (Engine 수정)를 후속 PHASE에서 진행")
    md.append("")
    
    # PHASE29-4 역할
    md.append("## 📝 PHASE29-4의 역할")
    md.append("")
    md.append("이 PHASE의 목표는:")
    md.append("- ✅ V4 전략이 1개월 기준으로 실질적인 후보가 될 수 있는지 **성능 탐색**")
    md.append("- ✅ 다양한 파라미터 조합으로 **신호 빈도 범위 확인**")
    md.append("- ✅ Guard 설정이 V4에 미치는 영향 분석")
    md.append("")
    md.append("**전략 최종 선정 및 Ensemble 반영은 후속 PHASE에서 진행**합니다.")
    md.append("")
    
    return "\n".join(md)


def generate_json_report(ranked_results):
    """JSON 리포트 생성"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_configs": len(ranked_results),
        "success_count": len([r for r in ranked_results if r["status"] == "SUCCESS"]),
        "ac3_pass_count": len([r for r in ranked_results if r.get("ac3_pass", False)]),
        "top3": ranked_results[:3],
        "all_results": ranked_results
    }
    
    return report


def main():
    """메인 함수"""
    
    print("=" * 80)
    print("PHASE29-4: V4 경량 튜닝 결과 분석")
    print("=" * 80)
    print()
    
    # 튜닝 결과 로드
    print("📂 튜닝 결과 JSON 로드 중...")
    tuning_data = load_tuning_results()
    
    if not tuning_data:
        return False
    
    results = tuning_data.get("results", [])
    print(f"✅ {len(results)}개 결과 로드 완료\n")
    
    # 순위 매기기
    print("📊 결과 순위 매기는 중...")
    ranked_results = rank_results(results)
    print(f"✅ 순위 매기기 완료\n")
    
    # 리포트 생성
    print("=" * 80)
    print("📄 리포트 생성")
    print("=" * 80)
    print()
    
    output_dir = project_root / "reports" / "analysis" / "PHASE29"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Markdown
    md_path = output_dir / "phase29_4_2_v4_light_tuning.md"
    md_content = generate_markdown_report(tuning_data, ranked_results)
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"✅ Markdown 리포트: {md_path}")
    
    # JSON
    json_path = output_dir / "phase29_4_2_v4_light_tuning.json"
    json_report = generate_json_report(ranked_results)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON 리포트: {json_path}")
    
    # 요약 출력
    print("\n" + "=" * 80)
    print("📊 분석 결과 요약")
    print("=" * 80)
    print()
    
    success_count = len([r for r in ranked_results if r["status"] == "SUCCESS"])
    ac3_pass_count = len([r for r in ranked_results if r.get("ac3_pass", False)])
    
    print(f"  성공: {success_count}/{len(results)}개")
    print(f"  AC3 PASS: {ac3_pass_count}개 (거래 건수 기준)")
    print()
    print("  상위 3개 조합:")
    
    for i, r in enumerate(ranked_results[:3], 1):
        print(f"    {i}. {r['run_id']}: {r.get('orders_submitted', 0)}건")
        print(f"       Range: {r.get('range_min_score', '-')}, Trend: {r.get('trend_min_score', '-')}, RR: {r.get('min_rr_required', '-')}, CD: {r.get('cooldown_candles', '-')}")
        print(f"       AC3: {'✅ PASS' if r.get('ac3_pass', False) else '❌ FAIL'}")
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
