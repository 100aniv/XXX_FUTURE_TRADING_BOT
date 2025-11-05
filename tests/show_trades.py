import psycopg2

c = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')
cur = c.cursor()
cur.execute('SELECT symbol, side, quantity, entry_price, status, created_at FROM trading.trades ORDER BY created_at DESC LIMIT 10')
rows = cur.fetchall()

print('\n최근 거래 10건:')
print('-' * 80)
for r in rows:
    print(f"{r[5]} | {r[0]:10} {r[1]:5} x{r[2]:8.3f} @ ${r[3]:10.2f} [{r[4]}]")

c.close()
