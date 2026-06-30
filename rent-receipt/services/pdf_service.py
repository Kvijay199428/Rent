import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from num2words import num2words

def generate_professional_pdf(data, landlord_config, output_path):
    # Ensure parent dir exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Border
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2.0, height - 70, "RENT RECEIPT")
    
    # Decorative line
    c.setLineWidth(2)
    c.line(40, height - 85, width - 40, height - 85)
    
    # Receipt Details Top Right / Left
    c.setFont("Helvetica", 11)
    y = height - 120
    c.drawString(50, y, f"Receipt No: {data['Bill']}")
    c.drawRightString(width - 50, y, f"Date: {data['Date']}")
    y -= 20
    c.drawString(50, y, f"Billing Month: {data['Month']}")
    
    c.setLineWidth(1)
    y -= 15
    c.line(40, y, width - 40, y)
    
    # Landlord & Tenant details side-by-side
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "LANDLORD")
    c.drawString(width/2 + 20, y, "TENANT")
    
    c.setFont("Helvetica", 10)
    # Landlord
    y -= 15
    c.drawString(50, y, f"Name: {landlord_config.get('name', '')}")
    # Tenant
    tenant_name = data.get('Tenant', '')
    c.drawString(width/2 + 20, y, f"Name: {tenant_name}")
    
    y -= 15
    c.drawString(50, y, f"Phone: {landlord_config.get('phone', '')}")
    c.drawString(width/2 + 20, y, f"Phone: {data.get('Tenant_Phone', '')}")
    
    y -= 15
    c.drawString(50, y, f"Email: {landlord_config.get('email', '')}")
    # Render address or company for Tenant
    company = data.get('Tenant_Company', '')
    if company:
        c.drawString(width/2 + 20, y, f"Company: {company}")
        y -= 15
        
    c.drawString(50, y, f"Address: {landlord_config.get('address', '')}")
    # Tenant Address
    tenant_addr = data.get('Tenant_Address', '')
    # Wrap address text if long
    c.drawString(width/2 + 20, y, f"Address: {tenant_addr[:40]}")
    if len(tenant_addr) > 40:
        y -= 12
        c.drawString(width/2 + 65, y, tenant_addr[40:80])
        
    y -= 20
    c.line(40, y, width - 40, y)
    
    # Table Description Header
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "DESCRIPTION")
    c.drawRightString(width - 60, y, "AMOUNT (₹)")
    
    y -= 10
    c.line(50, y, width - 50, y)
    
    # Table Content
    items = [
        ("Rent", float(data.get('Rent', 0))),
        ("Additional Person Charges", float(data.get('Additional', 0))),
        ("Water Charges", float(data.get('Water', 0))),
        ("Electricity Charges", float(data.get('Electricity', 0)))
    ]
    
    c.setFont("Helvetica", 11)
    for name, amt in items:
        y -= 20
        c.drawString(60, y, name)
        c.drawRightString(width - 60, y, f"₹{amt:,.2f}")
        
    y -= 15
    c.line(50, y, width - 50, y)
    
    # Total
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "TOTAL")
    c.drawRightString(width - 60, y, f"₹{float(data.get('Total', 0)):,.2f}")
    
    y -= 15
    c.line(40, y, width - 40, y)
    
    # Electricity Details
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Electricity Details")
    
    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(50, y, f"Previous Reading: {data.get('Previous', 0)}")
    c.drawString(width/2, y, f"Current Reading: {data.get('Current', 0)}")
    y -= 15
    c.drawString(50, y, f"Consumed: {data.get('Units', 0)} units")
    rate = data.get('Rate', landlord_config.get('electricity_rate', 15.0))
    c.drawString(width/2, y, f"Rate: ₹{rate}/unit")
    
    y -= 20
    c.line(40, y, width - 40, y)
    
    # Amount in words
    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Amount in Words:")
    c.setFont("Helvetica-Oblique", 11)
    try:
        total_float = float(data['Total'])
        words = num2words(total_float, lang='en_IN').replace(',', '').title()
        c.drawString(160, y, f"Rupees {words} Only")
    except Exception:
        c.drawString(160, y, f"{data['Total']}")
        
    # Signature
    y -= 60
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 60, y, "________________________")
    y -= 15
    c.drawRightString(width - 60, y, "Landlord Signature")
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 60, y, landlord_config.get('name', ''))
    
    c.showPage()
    c.save()
    return output_path
