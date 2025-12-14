#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(
    host='localhost', 
    port=5433, 
    user='trading_user', 
    password='trading_pw_2024', 
    database='trading_db'
)
cur = conn.cursor()

# Run1 거래 수
cur.execute("""
    SELECT COUNT(*) 
    FROM trading.trades 
    WHERE run_id LIKE %s AND status = 'CLOSED'
""", ('phase35_2_iter4_run1%',))
run1 = cur.fetchone()[0]

# Run2 거래 수
cur.execute("""
    SELECT COUNT(*) 
    FROM trading.trades 
    WHERE run_id LIKE %s AND status = 'CLOSED'
""", ('phase35_2_iter4_run2%',))
run2 = cur.fetchone()[0]

print(f'✅ Run1 실제 DB 거래: {run1}건')
print(f'✅ Run2 실제 DB 거래: {run2}건')

if run1 == 0 and run2 == 0:
    print('\n🎯 정상: 신호 100% 차단 → 거래 0건 (로직 일치)')
    print('❌ Summary 오류: 이전 리포트(10,498건)를 잘못 읽음')
else:
    print(f'\n⚠️ 비정상: 신호 100% 차단인데 거래 발생 (DB 버그?)')

conn.close()
