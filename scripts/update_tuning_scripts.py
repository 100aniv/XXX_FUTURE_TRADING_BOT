#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
튜닝 스크립트 일괄 업데이트
==========================
SQLite DB 파일 복사 방식 → PostgreSQL trial_id 기반으로 전환
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 업데이트 대상 파일 (tune_scalping.py는 이미 수정됨)
target_files = [
    'scripts/tuning/tune_breakout.py',
    'scripts/tuning/tune_daytrade.py',
    'scripts/tuning/tune_reversion.py',
    'scripts/tuning/tune_scalping_backup.py',
    'scripts/tuning/tune_swing.py',
    'scripts/tuning/tune_template.py',
    'scripts/tuning/tune_trend.py',
    'scripts/tuning/tune_trend_template.py',
]

# 변경 패턴
changes = [
    {
        'old': 'from reports.trading_reporter import calculate_tuning_score_from_db',
        'new': 'from analytics.report_generator import generate_backtest_report'
    },
    {
        'old': '''            # 파일 override용 overlay 복제 (deep copy 필수!)
            cfg_eval = configs_dir / f"trial_{trial.number:04d}_seg{idx+1}.yml"
            seg_overlay = deep_merge({}, overlay)  # Deep copy via deep_merge
            if data_file is not None:
                seg_overlay = deep_merge(seg_overlay, {'backtest': {'data_file': str(data_file.name)}})
            _write_overlay_config(base_cfg, seg_overlay, cfg_eval)''',
        'new': '''            # 파일 override용 overlay 복제 (deep copy 필수!)
            cfg_eval = configs_dir / f"trial_{trial.number:04d}_seg{idx+1}.yml"
            seg_overlay = deep_merge({}, overlay)  # Deep copy via deep_merge
            if data_file is not None:
                seg_overlay = deep_merge(seg_overlay, {'backtest': {'data_file': str(data_file.name)}})
            
            # ⭐ trial_id 추가 (PostgreSQL 필터링용)
            trial_id = f"trial_{trial.number:04d}_seg{idx+1}"
            seg_overlay = deep_merge(seg_overlay, {'trial_id': trial_id})
            
            _write_overlay_config(base_cfg, seg_overlay, cfg_eval)'''
    },
    {
        'old_start': '            # Fallback: 로그 파싱 실패 시 DB 스냅샷으로 계산',
        'old_end': '                    m = scores_db.get(\'metrics\', {})',
        'new': '''            # Fallback: 로그 파싱 실패 시 PostgreSQL에서 직접 조회
            def _metrics_from_db_snapshot() -> Dict[str, Any]:
                try:
                    # ⭐ PostgreSQL trial_id 기반 리포트 생성
                    result = generate_backtest_report(
                        trial_id=trial_id,
                        sinks=["log"]  # 로그만 출력
                    )
                    
                    if result.get('status') != 'success':
                        return metrics
                    
                    total_score = result.get('total_score', 0)
                    m = result.get('metrics', {})'''
    }
]

def update_file(filepath: Path):
    """파일 업데이트"""
    print(f"📝 {filepath.name} 업데이트 중...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 변경 1: import 문
        if changes[0]['old'] in content:
            content = content.replace(changes[0]['old'], changes[0]['new'])
            print(f"   ✅ import 문 변경")
        
        # 변경 2: trial_id 추가
        if changes[1]['old'] in content:
            content = content.replace(changes[1]['old'], changes[1]['new'])
            print(f"   ✅ trial_id 추가")
        
        # 변경 3: PostgreSQL 조회 (복잡한 패턴이므로 수동 확인 필요)
        # 이 부분은 파일마다 약간씩 다를 수 있으므로 경고만 출력
        if 'calculate_tuning_score_from_db' in content:
            print(f"   ⚠️  calculate_tuning_score_from_db 호출이 남아있음 - 수동 확인 필요")
        
        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ {filepath.name} 저장 완료\n")
        return True
        
    except Exception as e:
        print(f"   ❌ 오류: {e}\n")
        return False


def main():
    """메인 함수"""
    print("=" * 80)
    print("🚀 튜닝 스크립트 일괄 업데이트 시작")
    print("=" * 80)
    print()
    
    success_count = 0
    for filepath_str in target_files:
        filepath = project_root / filepath_str
        if filepath.exists():
            if update_file(filepath):
                success_count += 1
        else:
            print(f"⚠️  {filepath.name} 파일 없음\n")
    
    print("=" * 80)
    print(f"📊 결과: {success_count}/{len(target_files)} 파일 업데이트 완료")
    print("=" * 80)
    print()
    print("⚠️  주의: calculate_tuning_score_from_db 호출 부분은 수동 확인이 필요합니다.")
    print("   각 파일을 열어서 _metrics_from_db_snapshot() 함수를 확인하세요.")
    print()


if __name__ == '__main__':
    main()
