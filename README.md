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
8. [Product Variations](#-product-variations-sizecolor)
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
20. [Sample Database](#-sample-database)
21. [Database & File Structure](#-database--file-structure)
22. [Tech Stack](#-tech-stack)
23. [Important Notes](#-important-notes)
24. [Changelog](#-changelog)

---

## ✨ Features Overview

| Category | Features |
|---|---|
| 🧾 **Billing** | GST invoices, Retail & Wholesale, UPI/Cash/Credit/Cheque/Bank Transfer |
| 📋 **Quotations** | Sales Quotation (Proforma Invoice), 1-click convert to Tax Invoice |
| 📦 **Inventory** | Auto stock deduction on sale, low-stock alerts, product variations |
| 🏷️ **Rate List** | Full price list — HSN, GST%, cost, selling, MRP, stock — with live search |
| 👥 **Buyers** | Customer profiles, outstanding balance, opening balance support |
| 📒 **Ledger** | Running balance ledger with edit/delete payment entries |
| 🏭 **Vendors** | Supplier profiles, purchase bills, payment tracking |
| 🛒 **Purchases** | Full-page purchase form, Resale vs Raw Material, edit bills |
| 📦 **Batches** | Batch no. + expiry tracking from purchase to sale |
| 📊 **Reports** | GSTR-1, GSTR-2B, GSTR-3B with ITC cross-utilization — PDF + Excel |
| 📄 **PDF Sizes** | A4 / A4 Landscape / A5 / A5 Landscape for all PDFs |
| 🖼️ **Logo** | Company logo on PDF invoices — 2.5cm × 2cm |
| 👤 **Users** | Admin + Cashier roles, change password for all accounts |
| 📱 **Mobile** | Dedicated mobile UI, bottom navigation, touch autocomplete |
| 🗃️ **Sample Data** | Ready-made sample database for testing all features |

---

## 🚀 Installation

### Windows (One-Command — Recommended)

1. Download `install.bat` from the repository
2. **Double-click** `install.bat`
3. Script automatically:
   - Checks Python (shows install guide if missing)
   - Downloads entire repo as ZIP from GitHub
   - Extracts to `billing-app/` folder
   - Creates Python virtual environment
   - Installs all packages (Flask, ReportLab, openpyxl, num2words, qrcode, Pillow)
   - Downloads DejaVu fonts for ₹ symbol in PDFs
   - Creates `start.bat` launcher
   - Verifies everything — every step shows status
   - Optionally starts the app immediately

**After install — every time:**
```
Double-click  start.bat
```
Then open browser: `http://localhost:5000`

---

### Linux / macOS (One-Command)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/djkalirdp/billing/main/install.sh)
```

**After install:**
```bash
bash start.sh
```

---

### Manual Install (any OS)

```bash
git clone https://github.com/djkalirdp/billing.git billing-app
cd billing-app
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install flask werkzeug reportlab openpyxl num2words "qrcode[pil]" Pillow
python app.py
```

---

### Requirements

| Requirement | Version |
|---|---|
| Python | 3.8 or newer |
| Internet | Only needed during install |
| Browser | Any modern browser |
| OS | Windows 10/11, Linux, macOS |

---

## 🔐 Login & User Roles

**Default login:**

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

> ⚠️ **Change password immediately** → Settings → Users → Change Password

### Roles

| Role | Access |
|---|---|
| **Admin** | Everything — billing, inventory, reports, settings, users |
| **Cashier** | Billing + Buyers + Invoice view only |

### User Management
- **Add User** — Settings → Users → Add User form
- **Change Password** — blue key button next to every user (including admin)
- **Delete User** — only non-admin accounts

---

## 📊 Dashboard

| Card | Description |
|---|---|
| **Today's Sales** | Total invoices today |
| **Total Receivable** | All outstanding dues from buyers |
| **Estimated Profit** | (Invoice Rate − Variation Cost) × Qty |
| **Low Stock Items** | Products/variations below threshold |

Weekly / Monthly / Yearly sales chart (Chart.js).

> **Profit:** Uses each variation's own cost price — not parent product cost. Accurate margin per size/variant.

---

## 🧾 Billing / Create Invoice

### Steps
1. Select Buyer — previous balance auto-loaded
2. Add Items — autocomplete fills HSN, GST%, rate, unit
3. Variations — dropdown shows size/color options per product
4. GST auto-detected:
   - Same state → **CGST + SGST**
   - Different state → **IGST**
5. Per-item discount percentage
6. Payment mode — Cash / UPI / Credit / Cheque / Bank Transfer
7. Freight charge (optional)
8. Paid Amount — partial payment supported

### After Saving
- Stock deducted automatically per item/variation
- Invoice number auto-incremented
- PDF auto-saved to `invoices/` (A4)

---

## 📋 Invoice Management

| Feature | Details |
|---|---|
| Search | By invoice number, buyer name |
| Date Filter | Custom date range |
| PDF Download | A4 / A4L / A5 / A5L — size picker on detail page |
| Cancel Invoice | Marks `[CANCELLED]`, restores stock (Admin only) |
| 3 Copies | Original / Duplicate / Triplicate on single PDF |

---

## 📦 Products & Inventory

| Field | Description |
|---|---|
| Name | Unique product name |
| HSN Code | For GST filing |
| GST Rate | 0 / 5 / 12 / 18 / 28 % |
| Purchase Rate | Cost price — used for profit calculation |
| Selling Price | Default retail price |
| Wholesale Price | For wholesale buyers |
| Stock Qty | Current inventory |
| Unit | Pcs / Kg / Litre / Box / etc. |

---

## 🎨 Product Variations (Size/Color)

Each product can have unlimited variations.

| Field | Description |
|---|---|
| Variation Name | 100ml / 200ml / Large / Red etc. |
| Cost Rate | **Own purchase cost** — correct profit per size |
| Selling Price | Variation-specific retail |
| Wholesale Price | Variation-specific wholesale |
| Stock | Variation-specific stock |

In Billing autocomplete: `Product Name → Variation` dropdown.

---

## 🏷️ Product Rate List

`Products → Rate List`

- All products + variations in one table
- Columns: HSN, GST%, Cost, Selling, Wholesale, Stock, Unit
- Variations collapsible per product (▼ toggle)
- Live search filter

---

## 👥 Buyers (Customers)

| Field | Description |
|---|---|
| Name | Unique customer name |
| GSTIN | GST number (optional) |
| Address, Phone, Email | Contact info |
| State | Controls IGST vs CGST/SGST |
| Opening Balance | Previous outstanding before software start |

---

## 📒 Buyer Ledger / Khata

`Buyers → View Ledger`

| Feature | Details |
|---|---|
| Running Balance | Date-wise debit/credit with closing balance |
| Invoice Entries | Auto-posted as debit |
| Payment Entry | Cash / UPI / Cheque / Bank Transfer |
| Edit Payment | Change amount, date, mode, notes |
| Delete Payment | Remove incorrect entries |
| PDF Ledger | A4 / A4L / A5 / A5L |

---

## 🏭 Vendors (Suppliers)

Supplier profiles with GSTIN, address, phone, email.

---

## 🛒 Purchases

### Creating Purchase Bill
1. Select Vendor
2. Bill No., Date, Type (Resale / Raw Material)
3. Add items — product, qty, rate, GST, batch, expiry
4. Payment status — Paid / Partial / Unpaid

### Purchase Types

| Type | Stock Effect |
|---|---|
| **Resale** | Stock increases by qty purchased |
| **Raw Material** | Expense only — stock unchanged |

### ITC
- Regular → Eligible ITC (Section 4A)
- Reverse Charge → RCM ITC (Section 4D)

---

## 📋 Sales Quotations / Proforma Invoice

`More → Quotations`

| Feature | Details |
|---|---|
| Quotation Number | Auto-generated (QUOT/YY-YY/001) |
| Validity | Set validity days |
| Status | Draft / Sent / Approved / Converted |
| PDF | "SALES QUOTATION" heading, 1 copy |
| Convert | 1-click → Tax Invoice + stock deduction |

> Quotations do NOT deduct stock or create GST liability — only conversion does.

---

## 📦 Batch / Expiry Tracking

`More → Batch Tracker`

- Enter Batch No. + Expiry on Purchase Bill
- Select batch when billing (optional)
- Track: purchased from whom → sold to whom
- Expiry Alert: orange banner for batches expiring within 30 days

---

## 📊 GST Reports

`More → Reports` — set date range before generating.

| Report | Contents | Format |
|---|---|---|
| **GSTR-1** | Outward supplies, rate-wise | PDF + Excel |
| **GSTR-2B / Purchase Register** | Inward supplies, vendor GSTIN, RCM | PDF + Excel |
| **GSTR-3B Summary** | Output tax + ITC + Net Payable | PDF + Excel |
| **Stock Report** | Inventory — HSN, cost, selling, value | PDF + Excel |

### GSTR-3B ITC Cross-Utilization (GST Act compliant)

| ITC | Used Against |
|---|---|
| **IGST ITC** | IGST → CGST → SGST |
| **CGST ITC** | CGST → IGST |
| **SGST ITC** | SGST → IGST |

> IGST credit of ₹1,226 automatically covers CGST ₹233 + SGST ₹233 → Net Payable = ₹0 ✅

---

## 📄 PDF Page Sizes

| Size | Dimensions | Best For |
|---|---|---|
| **A4** | 210 × 297 mm | Default |
| **A4 Landscape** | 297 × 210 mm | Wide tables |
| **A5** | 148 × 210 mm | Compact booklets |
| **A5 Landscape** | 210 × 148 mm | Small horizontal |

A5 scaling: 67% column widths, 80% fonts, 6mm margins, full KeepTogether (never splits).

---

## ⚙️ Settings

`More → Settings` (Admin only)

| Section | Fields |
|---|---|
| **Company Info** | Name, Address, Phone, Email, GSTIN, State, Logo |
| **Bank Details** | Bank Name, Account No., IFSC, Holder |
| **UPI** | UPI ID → QR code on all invoice PDFs |
| **Invoice Settings** | Prefix, starting number |
| **Users** | Add / Change Password / Delete |

**Logo:** Upload PNG/JPG → displays at 2.5cm × 2cm on PDF invoices. Recommended: 295×236px @ 300dpi.

---

## 📱 Mobile Interface

Auto-loads on phones/tablets.

### Bottom Navigation
| Tab | Pages |
|---|---|
| 🏠 Home | Dashboard |
| 📄 Bills | Invoice list |
| ➕ | New Invoice |
| 👥 Buyers | Buyer list + ledger |
| ⋯ More | Everything else |

### More Menu
Inventory · Sales · Reports · Admin

---

## 🗃️ Sample Database

`sample_billing.db` — pre-filled demo data for testing.

| Data | Count |
|---|---|
| Users | 2 (admin + cashier) |
| Vendors | 5 |
| Buyers | 8 (local + outstation + opening balances) |
| Products | 15 (FMCG items) |
| Variations | 13 (sizes/packs) |
| Purchases | 6 (with items, payments, batches) |
| Invoices | 7 (local + IGST + cancelled) |
| Payments | 8 (Cash/UPI/Cheque/NEFT) |
| Quotations | 3 (Draft/Sent/Approved) |
| Batch Records | 41 |

### How to Use
1. Download `sample_billing.db`
2. Rename your existing `data/billing_app.db` as backup
3. Copy `sample_billing.db` → `data/billing_app.db`
4. Restart app

---

## 🗄️ Database & File Structure

```
billing-app/
├── app.py                    # Flask routes
├── database_manager.py       # DB functions + schema
├── pdf_generator.py          # Invoice + Ledger PDFs
├── reports_generator.py      # GSTR reports PDF + Excel
├── settings.json             # Company settings
├── install.sh                # Linux/Mac installer
├── install.bat               # Windows installer
├── start.sh / start.bat      # App launchers
├── requirements.txt
├── DejaVuSans.ttf            # Font for ₹ symbol
├── DejaVuSans-Bold.ttf
│
├── data/
│   └── billing_app.db        # SQLite database ← BACK THIS UP!
├── backups/                  # Auto daily backups
├── invoices/                 # Auto-saved A4 PDFs
├── reports/                  # Downloaded reports
├── static/uploads/           # Logo files
│
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── billing.html
    ├── invoices.html
    ├── invoice_detail.html
    ├── products.html
    ├── product_form.html
    ├── product_rate_list.html
    ├── product_variations.html
    ├── buyers.html
    ├── buyer_form.html
    ├── buyer_ledger.html
    ├── vendors.html
    ├── vendor_form.html
    ├── purchases.html
    ├── purchase_form.html
    ├── proforma_list.html
    ├── proforma_form.html
    ├── proforma_detail.html
    ├── batches.html
    ├── batch_history.html
    ├── reports.html
    ├── settings.html
    ├── users.html
    ├── login.html
    └── mobile/
        └── (all mobile equivalents)
```

### Database Tables

| Table | Contents |
|---|---|
| `users` | Login credentials, roles |
| `buyers` | Customer profiles, opening balance, state |
| `vendors` | Supplier profiles |
| `products` | Products, HSN, GST, cost, selling, stock |
| `product_variations` | Size/color variants — own cost, price, stock |
| `invoices` | Invoice headers — all tax fields, paid amount |
| `invoice_items` | Line items (variation_id, batch_no) |
| `customer_payments` | Payments — editable + deletable |
| `purchases` | Purchase bills — GST, RCM flag |
| `purchase_items` | Line items with batch/expiry |
| `purchase_payments` | Payments to vendors |
| `batch_tracking` | IN (purchase) and OUT (sale) movements |
| `proforma_invoices` | Quotation headers |
| `proforma_items` | Quotation line items |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.8+ + Flask 2.3+ |
| Database | SQLite (zero config) |
| PDF | ReportLab 4.0+ |
| Excel | openpyxl 3.1+ |
| Amount in Words | num2words (en_IN) |
| QR Code | qrcode + Pillow |
| Frontend | Bootstrap 5 + Jinja2 |
| Charts | Chart.js 4.4.1 (CDN) |
| Icons | Bootstrap Icons (CDN) |
| Auth | Werkzeug pbkdf2 hashing |

---

## ⚠️ Important Notes

1. **Default password** `admin123` — change immediately via Settings → Users
2. **Company State** — set before invoices; controls IGST vs CGST/SGST
3. **Variation cost** — set each variation's own purchase rate for correct profit
4. **ITC cross-utilization** — IGST credit offsets CGST/SGST per GST Act (automatic)
5. **Quotations** — no stock deduction, no GST liability until converted
6. **Purchase Type** — Resale = stock up; Raw Material = no stock change
7. **Cancel invoice** — restores stock; marks `[CANCELLED]` in invoice number
8. **Edit purchase** — old stock not reversed; adjust manually if needed
9. **A5 PDFs** — entire invoice on one page (KeepTogether)
10. **PDF auto-save** — A4 only saved to `invoices/`; other sizes download only
11. **Logo** — 2.5cm × 2cm recommended; 295×236px @ 300dpi
12. **DejaVu fonts** — required for ₹ symbol in PDFs; falls back to `Rs.` if missing
13. **Low stock threshold** — default 5; change in `database_manager.py`
14. **Manual items** — without autocomplete, stock not deducted
15. **Internet** — needed at startup for Chart.js + Bootstrap Icons CDN

---

## 📌 Changelog

### Latest — Current Version

#### Bug Fixes
- ✅ **PDF crash** — `NoneType.split()` when `order_ref`, `dispatch_info`, or item fields are NULL; all fields now safely coerced to string
- ✅ **Profit calculation** — was using parent product cost for variation items; now uses variation's own cost → correct margin per size
- ✅ **GSTR-3B Net Tax Payable** — IGST ITC was not offsetting CGST/SGST; now follows GST Act cross-utilization rules
- ✅ **GSTR-3B ITC section** — was hidden when no purchases existed; now always shown with ₹0 values
- ✅ **Change Password** — no option existed; added password change modal for all users

#### New Features
- ✅ **Windows installer** (`install.bat`) — step-by-step visible progress, no terminal needed
- ✅ **Sample database** — 15 products, 8 buyers, 5 vendors, 6 purchases, 7 invoices, 3 quotations
- ✅ **Default logo** — BillPro logo PNG (2.5cm × 2cm, 300dpi, transparent)
- ✅ **User password change** — Change Password button for every user in Settings → Users

#### Previous Releases
- ✅ Quotation form — HTML table layout, 4 default rows
- ✅ Sales Quotations — full create/list/detail/PDF/convert flow
- ✅ PDF Page Sizes — A4 / A4L / A5 / A5L
- ✅ Buyer Ledger — edit/delete payment entries
- ✅ Purchase Type — Resale vs Raw Material
- ✅ Purchase Edit — full-page item-level editing
- ✅ GSTR-1, GSTR-2B, GSTR-3B — PDF + Excel with ITC
- ✅ Batch Tracking — purchase to billing, expiry alerts
- ✅ UPI QR Code — on all invoice PDFs
- ✅ Product Variations — own price, cost, stock
- ✅ Rate List — with variations expand/collapse
- ✅ Opening Balance — buyer opening balance
- ✅ Mobile Interface — dedicated UI for all pages

---

*Built with Flask + SQLite · Runs locally · No subscription · GST compliant*
