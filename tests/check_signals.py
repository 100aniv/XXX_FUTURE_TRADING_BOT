import psycopg2
from datetime import datetime

conn = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')

with conn.cursor() as cur:
    # 전체 시그널 수
    cur.execute("SELECT COUNT(*) FROM monitoring.signals")
    total = cur.fetchone()[0]
    print(f'📊 전체 시그널: {total}개')
    
    # 최근 10개 시그널
    cur.execute("""
        SELECT signal_id, strategy_id, symbol, direction, confidence, created_at 
        FROM monitoring.signals 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    signals = cur.fetchall()
    
    if signals:
        print('\n최근 10개 시그널:')
        for s in signals:
            print(f'  {s[5]} | {s[1]:10} | {s[2]:10} | {s[3]:5} | {s[4]:.2f}')
    else:
        print('\n⚠️  시그널이 없습니다!')

    # 전략별 시그널 수
    cur.execute("""
        SELECT strategy_id, COUNT(*) as cnt
        FROM monitoring.signals
        GROUP BY strategy_id
        ORDER BY cnt DESC
    """)
    by_strategy = cur.fetchall()
    
    if by_strategy:
        print('\n전략별 시그널:')
        for s in by_strategy:
            print(f'  {s[0]:15} : {s[1]:5}개')

conn.close()
