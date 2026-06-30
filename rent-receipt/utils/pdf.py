import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from num2words import num2words

def generate_pdf(data, config, output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2.0, height - 50, "RENT RECEIPT")
    
    # Header Info
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Receipt No : {data['Bill']}")
    c.drawRightString(width - 50, height - 100, f"Date : {data['Date']}")
    
    c.drawString(50, height - 130, "Tenant :")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 145, str(data['Tenant']))
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 175, "Address :")
    c.setFont("Helvetica-Bold", 12)
    address_lines = config.get('property_address', '').split('\n')
    y_offset = 190
    for line in address_lines:
        c.drawString(50, height - y_offset, line)
        y_offset += 15
        
    y_offset += 15
    c.setLineWidth(1)
    c.line(50, height - y_offset, width - 50, height - y_offset)
    y_offset += 25
    
    # Details
    c.setFont("Helvetica", 12)
    curr = "₹"
    
    c.drawString(50, height - y_offset, "Rent")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Rent']}")
    y_offset += 20
    
    # In web app, we don't have "Additional Persons" count, just "Additional" charge directly in data, or maybe we do.
    # Let's just output Additional Charge
    c.drawString(50, height - y_offset, "Additional Charges")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Additional']}")
    y_offset += 20
    
    c.drawString(50, height - y_offset, "Water")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Water']}")
    y_offset += 30
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - y_offset, "Electricity")
    c.setFont("Helvetica", 12)
    y_offset += 20
    
    c.drawString(50, height - y_offset, f"Previous Reading {data['Previous']}")
    y_offset += 15
    c.drawString(50, height - y_offset, f"Current Reading {data['Current']}")
    y_offset += 15
    c.drawString(50, height - y_offset, f"Units Consumed {data['Units']}")
    y_offset += 15
    rate = config.get('electricity_rate', 0)
    c.drawString(50, height - y_offset, f"Rate {curr}{rate}")
    c.drawRightString(width - 50, height - y_offset, f"Electricity Charge {curr}{data['Electricity']}")
    y_offset += 25
    
    c.line(50, height - y_offset, width - 50, height - y_offset)
    y_offset += 25
    
    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - y_offset, "TOTAL")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Total']}")
    y_offset += 30
    
    # Words
    c.setFont("Helvetica-Oblique", 12)
    try:
        total_float = float(data['Total'])
        words = num2words(total_float, lang='en_IN').replace(',', '').title()
        c.drawString(50, height - y_offset, f"Rupees {words} Only")
    except Exception:
        c.drawString(50, height - y_offset, f"Amount in words: {data['Total']}")
        
    y_offset += 60
    
    # Signature
    c.setFont("Helvetica", 12)
    c.drawRightString(width - 50, height - y_offset, "________________________")
    y_offset += 15
    c.drawRightString(width - 50, height - y_offset, "Landlord Signature")
    y_offset += 15
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 50, height - y_offset, config.get('landlord_name', ''))
    y_offset += 15
    c.setFont("Helvetica", 10)
    phone = config.get('landlord_phone', '')
    email = config.get('landlord_email', '')
    if phone:
        c.drawRightString(width - 50, height - y_offset, f"Ph: {phone}")
        y_offset += 12
    if email:
        c.drawRightString(width - 50, height - y_offset, f"Email: {email}")
        
    c.showPage()
    c.save()
    return output_path
