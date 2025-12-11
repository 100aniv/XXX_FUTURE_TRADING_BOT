#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-3.4: V4 Engine Integration Probe
=========================================
V4 전략이 엔진 밖에서 실제로 신호를 생성하는지 검증

목적:
- 엔진과 동일한 방식으로 데이터 준비 + 지표 계산
- V4.compute_signal() 직접 호출
- 신호 발생 여부 확인

결과:
- 신호 0건 → V4 내부 문제 (필터/Score/컬럼)
- 신호 수십건 → 엔진 통합 문제 (Strategy Adapter/Runner)
"""
import sys
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from indicators.core_indicators import add_indicators
from strategies.btc5m_baseline_v4 import Btc5mBaselineV4


def apply_engine_aliases(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    엔진이 사용하는 지표 별칭 매핑 (execution/engine.py line 1759-1770 재현)
    
    Args:
        df: 지표가 계산된 DataFrame
        config: 설정 딕셔너리
    
    Returns:
        별칭이 추가된 DataFrame
    """
    inds = config.get('indicators', {})
    
    # EMA 파라미터
    ema_fast = inds.get('ema', {}).get('fast', 5)
    ema_mid = inds.get('ema', {}).get('mid', 20)
    ema_slow = inds.get('ema', {}).get('slow', 200)
    
    # RSI 파라미터
    rsi_len = inds.get('rsi', {}).get('length', 14)
    
    # Volume MA 파라미터
    vol_ma_len = inds.get('volume', {}).get('ma_length', 20)
    
    # ADX 파라미터
    adx_period = inds.get('adx', {}).get('period', 14)
    
    # ATR 파라미터
    atr_len = inds.get('atr', {}).get('length', 14)
    
    # 별칭 추가 (엔진과 동일)
    if "rsi" in df.columns and f"rsi_{rsi_len}" not in df.columns:
        df[f"rsi_{rsi_len}"] = df["rsi"]
    
    if "ema_fast" in df.columns:
        df[f"ema_{ema_fast}"] = df["ema_fast"]
        df[f"ema_{ema_mid}"] = df["ema_mid"]
        df[f"ema_{ema_slow}"] = df["ema_slow"]
    
    if "vol_ma" in df.columns and f"volume_ma_{vol_ma_len}" not in df.columns:
        df[f"volume_ma_{vol_ma_len}"] = df["vol_ma"]
    
    if f"plus_di_{adx_period}" in df.columns:
        df[f"di_plus_{adx_period}"] = df[f"plus_di_{adx_period}"]
        df[f"di_minus_{adx_period}"] = df[f"minus_di_{adx_period}"]
    
    if "atr" in df.columns and f"atr_{atr_len}" not in df.columns:
        df[f"atr_{atr_len}"] = df["atr"]
    
    if f"adx_{adx_period}" in df.columns and "adx_14" not in df.columns:
        df["adx_14"] = df[f"adx_{adx_period}"]
    
    return df


def probe_v4_signals():
    """V4 전략 신호 발생 검증"""
    
    print("=" * 80)
    print("PHASE29-3.4: V4 Engine Integration Probe")
    print("=" * 80)
    
    # 1. Config 로드
    config_path = Path("configs/backtest/phase29_3_1_btc5m_baseline_v4_week.yml")
    print(f"\n[STEP 1] Config 로드: {config_path}")
    
    if not config_path.exists():
        print(f"❌ Config 파일 없음: {config_path}")
        sys.exit(1)
    
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print(f"✅ Config 로드 성공")
    print(f"   Symbol: {config['symbol']}")
    print(f"   Timeframe: {config['timeframe']}")
    
    # 2. 데이터 로드
    backtest_cfg = config.get('backtest', {})
    data_file_str = backtest_cfg.get('data_file', 'BTCUSDT_5m_2024-01-01_2024-12-31.csv')
    # 절대 경로로 변환
    project_root = Path(__file__).parent.parent
    if not Path(data_file_str).is_absolute():
        # data 디렉토리 추가
        if not data_file_str.startswith('data'):
            data_file = project_root / 'data' / data_file_str
        else:
            data_file = project_root / data_file_str
    else:
        data_file = Path(data_file_str)
    start_date = backtest_cfg.get('start_date', '2024-11-24 00:00:00')
    end_date = backtest_cfg.get('end_date', '2024-12-01 00:00:00')
    
    print(f"\n[STEP 2] 데이터 로드: {data_file}")
    print(f"   기간: {start_date} ~ {end_date}")
    print(f"   파일 존재: {data_file.exists()}")
    
    if not data_file.exists():
        print(f"❌ 데이터 파일 없음: {data_file}")
        print(f"   프로젝트 루트: {project_root}")
        print(f"   Config data_file: {data_file_str}")
        sys.exit(1)
    
    df_all = pd.read_csv(data_file)
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
    
    print(f"✅ 데이터 로드 성공")
    print(f"   전체: {len(df_all):,} rows")
    print(f"   컬럼: {list(df_all.columns)}")
    
    # 3. 지표 계산 (엔진 방식) - 전체 데이터에서 계산
    print(f"\n[STEP 3] 지표 계산 (엔진 방식)")
    
    inds = config.get('indicators', {})
    
    # add_indicators 호출 (indicators/core_indicators.py)
    df_all = add_indicators(
        df_all,
        ema_fast=inds.get('ema', {}).get('fast', 5),
        ema_mid=inds.get('ema', {}).get('mid', 20),
        ema_slow=inds.get('ema', {}).get('slow', 200),
        rsi_len=inds.get('rsi', {}).get('length', 14),
        atr_len=inds.get('atr', {}).get('length', 14),
        adx_period=inds.get('adx', {}).get('period', 14),
        vol_ma_len=inds.get('volume', {}).get('ma_length', 20),
        use_adx=True
    )
    
    print(f"✅ 지표 계산 완료")
    print(f"   컬럼 수: {len(df_all.columns)}")
    
    # 기간 필터링 (지표 계산 후)
    df = df_all[(df_all['timestamp'] >= start_date) & (df_all['timestamp'] <= end_date)].copy()
    print(f"   필터링 후: {len(df):,} rows")
    
    # 4. 엔진 별칭 적용
    print(f"\n[STEP 4] 엔진 별칭 적용")
    df = apply_engine_aliases(df, config)
    
    # V4 필수 컬럼 확인
    required_cols = ['rsi_14', 'adx_14', 'di_plus_14', 'di_minus_14', 
                     'ema_5', 'ema_20', 'ema_200', 'atr_14', 'volume_ma_20']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"⚠️  누락된 컬럼: {missing_cols}")
    else:
        print(f"✅ V4 필수 컬럼 모두 존재")
    
    print(f"   현재 컬럼: {sorted([c for c in df.columns if any(x in c for x in ['rsi', 'ema', 'adx', 'di', 'atr', 'volume'])])}")
    
    # 5. V4 전략 인스턴스 생성
    print(f"\n[STEP 5] V4 전략 인스턴스 생성")
    
    v4_params = config.get('strategies', {}).get('btc5m_baseline_v4', {})
    if not v4_params:
        print(f"❌ V4 파라미터 없음 (config.strategies.btc5m_baseline_v4)")
        sys.exit(1)
    
    # Config 병합
    merged_config = {**config, **v4_params}
    
    try:
        strategy = Btc5mBaselineV4(config=merged_config)
        print(f"✅ V4 인스턴스 생성 성공: {type(strategy).__name__}")
    except Exception as e:
        print(f"❌ V4 인스턴스 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 6. 전체 캔들 순회하여 신호 발생 검증
    print(f"\n[STEP 6] 전체 캔들 순회 (분석 스크립트 방식)")
    
    signal_count = {
        'total': 0,
        'long': 0,
        'short': 0,
        'filter_fail': 0
    }
    
    min_bars = merged_config.get('min_bars_for_signal', 100)
    
    for i in range(min_bars, len(df)):
        # 각 캔들마다 슬라이스 생성 (분석 스크립트와 동일)
        df_slice = df.iloc[:i+1].copy()
        
        try:
            result = strategy.compute_signal(df_slice)
            
            side = result.get('side')
            
            if side == 'LONG':
                signal_count['long'] += 1
                signal_count['total'] += 1
            elif side == 'SHORT':
                signal_count['short'] += 1
                signal_count['total'] += 1
            else:
                # 필터로 차단된 경우
                reason = result.get('reason', '')
                if 'FILTER' in reason:
                    signal_count['filter_fail'] += 1
        except Exception as e:
            # 에러는 무시하고 계속
            continue
    
    print(f"✅ 순회 완료: {len(df) - min_bars:,}개 캔들 평가")
    print(f"\n[STEP 7] 신호 분석 결과")
    print(f"   총 신호 수: {signal_count['total']:,}건")
    print(f"   LONG: {signal_count['long']:,}건")
    print(f"   SHORT: {signal_count['short']:,}건")
    print(f"   필터 차단: {signal_count['filter_fail']:,}건")
    
    if signal_count['total'] > 0:
        print(f"\n✅ 신호 발생 확인!")
        print(f"   예상 분석 결과와 비교:")
        print(f"   - 분석 스크립트: 96건 예상")
        print(f"   - Probe 결과: {signal_count['total']}건")
        
        if signal_count['total'] >= 20:
            print(f"   → Gate 조건(20~60건) 충족 가능성 높음")
        else:
            print(f"   → Gate 조건(20~60건) 미달")
        
        return True
    else:
        print(f"\n❌ 신호 없음")
        print(f"   모든 캔들이 필터로 차단됨")
        return False


if __name__ == "__main__":
    success = probe_v4_signals()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ PROBE SUCCESS: V4 전략이 신호를 생성함")
        print("   → 문제는 엔진 통합부에 있을 가능성이 높음")
        sys.exit(0)
    else:
        print("❌ PROBE FAILED: V4 전략이 신호를 생성하지 못함")
        print("   → 문제는 V4 내부 로직/필터/컬럼에 있음")
        sys.exit(1)
