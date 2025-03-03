from flask import Flask, render_template, request, redirect, url_for
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DB_NAME = os.getenv("DB_NAME", "stock_analizer_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

connection_parms = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}

def get_invoices(start_date, end_date):
    conn = psycopg2.connect(**connection_parms)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT invoices.id, invoices.invoice_number, issuers.name, TO_CHAR(invoices.issue_date, 'DD-MM-YYYY'),
               TO_CHAR(SUM(invoice_items.quantity * invoice_items.price), 'FM999G999G990D00') || 'zł' AS total_value
        FROM invoices 
        JOIN issuers ON invoices.issuer_id = issuers.id 
        JOIN invoice_items ON invoices.id = invoice_items.invoice_id
        WHERE invoices.issue_date BETWEEN %s AND %s
        GROUP BY invoices.id, issuers.name
        ORDER BY invoices.issue_date DESC
    """, (start_date, end_date))
    invoices = cursor.fetchall()

    cursor.execute("""
        SELECT TO_CHAR(SUM(invoice_items.quantity * invoice_items.price), 'FM999G999G990D00') || 'zł' 
        FROM invoice_items 
        JOIN invoices ON invoice_items.invoice_id = invoices.id
        WHERE invoices.issue_date BETWEEN %s AND %s
    """, (start_date, end_date))
    total_sum = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return invoices, total_sum

def get_items(start_date, end_date):
    conn = psycopg2.connect(**connection_parms)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.item_code, items.description, 
               TO_CHAR(SUM(invoice_items.quantity * invoice_items.price), 'FM999G999G990D00') || 'zł' AS total_value,
               TO_CHAR(MIN(invoice_items.price), 'FM999G999G990D00') || 'zł' AS lowest_price,
               TO_CHAR(MAX(invoice_items.price), 'FM999G999G990D00') || 'zł' AS highest_price,
               TO_CHAR(AVG(invoice_items.price), 'FM999G999G990D00') || 'zł' AS average_price,
               TO_CHAR((SELECT price FROM invoice_items WHERE item_id = items.id ORDER BY id DESC LIMIT 1), 'FM999G999G990D00') || 'zł' AS last_price
        FROM items 
        JOIN invoice_items ON items.id = invoice_items.item_id 
        JOIN invoices ON invoice_items.invoice_id = invoices.id
        WHERE invoices.issue_date BETWEEN %s AND %s
        GROUP BY items.item_code, items.description, items.id 
        ORDER BY SUM(invoice_items.quantity * invoice_items.price) DESC
    """, (start_date, end_date))
    items = cursor.fetchall()

    cursor.execute("""
        SELECT TO_CHAR(SUM(invoice_items.quantity * invoice_items.price), 'FM999G999G990D00') || 'zł' 
        FROM invoice_items 
        JOIN invoices ON invoice_items.invoice_id = invoices.id
        WHERE invoices.issue_date BETWEEN %s AND %s
    """, (start_date, end_date))
    total_sum = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return items, total_sum

def get_invoice_details(invoice_id):
    conn = psycopg2.connect(**connection_parms)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT invoices.invoice_number, issuers.name, TO_CHAR(invoices.issue_date, 'DD-MM-YYYY')
        FROM invoices
        JOIN issuers ON invoices.issuer_id = issuers.id
        WHERE invoices.id = %s
    """, (invoice_id,))
    invoice_info = cursor.fetchone()

    cursor.execute("""
        SELECT items.item_code, items.description, invoice_items.quantity,
               TO_CHAR(invoice_items.price, 'FM999G999G990D00') || 'zł' AS price,
               TO_CHAR(invoice_items.quantity * invoice_items.price, 'FM999G999G990D00') || 'zł' AS total_value
        FROM invoice_items
        JOIN items ON invoice_items.item_id = items.id
        WHERE invoice_items.invoice_id = %s
    """, (invoice_id,))
    items = cursor.fetchall()

    cursor.execute("""
        SELECT TO_CHAR(SUM(invoice_items.quantity * invoice_items.price), 'FM999G999G990D00') || 'zł' 
        FROM invoice_items 
        WHERE invoice_items.invoice_id = %s
    """, (invoice_id,))
    total_sum = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return invoice_info, items, total_sum

def get_item_purchases(item_code):
    conn = psycopg2.connect(**connection_parms)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT description FROM items WHERE item_code = %s
    """, (item_code,))
    item_name = cursor.fetchone()[0]

    cursor.execute("""
        SELECT invoices.id, invoices.invoice_number, TO_CHAR(invoices.issue_date, 'DD-MM-YYYY'),
               TO_CHAR(invoice_items.price, 'FM999G999G990D00') || 'zł' AS unit_price,
               invoice_items.quantity,
               TO_CHAR(invoice_items.quantity * invoice_items.price, 'FM999G999G990D00') || 'zł' AS total_value
        FROM invoice_items
        JOIN invoices ON invoice_items.invoice_id = invoices.id
        JOIN items ON invoice_items.item_id = items.id
        WHERE items.item_code = %s
        ORDER BY invoices.issue_date DESC
    """, (item_code,))
    purchases = cursor.fetchall()

    cursor.close()
    conn.close()
    return item_name, purchases

@app.route('/')
def index():
    return redirect(url_for('items'))

@app.route('/invoices')
def invoices():
    start_date = request.args.get('start_date', '2000-01-01')
    end_date = request.args.get('end_date', '2100-01-01')
    invoices, total_sum = get_invoices(start_date, end_date)
    return render_template('invoices.html', invoices=invoices, total_sum=total_sum, start_date=start_date, end_date=end_date)

@app.route('/items')
def items():
    start_date = request.args.get('start_date', '2000-01-01')
    end_date = request.args.get('end_date', '2100-01-01')
    items, total_sum = get_items(start_date, end_date)
    return render_template('items.html', items=items, total_sum=total_sum, start_date=start_date, end_date=end_date)

@app.route('/item/<string:item_code>')
def item_purchases(item_code):
    item_name, purchases = get_item_purchases(item_code)
    return render_template('item_purchases.html', item_code=item_code, item_name=item_name, purchases=purchases)

@app.route('/invoice/<int:invoice_id>')
def invoice_details(invoice_id):
    invoice_info, items, total_sum = get_invoice_details(invoice_id)
    return render_template('invoice_details.html', invoice_info=invoice_info, items=items, total_sum=total_sum)

if __name__ == '__main__':
    app.run(debug=True)
