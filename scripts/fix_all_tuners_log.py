#!/usr/bin/env python3
"""
모든 튜너에 백테스트 진행 표시 추가
"""
from pathlib import Path

tuners = ['trend', 'daytrade', 'reversion', 'swing', 'breakout']

for tuner in tuners:
    file_path = Path(f'scripts/tuning/tune_{tuner}.py')
    
    print(f"Processing {tuner}...")
    
    content = file_path.read_text(encoding='utf-8')
    
    # 1. 백테스트 시작 표시 추가
    old1 = """        for idx, data_file in enumerate(eval_files):
            # 파일 override용 overlay 복제"""
    
    new1 = """        for idx, data_file in enumerate(eval_files):
            # 📄 파일 처리 시작 표시
            filename = data_file.name if data_file else 'config_default'
            print(f"  📄 [{idx+1}/{len(eval_files)}] {filename}... 백테스트 실행 중", flush=True)
            
            # 파일 override용 overlay 복제"""
    
    content = content.replace(old1, new1)
    
    # 2. 결과 출력 개선
    old2 = """            # 📊 파일별 상세 결과 출력
            filename = data_file.name if data_file else 'config_default'
            win_rate = metrics.get('win_rate', 0.0)
            rr = metrics.get('rr_realized', 0.0)
            pf = metrics.get('profit_factor', 0.0)
            roi = metrics.get('roi_pct', 0.0)
            print(f"  📄 [{idx+1}/{len(eval_files)}] {filename}:", flush=True)
            print(f"     Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)"""
    
    new2 = """            # 📊 파일별 상세 결과 출력
            win_rate = metrics.get('win_rate', 0.0)
            rr = metrics.get('rr_realized', 0.0)
            pf = metrics.get('profit_factor', 0.0)
            roi = metrics.get('roi_pct', 0.0)
            print(f"     ✅ 완료: Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)"""
    
    content = content.replace(old2, new2)
    
    # 저장
    file_path.write_text(content, encoding='utf-8')
    print(f"  ✅ {tuner} 완료")

print("\n✅ 모든 튜너 로그 개선 완료!")
