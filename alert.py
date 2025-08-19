import sqlite3
import smtplib
import schedule
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from collections import defaultdict

# --- FUNCTION TO GENERATE ALERT ---
def send_daily_alert():
    print(f"🔔 Running daily alert at {datetime.now()}")

    # --- DATABASE CONNECTION ---
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

    # --- LOW STOCK PRODUCTS ---
    cursor.execute("SELECT name, description, quantity FROM products WHERE quantity <= 3")
    low_stock = cursor.fetchall()

    # --- UNSOLD PRODUCTS ---
    cursor.execute("""
        SELECT p.name, p.description
        FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.product_id = p.id AND o.date >= ?
        )
    """, (thirty_days_ago,))
    unsold = cursor.fetchall()

    # --- TODAY'S SALES SUMMARY ---
    cursor.execute("""
        SELECT SUM(quantity), SUM(quantity * price)
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE DATE(o.date) = ?
    """, (today,))
    sold_today = cursor.fetchone()
    total_items_today = sold_today[0] or 0
    total_amount_today = sold_today[1] or 0

    # --- TOP PRODUCT OF THE WEEK ---
    cursor.execute("""
        SELECT p.name, SUM(oi.quantity) as total_sold
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.date >= ?
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 1
    """, (week_ago,))
    top_product = cursor.fetchone()

    # --- FULL TODAY SALES FOR PDF ---
    cursor.execute("""
        SELECT o.id AS order_id, o.customer_name, o.payment_mode, o.date AS sale_date,
               oi.name AS product_name, oi.description, oi.quantity, oi.price AS unit_price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE DATE(o.date) = DATE('now', 'localtime')
        ORDER BY o.date DESC
    """)
    sales_data = cursor.fetchall()

    # --- CUSTOMERS WHO HAVE NOT RETURNED/PAID IN 14 DAYS ---
    cursor.execute("""
        SELECT customer_name, product_name, description, quantity_taken, date_lent
        FROM lend_history
        WHERE action_type = 'lend'
          AND DATE(date_lent) <= DATE(?)
          AND customer_name NOT IN (
              SELECT customer_name FROM lend_history
              WHERE action_type IN ('return','pay')
                AND DATE(date_lent) > DATE(?)
          )
        ORDER BY date_lent ASC
    """, (fourteen_days_ago, fourteen_days_ago))
    overdue_customers = cursor.fetchall()

    conn.close()

    # --- GENERATE PDF ---
    def generate_pdf(sales, filename="todays_sales.pdf"):
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Kikitech - Today's Sales Report", styles['Title']))
        elements.append(Spacer(1, 12))

        grouped_sales = defaultdict(lambda: {
            'customer': '',
            'payment_mode': '',
            'sale_date': '',
            'items': [],
            'subtotal': 0
        })

        grand_total = 0
        for s in sales:
            oid = s['order_id']
            total = s['quantity'] * s['unit_price']
            grouped_sales[oid]['customer'] = s['customer_name']
            grouped_sales[oid]['payment_mode'] = s['payment_mode']
            grouped_sales[oid]['sale_date'] = s['sale_date']
            grouped_sales[oid]['items'].append({
                'product': s['product_name'],
                'description': s['description'],
                'qty': s['quantity'],
                'price': s['unit_price'],
                'total': total
            })
            grouped_sales[oid]['subtotal'] += total
            grand_total += total

        for order_id, data in grouped_sales.items():
            elements.append(Paragraph(f"<b>Sale ID:</b> {order_id}", styles['Heading4']))
            elements.append(Paragraph(f"<b>Customer:</b> {data['customer']}", styles['Normal']))
            elements.append(Paragraph(f"<b>Payment Mode:</b> {data['payment_mode']} | <b>Time:</b> {data['sale_date']}", styles['Normal']))
            elements.append(Spacer(1, 6))

            table_data = [['Product', 'Description', 'Qty', 'Unit Price', 'Total']]
            for item in data['items']:
                table_data.append([
                    item['product'],
                    item['description'],
                    str(item['qty']),
                    f"{item['price']:.2f}",
                    f"{item['total']:.2f}"
                ])
            table_data.append(['', '', '', 'Subtotal:', f"{data['subtotal']:.2f}"])

            table = Table(table_data, colWidths=[100, 150, 50, 60, 60])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#007b5e")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 24))

        elements.append(Paragraph(f"<b>Grand Total for All Sales Today:</b> KES {grand_total:.2f}", styles['Heading2']))
        doc.build(elements)

    pdf_filename = "todays_sales.pdf"
    generate_pdf(sales_data, pdf_filename)

    # --- EMAIL CONTENT ---
    PDF_DOWNLOAD_URL = 'http://127.0.0.1:5000/download_todays_sales'
    html = f"<h2>Daily Alert for {today}</h2>"

    # --- EMAIL SENDING ---
    sender = "kikitechsupplies@gmail.com"
    receiver = "Dianamartha237@gmail.com"
    password = "zknexvddxgliignh"

    msg = MIMEMultipart("mixed")
    msg['Subject'] = f"Kikitech Daily Alert - {today}"
    msg['From'] = sender
    msg['To'] = receiver
    msg.attach(MIMEText(html, "html"))

    with open(pdf_filename, "rb") as f:
        pdf_part = MIMEApplication(f.read(), _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(pdf_part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("✅ Alert email with PDF sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- SCHEDULE DAILY ALERT ---
schedule.every().day.at("23:00").do(send_daily_alert)

# --- KEEP SCRIPT RUNNING ---
print("⏳ Alert scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(60)