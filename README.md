# billing
web based billing software
# 🧾 Professional Billing & Inventory Software

A complete GST-compliant billing and inventory management system that works on both **desktop** and **mobile** browsers. Built with Python Flask + SQLite — no cloud subscription required, runs entirely on your local machine.

---

## 📋 Table of Contents

- [Features Overview](#-features-overview)
- [Installation](#-installation)
- [Login & User Roles](#-login--user-roles)
- [Dashboard](#-dashboard)
- [Billing / Create Invoice](#-billing--create-invoice)
- [Invoice Management](#-invoice-management)
- [Products & Inventory](#-products--inventory)
- [Buyers (Customers)](#-buyers-customers)
- [Vendors (Suppliers)](#-vendors-suppliers)
- [Purchases](#-purchases)
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
