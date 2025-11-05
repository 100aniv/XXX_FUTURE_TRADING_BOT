import psycopg2

conn = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')
cur = conn.cursor()

# 최근 1시간 신호
cur.execute("SELECT COUNT(*) FROM monitoring.signals WHERE created_at > NOW() - INTERVAL '1 hour'")
signals_count = cur.fetchone()[0]
print(f"✅ 최근 1시간 신호: {signals_count}개")

# 최근 1시간 결정
cur.execute("SELECT COUNT(*) FROM trading.decisions WHERE created_at > NOW() - INTERVAL '1 hour'")
decisions_count = cur.fetchone()[0]
print(f"✅ 최근 1시간 결정: {decisions_count}개")

# 최근 신호 상세
cur.execute("""
    SELECT strategy_id, symbol, direction, created_at 
    FROM monitoring.signals 
    WHERE created_at > NOW() - INTERVAL '10 minutes'
    ORDER BY created_at DESC 
    LIMIT 5
""")
recent_signals = cur.fetchall()
if recent_signals:
    print(f"\n📊 최근 10분 신호 (최대 5개):")
    for sig in recent_signals:
        print(f"   {sig[0]:10s} {sig[1]:10s} {sig[2]:5s} {sig[3]}")
else:
    print("\n⚠️  최근 10분 신호 없음")

conn.close()
