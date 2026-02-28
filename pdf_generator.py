"""
================================================================================
  pdf_generator.py  —  Web App Version (Flask Compatible)
  Converted from: Python Tkinter Desktop App → Flask Web Application

  Key Changes from Desktop Version:
    1. All functions return BytesIO object → Flask can serve PDF directly
       as download (no need to save files to disk first)
    2. save_to_disk=True parameter added → optionally still save to disk
       (useful for auto-backup / reprint feature)
    3. Font registration is server-safe with multiple fallback paths
    4. DejaVuSans used as primary Unicode font (supports ₹ symbol on Linux)
    5. All imports cleaned up — no Tkinter dependencies
    6. New helper: get_pdf_response() → returns Flask send_file() response
================================================================================
"""

from reportlab.lib.pagesizes import A4, A5, landscape, portrait
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, KeepTogether, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from num2words import num2words
import os
import io
import json
from datetime import datetime
import database_manager as db

# QR code via ReportLab
try:
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    _QR_AVAILABLE = True
except Exception:
    _QR_AVAILABLE = False


# ─────────────────────────────────────────────
#  FONT REGISTRATION  (Server-Safe)
# ─────────────────────────────────────────────
def register_fonts():
    """
    Tries to register fonts in this order:
      1. DejaVuSans (bundled with repo — best for ₹ on Linux servers)
      2. Arial (Windows)
      3. Helvetica (built-in ReportLab fallback — no ₹ support)
    Returns: (regular_font, bold_font, currency_symbol)
    """
    # Path options for DejaVuSans (check repo root + common system paths)
    dejavu_paths = [
        'DejaVuSans.ttf',
        os.path.join(os.path.dirname(__file__), 'DejaVuSans.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
    ]
    dejavu_bold_paths = [
        'DejaVuSans-Bold.ttf',
        os.path.join(os.path.dirname(__file__), 'DejaVuSans-Bold.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    ]

    for reg_path in dejavu_paths:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont('DejaVuSans', reg_path))
                # Find matching bold
                for bold_path in dejavu_bold_paths:
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_path))
                        return 'DejaVuSans', 'DejaVuSans-Bold', '₹'
                # Bold not found — use regular for both
                return 'DejaVuSans', 'DejaVuSans', '₹'
            except Exception:
                pass

    # Try Windows Arial
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
        return 'Arial', 'Arial-Bold', '₹'
    except Exception:
        pass

    # Final fallback — built-in Helvetica (no ₹)
    return 'Helvetica', 'Helvetica-Bold', 'Rs.'


FONT_REG, FONT_BOLD, CURRENCY_SYM = register_fonts()


# ─────────────────────────────────────────────
#  FLASK HELPER
# ─────────────────────────────────────────────
def get_pdf_response(pdf_bytes, filename):
    """
    Wraps a BytesIO PDF for Flask's send_file().

    Usage in Flask route:
        pdf_bytes = create_invoice_pdf(...)
        return get_pdf_response(pdf_bytes, "INV-0001.pdf")
    """
    from flask import send_file
    pdf_bytes.seek(0)
    return send_file(
        pdf_bytes,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


def _make_upi_qr(upi_id, payee_name, amount, note="Invoice Payment"):
    """
    Returns a ReportLab Drawing containing a UPI QR code.
    UPI URL: upi://pay?pa=<id>&pn=<name>&am=<amount>&tn=<note>&cu=INR
    Returns None if QR is unavailable or upi_id empty.
    """
    if not _QR_AVAILABLE or not upi_id:
        return None
    try:
        import urllib.parse
        url = (
            f"upi://pay?pa={urllib.parse.quote(str(upi_id))}"
            f"&pn={urllib.parse.quote(str(payee_name or ''))}"
            f"&am={float(amount):.2f}"
            f"&tn={urllib.parse.quote(str(note))}"
            f"&cu=INR"
        )
        qr       = QrCodeWidget(url)
        size     = 2.5 * cm
        qr.barWidth  = size
        qr.barHeight = size
        d = Drawing(size, size)
        d.add(qr)
        return d
    except Exception:
        return None


def _build_doc(buffer, pagesize=A4, margins=None):
    """Internal helper — creates a SimpleDocTemplate writing to a BytesIO buffer."""
    if margins is None:
        margins = dict(leftMargin=10*mm, rightMargin=10*mm,
                       topMargin=10*mm, bottomMargin=10*mm)
    return SimpleDocTemplate(buffer, pagesize=pagesize, **margins)


def resolve_pagesize(size_str):
    """
    Converts a string like 'A4', 'A4L', 'A5', 'A5L' to a ReportLab page size tuple.
    A4  = A4 portrait  (210 x 297 mm)
    A4L = A4 landscape (297 x 210 mm)
    A5  = A5 portrait  (148 x 210 mm)
    A5L = A5 landscape (210 x 148 mm)
    """
    mapping = {
        'A4' : A4,
        'A4L': landscape(A4),
        'A5' : A5,
        'A5L': landscape(A5),
    }
    return mapping.get((size_str or 'A4').upper(), A4)


# ─────────────────────────────────────────────
#  SHARED STYLE BUILDER
# ─────────────────────────────────────────────
def _get_invoice_styles(fs=1.0):
    """Returns a dict of all ParagraphStyles. fs=font_scale (0.75 for A5, 1.0 for A4)."""
    base = getSampleStyleSheet()
    def _s(name, fname, size, align=None, leading=None, after=None):
        kw = {'fontName': fname, 'fontSize': round(size * fs)}
        if leading:  kw['leading']    = round(leading * fs)
        if after:    kw['spaceAfter'] = after
        if align is not None: kw['alignment'] = align
        return ParagraphStyle(name, parent=base['Normal'], **kw)
    return {
        'title'        : _s('Title',   FONT_BOLD, 14, TA_CENTER),
        'copy_label'   : _s('CopyLbl', FONT_REG,   9, TA_RIGHT, after=2),
        'header_lbl'   : _s('H_Lbl',  FONT_BOLD,  8, leading=10),
        'header_txt'   : _s('H_Txt',  FONT_REG,   9, leading=11),
        'item_head'    : _s('I_Head', FONT_BOLD,   8, TA_CENTER),
        'item_txt'     : _s('I_Txt',  FONT_REG,    9, TA_LEFT),
        'item_num'     : _s('I_Num',  FONT_REG,    9, TA_RIGHT),
        'item_center'  : _s('I_Ctr',  FONT_REG,    9, TA_CENTER),
        'footer_lbl'   : _s('F_Lbl',  FONT_BOLD,   9, TA_RIGHT, leading=11),
        'footer_val'   : _s('F_Val',  FONT_REG,    9, TA_RIGHT, leading=11),
        'footer_txt'   : _s('F_Txt',  FONT_REG,    9, leading=11),
        'footer_small' : _s('F_Sm',   FONT_REG,    7, leading=9),
    }


# ─────────────────────────────────────────────
#  HELPER: Address Block Builder
# ─────────────────────────────────────────────
def _build_address_block(info, is_seller=False, styles=None):
    """
    Builds a list of Paragraph objects for a seller/buyer address block.
    Works for both company (seller) and buyer dicts.
    """
    S = styles
    lines = [Paragraph(f"<b>{info.get('name', '')}</b>", S['header_txt'])]

    if is_seller:
        if info.get('address_line1'):
            lines.append(Paragraph(info['address_line1'], S['header_txt']))
        if info.get('address_line2'):
            lines.append(Paragraph(info['address_line2'], S['header_txt']))
        lines.append(Paragraph(f"GSTIN: {info.get('gstin', '')}", S['header_txt']))
        lines.append(Paragraph(f"State: {info.get('state', '')}", S['header_txt']))
        lines.append(Paragraph(f"Ph: {info.get('phone', '')}  |  Email: {info.get('email', '')}", S['header_txt']))
    else:
        if info.get('address'):
            lines.append(Paragraph(info['address'], S['header_txt']))
        lines.append(Paragraph(f"GSTIN: {info.get('gstin', '')}", S['header_txt']))
        lines.append(Paragraph(f"State: {info.get('state', '')}", S['header_txt']))

    return lines


# ─────────────────────────────────────────────
#  1. INVOICE PDF  (3 copies: Original / Duplicate / Triplicate)
# ─────────────────────────────────────────────
def create_invoice_pdf(invoice_data, items, settings,
                       previous_balance=0.0, paid_amount=0.0,
                       save_to_disk=True, page_size='A4',
                       is_proforma=False):
    """
    Generates a GST-compliant Tax Invoice PDF with 3 copies.
    For proforma/quotation: set is_proforma=True.
    page_size: 'A4' (default), 'A4L' (landscape), 'A5', 'A5L'

    Parameters:
      invoice_data     : dict — invoice header (from get_full_invoice_details)
      items            : list of dicts — line items
      settings         : dict — company_info, bank_details, invoice_settings
      previous_balance : float — buyer's pending balance before this invoice
      paid_amount      : float — amount paid at time of billing
      save_to_disk     : bool — if True, also saves to /invoices/ folder
      page_size        : str  — 'A4', 'A4L', 'A5', 'A5L'
      is_proforma      : bool — if True, generates Sales Quotation instead of Tax Invoice

    Returns:
      BytesIO — PDF bytes ready for Flask send_file()
    """
    # ── Page geometry ─────────────────────────────────────────────
    # Usable widths: A4=190mm, A4L=277mm, A5=128mm, A5L=190mm
    # We normalise everything relative to A4 (190mm baseline).
    # A5L and A4 have the same usable width (190mm) so scale=1.0.
    # For A4L we keep scale=1.0 — tables stay 190mm, centred on wider page.
    _ps = (page_size or 'A4').upper()
    is_a5_portrait   = (_ps == 'A5')
    is_a5_landscape  = (_ps == 'A5L')
    is_a4_landscape  = (_ps == 'A4L')
    is_a5            = is_a5_portrait or is_a5_landscape
    W_SCALE = 0.67 if is_a5_portrait else 1.0
    # Font scale: smaller for A5 portrait so text fits narrow cells
    FS      = 0.80 if is_a5_portrait else 1.0
    # Margin: tighter for A5 to maximise space
    margins = dict(leftMargin=6*mm, rightMargin=6*mm, topMargin=7*mm, bottomMargin=7*mm) if is_a5_portrait else               dict(leftMargin=8*mm, rightMargin=8*mm, topMargin=8*mm, bottomMargin=8*mm)

    S = _get_invoice_styles(fs=FS)
    buffer = io.BytesIO()
    psize  = resolve_pagesize(_ps)
    doc    = _build_doc(buffer, pagesize=psize, margins=margins)
    elements = []

    c_info = settings.get('company_info', {})
    bank   = settings.get('bank_details', {})
    terms  = settings.get('invoice_settings', {}).get('terms_and_conditions', '')

    if is_proforma:
        copies     = ["SALES QUOTATION"]
        doc_title  = "SALES QUOTATION"
    else:
        copies     = [
            "ORIGINAL FOR RECIPIENT",
            "DUPLICATE FOR TRANSPORTER",
            "TRIPLICATE FOR SUPPLIER",
        ]
        doc_title  = "TAX INVOICE"

    for copy_idx, copy_name in enumerate(copies):
        _copy_start = len(elements)  # track where this copy's elements start

        # ── Copy Header ──────────────────────────────────────────
        elements.append(Paragraph(doc_title, S['title']))
        if not is_proforma:
            elements.append(Paragraph(f"({copy_name})", S['copy_label']))
        else:
            elements.append(Spacer(1, 2))

        # ── Seller Block (with optional logo) ────────────────────
        seller_lines = [Paragraph("<b>Seller:</b>", S['header_lbl'])] + \
                       _build_address_block(c_info, is_seller=True, styles=S)

        logo_path = c_info.get('logo_path', '')
        logo_img  = None
        # Logo size scales with W_SCALE
        _logo_w, _logo_h = 3 * W_SCALE * cm, 2.5 * W_SCALE * cm
        if logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=_logo_w, height=_logo_h)
                logo_img.hAlign = 'RIGHT'
            except Exception:
                pass

        _cell_w  = 9.5 * W_SCALE       # cm — one side of the header table
        _logo_cw = 2.2 * W_SCALE       # cm — logo column when present
        _text_cw = _cell_w - _logo_cw  # cm — text column when logo present

        if logo_img:
            t_text = Table([[line] for line in seller_lines], colWidths=[_text_cw*cm])
            t_text.setStyle(TableStyle([
                ('LEFTPADDING',  (0,0), (-1,-1), 0),
                ('TOPPADDING',   (0,0), (-1,-1), 0),
                ('VALIGN',       (0,0), (-1,-1), 'TOP'),
            ]))
            t_seller = Table([[t_text, logo_img]], colWidths=[_text_cw*cm, _logo_cw*cm])
            t_seller.setStyle(TableStyle([
                ('VALIGN',       (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING',  (0,0), (-1,-1), 2),
                ('TOPPADDING',   (0,0), (-1,-1), 2),
                ('ALIGN',        (1,0), (1,0),   'RIGHT'),
            ]))
        else:
            t_seller = Table([[line] for line in seller_lines], colWidths=[_cell_w*cm])
            t_seller.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 4)]))

        # ── Buyer Block ───────────────────────────────────────────
        b_info = {
            'name'   : invoice_data.get('buyer_name', ''),
            'address': invoice_data.get('buyer_address', ''),
            'gstin'  : invoice_data.get('buyer_gstin', ''),
            'state'  : invoice_data.get('buyer_state', ''),
        }
        buyer_lines = [Paragraph("<b>Buyer:</b>", S['header_lbl'])] + \
                      _build_address_block(b_info, is_seller=False, styles=S)
        t_buyer = Table([[line] for line in buyer_lines], colWidths=[_cell_w*cm])
        t_buyer.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING',  (0,0), (-1,-1), 6),
        ]))

        # ── Invoice Details Block ─────────────────────────────────
        if is_proforma:
            inv_rows = [
                ["Quotation No:", f"<b>{invoice_data.get('invoice_no', invoice_data.get('quotation_no', ''))}</b>"],
                ["Date:",          invoice_data.get('invoice_date', invoice_data.get('quotation_date', ''))],
                ["Mode:",          "Advance"],
                ["Ref:",           invoice_data.get('order_ref', '')],
                ["Valid Until:",   invoice_data.get('valid_until', '')],
            ]
        else:
            inv_rows = [
                ["Invoice No:", f"<b>{invoice_data['invoice_no']}</b>"],
                ["Date:",        invoice_data['invoice_date']],
                ["Mode:",        invoice_data.get('payment_mode', '')],
                ["Ref:",         invoice_data.get('order_ref', '')],
                ["Dispatch:",    invoice_data.get('dispatch_info', '')],
            ]
        _inv_lbl_w = 2.5 * W_SCALE
        _inv_val_w = (_cell_w - _inv_lbl_w)  # fills the remaining cell width
        t_inv = Table(
            [[Paragraph(r[0], S['header_lbl']), Paragraph(r[1], S['header_txt'])]
             for r in inv_rows],
            colWidths=[_inv_lbl_w*cm, _inv_val_w*cm]
        )

        # ── Main Header Layout (Seller | Invoice Details) / (Buyer | empty) ──
        # Use _cell_w (already defined above based on W_SCALE)
        t_head = Table(
            [[t_seller, t_inv],
             [t_buyer,  ""]],
            colWidths=[_cell_w*cm, _cell_w*cm]
        )
        t_head.setStyle(TableStyle([
            ('GRID',   (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN',   (1,1), (1,1)),
        ]))
        elements.append(t_head)

        # ── Items Table ───────────────────────────────────────────
        col_headers = ['S.No.', 'Description', 'HSN', 'GST%', 'Qty', 'Rate', 'Unit', 'Disc%', 'Amount']
        _cw = [1.2, 5.5, 2.2, 1.4, 1.5, 2.1, 1.4, 1.4, 2.3]
        col_widths = [w * W_SCALE * cm for w in _cw]
        table_data   = [[Paragraph(h, S['item_head']) for h in col_headers]]

        gst_analysis = {}
        total_qty    = 0

        for idx, item in enumerate(items):
            row = [
                Paragraph(str(idx + 1),                                  S['item_center']),
                Paragraph(f"<b>{item['description']}</b>",               S['item_txt']),
                Paragraph(item.get('hsn', ''),                           S['item_center']),
                Paragraph(f"{item['gst_rate']}%",                        S['item_center']),
                Paragraph(str(item['quantity']),                          S['item_num']),
                Paragraph(f"{CURRENCY_SYM} {item['rate']:.2f}",          S['item_num']),
                Paragraph(item.get('unit', ''),                           S['item_center']),
                Paragraph(str(item.get('discount_percent', 0)),           S['item_center']),
                Paragraph(f"{CURRENCY_SYM} {item['amount']:.2f}",        S['item_num']),
            ]
            table_data.append(row)
            total_qty += item['quantity']

            # Accumulate GST analysis per HSN+rate combination
            key = (item.get('hsn') or 'NA', item['gst_rate'])
            if key not in gst_analysis:
                gst_analysis[key] = {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0}
            gst_analysis[key]['taxable'] += item['amount']
            tax = item['amount'] * (item['gst_rate'] / 100)
            if invoice_data.get('total_igst', 0) > 0:
                gst_analysis[key]['igst'] += tax
            else:
                gst_analysis[key]['cgst'] += tax / 2
                gst_analysis[key]['sgst'] += tax / 2

        # Totals row
        table_data.append([
            '', Paragraph("<b>Total</b>", S['item_num']),
            '', '',
            Paragraph(f"<b>{total_qty}</b>", S['item_num']),
            '', '', '',
            Paragraph(f"<b>{CURRENCY_SYM} {float(invoice_data.get('subtotal') or 0):.2f}</b>", S['item_num'])
        ])

        t_items = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_items.setStyle(TableStyle([
            ('GRID',        (0,0), (-1,-2), 0.5, colors.black),
            ('BOX',         (0,0), (-1,-1), 0.5, colors.black),
            ('LINEBELOW',   (0,0), (-1,0),  0.5, colors.black),
            ('LINEABOVE',   (0,-1),(-1,-1), 0.5, colors.black),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',  (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ]))
        elements.append(t_items)

        # ── Footer: Amount in Words + Bank Details ────────────────
        try:
            _gt = float(invoice_data.get('grand_total') or 0)
            amt_words = num2words(int(_gt), lang='en_IN').title() + " Only"
        except Exception:
            _gt = float(invoice_data.get('grand_total') or 0)
            amt_words = f"{_gt:.2f} Only"

        # ── Footer: GST Totals + Grand Total ─────────────────────
        right_content = []

        def add_right_row(label, value, bold=False):
            style = S['footer_lbl'] if bold else S['footer_lbl']
            val_style = S['footer_lbl'] if bold else S['footer_val']
            lbl = f"<b>{label}</b>" if bold else label
            right_content.append([
                Paragraph(lbl, style),
                Paragraph(f"{CURRENCY_SYM} {value:.2f}", val_style)
            ])

        # Safe float helper — converts None/empty to 0.0
        def sf(key, default=0.0):
            v = invoice_data.get(key, default)
            try:
                return float(v) if v is not None else default
            except (TypeError, ValueError):
                return default

        is_igst = sf('total_igst') > 0
        if is_igst:
            add_right_row("IGST:", sf('total_igst'))
        else:
            add_right_row("CGST:", sf('total_cgst'))
            add_right_row("SGST:", sf('total_sgst'))

        if sf('freight') > 0:
            add_right_row("Freight:", sf('freight'))
        if sf('round_off') != 0:
            add_right_row("Round Off:", sf('round_off'))

        add_right_row("Grand Total:", sf('grand_total'), bold=True)
        right_content.append([Spacer(1, 4), Spacer(1, 4)])

        paid       = float(paid_amount or 0)
        grand      = float(sf('grand_total') or 0)
        bal_due    = max(0.0, grand - paid)
        prev_bal   = float(previous_balance or 0)

        # ── UPI QR Code (built once, used in bank section) ────────
        upi_id     = settings.get('upi', {}).get('upi_id', '') or ''
        upi_name   = c_info.get('name', '')
        qr_amount  = max(0.0, bal_due + prev_bal)  # total outstanding
        qr_note    = str(invoice_data.get('invoice_no', 'Invoice'))
        qr_drawing = _make_upi_qr(upi_id, upi_name, qr_amount, qr_note)

        # ── Left footer: bank details + optional QR ───────────────
        bank_lines = [
            [Paragraph(f"Amount in words:<br/><b>{amt_words}</b>", S['footer_txt'])],
            [Spacer(1, 4)],
            [Paragraph("<b>Bank Details:</b>", S['footer_txt'])],
        ]
        if bank.get('bank_name'):
            bank_lines.append([Paragraph(f"Bank: {bank.get('bank_name', '')}",  S['footer_txt'])])
        if bank.get('account_no'):
            bank_lines.append([Paragraph(f"A/c:  {bank.get('account_no', '')}",  S['footer_txt'])])
        if bank.get('ifsc_code'):
            bank_lines.append([Paragraph(f"IFSC: {bank.get('ifsc_code', '')}",   S['footer_txt'])])
        if upi_id:
            bank_lines.append([Paragraph(f"UPI:  {upi_id}", S['footer_txt'])])

        _qr_cw   = 3.0 * W_SCALE   # cm — QR column in bank section
        _bank_cw = (9 * W_SCALE) - _qr_cw  # remaining for bank text
        if qr_drawing:
            qr_col = [
                [Paragraph("<b>Scan to Pay</b>",
                           ParagraphStyle('qrl', parent=S['footer_txt'],
                                          alignment=TA_CENTER, fontSize=round(7*FS)))],
                [qr_drawing],
                [Paragraph(f"\u20b9{qr_amount:,.2f}",
                           ParagraphStyle('qra', parent=S['footer_txt'],
                                          alignment=TA_CENTER, fontName=FONT_BOLD, fontSize=round(8*FS)))],
            ]
            bank_tbl   = Table(bank_lines, colWidths=[_bank_cw*cm])
            bank_tbl.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0)]))
            qr_tbl     = Table(qr_col, colWidths=[_qr_cw*cm])
            qr_tbl.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            left_inner = Table([[bank_tbl, qr_tbl]], colWidths=[_bank_cw*cm, _qr_cw*cm])
            left_inner.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            left_content = [[left_inner]]
        else:
            left_content = bank_lines

        _lw = 11 * W_SCALE
        t_left = Table(left_content, colWidths=[_lw*cm])
        t_left.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 4)]))

        # Show paid only if actually paid (partial or full)
        if paid > 0:
            add_right_row("Paid at Billing:", paid)

        if prev_bal > 0:
            add_right_row("Balance Due (This Inv.):", bal_due)
            add_right_row("Prev. Balance:", prev_bal)
            add_right_row("Total Outstanding:", bal_due + prev_bal, bold=True)
        else:
            add_right_row("Total Outstanding:", bal_due, bold=True)

        _r1, _r2 = 4.5 * W_SCALE, 2.5 * W_SCALE
        t_right = Table(right_content, colWidths=[_r1*cm, _r2*cm])
        t_right.setStyle(TableStyle([
            ('ALIGN',   (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN',  (0,0), (-1,-1), 'TOP'),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))

        _fw = 8 * W_SCALE
        t_foot = Table([[t_left, t_right]], colWidths=[_lw*cm, _fw*cm])
        t_foot.setStyle(TableStyle([
            ('BOX',       (0,0), (-1,-1), 0.5, colors.black),
            ('LINEAFTER', (0,0), (0,-1),  0.5, colors.black),
            ('VALIGN',    (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING',(0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))

        # ── HSN/Tax Summary Table ─────────────────────────────────
        footer_group = [t_foot, Spacer(1, 2)]

        h_hsn = (['HSN/SAC', 'Taxable', 'Integrated Tax', 'Total Tax']
                 if is_igst else
                 ['HSN/SAC', 'Taxable', 'Central Tax', 'State Tax', 'Total Tax'])
        _wh_igst   = [w * W_SCALE * cm for w in [4, 4, 5, 6]]
        _wh_cgst   = [w * W_SCALE * cm for w in [2.5, 3.5, 4, 4, 5]]
        w_hsn = _wh_igst if is_igst else _wh_cgst

        d_hsn = [[Paragraph(f"<b>{x}</b>", S['item_center']) for x in h_hsn]]
        tot_taxable = 0
        tot_tax_amt = 0

        for (hsn, rate), v in gst_analysis.items():
            row = [
                Paragraph(hsn,                                            S['item_center']),
                Paragraph(f"{CURRENCY_SYM} {v['taxable']:.2f}",          S['item_num']),
            ]
            row_tax = 0
            if is_igst:
                row.append(Paragraph(f"{rate}% | {CURRENCY_SYM} {v['igst']:.2f}", S['item_num']))
                row_tax += v['igst']
            else:
                row.append(Paragraph(f"{rate/2}% | {CURRENCY_SYM} {v['cgst']:.2f}", S['item_num']))
                row.append(Paragraph(f"{rate/2}% | {CURRENCY_SYM} {v['sgst']:.2f}", S['item_num']))
                row_tax += v['cgst'] + v['sgst']
            row.append(Paragraph(f"<b>{CURRENCY_SYM} {row_tax:.2f}</b>", S['item_num']))
            d_hsn.append(row)
            tot_taxable += v['taxable']
            tot_tax_amt += row_tax

        # HSN Totals Row
        tot_row = [
            Paragraph("<b>Total</b>", S['item_num']),
            Paragraph(f"<b>{CURRENCY_SYM} {tot_taxable:.2f}</b>", S['item_num']),
        ]
        if is_igst:
            tot_row.append(Paragraph(f"<b>{CURRENCY_SYM} {float(invoice_data.get('total_igst') or 0):.2f}</b>", S['item_num']))
        else:
            tot_row.append(Paragraph(f"<b>{CURRENCY_SYM} {invoice_data.get('total_cgst',0):.2f}</b>", S['item_num']))
            tot_row.append(Paragraph(f"<b>{CURRENCY_SYM} {invoice_data.get('total_sgst',0):.2f}</b>", S['item_num']))
        tot_row.append(Paragraph(f"<b>{CURRENCY_SYM} {tot_tax_amt:.2f}</b>", S['item_num']))
        d_hsn.append(tot_row)

        try:
            tax_words = num2words(tot_tax_amt, lang='en_IN').title() + " Only"
        except Exception:
            tax_words = f"{tot_tax_amt:.2f} Only"

        footer_group.append(
            Paragraph(f"Total Tax in words: <b>{tax_words}</b>", S['footer_small'])
        )

        t_hsn = Table(d_hsn, colWidths=w_hsn)
        t_hsn.setStyle(TableStyle([
            ('GRID',       (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0),  colors.lightgrey),
            ('ALIGN',      (0,0), (-1,-1), 'RIGHT'),
        ]))
        footer_group.append(t_hsn)

        # ── Terms & Signature ─────────────────────────────────────
        _s1, _s2 = 10 * W_SCALE, 9 * W_SCALE
        t_sig = Table([[
            Paragraph(f"<b>Terms & Conditions:</b><br/>{terms}", S['footer_small']),
            Paragraph(f"For <b>{c_info.get('name', 'Company')}</b><br/><br/>Authorized Signatory", S['item_num'])
        ]], colWidths=[_s1*cm, _s2*cm])
        t_sig.setStyle(TableStyle([
            ('BOX',          (0,0), (-1,-1), 0.5, colors.black),
            ('LINEAFTER',    (0,0), (0,-1),  0.5, colors.black),
            ('VALIGN',       (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING',   (0,0), (-1,-1), 3),
            ('LEFTPADDING',  (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        footer_group.append(t_sig)

        # For A5/single-copy: wrap the ENTIRE invoice in KeepTogether
        # so header+items+footer never split across pages
        if is_a5 or is_proforma:
            # Replace last elements (since the last append was t_head and t_items)
            # We need to collect all elements for this copy into KeepTogether
            # Find elements added in this copy iteration
            copy_start_idx = _copy_start
            copy_elements  = elements[copy_start_idx:]
            copy_elements.extend(footer_group)
            del elements[copy_start_idx:]
            elements.append(KeepTogether(copy_elements))
        else:
            elements.append(KeepTogether(footer_group))

        # Page break between copies (not after last one)
        if copy_idx < len(copies) - 1:
            elements.append(PageBreak())

    # ── Build PDF into buffer ─────────────────────────────────────
    doc.build(elements)
    buffer.seek(0)

    # Optionally save to disk (for reprint / auto-backup feature)
    if save_to_disk:
        invoices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'invoices')
        os.makedirs(invoices_dir, exist_ok=True)
        # Sanitize invoice_no — remove any chars invalid in filenames
        safe_inv_no = "".join(c if c.isalnum() or c in ('-', '_') else '_'
                               for c in str(invoice_data['invoice_no']))
        filepath = os.path.join(invoices_dir, f"{safe_inv_no}.pdf")
        with open(filepath, 'wb') as f:
            f.write(buffer.read())
        buffer.seek(0)   # Reset so caller can still read it

    return buffer   # BytesIO — use with Flask send_file()


# ─────────────────────────────────────────────
#  2. LEDGER PDF
# ─────────────────────────────────────────────
def create_ledger_pdf(buyer_details, ledger_data, start_date, end_date,
                      settings, save_to_disk=True, page_size='A4'):
    """
    Generates a buyer ledger statement PDF.
    page_size: 'A4', 'A4L', 'A5', 'A5L'

    Parameters:
      buyer_details : dict — buyer name, address, gstin
      ledger_data   : list of dicts — from db.get_buyer_ledger()
      start_date    : str or None
      end_date      : str or None
      settings      : dict — company_info
      save_to_disk  : bool

    Returns:
      BytesIO
    """
    base   = getSampleStyleSheet()
    buffer = io.BytesIO()

    style_title = ParagraphStyle('T',   parent=base['Normal'], fontName=FONT_BOLD, fontSize=16, alignment=TA_CENTER, spaceAfter=10)
    style_th    = ParagraphStyle('TH',  parent=base['Normal'], fontName=FONT_BOLD, fontSize=9,  alignment=TA_CENTER)
    style_td    = ParagraphStyle('TD',  parent=base['Normal'], fontName=FONT_REG,  fontSize=9,  alignment=TA_CENTER)
    style_td_l  = ParagraphStyle('TDL', parent=base['Normal'], fontName=FONT_REG,  fontSize=9,  alignment=TA_LEFT)
    style_td_r  = ParagraphStyle('TDR', parent=base['Normal'], fontName=FONT_REG,  fontSize=9,  alignment=TA_RIGHT)
    style_td_rb = ParagraphStyle('TDB', parent=base['Normal'], fontName=FONT_BOLD, fontSize=9,  alignment=TA_RIGHT)
    style_addr  = ParagraphStyle('A',   parent=base['Normal'], fontName=FONT_REG,  fontSize=9,  alignment=TA_CENTER)

    psize = resolve_pagesize(page_size)
    doc = _build_doc(buffer, pagesize=psize, margins=dict(
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=12*mm,  bottomMargin=12*mm
    ))
    elements = []

    c_info = settings.get('company_info', {})
    elements.append(Paragraph(c_info.get('name', 'My Company'), style_title))
    elements.append(Paragraph(
        f"{c_info.get('address_line1', '')} {c_info.get('address_line2', '')}",
        style_addr
    ))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("<b>LEDGER STATEMENT</b>", style_title))

    # ── Party Info Header ─────────────────────────────────────────
    period = f"Period: {start_date} to {end_date}" if start_date else "All Time"
    info_data = [
        [Paragraph(f"Party: <b>{buyer_details['name']}</b>", base['Normal']),
         Paragraph(period, base['Normal'])],
        [Paragraph(f"Address: {buyer_details.get('address', '')}", base['Normal']),
         Paragraph(f"GSTIN: {buyer_details.get('gstin', '')}", base['Normal'])],
    ]
    elements.append(Table(info_data, colWidths=[10*cm, 9*cm]))
    elements.append(Spacer(1, 0.5*cm))

    # ── Ledger Table ──────────────────────────────────────────────
    headers = ['Date', 'Particulars', 'Vch Type', 'Debit', 'Credit', 'Balance']
    table_data = [[Paragraph(h, style_th) for h in headers]]

    total_debit  = 0
    total_credit = 0

    for entry in ledger_data:
        debit  = entry.get('debit',  0)
        credit = entry.get('credit', 0)
        bal    = entry.get('balance', 0)

        if entry['type'] != 'Opening':
            total_debit  += debit
            total_credit += credit

        table_data.append([
            Paragraph(entry['date'], style_td),
            Paragraph(entry['ref'],  style_td_l),
            Paragraph(entry['type'], style_td),
            Paragraph(f"{debit:.2f}"  if debit  > 0 else "", style_td_r),
            Paragraph(f"{credit:.2f}" if credit > 0 else "", style_td_r),
            Paragraph(
                f"{abs(bal):.2f} {'Dr' if bal >= 0 else 'Cr'}",
                style_td_rb
            ),
        ])

    # Totals / Closing Row
    closing_bal = ledger_data[-1]['balance'] if ledger_data else 0
    table_data.append([
        '',
        Paragraph('<b>Total / Closing Balance</b>', style_td_rb),
        '',
        Paragraph(f"<b>{total_debit:.2f}</b>",  style_td_rb),
        Paragraph(f"<b>{total_credit:.2f}</b>", style_td_rb),
        Paragraph(f"<b>{closing_bal:.2f}</b>",  style_td_rb),
    ])

    t = Table(
        table_data,
        colWidths=[2.5*cm, 6.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm],
        repeatRows=1
    )
    t.setStyle(TableStyle([
        ('GRID',           (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND',     (0,0), (-1,0),  colors.lightgrey),
        ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',     (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 4),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)

    if save_to_disk:
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        safe_name = "".join(c for c in buyer_details['name'] if c.isalnum() or c in ' _').strip()
        filepath = os.path.join(reports_dir, f"Ledger_{safe_name}.pdf")
        with open(filepath, 'wb') as f:
            f.write(buffer.read())
        buffer.seek(0)

    return buffer


# ─────────────────────────────────────────────
#  3. SALES SUMMARY REPORT PDF
# ─────────────────────────────────────────────
def create_transaction_report_pdf(invoices, start_date, end_date,
                                   settings, save_to_disk=True):
    """
    Generates a landscape Sales Summary Report PDF.

    Parameters:
      invoices    : list of dicts — from db.get_invoices_by_filter()
      start_date  : str
      end_date    : str
      settings    : dict
      save_to_disk: bool

    Returns:
      BytesIO
    """
    base   = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc    = _build_doc(buffer, pagesize=landscape(A4))
    elements = []

    elements.append(Paragraph(
        f"<b>Sales Summary Report</b> ({start_date} to {end_date})",
        base['Title']
    ))
    elements.append(Spacer(1, 0.5*cm))

    headers = ['Date', 'Invoice No', 'Buyer', 'Payment Mode', 'Taxable', 'GST', 'Grand Total']
    data = [[Paragraph(f"<b>{h}</b>", base['Normal']) for h in headers]]

    total_taxable    = 0
    total_gst        = 0
    total_grand      = 0
    invoice_count    = 0

    for inv in invoices:
        if '[CANCELLED]' in str(inv.get('invoice_no', '')):
            continue
        data.append([
            inv['invoice_date'],
            inv['invoice_no'],
            inv['buyer_name'],
            inv.get('payment_mode', ''),
            f"{inv['taxable_value']:.2f}",
            f"{inv['total_gst']:.2f}",
            f"{inv['grand_total']:.2f}",
        ])
        total_taxable += inv['taxable_value']
        total_gst     += inv['total_gst']
        total_grand   += inv['grand_total']
        invoice_count += 1

    # Totals row
    data.append([
        '', f"Total: {invoice_count} invoices", '', '',
        Paragraph(f"<b>{total_taxable:.2f}</b>", base['Normal']),
        Paragraph(f"<b>{total_gst:.2f}</b>",     base['Normal']),
        Paragraph(f"<b>{total_grand:.2f}</b>",   base['Normal']),
    ])

    t = Table(
        data,
        colWidths=[2.5*cm, 3.5*cm, 8*cm, 2.5*cm, 3*cm, 2.5*cm, 3.5*cm],
        repeatRows=1
    )
    t.setStyle(TableStyle([
        ('GRID',       (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0),  colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.Color(0.95, 0.95, 1)]),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)

    if save_to_disk:
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        filepath = os.path.join(reports_dir, "Summary_Report.pdf")
        with open(filepath, 'wb') as f:
            f.write(buffer.read())
        buffer.seek(0)

    return buffer


# ─────────────────────────────────────────────
#  4. DETAILED ITEM-WISE REPORT PDF
# ─────────────────────────────────────────────
def create_detailed_invoice_report(invoice_ids, settings, save_to_disk=True):
    """
    Generates a landscape Detailed Item-wise Report PDF.
    One row per line item across all selected invoices.

    Parameters:
      invoice_ids  : list of int — invoice IDs to include
      settings     : dict
      save_to_disk : bool

    Returns:
      BytesIO
    """
    base   = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc    = _build_doc(buffer, pagesize=landscape(A4))
    elements = []

    elements.append(Paragraph("<b>Detailed Item-Wise Sales Report</b>", base['Title']))
    elements.append(Spacer(1, 0.5*cm))

    headers = ['Date', 'Invoice No', 'Buyer', 'Item', 'HSN', 'GST%', 'Qty', 'Rate', 'Disc%', 'Amount']
    data = [[Paragraph(f"<b>{h}</b>", base['Normal']) for h in headers]]

    total_amount = 0

    for inv_id in invoice_ids:
        inv, items = db.get_full_invoice_details(inv_id)
        if not inv or '[CANCELLED]' in inv.get('invoice_no', ''):
            continue
        for item in items:
            data.append([
                inv['invoice_date'],
                inv['invoice_no'],
                inv['buyer_name'],
                item['description'],
                item.get('hsn', ''),
                f"{item['gst_rate']}%",
                str(item['quantity']),
                f"{item['rate']:.2f}",
                f"{item.get('discount_percent', 0)}%",
                f"{item['amount']:.2f}",
            ])
            total_amount += item['amount']

    # Grand total row
    data.append([
        '', '', '', '', '', '', '', '',
        Paragraph('<b>Total:</b>', base['Normal']),
        Paragraph(f"<b>{total_amount:.2f}</b>", base['Normal']),
    ])

    t = Table(
        data,
        colWidths=[2.2*cm, 2.8*cm, 4.5*cm, 5.5*cm, 1.5*cm, 1.2*cm, 1.5*cm, 2*cm, 1.3*cm, 2.5*cm],
        repeatRows=1
    )
    t.setStyle(TableStyle([
        ('GRID',       (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0),  colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.Color(0.95, 0.95, 1)]),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)

    if save_to_disk:
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        filepath = os.path.join(reports_dir, "Detailed_Report.pdf")
        with open(filepath, 'wb') as f:
            f.write(buffer.read())
        buffer.seek(0)

    return buffer


# ─────────────────────────────────────────────
#  QUICK TEST (run directly: python pdf_generator.py)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import database_manager as db
    db.create_tables()

    print(f"Fonts loaded  → Regular: {FONT_REG} | Bold: {FONT_BOLD} | Symbol: {CURRENCY_SYM}")
    print("pdf_generator.py is ready for Flask integration.")
    print()
    print("Usage in Flask route:")
    print("  from pdf_generator import create_invoice_pdf, get_pdf_response")
    print("  pdf_bytes = create_invoice_pdf(inv, items, settings)")
    print("  return get_pdf_response(pdf_bytes, 'INV-0001.pdf')")
