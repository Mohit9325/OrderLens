import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_sample_quote_pdf(output_path="sample_data/vendor_quote_apex_ai.pdf"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#0F172A'))
    h2_style = ParagraphStyle('H2Style', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#2563EB'))
    body_style = ParagraphStyle('BodyStyle', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#334155'))

    story = []
    story.append(Paragraph("APEX AI ENTERPRISE SYSTEMS LTD", title_style))
    story.append(Paragraph("700 Silicon Valley Way, Suite 400, San Jose, CA 95110 | Tel: +1 (408) 555-0199 | sales@apexai-systems.com", body_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("OFFICIAL COMMERCIAL QUOTATION # QUOTE-APX-9942", h2_style))
    story.append(Paragraph("Date: September 1, 2026 | Valid Until: September 30, 2026", body_style))
    story.append(Paragraph("Customer: AI Turing Technologies Ltd | Project: Enterprise AI Cluster Expansion Phase 2", body_style))
    story.append(Spacer(1, 15))

    th_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)
    td_style = ParagraphStyle('TD', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))

    data = [
        [Paragraph("Item Description", th_style), Paragraph("Qty", th_style), Paragraph("Unit Rate ($)", th_style), Paragraph("Subtotal ($)", th_style)],
        [Paragraph("NVIDIA H100 80GB SXM5 GPU Accelerator", td_style), Paragraph("4", td_style), Paragraph("33,000.00", td_style), Paragraph("132,000.00", td_style)],
        [Paragraph("Supermicro 4U 8-GPU AI Workstation Server", td_style), Paragraph("1", td_style), Paragraph("46,500.00", td_style), Paragraph("46,500.00", td_style)],
        [Paragraph("Mellanox Quantum-2 InfiniBand 400G Switch 64-Port", td_style), Paragraph("2", td_style), Paragraph("18,900.00", td_style), Paragraph("37,800.00", td_style)],
        [Paragraph("400G OSFP Active Optical Cable 5m", td_style), Paragraph("12", td_style), Paragraph("480.00", td_style), Paragraph("5,760.00", td_style)],
        [Paragraph("Micron 7450 PRO 7.68TB NVMe PCIe 4.0 Enterprise SSD", td_style), Paragraph("8", td_style), Paragraph("875.00", td_style), Paragraph("7,000.00", td_style)]
    ]

    t = Table(data, colWidths=[3.5*inch, 0.6*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT')
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    terms_text = """
    <b>COMMERCIAL TERMS & CONDITIONS:</b><br/>
    1. Payment Terms: 50% advance upon PO placement, 50% upon dispatch (Net 30 Days).<br/>
    2. Delivery: 10 to 14 business days from PO approval.<br/>
    3. Freight & Taxes: Standard 18% Tax added at checkout. Freight included.<br/>
    4. Warranty: 3-Year Factory Direct Replacement Warranty included.
    """
    story.append(Paragraph(terms_text, body_style))
    doc.build(story)
    print(f"Sample PDF created at {output_path}")

if __name__ == "__main__":
    generate_sample_quote_pdf()
