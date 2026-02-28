# 🧾 Professional Billing & Inventory Software

A complete GST-compliant billing and inventory management system built with **Python Flask + SQLite**. Works on both desktop and mobile browsers. Runs entirely on your local machine — no internet subscription, no cloud dependency.

---

## 📋 Table of Contents

- [Features Overview](#-features-overview)
- [Installation](#-installation)
- [Login & User Roles](#-login--user-roles)
- [Dashboard](#-dashboard)
- [Billing / Create Invoice](#-billing--create-invoice)
- [Invoice Management](#-invoice-management)
- [Products & Inventory](#-products--inventory)
- [Product Variations](#-product-variations-sizecolor)
- [Product Rate List](#-product-rate-list)
- [Buyers (Customers)](#-buyers-customers)
- [Buyer Ledger](#-buyer-ledger--khata)
- [Vendors (Suppliers)](#-vendors-suppliers)
- [Purchases](#-purchases)
- [Batch Tracking](#-batch--expiry-tracking)
- [GST Reports](#-gst-reports)
- [Settings](#-settings)
- [Mobile Interface](#-mobile-interface)
- [Database & File Structure](#-database--file-structure)
- [Tech Stack](#-tech-stack)

---

## ✨ Features Overview

| Category | Features |
|---|---|
| 🧾 **Billing** | GST invoices, Retail & Wholesale modes, Credit / Cash / UPI / Cheque / Bank Transfer |
| 📦 **Inventory** | Stock tracking, auto-deduction on sale, low-stock alerts, product variations |
| 🏷️ **Rate List** | Full price list with HSN, GST%, cost, selling price, MRP, stock — searchable |
| 👥 **Buyers** | Customer ledger, outstanding balance, payment collection, edit/delete entries |
| 🏭 **Vendors** | Supplier management, purchase bills, payment tracking |
| 🛒 **Purchases** | Full-page purchase form, Resale vs Raw Material type, purchase bill edit |
| 📦 **Batch Tracking** | Batch no. & expiry date per item, customer traceability, expiry alerts |
| 📊 **Reports** | GSTR-1, GSTR-2B (Purchase Register), GSTR-3B with ITC — PDF & Excel |
| 📱 **Mobile** | Full mobile UI, bottom navigation, touch-optimized autocomplete |
| 🔐 **Security** | Login required, role-based access (Admin / Cashier) |
| ⚙️ **Settings** | Company info, bank details, logo upload, GST number, UPI QR code |

---

## 🚀 Installation

### Requirements
- Python 3.8+
- pip

### Steps

```bash
# 1. Go to the project folder
cd billing-app

# 2. Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install flask reportlab openpyxl werkzeug

# 4. Start the app
python app.py

# 5. Open in browser
http://localhost:5000
```

> **Mobile access:** Find your PC's local IP and open `http://192.168.x.x:5000` on your phone (both on same Wi-Fi).

### Default Login
| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

> ⚠️ Change the default password immediately — Settings → Manage Users.

---

## 🔐 Login & User Roles

### Two Roles

#### 👑 Admin
- Full access to everything
- Add / delete users, cancel invoices, change settings
- Access all reports, purchases, batch tracking

#### 💼 Cashier
- Create invoices, view buyers, view products, view rate list
- Cannot cancel invoices, access settings, or manage users

### User Management
`Settings → Manage Users` → Add / Delete users. The `admin` account is protected.

---

## 📊 Dashboard

First page shown after login.

### KPI Cards
| Card | Description |
|---|---|
| **Today's Sales** | Total of all invoices created today |
| **Receivables** | Total outstanding amount across all buyers |
| **Est. Profit** | Estimated profit: (selling price − cost) × qty sold |
| **Low Stock** | Number of products below the stock threshold |

### Sales Chart
- Switch between **Week / Month / Year** tabs
- Bar chart powered by Chart.js

### Low Stock Alert Banner
- Appears when any product falls below the threshold
- Click "View →" to go directly to the products page

---

## 🧾 Billing / Create Invoice

Open via the `+` button (mobile FAB) or "New Invoice" on dashboard.

### 4-Step Wizard

#### Step 1 — Buyer
- Toggle **Retail / Wholesale** mode (rates switch automatically)
- Search existing buyers via autocomplete
- Buyer info card shows: GSTIN, State, GST type (IGST / CGST+SGST), outstanding balance
- **New buyer:** Click "➕ Add as new buyer" — saved automatically with invoice

#### Step 2 — Invoice Details
| Field | Notes |
|---|---|
| Invoice No. | Auto-generated, read-only |
| Invoice Date | Defaults to today |
| Payment Mode | Credit / Cash / UPI / Bank Transfer / Cheque |
| Order Reference | PO number (optional) |
| Dispatch Info | Lorry / courier (optional) |

#### Step 3 — Items
- Product search with instant autocomplete
- Selecting a product auto-fills: Rate, GST%, HSN Code, Unit, Batch dropdown
- **Batch dropdown** — shows available batches with stock quantity and expiry date
- Wholesale mode auto-uses wholesale price
- Discount % per item
- Add unlimited items per invoice

#### Step 4 — Review & Save
- Full summary with all line items
- CGST + SGST or IGST (based on buyer state vs company state)
- Freight / extra charges
- Paid at Billing → Balance Due → Previous Balance (outstanding)
- UPI QR code on PDF if UPI ID is configured in Settings

### GST Logic
| Scenario | Tax Applied |
|---|---|
| Buyer in same state as company | CGST + SGST (50/50 split) |
| Buyer in a different state | IGST (full rate) |

---

## 📄 Invoice Management

### Invoice List
- Filter by date range, search by invoice no. / buyer / payment mode
- Quick filter chips: All / Cash / UPI / Credit
- Stats strip: total invoices, total amount, total GST

### Invoice Detail
- Complete summary: buyer info, all line items, GST breakup
- Paid at Billing, Balance Due, Previous Balance, Total Outstanding
- Amount in words
- Batch number displayed per item (if recorded)

### Invoice Actions
| Action | Access |
|---|---|
| Download PDF | All users |
| View Buyer Ledger | All users |
| Cancel Invoice | Admin only |

### Cancelling an Invoice
- Stock is fully restored for all items
- Invoice prefixed with `[CANCELLED]`
- Cancelled invoices cannot be reprinted as PDF

---

## 📦 Products & Inventory

### Product Fields
| Field | Notes |
|---|---|
| Name | Must be unique |
| HSN Code | Required for GST compliance |
| GST % | Auto-applied in billing |
| Cost Price | Purchase price — used for profit estimation |
| Selling Price | Standard retail rate |
| Wholesale Price | Used in Wholesale billing mode |
| Stock Qty | Current available quantity |
| Unit | Pcs / Kg / Box / Litre / etc. |
| Batch No. | Optional — records which batch this opening stock belongs to |
| Expiry Date | Optional — triggers 30-day expiry alert |

### Automatic Stock Movement
| Event | Stock Change |
|---|---|
| Invoice saved | Deducted automatically |
| Purchase recorded (Resale type) | Added automatically |
| Invoice cancelled | Fully restored |
| Purchase (Raw Material type) | No stock change — expense only |
| Manual item entry in billing | No stock change |

### Low Stock Threshold
Edit `LOW_STOCK_THRESHOLD` in `database_manager.py` (default: 5).

---

## 🎨 Product Variations (Size/Color)

Products can have multiple **variations** (e.g. Small / Medium / Large, Red / Blue).

### Variation Fields
| Field | Notes |
|---|---|
| Variation Name | e.g. "Small", "Red", "500ml" |
| Selling Price | Can differ from main product |
| Wholesale Price | Optional |
| Cost Price | For profit tracking |
| Stock Qty | Tracked separately per variation |

### How It Works in Billing
- When you select a product that has variations, a second dropdown appears
- Selecting a variation auto-fills the variation-specific price and stock
- Stock deducted from the correct variation on invoice save
- Rate List page shows variations expandable under each product

### Managing Variations
`Products → [Product Name] → Manage Variations`

---

## 🏷️ Product Rate List

`Inventory → Rate List` — a read-only price list for customer reference.

### Columns
| Column | Description |
|---|---|
| # | Serial number |
| Product / Variation | Name with unit |
| HSN Code | GST classification code |
| Cost Price | Purchase / cost price |
| Rate (w/o GST) | Selling rate before tax |
| GST % | Color-coded badge (0%→grey, 5%→green, 12%→blue, 18%→orange, 28%→red) |
| Price (incl. GST) | Final price customer pays = Rate + GST |
| Stock | Current stock with LOW/OUT indicator |

### Features
- 🔍 **Live search** — type product name or HSN code, results appear after 400ms
- **Variation expand** — products with variations show a `▾ N` button; click to expand all variation rows
- When searching, all variations auto-expand
- Available to both Admin and Cashier roles
- Mobile-friendly (accessible via More → Rate List)

---

## 👥 Buyers (Customers)

### Buyer Fields
| Field | Notes |
|---|---|
| Name | Required |
| GSTIN | 15-character GST number |
| State | Determines IGST vs CGST/SGST |
| Address | Printed on invoice |
| Phone | Contact number |
| Opening Balance | Pre-existing outstanding when first added |

### Balance Tracking
- Dashboard "Receivables" = total across all buyers
- Invoice detail shows previous balance at time of billing
- Buyer list shows current balance per customer

---

## 📒 Buyer Ledger / Khata

`Buyers → [Select Buyer] → Ledger`

### What Shows in Ledger
| Row Type | Description |
|---|---|
| Opening Balance | Balance when buyer was first added |
| Invoice (Dr) | Each sale billed to the buyer |
| Payment (Cr) | Each payment received from the buyer |
| Running Balance | Updated after every row |

### Action Column (New)
Every ledger row now has an **Action** button:

**For Payment entries:**
- ✏️ **Edit** — opens a modal to change date, amount, payment mode, notes
- 🗑️ **Delete** — removes the payment entry (with confirmation)

**For Invoice entries:**
- 👁️ **View** — opens the full invoice detail

### Filtering
- Filter by custom date range
- Adjusts opening balance to include pre-period transactions

### Recording a Payment
From Ledger → "Receive Payment" panel:
- Enter amount, date, payment mode, optional notes
- Balance updates immediately

### Export
`Download PDF` → shareable account statement for the customer

---

## 🏭 Vendors (Suppliers)

### Vendor Fields
Name, GSTIN, Address, Phone, Email

### Features
- Add / Edit / Delete vendors
- View all purchases linked to a vendor
- Search vendor list

---

## 🛒 Purchases

`More → Purchases` — full GST-compliant purchase management.

### New Purchase Bill
Click **"New Purchase Bill"** button → opens a full-page form in a new tab.

#### Purchase Type (New)
| Type | Effect |
|---|---|
| 🛒 **Resale / Trading** | Item added to product inventory. Stock updated automatically. |
| 🏭 **Raw Material / Expense** | Only purchase record saved. Stock NOT updated. For materials, overhead, services. |

#### Purchase Form Fields
| Section | Fields |
|---|---|
| Supplier | Vendor dropdown |
| Bill Details | Bill No., Date, Place of Supply, Reverse Charge (RCM) |
| Items | Product search, Qty, Rate, GST%, Batch No., Expiry Date |
| GST Summary | Live Taxable, CGST/SGST/IGST, Total Tax, Grand Total |
| Payment | Amount Paid, Payment Mode |
| Notes | Internal remarks |

#### GST Auto-detection
- Select Place of Supply → system auto-detects IGST (inter-state) or CGST+SGST (intra-state)
- Color-coded banner shows which tax type applies

### Editing a Purchase Bill
Click **Edit** button on any purchase row → opens full-page edit form in new tab.
- All items are pre-loaded and editable
- Old items are replaced with new entries on save
- Handles Resale → stock recalculated

### GST Rates Available in Purchases
0%, 0.1%, 0.25%, 1%, 1.5%, 3%, 5%, 6%, 7.5%, 9%, 12%, 14%, 18%, 28%

Product selection auto-fills the exact GST rate from product master.

### Payment Tracking
- Record partial/full payment at time of entry
- Add more payments later: `Purchases → [Bill] → Pay`
- Status auto-updates: Unpaid → Partial → Paid

### Stock Impact
- Resale purchases → product `stock_qty` increases
- Cost price updated via WAC: `New Cost = (Old Stock × Old Cost + New Qty × New Cost) ÷ Total Stock`
- Raw Material purchases → no stock change, expense-only record

---

## 📦 Batch / Expiry Tracking

Full batch traceability from purchase to sale.

### Recording Batches in Purchases
When adding a purchase item → fill **Batch No.** and **Expiry Date**.
- Each batch is tracked with quantity IN from purchase
- Multiple batches can exist for the same product

### Selecting Batches in Billing
When adding a product in billing → **Batch dropdown** appears:
- Shows all available batches with: `Batch No (Qty: X | Exp: YYYY-MM-DD)`
- Expired batches show ⚠️ EXPIRED in red
- Valid batches show ✓ Exp: date in green
- Auto-selects if only one batch available
- Sale records quantity OUT from that specific batch

### Batch List Page
`More → Batch Tracker` — all batches with:
- Product name, Batch No., Expiry Date, Qty In, Qty Out, Balance
- 🔴 Expired batches highlighted
- 🟡 Expiring within 30 days highlighted

### Expiry Alert Banner
Appears at top of Purchases page when any batch is expiring within 30 days.

### Opening Stock Batches
When adding/editing a product → fill Batch No. and Expiry Date in the stock section.
Batch tracking entry is automatically created.

---

## 📊 GST Reports

`More → Reports` — all reports need a date range selection.

### Report 1 — GSTR-1 (Sales Register)
Outward supplies — for filing GST returns.
- Rate-wise breakup (5%, 12%, 18%, 28%)
- CGST, SGST, IGST, Taxable, Grand Total
- Available as **PDF** and **Excel**

### Report 2 — Purchase Register (GSTR-2B Style)
Inward supplies — ITC reconciliation.
- One row per purchase bill
- Supplier name, GSTIN, Bill No., Date, Place of Supply, RCM flag
- Taxable, CGST, SGST, IGST, Total Tax
- Summary totals at top
- Available as **PDF** and **Excel**

### Report 3 — GSTR-3B Summary
Monthly GST summary report.
- **Section 3.1** — Outward Taxable Supplies (rate-wise: 5%, 12%, 18%, 28%)
- **Section 4** — ITC (Input Tax Credit) from purchases
  - Eligible ITC (normal purchases)
  - RCM ITC (reverse charge purchases)
- **Net Tax Payable** = Output Tax − ITC
- Available as **PDF** and **Excel**

### Report 4 — Stock Report
Current inventory snapshot.
- Product name, HSN, Unit, Cost Price, Selling Price, Stock Qty, Stock Value
- Low-stock items highlighted in red
- Available as **PDF** and **Excel**

---

## ⚙️ Settings

`More → Settings` (Admin only).

### Company Information
| Field | Where It Appears |
|---|---|
| Company Name | Invoice header |
| Address | Invoice header |
| Phone / Email | Invoice footer |
| GSTIN | Invoice header |
| State | Controls IGST vs CGST/SGST for all invoices |
| Logo | Top-left corner of every invoice PDF |

### Bank Details
Printed at bottom of every invoice:
Bank Name, Account Number, IFSC Code, Account Holder Name

### UPI QR Code
Enter your UPI ID in settings → a QR code is printed on every invoice PDF for instant payment by customers.

### Logo Upload
Accepts JPG, PNG, GIF. Replaces the previous logo.

### User Management
- View all users with roles
- Add new user (username + password + role)
- Delete users (`admin` account is protected)

---

## 📱 Mobile Interface

Open the app on any mobile browser — mobile layout loads automatically.

### Bottom Navigation (5 tabs)
| Tab | Pages |
|---|---|
| 🏠 Home | Dashboard |
| 📄 Bills | Invoice list and detail |
| ➕ (FAB) | Create new invoice |
| 👥 Buyers | Buyer list and ledger |
| ⋯ More | All other sections |

### More Menu (Slide-up Sheet)
**Inventory:** Products, Rate List, Vendors, Purchases, Batch Tracker

**Reports:** Invoices, Buyer Ledger, PDF Report

**Admin** *(Admin only):* Settings, Manage Users, Logout

### Mobile Billing Features
- Touch-safe autocomplete
- 4-step wizard with sticky progress tabs
- Buyer info card with GST type badge
- Batch selection dropdown in item rows
- New buyer form embedded in billing wizard
- All totals update in real time

---

## 🗄️ Database & File Structure

### Project Layout
```
billing-app/
│
├── app.py                    # Flask application and all routes
├── database_manager.py       # All database functions
├── reports_generator.py      # GSTR-1, GSTR-2B, GSTR-3B, Stock report (PDF + Excel)
├── settings.json             # Company settings (auto-created)
├── billing.db                # SQLite database (your data)
│
├── uploads/                  # Uploaded logo files
├── pdfs/                     # Auto-saved invoice PDFs
│
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── billing.html
    ├── invoices.html
    ├── invoice_detail.html
    ├── products.html
    ├── product_form.html         # Add/Edit product (with batch fields)
    ├── product_variations.html   # Manage variations
    ├── product_rate_list.html    # ★ NEW — Price list with variations
    ├── buyers.html
    ├── buyer_ledger.html         # ★ UPDATED — Edit/delete payment entries
    ├── vendors.html
    ├── purchases.html
    ├── purchase_form.html        # ★ NEW — Full-page add/edit purchase
    ├── batches.html
    ├── batch_history.html
    ├── reports.html
    ├── settings.html
    ├── login.html
    │
    └── mobile/
        ├── base_mobile.html
        ├── billing.html
        ├── products.html
        ├── product_form.html
        ├── purchases.html
        ├── buyer_ledger.html
        ├── batches.html
        └── ...
```

### Database Tables
| Table | Contents |
|---|---|
| `users` | Login credentials and roles |
| `buyers` | Customer profiles and opening balances |
| `vendors` | Supplier profiles |
| `products` | Product catalogue, stock, prices |
| `product_variations` | Size/color/type variants with own price & stock |
| `invoices` | Invoice headers (totals, paid amount, previous balance) |
| `invoice_items` | Line items per invoice (with batch_no field) |
| `customer_payments` | Payment receipts from buyers (editable/deletable) |
| `purchases` | Purchase bills (with purchase_type: Resale / Raw Material) |
| `purchase_items` | Line items per purchase bill |
| `purchase_payments` | Payments made to vendors |
| `batch_tracking` | Batch IN (purchase) and OUT (sale) movements |

### Backup
The entire database is a single file — `billing.db`. Copy it to back up all data. To restore, replace the file and restart the app.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3 + Flask |
| Database | SQLite (file-based, no server needed) |
| PDF Generation | ReportLab |
| Excel Generation | openpyxl |
| Desktop Frontend | HTML + Bootstrap 5 + Jinja2 |
| Mobile Frontend | Custom CSS (no Bootstrap dependency) |
| Charts | Chart.js 4.4.1 (CDN) |
| Icons | Bootstrap Icons (CDN) |
| Password Security | Werkzeug password hashing |
| Mobile Detection | User-Agent detection in Flask |

---

## ⚠️ Important Notes

1. **First run:** Default password is `admin123` — change it immediately via Settings → Manage Users
2. **Company State:** Set this in Settings before creating invoices — incorrect state gives wrong IGST/CGST
3. **Purchase Type:** Use "Resale" for goods you resell (stock increases). Use "Raw Material" for expenses, services, overhead (stock unchanged)
4. **Batch Tracking:** Optional. If you don't enter a batch number, it's skipped — no compulsion
5. **Low stock threshold:** Edit `LOW_STOCK_THRESHOLD` in `database_manager.py` (default: 5)
6. **Internet required for:** Chart.js and Bootstrap Icons (CDN) — charts and icons won't display offline
7. **Change port:** Edit last line of `app.py`: `app.run(port=5000)` → replace `5000` with any free port
8. **Manual product entry in billing:** Typing a name without autocomplete creates the line item but does NOT affect stock
9. **PDF storage:** All PDFs saved in `pdfs/` folder — back this up along with `billing.db`
10. **GST report dates:** Always select the correct month when downloading GSTR reports — data is strictly date-filtered

---

## 🐛 Known Limitations

- No built-i- [Purchases](#-purchases)
- [Reports & PDF Export](#-reports--pdf-export)
- [Settings](#-settings)
- [Mobile Interface](#-mobile-interface)
- [Database & File Structure](#-database--file-structure)
- [Tech Stack](#-tech-stack)

---

## ✨ Features Overview

| Category | Features |
|---|---|
| 🧾 Billing | GST invoices, Retail & Wholesale modes, Credit / Cash / UPI / Cheque / Bank Transfer |
| 📦 Inventory | Stock tracking, auto-deduction on sale, low-stock alerts |
| 👥 Buyers | Customer ledger, outstanding balance, payment collection |
| 🏭 Vendors | Supplier management, purchase bills, payment tracking |
| 📊 Reports | Sales chart, summary PDF, detailed PDF, buyer ledger PDF |
| 📱 Mobile | Full mobile UI, bottom navigation, touch-optimized autocomplete |
| 🔐 Security | Login required, role-based access (Admin / Cashier) |
| ⚙️ Settings | Company info, bank details, logo upload, GST number, user management |

---

## 🚀 Installation

### Requirements
- Python 3.8+
- pip

### Steps

```bash
# 1. Go to the project folder
cd billing-app

# 2. Install dependencies
pip install flask reportlab werkzeug

# 3. Start the app
python app.py

# 4. Open in browser
http://localhost:5000
```

> **Mobile access:** Find your PC's local IP address and open `http://192.168.x.x:5000` on your phone (both devices must be on the same Wi-Fi).

### Default Login
| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

> ⚠️ Change the default password immediately after first login — Settings → Manage Users.

---

## 🔐 Login & User Roles

### Two Roles

#### 👑 Admin
- Full access to everything
- Add and delete users
- Cancel invoices
- Change settings
- Delete products

#### 💼 Cashier
- Create invoices, view buyers, view products
- Cannot cancel invoices
- Cannot access settings
- Cannot manage users

### User Management
Go to `Settings → Manage Users`:
- Add new users (username + password + role)
- Delete existing users
- The `admin` account cannot be deleted

---

## 📊 Dashboard

First page shown after login.

### KPI Cards
| Card | Description |
|---|---|
| **Today's Sales** | Total of all invoices created today |
| **Receivables** | Total outstanding amount across all buyers |
| **Est. Profit** | Estimated profit: (selling price − cost) × qty sold |
| **Low Stock** | Number of products below the stock threshold |

### Sales Chart
- Switch between **Week / Month / Year** tabs
- Bar chart powered by Chart.js
- Loads automatically on page open

### Low Stock Alert Banner
- Appears when any product falls below the threshold
- Click "View →" to go directly to the products page

### Quick Actions
Direct links from dashboard: New Invoice, Buyers, Invoices, Stock.

---

## 🧾 Billing / Create Invoice

Open via the `+` button (centre of bottom nav on mobile) or "New Invoice" on dashboard.

### 4-Step Wizard

#### Step 1 — Buyer
- Toggle **Retail / Wholesale** mode (rates switch automatically on all rows)
- Type a buyer name to search from existing buyers
- After selecting, an info card shows:
  - Address, GSTIN, State
  - GST type: **IGST** (inter-state) or **CGST + SGST** (intra-state)
  - Outstanding balance (red = due, green = clear)
- **New buyer:** Click "➕ Add as new buyer"
  - Fill State, GSTIN, Address, Phone (all optional)
  - Buyer is automatically saved when invoice is created

#### Step 2 — Invoice Details
| Field | Notes |
|---|---|
| Invoice No. | Auto-generated, read-only |
| Invoice Date | Defaults to today |
| Payment Mode | Credit / Cash / UPI / Bank Transfer / Cheque |
| Order Reference | PO number (optional) |
| Dispatch Info | Lorry / courier (optional) |

#### Step 3 — Items
- Type to search products — instant autocomplete
- Selecting a product **auto-fills**: Rate, GST%, HSN Code, Unit
- Wholesale mode uses the wholesale price automatically
- Set a discount % — amount recalculates in real time
- Add unlimited items per invoice
- Each row shows the GST amount for that item

#### Step 4 — Review & Save
- Full summary of buyer + all items
- **Totals:**
  - Subtotal → Discount → Taxable Value
  - CGST + SGST **or** IGST (based on buyer state vs company state)
  - Freight / extra charges
  - **Grand Total**
- **Paid at Billing** — enter partial or full amount received
- **Balance Due** = Grand Total − Paid at Billing
- **Previous Balance** — buyer's outstanding before this invoice
- PDF is automatically generated and saved on submit

### GST Logic
| Scenario | Tax Applied |
|---|---|
| Buyer in same state as company | CGST + SGST (50/50 split) |
| Buyer in a different state | IGST (full rate) |

Company state is set in Settings.

---

## 📄 Invoice Management

Access via the `Bills` tab.

### Invoice List
- Filter by date range
- Search by invoice number, buyer name, or payment mode
- Quick filter chips: All / Cash / UPI / Credit
- Stats strip: total invoices, total amount, total GST

### Invoice Detail
Opening an invoice shows:
- Complete summary: buyer info, all line items, GST breakup
- **Paid at Billing** (green)
- **Balance Due** (orange)
- **Previous Balance** if applicable (purple)
- **Total Outstanding** = Balance Due + Previous Balance
- Amount in Words
- UPI QR ALSO
- a QR code will automatically appear on every invoice PDF. Customers can scan with PhonePe, Google Pay, Paytm, or any UPI app to pay instantly.

### Invoice Actions
| Action | Access |
|---|---|
| Download PDF | All users |
| View Buyer Ledger | All users |
| Cancel Invoice | Admin only |

### Cancelling an Invoice
- Stock is fully restored for all items on the invoice
- Invoice number is prefixed with `[CANCELLED]`
- Cancelled invoices cannot be downloaded as PDF

---

## 📦 Products & Inventory

Access via `More → Products`.

### Product Fields
| Field | Notes |
|---|---|
| Name | Must be unique |
| HSN Code | Required for GST compliance |
| GST % | Auto-applied in billing |
| Cost Price | Purchase/cost price — used for profit estimation |
| Selling Price | Standard retail rate |
| Wholesale Price | Used when Wholesale mode is active in billing |
| Stock Qty | Current available quantity |
| Unit | Pcs / Kg / Box / Litre / etc. |
| Product variations options

### Automatic Stock Movement
| Event | Stock Change |
|---|---|
| Invoice saved | Deducted automatically |
| Purchase recorded | Added automatically |
| Invoice cancelled | Fully restored |
| Manual item entry (no autocomplete) | No stock change |

### Low Stock Threshold
Edit `LOW_STOCK_THRESHOLD` in `database_manager.py` to set your minimum level (default: 5).

---

## 👥 Buyers (Customers)

Access via the `Buyers` tab.

### Buyer Fields
| Field | Notes |
|---|---|
| Name | Required |
| GSTIN | 15-character GST number |
| State | Determines IGST vs CGST/SGST |
| Address | Printed on invoice |
| Phone | Contact number |
| Opening Balance | Pre-existing outstanding when first added |

### Buyer Ledger (Account Statement)
- **Invoice entries** — debit (amount billed)
- **Payment entries** — credit (amount received)
- **Running balance** on every row
- Filter by date range
- **Export to PDF** — shareable statement for the customer

### Recording a Payment
From the Buyer Ledger page → "Record Payment":
- Enter amount, date, payment mode, optional notes
- Balance updates immediately

### Balance Tracking
- Dashboard "Receivables" shows total across all buyers
- Invoice detail shows previous balance at time of billing
- Buyer list shows current balance for each customer

---

## 🏭 Vendors (Suppliers)

Access via `More → Vendors`.

### Vendor Fields
Name, GSTIN, Address, Phone, Email

### Features
- Vendor list with search
- Add / Edit / Delete vendors
- View all purchases linked to a vendor

---

## 🛒 Purchases

Access via `More → Purchases`.

### Purchase Bill Fields
| Field | Notes |
|---|---|
| Vendor | Select from dropdown |
| Bill No. | Supplier's invoice number |
| Date | Purchase date |
| Total Amount | Full bill value |
| Amount Paid | Initial payment at time of entry |
| Payment Status | Unpaid / Partial / Paid |
| Notes | Internal reference (optional) |

### Adding Payments Later
- Open a purchase → "Add Payment"
- Full payment history shown (date, amount, mode)
- Status auto-updates: Unpaid → Partial → Paid

### Stock & Cost Impact
- Saving a purchase **increases stock** for the product
- Cost price updates using **WAC (Weighted Average Cost)**:
  `New Cost = (Old Stock × Old Cost + New Qty × New Cost) ÷ Total Stock`

---

## 📊 Reports & PDF Export

### 1. Invoice PDF
Auto-generated when invoice is saved. Also available for reprint from invoice detail.
- Company logo and letterhead
- Item table with HSN codes and GST rates
- GST breakup (CGST/SGST or IGST)
- Amount in words
- Bank payment details
- Paid / Balance Due / Previous Balance / Total Outstanding

### 2. Buyer Ledger PDF
`Buyers → [Select Buyer] → Ledger → Download PDF`
- Complete statement from opening to closing balance
- Professional format for sharing with customers

### 3. Summary Report PDF
`More → PDF Report`
- All invoices in a date range
- Total sales, total GST, grand total
- Buyer-wise breakdown

### 4. Sales Chart (Dashboard)
| Tab | Data |
|---|---|
| Weekly | Last 7 days, day by day |
| Monthly | Last 30 days, week by week |
| Yearly | Last 12 months |

### 5. GSTR 1 and 3B Export Option
| Excel / CSV export
| Stock Report
Opening · Purchases · Sales · Closing · Stock Value

---

## ⚙️ Settings

Access via `More → Settings` (Admin only).

### Company Information
| Field | Where It Appears |
|---|---|
| Company Name | Invoice header |
| Address | Invoice header |
| Phone / Email | Invoice footer |
| GSTIN | Invoice header |
| State | Controls IGST vs CGST/SGST for all invoices |
| Logo | Top-left corner of every invoice PDF |

### Bank Details
Printed at the bottom of every invoice:
- Bank Name, Account Number, IFSC Code, Account Holder Name

### Logo Upload
- Accepts JPG, PNG, GIF
- Replaces the previous logo when a new one is uploaded

### User Management
- View all users with roles
- Add new user (username + password + role)
- Delete users (`admin` account is protected)

### UPI & QR Code
Add your UPI ID — a QR code will automatically appear on every invoice PDF. Customers can scan with PhonePe, Google Pay, Paytm, or any UPI app to pay instantly.

---

## 📱 Mobile Interface

Open the app on any mobile browser — the mobile layout loads automatically based on device detection.

### Bottom Navigation (5 tabs)

| Tab | Pages |
|---|---|
| 🏠 Home | Dashboard |
| 📄 Bills | Invoice list and detail |
| ➕ (FAB) | Create new invoice |
| 👥 Buyers | Buyer list and ledger |
| ⋯ More | All other sections |

### More Menu (Slide-up Sheet)
Tap "More" → panel slides up:

**Inventory:** Products, Vendors, Purchases

**Reports:** Invoices, Buyer Ledger, PDF Report

**Admin** *(Admin role only):* Settings, Manage Users, Logout

### Mobile Billing Features
- Touch-safe autocomplete — scrolling the list does not accidentally select an item
- 4-step wizard with sticky progress tabs
- Buyer info card with GST type badge and balance
- New buyer form embedded directly in the billing wizard
- All totals (CGST/SGST/IGST, balance due, previous balance) update in real time
- CSS-only spinner — no Bootstrap dependency

---

## 🗄️ Database & File Structure

### Project Layout
```
billing-app/
│
├── app.py                    # Flask application and all routes
├── database_manager.py       # All database functions
├── pdf_generator.py          # PDF creation (ReportLab)
├── settings.json             # Company settings (auto-created)
├── billing.db                # SQLite database
│
├── uploads/                  # Uploaded logo files
├── pdfs/                     # Auto-saved invoice PDFs
│
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── billing.html
    ├── invoices.html
    ├── invoice_detail.html
    ├── products.html
    ├── buyers.html
    ├── buyer_ledger.html
    ├── vendors.html
    ├── purchases.html
    ├── settings.html
    ├── login.html
    │
    └── mobile/
        ├── base_mobile.html
        ├── dashboard.html
        ├── billing.html
        ├── invoices.html
        ├── invoice_detail.html
        ├── buyers.html
        ├── buyer_ledger.html
        ├── products.html
        ├── vendors.html
        ├── purchases.html
        └── settings.html
```

### Database Tables
| Table | Contents |
|---|---|
| `users` | Login credentials and roles |
| `buyers` | Customer profiles and opening balances |
| `vendors` | Supplier profiles |
| `products` | Product catalogue, stock, prices |
| `invoices` | Invoice headers (totals, paid amount, previous balance) |
| `invoice_items` | Line items for each invoice |
| `customer_payments` | Payment receipts from buyers |
| `purchases` | Purchase bills from vendors |
| `purchase_payments` | Payments made to vendors |

### Backup
The entire database is a single file — `billing.db`. Copy this file to back up all your data. To restore, replace the file and restart the app.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3 + Flask |
| Database | SQLite (file-based, no server needed) |
| PDF Generation | ReportLab |
| Desktop Frontend | HTML + Bootstrap 5 + Jinja2 |
| Mobile Frontend | Custom CSS (no Bootstrap dependency) |
| Charts | Chart.js 4.4.1 (CDN) |
| Icons | Bootstrap Icons (CDN) |
| Password Security | Werkzeug password hashing |
| Mobile Detection | User-Agent detection in Flask |

---

## ⚠️ Important Notes

1. **First run:** Default password is `admin123` — change it immediately via Settings → Manage Users
2. **Company State:** Set this in Settings before creating invoices — incorrect state leads to wrong IGST/CGST calculations
3. **Low stock threshold:** Edit `LOW_STOCK_THRESHOLD` in `database_manager.py` (default: 5)
4. **Internet required for:** Chart.js and Bootstrap Icons (CDN) — charts and icons won't display offline
5. **Change port:** Edit the last line of `app.py` — `app.run(port=5000)` — replace `5000` with any free port
6. **Manual product entry:** You can type a product name in billing without using autocomplete — this creates a line item but does not affect stock levels
7. **PDF storage:** All generated PDFs are saved in the `pdfs/` folder — back this up along with `billing.db`

---

## 🐛 Known Limitations

- No Excel / CSV export (PDF only)
- No built-in email or WhatsApp sharing (manual download required)
- Charts require an internet connection to load (Chart.js via CDN)
- No multi-branch / multi-location support

---

*Built with Flask + SQLite · Runs locally · No subscription required*
