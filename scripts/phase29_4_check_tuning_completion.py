"""
PHASE29-4: 튜닝 완료 여부 확인 스크립트

목적: 24개 백테스트 완료 여부를 빠르게 확인
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_completion():
    """24개 summary JSON 파일 생성 여부 확인"""
    
    output_dir = project_root / "reports" / "backtest" / "phase29_4_1"
    
    if not output_dir.exists():
        print(f"❌ 출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return False
    
    # 예상되는 24개 run_id
    range_scores = [2, 3, 4]
    trend_scores = [2, 3]
    min_rrs = [1.0, 1.2]
    cooldowns = [0, 1]
    
    expected_files = []
    for r in range_scores:
        for t in trend_scores:
            for rr in min_rrs:
                for cd in cooldowns:
                    run_id = f"phase29_4_tuning_r{r}_t{t}_rr{rr}_cd{cd}"
                    expected_files.append(f"{run_id}_summary.json")
    
    # 실제 파일 확인
    existing_files = list(output_dir.glob("*.json"))
    existing_names = [f.name for f in existing_files]
    
    completed = []
    missing = []
    
    for expected in expected_files:
        if expected in existing_names:
            completed.append(expected)
        else:
            missing.append(expected)
    
    # 결과 출력
    print("=" * 80)
    print("PHASE29-4: 튜닝 완료 여부 확인")
    print("=" * 80)
    print()
    print(f"✅ 완료: {len(completed)}/24개")
    print(f"⏳ 대기: {len(missing)}/24개")
    print()
    
    if missing:
        print("⏳ 아직 완료되지 않은 파일:")
        for m in missing:
            print(f"  - {m}")
        print()
        print("💡 백테스트가 아직 실행 중입니다. 잠시 후 다시 확인하세요.")
        return False
    else:
        print("✅ 모든 백테스트가 완료되었습니다!")
        print()
        print("다음 단계:")
        print("  1. python scripts/phase29_4_analyze_light_tuning.py")
        print("  2. PHASE_ROADMAP 업데이트")
        print("  3. Git 커밋")
        return True


if __name__ == "__main__":
    success = check_completion()
    sys.exit(0 if success else 1)
