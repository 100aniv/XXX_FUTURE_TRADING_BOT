#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_metrics_from_db_snapshot() 함수 PostgreSQL 전환
================================================
SQLite DB 파일 복사 → PostgreSQL trial_id 기반 조회
"""
import sys
import re
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 업데이트 대상 파일
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

# 교체할 패턴 (정규식)
OLD_PATTERN = r'''            # Fallback: 로그 파싱 실패 시 DB 스냅샷으로 계산
            def _metrics_from_db_snapshot\(\) -> Dict\[str, Any\]:
                try:
                    # Prefer per-segment DB if exists, then env override, then default
                    from pathlib import Path as _P
                    db_src_candidates = \[\]
                    try:
                        db_src_candidates\.append\(db_temp\)
                    except Exception:
                        pass
                    env_db = os\.getenv\('BACKTEST_DB_PATH'\)
                    if env_db:
                        db_src_candidates\.append\(_P\(env_db\)\)
                    db_src_candidates\.append\(project_root / 'data' / 'db' / 'trading\.db'\)

                    snapshot_dir = study_dir / 'db'
                    snapshot_dir\.mkdir\(exist_ok=True\)
                    db_snap = snapshot_dir / f"trial_\{trial\.number:04d\}_seg\{idx\+1\}\.db"
                    for _src in db_src_candidates:
                        try:
                            if _src and _src\.exists\(\):
                                shutil\.copy2\(_src, db_snap\)
                                total_score, scores_db = calculate_tuning_score_from_db\(str\(db_snap\)\)
                                break
                        except Exception:
                            continue
                    else:
                        return metrics
                    m = scores_db\.get\('metrics', \{\}\)'''

NEW_CODE = '''            # Fallback: 로그 파싱 실패 시 PostgreSQL에서 직접 조회
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


def fix_file(filepath: Path):
    """파일의 _metrics_from_db_snapshot 함수 수정"""
    print(f"📝 {filepath.name} 수정 중...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # calculate_tuning_score_from_db 호출 확인
        if 'calculate_tuning_score_from_db' not in content:
            print(f"   ℹ️  이미 수정됨 (calculate_tuning_score_from_db 없음)")
            return True
        
        # 간단한 문자열 교체 (정규식 대신)
        old_block_start = "# Fallback: 로그 파싱 실패 시 DB 스냅샷으로 계산"
        old_block_end = "m = scores_db.get('metrics', {})"
        
        if old_block_start in content and old_block_end in content:
            # 블록 찾기
            start_idx = content.find(old_block_start)
            end_idx = content.find(old_block_end, start_idx) + len(old_block_end)
            
            if start_idx != -1 and end_idx > start_idx:
                # 교체
                new_content = content[:start_idx] + NEW_CODE + content[end_idx:]
                
                # 저장
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"   ✅ _metrics_from_db_snapshot() 함수 수정 완료")
                return True
            else:
                print(f"   ⚠️  블록을 찾을 수 없음")
                return False
        else:
            print(f"   ⚠️  패턴 매칭 실패")
            return False
        
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    print("=" * 80)
    print("🚀 _metrics_from_db_snapshot() 함수 PostgreSQL 전환")
    print("=" * 80)
    print()
    
    success_count = 0
    for filepath_str in target_files:
        filepath = project_root / filepath_str
        if filepath.exists():
            if fix_file(filepath):
                success_count += 1
        else:
            print(f"⚠️  {filepath.name} 파일 없음")
        print()
    
    print("=" * 80)
    print(f"📊 결과: {success_count}/{len(target_files)} 파일 수정 완료")
    print("=" * 80)


if __name__ == '__main__':
    main()
