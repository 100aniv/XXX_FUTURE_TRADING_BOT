#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE36-2 S6: Telemetry Checkpoint 자동 리포트 생성기
====================================================
목적: AI가 6시간/1개월 모니터링 대신 checkpoint JSON → markdown 자동 생성

Usage:
    python scripts/report_telemetry_checkpoints.py \
        --checkpoint-dir logs/checkpoints/phase36_2_s6_shadow_smoke \
        --output docs/PHASE36/PHASE36_2_S6_LIVE_SHADOW_SMOKE_REPORT.md \
        --title "PHASE36-2 S6 Live Shadow Smoke 20m"

입력: checkpoint json 폴더
출력: markdown 1개 (요약 테이블 + funnel + block_reasons TopN + 기간/에러/주문수)
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE36-2 S6: Checkpoint JSON → Markdown 자동 리포트',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        required=True,
        help='Checkpoint JSON 폴더 경로'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='출력 Markdown 파일 경로'
    )
    
    parser.add_argument(
        '--title',
        type=str,
        default='Telemetry Checkpoint Report',
        help='보고서 제목'
    )
    
    return parser.parse_args()


def load_checkpoints(checkpoint_dir: Path):
    """Checkpoint JSON 파일들을 로드"""
    checkpoint_files = sorted(checkpoint_dir.glob('telemetry_checkpoint_*.json'))
    
    if not checkpoint_files:
        print(f"⚠️  Checkpoint 파일 없음: {checkpoint_dir}")
        return []
    
    checkpoints = []
    for file_path in checkpoint_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_file'] = file_path.name
                checkpoints.append(data)
        except Exception as e:
            print(f"❌ {file_path.name} 로드 실패: {e}")
    
    return checkpoints


def generate_report(checkpoints: list, title: str) -> str:
    """Markdown 보고서 생성"""
    if not checkpoints:
        return f"# {title}\n\n❌ **Checkpoint 데이터 없음**\n"
    
    # 최종 checkpoint (가장 높은 카운터 값)
    final_checkpoint = max(checkpoints, key=lambda x: x['counters'].get('signal_evaluated_total', 0))
    counters = final_checkpoint['counters']
    
    # 시간 정보
    first_ts = checkpoints[0].get('timestamp', 'N/A')
    last_ts = final_checkpoint.get('timestamp', 'N/A')
    
    # Block reasons 집계
    block_reasons = counters.get('block_reasons', {})
    total_blocks = sum(block_reasons.values())
    
    # Markdown 생성
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**작성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**시작**: {first_ts}")
    lines.append(f"**종료**: {last_ts}")
    lines.append(f"**Checkpoint 수**: {len(checkpoints)}개")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 1. 실행 요약
    lines.append("## 1. 실행 요약")
    lines.append("")
    lines.append("| 항목 | 값 |")
    lines.append("|------|-----|")
    lines.append(f"| Signal Evaluated | {counters.get('signal_evaluated_total', 0)} |")
    lines.append(f"| Signal Passed | {counters.get('signal_passed_total', 0)} |")
    lines.append(f"| Order Submitted | {counters.get('order_submitted_total', 0)} |")
    lines.append(f"| Order Filled | {counters.get('order_filled_total', 0)} |")
    lines.append(f"| DB Persist Called | {counters.get('db_persist_called', 0)} |")
    lines.append(f"| DB Insert Success | {counters.get('db_insert_success', 0)} |")
    lines.append(f"| DB Insert Failed | {counters.get('db_insert_failed', 0)} |")
    lines.append(f"| Trades per Hour | {counters.get('trades_per_hour', 0):.1f} |")
    lines.append(f"| Elapsed Hours | {counters.get('elapsed_hours', 0):.2f} |")
    lines.append("")
    
    # 2. Signal Funnel
    lines.append("## 2. Signal Funnel")
    lines.append("")
    signal_evaluated = counters.get('signal_evaluated_total', 0)
    signal_passed = counters.get('signal_passed_total', 0)
    order_submitted = counters.get('order_submitted_total', 0)
    order_filled = counters.get('order_filled_total', 0)
    
    if signal_evaluated > 0:
        passed_rate = (signal_passed / signal_evaluated) * 100
        submitted_rate = (order_submitted / signal_evaluated) * 100 if signal_evaluated > 0 else 0
        filled_rate = (order_filled / signal_evaluated) * 100 if signal_evaluated > 0 else 0
    else:
        passed_rate = submitted_rate = filled_rate = 0
    
    lines.append("```")
    lines.append(f"Signal Evaluated: {signal_evaluated}")
    lines.append(f"        ↓ ({passed_rate:.1f}%)")
    lines.append(f"Signal Passed:    {signal_passed}")
    lines.append(f"        ↓ ({submitted_rate:.1f}%)")
    lines.append(f"Order Submitted:  {order_submitted}")
    lines.append(f"        ↓ ({filled_rate:.1f}%)")
    lines.append(f"Order Filled:     {order_filled}")
    lines.append("```")
    lines.append("")
    
    # 3. Block Reasons Top 10
    lines.append("## 3. Block Reasons (Top 10)")
    lines.append("")
    if block_reasons:
        lines.append("| Reason | Count | Percentage |")
        lines.append("|--------|-------|------------|")
        
        sorted_reasons = sorted(block_reasons.items(), key=lambda x: x[1], reverse=True)
        for reason, count in sorted_reasons[:10]:
            pct = (count / total_blocks * 100) if total_blocks > 0 else 0
            lines.append(f"| {reason} | {count} | {pct:.1f}% |")
        
        lines.append("")
        lines.append(f"**Total Block Reasons**: {total_blocks}개")
    else:
        lines.append("❌ **Block Reasons 데이터 없음**")
    lines.append("")
    
    # 4. Checkpoint 진행 상황
    lines.append("## 4. Checkpoint 진행 상황")
    lines.append("")
    lines.append("| Checkpoint | Timestamp | Signal Eval | Signal Pass | Order Submit | Order Fill | Trades/h |")
    lines.append("|------------|-----------|-------------|-------------|--------------|------------|----------|")
    
    for cp in checkpoints:
        label = cp.get('label', 'N/A')
        ts = cp.get('timestamp', 'N/A')
        cnt = cp['counters']
        lines.append(
            f"| {label} | {ts} | {cnt.get('signal_evaluated_total', 0)} | "
            f"{cnt.get('signal_passed_total', 0)} | {cnt.get('order_submitted_total', 0)} | "
            f"{cnt.get('order_filled_total', 0)} | {cnt.get('trades_per_hour', 0):.1f} |"
        )
    
    lines.append("")
    
    # 5. 최종 판정
    lines.append("## 5. 최종 판정")
    lines.append("")
    
    has_errors = counters.get('db_insert_failed', 0) > 0
    has_orders = counters.get('order_submitted_total', 0) > 0
    
    if has_errors:
        lines.append("❌ **FAIL**: DB Insert 에러 발생")
    elif has_orders:
        lines.append("⚠️ **WARNING**: 주문 제출 발생 (Shadow Mode 위반 가능)")
    else:
        lines.append("✅ **PASS**: 에러 없음, 주문 제출 없음")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by `scripts/report_telemetry_checkpoints.py` on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(lines)


def main():
    """메인 진입점"""
    args = parse_args()
    
    checkpoint_dir = Path(args.checkpoint_dir)
    output_file = Path(args.output)
    
    print(f"📂 Checkpoint 디렉토리: {checkpoint_dir}")
    print(f"📄 출력 파일: {output_file}")
    
    # 1. Checkpoint 로드
    checkpoints = load_checkpoints(checkpoint_dir)
    
    if not checkpoints:
        print("❌ Checkpoint 파일을 찾을 수 없습니다.")
        return 1
    
    print(f"✅ {len(checkpoints)}개 Checkpoint 로드 완료")
    
    # 2. 보고서 생성
    report_md = generate_report(checkpoints, args.title)
    
    # 3. 파일 저장
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_md)
    
    print(f"✅ 보고서 생성 완료: {output_file}")
    print(f"📊 Signal Evaluated: {checkpoints[-1]['counters'].get('signal_evaluated_total', 0)}")
    print(f"📊 Order Submitted: {checkpoints[-1]['counters'].get('order_submitted_total', 0)}")
    print(f"📊 Order Filled: {checkpoints[-1]['counters'].get('order_filled_total', 0)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
