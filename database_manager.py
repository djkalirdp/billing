"""
================================================================================
  database_manager.py  —  Web App Version (Flask Compatible)
  Converted from: Python Tkinter Desktop App → Flask Web Application
  
  Changes Made:
    1. Thread-safe SQLite connections (check_same_thread=False)
    2. Password hashing using werkzeug.security (bcrypt-style)
    3. All functions return Python dicts/lists (JSON-serializable)
    4. Added get_purchase_payments() for web ledger view
    5. Added update_product_stock() for purchase stock-in feature
    6. Added search functions for API endpoints
    7. Error handling improved with proper return types
    8. All sqlite3.Row objects converted to plain dicts
================================================================================
"""

import sqlite3
import os
import shutil
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
DB_FILE    = os.path.join('data', 'billing_app.db')
BACKUP_DIR = 'backups'


# ─────────────────────────────────────────────
#  CONNECTION HELPER
# ─────────────────────────────────────────────
def get_db_connection():
    """
    Returns a thread-safe SQLite connection.
    row_factory = sqlite3.Row allows dict-like column access.
    check_same_thread=False is required for Flask's threaded server.
    """
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrency for web
    conn.execute("PRAGMA foreign_keys=ON")    # Enforce FK constraints
    return conn


def row_to_dict(row):
    """Convert a single sqlite3.Row → plain Python dict."""
    return dict(row) if row else None


def rows_to_list(rows):
    """Convert list of sqlite3.Row → list of plain Python dicts."""
    return [dict(r) for r in rows] if rows else []


# ─────────────────────────────────────────────
#  GENERIC QUERY EXECUTOR
# ─────────────────────────────────────────────
def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Central query runner.
    Returns:
      - lastrowid  (int)   if commit=True
      - dict               if fetchone=True
      - list of dicts      if fetchall=True
      - None               otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        elif fetchone:
            return row_to_dict(cursor.fetchone())
        elif fetchall:
            return rows_to_list(cursor.fetchall())
        return None
    except sqlite3.Error as e:
        print(f"[DB ERROR] {e}  |  Query: {query}  |  Params: {params}")
        conn.rollback()
        return None
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  TABLE CREATION (Run once at app startup)
# ─────────────────────────────────────────────
def create_tables():
    """
    Creates all required tables if they don't exist.
    Also inserts a default Admin user on first run.
    """
    conn = get_db_connection()
    c = conn.cursor()

    # ── Products ──────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL UNIQUE,
            hsn             TEXT,
            gst_rate        REAL    NOT NULL,
            rate            REAL    NOT NULL,          -- cost / purchase price
            stock_qty       REAL    NOT NULL DEFAULT 0,
            unit            TEXT,
            selling_price   REAL    DEFAULT 0,
            wholesale_price REAL    DEFAULT 0
        )
    ''')

    # ── Vendors ───────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE,
            gstin   TEXT,
            address TEXT,
            phone   TEXT,
            email   TEXT
        )
    ''')

    # ── Buyers / Customers ────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS buyers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            gstin           TEXT,
            address         TEXT,
            phone           TEXT,
            email           TEXT,
            state           TEXT,
            opening_balance REAL DEFAULT 0
        )
    ''')

    # ── Sales Invoices ────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no     TEXT    UNIQUE NOT NULL,
            invoice_date   TEXT    NOT NULL,
            buyer_id       INTEGER,
            payment_mode   TEXT,
            order_ref      TEXT,
            dispatch_info  TEXT,
            subtotal       REAL    NOT NULL DEFAULT 0,
            total_discount REAL    NOT NULL DEFAULT 0,
            taxable_value  REAL    NOT NULL DEFAULT 0,
            total_gst      REAL    NOT NULL DEFAULT 0,
            total_cgst     REAL    NOT NULL DEFAULT 0,
            total_sgst     REAL    NOT NULL DEFAULT 0,
            total_igst     REAL    NOT NULL DEFAULT 0,
            freight        REAL    DEFAULT 0,
            round_off      REAL    DEFAULT 0,
            grand_total    REAL    NOT NULL DEFAULT 0,
            paid_amount       REAL    DEFAULT 0,
            previous_balance  REAL    DEFAULT 0,
            FOREIGN KEY (buyer_id) REFERENCES buyers(id)
        )
    ''')

    # Migration: add paid_amount to existing databases
    for col_sql in [
        "ALTER TABLE invoices ADD COLUMN paid_amount REAL DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN previous_balance REAL DEFAULT 0",
    ]:
        try:
            c.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # column already exists

    # ── Invoice Line Items ────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id       INTEGER,
            product_id       INTEGER,
            description      TEXT,
            hsn              TEXT,
            gst_rate         REAL,
            quantity         REAL,
            rate             REAL,
            discount_percent REAL DEFAULT 0,
            amount           REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # ── Purchase Bills ────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id      INTEGER NOT NULL,
            bill_no        TEXT,
            purchase_date  TEXT,
            total_amount   REAL DEFAULT 0,
            amount_paid    REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'Unpaid',
            notes          TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # ── Purchase Payments ─────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id  INTEGER NOT NULL,
            payment_date TEXT,
            amount       REAL,
            payment_mode TEXT,
            reference_no TEXT,
            FOREIGN KEY (purchase_id) REFERENCES purchases(id)
        )
    ''')

    # ── Customer Receipts / Payments ──────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS customer_payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id     INTEGER NOT NULL,
            payment_date TEXT,
            amount       REAL,
            payment_mode TEXT,
            notes        TEXT,
            FOREIGN KEY (buyer_id) REFERENCES buyers(id)
        )
    ''')

    # ── Users (Login + Roles) ─────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL   -- 'Admin' | 'Cashier'
        )
    ''')

    # ── Default Admin (only if no users exist) ─
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        hashed_pw = generate_password_hash('admin123')
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ('admin', hashed_pw, 'Admin')
        )
        print("[INFO] Default admin created → username: admin | password: admin123")

    conn.commit()
    conn.close()
    print("[INFO] All tables verified / created successfully.")


# ─────────────────────────────────────────────
#  BACKUP
# ─────────────────────────────────────────────
def daily_backup():
    """
    Creates a dated backup of the SQLite DB file (once per day).
    Call this from a Flask before_request or a scheduler.
    """
    if not os.path.exists(DB_FILE):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d")
    bf = os.path.join(BACKUP_DIR, f"backup_{ts}.db")
    if not os.path.exists(bf):
        shutil.copy2(DB_FILE, bf)
        print(f"[BACKUP] Created: {bf}")


# ─────────────────────────────────────────────
#  USER AUTH
# ─────────────────────────────────────────────
def check_login(username, password):
    """
    Verifies credentials using hashed password comparison.
    Returns role string ('Admin' / 'Cashier') or None if invalid.
    
    NOTE: Also supports legacy plain-text passwords for migration.
    """
    row = execute_query(
        "SELECT role, password FROM users WHERE username = ?",
        (username,), fetchone=True
    )
    if not row:
        return None

    stored_pw = row['password']

    # Support both hashed (new) and plain-text (legacy) passwords
    if stored_pw.startswith('pbkdf2:') or stored_pw.startswith('scrypt:'):
        # Hashed password (werkzeug)
        if check_password_hash(stored_pw, password):
            return row['role']
    else:
        # Legacy plain-text — auto-upgrade on login
        if stored_pw == password:
            new_hash = generate_password_hash(password)
            execute_query(
                "UPDATE users SET password = ? WHERE username = ?",
                (new_hash, username), commit=True
            )
            return row['role']

    return None


def add_user(username, password, role):
    """Add a new user with hashed password. Returns new user ID or None."""
    try:
        hashed = generate_password_hash(password)
        return add_record('users', {
            'username': username,
            'password': hashed,
            'role': role
        })
    except Exception as e:
        print(f"[add_user ERROR] {e}")
        return None


def change_password(username, new_password):
    """Change password for a user. Returns True on success."""
    hashed = generate_password_hash(new_password)
    result = execute_query(
        "UPDATE users SET password = ? WHERE username = ?",
        (hashed, username), commit=True
    )
    return result is not None


def get_all_users():
    """Returns all users (without password field for security)."""
    return execute_query(
        "SELECT id, username, role FROM users ORDER BY id",
        fetchall=True
    )


def delete_user(user_id):
    """Delete a user by ID."""
    return delete_record('users', user_id)


def get_user_by_username(username):
    """Fetch a single user record by username (without password)."""
    return execute_query(
        "SELECT id, username, role FROM users WHERE username = ?",
        (username,), fetchone=True
    )


# ─────────────────────────────────────────────
#  GENERIC CRUD HELPERS
# ─────────────────────────────────────────────
def get_all(table):
    """
    Fetch all rows from a table.
    Tables with 'name' column are sorted by name; others by id.
    """
    tables_with_name = ('products', 'vendors', 'buyers')
    if table in tables_with_name:
        return execute_query(f"SELECT * FROM {table} ORDER BY name", fetchall=True)
    return execute_query(f"SELECT * FROM {table} ORDER BY id", fetchall=True)


def get_by_id(table, record_id):
    """Fetch a single row by primary key."""
    return execute_query(
        f"SELECT * FROM {table} WHERE id = ?",
        (record_id,), fetchone=True
    )


def add_record(table, data_dict):
    """
    Generic INSERT.
    data_dict → { column_name: value, ... }
    Returns: new row ID (int) or None
    """
    columns  = ', '.join(data_dict.keys())
    placeholders = ', '.join(['?'] * len(data_dict))
    return execute_query(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        tuple(data_dict.values()), commit=True
    )


def update_record(table, record_id, data_dict):
    """
    Generic UPDATE by primary key.
    Returns: lastrowid (int) or None
    """
    set_clause = ', '.join([f"{k} = ?" for k in data_dict.keys()])
    return execute_query(
        f"UPDATE {table} SET {set_clause} WHERE id = ?",
        tuple(data_dict.values()) + (record_id,), commit=True
    )


def delete_record(table, record_id):
    """Generic DELETE by primary key."""
    execute_query(
        f"DELETE FROM {table} WHERE id = ?",
        (record_id,), commit=True
    )


# ─────────────────────────────────────────────
#  PRODUCTS
# ─────────────────────────────────────────────
def search_products(query):
    """Search products by name (for autocomplete / search bar)."""
    return execute_query(
        "SELECT * FROM products WHERE name LIKE ? ORDER BY name LIMIT 20",
        (f'%{query}%',), fetchall=True
    )


def get_low_stock_products(threshold=10):
    """Return all products with stock_qty <= threshold."""
    return execute_query(
        "SELECT * FROM products WHERE stock_qty <= ? ORDER BY stock_qty ASC",
        (threshold,), fetchall=True
    )


def update_product_stock(product_id, qty_to_add, new_cost_price=None):
    """
    Add stock to a product using Weighted Average Cost (WAC).
    If new_cost_price is provided, WAC is recalculated automatically.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT stock_qty, rate FROM products WHERE id = ?", (product_id,))
        row = c.fetchone()
        if not row:
            return False

        old_qty  = row['stock_qty']
        old_rate = row['rate']

        if new_cost_price and new_cost_price > 0:
            # Weighted Average Cost formula
            total_value = (old_qty * old_rate) + (qty_to_add * new_cost_price)
            new_total_qty = old_qty + qty_to_add
            wac = total_value / new_total_qty if new_total_qty > 0 else new_cost_price
            c.execute(
                "UPDATE products SET stock_qty = ?, rate = ? WHERE id = ?",
                (new_total_qty, round(wac, 2), product_id)
            )
        else:
            c.execute(
                "UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?",
                (qty_to_add, product_id)
            )

        conn.commit()
        return True
    except Exception as e:
        print(f"[update_product_stock ERROR] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  INVOICES  (Sales)
# ─────────────────────────────────────────────
def get_next_invoice_number(prefix="INV-"):
    """
    Auto-generates the next sequential invoice number.
    Example: INV-0001, INV-0002, ...
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT invoice_no FROM invoices WHERE invoice_no LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{prefix}%",)
    )
    last = c.fetchone()
    conn.close()
    if last:
        try:
            last_num = int(last['invoice_no'].split(prefix)[-1])
            return f"{prefix}{last_num + 1:04d}"
        except (ValueError, IndexError):
            pass
    return f"{prefix}0001"


def save_invoice(inv_data, items, company_state):
    """
    Saves a complete invoice with line items.
    Automatically:
      - Determines CGST/SGST vs IGST based on buyer's state vs company state
      - Deducts stock for each item
      - Returns the new invoice ID or None on failure

    Parameters:
      inv_data      : dict with invoice header fields
      items         : list of dicts (each line item)
      company_state : string, company's registered state (from settings)
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # ── Determine GST type (Intra-state vs Inter-state) ──
        c.execute("SELECT state FROM buyers WHERE id = ?", (inv_data['buyer_id'],))
        row = c.fetchone()
        buyer_state = row['state'] if row and row['state'] else company_state
        is_interstate = (buyer_state.strip().lower() != company_state.strip().lower())

        total_gst = inv_data.get('total_gst', 0)
        if total_gst == 0:
            # Fallback: sum up individual GST components
            total_gst = (
                inv_data.get('total_cgst', 0) +
                inv_data.get('total_sgst', 0) +
                inv_data.get('total_igst', 0)
            )

        igst = total_gst       if is_interstate else 0
        cgst = 0               if is_interstate else round(total_gst / 2, 2)
        sgst = 0               if is_interstate else round(total_gst / 2, 2)

        # ── Insert Invoice Header ──────────────────────────────
        c.execute('''
            INSERT INTO invoices
              (invoice_no, invoice_date, buyer_id, payment_mode, order_ref,
               dispatch_info, subtotal, total_discount, taxable_value,
               total_gst, total_cgst, total_sgst, total_igst,
               freight, round_off, grand_total, paid_amount, previous_balance)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            inv_data['invoice_no'],
            inv_data['invoice_date'],
            inv_data['buyer_id'],
            inv_data.get('payment_mode', 'Cash'),
            inv_data.get('order_ref', ''),
            inv_data.get('dispatch_info', ''),
            inv_data.get('subtotal', 0),
            inv_data.get('total_discount', 0),
            inv_data.get('taxable_value', 0),
            total_gst, cgst, sgst, igst,
            inv_data.get('freight', 0),
            inv_data.get('round_off', 0),
            inv_data['grand_total'],
            inv_data.get('paid_amount', 0),
            inv_data.get('previous_balance', 0)
        ))

        invoice_id = c.lastrowid

        # ── Insert Line Items & Deduct Stock ──────────────────
        for item in items:
            c.execute('''
                INSERT INTO invoice_items
                  (invoice_id, product_id, description, hsn,
                   gst_rate, quantity, rate, discount_percent, amount)
                VALUES (?,?,?,?,?,?,?,?,?)
            ''', (
                invoice_id,
                item['product_id'],
                item.get('description', ''),
                item.get('hsn', ''),
                item.get('gst_rate', 0),
                item['quantity'],
                item['rate'],
                item.get('discount_percent', 0),
                item['amount']
            ))
            # Deduct from inventory only for known products
            if item.get('product_id') and int(item['product_id']) > 0:
                c.execute(
                    "UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                    (item['quantity'], int(item['product_id']))
                )

        conn.commit()
        return invoice_id

    except Exception as e:
        print(f"[save_invoice ERROR] {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_full_invoice_details(invoice_id):
    """
    Returns (invoice_dict, [items_list]) for a given invoice ID.
    Joins buyer info into the invoice dict.
    """
    conn = get_db_connection()
    c = conn.cursor()

    inv = c.execute('''
        SELECT
            i.*,
            b.name    AS buyer_name,
            b.gstin   AS buyer_gstin,
            b.address AS buyer_address,
            b.phone   AS buyer_phone,
            b.state   AS buyer_state
        FROM invoices i
        JOIN buyers b ON i.buyer_id = b.id
        WHERE i.id = ?
    ''', (invoice_id,)).fetchone()

    if not inv:
        conn.close()
        return None, []

    items = c.execute(
        "SELECT * FROM invoice_items WHERE invoice_id = ?",
        (invoice_id,)
    ).fetchall()

    conn.close()
    return row_to_dict(inv), rows_to_list(items)


def get_invoices_by_filter(start_date, end_date, buyer_id=None, search_text=None):
    """
    Fetch invoices within a date range.
    Optionally filter by buyer or invoice number text search.
    Returns list of dicts for easy JSON serialization.
    """
    query = '''
        SELECT
            i.id, i.invoice_no, i.invoice_date,
            b.name       AS buyer_name,
            b.gstin      AS buyer_gstin,
            i.taxable_value, i.total_gst, i.grand_total,
            i.payment_mode
        FROM invoices i
        JOIN buyers b ON i.buyer_id = b.id
        WHERE i.invoice_date BETWEEN ? AND ?
    '''
    params = [start_date, end_date]

    if buyer_id:
        query  += " AND i.buyer_id = ?"
        params.append(buyer_id)

    if search_text:
        query  += " AND (i.invoice_no LIKE ? OR b.name LIKE ?)"
        params += [f'%{search_text}%', f'%{search_text}%']

    query += " ORDER BY i.invoice_date DESC, i.id DESC"
    return execute_query(query, params, fetchall=True) or []


def cancel_invoice(invoice_id):
    """
    Cancels an invoice:
      1. Restores stock for all line items
      2. Prefixes invoice_no with [CANCELLED]
      3. Zeroes out all financial totals
    Returns True on success, False on failure.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Check it's not already cancelled
        row = c.execute("SELECT invoice_no FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            return False
        if row['invoice_no'].startswith('[CANCELLED]'):
            return False   # Already cancelled

        # Restore stock
        items = c.execute(
            "SELECT product_id, quantity FROM invoice_items WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchall()
        for item in items:
            c.execute(
                "UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?",
                (item['quantity'], item['product_id'])
            )

        # Mark as cancelled
        c.execute('''
            UPDATE invoices SET
                grand_total   = 0,
                taxable_value = 0,
                total_gst     = 0,
                total_cgst    = 0,
                total_sgst    = 0,
                total_igst    = 0,
                invoice_no    = '[CANCELLED] ' || invoice_no
            WHERE id = ?
        ''', (invoice_id,))

        conn.commit()
        return True
    except Exception as e:
        print(f"[cancel_invoice ERROR] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  CUSTOMER PAYMENTS & LEDGER
# ─────────────────────────────────────────────
def add_customer_payment(payment_data):
    """
    Record a payment received from a customer.
    payment_data: { buyer_id, payment_date, amount, payment_mode, notes }
    """
    return add_record('customer_payments', payment_data)


def get_buyer_ledger(buyer_id, start_date=None, end_date=None):
    """
    Generates a full ledger for a buyer showing:
      - Opening Balance
      - Invoice debits
      - Payment credits
      - Running balance after each transaction
    
    Returns: (ledger_list, closing_balance)
    """
    conn = get_db_connection()
    c = conn.cursor()

    # Opening balance from buyer master
    c.execute("SELECT opening_balance FROM buyers WHERE id = ?", (buyer_id,))
    row = c.fetchone()
    opening_balance = row['opening_balance'] if row else 0.0

    # Build invoice query
    q_inv = """
        SELECT invoice_date AS date, invoice_no AS ref,
               'Invoice' AS type, grand_total AS debit, 0 AS credit, '' AS payment_mode
        FROM invoices
        WHERE buyer_id = ? AND invoice_no NOT LIKE '[CANCELLED]%'
    """
    p_inv = [buyer_id]

    # Build payment query
    q_pay = """
        SELECT payment_date AS date, 'Payment' AS ref,
               'Payment' AS type, 0 AS debit, amount AS credit, payment_mode
        FROM customer_payments
        WHERE buyer_id = ?
    """
    p_pay = [buyer_id]

    if start_date and end_date:
        q_inv += " AND invoice_date BETWEEN ? AND ?"
        p_inv += [start_date, end_date]
        q_pay += " AND payment_date BETWEEN ? AND ?"
        p_pay += [start_date, end_date]

        # Adjust opening balance: add pre-period invoices, subtract pre-period payments
        c.execute("""
            SELECT SUM(grand_total) FROM invoices
            WHERE buyer_id = ? AND invoice_date < ? AND invoice_no NOT LIKE '[CANCELLED]%'
        """, (buyer_id, start_date))
        row = c.fetchone()
        prev_debit = row[0] if row and row[0] else 0.0

        c.execute("""
            SELECT SUM(amount) FROM customer_payments
            WHERE buyer_id = ? AND payment_date < ?
        """, (buyer_id, start_date))
        row = c.fetchone()
        prev_credit = row[0] if row and row[0] else 0.0

        opening_balance += prev_debit - prev_credit

    c.execute(q_inv, tuple(p_inv))
    invoices = rows_to_list(c.fetchall())

    c.execute(q_pay, tuple(p_pay))
    payments = rows_to_list(c.fetchall())

    conn.close()

    # Merge, annotate payment_mode into ref, sort by date
    all_entries = invoices + payments
    for entry in all_entries:
        if entry.get('payment_mode') and entry['type'] == 'Payment':
            entry['ref'] += f" ({entry['payment_mode']})"
    all_entries.sort(key=lambda x: x['date'])

    # Build running balance
    ledger = [{
        'date'    : start_date or '-',
        'ref'     : 'Opening Balance',
        'type'    : 'Opening',
        'debit'   : 0,
        'credit'  : 0,
        'balance' : round(opening_balance, 2)
    }]
    balance = opening_balance
    for entry in all_entries:
        balance += entry['debit'] - entry['credit']
        entry['balance'] = round(balance, 2)
        ledger.append(entry)

    return ledger, round(balance, 2)


def get_buyer_current_balance(buyer_id):
    """Shortcut to get just the closing balance for a buyer."""
    _, balance = get_buyer_ledger(buyer_id)
    return balance


def get_all_buyer_balances():
    """
    Returns all buyers with their current outstanding balance.
    Useful for receivables dashboard / summary.
    """
    buyers = get_all('buyers')
    result = []
    for b in buyers:
        bal = get_buyer_current_balance(b['id'])
        result.append({
            'id'      : b['id'],
            'name'    : b['name'],
            'phone'   : b.get('phone', ''),
            'balance' : bal
        })
    return result


# ─────────────────────────────────────────────
#  PURCHASES & VENDOR PAYMENTS
# ─────────────────────────────────────────────
def get_all_purchases_with_vendor():
    """
    All purchase bills joined with vendor name.
    Ordered by most recent first.
    """
    return execute_query('''
        SELECT
            p.id, v.name AS vendor_name,
            p.bill_no, p.purchase_date,
            p.total_amount, p.amount_paid, p.payment_status, p.notes
        FROM purchases p
        JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.purchase_date DESC, p.id DESC
    ''', fetchall=True) or []


def get_purchase_details(purchase_id):
    """Single purchase with vendor name."""
    return execute_query('''
        SELECT p.*, v.name AS vendor_name
        FROM purchases p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE p.id = ?
    ''', (purchase_id,), fetchone=True)


def get_purchase_payments(purchase_id):
    """All payment transactions for a specific purchase bill."""
    return execute_query(
        "SELECT * FROM purchase_payments WHERE purchase_id = ? ORDER BY payment_date",
        (purchase_id,), fetchall=True
    ) or []


def add_purchase_payment(purchase_id, payment_data):
    """
    Record a payment against a purchase bill.
    Automatically recalculates amount_paid and updates payment_status:
      'Unpaid' → 'Partial' → 'Paid'
    
    payment_data: { payment_date, amount, payment_mode, reference_no }
    Returns True on success, False on failure.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Insert payment record
        c.execute('''
            INSERT INTO purchase_payments
              (purchase_id, payment_date, amount, payment_mode, reference_no)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            purchase_id,
            payment_data['payment_date'],
            payment_data['amount'],
            payment_data.get('payment_mode', 'Cash'),
            payment_data.get('reference_no', '')
        ))

        # Recalculate total paid
        row = c.execute(
            "SELECT SUM(amount) FROM purchase_payments WHERE purchase_id = ?",
            (purchase_id,)
        ).fetchone()
        total_paid = row[0] if row and row[0] else 0.0

        # Get original bill total
        row = c.execute(
            "SELECT total_amount FROM purchases WHERE id = ?",
            (purchase_id,)
        ).fetchone()
        total_amount = row['total_amount'] if row else 0.0

        # Determine status
        if total_amount > 0 and total_paid >= total_amount:
            status = 'Paid'
        elif total_paid > 0:
            status = 'Partial'
        else:
            status = 'Unpaid'

        c.execute(
            "UPDATE purchases SET amount_paid = ?, payment_status = ? WHERE id = ?",
            (round(total_paid, 2), status, purchase_id)
        )
        conn.commit()
        return True

    except Exception as e:
        print(f"[add_purchase_payment ERROR] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  DASHBOARD KPIs
# ─────────────────────────────────────────────
def get_dashboard_kpi():
    """
    Returns 4 key metrics for the dashboard:
      1. today_sales     — Total sales amount for today
      2. total_due       — Net receivables (all invoices - all receipts + opening balances)
      3. total_profit    — Estimated profit (selling rate - cost rate) × qty
      4. low_stock_count — Number of products with stock ≤ 10

    Returns: (today_sales, total_due, total_profit, low_stock_count)
    """
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    # 1. Today's Sales
    c.execute("""
        SELECT SUM(grand_total) FROM invoices
        WHERE invoice_date = ? AND invoice_no NOT LIKE '[CANCELLED]%'
    """, (today,))
    row = c.fetchone()
    today_sales = row[0] if row and row[0] else 0.0

    # 2. Total Receivables
    c.execute("SELECT SUM(grand_total) FROM invoices WHERE invoice_no NOT LIKE '[CANCELLED]%'")
    row = c.fetchone()
    total_invoiced = row[0] if row and row[0] else 0.0

    c.execute("SELECT SUM(amount) FROM customer_payments")
    row = c.fetchone()
    total_received = row[0] if row and row[0] else 0.0

    c.execute("SELECT SUM(opening_balance) FROM buyers")
    row = c.fetchone()
    total_opening = row[0] if row and row[0] else 0.0

    total_due = (total_invoiced + total_opening) - total_received

    # 3. Estimated Profit
    c.execute("""
        SELECT SUM((ii.rate - p.rate) * ii.quantity)
        FROM invoice_items ii
        JOIN products p  ON ii.product_id = p.id
        JOIN invoices i  ON ii.invoice_id = i.id
        WHERE i.invoice_no NOT LIKE '[CANCELLED]%'
    """)
    row = c.fetchone()
    total_profit = row[0] if row and row[0] else 0.0

    # 4. Low Stock Count
    c.execute("SELECT COUNT(*) FROM products WHERE stock_qty <= 10")
    row = c.fetchone()
    low_stock = row[0] if row and row[0] else 0

    conn.close()
    return (
        round(today_sales, 2),
        round(total_due, 2),
        round(total_profit, 2),
        int(low_stock)
    )


# ─────────────────────────────────────────────
#  DASHBOARD CHART DATA
# ─────────────────────────────────────────────
def get_graph_data(mode='Weekly'):
    """
    Returns (labels, values) for the sales trend chart.
    mode: 'Weekly' → last 7 days
          'Monthly' → last 6 months
          'Yearly'  → last 5 years
    
    Both lists are JSON-serializable (strings + floats).
    """
    conn = get_db_connection()
    c = conn.cursor()
    labels = []
    values = []

    if mode == 'Weekly':
        for i in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            c.execute("""
                SELECT SUM(grand_total) FROM invoices
                WHERE invoice_date = ? AND invoice_no NOT LIKE '[CANCELLED]%'
            """, (day,))
            row = c.fetchone()
            labels.append(day)
            values.append(round(row[0] if row and row[0] else 0.0, 2))

    elif mode == 'Monthly':
        for i in range(5, -1, -1):
            date_calc  = datetime.now().replace(day=1) - timedelta(days=i * 30)
            month_str  = date_calc.strftime('%Y-%m')
            c.execute("""
                SELECT SUM(grand_total) FROM invoices
                WHERE strftime('%Y-%m', invoice_date) = ?
                  AND invoice_no NOT LIKE '[CANCELLED]%'
            """, (month_str,))
            row = c.fetchone()
            labels.append(date_calc.strftime('%b %Y'))
            values.append(round(row[0] if row and row[0] else 0.0, 2))

    elif mode == 'Yearly':
        current_year = datetime.now().year
        for i in range(4, -1, -1):
            year_str = str(current_year - i)
            c.execute("""
                SELECT SUM(grand_total) FROM invoices
                WHERE strftime('%Y', invoice_date) = ?
                  AND invoice_no NOT LIKE '[CANCELLED]%'
            """, (year_str,))
            row = c.fetchone()
            labels.append(year_str)
            values.append(round(row[0] if row and row[0] else 0.0, 2))

    conn.close()
    return labels, values


# ─────────────────────────────────────────────
#  REPORTING HELPERS
# ─────────────────────────────────────────────
def get_sales_summary_report(start_date, end_date):
    """
    Returns total sales, total tax, and grand total for a date range.
    Used for generating summary PDF reports.
    """
    return execute_query('''
        SELECT
            COUNT(*)              AS total_invoices,
            SUM(taxable_value)    AS total_taxable,
            SUM(total_gst)        AS total_gst,
            SUM(grand_total)      AS total_grand
        FROM invoices
        WHERE invoice_date BETWEEN ? AND ?
          AND invoice_no NOT LIKE '[CANCELLED]%'
    ''', (start_date, end_date), fetchone=True)


def get_item_wise_report(start_date, end_date):
    """
    Returns product-wise sales totals for a date range.
    Useful for item-wise sales report PDF.
    """
    return execute_query('''
        SELECT
            p.name       AS product_name,
            p.hsn,
            SUM(ii.quantity)   AS total_qty,
            AVG(ii.rate)       AS avg_rate,
            SUM(ii.amount)     AS total_amount
        FROM invoice_items ii
        JOIN products p  ON ii.product_id = p.id
        JOIN invoices i  ON ii.invoice_id = i.id
        WHERE i.invoice_date BETWEEN ? AND ?
          AND i.invoice_no NOT LIKE '[CANCELLED]%'
        GROUP BY p.id, p.name, p.hsn
        ORDER BY total_amount DESC
    ''', (start_date, end_date), fetchall=True) or []


# ─────────────────────────────────────────────
#  ENTRY POINT (for direct testing)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    create_tables()
    print("=" * 50)
    print("  Database initialized and ready for Flask!")
    print("  Default login → admin / admin123")
    print("=" * 50)

    # Quick smoke test
    kpi = get_dashboard_kpi()
    print(f"\nDashboard KPI Test:")
    print(f"  Today's Sales : ₹{kpi[0]:,.2f}")
    print(f"  Total Due     : ₹{kpi[1]:,.2f}")
    print(f"  Est. Profit   : ₹{kpi[2]:,.2f}")
    print(f"  Low Stock     : {kpi[3]} items")
