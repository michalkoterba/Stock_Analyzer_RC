import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
from datetime import datetime

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "stock_analizer_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


def create_database():
    """Connects to PostgreSQL and creates the database if it doesn't exist."""
    conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    conn.set_client_encoding('WIN1250')
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [DB_NAME])
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(sql.SQL("CREATE DATABASE {}".format(DB_NAME)))
    cursor.close()
    conn.close()

def create_tables():
    """Creates necessary tables in the database."""
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    cursor = conn.cursor()

    queries = [
        """
        CREATE TABLE IF NOT EXISTS issuers (
            id SERIAL PRIMARY KEY,
            name TEXT,
            tax_id TEXT UNIQUE,
            address TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            item_code TEXT UNIQUE,
            description TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            invoice_number TEXT UNIQUE,
            issuer_id INTEGER REFERENCES issuers(id),
            date TIMESTAMP,
            issue_date TIMESTAMP,
            xml TEXT,
            pdf BYTEA
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS invoice_items (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER REFERENCES invoices(id),
            item_id INTEGER REFERENCES items(id),
            quantity INTEGER,
            price DECIMAL(10,2)
        )
        """
    ]

    for query in queries:
        cursor.execute(query)

    conn.commit()
    cursor.close()
    conn.close()

def import_makro_xml_invoice(xml_file, pdf_file=None, overwrite=False):
    """Imports an XML invoice into the database."""
    tree = ET.parse(xml_file)
    root = tree.getroot()

    invoice_number = root.find(".//szInvoiceID").text
    issuer_name = root.find(".//szExternalStorePartyOrganizationName").text
    tax_id = root.find(".//szCompanyTaxNmbr").text
    address = root.find(".//szExternalStorePartyAddressStreetName").text
    issue_date_str = root.find(".//szDate").text
    issue_date = datetime.strptime(issue_date_str, "%Y%m%d%H%M%S")

    with open(xml_file, "r", encoding="ISO-8859-2") as f:
        xml_content = f.read()

    pdf_content = None
    if pdf_file:
        with open(pdf_file, "rb") as f:
            pdf_content = f.read()

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM invoices WHERE invoice_number = %s", (invoice_number,))
    existing_invoice = cursor.fetchone()

    if existing_invoice:
        if not overwrite:
            print("Invoice already exists. Skipping import.")
            cursor.close()
            conn.close()
            return
        else:
            cursor.execute("DELETE FROM invoice_items WHERE invoice_id = %s", (existing_invoice[0],))
            cursor.execute("DELETE FROM invoices WHERE id = %s", (existing_invoice[0],))

    cursor.execute("INSERT INTO issuers (name, tax_id, address) VALUES (%s, %s, %s) ON CONFLICT (tax_id) DO NOTHING RETURNING id",
                   (issuer_name, tax_id, address))
    issuer_id = cursor.fetchone()

    if issuer_id is None:
        cursor.execute("SELECT id FROM issuers WHERE tax_id = %s", (tax_id,))
        issuer_id = cursor.fetchone()[0]
    else:
        issuer_id = issuer_id[0]

    cursor.execute("INSERT INTO invoices (invoice_number, issuer_id, date, issue_date, xml, pdf) VALUES (%s, %s, NOW(), %s, %s, %s) RETURNING id",
                   (invoice_number, issuer_id, issue_date, xml_content, pdf_content))
    invoice_id = cursor.fetchone()[0]

    for article in root.findall(".//ART_SALE"):
        item_code = article.find(".//szItemID").text
        description = article.find(".//szDescription").text
        quantity = int(float(article.find(".//dQuantityEntry").text)) * int(float(article.find(".//dPieceQuantity").text))
        price = float(article.find(".//dTaAveragePiecePriceDiscounted").text)

        cursor.execute("INSERT INTO items (item_code, description) VALUES (%s, %s) ON CONFLICT (item_code) DO NOTHING RETURNING id",
                       (item_code, description))
        item_id = cursor.fetchone()

        if item_id is None:
            cursor.execute("SELECT id FROM items WHERE item_code = %s", (item_code,))
            item_id = cursor.fetchone()[0]
        else:
            item_id = item_id[0]

        cursor.execute("INSERT INTO invoice_items (invoice_id, item_id, quantity, price) VALUES (%s, %s, %s, %s)",
                       (invoice_id, item_id, quantity, price))

    conn.commit()
    cursor.close()
    conn.close()
    print("Invoice imported successfully.")

def setup_database():
    create_database()
    create_tables()

if __name__ == "__main__":
    setup_database()
