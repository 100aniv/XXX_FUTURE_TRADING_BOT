#!/usr/bin/env python3
"""
Scalping 코드를 기준으로 나머지 5개 튜너의 로그 부분을 완전히 재작성
"""
from pathlib import Path
import re

# Scalping의 올바른 코드 블록
correct_file_start = """        for idx, data_file in enumerate(eval_files):
            # 📄 파일 처리 시작 표시
            filename = data_file.name if data_file else 'config_default'
            print(f"  📄 [{idx+1}/{len(eval_files)}] {filename}... 백테스트 실행 중", flush=True)
            
            # 파일 override용 overlay 복제"""

correct_file_result = """            # 📊 파일별 상세 결과 출력
            win_rate = metrics.get('win_rate', 0.0)
            rr = metrics.get('rr_realized', 0.0)
            pf = metrics.get('profit_factor', 0.0)
            roi = metrics.get('roi_pct', 0.0)
            grade_str = metrics.get('grade', '?')
            print(f"     ✅ 완료: Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)"""

correct_final_result = """        # 등급 계산
        if score >= 80:
            grade_emoji = "🎉"
            grade = "S"
        elif score >= 70:
            grade_emoji = "✅"
            grade = "A"
        elif score >= 60:
            grade_emoji = "⚠️"
            grade = "B"
        elif score >= 50:
            grade_emoji = "⚠️"
            grade = "C"
        elif score >= 40:
            grade_emoji = "❌"
            grade = "D"
        else:
            grade_emoji = "❌"
            grade = "FAIL"
        
        # 🎯 Trial 결과 출력 (매 trial마다)
        print(f"\\n  🎯 Trial #{trial.number} 결과:", flush=True)
        print(f"     Score={score:.2f} (avg of {len(scores)} segments)", flush=True)
        print(f"     Total Trades={trades_total}", flush=True)
        print(f"     등급: {grade_emoji} {grade} ({score:.1f}/100)", flush=True)"""

tuners = ['trend', 'daytrade', 'reversion', 'swing', 'breakout']

for tuner in tuners:
    file_path = Path(f'scripts/tuning/tune_{tuner}.py')
    
    print(f"Rebuilding {tuner}...")
    
    content = file_path.read_text(encoding='utf-8')
    
    # 1. 파일 시작 부분 교체
    pattern1 = r'        for idx, data_file in enumerate\(eval_files\):\s+# 파일 override용 overlay 복제'
    content = re.sub(pattern1, correct_file_start.replace('\n            # 파일 override용 overlay 복제', '\n            # 파일 override용 overlay 복제'), content)
    
    # 2. 파일 결과 부분 교체
    pattern2 = r'            # 📊 파일별 상세 결과 출력.*?print\(f"     ✅ 완료:.*?\)", flush=True\)'
    content = re.sub(pattern2, correct_file_result, content, flags=re.DOTALL)
    
    # 3. 최종 결과 부분 교체 (네이밍 변경)
    pattern3 = r'        # 등급 계산.*?print\(f"     등급:.*?\)", flush=True\)'
    content = re.sub(pattern3, correct_final_result, content, flags=re.DOTALL)
    
    # 저장
    file_path.write_text(content, encoding='utf-8')
    print(f"  ✅ {tuner} 완료")

print("\n✅ 모든 튜너 재빌드 완료!")
print("Docker 이미지 재빌드가 필요합니다.")
