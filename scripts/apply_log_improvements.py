#!/usr/bin/env python3
"""
나머지 4개 튜너에 로그 개선 적용
"""
import re
from pathlib import Path

# 개선할 튜너 목록
tuners = ['daytrade', 'reversion', 'swing', 'breakout']

# 각 튜너별 파라미터 키 (테스트 파라미터 출력용)
param_keys = {
    'daytrade': ['rsi_min', 'rsi_max', 'cooldown_candles', 'atr_mult_sl', 'rr_ratio', 'allow_short'],
    'reversion': ['rsi_threshold', 'bb_lower_pct', 'bb_upper_pct', 'allow_short'],
    'swing': ['ema_fast', 'ema_slow', 'rsi_min', 'rsi_max', 'allow_short'],
    'breakout': ['donchian_period', 'atr_mult_sl', 'volume_mult', 'allow_short'],
}

for tuner in tuners:
    file_path = Path(f'scripts/tuning/tune_{tuner}.py')
    
    print(f"Processing {tuner}...")
    
    content = file_path.read_text(encoding='utf-8')
    
    # 1. 파라미터 출력 추가
    param_code = f"""    def objective(trial: 'optuna.trial.Trial') -> float:
        overlay = _build_overlay_from_trial(trial)
        
        # 📊 테스트 중인 파라미터 출력
        print(f"\\n  🔧 테스트 파라미터:", flush=True)
        param_items = []
        for key in {param_keys[tuner]}:
            if key in trial.params:
                param_items.append(f"{{key}}={{trial.params[key]}}")
        if param_items:
            print(f"     {{', '.join(param_items)}}", flush=True)

        # Trial별 출력 경로"""
    
    old_pattern1 = r"    def objective\(trial: 'optuna\.trial\.Trial'\) -> float:\s+overlay = _build_overlay_from_trial\(trial\)\s+# Trial별 출력 경로"
    content = re.sub(old_pattern1, param_code, content)
    
    # 2. 파일별 상세 결과 출력 추가
    detail_code = """            seg_score = objective_score(metrics)
            scores.append(seg_score)
            seg_scores.append(seg_score)
            
            # 📊 파일별 상세 결과 출력
            filename = data_file.name if data_file else 'config_default'
            win_rate = metrics.get('win_rate', 0.0)
            rr = metrics.get('rr_realized', 0.0)
            pf = metrics.get('profit_factor', 0.0)
            roi = metrics.get('roi_pct', 0.0)
            print(f"  📄 [{idx+1}/{len(eval_files)}] {filename}:", flush=True)
            print(f"     Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)"""
    
    old_pattern2 = r"            seg_score = objective_score\(metrics\)\s+scores\.append\(seg_score\)\s+seg_scores\.append\(seg_score\)"
    content = re.sub(old_pattern2, detail_code, content)
    
    # 3. 최종 등급 출력 추가
    grade_code = """        # 평균 점수
        score = sum(scores) / max(1, len(scores))
        
        # 등급 계산
        if score >= 80: grade_emoji, grade = "🎉", "S"
        elif score >= 70: grade_emoji, grade = "✅", "A"
        elif score >= 60: grade_emoji, grade = "⚠️", "B"
        elif score >= 50: grade_emoji, grade = "⚠️", "C"
        elif score >= 40: grade_emoji, grade = "❌", "D"
        else: grade_emoji, grade = "❌", "FAIL"
        
        # 🎯 최종 집계 출력
        print(f"\\n  🎯 최종 결과:", flush=True)
        print(f"     Score={score:.2f} (avg of {len(scores)} segments)", flush=True)
        print(f"     Total Trades={trades_total}", flush=True)
        print(f"     등급: {grade_emoji} {grade} ({score:.1f}/100)", flush=True)"""
    
    old_pattern3 = r"        # 평균 점수\s+score = sum\(scores\) / max\(1, len\(scores\)\)"
    content = re.sub(old_pattern3, grade_code, content)
    
    # 저장
    file_path.write_text(content, encoding='utf-8')
    print(f"  ✅ {tuner} 완료")

print("\n✅ 모든 튜너 로그 개선 완료!")
