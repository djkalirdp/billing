# 🧾 Professional Billing & Inventory Software

GST-compliant billing and inventory management system built with **Python Flask + SQLite**. Runs entirely on your local machine — no internet subscription, no cloud.

---

## 📋 Table of Contents

1. [Features Overview](#-features-overview)
2. [Installation](#-installation)
3. [Login & User Roles](#-login--user-roles)
4. [Dashboard](#-dashboard)
5. [Billing / Create Invoice](#-billing--create-invoice)
6. [Invoice Management](#-invoice-management)
7. [Products & Inventory](#-products--inventory)
8. [Product Variations (Size/Color)](#-product-variations-sizecolor)
9. [Product Rate List](#-product-rate-list)
10. [Buyers (Customers)](#-buyers-customers)
11. [Buyer Ledger / Khata](#-buyer-ledger--khata)
12. [Vendors (Suppliers)](#-vendors-suppliers)
13. [Purchases](#-purchases)
14. [Sales Quotations / Proforma](#-sales-quotations--proforma-invoice)
15. [Batch / Expiry Tracking](#-batch--expiry-tracking)
16. [GST Reports](#-gst-reports)
17. [PDF Page Sizes](#-pdf-page-sizes)
18. [Settings](#-settings)
19. [Mobile Interface](#-mobile-interface)
20. [Database & File Structure](#-database--file-structure)
21. [Tech Stack](#-tech-stack)
22. [Important Notes](#-important-notes)
23. [Changelog](#-changelog)

---

## ✨ Features Overview

| Category | Features |
|---|---|
| 🧾 **Billing** | GST invoices, Retail & Wholesale, UPI/Cash/Credit/Cheque/Bank Transfer |
| 📋 **Quotations** | Sales Quotation (Proforma Invoice), 1-click convert to Tax Invoice |
| 📦 **Inventory** | Auto stock deduction on sale, low-stock alerts, product variations |
| 🏷️ **Rate List** | Full price list — HSN, GST%, cost, selling, MRP, stock — with live search |
| 👥 **Buyers** | Customer profiles, outstanding balance, payment collection |
| 📒 **Ledger** | Running balance ledger with edit/delete payment entries |
| 🏭 **Vendors** | Supplier profiles, purchase bills, payment tracking |
| 🛒 **Purchases** | Full-page purchase form, Resale vs Raw Material, edit bills |
| 📦 **Batches** | Batch no. + expiry tracking from purchase to sale |
| 📊 **Reports** | GSTR-1, GSTR-2B, GSTR-3B with ITC — PDF + Excel |
| 📄 **PDF Sizes** | A4 / A4 Landscape / A5 / A5 Landscape for all PDFs |
| 📱 **Mobile** | Dedicated mobile UI, bottom navigation, touch autocomplete |
| 🔐 **Auth** | Login required, Admin vs Cashier roles |
| ⚙️ **Settings** | Company info, logo, bank details, UPI QR code |

---

## 🚀 Installation

**Requirements:** Python 3.8+, pip

```bash
# 1. Enter project folder
cd billing-app
    or
#simply type this command in terminal
bash <(curl -fsSL https://raw.githubusercontent.com/djkalirdp/billing/main/install.sh)
    or
Run the install.bat file  #for windows(after installation of python)

# 2. Virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install packages
pip install flask reportlab openpyxl werkzeug

# 4. Run
python app.py

# 5. Open browser
http://localhost:5000
```

**Mobile access:** Both devices on same Wi-Fi → open `http://YOUR-PC-IP:5000`

### Default Login
| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

> ⚠️ Change the password immediately after first login — Settings → Manage Users

---

## 🔐 Login & User Roles

| Feature | Admin | Cashier |
|---|---|---|
| Create invoices / quotations | ✅ | ✅ |
| View products, buyers, rate list | ✅ | ✅ |
| Cancel invoices | ✅ | ❌ |
| Edit/delete payments in ledger | ✅ | ❌ |
| Purchases, purchases edit | ✅ | ❌ |
| GST reports | ✅ | ❌ |
| Settings, manage users | ✅ | ❌ |

---

## 📊 Dashboard

| Card | Description |
|---|---|
| Today's Sales | All invoices created today |
| Receivables | Total outstanding across all buyers |
| Est. Profit | (Selling − Cost) × Qty sold |
| Low Stock | Products below threshold (default: 5) |

Sales chart — switch Week / Month / Year tabs.

---

## 🧾 Billing / Create Invoice

Click `+` button (mobile) or **New Invoice** button.

### 4-Step Wizard

**Step 1 — Buyer:**
- Toggle **Retail / Wholesale** (prices auto-switch)
- Autocomplete search — fills GSTIN, State, pending balance
- Walk-in: type name manually → saved as new buyer on submit

**Step 2 — Invoice Details:**
Invoice No. (auto), Date, Payment Mode, Order Ref., Dispatch Info

**Step 3 — Items:**
- Product search autocomplete — fills Rate, GST%, HSN, Unit, Batch
- Discount % per item, unlimited rows

**Step 4 — Review & Save:**
- CGST+SGST or IGST auto-detected from buyer state
- Freight, paid at billing, balance due, previous balance
- UPI QR on PDF if UPI ID set in Settings

### GST Rules
| Buyer State | Tax |
|---|---|
| Same as company | CGST + SGST (50/50) |
| Different state | IGST (full rate) |

---

## 📄 Invoice Management

Filter by date range, search by invoice no/buyer/mode. Quick filter chips: All / Cash / UPI / Credit.

| Action | Who |
|---|---|
| Download PDF (A4/A4L/A5/A5L) | All users |
| View Buyer Ledger | All users |
| Cancel Invoice | Admin only |

Cancelled invoices: stock restored, prefixed `[CANCELLED]`, cannot be reprinted.

---

## 📦 Products & Inventory

**Fields:** Name, HSN, GST%, Cost Price, Selling Price, Wholesale Price, Stock Qty, Unit, Batch No., Expiry Date

**Stock movement:**
| Event | Stock |
|---|---|
| Invoice saved | Deducted |
| Purchase (Resale) | Added |
| Invoice cancelled | Restored |
| Purchase (Raw Material) | No change |

---

## 🎨 Product Variations (Size/Color)

Each product can have multiple variations (e.g. S/M/L, Red/Blue).

- Variation fields: Name, Selling Price, Wholesale Price, Cost Price, Stock Qty
- In billing: selecting a product with variations shows a second dropdown
- Stock deducted from the specific variation selected
- Rate List: variations expandable under each product row with a ▾ button

`Products → [Product Name] → Manage Variations`

---

## 🏷️ Product Rate List

`Inventory → Rate List`

| Column | Info |
|---|---|
| Product / Variation | Name + unit |
| HSN Code | Tax classification |
| Cost Price | Purchase cost |
| Rate (w/o GST) | Selling rate before tax |
| GST % | Color-coded badge |
| Price (incl. GST) | Customer-facing final price |
| Stock | Current qty with LOW/OUT badge |

- 🔍 Live search — by product name or HSN (auto-submits after 400ms)
- Expand variations — click `▾ N` button on any product row
- All variations auto-expand when search query is active

---

## 👥 Buyers (Customers)

Fields: Name, GSTIN, State, Address, Phone, Opening Balance

Dashboard Receivables = sum of all outstanding balances.

---

## 📒 Buyer Ledger / Khata

`Buyers → [Buyer Name] → Ledger`

| Row Type | Effect on Balance |
|---|---|
| Opening Balance | Initial amount |
| Invoice (Dr) | Increases balance (amount owed) |
| Payment (Cr) | Reduces balance |

Running balance updated per row. Filter by date range — opening balance adjusts automatically.

**Action column:**
- Payment rows → ✏️ Edit (date, amount, mode, notes) or 🗑️ Delete (confirmation required)
- Invoice rows → 👁️ View full invoice

**Download PDF** — page size selector (A4/A4L/A5/A5L) appears above the button.

---

## 🏭 Vendors (Suppliers)

Name, GSTIN, Address, Phone, Email. Add / Edit / Delete / Search. View all purchases per vendor.

---

## 🛒 Purchases

`More → Purchases`

### New Purchase Form (Full-Page)

**Purchase Type:**
| Type | Stock Effect |
|---|---|
| 🛒 Resale / Trading | Stock increases |
| 🏭 Raw Material / Expense | No stock change |

**Form fields:** Vendor, Bill No., Date, Place of Supply, RCM toggle, line items (Product, Qty, Rate, GST%, Batch, Expiry), Amount Paid, Payment Mode

**GST auto-detection:** Select Place of Supply → IGST or CGST+SGST detected automatically with colour banner.

**GST rates:** 0%, 0.1%, 0.25%, 1%, 1.5%, 3%, 5%, 6%, 7.5%, 9%, 12%, 14%, 18%, 28%

**Edit:** Click Edit on any purchase row → opens same full-page form pre-filled.

**Payment tracking:** Partial or full payment at entry; add more payments later. Status: Unpaid → Partial → Paid.

> ⚠️ Editing a purchase bill does not reverse old stock movements. Adjust stock manually if needed.

---

## 📋 Sales Quotations / Proforma Invoice

`Desktop sidebar → Quotations` | `Mobile → More → Quotations`

### What is a Quotation?

A price estimate sent to the customer **before** the sale. No stock is deducted, no GST liability is created. Quotation number series: `QT-0001`, `QT-0002`, …

### Creating a Quotation

`Quotations → New Quotation`

**Form layout:**
- Top section (2-column): Buyer info on left, GST summary panel on right
- **Full-width items table** below — proper HTML table with wide description column
- **4 empty rows by default** — type or search product directly
- Product autocomplete fills: Selling Price ✅, GST% ✅, HSN, Unit
- Live GST summary updates as you type
- IGST / CGST+SGST auto-detected from buyer state

**Item table columns:** # | Product/Description | Qty | Rate ₹ | GST% | Disc% | ✕

**Fixed fields:** Payment Mode always shows **"Advance"** on the PDF (not editable)

### Quotation PDF vs Tax Invoice PDF

| | Tax Invoice | Sales Quotation |
|---|---|---|
| Title | TAX INVOICE | SALES QUOTATION |
| Number | Invoice No. | Quotation No. |
| Copies | 3 (Original / Duplicate / Triplicate) | 1 |
| Dispatch field | ✅ | ❌ Removed |
| Payment Mode | As entered | Always "Advance" |
| Valid Until date | ❌ | ✅ |
| Stock deducted | ✅ | ❌ |
| GST liability | ✅ | ❌ |

### Convert Quotation → Tax Invoice

On the Quotation Detail page → **Convert to Tax Invoice** section:
1. Select payment mode
2. Enter amount paid (if any)
3. Click **Convert** — new Tax Invoice is created, stock deducted, redirected to invoice

### Actions on Quotation Detail
- 📄 **Download PDF** — with A4/A4L/A5/A5L size picker
- 🔄 **Convert to Tax Invoice**
- 🗑️ **Delete Quotation** — permanent, no stock impact

---

## 📦 Batch / Expiry Tracking

### Adding Batch in Purchase
Enter Batch No. and Expiry Date per line item. Multiple batches per product supported.

### Using Batch in Billing
Product autocomplete → Batch dropdown shows:
- `BATCH-001 (Qty: 50 | Exp: 2025-06-30)` — ✅ green
- `BATCH-002 (Qty: 10 | Exp: 2024-01-01)` — ⚠️ EXPIRED red

### Batch List
`More → Batch Tracker` — Qty In, Qty Out, Balance per batch. Expired and near-expiry (≤ 30 days) highlighted.

### Expiry Alert
Orange banner on Purchases page when any batch expires within 30 days.

---

## 📊 GST Reports

`More → Reports` — always set date range before generating.

| Report | Contents | Formats |
|---|---|---|
| **GSTR-1** | Outward supplies, rate-wise (5/12/18/28%) | PDF + Excel |
| **Purchase Register (GSTR-2B)** | Inward supplies, vendor GSTIN, RCM flag, tax amounts | PDF + Excel |
| **GSTR-3B Summary** | Section 3.1 output tax + Section 4 ITC + net payable | PDF + Excel |
| **Stock Report** | Current inventory — HSN, unit, cost, selling price, stock value | PDF + Excel |

**GSTR-3B Section 4 (ITC):**
- 4(A) — ITC available from purchases (normal)
- 4(D) — RCM purchases
- Net Tax Payable = Output Tax − ITC

---

## 📄 PDF Page Sizes

All invoice, quotation, and ledger PDFs support 4 sizes:

| Option | Dimensions | Best For |
|---|---|---|
| **A4** | 210 × 297 mm Portrait | Default — all printers |
| **A4 Landscape** | 297 × 210 mm | Wide tables, landscape printing |
| **A5** | 148 × 210 mm Portrait | Booklet-style compact invoices |
| **A5 Landscape** | 210 × 148 mm | Small horizontal format |

**How to use:** On Invoice Detail / Buyer Ledger / Quotation Detail pages — click a size tile → then Download PDF.

**A5 behaviour:**
- Column widths scale to 67% of A4 values
- Fonts scale to 80% — text fits narrow cells
- Margins tightened to 6mm
- Entire invoice copy wrapped in `KeepTogether` — header, items, totals, HSN table, signature **never split** across pages
- Logo scales proportionally

---

## ⚙️ Settings

`More → Settings` (Admin only)

| Section | Fields |
|---|---|
| **Company Info** | Name, Address, Phone, Email, GSTIN, State, Logo |
| **Bank Details** | Bank Name, Account No., IFSC, Account Holder |
| **UPI** | UPI ID (generates QR code on invoice PDFs) |
| **Users** | Add/delete cashier or admin accounts |

**Company State** is critical — controls whether IGST or CGST+SGST applies.

---

## 📱 Mobile Interface

Mobile layout auto-loads on phones/tablets.

### Bottom Navigation
| Tab | Pages |
|---|---|
| 🏠 Home | Dashboard |
| 📄 Bills | Invoice list |
| ➕ FAB | Create new invoice |
| 👥 Buyers | Buyer list + ledger |
| ⋯ More | All other pages |

### More Menu (slide-up panel)
**Inventory:** Products, Rate List, Vendors, Purchases, Batch Tracker
**Sales:** Quotations
**Reports:** Invoices, Buyer Ledger, PDF Reports
**Admin:** Settings, Manage Users, Logout

---

## 🗄️ Database & File Structure

```
billing-app/
│
├── app.py                      # All Flask routes
├── database_manager.py         # All DB functions
├── pdf_generator.py            # Invoice + Ledger PDFs (A4/A4L/A5/A5L)
├── reports_generator.py        # GSTR-1/2B/3B/Stock — PDF + Excel
├── settings.json               # Company settings (auto-created)
├── billing.db                  # SQLite database
│
├── uploads/                    # Company logo files
├── invoices/                   # Auto-saved A4 invoice PDFs
│
└── templates/
    ├── base.html               # Desktop sidebar nav (Quotations added)
    ├── dashboard.html
    ├── billing.html            # 4-step invoice wizard
    ├── invoices.html
    ├── invoice_detail.html     # PDF size picker (A4/A4L/A5/A5L)
    ├── products.html
    ├── product_rate_list.html  # With variations expand/collapse
    ├── buyers.html
    ├── buyer_ledger.html       # Edit/delete payments + PDF size picker
    ├── vendors.html
    ├── purchases.html
    ├── purchase_form.html      # Full-page purchase add/edit
    ├── proforma_list.html      # Quotation list
    ├── proforma_form.html      # Quotation form — full-width table, 4 rows
    ├── proforma_detail.html    # Quotation detail, convert, PDF + size picker
    ├── batches.html
    ├── reports.html
    ├── settings.html
    ├── login.html
    └── mobile/
        ├── base_mobile.html    # Quotations in More menu
        └── ...
```

### Database Tables

| Table | Contents |
|---|---|
| `users` | Login credentials, roles |
| `buyers` | Customer profiles, opening balances |
| `vendors` | Supplier profiles |
| `products` | Products, prices, stock |
| `product_variations` | Size/color variants — own price & stock |
| `invoices` | Invoice headers |
| `invoice_items` | Line items per invoice (with batch_no) |
| `customer_payments` | Payment receipts — editable & deletable |
| `purchases` | Purchase bills (type: Resale / Raw Material) |
| `purchase_items` | Line items per purchase bill |
| `purchase_payments` | Payments to vendors |
| `batch_tracking` | Batch IN (purchase) and OUT (sale) movements |
| `proforma_invoices` | Quotation headers |
| `proforma_items` | Quotation line items |

**Backup:** Copy `billing.db`. Restore by replacing the file and restarting the app.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3 + Flask |
| Database | SQLite (file-based) |
| PDF | ReportLab (A4/A4L/A5/A5L) |
| Excel | openpyxl |
| Frontend (Desktop) | HTML + Bootstrap 5 + Jinja2 |
| Frontend (Mobile) | Custom responsive CSS |
| Charts | Chart.js 4.4.1 (CDN) |
| Icons | Bootstrap Icons (CDN) |
| Auth | Werkzeug password hashing |

---

## ⚠️ Important Notes

1. **Default password** `admin123` — change immediately after first login
2. **Company State** — set before creating any invoices; wrong state = wrong IGST/CGST/SGST
3. **Proforma/Quotation** — does NOT deduct stock and does NOT create GST liability
4. **Convert Quotation** — 1-click creates Tax Invoice, deducts stock, records sale
5. **Purchase Type** — Resale = stock increases; Raw Material = expense only, no stock
6. **Editing purchases** — does not reverse old stock movements; adjust stock manually if needed
7. **Batch Tracking** — optional; skip batch fields if not needed
8. **A5 PDFs** — entire invoice guaranteed on one page (KeepTogether applied)
9. **PDF auto-save** — A4 PDFs saved in `invoices/` folder; other sizes download only
10. **Low stock threshold** — change `LOW_STOCK_THRESHOLD` in `database_manager.py` (default: 5)
11. **Internet** — required for Chart.js + Bootstrap Icons (CDN); offline = no charts/icons
12. **Change port** — last line of `app.py`: `app.run(port=5000)`
13. **Manual items in billing** — items typed without autocomplete do NOT update stock

---

## 📌 Changelog

### Latest — Current Version
- ✅ **Quotation form items table** — rewritten as proper `<table>` (was CSS grid); description column now full-width (`min-width: 240px`), never cramped
- ✅ **4 default rows** in quotation form — no need to manually click "Add Row" to start
- ✅ **Autocomplete fixed** — selling price and GST rate now fill correctly from product search
- ✅ **Sales Quotations / Proforma** — full QT-XXXX numbering, separate list, detail, PDF
- ✅ **Convert Quotation → Tax Invoice** — 1 click, stock deducted
- ✅ **Quotation PDF** — "SALES QUOTATION", Advance mode, Valid Until, no dispatch row, 1 copy
- ✅ **PDF Page Sizes** — A4 / A4 Landscape / A5 / A5 Landscape for invoices, quotations, ledger
- ✅ **A5 PDF layout** — all widths, logo, fonts scale proportionally; single-page KeepTogether
- ✅ **Rate List** — with variation rows expand/collapse per product
- ✅ **Buyer Ledger** — edit/delete payment entries, edit modal with all fields
- ✅ **Purchase Type** — Resale vs Raw Material (conditional stock update)
- ✅ **Purchase Edit** — full-page edit with item-level changes
- ✅ **GSTR-1, GSTR-2B, GSTR-3B** — PDF & Excel with ITC section 4
- ✅ **Batch Tracking** — from purchase to billing, expiry alerts
- ✅ **UPI QR Code** — on all invoice PDFs

---

*Built with Flask + SQLite · Runs locally · No subscription required*
