#!/usr/bin/env python3
"""
나머지 5개 튜너의 prune 로깅 수정
"""
from pathlib import Path

tuners = ['trend', 'daytrade', 'reversion', 'swing', 'breakout']

for tuner in tuners:
    file_path = Path(f'scripts/tuning/tune_{tuner}.py')
    
    print(f"Processing {tuner}...")
    
    content = file_path.read_text(encoding='utf-8')
    
    # Scalping과 동일한 패턴으로 교체
    old_pattern = """            # Early prune: 거래 부족 시 중단
            t = int(metrics.get('trades') or 0)
            trades_total += t
            # Per-segment min trades gate for robust mode
            if (str(getattr(args, 'dod_mode', '')).lower() == 'robust') and int(getattr(args, 'min_trades_oos', 0) or 0) > 0:
                if t < int(args.min_trades_oos):
                    raise optuna.TrialPruned()
            if t < 10 and len(eval_files) == 1:
                raise optuna.TrialPruned()

            # 제약 위반있으면 약한 패널티 점수 부여(집계 유지), 또는 prune
            if not constraints_ok(metrics):
                worst_ok = False

            seg_score = objective_score(metrics)
            scores.append(seg_score)
            seg_scores.append(seg_score)
            
            # 📊 파일별 상세 결과 출력
            win_rate = metrics.get('win_rate', 0.0)
            rr = metrics.get('rr_realized', 0.0)
            pf = metrics.get('profit_factor', 0.0)
            roi = metrics.get('roi_pct', 0.0)
            print(f"     ✅ 완료: Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)"""
    
    new_pattern = """            # Early prune: 거래 부족 시 중단
            t = int(metrics.get('trades') or 0)
            trades_total += t
            
            # 📊 파일별 상세 결과 출력 (prune 전에!)
            win_rate = metrics.get('win_rate', 0.0)
            rr = metrics.get('rr_realized', 0.0)
            pf = metrics.get('profit_factor', 0.0)
            roi = metrics.get('roi_pct', 0.0)
            seg_score = objective_score(metrics)
            print(f"     ✅ 완료: Trades={t}, Win%={win_rate:.1f}%, RR={rr:.2f}, PF={pf:.2f}, ROI={roi:.1f}%, Score={seg_score:.2f}", flush=True)
            
            # Per-segment min trades gate for robust mode
            if (str(getattr(args, 'dod_mode', '')).lower() == 'robust') and int(getattr(args, 'min_trades_oos', 0) or 0) > 0:
                if t < int(args.min_trades_oos):
                    print(f"     ⚠️ Pruned: 거래 부족 ({t} < {args.min_trades_oos})", flush=True)
                    raise optuna.TrialPruned()
            if t < 10 and len(eval_files) == 1:
                print(f"     ⚠️ Pruned: 거래 부족 ({t} < 10)", flush=True)
                raise optuna.TrialPruned()

            # 제약 위반있으면 약한 패널티 점수 부여(집계 유지), 또는 prune
            if not constraints_ok(metrics):
                worst_ok = False

            scores.append(seg_score)
            seg_scores.append(seg_score)"""
    
    content = content.replace(old_pattern, new_pattern)
    
    # 저장
    file_path.write_text(content, encoding='utf-8')
    print(f"  ✅ {tuner} 완료")

print("\n✅ 모든 튜너 prune 로깅 수정 완료!")
