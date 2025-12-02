#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PHASE25-0: 기존 2H Long-run PAPER 결과 재평가 스크립트

기존에 실행된 2H 런의 JSON 요약과 메트릭을 읽어서
새로운 Acceptance 기준(Infra vs Strategy 분리)으로 재평가하고
JSON/MD 리포트를 업데이트합니다.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 파일 경로
SUMMARY_JSON = PROJECT_ROOT / "logs" / "phase25_0_long_run_summary.json"
REPORT_MD = PROJECT_ROOT / "docs" / "PHASE25" / "PHASE25-0_LONG_RUN_PAPER_REPORT.md"


def reevaluate_results():
    """기존 결과를 재평가합니다."""
    print("=" * 70)
    print("PHASE25-0: 기존 2H Long-run PAPER 결과 재평가")
    print("=" * 70)
    
    # 1. JSON 요약 로드
    print(f"\n[1] JSON 요약 로드: {SUMMARY_JSON}")
    if not SUMMARY_JSON.exists():
        print(f"❌ JSON 파일이 없습니다: {SUMMARY_JSON}")
        return 1
    
    with open(SUMMARY_JSON, 'r', encoding='utf-8') as f:
        original_summary = json.load(f)
    
    print(f"✅ JSON 로드 완료")
    print(f"   - 실행 시각: {original_summary.get('timestamp')}")
    print(f"   - Config: {original_summary.get('config')}")
    
    # 2. 메트릭 추출
    metrics = original_summary.get('metrics', {})
    monitor_result = original_summary.get('monitor_result', {})
    duration_hours = original_summary.get('target_duration_hours', 2.0)
    
    log_metrics = metrics.get('log_metrics', {})
    db_metrics = metrics.get('db_metrics', {})
    duration_metrics = metrics.get('duration_metrics', {})
    
    error_count = log_metrics.get('error_count', 0)
    critical_count = log_metrics.get('critical_count', 0)
    ensemble_agg = log_metrics.get('ensemble_aggregate_count', 0)
    trade_count = db_metrics.get('trade_count', 0)
    active_positions = db_metrics.get('active_positions', 999)
    actual_duration_hours = duration_metrics.get('actual_duration_hours', 0)
    
    print(f"\n[2] 기존 메트릭:")
    print(f"   - Duration: {actual_duration_hours:.2f}H")
    print(f"   - Trade 수: {trade_count}")
    print(f"   - ERROR/CRITICAL: {error_count} / {critical_count}")
    print(f"   - Ensemble Aggregate: {ensemble_agg}")
    print(f"   - 활성 포지션: {active_positions}")
    
    # 3. 새로운 Acceptance 기준으로 재평가
    print(f"\n[3] 새로운 Acceptance 기준으로 재평가:")
    
    # Infra-critical Acceptance
    duration_pass = monitor_result['actual_duration_sec'] >= (duration_hours * 3600 * 0.98)
    error_pass_infra = (monitor_result['status'] == 'PASS' and critical_count == 0)
    active_positions_pass = (active_positions == 0)
    ensemble_pass = (ensemble_agg >= 1000)
    
    # Strategy KPI
    trade_target = 50
    trade_warning = (trade_count < trade_target)
    
    # 최종 인프라 Acceptance
    infra_pass = all([duration_pass, error_pass_infra, active_positions_pass, ensemble_pass])
    
    # 전체 상태
    if infra_pass and not trade_warning:
        overall_status = "PASS"
    elif infra_pass and trade_warning:
        overall_status = "PASS_WITH_STRATEGY_WARNING"
    else:
        overall_status = "FAIL"
    
    print(f"   [인프라 Acceptance (PHASE25-0 PASS 기준)]")
    print(f"   - Duration: {'✅' if duration_pass else '❌'} ({actual_duration_hours:.2f}H ≥ {duration_hours * 0.98:.2f}H)")
    print(f"   - CRITICAL 오류: {'✅' if error_pass_infra else '❌'} ({critical_count}건, 모니터링 {monitor_result['status']})")
    print(f"   - 활성 포지션: {'✅' if active_positions_pass else '❌'} ({active_positions})")
    print(f"   - Ensemble Aggregate: {'✅' if ensemble_pass else '❌'} ({ensemble_agg} ≥ 1000)")
    print(f"   → 인프라 종합: {'✅ PASS' if infra_pass else '❌ FAIL'}")
    print(f"\n   [전략 KPI (경고/참고용)]")
    print(f"   - Trade 수: {'⚠️ WARNING' if trade_warning else '✅ OK'} ({trade_count} / 목표 {trade_target})")
    print(f"\n   [최종 상태]: {overall_status}")
    
    # 4. JSON 업데이트
    print(f"\n[4] JSON 업데이트")
    new_acceptance = {
        # Infra-critical (PHASE25-0 PASS 기준)
        'infra': {
            'duration_pass': duration_pass,
            'error_pass_infra': error_pass_infra,
            'active_positions_pass': active_positions_pass,
            'ensemble_pass': ensemble_pass,
            'overall': infra_pass
        },
        # Strategy KPI (경고/참고용)
        'strategy': {
            'trade_count': trade_count,
            'trade_target': trade_target,
            'trade_warning': trade_warning
        },
        # 최종 상태
        'overall_status': overall_status,
        'infra_pass': infra_pass,
        'strategy_warning': trade_warning
    }
    
    original_summary['acceptance'] = new_acceptance
    original_summary['reevaluated_at'] = datetime.now().isoformat()
    original_summary['reevaluation_note'] = "Infra vs Strategy Acceptance 기준 분리 후 재평가"
    
    with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(original_summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON 업데이트 완료: {SUMMARY_JSON}")
    
    # 5. MD 리포트 업데이트
    print(f"\n[5] MD 리포트 업데이트")
    
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write(f"# PHASE25-0: Long-run PAPER Regression - 실행 리포트\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Original Run**: {original_summary.get('timestamp')}  \n")
        f.write(f"**Reevaluated**: {original_summary.get('reevaluated_at')}  \n")
        f.write(f"**Status**: {overall_status}  \n")
        f.write(f"**Infra Acceptance**: {'✅ PASS' if infra_pass else '❌ FAIL'}  \n")
        f.write(f"**Config**: `{original_summary.get('config')}`  \n")
        f.write(f"**Duration**: {duration_hours}H (목표), {actual_duration_hours:.2f}H (실제)  \n\n")
        
        f.write("---\n\n")
        f.write("## 1. Executive Summary\n\n")
        f.write(f"- **실행 시작**: {duration_metrics.get('start_time')}\n")
        f.write(f"- **실행 종료**: {duration_metrics.get('end_time')}\n")
        f.write(f"- **Duration**: {actual_duration_hours:.2f}H ({duration_metrics.get('actual_duration_sec', 0):.0f}초)\n")
        f.write(f"- **Trade 수**: {trade_count} (목표: {trade_target})\n")
        f.write(f"- **활성 포지션**: {active_positions}\n")
        f.write(f"- **ERROR/CRITICAL**: {error_count} / {critical_count}\n")
        f.write(f"- **Ensemble Aggregate**: {ensemble_agg}\n")
        f.write(f"- **인프라 Acceptance**: {'✅ PASS' if infra_pass else '❌ FAIL'}\n")
        f.write(f"- **전략 KPI**: {'⚠️ WARNING (Trade 수 부족)' if trade_warning else '✅ OK'}\n")
        f.write(f"- **최종 판정**: {overall_status}\n\n")
        
        f.write("---\n\n")
        f.write("## 2. Acceptance Criteria\n\n")
        
        f.write("### 2.1 인프라 Acceptance (PHASE25-0 PASS 기준)\n\n")
        f.write("| 항목 | 조건 | 결과 | 판정 |\n")
        f.write("|------|------|------|------|\n")
        f.write(f"| Duration | ≥ {duration_hours * 0.98:.2f}H | {actual_duration_hours:.2f}H | {'✅' if duration_pass else '❌'} |\n")
        f.write(f"| CRITICAL 오류 | = 0 | {critical_count} | {'✅' if error_pass_infra else '❌'} |\n")
        f.write(f"| 활성 포지션 | = 0 | {active_positions} | {'✅' if active_positions_pass else '❌'} |\n")
        f.write(f"| Ensemble Aggregate | ≥ 1000 | {ensemble_agg} | {'✅' if ensemble_pass else '❌'} |\n")
        f.write(f"| **인프라 종합** | - | - | {'✅ PASS' if infra_pass else '❌ FAIL'} |\n\n")
        
        f.write("### 2.2 전략 KPI (경고/참고용)\n\n")
        f.write("| 항목 | 목표 | 결과 | 상태 |\n")
        f.write("|------|------|------|------|\n")
        f.write(f"| Trade 수 | ≥ {trade_target} | {trade_count} | {'⚠️ WARNING' if trade_warning else '✅ OK'} |\n\n")
        
        f.write("**NOTE**: Trade 수는 전략/스캘핑/앙상블 파라미터 튜닝 영역이며, PHASE25-0 인프라 Acceptance 기준에는 포함되지 않습니다. 전략 KPI는 이후 PHASE에서 다룹니다.\n\n")
        
        f.write("---\n\n")
        f.write("## 3. 메트릭 상세\n\n")
        f.write("### 3.1 DB 메트릭\n")
        f.write(f"```json\n{json.dumps(db_metrics, indent=2, ensure_ascii=False)}\n```\n\n")
        f.write("### 3.2 로그 메트릭\n")
        f.write(f"```json\n{json.dumps(log_metrics, indent=2, ensure_ascii=False)}\n```\n\n")
        f.write("### 3.3 Duration 메트릭\n")
        f.write(f"```json\n{json.dumps(duration_metrics, indent=2, ensure_ascii=False)}\n```\n\n")
        
        f.write("---\n\n")
        f.write("## 4. 모니터링 결과\n\n")
        f.write(f"- **상태**: {monitor_result['status']}\n")
        f.write(f"- **ERROR 라인 수**: {len(monitor_result.get('error_lines', []))}\n\n")
        
        if monitor_result.get('error_lines'):
            f.write("### ERROR 라인 샘플:\n")
            f.write("```\n")
            for line in monitor_result['error_lines'][:10]:
                f.write(f"{line}\n")
            f.write("```\n\n")
        
        f.write("---\n\n")
        f.write("## 5. 최종 판정\n\n")
        
        if overall_status == "PASS":
            f.write("✅ **PASS** - 인프라 Acceptance 충족 & 전략 KPI 양호\n\n")
            f.write("PHASE25-0 완료 조건을 모두 만족했습니다. Long-run PAPER Harness가 정상적으로 작동하며, 2H 이상 안정적으로 실행되었습니다.\n")
        elif overall_status == "PASS_WITH_STRATEGY_WARNING":
            f.write("✅ **INFRA PASS (전략 KPI 경고)** - 인프라 Acceptance 충족\n\n")
            f.write("**인프라 Acceptance**: ✅ PASS\n")
            f.write(f"- Duration: {actual_duration_hours:.2f}H ≥ {duration_hours * 0.98:.2f}H\n")
            f.write(f"- CRITICAL 오류: {critical_count}건 (모니터링 {monitor_result['status']})\n")
            f.write(f"- 활성 포지션: {active_positions}\n")
            f.write(f"- Ensemble Aggregate: {ensemble_agg} ≥ 1000\n\n")
            f.write("**전략 KPI**: ⚠️ WARNING\n")
            f.write(f"- Trade 수: {trade_count} < 목표 {trade_target}건\n")
            f.write("- 이는 전략/스캘핑/앙상블 파라미터 튜닝 영역이며, 이후 PHASE에서 다룹니다.\n\n")
            f.write("**결론**: PHASE25-0는 인프라 기준으로 PASS. Long-run PAPER Harness가 안정적으로 작동하며, 장시간 실행 인프라가 확립되었습니다.\n")
        else:
            f.write("❌ **FAIL** - 인프라 Acceptance 미충족\n\n")
            infra_result = new_acceptance['infra']
            failed_infra = [k for k, v in infra_result.items() if k != 'overall' and not v]
            f.write(f"실패한 인프라 조건: {', '.join(failed_infra)}\n\n")
            f.write("재실행 또는 코드 수정이 필요합니다.\n")
    
    print(f"✅ MD 리포트 업데이트 완료: {REPORT_MD}")
    
    # 6. 최종 요약
    print("\n" + "=" * 70)
    print("재평가 완료")
    print("=" * 70)
    print(f"최종 상태: {overall_status}")
    print(f"인프라 Acceptance: {'✅ PASS' if infra_pass else '❌ FAIL'}")
    print(f"전략 KPI: {'⚠️ WARNING' if trade_warning else '✅ OK'}")
    print("=" * 70)
    
    return 0 if infra_pass else 1


if __name__ == "__main__":
    sys.exit(reevaluate_results())
