import sqlite3

conn = sqlite3.connect('kikitech.db')
cur = conn.cursor()

try:
    # Try adding the column only if it doesn't exist
    cur.execute("ALTER TABLE orders ADD COLUMN sale_time TEXT")
    print("✅ 'sale_time' column added successfully.")
except sqlite3.OperationalError as e:
    print("⚠️ Skipping: ", e)

conn.commit()
conn.close()