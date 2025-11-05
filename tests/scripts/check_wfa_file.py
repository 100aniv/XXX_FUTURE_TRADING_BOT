import pandas as pd

df = pd.read_csv('data/wfa_blocks/BTCUSDT_15m_2018_WFA01_TRAIN.csv')
print(f"캔들 수: {len(df):,}")
print(f"시작: {df.iloc[0]['time']}")
print(f"종료: {df.iloc[-1]['time']}")
print(f"컬럼: {list(df.columns)}")
