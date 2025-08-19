import sqlite3

DATABASE = "database.db"  

def create_tables():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    with open("schema.sql", "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()
    print("✅ Database and tables created successfully.")

if __name__ == "__main__":
    create_tables()