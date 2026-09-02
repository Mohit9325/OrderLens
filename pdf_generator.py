import io
import base64
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Template
from PIL import Image

# 1. Absolute Path Resolution using pathlib
PROJECT_ROOT = Path(__file__).resolve().parent

def get_base64_image_from_file(filename: str, resize_height: int = None) -> str:
    """
    Finds file in project root or assets subfolder using absolute Path resolution,
    reads in binary mode ('rb'), and converts directly to a base64 data URI string.
    """
    candidate_paths = [
        PROJECT_ROOT / filename,
        PROJECT_ROOT / "assets" / filename,
        Path.cwd() / filename,
        Path.cwd() / "assets" / filename
    ]
    
    for file_path in candidate_paths:
        try:
            if file_path.exists() and file_path.is_file():
                if resize_height:
                    with Image.open(file_path) as img:
                        # Paste onto a 600x600 transparent canvas to lock proportions
                        canvas = Image.new('RGBA', (600, 600), (255, 255, 255, 0))
                        img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                        x = (600 - img.width) // 2
                        y = (600 - img.height) // 2
                        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                            canvas.paste(img, (x, y), img)
                        else:
                            canvas.paste(img, (x, y))
                        
                        buffered = io.BytesIO()
                        canvas.save(buffered, format="PNG")
                        encoded_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        return f"data:image/png;base64,{encoded_b64}"
                else:
                    with Image.open(file_path) as img:
                        bbox = img.getbbox()
                        if bbox:
                            img = img.crop(bbox)
                        buffered = io.BytesIO()
                        img.save(buffered, format="PNG")
                        encoded_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        return f"data:image/png;base64,{encoded_b64}"
        except Exception as e:
            print(f"Error reading image {file_path}: {e}")
            
    return ""


def get_absolute_image_path(filename: str) -> Optional[str]:
    """Resolves absolute path string for ReportLab Image flowable."""
    candidate_paths = [
        PROJECT_ROOT / filename,
        PROJECT_ROOT / "assets" / filename,
        Path.cwd() / filename,
        Path.cwd() / "assets" / filename
    ]
    for file_path in candidate_paths:
        if file_path.exists() and file_path.is_file():
            return str(file_path.resolve())
    return None


# 2. Official AI Turing Technologies A4 Document HTML Template (Crimson Red Theme)
HTML_DOCUMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {{ po.po_number }}</title>
    <style>
        @page {
            size: A4;
            margin: 12mm 14mm 12mm 14mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8pt;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #64748B;
            }
        }
        
        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #1E293B;
            margin: 0;
            padding: 0;
            font-size: 9pt;
            line-height: 1.35;
            background-color: #FFFFFF;
        }

        .header-table {
            width: 100%;
            border-collapse: collapse;
            border-bottom: 2.5px solid #B91C1C;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }

        .header-left {
            width: 55%;
            vertical-align: middle;
            text-align: left;
        }





        .header-right {
            width: 45%;
            text-align: right;
            vertical-align: middle;
        }

        .po-badge-box {
            display: inline-block;
            background-color: #B91C1C;
            color: #FFFFFF;
            padding: 5px 12px;
            border-radius: 4px;
            font-weight: 800;
            font-size: 13pt;
            letter-spacing: 0.5px;
            line-height: 1.1;
        }

        .po-number-text {
            font-weight: 700;
            font-size: 10.5pt;
            color: #B91C1C;
            margin-top: 3px;
        }


        .po-status-badge {
            display: inline-block;
            background-color: #FEF2F2;
            color: #991B1B;
            font-size: 7.5pt;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            margin-top: 3px;
            border: 1px solid #FECACA;
        }

        .address-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 14px;
        }

        .address-card {
            width: 48%;
            vertical-align: top;
            padding: 10px 12px;
            background-color: #F8FAFC;
            border-radius: 6px;
            border: 1px solid #E2E8F0;
            border-top: 3px solid #B91C1C;
        }

        .card-label {
            font-size: 7.5pt;
            font-weight: 800;
            color: #B91C1C;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .party-heading {
            font-size: 10.5pt;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 3px;
        }

        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 14px;
        }

        .items-table th {
            background-color: #B91C1C;
            color: #FFFFFF;
            font-size: 8pt;
            font-weight: 700;
            text-transform: uppercase;
            padding: 7px 8px;
            text-align: left;
        }

        .items-table td {
            padding: 6px 8px;
            border-bottom: 1px solid #E2E8F0;
            font-size: 8.5pt;
        }

        .items-table tr:nth-child(even) {
            background-color: #F8FAFC;
        }

        .text-right {
            text-align: right;
        }

        .text-center {
            text-align: center;
        }

        .summary-wrapper {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 14px;
        }

        .summary-table {
            width: 42%;
            margin-left: auto;
            border-collapse: collapse;
        }

        .summary-table td {
            padding: 4px 6px;
            font-size: 8.5pt;
        }

        .grand-total-box {
            font-size: 10.5pt;
            font-weight: 800;
            background-color: #F8FAFC;
            color: #000000;
            border-top: 2px solid #000000;
            border-bottom: 2px solid #000000;
        }

        .terms-card {
            background-color: #F8FAFC;
            border-left: 4px solid #B91C1C;
            padding: 8px 12px;
            border-radius: 0 6px 6px 0;
            margin-bottom: 16px;
            font-size: 8pt;
            color: #475569;
        }

        .terms-title {
            font-weight: 800;
            font-size: 7.5pt;
            color: #1E293B;
            text-transform: uppercase;
            margin-bottom: 3px;
        }

        .signature-table {
            width: 100%;
            border-collapse: collapse;
            border-top: 1px dashed #CBD5E1;
            padding-top: 10px;
            margin-top: 8px;
        }

        .sig-left-cell {
            width: 50%;
            vertical-align: top;
            padding-top: 8px;
        }

        .sig-right-cell {
            width: 50%;
            text-align: right;
            vertical-align: top;
            padding-top: 4px;
        }

        .stamp-signature-img {
            height: 70px;
            width: auto;
            max-width: 180px;
            object-fit: contain;
            margin-bottom: -6px;
            display: inline-block;
        }

        .company-seal-name {
            font-size: 9.5pt;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 4px;
        }

        .sig-auth-line {
            width: 220px;
            border-bottom: 1.5px solid #0F172A;
            margin-left: auto;
            margin-top: 2px;
            margin-bottom: 4px;
        }
    </style>
</head>
<body>

    <!-- Header with Absolute Base64 Logo -->
    <table style="width: 100%; border-collapse: collapse; border: none; margin: 0 0 8px 0; padding: 0;">
        <tr>
            <td style="width: 360px; border: none; vertical-align: middle; text-align: left; padding: 0;">
                <img src="data:image/png;base64,{{ logo_base64 }}" style="height: 63px; width: auto; object-fit: contain; display: block; margin: 0; padding: 0;" />
            </td>
            <td style="text-align: right; border: none; vertical-align: middle; padding: 0;">
                <span style="font-size: 22px; font-weight: bold; color: #111; line-height: 1.1;">PURCHASE ORDER</span><br>
                <span style="font-size: 13px; color: #333; font-weight: 600;">#{{ po.po_number }}</span><br>
                <span style="font-size: 11px; color: #555; font-weight: bold;">STATUS: {{ po.status|default('APPROVED')|upper }}</span>
            </td>
        </tr>
    </table>

    <!-- Address Parties -->
    <table class="address-table">
        <tr>
            <td class="address-card">
                <div class="card-label">SUPPLIER DETAILS</div>
                <div class="party-heading">{{ po.vendor_name }}</div>
                <div>{{ po.vendor_address or 'Address not specified' }}</div>
                <div>Email: {{ po.vendor_email or 'N/A' }} | Phone: {{ po.vendor_phone or 'N/A' }}</div>
            </td>
            <td style="width: 4%;"></td>
            <td class="address-card">
                <div class="card-label">SHIPMENT DETAILS</div>
                <div class="party-heading">AiTuring Technologies Private Limited</div>
                <div style="font-size: 8pt; line-height: 1.3;">
                    13/8, MIDC Phase III Main Rd, Phase 3, Hinjewadi Rajiv Gandhi Infotech Park, Hinjewadi, Pune, 411057<br>
                    GSTN: 27AAYCA6417E1ZD | Contact: +91-7741827349
                </div>
                <div style="margin-top: 6px; font-size: 8.5pt;">
                    PO Date: <strong>{{ po.po_date }}</strong> | Currency: <strong>USD ($)</strong><br>
                    Ref. No: <strong>{{ po.ref_no or 'N/A' }}</strong>
                </div>
            </td>
        </tr>
    </table>

    <!-- Line Items Table -->
    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 5%;">#</th>
                <th style="width: 45%;">Item Description</th>
                <th style="width: 10%; text-align: center;">Qty</th>
                <th style="width: 14%; text-align: right;">Unit Rate</th>
                <th style="width: 14%; text-align: right;">Catalog Rate</th>
                <th style="width: 12%; text-align: right;">Total Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>
                    <strong>{{ item.description }}</strong>
                    {% if item.catalog_sku and item.catalog_sku != 'N/A' %}
                    <br><span style="font-size: 7.5pt; color: #64748B;">SKU: {{ item.catalog_sku }}</span>
                    {% endif %}
                </td>
                <td class="text-center">{{ item.quantity }}</td>
                <td class="text-right">${{ "{:,.2f}".format(item.rate or item.unit_price) }}</td>
                <td class="text-right">
                    {% if item.catalog_rate %}
                    ${{ "{:,.2f}".format(item.catalog_rate) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td class="text-right"><strong>${{ "{:,.2f}".format(item.total or item.total_price) }}</strong></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Summary Box -->
    <table class="summary-wrapper">
        <tr>
            <td style="width: 55%;"></td>
            <td style="width: 45%;">
                <table class="summary-table">
                    <tr>
                        <td>Subtotal:</td>
                        <td class="text-right">${{ "{:,.2f}".format(po.subtotal) }}</td>
                    </tr>
                    <tr>
                        <td>Tax Amount:</td>
                        <td class="text-right">${{ "{:,.2f}".format(po.tax_amount) }}</td>
                    </tr>
                    <tr>
                        <td>Shipping & Handling:</td>
                        <td class="text-right">${{ "{:,.2f}".format(po.shipping_amount) }}</td>
                    </tr>
                    <tr class="grand-total-box">
                        <td style="text-align: right; font-weight: bold; color: #111;">GRAND TOTAL:</td>
                        <td style="text-align: right; font-weight: bold; color: #111;">${{ "{:,.2f}".format(po.grand_total) }}</td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    <!-- Commercial Terms -->
    <div class="terms-card">
        <div class="terms-title">Commercial Terms & Conditions</div>
        <div>{{ po.terms_and_conditions or 'Standard Payment Terms: Net 30 Days from receipt of verified delivery.' }}</div>
    </div>

    <!-- Official Signature Block with Base64 Digital Stamp -->
    <table class="signature-table">
        <tr>
            <td class="sig-left-cell">
                <!-- Left blank as requested -->
            </td>
            <td class="sig-right-cell">
                <div class="company-seal-name">For, AiTuring Technologies Private Limited</div>
                <div style="height: 80px; margin-top: 10px; margin-bottom: 10px;">
                    <!-- Blank space for physical stamp -->
                </div>
                <div class="sig-auth-line"></div>
                <div style="font-weight: 700; font-size: 8.5pt; color: #0F172A;">Authorized Signatory</div>
                <!-- Removed CPO title -->
            </td>
        </tr>
    </table>

    <!-- Company Footer -->
    <div style="margin-top: 40px; text-align: center; font-size: 8.5pt; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 15px;">
        Email: info@aituring.ai &nbsp;|&nbsp; CIN: U46529PN2023PTC220275 &nbsp;|&nbsp; Website: www.aituring.ai
    </div>

</body>
</html>
"""

def generate_po_html(po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> str:
    """Renders HTML template with embedded base64 branding assets using absolute paths."""
    subtotal = float(po_data.get('subtotal') or sum(float(it.get('total') or (float(it.get('quantity', 1)) * float(it.get('rate', 0)))) for it in items_data))
    tax_amount = float(po_data.get('tax_amount') or 0.0)
    shipping_amount = float(po_data.get('shipping_amount') or 0.0)
    grand_total = float(po_data.get('grand_total') or (subtotal + tax_amount + shipping_amount))
    
    clean_po = {
        "po_number": po_data.get("po_number") or po_data.get("po_number_suggestion") or f"PO-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}",
        "vendor_name": po_data.get("vendor_name") or "Vendor Name",
        "vendor_address": po_data.get("address") or po_data.get("vendor_address") or "",
        "vendor_email": po_data.get("email") or po_data.get("vendor_email") or "",
        "vendor_phone": po_data.get("phone") or po_data.get("vendor_phone") or "",
        "po_date": str(po_data.get("po_date") or datetime.date.today()),
        "terms_and_conditions": po_data.get("terms_and_conditions") or "Standard Payment Terms: Net 30 Days.",
        "status": po_data.get("status") or "APPROVED",
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "shipping_amount": shipping_amount,
        "grand_total": grand_total
    }
    
    clean_items = []
    for it in items_data:
        qty = float(it.get("quantity", 1.0))
        rate = float(it.get("rate", it.get("unit_price", 0.0)))
        cat_rate = float(it.get("catalog_rate", 0.0))
        tot = float(it.get("total", it.get("total_price", qty * rate)))
        clean_items.append({
            "description": it.get("description", "Item Description"),
            "catalog_sku": it.get("catalog_sku", "N/A"),
            "quantity": qty,
            "rate": rate,
            "unit_price": rate,
            "catalog_rate": cat_rate,
            "total": tot,
            "total_price": tot
        })

    # Explicitly load and encode logo1.png to raw base64 string
    logo1_path = PROJECT_ROOT / "logo1.png"
    if not logo1_path.exists():
        logo1_path = Path.cwd() / "logo1.png"
        
    logo_b64 = ""
    try:
        with open(logo1_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error reading logo1.png: {e}")

    stamp_b64 = get_base64_image_from_file("stamp.png")

    template = Template(HTML_DOCUMENT_TEMPLATE)
    return template.render(
        po=clean_po,
        items=clean_items,
        logo_base64=logo_b64,
        stamp_base64=stamp_b64
    )


def generate_po_pdf(po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> bytes:
    """
    Compiles verified PO data into an official A4 PDF document.
    Uses WeasyPrint with automatic fallback to ReportLab.
    """
    try:
        import weasyprint
        html_content = generate_po_html(po_data, items_data)
        pdf_bytes = weasyprint.HTML(string=html_content, base_url=str(PROJECT_ROOT)).write_pdf()
        if pdf_bytes and len(pdf_bytes) > 0:
            return pdf_bytes
    except Exception:
        pass

    # Robust ReportLab Generation Fallback
    return generate_reportlab_pdf(po_data, items_data)


def generate_reportlab_pdf(po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> bytes:
    """
    Generates official AI Turing Technologies A4 PDF with ReportLab matching the Crimson Red palette.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    COLOR_PRIMARY = colors.HexColor("#0F172A")
    COLOR_CRIMSON = colors.HexColor("#B91C1C")
    COLOR_LIGHT = colors.HexColor("#F8FAFC")
    COLOR_TEXT = colors.HexColor("#1E293B")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=COLOR_PRIMARY,
        fontName='Helvetica-Bold'
    )

    po_num_style = ParagraphStyle(
        'PONumber',
        parent=styles['Heading2'],
        fontSize=13,
        leading=15,
        alignment=2,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )

    # 1. Header with Absolute Logo Image
    logo_path = get_absolute_image_path("logo1.png")
    header_logo = None
    if logo_path:
        try:
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(logo_path)
            iw, ih = img_reader.getSize()
            target_height = 1.25 * inch
            target_width = (iw / float(ih)) * target_height
            
            # Cap width to avoid pushing table out of bounds
            if target_width > 4.4 * inch:
                target_width = 4.4 * inch
                target_height = (ih / float(iw)) * target_width
                
            header_logo = RLImage(logo_path, width=target_width, height=target_height)
        except Exception:
            header_logo = None




    if header_logo is None:
        header_logo = Paragraph("<b>AI TURING</b> <font color='#B91C1C'>TECHNOLOGIES</font>", title_style)

    po_info_para = Paragraph(
        f"<b>PURCHASE ORDER</b><br/><font size=10 color='#000000'>#{po_data.get('po_number', 'PO-001')}</font><br/><font size=7.5 color='#000000'>STATUS: {po_data.get('status', 'APPROVED').upper()}</font>",
        po_num_style
    )

    header_table = Table([[header_logo, po_info_para]], colWidths=[4.6*inch, 2.6*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))

    story = [header_table]
    story.append(HRFlowable(width="100%", thickness=2.5, color=COLOR_CRIMSON, spaceAfter=12))

    # 2. Party Details
    party_title = ParagraphStyle('PartyTitle', fontName='Helvetica-Bold', fontSize=7.5, textColor=COLOR_CRIMSON)
    party_body = ParagraphStyle('PartyBody', fontName='Helvetica', fontSize=8.5, leading=11, textColor=COLOR_TEXT)

    vendor_text = f"""
    <b>{po_data.get('vendor_name', 'Vendor')}</b><br/>
    {po_data.get('vendor_address', po_data.get('address', 'Address N/A'))}<br/>
    Email: {po_data.get('vendor_email', po_data.get('email', 'N/A'))} | Phone: {po_data.get('vendor_phone', po_data.get('phone', 'N/A'))}
    """
    
    buyer_text = f"""
    <b>AiTuring Technologies Private Limited</b><br/>
    <font size=8>13/8, MIDC Phase III Main Rd, Phase 3, Hinjewadi Rajiv Gandhi Infotech Park, Hinjewadi, Pune, 411057<br/>
    GSTN: 27AAYCA6417E1ZD | Contact: +91-7741827349</font><br/>
    PO Date: <b>{po_data.get('po_date', datetime.date.today())}</b> | Currency: <b>USD ($)</b><br/>
    Ref. No: <b>{po_data.get('ref_no', 'N/A')}</b>
    """

    address_data = [
        [Paragraph("SUPPLIER DETAILS", party_title), Paragraph("SHIPMENT DETAILS", party_title)],
        [Paragraph(vendor_text, party_body), Paragraph(buyer_text, party_body)]
    ]

    address_table = Table(address_data, colWidths=[3.5*inch, 3.5*inch])
    address_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_LIGHT),
        ('BOX', (0,0), (0,1), 1, colors.HexColor("#CBD5E1")),
        ('BOX', (1,0), (1,1), 1, colors.HexColor("#CBD5E1")),
        ('LINEABOVE', (0,0), (1,0), 2.5, COLOR_CRIMSON),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(address_table)
    story.append(Spacer(1, 10))

    # 3. Line Items Table with Crimson Headers
    th_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.white)
    td_style = ParagraphStyle('TD', fontName='Helvetica', fontSize=8, leading=10, textColor=COLOR_TEXT)
    td_bold = ParagraphStyle('TDBold', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=COLOR_TEXT, alignment=2)

    items_table_data = [
        [Paragraph("<b>#</b>", th_style), Paragraph("<b>Item Description</b>", th_style), Paragraph("<b>Qty</b>", th_style), Paragraph("<b>Unit Rate</b>", th_style), Paragraph("<b>Cat. Rate</b>", th_style), Paragraph("<b>Total</b>", th_style)]
    ]

    for idx, item in enumerate(items_data, 1):
        desc = f"<b>{item.get('description', 'Item')}</b>"
        if item.get('catalog_sku') and item.get('catalog_sku') != 'N/A':
            desc += f"<br/><font size=6.5 color='#64748B'>SKU: {item.get('catalog_sku')}</font>"
            
        rate = float(item.get('rate', item.get('unit_price', 0.0)))
        cat_rate = float(item.get('catalog_rate', 0.0))
        tot = float(item.get('total', item.get('total_price', rate * float(item.get('quantity', 1)))))
        
        items_table_data.append([
            Paragraph(str(idx), td_style),
            Paragraph(desc, td_style),
            Paragraph(str(item.get('quantity', 1)), td_style),
            Paragraph(f"${rate:,.2f}", td_style),
            Paragraph(f"${cat_rate:,.2f}" if cat_rate > 0 else "-", td_style),
            Paragraph(f"<b>${tot:,.2f}</b>", td_bold)
        ])

    items_table = Table(items_table_data, colWidths=[0.3*inch, 3.2*inch, 0.6*inch, 1.0*inch, 1.0*inch, 0.9*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_CRIMSON),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_LIGHT]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Summary Calculation
    subtotal = float(po_data.get('subtotal') or sum(float(it.get('total', float(it.get('quantity', 1)) * float(it.get('rate', 0)))) for it in items_data))
    tax = float(po_data.get('tax_amount') or 0.0)
    shipping = float(po_data.get('shipping_amount') or 0.0)
    grand_total = float(po_data.get('grand_total') or (subtotal + tax + shipping))

    summary_data = [
        [Paragraph("Subtotal:", td_style), Paragraph(f"${subtotal:,.2f}", td_bold)],
        [Paragraph("Tax Amount:", td_style), Paragraph(f"${po_data.get('tax_amount', 0.0):,.2f}", td_bold)],
        [Paragraph("Shipping & Handling:", td_style), Paragraph(f"${shipping:,.2f}", td_bold)],
        [Paragraph("<b>GRAND TOTAL:</b>", ParagraphStyle('GT', fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.black)), 
         Paragraph(f"<b>${grand_total:,.2f}</b>", ParagraphStyle('GTB', fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.black, alignment=2))]
    ]

    summary_table = Table(summary_data, colWidths=[1.8*inch, 1.4*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,3), (1,3), 2, colors.black),
        ('BACKGROUND', (0,3), (1,3), colors.HexColor("#F8FAFC")),
        ('PADDING', (0,0), (-1,-1), 3.5),
    ]))

    story.append(Table([[Paragraph("", td_style), summary_table]], colWidths=[3.8*inch, 3.2*inch]))
    story.append(Spacer(1, 10))

    # 5. Terms
    terms_text = f"<b>COMMERCIAL TERMS & CONDITIONS</b><br/><font color='#475569'>{po_data.get('terms_and_conditions', 'Standard Payment Terms: Net 30 Days.')}</font>"
    terms_table = Table([[Paragraph(terms_text, party_body)]], colWidths=[7.0*inch])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_LIGHT),
        ('LINELEFT', (0,0), (-1,-1), 3.5, COLOR_CRIMSON),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(terms_table)
    story.append(Spacer(1, 10))

    # 6. Signature Block with Absolute Digital Stamp Asset
    sig_left_text = ""

    stamp_element = Spacer(1, 0.95*inch)

    sig_right_data = [
        [Paragraph("<b>For, AiTuring Technologies Private Limited</b>", party_body)],
        [stamp_element],
        [Paragraph("_______________________________<br/><b>Authorized Signatory</b><br/>", party_body)]
    ]
    sig_right_table = Table(sig_right_data, colWidths=[3.4*inch])
    sig_right_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 1),
    ]))

    sig_table = Table([[Paragraph(sig_left_text, party_body), sig_right_table]], colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(sig_table)
    
    # 7. Company Footer
    story.append(Spacer(1, 40))
    footer_text = "<para align=center><font size=8.5 color='#64748B'>Email: info@aituring.ai &nbsp;|&nbsp; CIN: U46529PN2023PTC220275 &nbsp;|&nbsp; Website: www.aituring.ai</font></para>"
    story.append(Paragraph(footer_text, styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
