#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV Data Quality Inspector (PHASE8-5)
======================================
백테스트 CSV 데이터의 품질을 검증하는 스크립트

Usage:
    python scripts/inspect_csv.py --csv data/BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv --tf 5m
"""
import sys
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger(__name__)


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='CSV 데이터 품질 검증',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        default='data/BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv',
        help='검사할 CSV 파일 경로'
    )
    
    parser.add_argument(
        '--tf',
        type=str,
        default='5m',
        help='타임프레임 (예: 5m, 15m, 1h)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='docs/PHASE8/PHASE8-5_DATA_QUALITY.md',
        help='리포트 출력 경로'
    )
    
    return parser.parse_args()


def tf_to_minutes(tf: str) -> int:
    """타임프레임 문자열을 분(minute)으로 변환"""
    tf = tf.strip().lower()
    if tf.endswith('m'):
        return int(tf[:-1])
    elif tf.endswith('h'):
        return int(tf[:-1]) * 60
    elif tf.endswith('d'):
        return int(tf[:-1]) * 60 * 24
    else:
        return int(tf)


def load_and_normalize_csv(csv_path: str) -> pd.DataFrame:
    """CSV 로드 및 시간 컬럼 정규화"""
    df = pd.read_csv(csv_path)
    
    # 컬럼명 표준화
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'time'})
    
    # 시간 변환
    if 'time' in df.columns:
        if pd.api.types.is_numeric_dtype(df['time']):
            # 숫자형 → datetime
            sample = int(df['time'].iloc[0])
            if sample > 10_000_000_000:  # 밀리초
                df['time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
            else:  # 초
                df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        else:
            # 문자열 → datetime
            df['time'] = pd.to_datetime(df['time'], utc=True)
    
    # 시간순 정렬
    df = df.sort_values('time').reset_index(drop=True)
    
    return df


def check_data_quality(df: pd.DataFrame, tf_minutes: int) -> Dict[str, Any]:
    """데이터 품질 검증"""
    results = {}
    
    # 기본 정보
    results['total_rows'] = len(df)
    results['first_ts'] = df['time'].iloc[0]
    results['last_ts'] = df['time'].iloc[-1]
    results['actual_days'] = (results['last_ts'] - results['first_ts']).days
    
    # 이론상 캔들 개수 계산
    total_minutes = (results['last_ts'] - results['first_ts']).total_seconds() / 60
    expected_candles = int(total_minutes / tf_minutes) + 1
    results['expected_candles'] = expected_candles
    
    # 누락 캔들
    missing_count = expected_candles - results['total_rows']
    results['missing_candles'] = missing_count
    results['missing_pct'] = (missing_count / expected_candles * 100) if expected_candles > 0 else 0
    
    # 중복 timestamp 체크
    duplicated = df['time'].duplicated().sum()
    results['duplicated_ts'] = duplicated
    results['duplicated_pct'] = (duplicated / results['total_rows'] * 100) if results['total_rows'] > 0 else 0
    
    # Gap 분석 (5분 이상 간격)
    df['time_diff'] = df['time'].diff()
    expected_diff = pd.Timedelta(minutes=tf_minutes)
    
    # Gap이 있는 구간 찾기
    gaps = df[df['time_diff'] > expected_diff].copy()
    results['gap_count'] = len(gaps)
    
    # 최대 gap 찾기
    if len(gaps) > 0:
        max_gap_idx = gaps['time_diff'].idxmax()
        max_gap_row = df.loc[max_gap_idx]
        prev_row = df.loc[max_gap_idx - 1]
        
        gap_minutes = max_gap_row['time_diff'].total_seconds() / 60
        missing_in_gap = int(gap_minutes / tf_minutes) - 1
        
        results['max_gap'] = {
            'start': prev_row['time'],
            'end': max_gap_row['time'],
            'gap_minutes': gap_minutes,
            'missing_candles': missing_in_gap
        }
    else:
        results['max_gap'] = None
    
    # Timezone 체크
    if hasattr(results['first_ts'], 'tz'):
        results['timezone'] = str(results['first_ts'].tz)
    else:
        results['timezone'] = 'None (naive datetime)'
    
    return results


def find_top_gaps(df: pd.DataFrame, tf_minutes: int, top_n: int = 5) -> List[Dict]:
    """상위 N개 gap 구간 찾기"""
    df['time_diff'] = df['time'].diff()
    expected_diff = pd.Timedelta(minutes=tf_minutes)
    
    gaps = df[df['time_diff'] > expected_diff].copy()
    gaps = gaps.sort_values('time_diff', ascending=False).head(top_n)
    
    gap_list = []
    for idx in gaps.index:
        row = df.loc[idx]
        prev_row = df.loc[idx - 1]
        
        gap_minutes = row['time_diff'].total_seconds() / 60
        missing_candles = int(gap_minutes / tf_minutes) - 1
        
        gap_list.append({
            'start': prev_row['time'],
            'end': row['time'],
            'gap_minutes': gap_minutes,
            'missing_candles': missing_candles
        })
    
    return gap_list


def generate_report(csv_path: str, tf: str, results: Dict[str, Any], top_gaps: List[Dict]) -> str:
    """Markdown 리포트 생성"""
    report = f"""# PHASE8-5: Data Quality Report

## CSV File: `{csv_path}`

**Inspection Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Timeframe**: {tf}

---

## 📊 Basic Information

| Item | Value |
|------|-------|
| **Total Rows** | {results['total_rows']:,} |
| **First Timestamp** | {results['first_ts']} |
| **Last Timestamp** | {results['last_ts']} |
| **Actual Period** | {results['actual_days']} days |
| **Timezone** | {results['timezone']} |

---

## 🔍 Data Continuity Check

| Item | Value | Status |
|------|-------|--------|
| **Expected Candles** | {results['expected_candles']:,} | - |
| **Actual Candles** | {results['total_rows']:,} | - |
| **Missing Candles** | {results['missing_candles']:,} ({results['missing_pct']:.2f}%) | {'✅ Good' if results['missing_pct'] < 1 else '⚠️ Warning' if results['missing_pct'] < 5 else '❌ Poor'} |
| **Duplicated Timestamps** | {results['duplicated_ts']} ({results['duplicated_pct']:.2f}%) | {'✅ Good' if results['duplicated_ts'] == 0 else '⚠️ Warning'} |
| **Gap Count** | {results['gap_count']} | {'✅ Good' if results['gap_count'] < 10 else '⚠️ Warning' if results['gap_count'] < 50 else '❌ Poor'} |

---

## 🚨 Top {len(top_gaps)} Largest Gaps

"""
    
    if top_gaps:
        for i, gap in enumerate(top_gaps, 1):
            report += f"""
### Gap #{i}
- **Period**: {gap['start']} → {gap['end']}
- **Gap Duration**: {gap['gap_minutes']:.1f} minutes
- **Missing Candles**: {gap['missing_candles']}
"""
    else:
        report += "\n✅ **No gaps detected!** Data is continuous.\n"
    
    report += f"""
---

## 📈 Data Quality Summary

"""
    
    # 종합 평가
    score = 100
    issues = []
    
    if results['missing_pct'] > 5:
        score -= 30
        issues.append(f"❌ High missing rate ({results['missing_pct']:.2f}%)")
    elif results['missing_pct'] > 1:
        score -= 10
        issues.append(f"⚠️ Some missing candles ({results['missing_pct']:.2f}%)")
    
    if results['duplicated_ts'] > 0:
        score -= 20
        issues.append(f"⚠️ {results['duplicated_ts']} duplicated timestamps")
    
    if results['gap_count'] > 50:
        score -= 30
        issues.append(f"❌ Too many gaps ({results['gap_count']})")
    elif results['gap_count'] > 10:
        score -= 10
        issues.append(f"⚠️ Some gaps ({results['gap_count']})")
    
    if score >= 90:
        overall = "✅ **EXCELLENT** - Data quality is very good"
    elif score >= 70:
        overall = "⚠️ **GOOD** - Data quality is acceptable with minor issues"
    elif score >= 50:
        overall = "⚠️ **FAIR** - Data quality has some concerns"
    else:
        overall = "❌ **POOR** - Data quality needs attention"
    
    report += f"**Overall Score**: {score}/100\n\n"
    report += f"**Overall Assessment**: {overall}\n\n"
    
    if issues:
        report += "**Issues Detected**:\n"
        for issue in issues:
            report += f"- {issue}\n"
    else:
        report += "✅ **No issues detected!**\n"
    
    report += """
---

## 💡 Recommendations

"""
    
    if results['missing_pct'] > 5 or results['gap_count'] > 50:
        report += """
1. **Consider re-downloading data from Binance API**
   - Use `ccxt` library or Binance official API
   - Ensure proper timezone handling (UTC)
   - Implement retry logic for API failures

2. **Data Generation Script**
   - Create `scripts/download_ohlcv_binance.py`
   - Use historical data endpoints
   - Validate downloaded data before saving
"""
    elif results['missing_pct'] > 1:
        report += """
1. **Minor gaps detected** - Data is mostly good
   - Consider filling small gaps with interpolation (optional)
   - Or accept as-is if gaps are during low-activity periods

2. **For production use**
   - Monitor gap patterns (are they at specific times?)
   - Ensure gaps don't correlate with important market events
"""
    else:
        report += """
✅ **Data quality is good!**

- Current CSV is suitable for backtesting
- No immediate action required
- Continue with strategy analysis (PHASE9)
"""
    
    report += f"""
---

*Generated by PHASE8-5 Data Quality Inspector*  
*Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    return report


def main():
    """메인 실행 함수"""
    args = parse_args()
    
    print("=" * 60)
    print("🔍 PHASE8-5: CSV Data Quality Inspector")
    print("=" * 60)
    
    # CSV 로드
    logger.info(f"📂 Loading CSV: {args.csv}")
    csv_path = Path(args.csv)
    
    if not csv_path.exists():
        logger.error(f"❌ CSV file not found: {args.csv}")
        sys.exit(1)
    
    df = load_and_normalize_csv(str(csv_path))
    logger.info(f"✅ Loaded {len(df):,} rows")
    
    # 타임프레임 변환
    tf_minutes = tf_to_minutes(args.tf)
    logger.info(f"⏱️  Timeframe: {args.tf} ({tf_minutes} minutes)")
    
    # 데이터 품질 검증
    logger.info("🔍 Analyzing data quality...")
    results = check_data_quality(df, tf_minutes)
    
    # 상위 gap 찾기
    top_gaps = find_top_gaps(df, tf_minutes, top_n=5)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 ANALYSIS RESULTS")
    print("=" * 60)
    print(f"Total Rows: {results['total_rows']:,}")
    print(f"Period: {results['first_ts']} ~ {results['last_ts']}")
    print(f"Actual Days: {results['actual_days']}")
    print(f"Expected Candles: {results['expected_candles']:,}")
    print(f"Missing Candles: {results['missing_candles']:,} ({results['missing_pct']:.2f}%)")
    print(f"Duplicated Timestamps: {results['duplicated_ts']} ({results['duplicated_pct']:.2f}%)")
    print(f"Gap Count: {results['gap_count']}")
    
    if results['max_gap']:
        gap = results['max_gap']
        print(f"\nLargest Gap:")
        print(f"  {gap['start']} → {gap['end']}")
        print(f"  {gap['gap_minutes']:.1f} minutes ({gap['missing_candles']} missing candles)")
    
    # 리포트 생성
    logger.info("📝 Generating report...")
    report = generate_report(args.csv, args.tf, results, top_gaps)
    
    # 리포트 저장
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✅ Report saved: {output_path}")
    
    print("\n" + "=" * 60)
    print(f"✅ Report saved: {output_path}")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    main()
