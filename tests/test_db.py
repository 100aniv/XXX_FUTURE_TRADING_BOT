import psycopg2

conn = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')
print('✅ DB 연결 성공')

# 시그널 확인
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM monitoring.signals WHERE created_at > NOW() - INTERVAL '1 hour'")
    count = cur.fetchone()[0]
    print(f'📊 최근 1시간 시그널: {count}개')

conn.close()
