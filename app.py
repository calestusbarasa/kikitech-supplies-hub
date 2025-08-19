from flask import Flask, render_template, request, redirect, url_for, make_response, send_file, jsonify, flash, g, session
import sqlite3
from datetime import datetime, date, timedelta
from xhtml2pdf import pisa
from weasyprint import HTML
import io
import pdfkit
import calendar
from flask import session, redirect, url_for, render_template, flash
from models import User
from functools import wraps
from sqlalchemy import or_
from models import db, User, LoginAttempt          # db, User, LoginAttempt from models.py
from utils import get_client_info  
import smtplib
from email.message import EmailMessage
import secrets                # must return (ip_address, device_info)

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(days=30)

# Initialize SQLAlchemy with Flask app
db.init_app(app)

# Create tables once at startup (will no-op if they already exist)
with app.app_context():
    db.create_all()

# Keep your old sqlite3 helper for raw queries
DATABASE = "database.db"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db_conn = g.pop("db", None)
    if db_conn is not None:
        db_conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv


# --------------------
# ROUTES
# --------------------
EMAIL_ADDRESS = "kikitechsupplies@gmail.com"
EMAIL_PASSWORD = "zknexvddxgliignh"


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone', '').strip()
        password = request.form.get('password', '')
        remember = 'remember' in request.form

        user = User.query.filter(
            or_(User.email == email_or_phone, User.phone_number == email_or_phone)
        ).first()

        if not user:
            flash("Invalid credentials.", "danger")
            return render_template('login.html')

        if user.is_locked:
            flash("Your account is locked. Contact admin.", "danger")
            return render_template('login.html')

        ip_address, device_info = get_client_info()
        is_new_device = (user.last_login_ip != ip_address or user.last_login_device != device_info)

        if user.check_password(password):
            # Update user login info
            user.failed_attempts = 0
            user.last_login_ip = ip_address
            user.last_login_device = device_info
            user.last_login_time = datetime.utcnow()
            db.session.add(user)

            # Log the login attempt
            attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                device_info=device_info,
                successful=True,
                timestamp=datetime.utcnow()
            )
            db.session.add(attempt)
            db.session.commit()

            # Store session info
            session['user_id'] = user.id
            session['full_name'] = user.full_name
            session['role'] = user.role
            if remember:
                session.permanent = True

            # Set flag to show flash in dashboard
            session['just_logged_in'] = True

            # Optional new device warning
            if is_new_device:
                flash("Login from a new device detected.", "warning")

            # Flash welcome message
            flash(f"Welcome {user.full_name}!", "success")

            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard_view'))
            else:
                return redirect(url_for('mydashboard'))

        else:
            # Failed login attempt
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= 3:
                user.is_locked = True

            db.session.add(user)
            attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                device_info=device_info,
                successful=False,
                timestamp=datetime.utcnow()
            )
            db.session.add(attempt)
            db.session.commit()

            if user.is_locked:
                flash("Account locked after too many failed attempts.", "danger")
            else:
                flash("Invalid credentials.", "danger")

    return render_template('login.html')
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
@app.route('/admin/dashboard')
def admin_dashboard_view():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    # Fetch all users, newest first
    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin_dashboard.html', users=users)


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(16)
            reset_link = url_for('reset_with_token', token=token, _external=True)

            msg = EmailMessage()
            msg['Subject'] = 'Password Reset Request'
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = user.email
            msg.set_content(f"Hello {user.full_name},\n\n"
                            f"Click the link below to reset your password:\n{reset_link}\n\n"
                            f"If you did not request this, ignore this email.")

            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                    smtp.send_message(msg)
                flash("A reset link has been sent to your email.", "success")
            except Exception as e:
                print("Email sending failed:", e)
                flash("Failed to send reset email. Try again later.", "danger")
        else:
            flash("No account found with that email.", "danger")

        return redirect(url_for("login"))

    return render_template("reset_password.html")


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_with_token(token):
    # TODO: Validate token and fetch associated user from DB
    if request.method == "POST":
        new_password = request.form.get("password", "")
        # TODO: Update user password securely
        flash("Password has been reset successfully.", "success")
        return redirect(url_for("login"))
    return render_template("reset_with_token.html", token=token)


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))
@app.route('/check_login')
def check_login():
    if 'user_id' in session:
        return jsonify({
            "logged_in": True,
            "full_name": session.get("full_name", "User"),
            "role": session.get("role", "user")
        })
    return jsonify({"logged_in": False}), 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "info")
        return redirect(url_for('login'))

    full_name = session.get('full_name', 'User')

    # Greeting based on the current hour
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # Show success message once after login
    if session.get("just_logged_in"):
        flash("You have successfully logged in.", "success")
        session.pop("just_logged_in", None)

    conn = get_db_connection()
    # Get today's revenue
    sales_today = conn.execute(
        "SELECT SUM(total_amount) as total FROM sales WHERE DATE(date) = DATE('now')"
    ).fetchone()
    todays_revenue = sales_today["total"] if sales_today["total"] else 0.0

    # Total quantity in stock
    stock = conn.execute("SELECT SUM(quantity) as total_stock FROM products").fetchone()
    total_quantity_in_stock = stock["total_stock"] if stock["total_stock"] else 0

    # Total products sold today
    quantity_today = conn.execute("""
        SELECT SUM(oi.quantity) as total_sold
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.date) = DATE('now')
    """).fetchone()
    total_products_sold_today = quantity_today["total_sold"] if quantity_today["total_sold"] else 0

    # Top 5 selling products
    top_products = conn.execute("""
        SELECT 
            p.name AS product_name,
            p.description,
            SUM(oi.quantity) AS total_quantity,
            SUM(oi.quantity * oi.price) AS total_revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.id
        ORDER BY total_quantity DESC
        LIMIT 5
    """).fetchall()

    # Low stock alert
    low_stock_products = conn.execute("""
        SELECT name AS product_name, description, quantity
        FROM products
        WHERE quantity <= 3
        ORDER BY quantity ASC
        LIMIT 5
    """).fetchall()

    # Recent sales (limit to latest 5 sales)
    recent_sales = conn.execute("""
        SELECT * FROM sales
        ORDER BY date DESC
        LIMIT 5
    """).fetchall()

    recent_sales_data = []
    for sale in recent_sales:
        items = conn.execute("""
            SELECT p.name AS name, p.description
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (sale["order_id"],)).fetchall()

        recent_sales_data.append({
            "customer_name": sale["customer_name"],
            "items": items,
            "total_amount": sale["total_amount"]
        })

    # Frequent customers (top 10)
    frequent_customers = conn.execute("""
        SELECT customer_name, COUNT(*) as frequency
        FROM sales
        WHERE customer_name IS NOT NULL AND customer_name != ''
        GROUP BY customer_name
        HAVING COUNT(*) > 10
        ORDER BY frequency DESC
        LIMIT 10
    """).fetchall()

    # Best selling month by revenue
    best_month = conn.execute("""
        SELECT 
            strftime('%Y-%m', date) AS year_month,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY year_month
        ORDER BY revenue DESC
        LIMIT 1
    """).fetchone()

    best_selling_month = None
    if best_month:
        year, month = best_month["year_month"].split("-")
        month_name = calendar.month_name[int(month)]
        best_selling_month = {
            "month": f"{month_name} {year}",
            "revenue": round(best_month["revenue"], 2)
        }

    # Sales chart data (default last 7 days)
    rows = conn.execute("""
        SELECT DATE(date) as day, SUM(total_amount) as total
        FROM sales
        GROUP BY day
        ORDER BY day DESC
        LIMIT 7
    """).fetchall()
    labels = [row["day"] for row in reversed(rows)]
    data = [row["total"] for row in reversed(rows)]

    # Recent products (optional, used in chart_view but not necessarily needed here)
    recent_products = conn.execute("""
        SELECT name, description, quantity_added, date_added
        FROM product_entries
        ORDER BY date_added DESC
        LIMIT 5
    """).fetchall()

    notifications = get_notifications()

    conn.close()
    return render_template(
        'dashboard.html',
        todays_revenue=todays_revenue,
        total_quantity_in_stock=total_quantity_in_stock,
        total_products_sold_today=total_products_sold_today,
        top_products=top_products,
        low_stock_products=low_stock_products,
        recent_sales=recent_sales_data,
        frequent_customers=frequent_customers,
        best_selling_month=best_selling_month,
        chart_labels=labels,
        chart_data=data,
        filter_type="range",
        start_date=None,
        end_date=None,
        selected_month=None,
        selected_year=None,
        recent_products=recent_products,
        notifications=notifications,
        full_name=full_name,         
        greeting=greeting            
    )
def get_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()
    today = now.strftime('%Y-%m-%d %H:%M:%S')

    # --- Cleanup: delete notifications older than 10 days ---
    ten_days_ago = (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("DELETE FROM notifications WHERE datetime(created_at) < ?", (ten_days_ago,))

    def add_notification(message):
        """Insert a notification only if not already stored recently."""
        cursor.execute("""
            SELECT 1 FROM notifications 
            WHERE message = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (message,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO notifications (message, created_at) VALUES (?, ?)",
                (message, today)
            )

    # --- 1. Low stock products (<= 3 and > 0) ---
    cursor.execute("SELECT name, quantity FROM products WHERE quantity <= 3 AND quantity > 0")
    for product in cursor.fetchall():
        add_notification(f"⚠️ Low stock: {product['name']} ({product['quantity']} left)")

    # --- 2. Out of stock products ---
    cursor.execute("SELECT name FROM products WHERE quantity = 0")
    for product in cursor.fetchall():
        add_notification(f"❌ Out of stock: {product['name']}")

    # --- 3. Newly added products (last 24 hours) ---
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT name FROM product_entries WHERE datetime(date_added) >= ?", (yesterday,))
    for product in cursor.fetchall():
        add_notification(f"🆕 New stock added: {product['name']}")

    # --- 4. Products with no sales in the last 30 days ---
    thirty_days_ago = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT p.name 
        FROM products p
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON o.id = oi.order_id
        WHERE o.date IS NULL OR datetime(o.date) < ?
        GROUP BY p.id
    """, (thirty_days_ago,))
    for product in cursor.fetchall():
        add_notification(f"📭 No sales for '{product['name']}' in last 30 days")

    conn.commit()  # Save changes (cleanup + new notifications)

    # --- Get the latest 10 notifications ---
    cursor.execute("""
        SELECT message, created_at 
        FROM notifications
        ORDER BY created_at DESC
        LIMIT 10
    """)
    notifications = cursor.fetchall()
    conn.close()

    # Format for template
    return [{"message": n["message"], "timestamp": n["created_at"]} for n in notifications]
@app.route('/clear_notifications', methods=['POST'])
def clear_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notifications")
    conn.commit()
    conn.close()
    return jsonify({"success": True})
# ---------- 1. Lend ----------
@app.route("/lend", methods=["GET", "POST"])
def lend():
    conn = get_db()
    cursor = conn.cursor()

    # Fetch products for dropdown
    cursor.execute("SELECT id, name, quantity FROM products")
    products = cursor.fetchall()

    if request.method == "POST":
        customer_name = request.form.get("customer_name")
        product_id = request.form.get("product_id")
        quantity_taken = request.form.get("quantity_taken")

        # Validation
        if not customer_name or not product_id or not quantity_taken:
            flash("Please fill out all fields.", "danger")
            return redirect(url_for("lend"))

        quantity_taken = int(quantity_taken)

        # Check product stock
        cursor.execute("SELECT name, description, quantity FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            flash("Selected product does not exist.", "danger")
            return redirect(url_for("lend"))

        product_name, description, available_qty = product

        if quantity_taken > available_qty:
            flash(f"Not enough stock. Only {available_qty} available.", "danger")
            return redirect(url_for("lend"))

        # Insert lending record
        cursor.execute("""
            INSERT INTO lending (customer_name, product_id, product_name, description, quantity_taken)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_name, product_id, product_name, description, quantity_taken))

        # Also insert into lend_history
        cursor.execute("""
            INSERT INTO lend_history (customer_name, product_name, description, quantity_taken, action_type, date_lent)
            VALUES (?, ?, ?, ?, 'lend', datetime('now', 'localtime'))
        """, (customer_name, product_name, description, quantity_taken))

        # Update stock
        cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity_taken, product_id))

        conn.commit()
        flash("Product lent successfully.", "success")
        return redirect(url_for("lend"))

    conn.close()
    return render_template("lend.html", products=products)


# ---------- 2. Lend History ----------
@app.route("/lend_history", methods=["GET"])
def lend_history():
    search_name = request.args.get("customer_name", "").strip()
    conn = get_db()
    cursor = conn.cursor()

    if search_name:
        cursor.execute("""
            SELECT * FROM lending
            WHERE customer_name LIKE ?
            ORDER BY date_lent DESC
        """, ('%' + search_name + '%',))
    else:
        cursor.execute("SELECT * FROM lending ORDER BY date_lent DESC")

    lends = cursor.fetchall()
    conn.close()

    return render_template("lend_history.html", lends=lends, search_name=search_name)


# ---------- 3. Return / Pay ----------
@app.route("/return_pay", methods=["GET", "POST"])
def return_pay():
    if request.method == "POST":
        action_type = request.form["action_type"]  # return or pay
        customer_name = request.form["customer_name"].strip()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM lending
            WHERE customer_name = ?
            ORDER BY date_lent DESC
        """, (customer_name,))
        items = cursor.fetchall()
        conn.close()

        return render_template("return_pay_list.html", action_type=action_type, items=items, customer_name=customer_name)

    return render_template("return_pay.html")


# ---------- 4. Process Return / Pay ----------
@app.route("/process_return_pay/<int:lending_id>", methods=["POST"])
def process_return_pay(lending_id):
    action_type = request.form["action_type"]
    quantity = int(request.form["quantity"])

    conn = get_db()
    cursor = conn.cursor()

    # Get lending record
    cursor.execute("SELECT * FROM lending WHERE id = ?", (lending_id,))
    lending_record = cursor.fetchone()

    if lending_record:
        remaining_qty = lending_record["quantity_taken"] - quantity

        # If return, restore stock
        if action_type == "return":
            cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", 
                           (quantity, lending_record["product_id"]))

        # Update lending table
        if remaining_qty > 0:
            cursor.execute("UPDATE lending SET quantity_taken = ? WHERE id = ?", 
                           (remaining_qty, lending_id))
        else:
            cursor.execute("DELETE FROM lending WHERE id = ?", (lending_id,))

        # Insert into lending_transactions
        cursor.execute("""
            INSERT INTO lending_transactions (lending_id, customer_name, product_id, product_name, quantity, action_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            lending_id,
            lending_record["customer_name"],
            lending_record["product_id"],
            lending_record["product_name"],
            quantity,
            action_type
        ))

        # ✅ Also insert into lend_history
        cursor.execute("""
            INSERT INTO lend_history (customer_name, product_name, description, quantity_taken, action_type, date_lent)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """, (
            lending_record["customer_name"],
            lending_record["product_name"],
            lending_record["description"],
            quantity,
            action_type
        ))

        conn.commit()
    conn.close()

    return redirect(url_for("return_pay"))


# ---------- 5. Customer History ----------
@app.route("/customer_history", methods=["GET"])
def customer_history():
    customer_name = request.args.get("customer_name", "").strip()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if customer_name:
        cursor.execute("""
            SELECT * FROM lend_history
            WHERE customer_name LIKE ?
            ORDER BY date_lent ASC, id ASC
        """, ('%' + customer_name + '%',))
    else:
        cursor.execute("""
            SELECT * FROM lend_history
            ORDER BY date_lent ASC, id ASC
        """)

    records = cursor.fetchall()
    conn.close()

    # Track balances per lending record separately
    record_balances = {}  # {lending_id: remaining_qty}
    history_with_balance = []

    for rec in records:
        lid = rec["id"]
        qty = rec["quantity_taken"]
        action = rec["action_type"]

        # Initialize balance for lending action
        if action == "lend":
            record_balances[lid] = qty
        elif action in ("return", "pay"):
            # Reduce balance from the original lending record
            record_balances[lid] = record_balances.get(lid, 0) - qty
            if record_balances[lid] < 0:
                record_balances[lid] = 0  # prevent negative

        # Determine status
        status = "Pending" if record_balances.get(lid, 0) > 0 else "Cleared"
        balance = record_balances.get(lid, 0)

        history_with_balance.append({
            "date_lent": rec["date_lent"],
            "customer_name": rec["customer_name"],
            "product_name": rec["product_name"],
            "description": rec["description"],
            "quantity_taken": rec["quantity_taken"],
            "action_type": rec["action_type"],
            "balance": balance,
            "status": status
        })

    return render_template("customer_history.html", history=history_with_balance)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        quantity = int(request.form['quantity'])

        existing = query_db(
            'SELECT * FROM products WHERE name = ? AND description = ?',
            [name, description], one=True
        )

        if existing:
            new_quantity = existing['quantity'] + quantity
            query_db('UPDATE products SET quantity = ? WHERE id = ?', [new_quantity, existing['id']])
            product_id = existing['id']
        else:
            query_db('INSERT INTO products (name, description, quantity) VALUES (?, ?, ?)', [name, description, quantity])
            product_id = query_db('SELECT last_insert_rowid() AS id', one=True)['id']

        query_db('''INSERT INTO product_entries (product_id, name, description, quantity_added, date_added)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                 [product_id, name, description, quantity])
        return redirect(url_for('view_products'))

    return render_template('add_product.html')

@app.route('/view_products')
def view_products():
    products = query_db("SELECT id, name, description, quantity FROM products")
    return render_template('view_products.html', products=products)

@app.route('/product_entries')
def view_product_entries():
    name_filter = request.args.get('name', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = '''SELECT name, description, quantity_added, date_added FROM product_entries WHERE 1=1'''
    params = []

    if name_filter:
        query += ' AND name LIKE ?'
        params.append(f'%{name_filter}%')
    if start_date:
        query += ' AND DATE(date_added) >= DATE(?)'
        params.append(start_date)
    if end_date:
        query += ' AND DATE(date_added) <= DATE(?)'
        params.append(end_date)

    query += ' ORDER BY date_added DESC'
    entries = query_db(query, params)
    return render_template('product_entries.html', entries=entries,
                           name_filter=name_filter,
                           start_date=start_date,
                           end_date=end_date)

@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        customer = request.form['customer_name']
        payment_mode = request.form['payment_mode']
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        totals = request.form.getlist('item_total[]')

        total_amount = sum(float(t) for t in totals)

        cur.execute("INSERT INTO orders (customer_name, payment_mode, total_amount) VALUES (?, ?, ?)",
                    (customer, payment_mode, total_amount))
        order_id = cur.lastrowid

        for i in range(len(product_ids)):
            pid = int(product_ids[i])
            qty = int(quantities[i])
            price = float(prices[i])
            total = float(totals[i])

            product = cur.execute("SELECT name, description FROM products WHERE id = ?", (pid,)).fetchone()

            if product:
                cur.execute("""INSERT INTO order_items 
                               (order_id, product_id, name, description, quantity, price, total)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (order_id, pid, product['name'], product['description'], qty, price, total))

                cur.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (qty, pid))

        cur.execute("""INSERT INTO sales 
                       (order_id, customer_name, total_amount, payment_mode, date)
                       VALUES (?, ?, ?, ?, datetime('now', 'localtime'))""",
                    (order_id, customer, total_amount, payment_mode))

        conn.commit()
        conn.close()
        return redirect(url_for('receipt', order_id=order_id))

    products = cur.execute("SELECT * FROM products WHERE quantity > 0").fetchall()
    conn.close()
    return render_template('add_order.html', products=products)

@app.route('/receipt/<int:order_id>')
def receipt(order_id):
    conn = get_db_connection()
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    items = conn.execute(
        "SELECT quantity, price, name, description FROM order_items WHERE order_id = ?", 
        (order_id,)
    ).fetchall()

    item_list = [{
        'product_name': f"{item['name']} ({item['description']})",
        'quantity': item['quantity'],
        'price': item['price'],
        'subtotal': item['quantity'] * item['price']
    } for item in items]

    total = sum(item['subtotal'] for item in item_list)

    # ✅ Always show actual logged-in user
    active_user = session['full_name'] if 'full_name' in session else "Unknown User"

    conn.close()

    return render_template(
        'receipt.html',
        order=order,
        items=item_list,
        total=total,
        active_user=active_user,
        current_time=datetime.now()
    )
@app.route('/receipt_pdf/<int:order_id>')
def receipt_pdf(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()

    if not order:
        conn.close()
        return "Order not found", 404

    items = conn.execute("""
        SELECT oi.quantity, oi.price, p.name, p.description 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    # Prepare item list with subtotals
    item_list = [{
        'product_name': f"{item['name']} ({item['description']})",
        'quantity': item['quantity'],
        'price': item['price'],
        'subtotal': item['quantity'] * item['price']
    } for item in items]

    total = sum(item['subtotal'] for item in item_list)
    active_user = session.get('full_name', 'System User')
    conn.close()

    # Render HTML for the PDF
    html = render_template(
        'receipt_pdf.html',
        order=order,
        items=item_list,
        total=total,
        active_user=active_user,
        current_time=datetime.now().strftime("%d %b %Y %I:%M %p")
    )

    # Generate PDF
    result = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(html.encode("utf-8")), dest=result)

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=receipt_{order_id}.pdf'
    return response
@app.route('/product_insight')
def product_insight():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = """SELECT p.name as product_name, p.description,
                      SUM(oi.quantity) as total_quantity,
                      SUM(oi.quantity * oi.price) as total_revenue
               FROM order_items oi
               JOIN orders o ON oi.order_id = o.id
               JOIN products p ON oi.product_id = p.id"""
    params = []
    filters = []

    if start_date:
        filters.append("o.date >= ?")
        params.append(start_date)
    if end_date:
        filters.append("o.date <= ?")
        params.append(end_date)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " GROUP BY oi.product_id ORDER BY total_quantity DESC"
    products = query_db(query, params)
    return render_template('product_insight.html', products=products, start_date=start_date, end_date=end_date)

@app.route('/view_sales')
def view_sales():
    conn = get_db_connection()
    sales = conn.execute("""
        SELECT o.id AS order_id, o.customer_name, o.payment_mode,
               o.date AS sale_date, oi.name AS product_name,
               oi.description, oi.quantity, oi.price AS unit_price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        ORDER BY o.date DESC
    """).fetchall()

    grouped_sales = {}
    grand_total = 0

    for sale in sales:
        order_id = sale['order_id']
        raw_date = sale['sale_date']

        try:
            if isinstance(raw_date, str):
                sale_date = datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S')
            else:
                sale_date = raw_date
        except:
            sale_date = raw_date

        if order_id not in grouped_sales:
            grouped_sales[order_id] = {
                'customer_name': sale['customer_name'],
                'payment_mode': sale['payment_mode'],
                'date': sale_date,
                'items': [],
                'total_amount': 0
            }

        item_total = sale['quantity'] * sale['unit_price']
        grouped_sales[order_id]['items'].append({
            'product_name': sale['product_name'],
            'description': sale['description'],
            'quantity': sale['quantity'],
            'price': sale['unit_price']
        })
        grouped_sales[order_id]['total_amount'] += item_total
        grand_total += item_total

    conn.close()
    return render_template('view_sales.html', grouped_sales=grouped_sales, grand_total=grand_total)

@app.route('/sales_pdf', endpoint='sales_pdf')
def sales_pdf():
    conn = get_db_connection()
    sales = conn.execute("""
        SELECT o.id AS order_id, o.customer_name, o.payment_mode,
               DATE(o.date) AS sale_date, oi.name AS product_name,
               oi.description, oi.quantity, oi.price AS unit_price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        ORDER BY o.date DESC
    """).fetchall()

    grouped_sales = {}
    for sale in sales:
        order_id = sale['order_id']
        if order_id not in grouped_sales:
            grouped_sales[order_id] = {
                'customer_name': sale['customer_name'],
                'payment_mode': sale['payment_mode'],
                'date': sale['sale_date'],
                'items': [],
                'total_amount': 0
            }
        item_total = sale['quantity'] * sale['unit_price']
        grouped_sales[order_id]['items'].append({
            'product_name': sale['product_name'],
            'description': sale['description'],
            'quantity': sale['quantity'],
            'price': sale['unit_price']
        })
        grouped_sales[order_id]['total_amount'] += item_total

    grand_total = sum(order['total_amount'] for order in grouped_sales.values())
    rendered = render_template('sales_pdf.html', grouped_sales=grouped_sales, grand_total=grand_total)
    pdf = HTML(string=rendered).write_pdf()

    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='all_sales.pdf'
    )
@app.route('/mydashboard')
def mydashboard():
    return render_template('mydashboard.html')
@app.route('/todays_sales')
def todays_sales():
    conn = get_db_connection()
    sales = conn.execute("""
        SELECT o.id AS order_id, o.customer_name, o.payment_mode, o.date AS sale_date,
               oi.name AS product_name, oi.description, oi.quantity, oi.price AS unit_price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE DATE(o.date) = DATE('now', 'localtime')
        ORDER BY o.date DESC
    """).fetchall()

    grouped_sales = {}
    grand_total = 0

    for sale in sales:
        order_id = sale['order_id']
        sale_date = sale['sale_date']
        if order_id not in grouped_sales:
            grouped_sales[order_id] = {
                'customer_name': sale['customer_name'],
                'payment_mode': sale['payment_mode'],
                'date': sale_date,
                'items': [],
                'total_amount': 0
            }
        item_total = sale['quantity'] * sale['unit_price']
        grouped_sales[order_id]['items'].append({
            'product_name': sale['product_name'],
            'description': sale['description'],
            'quantity': sale['quantity'],
            'price': sale['unit_price']
        })
        grouped_sales[order_id]['total_amount'] += item_total
        grand_total += item_total

    conn.close()
    return render_template('todays_sales.html', grouped_sales=grouped_sales, grand_total=grand_total)
@app.route('/admin/login_attempts')
def view_login_attempts():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    attempts = LoginAttempt.query.order_by(LoginAttempt.timestamp.desc()).all()
    return render_template('login_attempts.html', attempts=attempts)


@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        phone = (request.form.get('phone_number') or '').strip()
        password = request.form.get('password')
        role = request.form.get('role', 'user')

        if User.query.filter((User.email==email)|(User.phone_number==phone)).first():
            flash("User with this email or phone already exists.", "danger")
            return redirect(url_for('create_user'))

        new_user = User(
            full_name=full_name,
            email=email,
            phone_number=phone,
            role=role
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash(f"User {full_name} created successfully.", "success")
        # Redirect to the admin dashboard so you can see the new user
        return redirect(url_for('admin_dashboard_view'))

    return render_template('create_user.html')

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'], endpoint='edit_user')
def edit_user(user_id):
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        # Safely get form data; if None, use current value
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        role = request.form.get('role', 'user')
        password = request.form.get('password')

        if full_name:
            user.full_name = full_name.strip()
        if email:
            user.email = email.strip()
        if phone_number:
            user.phone_number = phone_number.strip()
        if role:
            user.role = role
        if password:
            user.set_password(password)  # only update if password is entered

        db.session.commit()  # commit changes to DB
        flash(f"User {user.full_name} updated successfully.", "success")
        return redirect(url_for('admin_dashboard_view'))

    return render_template('edit_user.html', user=user)

@app.route('/admin/toggle_lock/<int:user_id>', endpoint='toggle_lock')
def toggle_lock(user_id):
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_locked = not user.is_locked
    db.session.commit()

    status = "locked" if user.is_locked else "unlocked"
    flash(f"User {user.full_name} has been {status}.", "success")
    return redirect(url_for('admin_dashboard_view'))


@app.route('/admin/delete_user/<int:user_id>', endpoint='delete_user')
def delete_user(user_id):
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    flash(f"User {user.full_name} has been deleted.", "success")
    return redirect(url_for('admin_dashboard_view'))


@app.route('/admin/force_reset/<int:user_id>', methods=['GET', 'POST'], endpoint='force_reset')
def force_reset(user_id):
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)
            db.session.commit()
            flash(f"Password for {user.full_name} has been reset.", "success")
            return redirect(url_for('admin_dashboard_view'))

    return render_template('force_reset.html', user=user)


@app.route('/admin/toggle_active/<int:user_id>', endpoint='toggle_active')
def toggle_active(user_id):
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_active = not getattr(user, 'is_active', True)
    db.session.commit()

    status = "deactivated" if not user.is_active else "reactivated"
    flash(f"User {user.full_name} has been {status}.", "success")
    return redirect(url_for('admin_dashboard_view'))

if __name__ == '__main__':
    app.run(debug=True)