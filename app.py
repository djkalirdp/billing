"""
================================================================================
  app.py  —  Flask Web Application
  Converted from: Python Tkinter Desktop App → Flask Web App

  This file replaces main.py entirely.
  Every Tkinter tab is now a set of Flask routes + HTML templates.

  Route Map:
    /                         → redirect to dashboard or login
    /login                    → GET/POST login page
    /logout                   → logout

    /dashboard                → Dashboard (KPIs + chart data API)
    /dashboard/chart-data     → JSON API for sales chart

    /billing                  → GET: billing form | POST: save invoice
    /billing/buyer-info       → JSON API: get buyer details by name
    /billing/product-info     → JSON API: get product details by name

    /invoices                 → Reports tab (list + filter)
    /invoices/<id>/pdf        → Download invoice PDF
    /invoices/<id>/cancel     → Cancel invoice
    /invoices/summary-pdf     → Export summary report PDF
    /invoices/detailed-pdf    → Export detailed item report PDF

    /products                 → List products (Admin)
    /products/add             → Add product (Admin)
    /products/<id>/edit       → Edit product / update stock (Admin)
    /products/<id>/delete     → Delete product (Admin)
    /products/search          → JSON API: search products

    /buyers                   → List buyers + outstanding
    /buyers/add               → Add buyer
    /buyers/<id>/edit         → Edit buyer
    /buyers/<id>/delete       → Delete buyer
    /buyers/<id>/ledger       → View ledger / khata
    /buyers/<id>/ledger/pdf   → Download ledger PDF
    /buyers/<id>/payment      → Add payment receipt

    /vendors                  → List vendors (Admin)
    /vendors/add              → Add vendor (Admin)
    /vendors/<id>/edit        → Edit vendor (Admin)
    /vendors/<id>/delete      → Delete vendor (Admin)

    /purchases                → List purchases (Admin)
    /purchases/add            → Add purchase bill (Admin)
    /purchases/<id>/payment   → Add payment to purchase (Admin)

    /settings                 → GET/POST settings page (Admin)
    /settings/upload-logo     → Upload company logo (Admin)
    /settings/users           → User management (Admin)
    /settings/users/add       → Add user (Admin)
    /settings/users/<id>/delete → Delete user (Admin)

================================================================================
"""

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file
)
from functools import wraps
from datetime import datetime, timedelta
import json
import os
import io
from werkzeug.utils import secure_filename

import database_manager as db
import reports_generator as rg
import pdf_generator

# ── Utility: number to Indian words ──────────────────────────────────────
def _num_to_words_indian(n):
    """Convert integer rupee amount to words (Indian style)."""
    ones = ['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine',
            'Ten','Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen',
            'Seventeen','Eighteen','Nineteen']
    tens = ['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety']
    def two_digit(n):
        if n < 20: return ones[n]
        return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
    def three_digit(n):
        if n >= 100:
            return ones[n // 100] + ' Hundred' + (' ' + two_digit(n % 100) if n % 100 else '')
        return two_digit(n)
    if n == 0: return 'Zero'
    parts = []
    if n >= 10000000:
        parts.append(three_digit(n // 10000000) + ' Crore'); n %= 10000000
    if n >= 100000:
        parts.append(three_digit(n // 100000) + ' Lakh'); n %= 100000
    if n >= 1000:
        parts.append(three_digit(n // 1000) + ' Thousand'); n %= 1000
    if n > 0:
        parts.append(three_digit(n))
    return ' '.join(parts) + ' Rupees Only'

# ─────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'billing-app-secret-2025-change-this')

# Register custom Jinja2 filter
app.jinja_env.filters['format_words'] = _num_to_words_indian

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER   = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTS    = {'png', 'jpg', 'jpeg'}
SETTINGS_FILE   = os.path.join(BASE_DIR, 'settings.json')
INVOICES_DIR    = os.path.join(BASE_DIR, 'invoices')
REPORTS_DIR     = os.path.join(BASE_DIR, 'reports')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'data'),    exist_ok=True)
os.makedirs(INVOICES_DIR,  exist_ok=True)
os.makedirs(REPORTS_DIR,   exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'backups'), exist_ok=True)


# ─────────────────────────────────────────────
#  SETTINGS HELPERS
# ─────────────────────────────────────────────
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            "company_info"    : {"name": "My Company", "state": "Delhi"},
            "bank_details"    : {},
            "invoice_settings": {"invoice_prefix": "INV-", "terms_and_conditions": ""},
            "upi"             : {"upi_id": "", "upi_name": ""}
        }

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_invoice_prefix():
    s = load_settings()
    return s.get('invoice_settings', {}).get('invoice_prefix', 'INV-')


def get_company_state():
    s = load_settings()
    return s.get('company_info', {}).get('state', 'Delhi')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS


# ─────────────────────────────────────────────
#  MOBILE DETECTION HELPER
# ─────────────────────────────────────────────
_MOBILE_UAS = (
    'android', 'iphone', 'ipad', 'ipod', 'blackberry',
    'windows phone', 'mobile', 'opera mini', 'opera mobi',
    'webos', 'silk', 'bada', 'kaios',
)

def is_mobile_request():
    """
    Returns True if the request comes from a mobile browser.
    Checks User-Agent string + optional ?mobile=1/0 override.
    """
    override = request.args.get('mobile') or request.cookies.get('force_mobile')
    if override == '1':
        return True
    if override == '0':
        return False
    ua = request.headers.get('User-Agent', '').lower()
    return any(token in ua for token in _MOBILE_UAS)


def mrender(template_name, **ctx):
    """
    Smart render_template wrapper.
    - Mobile browsers → mobile/<template_name>  (if it exists)
    - Desktop browsers → <template_name>
    Usage: replace mrender('foo.html', ...) with mrender('foo.html', ...)
    """
    import os
    if is_mobile_request():
        mobile_tpl = 'mobile/' + template_name
        # Flask looks in the templates/ folder; check real file path
        mobile_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'templates', 'mobile', template_name
        )
        if os.path.exists(mobile_path):
            return render_template(mobile_tpl, **ctx)
    return render_template(template_name, **ctx)


# ─────────────────────────────────────────────
#  AUTH DECORATORS
# ─────────────────────────────────────────────
def login_required(f):
    """Redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Redirect to dashboard if not Admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'Admin':
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  APP STARTUP
# ─────────────────────────────────────────────
with app.app_context():
    db.create_tables()
    db.daily_backup()


# ─────────────────────────────────────────────
#  CONTEXT PROCESSOR  (available in all templates)
# ─────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {
        'now'          : datetime.now(),
        'app_name'     : load_settings().get('company_info', {}).get('name', 'Billing App'),
        'user_role'    : session.get('role', ''),
        'username'     : session.get('username', ''),
    }


# ─────────────────────────────────────────────
#  LOGIN / LOGOUT
# ─────────────────────────────────────────────
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = db.check_login(username, password)

        if role:
            session['username'] = username
            session['role']     = role
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return mrender('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    today_sales, total_due, total_profit, low_stock = db.get_dashboard_kpi()
    return mrender('dashboard.html',
        today_sales  = today_sales,
        total_due    = total_due,
        total_profit = total_profit,
        low_stock    = low_stock,
    )


@app.route('/dashboard/chart-data')
@login_required
def chart_data():
    """JSON API — returns sales chart labels + values for Chart.js"""
    mode = request.args.get('mode', 'Weekly')
    labels, values = db.get_graph_data(mode)
    return jsonify({'labels': labels, 'values': values})


# ─────────────────────────────────────────────
#  BILLING
# ─────────────────────────────────────────────
@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    settings = load_settings()
    prefix   = settings.get('invoice_settings', {}).get('invoice_prefix', 'INV-')

    if request.method == 'GET':
        products = db.get_all('products')
        buyers   = db.get_all('buyers')
        inv_no   = db.get_next_invoice_number(prefix)
        return mrender('billing.html',
            products = products,
            buyers   = buyers,
            inv_no   = inv_no,
            today    = datetime.now().strftime('%Y-%m-%d'),
            settings = settings,
        )

    # ── POST: Save invoice ─────────────────────────────────────────
    form = request.form

    buyer_name = form.get('buyer_name', '').strip()
    if not buyer_name:
        flash('Buyer name is required.', 'danger')
        return redirect(url_for('billing'))

    # Handle new vs existing buyer
    existing_buyers = {b['name'].strip().lower(): b for b in db.get_all('buyers')}
    if buyer_name.lower() in existing_buyers:
        buyer_id = existing_buyers[buyer_name.lower()]['id']
    else:
        # Auto-create new buyer
        gstin   = form.get('buyer_gstin', '').strip()
        address = form.get('buyer_address', '').strip()
        state   = form.get('buyer_state', '').strip()
        # GSTIN/address/state optional for quick billing; buyer can be edited later
        buyer_id = db.add_record('buyers', {
            'name': buyer_name, 'gstin': gstin, 'address': address,
            'phone': form.get('buyer_phone',''), 'email': '',
            'state': state, 'opening_balance': 0
        })
        if not buyer_id:
            flash('Failed to save new buyer.', 'danger')
            return redirect(url_for('billing'))

    prev_balance    = db.get_buyer_current_balance(buyer_id)
    company_state   = get_company_state()

    # ── Build items list from form ─────────────────────────────────
    product_ids     = request.form.getlist('product_id[]')
    descriptions    = request.form.getlist('description[]')
    hsns            = request.form.getlist('hsn[]')
    gst_rates       = request.form.getlist('gst_rate[]')
    quantities      = request.form.getlist('quantity[]')
    rates           = request.form.getlist('rate[]')
    discounts       = request.form.getlist('discount_percent[]')
    amounts         = request.form.getlist('amount[]')
    batch_nos       = request.form.getlist('batch_no[]')

    items_data = []

    for i in range(len(descriptions)):
        try:
            desc = descriptions[i].strip() if i < len(descriptions) else ''
            if not desc:
                continue
            qty  = float(quantities[i] or 0) if i < len(quantities) else 0
            if qty <= 0:
                continue
            rate    = float(rates[i] or 0)     if i < len(rates)     else 0
            disc    = float(discounts[i] or 0)  if i < len(discounts) else 0
            gst     = float(gst_rates[i] or 0)  if i < len(gst_rates) else 0
            # Accept product_id if valid int, else use 0 (manual product entry)
            pid_raw = product_ids[i].strip()    if i < len(product_ids) else ''
            pid     = int(pid_raw) if pid_raw and pid_raw.isdigit() and int(pid_raw) > 0 else 0
            # Calculate amount from qty/rate/disc if client didn't send it
            base_amt = qty * rate
            disc_amt = base_amt * disc / 100
            taxable  = base_amt - disc_amt
            sent_amt   = amounts[i] if i < len(amounts) else ''
            amount     = float(sent_amt) if sent_amt and sent_amt != '' else taxable
            var_ids    = request.form.getlist('variation_id[]')
            var_id_raw = var_ids[i].strip() if i < len(var_ids) else ''
            var_id     = int(var_id_raw) if var_id_raw and var_id_raw.isdigit() and int(var_id_raw) > 0 else None
            batch_no   = batch_nos[i].strip() if i < len(batch_nos) else ''
            items_data.append({
                'product_id'      : pid,
                'variation_id'    : var_id,
                'description'     : desc,
                'hsn'             : hsns[i].strip() if i < len(hsns) else '',
                'gst_rate'        : gst,
                'quantity'        : qty,
                'rate'            : rate,
                'discount_percent': disc,
                'batch_no'        : batch_no,
                'amount'          : round(amount, 4),
            })
        except (ValueError, IndexError, AttributeError):
            continue

    if not items_data:
        flash('Invoice must have at least one item.', 'danger')
        return redirect(url_for('billing'))

    # ── Calculate totals ───────────────────────────────────────────
    subtotal      = sum(float(r) * float(rt) for r, rt in zip(quantities[:len(items_data)], rates[:len(items_data)]) if r and rt)
    total_discount= sum(float(items_data[i]['rate']) * float(items_data[i]['quantity']) * (items_data[i]['discount_percent']/100) for i in range(len(items_data)))
    taxable_val   = subtotal - total_discount

    # Determine GST type
    buyer_obj     = db.get_by_id('buyers', buyer_id)
    buyer_state   = buyer_obj.get('state', '') if buyer_obj else ''
    is_igst       = buyer_state.strip().lower() != company_state.strip().lower()

    total_gst = sum(
        item['amount'] * (item['gst_rate'] / 100)
        for item in items_data
    )
    total_igst = total_gst if is_igst else 0
    total_cgst = 0 if is_igst else round(total_gst / 2, 2)
    total_sgst = 0 if is_igst else round(total_gst / 2, 2)

    freight    = float(form.get('freight', 0) or 0)
    grand_total_raw = taxable_val + total_gst + freight
    round_off  = round(grand_total_raw) - grand_total_raw
    grand_total = round(grand_total_raw)

    paid_now = float(form.get('paid_amount', 0) or 0)

    inv_data = {
        'invoice_no'       : form.get('invoice_no'),
        'invoice_date'     : form.get('invoice_date'),
        'buyer_id'         : buyer_id,
        'payment_mode'     : form.get('payment_mode', 'Cash'),
        'order_ref'        : form.get('order_ref', ''),
        'dispatch_info'    : form.get('dispatch_info', ''),
        'subtotal'         : round(subtotal, 2),
        'total_discount'   : round(total_discount, 2),
        'taxable_value'    : round(taxable_val, 2),
        'total_gst'        : round(total_gst, 2),
        'total_cgst'       : total_cgst,
        'total_sgst'       : total_sgst,
        'total_igst'       : total_igst,
        'freight'          : freight,
        'round_off'        : round(round_off, 2),
        'grand_total'      : grand_total,
        'paid_amount'      : paid_now,       # stored permanently in DB
        'previous_balance' : prev_balance,   # buyer balance BEFORE this invoice
    }

    invoice_id = db.save_invoice(inv_data, items_data, company_state)
    if not invoice_id:
        flash('Failed to save invoice. Please try again.', 'danger')
        return redirect(url_for('billing'))

    # Record payment received in customer_payments ledger
    if paid_now > 0:
        db.add_customer_payment({
            'buyer_id'    : buyer_id,
            'payment_date': inv_data['invoice_date'],
            'amount'      : paid_now,
            'payment_mode': inv_data['payment_mode'],
            'notes'       : f"Inv Ref: {inv_data['invoice_no']}"
        })

    # Generate PDF
    full_inv, full_items = db.get_full_invoice_details(invoice_id)
    if full_inv:
        try:
            pdf_generator.create_invoice_pdf(
                full_inv, full_items, settings,
                previous_balance=prev_balance,
                paid_amount=paid_now,
                save_to_disk=True
            )
        except Exception as e:
            flash(f'Invoice saved but PDF generation failed: {e}', 'warning')

    flash(f"Invoice {inv_data['invoice_no']} saved successfully!", 'success')
    return redirect(url_for('view_invoice', invoice_id=invoice_id))


@app.route('/billing/buyer-info')
@login_required
def buyer_info_api():
    """JSON API — returns buyer details + current balance for autocomplete."""
    name = request.args.get('name', '').strip()
    buyers = db.get_all('buyers')
    buyer  = next((b for b in buyers if b['name'].lower() == name.lower()), None)
    if buyer:
        balance = db.get_buyer_current_balance(buyer['id'])
        return jsonify({
            'found'  : True,
            'id'     : buyer['id'],
            'gstin'  : buyer.get('gstin', ''),
            'address': buyer.get('address', ''),
            'state'  : buyer.get('state', ''),
            'phone'  : buyer.get('phone', ''),
            'balance': balance,
        })
    return jsonify({'found': False})


@app.route('/billing/product-info')
@login_required
def product_info_api():
    """JSON API — returns product details for billing row auto-fill."""
    name  = request.args.get('name', '').strip()
    mode  = request.args.get('mode', 'Retail')   # Retail | Wholesale
    products = db.get_all('products')
    product  = next((p for p in products if p['name'].lower() == name.lower()), None)
    if product:
        price = product['wholesale_price'] if mode == 'Wholesale' else product['selling_price']
        return jsonify({
            'found'     : True,
            'id'        : product['id'],
            'hsn'       : product.get('hsn', ''),
            'gst_rate'  : product.get('gst_rate', 0),
            'unit'      : product.get('unit', ''),
            'rate'      : price,
            'stock_qty' : product.get('stock_qty', 0),
        })
    return jsonify({'found': False})


@app.route('/products/search')
@login_required
def product_search_api():
    """JSON API — product search including variations for billing autocomplete."""
    try:
        q        = request.args.get('q', '')
        products = db.search_products(q)
        return jsonify([{
            'id'             : p['id'],
            'name'           : p.get('display_name') or p['name'],
            'hsn'            : p.get('hsn') or '',
            'gst_rate'       : p.get('gst_rate') or 0,
            'unit'           : p.get('unit') or '',
            'stock_qty'      : p.get('stock_qty') or 0,
            'selling_price'  : round(float(p.get('selling_price') or 0), 2),
            'wholesale_price': round(float(p.get('wholesale_price') or p.get('selling_price') or 0), 2),
            'variation_id'   : p.get('variation_id'),
            'variation_name' : p.get('variation_name'),
        } for p in products])
    except Exception as e:
        app.logger.error(f"product_search_api error: {e}")
        return jsonify([])


@app.route('/products/<int:product_id>/batches')
@login_required
def product_batches_api(product_id):
    """JSON API — active batches for a product (for billing batch selection)."""
    try:
        batches = db.get_batches_for_product(product_id=product_id, include_expired=False)
        return jsonify([{
            'batch_no'    : b['batch_no'],
            'expiry_date' : b['expiry_date'] or '',
            'balance'     : round(float(b['balance'] or 0), 3),
            'unit'        : b['unit'] or '',
        } for b in batches if float(b.get('balance') or 0) > 0])
    except Exception as e:
        app.logger.error(f"product_batches_api error: {e}")
        return jsonify([])


# ─────────────────────────────────────────────
#  INVOICES / REPORTS
# ─────────────────────────────────────────────
@app.route('/invoices')
@login_required
def invoices():
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end   = request.args.get('end',   datetime.now().strftime('%Y-%m-%d'))
    buyer_id   = request.args.get('buyer_id', None, type=int)
    search_txt = request.args.get('search', '')

    inv_list   = db.get_invoices_by_filter(start, end, buyer_id, search_txt)
    buyers     = db.get_all('buyers')

    total_taxable = sum(i['taxable_value'] for i in inv_list if '[CANCELLED]' not in str(i['invoice_no']))
    total_gst     = sum(i['total_gst']     for i in inv_list if '[CANCELLED]' not in str(i['invoice_no']))
    total_grand   = sum(i['grand_total']   for i in inv_list if '[CANCELLED]' not in str(i['invoice_no']))

    return mrender('invoices.html',
        invoices      = inv_list,
        buyers        = buyers,
        start         = start,
        end           = end,
        buyer_id      = buyer_id,
        search        = search_txt,
        total_taxable = total_taxable,
        total_gst     = total_gst,
        total_grand   = total_grand,
    )


@app.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    inv, items = db.get_full_invoice_details(invoice_id)
    if not inv:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('invoices'))
    # paid_amount and previous_balance stored in invoice at billing time — read directly
    paid     = float(inv.get('paid_amount')      or 0)
    prev_bal = float(inv.get('previous_balance') or 0)
    return mrender('invoice_detail.html',
                   invoice=inv, items=items, settings=load_settings(),
                   paid_amount=paid, previous_balance=prev_bal)


@app.route('/invoices/<int:invoice_id>/pdf')
@login_required
def download_invoice_pdf(invoice_id):
    """Download / reprint invoice as PDF. Accepts ?size=A4|A4L|A5|A5L"""
    inv, items = db.get_full_invoice_details(invoice_id)
    if not inv:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('invoices'))

    if '[CANCELLED]' in str(inv.get('invoice_no', '')):
        flash('Cannot download PDF for a cancelled invoice.', 'warning')
        return redirect(url_for('invoices'))

    settings   = load_settings()
    paid       = float(inv.get('paid_amount')      or 0)
    prev_bal   = float(inv.get('previous_balance') or 0)
    page_size  = request.args.get('size', 'A4').upper()
    pdf_bytes  = pdf_generator.create_invoice_pdf(
        inv, items, settings,
        previous_balance=prev_bal,
        paid_amount=paid,
        save_to_disk=(page_size == 'A4'),
        page_size=page_size
    )
    safe_name = "".join(c if c.isalnum() or c in ('-', '_', '.') else '_'
                        for c in str(inv['invoice_no']))
    filename  = f"{safe_name}_{page_size}.pdf"
    return pdf_generator.get_pdf_response(pdf_bytes, filename)


@app.route('/invoices/<int:invoice_id>/cancel', methods=['POST'])
@admin_required
def cancel_invoice(invoice_id):
    """Cancel invoice and restore stock."""
    inv, _ = db.get_full_invoice_details(invoice_id)
    if not inv:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('invoices'))

    if '[CANCELLED]' in str(inv.get('invoice_no', '')):
        flash('Invoice is already cancelled.', 'warning')
        return redirect(url_for('invoices'))

    if db.cancel_invoice(invoice_id):
        flash(f"Invoice {inv['invoice_no']} cancelled. Stock restored.", 'success')
    else:
        flash('Failed to cancel invoice.', 'danger')

    return redirect(url_for('invoices'))


@app.route('/invoices/summary-pdf')
@admin_required
def export_summary_pdf():
    """Export filtered invoices as a Summary PDF."""
    start  = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end    = request.args.get('end',   datetime.now().strftime('%Y-%m-%d'))
    inv_list = db.get_invoices_by_filter(start, end)
    settings = load_settings()
    pdf_bytes = pdf_generator.create_transaction_report_pdf(inv_list, start, end, settings, save_to_disk=True)
    return pdf_generator.get_pdf_response(pdf_bytes, 'Summary_Report.pdf')


@app.route('/invoices/detailed-pdf')
@admin_required
def export_detailed_pdf():
    """Export item-wise detailed report PDF."""
    start  = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end    = request.args.get('end',   datetime.now().strftime('%Y-%m-%d'))
    inv_list = db.get_invoices_by_filter(start, end)
    ids      = [i['id'] for i in inv_list]
    settings = load_settings()
    pdf_bytes = pdf_generator.create_detailed_invoice_report(ids, settings, save_to_disk=True)
    return pdf_generator.get_pdf_response(pdf_bytes, 'Detailed_Report.pdf')


# ─────────────────────────────────────────────
#  PRODUCTS  (Admin only)
# ─────────────────────────────────────────────
@app.route('/products')
@admin_required
def products():
    search   = request.args.get('search', '')
    if search:
        prod_list = db.search_products(search)
    else:
        prod_list = db.get_all('products')
    # Add variation counts to each product
    for p in prod_list:
        p['variation_count'] = len(db.get_variations(p['id']))
    return mrender('products.html', products=prod_list, search=search)




@app.route('/products/rate-list')
@login_required
def product_rate_list():
    """Product Rate List — shows all products + variations with HSN, cost, rate, GST, MRP, stock."""
    q = request.args.get('q', '').strip()
    conn = db.get_db_connection()
    c = conn.cursor()

    like = f'%{q}%'
    where = "WHERE p.name LIKE ? OR p.hsn LIKE ?" if q else ""
    params = (like, like) if q else ()

    rows = c.execute(f"""
        SELECT p.*,
               COALESCE(p.selling_price, p.rate) AS sp,
               ROUND(COALESCE(p.selling_price, p.rate) * (1 + p.gst_rate/100.0), 2) AS price_with_gst
        FROM products p
        {where}
        ORDER BY p.name
    """, params).fetchall()

    products_list = []
    for r in rows:
        prod = dict(r)
        # Fetch variations for this product
        vars_rows = c.execute("""
            SELECT * FROM product_variations WHERE product_id = ? ORDER BY variation_name
        """, (prod['id'],)).fetchall()
        prod['variations'] = [dict(v) for v in vars_rows]
        products_list.append(prod)

    conn.close()
    settings = load_settings()
    return mrender('product_rate_list.html',
                   products=products_list, q=q,
                   settings=settings)

@app.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        f = request.form
        try:
            name        = f.get('name', '').strip()
            added_stock = float(f.get('add_stock', 0) or 0)
            purch_rate  = float(f.get('purchase_rate', 0) or 0)
            batch_no    = f.get('batch_no', '').strip()
            expiry_date = f.get('expiry_date', '').strip()

            if not name:
                flash('Product name is required.', 'danger')
                return mrender('product_form.html', product=None, action='Add')

            new_id = db.add_record('products', {
                'name'           : name,
                'hsn'            : f.get('hsn', ''),
                'gst_rate'       : float(f.get('gst_rate', 0)),
                'unit'           : f.get('unit', ''),
                'selling_price'  : float(f.get('selling_price', 0)),
                'wholesale_price': float(f.get('wholesale_price', 0)),
                'stock_qty'      : added_stock,
                'rate'           : purch_rate,
            })
            if new_id:
                # Record batch_tracking entry if batch_no provided
                if batch_no and added_stock > 0:
                    db.add_batch_tracking_entry({
                        'product_id'  : new_id,
                        'batch_no'    : batch_no,
                        'expiry_date' : expiry_date,
                        'qty_in'      : added_stock,
                        'qty_out'     : 0,
                        'tracking_date': datetime.now().strftime('%Y-%m-%d'),
                        'notes'       : 'Opening stock entry',
                    })
                flash(f'Product "{name}" added successfully!', 'success')
            else:
                flash('Product name already exists.', 'danger')
        except ValueError as e:
            flash(f'Invalid number value: {e}', 'danger')
        return redirect(url_for('products'))

    return mrender('product_form.html', product=None, action='Add')


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = db.get_by_id('products', product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products'))

    if request.method == 'POST':
        f = request.form
        try:
            added_stock = float(f.get('add_stock', 0) or 0)
            purch_rate  = float(f.get('purchase_rate', 0) or 0)

            update_data = {
                'name'           : f.get('name', product['name']),
                'hsn'            : f.get('hsn', ''),
                'gst_rate'       : float(f.get('gst_rate', 0)),
                'unit'           : f.get('unit', ''),
                'selling_price'  : float(f.get('selling_price', 0)),
                'wholesale_price': float(f.get('wholesale_price', 0)),
            }

            # WAC stock update
            if added_stock > 0:
                old_qty   = product['stock_qty']
                old_rate  = product['rate']
                total_val = (old_qty * old_rate) + (added_stock * purch_rate)
                new_qty   = old_qty + added_stock
                update_data['stock_qty'] = new_qty
                update_data['rate']      = round(total_val / new_qty, 2) if new_qty > 0 else purch_rate

                # Record batch_tracking entry if batch_no given
                batch_no    = f.get('batch_no', '').strip()
                expiry_date = f.get('expiry_date', '').strip()
                if batch_no:
                    db.add_batch_tracking_entry({
                        'product_id'   : product_id,
                        'batch_no'     : batch_no,
                        'expiry_date'  : expiry_date,
                        'qty_in'       : added_stock,
                        'qty_out'      : 0,
                        'tracking_date': datetime.now().strftime('%Y-%m-%d'),
                        'notes'        : f'Stock added via product edit',
                    })
            else:
                update_data['stock_qty'] = product['stock_qty']
                update_data['rate']      = product['rate']

            db.update_record('products', product_id, update_data)
            flash(f'Product "{product["name"]}" updated!', 'success')
        except ValueError as e:
            flash(f'Invalid number value: {e}', 'danger')
        return redirect(url_for('products'))

    return mrender('product_form.html', product=product, action='Edit')


@app.route('/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = db.get_by_id('products', product_id)
    if product:
        db.delete_record('products', product_id)
        flash(f'Product "{product["name"]}" deleted.', 'success')
    return redirect(url_for('products'))


# ─────────────────────────────────────────────
#  PRODUCT VARIATIONS
# ─────────────────────────────────────────────
@app.route('/products/<int:product_id>/variations')
@admin_required
def product_variations(product_id):
    product    = db.get_by_id('products', product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products'))
    variations = db.get_variations(product_id)
    return mrender('product_variations.html', product=product, variations=variations)


@app.route('/products/<int:product_id>/variations/add', methods=['POST'])
@admin_required
def add_variation(product_id):
    f    = request.form
    name = f.get('variation_name', '').strip()
    if not name:
        flash('Variation name is required.', 'danger')
        return redirect(url_for('product_variations', product_id=product_id))
    db.add_variation(
        product_id    = product_id,
        name          = name,
        selling_price = f.get('selling_price',   0),
        wholesale_price= f.get('wholesale_price', 0),
        stock_qty     = f.get('stock_qty',        0),
        cost_rate     = f.get('cost_rate',         0),
    )
    flash(f'Variation "{name}" added.', 'success')
    return redirect(url_for('product_variations', product_id=product_id))


@app.route('/products/<int:product_id>/variations/<int:variation_id>/edit', methods=['POST'])
@admin_required
def edit_variation(product_id, variation_id):
    f    = request.form
    name = f.get('variation_name', '').strip()
    if not name:
        flash('Variation name is required.', 'danger')
        return redirect(url_for('product_variations', product_id=product_id))
    db.update_variation(
        variation_id    = variation_id,
        name            = name,
        selling_price   = f.get('selling_price',   0),
        wholesale_price = f.get('wholesale_price',  0),
        stock_qty       = f.get('stock_qty',        0),
        cost_rate       = f.get('cost_rate',         0),
    )
    flash(f'Variation "{name}" updated.', 'success')
    return redirect(url_for('product_variations', product_id=product_id))


@app.route('/products/<int:product_id>/variations/<int:variation_id>/delete', methods=['POST'])
@admin_required
def delete_variation(product_id, variation_id):
    db.delete_variation(variation_id)
    flash('Variation deleted.', 'success')
    return redirect(url_for('product_variations', product_id=product_id))


# ─────────────────────────────────────────────
#  BUYERS
# ─────────────────────────────────────────────
@app.route('/buyers')
@login_required
def buyers():
    search    = request.args.get('search', '')
    all_buyers = db.get_all('buyers')

    if search:
        all_buyers = [b for b in all_buyers if search.lower() in b['name'].lower()]

    # Calculate outstanding balance for each buyer
    buyer_list = []
    for b in all_buyers:
        bal = db.get_buyer_current_balance(b['id'])
        buyer_list.append({**b, 'balance': bal})

    return mrender('buyers.html', buyers=buyer_list, search=search)


@app.route('/buyers/add', methods=['GET', 'POST'])
@login_required
def add_buyer():
    if request.method == 'POST':
        f = request.form
        try:
            ob = float(f.get('opening_balance', 0) or 0)
        except ValueError:
            ob = 0

        result = db.add_record('buyers', {
            'name'           : f.get('name', '').strip(),
            'gstin'          : f.get('gstin', ''),
            'address'        : f.get('address', ''),
            'phone'          : f.get('phone', ''),
            'email'          : f.get('email', ''),
            'state'          : f.get('state', ''),
            'opening_balance': ob,
        })
        if result:
            flash('Buyer added successfully!', 'success')
        else:
            flash('Buyer name already exists.', 'danger')
        return redirect(url_for('buyers'))

    return mrender('buyer_form.html', buyer=None, action='Add')


@app.route('/buyers/<int:buyer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_buyer(buyer_id):
    buyer = db.get_by_id('buyers', buyer_id)
    if not buyer:
        flash('Buyer not found.', 'danger')
        return redirect(url_for('buyers'))

    if request.method == 'POST':
        f = request.form
        try:
            ob = float(f.get('opening_balance', 0) or 0)
        except ValueError:
            ob = buyer.get('opening_balance', 0)

        db.update_record('buyers', buyer_id, {
            'name'           : f.get('name', buyer['name']),
            'gstin'          : f.get('gstin', ''),
            'address'        : f.get('address', ''),
            'phone'          : f.get('phone', ''),
            'email'          : f.get('email', ''),
            'state'          : f.get('state', ''),
            'opening_balance': ob,
        })
        flash('Buyer updated successfully!', 'success')
        return redirect(url_for('buyers'))

    return mrender('buyer_form.html', buyer=buyer, action='Edit')


@app.route('/buyers/<int:buyer_id>/delete', methods=['POST'])
@admin_required
def delete_buyer(buyer_id):
    buyer = db.get_by_id('buyers', buyer_id)
    if buyer:
        db.delete_record('buyers', buyer_id)
        flash(f'Buyer "{buyer["name"]}" deleted.', 'success')
    return redirect(url_for('buyers'))




@app.route('/payments/<int:payment_id>/delete', methods=['POST'])
@admin_required
def delete_payment(payment_id):
    """Delete a customer payment entry from ledger."""
    pay = db.get_customer_payment(payment_id)
    if not pay:
        flash('Payment not found.', 'danger')
        return redirect(url_for('buyers'))
    buyer_id = pay['buyer_id']
    if db.delete_customer_payment(payment_id):
        flash('Payment entry deleted.', 'success')
    else:
        flash('Failed to delete payment.', 'danger')
    return redirect(url_for('buyer_ledger', buyer_id=buyer_id))


@app.route('/payments/<int:payment_id>/edit', methods=['POST'])
@admin_required
def edit_payment(payment_id):
    """Edit a customer payment entry."""
    pay = db.get_customer_payment(payment_id)
    if not pay:
        flash('Payment not found.', 'danger')
        return redirect(url_for('buyers'))
    buyer_id = pay['buyer_id']
    f = request.form
    data = {
        'payment_date': f.get('payment_date', pay['payment_date']),
        'amount'      : f.get('amount', pay['amount']),
        'payment_mode': f.get('payment_mode', pay['payment_mode']),
        'notes'       : f.get('notes', ''),
    }
    if db.update_customer_payment(payment_id, data):
        flash('Payment updated successfully.', 'success')
    else:
        flash('Failed to update payment.', 'danger')
    return redirect(url_for('buyer_ledger', buyer_id=buyer_id))

@app.route('/buyers/<int:buyer_id>/ledger')
@login_required
def buyer_ledger(buyer_id):
    buyer = db.get_by_id('buyers', buyer_id)
    if not buyer:
        flash('Buyer not found.', 'danger')
        return redirect(url_for('buyers'))

    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end   = request.args.get('end',   datetime.now().strftime('%Y-%m-%d'))

    ledger_data, closing_balance = db.get_buyer_ledger(buyer_id, start, end)

    return mrender('buyer_ledger.html',
        buyer           = buyer,
        ledger          = ledger_data,
        closing_balance = closing_balance,
        start           = start,
        end             = end,
    )


@app.route('/buyers/<int:buyer_id>/ledger/pdf')
@login_required
def buyer_ledger_pdf(buyer_id):
    buyer = db.get_by_id('buyers', buyer_id)
    if not buyer:
        flash('Buyer not found.', 'danger')
        return redirect(url_for('buyers'))

    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end   = request.args.get('end',   datetime.now().strftime('%Y-%m-%d'))

    page_size   = request.args.get('size', 'A4').upper()
    ledger_data, _ = db.get_buyer_ledger(buyer_id, start, end)
    settings  = load_settings()
    pdf_bytes = pdf_generator.create_ledger_pdf(
        dict(buyer), ledger_data, start, end, settings, page_size=page_size
    )
    safe_name = "".join(c for c in buyer['name'] if c.isalnum() or c in ' _').strip()
    return pdf_generator.get_pdf_response(pdf_bytes, f"Ledger_{safe_name}_{page_size}.pdf")


@app.route('/buyers/<int:buyer_id>/payment', methods=['POST'])
@login_required
def add_buyer_payment(buyer_id):
    buyer = db.get_by_id('buyers', buyer_id)
    if not buyer:
        return jsonify({'success': False, 'error': 'Buyer not found'})

    f = request.form
    try:
        amount = float(f.get('amount', 0))
        if amount <= 0:
            flash('Payment amount must be greater than 0.', 'danger')
            return redirect(url_for('buyer_ledger', buyer_id=buyer_id))

        db.add_customer_payment({
            'buyer_id'    : buyer_id,
            'payment_date': f.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
            'amount'      : amount,
            'payment_mode': f.get('payment_mode', 'Cash'),
            'notes'       : f.get('notes', ''),
        })
        flash(f'Payment of ₹{amount:,.2f} recorded for {buyer["name"]}.', 'success')
    except ValueError:
        flash('Invalid amount entered.', 'danger')

    return redirect(url_for('buyer_ledger', buyer_id=buyer_id,
                             start=f.get('start'), end=f.get('end')))


# ─────────────────────────────────────────────
#  VENDORS  (Admin only)
# ─────────────────────────────────────────────
@app.route('/vendors')
@admin_required
def vendors():
    search = request.args.get('search', '')
    vendor_list = db.get_all('vendors')
    if search:
        vendor_list = [v for v in vendor_list if search.lower() in v['name'].lower()]
    return mrender('vendors.html', vendors=vendor_list, search=search)


@app.route('/vendors/add', methods=['GET', 'POST'])
@admin_required
def add_vendor():
    if request.method == 'POST':
        f = request.form
        result = db.add_record('vendors', {
            'name'   : f.get('name', '').strip(),
            'gstin'  : f.get('gstin', ''),
            'address': f.get('address', ''),
            'phone'  : f.get('phone', ''),
            'email'  : f.get('email', ''),
        })
        flash('Vendor added!' if result else 'Vendor name already exists.', 'success' if result else 'danger')
        return redirect(url_for('vendors'))
    return mrender('vendor_form.html', vendor=None, action='Add')


@app.route('/vendors/<int:vendor_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_vendor(vendor_id):
    vendor = db.get_by_id('vendors', vendor_id)
    if not vendor:
        flash('Vendor not found.', 'danger')
        return redirect(url_for('vendors'))

    if request.method == 'POST':
        f = request.form
        db.update_record('vendors', vendor_id, {
            'name'   : f.get('name', vendor['name']),
            'gstin'  : f.get('gstin', ''),
            'address': f.get('address', ''),
            'phone'  : f.get('phone', ''),
            'email'  : f.get('email', ''),
        })
        flash('Vendor updated!', 'success')
        return redirect(url_for('vendors'))

    return mrender('vendor_form.html', vendor=vendor, action='Edit')


@app.route('/vendors/<int:vendor_id>/delete', methods=['POST'])
@admin_required
def delete_vendor(vendor_id):
    vendor = db.get_by_id('vendors', vendor_id)
    if vendor:
        db.delete_record('vendors', vendor_id)
        flash(f'Vendor "{vendor["name"]}" deleted.', 'success')
    return redirect(url_for('vendors'))


# ─────────────────────────────────────────────
#  PURCHASES  (Admin only)
# ─────────────────────────────────────────────
@app.route('/purchases')
@admin_required
def purchases():
    purchase_list   = db.get_all_purchases_with_vendor()
    vendors         = db.get_all('vendors')
    expiring        = db.get_expiring_batches(days_ahead=30)
    settings        = load_settings()
    today_str       = datetime.now().strftime('%Y-%m-%d')
    return mrender('purchases.html',
                   purchases=purchase_list,
                   vendors=vendors,
                   expiring=expiring,
                   settings=settings,
                   today=today_str)


@app.route('/purchases/add', methods=['POST'])
@admin_required
def add_purchase():
    f = request.form
    try:
        vendor_id    = int(f.get('vendor_id', 0))
        purch_date   = f.get('purchase_date', datetime.now().strftime('%Y-%m-%d'))
        bill_no      = f.get('bill_no', '').strip()
        amount_paid  = float(f.get('amount_paid', 0))

        if vendor_id <= 0:
            flash('Please select a vendor.', 'danger')
            return redirect(url_for('purchases'))

        # ── Parse line items ──────────────────────────────────────
        descriptions  = f.getlist('description[]')
        product_ids   = f.getlist('product_id[]')
        quantities    = f.getlist('quantity[]')
        rates         = f.getlist('rate[]')
        gst_rates     = f.getlist('gst_rate[]')
        batch_nos     = f.getlist('batch_no[]')
        expiry_dates  = f.getlist('expiry_date[]')

        # Get company state to determine IGST/CGST
        settings      = load_settings()
        company_state = settings.get('company_info', {}).get('state', '').strip().lower()
        place_of_supply = f.get('place_of_supply', '').strip()
        is_igst       = (place_of_supply.strip().lower() != company_state) if place_of_supply else False
        reverse_charge = f.get('reverse_charge') == '1'

        items_data   = []
        total_taxable = 0.0
        total_cgst   = 0.0
        total_sgst   = 0.0
        total_igst   = 0.0

        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qty      = float(quantities[i]) if i < len(quantities) else 0
            rate     = float(rates[i])      if i < len(rates)      else 0
            gst_rate = float(gst_rates[i])  if i < len(gst_rates)  else 0
            if qty <= 0 or rate <= 0:
                continue

            taxable = round(qty * rate, 2)
            cgst    = round(taxable * gst_rate / 200, 2) if not is_igst else 0
            sgst    = round(taxable * gst_rate / 200, 2) if not is_igst else 0
            igst    = round(taxable * gst_rate / 100, 2) if is_igst     else 0

            total_taxable += taxable
            total_cgst    += cgst
            total_sgst    += sgst
            total_igst    += igst

            items_data.append({
                'product_id' : int(product_ids[i]) if i < len(product_ids) and product_ids[i].strip().isdigit() else None,
                'description': desc.strip(),
                'batch_no'   : batch_nos[i].strip()   if i < len(batch_nos)    else '',
                'expiry_date': expiry_dates[i].strip() if i < len(expiry_dates) else '',
                'quantity'   : qty,
                'rate'       : rate,
                'gst_rate'   : gst_rate,
                'is_igst'    : is_igst,
            })

        total_tax    = total_cgst + total_sgst + total_igst
        total_amount = round(total_taxable + total_tax, 2)

        purchase_data = {
            'vendor_id'     : vendor_id,
            'bill_no'       : bill_no,
            'purchase_date' : purch_date,
            'taxable_amount': round(total_taxable, 2),
            'gst_rate'      : 0,   # mixed rates — individual items have rates
            'cgst_amount'   : round(total_cgst, 2),
            'sgst_amount'   : round(total_sgst, 2),
            'igst_amount'   : round(total_igst, 2),
            'total_tax'     : round(total_tax, 2),
            'total_amount'  : total_amount,
            'amount_paid'   : amount_paid,
            'place_of_supply': place_of_supply,
            'reverse_charge' : reverse_charge,
            'notes'         : f.get('notes', ''),
            'purchase_type' : f.get('purchase_type', 'Resale'),  # Resale or Raw Material
        }

        if items_data:
            pid = db.save_purchase_with_items(purchase_data, items_data)
        else:
            # Fallback: old simple form (no items)
            manual_total = float(f.get('total_amount', total_amount))
            manual_gst   = float(f.get('gst_amount', 0))
            purchase_data['total_amount']  = manual_total
            purchase_data['total_tax']     = manual_gst
            pid = db.save_purchase_with_items(purchase_data, [])

        if pid:
            if amount_paid > 0:
                db.add_purchase_payment(pid, {
                    'payment_date': purch_date,
                    'amount'      : amount_paid,
                    'payment_mode': f.get('payment_mode', 'Cash'),
                    'reference_no': f.get('ref_no', ''),
                })
            flash('Purchase bill saved with GST details!', 'success')
        else:
            flash('Failed to save purchase bill.', 'danger')

    except (ValueError, IndexError) as e:
        flash(f'Invalid data in form: {e}', 'danger')

    return redirect(url_for('purchases'))



@app.route('/purchases/new')
@admin_required
def new_purchase():
    """Full-page form to add a new purchase bill."""
    vendors  = db.get_all('vendors')
    products = db.get_all('products')
    settings = load_settings()
    today_str = datetime.now().strftime('%Y-%m-%d')
    return mrender('purchase_form.html',
                   purchase=None, items=[],
                   vendors=vendors, products=products,
                   settings=settings, today=today_str,
                   action='New')


@app.route('/purchases/<int:purchase_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_purchase(purchase_id):
    """Full-page form to edit an existing purchase bill."""
    purchase = db.get_purchase_with_vendor(purchase_id)
    if not purchase:
        flash('Purchase bill not found.', 'danger')
        return redirect(url_for('purchases'))

    if request.method == 'POST':
        f = request.form
        try:
            vendor_id   = int(f.get('vendor_id', purchase['vendor_id']))
            purch_date  = f.get('purchase_date', purchase['purchase_date'])
            bill_no     = f.get('bill_no', '').strip()

            settings_d    = load_settings()
            company_state = settings_d.get('company_info', {}).get('state', '').strip().lower()
            place_of_supply = f.get('place_of_supply', '').strip()
            is_igst = (place_of_supply.strip().lower() != company_state) if place_of_supply else False
            reverse_charge = f.get('reverse_charge') == '1'
            purchase_type  = f.get('purchase_type', 'Resale')

            descriptions = f.getlist('description[]')
            product_ids  = f.getlist('product_id[]')
            quantities   = f.getlist('quantity[]')
            rates        = f.getlist('rate[]')
            gst_rates    = f.getlist('gst_rate[]')
            batch_nos    = f.getlist('batch_no[]')
            expiry_dates = f.getlist('expiry_date[]')

            items_data    = []
            total_taxable = total_cgst = total_sgst = total_igst = 0.0

            for i, desc in enumerate(descriptions):
                if not desc.strip(): continue
                qty  = float(quantities[i]) if i < len(quantities) else 0
                rate = float(rates[i])      if i < len(rates)      else 0
                gst  = float(gst_rates[i])  if i < len(gst_rates)  else 0
                if qty <= 0 or rate <= 0: continue

                taxable = round(qty * rate, 2)
                cgst = round(taxable * gst / 200, 2) if not is_igst else 0
                sgst = round(taxable * gst / 200, 2) if not is_igst else 0
                igst = round(taxable * gst / 100, 2) if is_igst     else 0

                total_taxable += taxable
                total_cgst += cgst; total_sgst += sgst; total_igst += igst

                items_data.append({
                    'product_id'   : int(product_ids[i]) if i < len(product_ids) and product_ids[i].strip().isdigit() else None,
                    'description'  : desc.strip(),
                    'batch_no'     : batch_nos[i].strip()    if i < len(batch_nos)    else '',
                    'expiry_date'  : expiry_dates[i].strip() if i < len(expiry_dates) else '',
                    'quantity'     : qty, 'rate': rate, 'gst_rate': gst,
                    'purchase_type': purchase_type,
                })

            total_tax    = round(total_cgst + total_sgst + total_igst, 2)
            total_amount = round(total_taxable + total_tax, 2)
            amount_paid  = float(f.get('amount_paid', purchase.get('amount_paid', 0)) or 0)

            upd = {
                'vendor_id'      : vendor_id,
                'bill_no'        : bill_no,
                'purchase_date'  : purch_date,
                'taxable_amount' : round(total_taxable, 2),
                'cgst_amount'    : round(total_cgst, 2),
                'sgst_amount'    : round(total_sgst, 2),
                'igst_amount'    : round(total_igst, 2),
                'total_tax'      : total_tax,
                'total_amount'   : total_amount,
                'amount_paid'    : amount_paid,
                'place_of_supply': place_of_supply,
                'reverse_charge' : reverse_charge,
                'notes'          : f.get('notes', ''),
                'purchase_type'  : purchase_type,
            }

            db.update_purchase_header(purchase_id, upd)
            db.delete_purchase_items(purchase_id)
            for item in items_data:
                db.save_purchase_item(purchase_id, item, is_igst)

            flash('Purchase bill updated successfully!', 'success')
            return redirect(url_for('purchases'))

        except (ValueError, IndexError) as e:
            flash(f'Error updating purchase: {e}', 'danger')

    vendors  = db.get_all('vendors')
    products = db.get_all('products')
    items    = db.get_purchase_items(purchase_id)
    settings = load_settings()
    today_str = datetime.now().strftime('%Y-%m-%d')
    return mrender('purchase_form.html',
                   purchase=purchase, items=items,
                   vendors=vendors, products=products,
                   settings=settings, today=today_str,
                   action='Edit')


@app.route('/purchases/<int:purchase_id>/payment', methods=['POST'])
@admin_required
def add_purchase_payment(purchase_id):
    purchase = db.get_purchase_details(purchase_id)
    if not purchase:
        flash('Purchase not found.', 'danger')
        return redirect(url_for('purchases'))

    f = request.form
    due_amount = purchase['total_amount'] - purchase['amount_paid']

    try:
        pay_amount = float(f.get('amount', 0))
        if pay_amount <= 0 or pay_amount > due_amount:
            flash(f'Payment amount must be between ₹0 and ₹{due_amount:.2f}', 'danger')
            return redirect(url_for('purchases'))

        success = db.add_purchase_payment(purchase_id, {
            'payment_date': f.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
            'amount'      : pay_amount,
            'payment_mode': f.get('payment_mode', 'Cash'),
            'reference_no': f.get('reference_no', ''),
        })
        flash('Payment recorded!' if success else 'Failed to record payment.', 'success' if success else 'danger')
    except ValueError:
        flash('Invalid amount.', 'danger')

    return redirect(url_for('purchases'))


@app.route('/purchases/<int:purchase_id>/payments-json')
@admin_required
def purchase_payments_json(purchase_id):
    """JSON API — payment history for a purchase (for modal popup)."""
    payments = db.get_purchase_payments(purchase_id)
    purchase = db.get_purchase_details(purchase_id)
    return jsonify({
        'purchase': dict(purchase) if purchase else {},
        'payments': payments,
    })


# ─────────────────────────────────────────────
#  SETTINGS  (Admin only)
# ─────────────────────────────────────────────
@app.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        f    = request.form
        data = load_settings()

        data['company_info'] = {
            'name'        : f.get('name', ''),
            'gstin'       : f.get('gstin', ''),
            'pan'         : f.get('pan', ''),
            'address_line1': f.get('address_line1', ''),
            'address_line2': f.get('address_line2', ''),
            'state'       : f.get('state', ''),
            'phone'       : f.get('phone', ''),
            'email'       : f.get('email', ''),
            'website'     : f.get('website', ''),
            'logo_path'   : data.get('company_info', {}).get('logo_path', ''),  # keep existing
        }
        data['bank_details'] = {
            'bank_name' : f.get('bank_name', ''),
            'account_no': f.get('account_no', ''),
            'ifsc_code' : f.get('ifsc_code', ''),
            'branch'    : f.get('branch', ''),
        }
        data['invoice_settings'] = {
            'invoice_prefix'     : f.get('invoice_prefix', 'INV-'),
            'terms_and_conditions': f.get('terms_and_conditions', ''),
        }
        data['upi'] = {
            'upi_id'   : f.get('upi_id', '').strip(),
            'upi_name' : f.get('upi_name', '').strip(),
        }

        save_settings(data)
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))

    current = load_settings()
    return mrender('settings.html', settings=current)


@app.route('/settings/upload-logo', methods=['POST'])
@admin_required
def upload_logo():
    if 'logo' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('settings'))

    file = request.files['logo']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('settings'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        logo_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(logo_path)

        # Update settings with new logo path
        data = load_settings()
        data.setdefault('company_info', {})['logo_path'] = logo_path
        save_settings(data)

        flash('Logo uploaded successfully!', 'success')
    else:
        flash('Invalid file type. Only PNG, JPG allowed.', 'danger')

    return redirect(url_for('settings'))


# ─────────────────────────────────────────────
#  USER MANAGEMENT  (Admin only)
# ─────────────────────────────────────────────
@app.route('/settings/users')
@admin_required
def manage_users():
    users = db.get_all_users()
    return mrender('users.html', users=users)


@app.route('/settings/users/add', methods=['POST'])
@admin_required
def add_user():
    f        = request.form
    username = f.get('username', '').strip()
    password = f.get('password', '').strip()
    role     = f.get('role', 'Cashier')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('manage_users'))

    result = db.add_user(username, password, role)
    flash('User added successfully!' if result else 'Username already exists.', 'success' if result else 'danger')
    return redirect(url_for('manage_users'))


@app.route('/settings/users/<int:user_id>/change-password', methods=['POST'])
@admin_required
def change_user_password(user_id):
    user        = db.get_by_id('users', user_id)
    new_pass    = request.form.get('new_password', '').strip()
    confirm     = request.form.get('confirm_password', '').strip()

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_users'))
    if len(new_pass) < 4:
        flash('Password must be at least 4 characters.', 'danger')
        return redirect(url_for('manage_users'))
    if new_pass != confirm:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('manage_users'))

    success = db.change_password(user['username'], new_pass)
    if success:
        flash(f'Password for "{user["username"]}" changed successfully!', 'success')
    else:
        flash('Failed to change password.', 'danger')
    return redirect(url_for('manage_users'))


@app.route('/settings/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db.get_by_id('users', user_id)
    if user:
        if user.get('username') == 'admin':
            flash('Cannot delete the main admin account.', 'danger')
        else:
            db.delete_user(user_id)
            flash(f'User "{user["username"]}" deleted.', 'success')
    return redirect(url_for('manage_users'))


# ─────────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return mrender('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return mrender('500.html'), 500


# ─────────────────────────────────────────────
#  BATCH TRACKING
# ─────────────────────────────────────────────
@app.route('/batches')
@login_required
def batch_list():
    """All active batches with balance and expiry status."""
    batches        = db.get_batches_for_product(include_expired=False)
    expiring       = db.get_expiring_batches(days_ahead=30)
    all_batches    = db.get_batches_for_product(include_expired=True)
    return mrender('batches.html',
                   batches=batches,
                   expiring=expiring,
                   all_batches=all_batches)


@app.route('/batches/history')
@login_required
def batch_history():
    """Full movement history for a batch."""
    product_id = request.args.get('product_id', type=int)
    batch_no   = request.args.get('batch_no', '')
    history    = db.get_batch_history(product_id=product_id, batch_no=batch_no)
    return mrender('batch_history.html',
                   history=history,
                   batch_no=batch_no,
                   product_id=product_id)


@app.route('/purchases/<int:purchase_id>/items')
@login_required
def purchase_items_view(purchase_id):
    """View line items for a purchase bill (JSON)."""
    items = db.get_purchase_items(purchase_id)
    return jsonify([dict(i) for i in items])


# ─────────────────────────────────────────────
#  REPORTS
# ─────────────────────────────────────────────
@app.route('/reports')
@login_required
def reports():
    return mrender('reports.html')


@app.route('/reports/stock')
@login_required
def stock_report():
    start = request.args.get('start', '')
    end   = request.args.get('end', '')
    fmt   = request.args.get('format', 'pdf')   # pdf or excel

    if not start or not end:
        flash('Please provide start and end dates.', 'danger')
        return redirect(url_for('reports'))

    data = db.get_stock_report(start, end)

    if fmt == 'excel':
        from flask import send_file
        xlsx_bytes = rg.create_stock_report_excel(data, start, end)
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Stock_Report_{start}_to_{end}.xlsx'
        )
    else:
        from flask import send_file
        pdf_bytes = rg.create_stock_report_pdf(data, start, end)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Stock_Report_{start}_to_{end}.pdf'
        )


@app.route('/reports/gstr1')
@login_required
def gstr1_report():
    start = request.args.get('start', '')
    end   = request.args.get('end', '')
    fmt   = request.args.get('format', 'pdf')

    if not start or not end:
        flash('Please provide start and end dates.', 'danger')
        return redirect(url_for('reports'))

    data = db.get_gstr1_data(start, end)

    if fmt == 'excel':
        from flask import send_file
        xlsx_bytes = rg.create_gstr1_excel(data)
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'GSTR1_{start}_to_{end}.xlsx'
        )
    else:
        from flask import send_file
        pdf_bytes = rg.create_gstr1_pdf(data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'GSTR1_{start}_to_{end}.pdf'
        )


@app.route('/reports/gstr3b')
@login_required
def gstr3b_report():
    start = request.args.get('start', '')
    end   = request.args.get('end', '')
    fmt   = request.args.get('format', 'pdf')

    if not start or not end:
        flash('Please provide start and end dates.', 'danger')
        return redirect(url_for('reports'))

    data     = db.get_gstr3b_data(start, end)
    itc_data = db.get_purchase_itc_summary(start, end)
    data['itc'] = itc_data

    if fmt == 'excel':
        from flask import send_file
        xlsx_bytes = rg.create_gstr3b_excel(data)
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'GSTR3B_{start}_to_{end}.xlsx'
        )
    else:
        from flask import send_file
        pdf_bytes = rg.create_gstr3b_pdf(data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'GSTR3B_{start}_to_{end}.pdf'
        )


@app.route('/reports/gstr2b')
@login_required
def gstr2b_report():
    start = request.args.get('start', '')
    end   = request.args.get('end', '')
    fmt   = request.args.get('format', 'pdf')

    if not start or not end:
        flash('Please provide start and end dates.', 'danger')
        return redirect(url_for('reports'))

    try:
        data = db.get_gstr2b_data(start, end)

        if fmt == 'excel':
            from flask import send_file
            xlsx_bytes = rg.create_gstr2b_excel(data)
            return send_file(
                io.BytesIO(xlsx_bytes),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'Purchase_Register_{start}_to_{end}.xlsx'
            )
        else:
            from flask import send_file
            pdf_bytes = rg.create_gstr2b_pdf(data)
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'Purchase_Register_{start}_to_{end}.pdf'
            )
    except Exception as e:
        app.logger.error(f"GSTR-2B report error: {e}", exc_info=True)
        flash(f'Report generation error: {e}', 'danger')
        return redirect(url_for('reports'))


# ─────────────────────────────────────────────
#  ENTRY POINT

# ══════════════════════════════════════════════════════════════
#  PROFORMA INVOICE / SALES QUOTATION ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/proforma')
@login_required
def proforma_list():
    """List all proforma invoices / sales quotations."""
    proformas = db.get_all_proformas()
    today_str = datetime.now().strftime('%Y-%m-%d')
    return mrender('proforma_list.html', proformas=proformas, today=today_str)


@app.route('/proforma/new', methods=['GET','POST'])
@login_required
def new_proforma():
    """Create a new proforma invoice / sales quotation."""
    if request.method == 'POST':
        f = request.form
        settings_d    = load_settings()
        company_state = settings_d.get('company_info',{}).get('state','').strip().lower()
        buyer_state   = f.get('buyer_state','').strip()
        is_igst       = buyer_state.strip().lower() != company_state if buyer_state else False

        # Parse line items
        descs   = f.getlist('description[]')
        pids    = f.getlist('product_id[]')
        hsns    = f.getlist('hsn[]')
        qtys    = f.getlist('quantity[]')
        rates   = f.getlist('rate[]')
        gst_rs  = f.getlist('gst_rate[]')
        units   = f.getlist('unit[]')
        discs   = f.getlist('discount[]')

        items        = []
        subtotal     = 0.0
        total_disc   = 0.0
        total_cgst = total_sgst = total_igst = 0.0

        for i, desc in enumerate(descs):
            if not desc.strip(): continue
            qty  = float(qtys[i])  if i < len(qtys)  else 0
            rate = float(rates[i]) if i < len(rates)  else 0
            gst  = float(gst_rs[i])if i < len(gst_rs) else 0
            disc = float(discs[i]) if i < len(discs)  else 0
            if qty <= 0: continue

            gross    = round(qty * rate, 2)
            disc_amt = round(gross * disc / 100, 2)
            amount   = round(gross - disc_amt, 2)
            cgst = round(amount * gst / 200, 2) if not is_igst else 0
            sgst = round(amount * gst / 200, 2) if not is_igst else 0
            igst = round(amount * gst / 100, 2) if is_igst     else 0

            subtotal   += gross
            total_disc += disc_amt
            total_cgst += cgst; total_sgst += sgst; total_igst += igst

            items.append({
                'product_id'     : int(pids[i]) if i < len(pids) and pids[i].strip().isdigit() else None,
                'description'    : desc.strip(),
                'hsn'            : hsns[i].strip() if i < len(hsns) else '',
                'quantity'       : qty, 'unit': units[i] if i < len(units) else '',
                'rate'           : rate, 'gst_rate': gst,
                'discount_percent': disc, 'amount': amount,
            })

        taxable   = round(subtotal - total_disc, 2)
        total_gst = round(total_cgst + total_sgst + total_igst, 2)
        freight   = float(f.get('freight', 0) or 0)
        grand     = round(taxable + total_gst + freight, 2)

        data = {
            'quotation_no'  : db.get_next_quotation_number(),
            'quotation_date': f.get('quotation_date', datetime.now().strftime('%Y-%m-%d')),
            'valid_until'   : f.get('valid_until', ''),
            'buyer_id'      : int(f.get('buyer_id') or 0) or None,
            'buyer_name'    : f.get('buyer_name',''),
            'buyer_address' : f.get('buyer_address',''),
            'buyer_gstin'   : f.get('buyer_gstin',''),
            'buyer_state'   : buyer_state,
            'buyer_phone'   : f.get('buyer_phone',''),
            'payment_mode'  : 'Advance',
            'order_ref'     : f.get('order_ref',''),
            'subtotal'      : round(subtotal,2),
            'total_discount': round(total_disc,2),
            'taxable_value' : taxable,
            'total_gst'     : total_gst,
            'total_cgst'    : round(total_cgst,2),
            'total_sgst'    : round(total_sgst,2),
            'total_igst'    : round(total_igst,2),
            'freight'       : freight,
            'round_off'     : 0,
            'grand_total'   : grand,
            'notes'         : f.get('notes',''),
        }

        pid = db.save_proforma(data, items)
        if pid:
            flash(f"Quotation {data['quotation_no']} saved!", 'success')
            return redirect(url_for('proforma_detail', proforma_id=pid))
        else:
            flash('Failed to save quotation.', 'danger')

    # GET
    buyers   = db.get_all('buyers')
    products = db.get_all('products')
    settings = load_settings()
    today_str= datetime.now().strftime('%Y-%m-%d')
    next_qno = db.get_next_quotation_number()
    return mrender('proforma_form.html',
                   buyers=buyers, products=products,
                   settings=settings, today=today_str,
                   next_qno=next_qno, proforma=None)


@app.route('/proforma/<int:proforma_id>')
@login_required
def proforma_detail(proforma_id):
    """View a proforma invoice detail."""
    proforma, items = db.get_proforma_detail(proforma_id)
    if not proforma:
        flash('Quotation not found.', 'danger')
        return redirect(url_for('proforma_list'))
    settings = load_settings()
    return mrender('proforma_detail.html', proforma=proforma, items=items, settings=settings)


@app.route('/proforma/<int:proforma_id>/pdf')
@login_required
def proforma_pdf(proforma_id):
    """Download proforma invoice as PDF. ?size=A4|A4L|A5|A5L"""
    proforma, items = db.get_proforma_detail(proforma_id)
    if not proforma:
        flash('Quotation not found.', 'danger')
        return redirect(url_for('proforma_list'))

    settings  = load_settings()
    page_size = request.args.get('size', 'A4').upper()

    # Build invoice_data-compatible dict for create_invoice_pdf
    inv_data = {
        'invoice_no'     : proforma['quotation_no'],
        'quotation_no'   : proforma['quotation_no'],
        'invoice_date'   : proforma['quotation_date'],
        'quotation_date' : proforma['quotation_date'],
        'valid_until'    : proforma.get('valid_until',''),
        'buyer_name'     : proforma.get('buyer_name',''),
        'buyer_address'  : proforma.get('buyer_address',''),
        'buyer_gstin'    : proforma.get('buyer_gstin',''),
        'buyer_state'    : proforma.get('buyer_state',''),
        'payment_mode'   : 'Advance',
        'order_ref'      : proforma.get('order_ref',''),
        'dispatch_info'  : '',
        'subtotal'       : proforma.get('subtotal',0),
        'total_discount' : proforma.get('total_discount',0),
        'taxable_value'  : proforma.get('taxable_value',0),
        'total_gst'      : proforma.get('total_gst',0),
        'total_cgst'     : proforma.get('total_cgst',0),
        'total_sgst'     : proforma.get('total_sgst',0),
        'total_igst'     : proforma.get('total_igst',0),
        'freight'        : proforma.get('freight',0),
        'round_off'      : proforma.get('round_off',0),
        'grand_total'    : proforma.get('grand_total',0),
    }
    # Convert proforma items to invoice-item format
    inv_items = []
    for it in items:
        inv_items.append({
            'description'     : it.get('description',''),
            'hsn'             : it.get('hsn',''),
            'gst_rate'        : it.get('gst_rate',0),
            'quantity'        : it.get('quantity',0),
            'unit'            : it.get('unit',''),
            'rate'            : it.get('rate',0),
            'discount_percent': it.get('discount_percent',0),
            'amount'          : it.get('amount',0),
        })

    pdf_bytes = pdf_generator.create_invoice_pdf(
        inv_data, inv_items, settings,
        previous_balance=0, paid_amount=0,
        save_to_disk=False,
        page_size=page_size,
        is_proforma=True
    )
    safe_name = "".join(c if c.isalnum() or c in ('-','_') else '_'
                        for c in proforma['quotation_no'])
    return pdf_generator.get_pdf_response(pdf_bytes, f"{safe_name}_{page_size}.pdf")


@app.route('/proforma/<int:proforma_id>/delete', methods=['POST'])
@admin_required
def delete_proforma(proforma_id):
    """Delete a proforma invoice."""
    if db.delete_proforma(proforma_id):
        flash('Quotation deleted.', 'success')
    else:
        flash('Failed to delete quotation.', 'danger')
    return redirect(url_for('proforma_list'))


@app.route('/proforma/<int:proforma_id>/convert', methods=['POST'])
@admin_required
def convert_proforma(proforma_id):
    """Convert a proforma to a regular Tax Invoice."""
    proforma, items = db.get_proforma_detail(proforma_id)
    if not proforma:
        flash('Quotation not found.', 'danger')
        return redirect(url_for('proforma_list'))

    settings_d    = load_settings()
    company_state = settings_d.get('company_info',{}).get('state','').strip().lower()
    buyer_state   = (proforma.get('buyer_state') or '').strip().lower()
    is_igst       = buyer_state != company_state if buyer_state else False

    # Build inv_data
    inv_data = {
        'invoice_no'     : db.get_next_invoice_number(),
        'invoice_date'   : datetime.now().strftime('%Y-%m-%d'),
        'buyer_id'       : proforma.get('buyer_id'),
        'payment_mode'   : request.form.get('payment_mode','Credit'),
        'order_ref'      : proforma.get('order_ref',''),
        'dispatch_info'  : '',
        'subtotal'       : proforma.get('subtotal',0),
        'total_discount' : proforma.get('total_discount',0),
        'taxable_value'  : proforma.get('taxable_value',0),
        'total_gst'      : proforma.get('total_gst',0),
        'total_cgst'     : proforma.get('total_cgst',0) if not is_igst else 0,
        'total_sgst'     : proforma.get('total_sgst',0) if not is_igst else 0,
        'total_igst'     : proforma.get('total_igst',0) if is_igst else 0,
        'freight'        : proforma.get('freight',0),
        'round_off'      : 0,
        'grand_total'    : proforma.get('grand_total',0),
        'paid_amount'    : float(request.form.get('paid_amount',0) or 0),
        'previous_balance': 0,
    }
    inv_items = []
    for it in items:
        inv_items.append({
            'product_id'      : it.get('product_id'),
            'description'     : it.get('description',''),
            'hsn'             : it.get('hsn',''),
            'gst_rate'        : it.get('gst_rate',0),
            'quantity'        : it.get('quantity',0),
            'unit'            : it.get('unit',''),
            'rate'            : it.get('rate',0),
            'discount_percent': it.get('discount_percent',0),
            'amount'          : it.get('amount',0),
        })

    new_id = db.save_invoice(inv_data, inv_items, company_state)
    if new_id:
        flash(f"Invoice {inv_data['invoice_no']} created from quotation!", 'success')
        return redirect(url_for('view_invoice', invoice_id=new_id))
    else:
        flash('Failed to convert quotation to invoice.', 'danger')
        return redirect(url_for('proforma_detail', proforma_id=proforma_id))


# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("  Professional Billing Web App — Starting...")
    print("  URL: http://localhost:5000")
    print("  Default Login → admin / admin123")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
