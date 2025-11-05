import sqlite3
conn = sqlite3.connect('backtest_results.db')
cursor = conn.cursor()

# 테이블 목록
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("테이블:", tables)

# 각 테이블 구조
for table in tables:
    print(f"\n{table[0]} 구조:")
    info = cursor.execute(f"PRAGMA table_info({table[0]})").fetchall()
    for col in info:
        print(f"  {col[1]} ({col[2]})")

conn.close()
