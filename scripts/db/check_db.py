import sqlite3

conn = sqlite3.connect('data/trading.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM trades')
total = cursor.fetchone()[0]
print(f'Total trades in DB: {total}')

if total > 0:
    cursor.execute('SELECT symbol, entry_time, exit_time, pnl FROM trades ORDER BY exit_time DESC LIMIT 5')
    print('\nLast 5 trades:')
    for row in cursor.fetchall():
        print(f'  {row}')

conn.close()
