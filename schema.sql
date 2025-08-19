-- Drop existing tables if they exist
DROP TABLE IF EXISTS lending;
DROP TABLE IF EXISTS product_entries;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS notifications;

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL
);

-- Product entries (quantity logs)
CREATE TABLE IF NOT EXISTS product_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity_added INTEGER NOT NULL,
    date_added TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Orders table with date
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    payment_mode TEXT NOT NULL,
    date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    total_amount REAL NOT NULL
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    total REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
);

-- Sales table
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    customer_name TEXT NOT NULL,
    total_amount REAL NOT NULL,
    payment_mode TEXT NOT NULL,
    date TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Lending table (corrected)
CREATE TABLE IF NOT EXISTS lending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity_taken INTEGER NOT NULL,
    date_lent TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS lending_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lending_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    action_type TEXT NOT NULL, -- "return" or "pay"
    date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (lending_id) REFERENCES lending(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS lend_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_lent TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    customer_name TEXT NOT NULL,
    product_name TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity_taken INTEGER NOT NULL,
    action_type TEXT NOT NULL  -- "lend", "return", or "pay"
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    email TEXT UNIQUE,
    phone_number TEXT UNIQUE,
    password_hash TEXT,
    role TEXT DEFAULT 'user',   -- added role column
    is_locked BOOLEAN DEFAULT 0,
    failed_attempts INTEGER DEFAULT 0,
    last_login_ip TEXT,
    last_login_device TEXT,
    last_login_time DATETIME
);

-- Login attempts table
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ip_address TEXT,
    device_info TEXT,
    successful BOOLEAN,
    timestamp DATETIME
);