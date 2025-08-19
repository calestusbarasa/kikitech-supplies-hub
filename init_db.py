import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create products table
c.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL
)
''')

# Create product_entries table
c.execute('''
CREATE TABLE IF NOT EXISTS product_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity_added INTEGER NOT NULL,
    date_added TEXT DEFAULT CURRENT_TIMESTAMP
)
''')

# Create orders table
c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    payment_mode TEXT,
    total_amount REAL,
    date TEXT DEFAULT CURRENT_TIMESTAMP
)
''')

# Create order_items table
c.execute('''
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    name TEXT,
    description TEXT,
    quantity INTEGER,
    price REAL,
    total REAL
)
''')

# Create sales table
c.execute('''
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    customer_name TEXT,
    total_amount REAL,
    payment_mode TEXT,
    date TEXT DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()
print("✅ Database initialized successfully.")