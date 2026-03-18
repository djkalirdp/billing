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
        """CREATE TABLE IF NOT EXISTS product_variations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variation_name TEXT NOT NULL,
            selling_price REAL DEFAULT 0,
            wholesale_price REAL DEFAULT 0,
            stock_qty REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id))""",
        "ALTER TABLE invoice_items ADD COLUMN variation_id INTEGER DEFAULT NULL",
        "ALTER TABLE invoice_items ADD COLUMN batch_no TEXT DEFAULT ''",
        # Purchase GST columns (for existing DBs)
        "ALTER TABLE purchases ADD COLUMN taxable_amount REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN gst_rate REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN cgst_amount REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN sgst_amount REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN igst_amount REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN total_tax REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN place_of_supply TEXT DEFAULT ''",
        "ALTER TABLE purchases ADD COLUMN reverse_charge INTEGER DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN purchase_type TEXT DEFAULT 'Resale'",  # Resale or Raw Material
        # purchase_items columns (for existing DBs that had old schema with 'amount' only)
        "ALTER TABLE purchase_items ADD COLUMN taxable_amount REAL DEFAULT 0",
        "ALTER TABLE purchase_items ADD COLUMN cgst_amount REAL DEFAULT 0",
        "ALTER TABLE purchase_items ADD COLUMN sgst_amount REAL DEFAULT 0",
        "ALTER TABLE purchase_items ADD COLUMN igst_amount REAL DEFAULT 0",
        "ALTER TABLE purchase_items ADD COLUMN total_amount REAL DEFAULT 0",
        "ALTER TABLE purchase_items ADD COLUMN gst_rate REAL DEFAULT 0",
        # vendor_payments table (for existing DBs without vendor ledger)
        """CREATE TABLE IF NOT EXISTS vendor_payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id    INTEGER NOT NULL,
            payment_date TEXT,
            amount       REAL,
            payment_mode TEXT,
            reference_no TEXT,
            notes        TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id))""",
    ]:
        try:
            c.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # already exists

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

    # ── Product Variations ───────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS product_variations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id      INTEGER NOT NULL,
            variation_name  TEXT    NOT NULL,
            selling_price   REAL    DEFAULT 0,
            wholesale_price REAL    DEFAULT 0,
            stock_qty       REAL    DEFAULT 0,
            rate            REAL    DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # ── Purchase Bills ────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id       INTEGER NOT NULL,
            bill_no         TEXT,
            purchase_date   TEXT,
            taxable_amount  REAL DEFAULT 0,
            gst_rate        REAL DEFAULT 0,
            cgst_amount     REAL DEFAULT 0,
            sgst_amount     REAL DEFAULT 0,
            igst_amount     REAL DEFAULT 0,
            total_tax       REAL DEFAULT 0,
            total_amount    REAL DEFAULT 0,
            amount_paid     REAL DEFAULT 0,
            payment_status  TEXT DEFAULT 'Unpaid',
            place_of_supply TEXT DEFAULT '',
            reverse_charge  INTEGER DEFAULT 0,
            notes           TEXT,
            purchase_type   TEXT DEFAULT 'Resale',
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # ── Purchase Items (with Batch & Expiry tracking) ──
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS purchase_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id     INTEGER NOT NULL,
            product_id      INTEGER,
            description     TEXT,
            batch_no        TEXT,
            expiry_date     TEXT,
            quantity        REAL DEFAULT 0,
            rate            REAL DEFAULT 0,
            gst_rate        REAL DEFAULT 0,
            taxable_amount  REAL DEFAULT 0,
            cgst_amount     REAL DEFAULT 0,
            sgst_amount     REAL DEFAULT 0,
            igst_amount     REAL DEFAULT 0,
            total_amount    REAL DEFAULT 0,
            FOREIGN KEY (purchase_id) REFERENCES purchases(id),
            FOREIGN KEY (product_id)  REFERENCES products(id)
        )
    ''')

    # ── Batch Tracking (which batch → which customer invoice) ──
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS batch_tracking (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id      INTEGER NOT NULL,
            batch_no        TEXT NOT NULL,
            expiry_date     TEXT,
            purchase_id     INTEGER,
            purchase_item_id INTEGER,
            invoice_id      INTEGER,
            invoice_item_id INTEGER,
            buyer_id        INTEGER,
            qty_in          REAL DEFAULT 0,
            qty_out         REAL DEFAULT 0,
            tracking_date   TEXT,
            notes           TEXT,
            FOREIGN KEY (product_id)  REFERENCES products(id),
            FOREIGN KEY (purchase_id) REFERENCES purchases(id),
            FOREIGN KEY (invoice_id)  REFERENCES invoices(id),
            FOREIGN KEY (buyer_id)    REFERENCES buyers(id)
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

    # ── Vendor Payments (Ledger) ──────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id    INTEGER NOT NULL,
            payment_date TEXT,
            amount       REAL,
            payment_mode TEXT,
            reference_no TEXT,
            notes        TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
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

    
    # ── Proforma Invoices / Sales Quotations ──────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS proforma_invoices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            quotation_no    TEXT    UNIQUE NOT NULL,
            quotation_date  TEXT    NOT NULL,
            valid_until     TEXT,
            buyer_id        INTEGER,
            buyer_name      TEXT,
            buyer_address   TEXT,
            buyer_gstin     TEXT,
            buyer_state     TEXT,
            buyer_phone     TEXT,
            payment_mode    TEXT    DEFAULT 'Advance',
            order_ref       TEXT,
            subtotal        REAL    DEFAULT 0,
            total_discount  REAL    DEFAULT 0,
            taxable_value   REAL    DEFAULT 0,
            total_gst       REAL    DEFAULT 0,
            total_cgst      REAL    DEFAULT 0,
            total_sgst      REAL    DEFAULT 0,
            total_igst      REAL    DEFAULT 0,
            freight         REAL    DEFAULT 0,
            round_off       REAL    DEFAULT 0,
            grand_total     REAL    DEFAULT 0,
            status          TEXT    DEFAULT 'Active',
            notes           TEXT,
            FOREIGN KEY (buyer_id) REFERENCES buyers(id)
        )
    ''')

    # ── Proforma Invoice Items ─────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS proforma_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            proforma_id     INTEGER NOT NULL,
            product_id      INTEGER,
            description     TEXT,
            hsn             TEXT,
            gst_rate        REAL    DEFAULT 0,
            quantity        REAL    DEFAULT 0,
            unit            TEXT,
            rate            REAL    DEFAULT 0,
            discount_percent REAL   DEFAULT 0,
            amount          REAL    DEFAULT 0,
            FOREIGN KEY (proforma_id) REFERENCES proforma_invoices(id)
        )
    ''')

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
    """
    Search products AND their variations by name.
    Returns flat list — variations appear as separate rows with parent HSN/GST.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    pat  = f'%{query}%'
    results = []

    try:
        # Parent products matching query
        rows = c.execute(
            "SELECT * FROM products WHERE name LIKE ? ORDER BY name LIMIT 15",
            (pat,)
        ).fetchall()
        for r in rows:
            p = dict(r)
            p['display_name']   = p['name']
            p['variation_id']   = None
            p['variation_name'] = None
            results.append(p)

        # Variations matching query (by variation_name OR parent name)
        try:
            var_rows = c.execute("""
                SELECT pv.id         AS var_id,
                       pv.product_id,
                       pv.variation_name,
                       pv.selling_price,
                       pv.wholesale_price,
                       pv.stock_qty,
                       pv.rate       AS var_rate,
                       p.name        AS parent_name,
                       p.hsn,
                       p.gst_rate,
                       p.unit
                FROM product_variations pv
                JOIN products p ON pv.product_id = p.id
                WHERE pv.variation_name LIKE ? OR p.name LIKE ?
                ORDER BY p.name, pv.variation_name
                LIMIT 20
            """, (pat, pat)).fetchall()

            for v in var_rows:
                vd = dict(v)
                results.append({
                    'id'              : vd['product_id'],
                    'name'            : vd['parent_name'],
                    'display_name'    : f"{vd['parent_name']} — {vd['variation_name']}",
                    'hsn'             : vd['hsn'],
                    'gst_rate'        : vd['gst_rate'],
                    'unit'            : vd['unit'],
                    'selling_price'   : vd['selling_price'],
                    'wholesale_price' : vd['wholesale_price'],
                    'stock_qty'       : vd['stock_qty'],
                    'rate'            : vd['var_rate'],
                    'variation_id'    : vd['var_id'],
                    'variation_name'  : vd['variation_name'],
                })
        except Exception:
            # product_variations table may not exist yet — just return parents
            pass

    finally:
        conn.close()

    # Deduplicate — parent product + its variations both appear separately
    seen_keys = set()
    deduped   = []
    for item in results:
        key = (item['id'], item.get('variation_id'))
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(item)
    return deduped[:20]


# ── Variation CRUD ─────────────────────────────────────────────────

def get_variations(product_id):
    """Return all variations for a product."""
    return execute_query(
        "SELECT * FROM product_variations WHERE product_id = ? ORDER BY variation_name",
        (product_id,), fetchall=True
    ) or []


def add_variation(product_id, name, selling_price, wholesale_price, stock_qty, cost_rate):
    """Add a new variation."""
    return add_record('product_variations', {
        'product_id'     : product_id,
        'variation_name' : name.strip(),
        'selling_price'  : float(selling_price  or 0),
        'wholesale_price': float(wholesale_price or 0),
        'stock_qty'      : float(stock_qty       or 0),
        'rate'           : float(cost_rate        or 0),
    })


def update_variation(variation_id, name, selling_price, wholesale_price, stock_qty, cost_rate):
    """Update an existing variation."""
    return update_record('product_variations', variation_id, {
        'variation_name' : name.strip(),
        'selling_price'  : float(selling_price  or 0),
        'wholesale_price': float(wholesale_price or 0),
        'stock_qty'      : float(stock_qty       or 0),
        'rate'           : float(cost_rate        or 0),
    })


def delete_variation(variation_id):
    """Delete a variation."""
    return delete_record('product_variations', variation_id)


def deduct_variation_stock(variation_id, qty):
    """Deduct stock from a variation."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE product_variations SET stock_qty = stock_qty - ? WHERE id = ?",
            (qty, variation_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[deduct_variation_stock ERROR] {e}")
        return False
    finally:
        conn.close()


def restore_variation_stock(variation_id, qty):
    """Restore stock to a variation (on invoice cancel)."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE product_variations SET stock_qty = stock_qty + ? WHERE id = ?",
            (qty, variation_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[restore_variation_stock ERROR] {e}")
        return False
    finally:
        conn.close()


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
                   gst_rate, quantity, rate, discount_percent, amount, variation_id, batch_no)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                invoice_id,
                item['product_id'],
                item.get('description', ''),
                item.get('hsn', ''),
                item.get('gst_rate', 0),
                item['quantity'],
                item['rate'],
                item.get('discount_percent', 0),
                item['amount'],
                item.get('variation_id') or None,
                item.get('batch_no', '') or ''
            ))
            item_id = c.lastrowid

            # ── Batch Tracking: record OUT movement for this sale ──
            batch_no = item.get('batch_no', '').strip()
            pid_val = item.get('product_id')
            qty_val = item['quantity']
            if batch_no and pid_val and int(pid_val) > 0:
                from datetime import date as _date
                c.execute("""
                    INSERT INTO batch_tracking
                      (product_id, batch_no, invoice_id, invoice_item_id,
                       buyer_id, qty_in, qty_out, tracking_date, notes)
                    VALUES (?,?,?,?,?,0,?,?,?)
                """, (
                    int(pid_val),
                    batch_no,
                    invoice_id,
                    item_id,
                    inv_data.get('buyer_id'),
                    qty_val,
                    inv_data.get('invoice_date', _date.today().isoformat()),
                    f"Sale OUT — Invoice {inv_data.get('invoice_no','')}",
                ))

            # Deduct stock — from variation if set, else from parent product
            vid = item.get('variation_id')
            pid = item.get('product_id')
            qty = item['quantity']
            if vid and int(vid) > 0:
                c.execute(
                    "UPDATE product_variations SET stock_qty = stock_qty - ? WHERE id = ?",
                    (qty, int(vid))
                )
            elif pid and int(pid) > 0:
                c.execute(
                    "UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                    (qty, int(pid))
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

        # Restore stock — variations first, then parent products
        items = c.execute(
            "SELECT product_id, quantity, variation_id FROM invoice_items WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchall()
        for item in items:
            if item['variation_id']:
                c.execute(
                    "UPDATE product_variations SET stock_qty = stock_qty + ? WHERE id = ?",
                    (item['quantity'], item['variation_id'])
                )
            elif item['product_id']:
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




def delete_customer_payment(payment_id):
    """Delete a customer payment entry."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM customer_payments WHERE id = ?", (payment_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"[delete_customer_payment ERROR] {e}")
        return False
    finally:
        conn.close()


def update_customer_payment(payment_id, data):
    """Update a customer payment entry."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE customer_payments
               SET payment_date = ?, amount = ?, payment_mode = ?, notes = ?
             WHERE id = ?
        """, (
            data.get('payment_date', ''),
            float(data.get('amount', 0)),
            data.get('payment_mode', 'Cash'),
            data.get('notes', ''),
            payment_id,
        ))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"[update_customer_payment ERROR] {e}")
        return False
    finally:
        conn.close()


def get_customer_payment(payment_id):
    """Fetch a single customer payment row."""
    return execute_query(
        "SELECT * FROM customer_payments WHERE id = ?",
        (payment_id,), fetchone=True
    )

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
        SELECT id, invoice_date AS date, invoice_no AS ref,
               'Invoice' AS type, grand_total AS debit, 0 AS credit, '' AS payment_mode
        FROM invoices
        WHERE buyer_id = ? AND invoice_no NOT LIKE '[CANCELLED]%'
    """
    p_inv = [buyer_id]

    # Build payment query
    q_pay = """
        SELECT id, payment_date AS date, 'Payment' AS ref,
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
#  VENDOR LEDGER
# ─────────────────────────────────────────────

def add_vendor_payment(payment_data):
    """
    Record a payment made to a vendor (independent of any purchase bill).
    payment_data: { vendor_id, payment_date, amount, payment_mode, reference_no, notes }
    """
    return add_record('vendor_payments', payment_data)


def delete_vendor_payment(payment_id):
    """Delete a vendor payment entry."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM vendor_payments WHERE id = ?", (payment_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"[delete_vendor_payment ERROR] {e}")
        return False
    finally:
        conn.close()


def update_vendor_payment(payment_id, data):
    """Update a vendor payment entry."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE vendor_payments
               SET payment_date = ?, amount = ?, payment_mode = ?,
                   reference_no = ?, notes = ?
             WHERE id = ?
        """, (
            data.get('payment_date', ''),
            float(data.get('amount', 0)),
            data.get('payment_mode', 'Cash'),
            data.get('reference_no', ''),
            data.get('notes', ''),
            payment_id,
        ))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"[update_vendor_payment ERROR] {e}")
        return False
    finally:
        conn.close()


def get_vendor_payment(payment_id):
    """Fetch a single vendor payment row."""
    return execute_query(
        "SELECT * FROM vendor_payments WHERE id = ?",
        (payment_id,), fetchone=True
    )


def get_vendor_ledger(vendor_id, start_date=None, end_date=None):
    """
    Generates a full ledger for a vendor showing:
      - Purchase debits  (what we owe them)
      - Payment credits  (what we paid them)
        Sources of payments:
          1. purchase_payments — payments made directly against a purchase bill
          2. vendor_payments   — standalone payments added from vendor ledger page
      - Running balance after each transaction

    Balance > 0  = we owe money to vendor
    Balance <= 0 = we have overpaid or no dues

    Returns: (ledger_list, closing_balance)
    """
    conn = get_db_connection()
    c = conn.cursor()

    # ── Purchases query (debit = what we owe) ────────────────────
    q_pur = """
        SELECT id, purchase_date AS date, bill_no AS ref,
               'Purchase' AS type, total_amount AS debit, 0 AS credit, '' AS payment_mode
        FROM purchases
        WHERE vendor_id = ?
    """
    p_pur = [vendor_id]

    # ── Purchase payments (credit = paid against a specific bill) ─
    # Join with purchases to filter by vendor_id
    q_pp = """
        SELECT pp.id, pp.payment_date AS date,
               'Payment' AS ref,
               'Payment' AS type,
               0 AS debit, pp.amount AS credit,
               pp.payment_mode
        FROM purchase_payments pp
        JOIN purchases p ON pp.purchase_id = p.id
        WHERE p.vendor_id = ?
    """
    p_pp = [vendor_id]

    # ── Standalone vendor payments (credit = direct payment) ──────
    q_vp = """
        SELECT id, payment_date AS date, 'Payment' AS ref,
               'Payment' AS type, 0 AS debit, amount AS credit, payment_mode
        FROM vendor_payments
        WHERE vendor_id = ?
    """
    p_vp = [vendor_id]

    if start_date and end_date:
        q_pur += " AND purchase_date BETWEEN ? AND ?"
        p_pur += [start_date, end_date]
        q_pp  += " AND pp.payment_date BETWEEN ? AND ?"
        p_pp  += [start_date, end_date]
        q_vp  += " AND payment_date BETWEEN ? AND ?"
        p_vp  += [start_date, end_date]

        # Opening balance = purchases before period - payments before period
        c.execute("""
            SELECT COALESCE(SUM(total_amount), 0) FROM purchases
            WHERE vendor_id = ? AND purchase_date < ?
        """, (vendor_id, start_date))
        prev_debit = c.fetchone()[0] or 0.0

        # Purchase payments before period
        c.execute("""
            SELECT COALESCE(SUM(pp.amount), 0)
            FROM purchase_payments pp
            JOIN purchases p ON pp.purchase_id = p.id
            WHERE p.vendor_id = ? AND pp.payment_date < ?
        """, (vendor_id, start_date))
        prev_pp = c.fetchone()[0] or 0.0

        # Standalone vendor payments before period
        c.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM vendor_payments
            WHERE vendor_id = ? AND payment_date < ?
        """, (vendor_id, start_date))
        prev_vp = c.fetchone()[0] or 0.0

        opening_balance = prev_debit - prev_pp - prev_vp
    else:
        opening_balance = 0.0

    c.execute(q_pur, tuple(p_pur))
    purchases = rows_to_list(c.fetchall())

    c.execute(q_pp, tuple(p_pp))
    purchase_payments = rows_to_list(c.fetchall())

    c.execute(q_vp, tuple(p_vp))
    vendor_payments = rows_to_list(c.fetchall())

    conn.close()

    # Annotate purchase ref
    for entry in purchases:
        entry['ref'] = f"Bill No: {entry['ref']}" if entry.get('ref') else 'Purchase'

    # Annotate purchase_payments ref — show which bill it was against
    for entry in purchase_payments:
        mode = entry.get('payment_mode', '')
        entry['ref'] = f"Payment against Bill ({mode})" if mode else "Payment against Bill"

    # Annotate standalone vendor payments
    for entry in vendor_payments:
        mode = entry.get('payment_mode', '')
        entry['ref'] = f"Payment ({mode})" if mode else "Payment"

    # Merge all and sort by date
    all_entries = purchases + purchase_payments + vendor_payments
    all_entries.sort(key=lambda x: (x['date'] or ''))

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


def get_vendor_current_balance(vendor_id):
    """
    Fast calculation of vendor outstanding balance:
      Total purchases - purchase_payments - vendor_payments
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Total purchase amount
        c.execute("SELECT COALESCE(SUM(total_amount),0) FROM purchases WHERE vendor_id=?", (vendor_id,))
        total_purchases = c.fetchone()[0] or 0.0

        # Payments made against purchase bills
        c.execute("""
            SELECT COALESCE(SUM(pp.amount),0)
            FROM purchase_payments pp
            JOIN purchases p ON pp.purchase_id = p.id
            WHERE p.vendor_id = ?
        """, (vendor_id,))
        purchase_payments = c.fetchone()[0] or 0.0

        # Standalone vendor payments
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_payments WHERE vendor_id=?", (vendor_id,))
        vendor_payments = c.fetchone()[0] or 0.0

        return round(total_purchases - purchase_payments - vendor_payments, 2)
    except Exception as e:
        print(f"[get_vendor_current_balance ERROR] {e}")
        return 0.0
    finally:
        conn.close()


def get_all_vendor_balances():
    """
    Returns all vendors with their current outstanding payable balance.
    """
    vendors = get_all('vendors')
    result = []
    for v in vendors:
        bal = get_vendor_current_balance(v['id'])
        result.append({
            'id'     : v['id'],
            'name'   : v['name'],
            'phone'  : v.get('phone', ''),
            'balance': bal
        })
    return result


# ─────────────────────────────────────────────
#  PURCHASES & VENDOR PAYMENTS
# ─────────────────────────────────────────────
def get_all_purchases_with_vendor():
    """
    All purchase bills joined with vendor name + GSTIN.
    Includes GST breakdown columns for display & GSTR reporting.
    """
    return execute_query('''
        SELECT
            p.id,
            v.name        AS vendor_name,
            v.gstin       AS vendor_gstin,
            p.bill_no,
            p.purchase_date,
            p.taxable_amount,
            p.gst_rate,
            p.cgst_amount,
            p.sgst_amount,
            p.igst_amount,
            p.total_tax,
            p.total_amount,
            p.amount_paid,
            p.payment_status,
            p.place_of_supply,
            p.reverse_charge,
            p.notes
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
    # COALESCE(pv.rate, p.rate): variation ka cost use karo agar variation hai,
    # warna parent product ka cost use karo
    c.execute("""
        SELECT SUM((ii.rate - COALESCE(pv.rate, p.rate)) * ii.quantity)
        FROM invoice_items ii
        JOIN products p              ON ii.product_id = p.id
        LEFT JOIN product_variations pv ON ii.variation_id = pv.id
        JOIN invoices i              ON ii.invoice_id = i.id
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
#  PURCHASE ITEMS & BATCH TRACKING
# ─────────────────────────────────────────────
def save_purchase_with_items(purchase_data, items_data):
    """
    Save a purchase bill with line items.
    Automatically updates product stock_qty.
    Records batch tracking entries.
    Returns: new purchase_id or None.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        # Insert purchase header
        c.execute("""
            INSERT INTO purchases
              (vendor_id, bill_no, purchase_date, taxable_amount,
               gst_rate, cgst_amount, sgst_amount, igst_amount,
               total_tax, total_amount, amount_paid,
               payment_status, place_of_supply, reverse_charge, notes, purchase_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            purchase_data['vendor_id'],
            purchase_data.get('bill_no',''),
            purchase_data.get('purchase_date',''),
            purchase_data.get('taxable_amount', 0),
            purchase_data.get('gst_rate', 0),
            purchase_data.get('cgst_amount', 0),
            purchase_data.get('sgst_amount', 0),
            purchase_data.get('igst_amount', 0),
            purchase_data.get('total_tax', 0),
            purchase_data.get('total_amount', 0),
            purchase_data.get('amount_paid', 0),
            'Unpaid' if purchase_data.get('amount_paid', 0) <= 0
                     else ('Paid' if purchase_data.get('amount_paid', 0) >= purchase_data.get('total_amount', 0)
                     else 'Partial'),
            purchase_data.get('place_of_supply', ''),
            1 if purchase_data.get('reverse_charge') else 0,
            purchase_data.get('notes', ''),
            purchase_data.get('purchase_type', 'Resale'),
        ))
        purchase_id = c.lastrowid

        for item in items_data:
            qty      = float(item.get('quantity', 0))
            rate     = float(item.get('rate', 0))
            gst_rate = float(item.get('gst_rate', 0))
            taxable  = round(qty * rate, 2)
            is_igst  = bool(item.get('is_igst', False))

            cgst = round(taxable * gst_rate / 200, 2) if not is_igst else 0
            sgst = round(taxable * gst_rate / 200, 2) if not is_igst else 0
            igst = round(taxable * gst_rate / 100, 2) if is_igst     else 0
            total_item = taxable + cgst + sgst + igst

            c.execute("""
                INSERT INTO purchase_items
                  (purchase_id, product_id, description, batch_no, expiry_date,
                   quantity, rate, gst_rate, taxable_amount,
                   cgst_amount, sgst_amount, igst_amount, total_amount)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                purchase_id,
                item.get('product_id') or None,
                item.get('description', ''),
                item.get('batch_no', '') or '',
                item.get('expiry_date', '') or '',
                qty, rate, gst_rate, taxable,
                cgst, sgst, igst, total_item,
            ))
            item_id = c.lastrowid

            # Update product stock
            if item.get('product_id'):
                c.execute(
                    "UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?",
                    (qty, item['product_id'])
                )

            # Batch tracking entry (IN)
            if item.get('batch_no'):
                c.execute("""
                    INSERT INTO batch_tracking
                      (product_id, batch_no, expiry_date, purchase_id,
                       purchase_item_id, qty_in, qty_out, tracking_date, notes)
                    VALUES (?,?,?,?,?,?,0,?,?)
                """, (
                    item.get('product_id'),
                    item['batch_no'],
                    item.get('expiry_date', ''),
                    purchase_id,
                    item_id,
                    qty,
                    purchase_data.get('purchase_date', ''),
                    f"Stock IN from purchase bill {purchase_data.get('bill_no','')}",
                ))

        conn.commit()
        return purchase_id
    except Exception as e:
        conn.rollback()
        import traceback; traceback.print_exc()
        print(f"[save_purchase_with_items ERROR] {e}")
        return None
    finally:
        conn.close()


def get_purchase_items(purchase_id):
    """Return line items for a purchase bill."""
    return execute_query(
        """SELECT pi.*, p.name AS product_name
           FROM purchase_items pi
           LEFT JOIN products p ON pi.product_id = p.id
           WHERE pi.purchase_id = ?
           ORDER BY pi.id""",
        (purchase_id,), fetchall=True
    ) or []


def get_purchase_with_vendor(purchase_id):
    """Return a single purchase bill with vendor info."""
    return execute_query(
        """SELECT p.*,
                  COALESCE(v.name,  'Unknown') AS supplier_name,
                  COALESCE(v.gstin, '')         AS supplier_gstin
           FROM purchases p
           LEFT JOIN vendors v ON p.vendor_id = v.id
           WHERE p.id = ?""",
        (purchase_id,), fetchone=True
    )


def update_purchase_header(purchase_id, data):
    """Update purchase bill header fields (not items — items require re-save)."""
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        c.execute("""
            UPDATE purchases SET
              vendor_id       = ?,
              bill_no         = ?,
              purchase_date   = ?,
              taxable_amount  = ?,
              cgst_amount     = ?,
              sgst_amount     = ?,
              igst_amount     = ?,
              total_tax       = ?,
              total_amount    = ?,
              amount_paid     = ?,
              place_of_supply = ?,
              reverse_charge  = ?,
              notes           = ?,
              purchase_type   = ?,
              payment_status  = ?
            WHERE id = ?
        """, (
            data['vendor_id'],
            data.get('bill_no', ''),
            data.get('purchase_date', ''),
            data.get('taxable_amount', 0),
            data.get('cgst_amount', 0),
            data.get('sgst_amount', 0),
            data.get('igst_amount', 0),
            data.get('total_tax', 0),
            data.get('total_amount', 0),
            data.get('amount_paid', 0),
            data.get('place_of_supply', ''),
            1 if data.get('reverse_charge') else 0,
            data.get('notes', ''),
            data.get('purchase_type', 'Resale'),
            'Unpaid' if data.get('amount_paid', 0) <= 0
                     else ('Paid' if data.get('amount_paid', 0) >= data.get('total_amount', 0)
                     else 'Partial'),
            purchase_id,
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[update_purchase_header ERROR] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()



def save_purchase_item(purchase_id, item, is_igst=False):
    """Save a single purchase line item. Used by edit_purchase route."""
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        qty      = float(item.get('quantity', 0))
        rate     = float(item.get('rate', 0))
        gst_rate = float(item.get('gst_rate', 0))
        taxable  = round(qty * rate, 2)
        cgst     = round(taxable * gst_rate / 200, 2) if not is_igst else 0
        sgst     = round(taxable * gst_rate / 200, 2) if not is_igst else 0
        igst     = round(taxable * gst_rate / 100, 2) if is_igst     else 0
        total    = round(taxable + cgst + sgst + igst, 2)

        c.execute("""
            INSERT INTO purchase_items
              (purchase_id, product_id, description, batch_no, expiry_date,
               quantity, rate, gst_rate, taxable_amount,
               cgst_amount, sgst_amount, igst_amount, total_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            purchase_id,
            item.get('product_id') or None,
            item.get('description', ''),
            item.get('batch_no', '') or '',
            item.get('expiry_date', '') or '',
            qty, rate, gst_rate,
            taxable, cgst, sgst, igst, total
        ))
        item_id = c.lastrowid

        # Update product stock (only if product_id exists and purchase_type != Raw Material)
        pid = item.get('product_id')
        purchase_type = item.get('purchase_type', 'Resale')
        if pid and int(pid) > 0 and purchase_type != 'Raw Material' and qty > 0:
            c.execute("UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?", (qty, int(pid)))

        # Batch tracking
        batch_no = (item.get('batch_no') or '').strip()
        if batch_no and pid and int(pid) > 0:
            from datetime import date as _date
            c.execute("""
                INSERT INTO batch_tracking
                  (product_id, batch_no, expiry_date, purchase_id, purchase_item_id,
                   qty_in, qty_out, tracking_date, notes)
                VALUES (?,?,?,?,?,?,0,?,?)
            """, (
                int(pid), batch_no,
                item.get('expiry_date', '') or '',
                purchase_id, item_id,
                qty,
                _date.today().isoformat(),
                f"Stock IN (Edit) — Purchase #{purchase_id}",
            ))

        conn.commit()
        return item_id
    except Exception as e:
        print(f"[save_purchase_item ERROR] {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def delete_purchase_items(purchase_id):
    """Delete all line items for a purchase (before re-saving edited items)."""
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        c.execute("DELETE FROM purchase_items WHERE purchase_id = ?", (purchase_id,))
        conn.commit()
    except Exception as e:
        print(f"[delete_purchase_items ERROR] {e}")
    finally:
        conn.close()


def add_batch_tracking_entry(data):
    """
    Insert a single batch_tracking row (IN movement).
    data keys: product_id, batch_no, expiry_date, purchase_id (opt),
               invoice_id (opt), buyer_id (opt), qty_in, qty_out,
               tracking_date, notes
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        c.execute("""
            INSERT INTO batch_tracking
              (product_id, batch_no, expiry_date, purchase_id, invoice_id,
               buyer_id, qty_in, qty_out, tracking_date, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get('product_id'),
            data.get('batch_no', ''),
            data.get('expiry_date', '') or '',
            data.get('purchase_id'),
            data.get('invoice_id'),
            data.get('buyer_id'),
            data.get('qty_in', 0),
            data.get('qty_out', 0),
            data.get('tracking_date', ''),
            data.get('notes', ''),
        ))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"[add_batch_tracking_entry ERROR] {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_batches_for_product(product_id=None, include_expired=False):
    """
    Return batch summary for a product (or all products).
    Groups by product + batch_no, shows qty_in, qty_out, balance, expiry.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        from datetime import date
        today = date.today().isoformat()
        where = "WHERE 1=1"
        params = []
        if product_id:
            where += " AND bt.product_id = ?"
            params.append(product_id)
        if not include_expired:
            where += " AND (bt.expiry_date = '' OR bt.expiry_date IS NULL OR bt.expiry_date >= ?)"
            params.append(today)

        rows = c.execute(f"""
            SELECT bt.product_id,
                   p.name  AS product_name,
                   p.unit  AS unit,
                   bt.batch_no,
                   bt.expiry_date,
                   SUM(bt.qty_in)  AS total_in,
                   SUM(bt.qty_out) AS total_out,
                   SUM(bt.qty_in) - SUM(bt.qty_out) AS balance,
                   MAX(bt.purchase_id) AS last_purchase_id
            FROM batch_tracking bt
            JOIN products p ON bt.product_id = p.id
            {where}
            GROUP BY bt.product_id, bt.batch_no
            ORDER BY p.name, bt.expiry_date
        """, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[get_batches_for_product ERROR] {e}")
        return []
    finally:
        conn.close()


def get_batch_history(product_id=None, batch_no=None):
    """
    Full movement history for a batch — shows which customers received it.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        where  = "WHERE 1=1"
        params = []
        if product_id:
            where += " AND bt.product_id = ?"
            params.append(product_id)
        if batch_no:
            where += " AND bt.batch_no = ?"
            params.append(batch_no)

        rows = c.execute(f"""
            SELECT bt.*,
                   p.name  AS product_name,
                   b.name  AS buyer_name,
                   i.invoice_no,
                   v.name  AS vendor_name,
                   pu.bill_no AS purchase_bill_no
            FROM batch_tracking bt
            LEFT JOIN products p  ON bt.product_id  = p.id
            LEFT JOIN buyers   b  ON bt.buyer_id    = b.id
            LEFT JOIN invoices i  ON bt.invoice_id  = i.id
            LEFT JOIN purchases pu ON bt.purchase_id = pu.id
            LEFT JOIN vendors  v  ON pu.vendor_id   = v.id
            {where}
            ORDER BY bt.tracking_date DESC, bt.id DESC
        """, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[get_batch_history ERROR] {e}")
        return []
    finally:
        conn.close()


def get_expiring_batches(days_ahead=30):
    """Return batches expiring within N days — for reminders."""
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        from datetime import date, timedelta
        today  = date.today().isoformat()
        cutoff = (date.today() + timedelta(days=days_ahead)).isoformat()
        rows   = c.execute("""
            SELECT bt.product_id,
                   p.name  AS product_name,
                   p.unit  AS unit,
                   bt.batch_no,
                   bt.expiry_date,
                   SUM(bt.qty_in) - SUM(bt.qty_out) AS balance,
                   CASE WHEN bt.expiry_date < ? THEN 1 ELSE 0 END AS expired
            FROM batch_tracking bt
            JOIN products p ON bt.product_id = p.id
            WHERE bt.expiry_date != '' AND bt.expiry_date IS NOT NULL
              AND bt.expiry_date <= ?
            GROUP BY bt.product_id, bt.batch_no
            HAVING balance > 0
            ORDER BY bt.expiry_date
        """, (today, cutoff)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[get_expiring_batches ERROR] {e}")
        return []
    finally:
        conn.close()


def get_purchase_itc_summary(start_date, end_date):
    """
    ITC summary for GSTR-3B Table 4.
    Returns total CGST, SGST, IGST from purchases in date range.
    Excludes RCM purchases (they are reported separately).
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        row = c.execute("""
            SELECT
              COALESCE(SUM(taxable_amount), 0) AS taxable,
              COALESCE(SUM(cgst_amount),    0) AS cgst,
              COALESCE(SUM(sgst_amount),    0) AS sgst,
              COALESCE(SUM(igst_amount),    0) AS igst,
              COALESCE(SUM(total_tax),      0) AS total_tax,
              COUNT(*)                          AS purchase_count
            FROM purchases
            WHERE purchase_date BETWEEN ? AND ?
              AND reverse_charge = 0
        """, (start_date, end_date)).fetchone()

        rcm_row = c.execute("""
            SELECT
              COALESCE(SUM(cgst_amount), 0) AS cgst,
              COALESCE(SUM(sgst_amount), 0) AS sgst,
              COALESCE(SUM(igst_amount), 0) AS igst,
              COALESCE(SUM(total_tax),   0) AS total_tax,
              COUNT(*)                       AS count
            FROM purchases
            WHERE purchase_date BETWEEN ? AND ?
              AND reverse_charge = 1
        """, (start_date, end_date)).fetchone()

        return {
            'eligible_itc' : dict(row),
            'rcm_itc'      : dict(rcm_row),
            'start_date'   : start_date,
            'end_date'     : end_date,
        }
    except Exception as e:
        print(f"[get_purchase_itc_summary ERROR] {e}")
        return {'eligible_itc': {}, 'rcm_itc': {}, 'start_date': start_date, 'end_date': end_date}
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  STOCK REPORT
# ─────────────────────────────────────────────
def get_stock_report(start_date, end_date):
    """
    Stock report for a date range.
    Closing stock = current stock_qty in DB.
    Sales in range = sum of invoice_items qty for this product in date range.
    Opening stock  = closing_stock + sales_in_range (reverse-calculated).
    Note: No purchase_items table exists; stock changes are tracked on products.stock_qty.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        products = c.execute("SELECT * FROM products ORDER BY name").fetchall()
        report   = []
        # Check if variation_id column exists in invoice_items
        cols = [r[1] for r in c.execute("PRAGMA table_info(invoice_items)").fetchall()]
        has_variation_col = 'variation_id' in cols

        for p in products:
            pid = p['id']

            # Sales qty — all invoice_items for this product in range
            if has_variation_col:
                row = c.execute("""
                    SELECT COALESCE(SUM(ii.quantity), 0)
                    FROM invoice_items ii
                    JOIN invoices i ON ii.invoice_id = i.id
                    WHERE ii.product_id = ?
                      AND (ii.variation_id IS NULL OR ii.variation_id = 0)
                      AND i.invoice_date BETWEEN ? AND ?
                      AND i.invoice_no NOT LIKE '[CANCELLED]%'
                """, (pid, start_date, end_date)).fetchone()
            else:
                row = c.execute("""
                    SELECT COALESCE(SUM(ii.quantity), 0)
                    FROM invoice_items ii
                    JOIN invoices i ON ii.invoice_id = i.id
                    WHERE ii.product_id = ?
                      AND i.invoice_date BETWEEN ? AND ?
                      AND i.invoice_no NOT LIKE '[CANCELLED]%'
                """, (pid, start_date, end_date)).fetchone()
            sales_direct = float(row[0] or 0)

            # Sales via variations (only if column exists)
            sales_var = 0.0
            if has_variation_col:
                try:
                    row2 = c.execute("""
                        SELECT COALESCE(SUM(ii.quantity), 0)
                        FROM invoice_items ii
                        JOIN invoices i ON ii.invoice_id = i.id
                        JOIN product_variations pv ON ii.variation_id = pv.id
                        WHERE pv.product_id = ?
                          AND i.invoice_date BETWEEN ? AND ?
                          AND i.invoice_no NOT LIKE '[CANCELLED]%'
                    """, (pid, start_date, end_date)).fetchone()
                    sales_var = float(row2[0] or 0)
                except Exception:
                    pass

            total_sales   = sales_direct + sales_var
            closing_stock = float(p['stock_qty'] or 0)
            opening_stock = closing_stock + total_sales  # reverse-calculated

            report.append({
                'id'            : pid,
                'name'          : p['name'],
                'hsn'           : p['hsn'] or '',
                'unit'          : p['unit'] or 'Pcs',
                'opening_stock' : round(opening_stock, 3),
                'purchases'     : 0,  # not tracked per item
                'sales'         : round(total_sales, 3),
                'closing_stock' : round(closing_stock, 3),
                'selling_price' : float(p['selling_price'] or 0),
                'rate'          : float(p['rate'] or 0),
                'stock_value'   : round(closing_stock * float(p['rate'] or 0), 2),
            })
        return report
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[get_stock_report ERROR] {e}")
        return []
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  GSTR REPORTS
# ─────────────────────────────────────────────
def get_gstr1_data(start_date, end_date):
    """
    GSTR-1 data: B2B (with GSTIN), B2C (without), HSN summary.
    Returns dict with b2b, b2c, hsn_summary, totals.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        invoices = c.execute("""
            SELECT i.*, b.name AS buyer_name, b.gstin AS buyer_gstin,
                   b.state AS buyer_state
            FROM invoices i
            JOIN buyers b ON i.buyer_id = b.id
            WHERE i.invoice_date BETWEEN ? AND ?
              AND i.invoice_no NOT LIKE '[CANCELLED]%'
            ORDER BY i.invoice_date
        """, (start_date, end_date)).fetchall()

        b2b, b2c = [], []
        for inv in invoices:
            row = dict(inv)
            items = c.execute(
                "SELECT * FROM invoice_items WHERE invoice_id = ?", (row['id'],)
            ).fetchall()
            row['items'] = [dict(it) for it in items]
            gstin = (row.get('buyer_gstin') or '').strip()
            if gstin and len(gstin) == 15:
                b2b.append(row)
            else:
                b2c.append(row)

        # HSN Summary
        hsn_rows = c.execute("""
            SELECT ii.hsn, ii.gst_rate,
                   SUM(ii.quantity)                     AS total_qty,
                   SUM(ii.amount)                       AS taxable_value,
                   SUM(ii.amount * ii.gst_rate / 100)  AS total_tax
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            WHERE i.invoice_date BETWEEN ? AND ?
              AND i.invoice_no NOT LIKE '[CANCELLED]%'
              AND ii.hsn IS NOT NULL AND ii.hsn != ''
            GROUP BY ii.hsn, ii.gst_rate
            ORDER BY ii.hsn
        """, (start_date, end_date)).fetchall()
        hsn_summary = [dict(r) for r in hsn_rows]

        # Totals
        tot = c.execute("""
            SELECT
              COALESCE(SUM(taxable_value), 0) AS taxable,
              COALESCE(SUM(total_cgst),    0) AS cgst,
              COALESCE(SUM(total_sgst),    0) AS sgst,
              COALESCE(SUM(total_igst),    0) AS igst,
              COALESCE(SUM(grand_total),   0) AS grand
            FROM invoices
            WHERE invoice_date BETWEEN ? AND ?
              AND invoice_no NOT LIKE '[CANCELLED]%'
        """, (start_date, end_date)).fetchone()

        return {
            'b2b'        : b2b,
            'b2c'        : b2c,
            'hsn_summary': hsn_summary,
            'totals'     : dict(tot),
            'start_date' : start_date,
            'end_date'   : end_date,
        }
    except Exception as e:
        print(f"[get_gstr1_data ERROR] {e}")
        return {'b2b':[], 'b2c':[], 'hsn_summary':[], 'totals':{}, 'start_date':start_date, 'end_date':end_date}
    finally:
        conn.close()


def get_gstr3b_data(start_date, end_date):
    """
    GSTR-3B summary: outward taxable supplies broken by tax rate.
    Returns dict with rate-wise breakup and totals.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        # Rate-wise outward supply from invoice_items
        rate_rows = c.execute("""
            SELECT ii.gst_rate,
                   SUM(ii.amount)                      AS taxable_value,
                   SUM(ii.amount * ii.gst_rate / 200)  AS cgst,
                   SUM(ii.amount * ii.gst_rate / 200)  AS sgst,
                   SUM(ii.amount * ii.gst_rate / 100)  AS igst_total,
                   COUNT(DISTINCT i.id)                AS invoice_count
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            WHERE i.invoice_date BETWEEN ? AND ?
              AND i.invoice_no NOT LIKE '[CANCELLED]%'
            GROUP BY ii.gst_rate
            ORDER BY ii.gst_rate
        """, (start_date, end_date)).fetchall()
        rate_wise = [dict(r) for r in rate_rows]

        # IGST vs CGST/SGST split from invoices table
        tax_totals = c.execute("""
            SELECT
              COALESCE(SUM(taxable_value),0) AS total_taxable,
              COALESCE(SUM(total_cgst),   0) AS total_cgst,
              COALESCE(SUM(total_sgst),   0) AS total_sgst,
              COALESCE(SUM(total_igst),   0) AS total_igst,
              COALESCE(SUM(total_gst),    0) AS total_gst,
              COALESCE(SUM(grand_total),  0) AS total_grand,
              COUNT(*)                        AS invoice_count
            FROM invoices
            WHERE invoice_date BETWEEN ? AND ?
              AND invoice_no NOT LIKE '[CANCELLED]%'
        """, (start_date, end_date)).fetchone()

        # ── Section 4: ITC from Purchases ─────────────────────────────
        # Eligible ITC = purchases where reverse_charge = 0
        ei_row = c.execute("""
            SELECT
              COALESCE(SUM(taxable_amount), 0) AS taxable,
              COALESCE(SUM(cgst_amount),    0) AS cgst,
              COALESCE(SUM(sgst_amount),    0) AS sgst,
              COALESCE(SUM(igst_amount),    0) AS igst,
              COALESCE(SUM(total_tax),      0) AS total_tax,
              COUNT(*)                          AS bill_count
            FROM purchases
            WHERE purchase_date BETWEEN ? AND ?
              AND (reverse_charge = 0 OR reverse_charge IS NULL)
        """, (start_date, end_date)).fetchone()

        # RCM ITC = purchases where reverse_charge = 1
        rcm_row = c.execute("""
            SELECT
              COALESCE(SUM(cgst_amount), 0) AS cgst,
              COALESCE(SUM(sgst_amount), 0) AS sgst,
              COALESCE(SUM(igst_amount), 0) AS igst,
              COALESCE(SUM(total_tax),   0) AS total_tax,
              COUNT(*)                       AS bill_count
            FROM purchases
            WHERE purchase_date BETWEEN ? AND ?
              AND reverse_charge = 1
        """, (start_date, end_date)).fetchone()

        itc = {
            'eligible_itc': dict(ei_row)  if ei_row  else {},
            'rcm_itc'     : dict(rcm_row) if rcm_row else {},
        }

        return {
            'rate_wise'  : rate_wise,
            'tax_totals' : dict(tax_totals),
            'itc'        : itc,
            'start_date' : start_date,
            'end_date'   : end_date,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[get_gstr3b_data ERROR] {e}")
        return {'rate_wise':[], 'tax_totals':{}, 'itc':{}, 'start_date':start_date, 'end_date':end_date}
    finally:
        conn.close()

# ─────────────────────────────────────────────
#  ENTRY POINT (for direct testing)
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
#  ENTRY POINT (for direct testing)
# ─────────────────────────────────────────────
def get_gstr2b_data(start_date, end_date):
    """
    GSTR-2B style Purchase Register — ITC details from purchases.
    Returns all purchase bills in the date range with GST breakdown.
    Columns: Supplier, GSTIN, Bill No, Bill Date, Place of Supply,
             RCM, Taxable, CGST, SGST, IGST, Total Tax.
    """
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        rows = c.execute("""
            SELECT p.*,
                   COALESCE(v.name,  'Unknown Vendor')  AS supplier_name,
                   COALESCE(v.gstin, '')                 AS supplier_gstin,
                   COALESCE(v.phone, '')                 AS supplier_phone
            FROM purchases p
            LEFT JOIN vendors v ON p.vendor_id = v.id
            WHERE p.purchase_date BETWEEN ? AND ?
            ORDER BY p.purchase_date, p.id
        """, (start_date, end_date)).fetchall()

        purchases = [dict(r) for r in rows]

        # Totals — taxable_amount fallback for old bills without GST breakdown
        def _tax(r, k):     return float(r.get(k,0) or 0)
        def _taxable(r):
            ta = _tax(r,'taxable_amount')
            if ta > 0: return ta
            # Fallback: total_amount - total_tax
            return max(0, _tax(r,'total_amount') - _tax(r,'total_tax'))

        for r in purchases:
            if not r.get('taxable_amount'):
                r['taxable_amount'] = _taxable(r)

        totals = {
            'taxable'   : sum(_taxable(r)              for r in purchases),
            'cgst'      : sum(_tax(r,'cgst_amount')    for r in purchases),
            'sgst'      : sum(_tax(r,'sgst_amount')    for r in purchases),
            'igst'      : sum(_tax(r,'igst_amount')    for r in purchases),
            'total_tax' : sum(_tax(r,'total_tax')      for r in purchases),
            'grand'     : sum(_tax(r,'total_amount')   for r in purchases),
            'bill_count': len(purchases),
        }

        return {
            'purchases' : purchases,
            'totals'    : totals,
            'start_date': start_date,
            'end_date'  : end_date,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[get_gstr2b_data ERROR] {e}")
        return {'purchases':[], 'totals':{}, 'start_date':start_date, 'end_date':end_date}
    finally:
        conn.close()


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


# ─────────────────────────────────────────────────────────────
#  PROFORMA INVOICE / SALES QUOTATION FUNCTIONS
# ─────────────────────────────────────────────────────────────

def get_next_quotation_number():
    """Auto-generates next quotation number: QT-0001, QT-0002 ..."""
    conn = get_db_connection()
    c    = conn.cursor()
    c.execute("SELECT quotation_no FROM proforma_invoices ORDER BY id DESC LIMIT 1")
    last = c.fetchone()
    conn.close()
    prefix = "QT-"
    if last:
        try:
            return f"{prefix}{int(last['quotation_no'].split(prefix)[-1]) + 1:04d}"
        except Exception:
            pass
    return f"{prefix}0001"


def save_proforma(data, items):
    """Save a new proforma invoice with line items. Returns new id or None."""
    conn = get_db_connection()
    c    = conn.cursor()
    try:
        c.execute("""
            INSERT INTO proforma_invoices
              (quotation_no, quotation_date, valid_until, buyer_id,
               buyer_name, buyer_address, buyer_gstin, buyer_state, buyer_phone,
               payment_mode, order_ref,
               subtotal, total_discount, taxable_value,
               total_gst, total_cgst, total_sgst, total_igst,
               freight, round_off, grand_total, status, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data['quotation_no'], data['quotation_date'], data.get('valid_until',''),
            data.get('buyer_id'), data.get('buyer_name',''),
            data.get('buyer_address',''), data.get('buyer_gstin',''),
            data.get('buyer_state',''),  data.get('buyer_phone',''),
            data.get('payment_mode','Advance'), data.get('order_ref',''),
            data.get('subtotal',0), data.get('total_discount',0),
            data.get('taxable_value',0), data.get('total_gst',0),
            data.get('total_cgst',0), data.get('total_sgst',0),
            data.get('total_igst',0), data.get('freight',0),
            data.get('round_off',0), data.get('grand_total',0),
            data.get('status','Active'), data.get('notes',''),
        ))
        pid = c.lastrowid
        for item in items:
            c.execute("""
                INSERT INTO proforma_items
                  (proforma_id, product_id, description, hsn, gst_rate,
                   quantity, unit, rate, discount_percent, amount)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                pid,
                item.get('product_id'),   item.get('description',''),
                item.get('hsn',''),        item.get('gst_rate',0),
                item.get('quantity',0),    item.get('unit',''),
                item.get('rate',0),        item.get('discount_percent',0),
                item.get('amount',0),
            ))
        conn.commit()
        return pid
    except Exception as e:
        print(f"[save_proforma ERROR] {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_all_proformas():
    """Return all proforma invoices, newest first."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT p.*, b.name AS buyer_display
        FROM proforma_invoices p
        LEFT JOIN buyers b ON p.buyer_id = b.id
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_proforma_detail(proforma_id):
    """Return (proforma_dict, items_list) for a single quotation."""
    conn = get_db_connection()
    row  = conn.execute(
        "SELECT * FROM proforma_invoices WHERE id = ?", (proforma_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None, []
    items = conn.execute(
        "SELECT * FROM proforma_items WHERE proforma_id = ? ORDER BY id", (proforma_id,)
    ).fetchall()
    conn.close()
    return dict(row), [dict(i) for i in items]


def delete_proforma(proforma_id):
    """Delete a proforma invoice and its items."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM proforma_items WHERE proforma_id = ?", (proforma_id,))
        conn.execute("DELETE FROM proforma_invoices WHERE id = ?", (proforma_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[delete_proforma ERROR] {e}")
        return False
    finally:
        conn.close()

