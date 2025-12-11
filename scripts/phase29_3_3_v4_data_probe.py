#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-3.3: V4 Data Probe
==========================
V4 전략에 필요한 지표 컬럼 존재 여부 및 상태 검사

목적:
- V4가 사용하는 지표 컬럼이 데이터 파일에 존재하는지 확인
- 결측치 비율, 기본 통계 출력
- 누락 시 fallback 전략 제안
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger('phase29_3_3_data_probe', log_type='application')


# V4 전략 필수 지표 목록
REQUIRED_INDICATORS = {
    'rsi_14': {'default': 50, 'desc': 'RSI (Pullback/Oversold)'},
    'adx_14': {'default': 25, 'desc': 'ADX (Trend vs Range)'},
    'di_plus_14': {'default': 25, 'desc': 'DI+ (상승 강도)'},
    'di_minus_14': {'default': 25, 'desc': 'DI- (하락 강도)'},
    'ema_5': {'default': 'price', 'desc': 'EMA 5 (Pullback)'},
    'ema_20': {'default': 'price', 'desc': 'EMA 20 (Pullback)'},
    'ema_200': {'default': 'price', 'desc': 'EMA 200 (장기 추세)'},
    'atr_14': {'default': 'price * 0.002', 'desc': 'ATR (SL/TP)'},
    'volume': {'default': 0, 'desc': 'Volume'},
    'volume_ma_20': {'default': 'volume', 'desc': 'Volume MA'},
    'close': {'default': None, 'desc': 'Close (필수)'},
    'high': {'default': None, 'desc': 'High (필수)'},
    'low': {'default': None, 'desc': 'Low (필수)'},
}


def load_data(data_file: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    백테스트 데이터 로딩
    
    Args:
        data_file: 데이터 파일 경로
        start_date: 시작 날짜
        end_date: 종료 날짜
    
    Returns:
        pd.DataFrame: 필터링된 데이터
    """
    logger.info(f"📂 데이터 로딩: {data_file}")
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"데이터 파일 없음: {data_file}")
    
    df = pd.read_csv(data_file)
    logger.info(f"✅ 전체 데이터 로딩: {len(df):,} rows")
    
    # 날짜 컬럼 파싱
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    elif 'date' in df.columns:
        df['timestamp'] = pd.to_datetime(df['date'])
    else:
        raise ValueError("timestamp 또는 date 컬럼이 없습니다.")
    
    # 날짜 필터링
    df = df[
        (df['timestamp'] >= start_date) & 
        (df['timestamp'] < end_date)
    ].reset_index(drop=True)
    
    logger.info(f"✅ 날짜 필터링 후: {len(df):,} rows ({start_date} ~ {end_date})")
    
    return df


def check_indicator_columns(df: pd.DataFrame) -> dict:
    """
    지표 컬럼 존재 여부 및 상태 검사
    
    Args:
        df: 데이터프레임
    
    Returns:
        dict: 검사 결과
    """
    logger.info("=" * 80)
    logger.info("🔍 지표 컬럼 검사 시작")
    logger.info("=" * 80)
    
    results = {
        'total_columns': len(df.columns),
        'total_rows': len(df),
        'indicators': {},
        'missing': [],
        'present': []
    }
    
    # 전체 컬럼 목록 출력
    logger.info(f"\n📋 전체 컬럼 목록 ({results['total_columns']}개):")
    for i, col in enumerate(df.columns, 1):
        logger.info(f"  {i:2d}. {col}")
    
    # 필수 지표 검사
    logger.info(f"\n🔎 필수 지표 검사 ({len(REQUIRED_INDICATORS)}개):")
    logger.info("-" * 80)
    
    for indicator, info in REQUIRED_INDICATORS.items():
        exists = indicator in df.columns
        
        indicator_result = {
            'exists': exists,
            'description': info['desc'],
            'default_value': info['default']
        }
        
        if exists:
            col_data = df[indicator]
            
            # 결측치 비율
            null_count = col_data.isnull().sum()
            null_pct = (null_count / len(col_data)) * 100
            
            # 기본 통계 (숫자형일 경우만)
            if pd.api.types.is_numeric_dtype(col_data):
                stats = col_data.describe()
                indicator_result.update({
                    'null_count': int(null_count),
                    'null_pct': round(null_pct, 2),
                    'mean': round(stats['mean'], 4),
                    'std': round(stats['std'], 4),
                    'min': round(stats['min'], 4),
                    'max': round(stats['max'], 4),
                    'q25': round(stats['25%'], 4),
                    'median': round(stats['50%'], 4),
                    'q75': round(stats['75%'], 4),
                })
                
                logger.info(f"✅ {indicator:20s} | {info['desc']:30s}")
                logger.info(f"   └─ Mean: {indicator_result['mean']:10.4f} | Std: {indicator_result['std']:10.4f} | Null: {null_pct:.2f}%")
            else:
                indicator_result.update({
                    'null_count': int(null_count),
                    'null_pct': round(null_pct, 2),
                })
                logger.info(f"✅ {indicator:20s} | {info['desc']:30s} (비숫자형)")
            
            results['present'].append(indicator)
        else:
            logger.warning(f"❌ {indicator:20s} | {info['desc']:30s} | ⚠️ 누락 (Fallback: {info['default']})")
            results['missing'].append(indicator)
        
        results['indicators'][indicator] = indicator_result
    
    # 요약
    logger.info("\n" + "=" * 80)
    logger.info("📊 검사 결과 요약")
    logger.info("=" * 80)
    logger.info(f"✅ 존재하는 지표: {len(results['present'])}/{len(REQUIRED_INDICATORS)}")
    logger.info(f"❌ 누락된 지표: {len(results['missing'])}/{len(REQUIRED_INDICATORS)}")
    
    if results['missing']:
        logger.warning(f"\n⚠️ 누락된 지표 목록:")
        for indicator in results['missing']:
            info = REQUIRED_INDICATORS[indicator]
            logger.warning(f"  - {indicator:20s}: {info['desc']} (Fallback: {info['default']})")
    
    return results


def suggest_solutions(results: dict):
    """
    누락 지표에 대한 해결 방안 제안
    
    Args:
        results: check_indicator_columns 결과
    """
    if not results['missing']:
        logger.info("\n✅ 모든 필수 지표가 존재합니다. 추가 조치 불필요.")
        return
    
    logger.info("\n" + "=" * 80)
    logger.info("💡 해결 방안 제안")
    logger.info("=" * 80)
    
    logger.info("\n📌 Option 1: 데이터 파이프라인 보완 (권장)")
    logger.info("  - collectors/historical_collector.py에서 누락 지표 추가")
    logger.info("  - indicators/core_indicators.py 활용하여 지표 계산")
    logger.info("  - 데이터 재수집 또는 전처리 단계에서 지표 추가")
    
    logger.info("\n📌 Option 2: V4 전략 Fallback 강화 (임시 방편)")
    logger.info("  - signal_logic()에서 누락 컬럼 체크 및 기본값 사용")
    logger.info("  - 예: adx = float(last.get('adx_14', 25))  # 기본값 25")
    logger.info("  - 단점: 정확한 신호 생성 불가, 성능 저하 가능")
    
    logger.info("\n📌 Option 3: 데이터 소스 변경")
    logger.info("  - 지표가 포함된 다른 데이터 파일 사용")
    logger.info("  - 또는 실시간 지표 계산 (indicators/indicator_cache.py)")
    
    logger.info("\n🎯 PHASE29-3.3 권장 조치:")
    logger.info("  - 이번 PHASE에서는 Option 2 (Fallback 강화)로 진행")
    logger.info("  - V4 전략이 이미 fallback 로직을 포함하고 있는지 확인")
    logger.info("  - 없다면 최소 수정으로 fallback 추가")
    logger.info("  - 데이터 파이프라인 보완은 PHASE30+로 이월")


def main():
    """
    메인 실행 함수
    """
    logger.info("=" * 80)
    logger.info("🚀 PHASE29-3.3: V4 Data Probe 시작")
    logger.info("=" * 80)
    
    # 백테스트 설정 (1주일)
    data_file = project_root / "data" / "BTCUSDT_5m_2024-01-01_2024-12-31.csv"
    start_date = "2024-11-24 00:00:00"
    end_date = "2024-12-01 00:00:00"
    
    try:
        # 1. 데이터 로딩
        df = load_data(str(data_file), start_date, end_date)
        
        # 2. 지표 컬럼 검사
        results = check_indicator_columns(df)
        
        # 3. 해결 방안 제안
        suggest_solutions(results)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ PHASE29-3.3: V4 Data Probe 완료")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
