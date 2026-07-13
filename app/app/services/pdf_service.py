import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from num2words import num2words
from datetime import datetime
import sys
from app.core.paths import UPLOADS_DIR
from app.services.tenant_service import load_tenants
from app.core.config_service import config

font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.fonts')

FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_ITALIC = 'Helvetica-Oblique'

try:
    pdfmetrics.registerFont(TTFont('NotoSans', os.path.join(font_dir, 'NotoSans-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoSans-Bold', os.path.join(font_dir, 'NotoSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('NotoSans-Italic', os.path.join(font_dir, 'NotoSans-Italic.ttf')))
    FONT_REGULAR = FONT_REGULAR
    FONT_BOLD = FONT_BOLD
    FONT_ITALIC = FONT_ITALIC
except Exception as e:
    print(f"WARNING: Missing custom fonts in {font_dir}. PDFs may generate without the ? symbol. Error: {e}", file=sys.stderr)

def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def generate_professional_pdf(data, landlord_config, output_path=None):
    # Live Tenant Sync Engine: Override PDF with the most current tenant attributes
    tenants = load_tenants()
    tenantName = data.get('Tenant', 'Unknown')
    current_tenant = next((t for t in tenants if t.name == tenantName), None)
    if current_tenant:
        data['Tenant_Phone'] = current_tenant.phone
        data['Tenant_Company'] = current_tenant.company
        data['Tenant_Address'] = current_tenant.address

    is_stream = False
    if output_path is None:
        output_path = io.BytesIO()
        is_stream = True
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    tenantName = data.get('Tenant', 'Unknown')
    billNo = data.get('Bill', '000')
    date_str = data.get('Date') or ''
    try:
        date_obj = datetime.strptime(str(date_str), "%d %B %Y")
        formatted_date = date_obj.strftime("%Y%m%d")
    except Exception:
        formatted_date = str(date_str).replace(" ", "")

    safe_tenantName = tenantName.replace(" ", "_")
    pdf_title = f"{safe_tenantName}_{formatted_date}_{billNo}"
    c.setTitle(pdf_title)
    
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)
    
    c.setFont(FONT_BOLD, 24)
    c.drawCentredString(width / 2.0, height - 70, "RENT RECEIPT")
    
    c.setLineWidth(2)
    c.line(40, height - 85, width - 40, height - 85)
    
    c.setFont(FONT_REGULAR, 11)
    y = height - 105
    c.drawString(50, y, f"Receipt No: {data['Bill']}")
    c.drawCentredString(width / 2.0, y, f"Billing Month: {data['Month']}")
    c.drawRightString(width - 50, y, f"Date: {data['Date']}")
    y -= 15
    
    
    c.setLineWidth(1)
    y -= 10
    c.line(40, y, width - 40, y)
    
    y -= 15 
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_normal.fontName = FONT_REGULAR
    style_normal.fontSize = 10
    style_normal.leading = 14
    
    style_heading = ParagraphStyle('Heading', parent=style_normal, fontName=FONT_BOLD, fontSize=12, spaceAfter=8)
    
    landlord_html = f"<b>Name:</b> {landlord_config.get('name', '')}<br/>" \
                    f"<b>Phone:</b> {landlord_config.get('phone', '')}<br/>" \
                    f"<b>Email:</b> {landlord_config.get('email', '')}<br/>" \
                    f"<b>Address:</b> {landlord_config.get('address', '')}<br/>" \
                    
    tenant_html = f"<b>Name:</b> {data.get('Tenant', '')}<br/>" \
                  f"<b>Phone:</b> {data.get('Tenant_Phone', '')}<br/>"
    company = data.get('Tenant_Company', '')
    if company:
        tenant_html += f"<b>Company:</b> {company}<br/>"
    tenant_html += f"<b>Address:</b> {data.get('Tenant_Address', '')}"
    
    p_landlord_title = Paragraph("LANDLORD", style_heading)
    p_landlord_body = Paragraph(landlord_html, style_normal)
    
    p_tenant_title = Paragraph("TENANT", style_heading)
    p_tenant_body = Paragraph(tenant_html, style_normal)
    
    card_width = (width - 100 - 20) / 2.0 
    
    table = Table([[ [p_landlord_title, p_landlord_body], "", [p_tenant_title, p_tenant_body] ]], 
                  colWidths=[card_width, 20, card_width])
                  
    table.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 1, colors.black),
        ('BOX', (2,0), (2,0), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    
    tw, th = table.wrapOn(c, width, height)
    y -= th
    table.drawOn(c, 50, y)
    
    y -= 25
    c.setLineWidth(1)
    c.line(40, y, width - 40, y)
    
    y -= 25
    c.setFont(FONT_BOLD, 12)
    c.drawString(60, y, "DESCRIPTION")
    c.drawRightString(width - 60, y, "AMOUNT")
    
    y -= 10
    c.line(50, y, width - 50, y)
    
    items = []
    
    rent = _safe_float(data.get('Rent'))
    items.append(("Rent", "", rent))
        
    add_charge = _safe_float(data.get('Additional'))
    add_count = _safe_int(data.get("Additional_Persons"))
    add_rate = _safe_float(data.get("additionalPersonRate"))
    items.append(("Additional Person Charges", f"{add_count} Persons x ₹{add_rate:,.2f}", add_charge))
            
    water = _safe_float(data.get('Water'))
    items.append(("Water Charges", "", water))
        
    tankWater = _safe_float(data.get('tankWater'))
    items.append(("Tank Water Charges", "", tankWater))
        
    maintenance = _safe_float(data.get('MaintenanceCharge'))
    if maintenance > 0:
        desc = data.get('MaintenanceDesc', '')
        items.append(("Maintenance Charges", desc, maintenance))
        
    electricity = _safe_float(data.get('Electricity'))
    units = _safe_float(data.get('Units'))
    rate = _safe_float(data.get('Rate'))
    prev = data.get('Previous', '')
    curr = data.get('Current', '')
    
    if prev == '' and curr == '':
        items.append(("Electricity Charges", f"{units:g} Units x ₹{rate:,.2f}", electricity))
    else:
        items.append(("Electricity Charges", f"{prev}-{curr} = {units:g} Units x ₹{rate:,.2f}", electricity))

    for title, subtitle, amt in items:
        y -= 20
        c.setFont(FONT_REGULAR, 11)
        c.drawString(60, y, title)
        c.drawRightString(width - 60, y, f"     {amt:,.2f}")
        if subtitle:
            y -= 15
            c.setFont(FONT_REGULAR, 10)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(60, y, subtitle)
            c.setFillColorRGB(0, 0, 0)
        
    y -= 15
    c.line(50, y, width - 50, y)
    
    curr_total = _safe_float(data.get('Total'))
    prev_arr = _safe_float(data.get('previousArrears'))
    grandTotal = curr_total + prev_arr
    amt_recv = _safe_float(data.get('amountReceived'), grandTotal)
    balance = grandTotal - amt_recv

    y -= 20
    c.setFont(FONT_REGULAR, 11)
    c.drawString(60, y, "CURRENT MONTH TOTAL")
    c.drawRightString(width - 60, y, f"     {curr_total:,.2f}")

    if prev_arr != 0:
        y -= 15
        c.setFont(FONT_REGULAR, 11)
        c.drawString(60, y, "PREVIOUS ARREARS" if prev_arr > 0 else "PREVIOUS ADVANCE")
        c.drawRightString(width - 60, y, f"     {abs(prev_arr):,.2f}")

    y -= 15
    c.line(40, y, width - 40, y)

    y -= 20
    c.setFont(FONT_BOLD, 12)
    c.drawString(60, y, "GRAND TOTAL")
    c.drawRightString(width - 60, y, f"     {grandTotal:,.2f}")

    if amt_recv != grandTotal:
        # y -= 15
        # c.setFont(FONT_REGULAR, 11)
        # c.drawString(60, y, "AMOUNT RECEIVED")
        # c.drawRightString(width - 60, y, f"     {amt_recv:,.2f}")
        
        # if balance > 0:
        #     y -= 15
        #     c.setFont(FONT_BOLD, 11)
        #     c.drawString(60, y, "BALANCE DUE")
        #     c.drawRightString(width - 60, y, f"     {balance:,.2f}")
        if balance < 0:
            y -= 15
            c.setFont(FONT_BOLD, 11)
            c.drawString(60, y, "ADVANCE AMOUNT")
            c.drawRightString(width - 60, y, f"     {abs(balance):,.2f}")

    y -= 15
    c.line(40, y, width - 40, y)
    
    y -= 25
    c.setFont(FONT_BOLD, 11)
    c.drawString(50, y, "Amount in Words:")
    c.setFont(FONT_ITALIC, 11)
    try:
        total_float = grandTotal
        words = num2words(total_float, lang='en_IN').replace(',', '').title()
        
        amount_style = ParagraphStyle('Amount', parent=style_normal, fontName=FONT_ITALIC, fontSize=11)
        p_amount = Paragraph(f"Rupees {words} Only", amount_style)
        pw, ph = p_amount.wrapOn(c, width - 200, height)
        y -= ph - 11 
        p_amount.drawOn(c, 160, y)
    except Exception:
        c.drawString(160, y, f"{total_float}")
        
    bank_acc_no = str(landlord_config.get("bank_account_number") or "").strip()
    # pyrefly: ignore [bad-keyword-argument]
    if bank_acc_no and config.get("receipt", "toggles.show_bank_details", default=True):
        y -= 25
        if landlord_config.get("mask_bank_account", True):
            if len(bank_acc_no) > 4:
                masked_no = "X" * (len(bank_acc_no) - 4) + bank_acc_no[-4:]
            else:
                masked_no = "XXXX"
        else:
            masked_no = bank_acc_no
            
        box_y = y - 90
        box_width = 320
        c.setLineWidth(1)
        c.rect(50, box_y, box_width, 90)
        
        c.setFont(FONT_BOLD, 10)
        c.drawString(60, box_y + 75, "PAYMENT DETAILS")
        c.line(50, box_y + 70, 50 + box_width, box_y + 70)
        
        c.setFont(FONT_REGULAR, 10)
        c.drawString(60, box_y + 53, f"Account Holder     : {landlord_config.get('bank_account_name', '')}")
        c.drawString(60, box_y + 38, f"Account Number   : {masked_no}")
        c.drawString(60, box_y + 23, f"Bank Name           : {landlord_config.get('bank_name', '')}")
        
        branch = str(landlord_config.get('bank_branch') or '')
        ifsc = str(landlord_config.get('bank_ifsc') or '')
        branch_ifsc = []
        if branch: branch_ifsc.append(branch)
        if ifsc: branch_ifsc.append(ifsc)
        
        c.drawString(60, box_y + 8, f"Branch & IFSC      : {' - '.join(branch_ifsc)}")
        
        y = box_y
        
    # Move down for the signature, but clamp 'y' to a minimum of 90 
    # to prevent overlapping the footer (y=40) and outer border (y=30)
    y -= 50
    if y < 90:
        y = 90
    
    sig_filename = landlord_config.get('signature_image', '')
    # pyrefly: ignore [bad-keyword-argument]
    if sig_filename and config.get("receipt", "toggles.show_signature", default=True):
        sig_img_path = os.path.join(UPLOADS_DIR, sig_filename)
        
        if os.path.exists(sig_img_path):
            try:
                from reportlab.lib.utils import ImageReader
                from PIL import Image
                
                pil_img = Image.open(sig_img_path).convert("RGBA")
                background = Image.new('RGBA', pil_img.size, (255, 255, 255, 255))
                alpha_composite = Image.alpha_composite(background, pil_img)
                final_img = alpha_composite.convert('RGB')
                
                img = ImageReader(final_img)
                max_w, max_h = 160, 60
                img_w, img_h = img.getSize()
                
                aspect = img_w / float(img_h)
                if (max_w / aspect) <= max_h:
                    new_w = max_w
                    new_h = max_w / aspect
                else:
                    new_h = max_h
                    new_w = max_h * aspect
                    
                c.drawImage(img, width - 60 - new_w, y, width=new_w, height=new_h, preserveAspectRatio=True)
                y -= 15
            except Exception as e:
                print(f"Error drawing signature image: {e}")
                c.setFont(FONT_REGULAR, 11)
                c.drawRightString(width - 60, y, "________________________")
                y -= 15
        else:
            print(f"Warning: Signature image configured but not found at {sig_img_path}")
            c.setFont(FONT_REGULAR, 11)
            c.drawRightString(width - 60, y, "________________________")
            y -= 15
    else:
        c.setFont(FONT_REGULAR, 11)
        c.drawRightString(width - 60, y, "________________________")
        y -= 15
        
    c.setFont(FONT_REGULAR, 11)
    sig_text = landlord_config.get('signature_text', '')
    if sig_text:
        c.drawRightString(width - 60, y, sig_text)
    else:
        c.drawRightString(width - 60, y, "Authorized Signature")
        
    y -= 15
    c.setFont(FONT_BOLD, 11)
    c.drawRightString(width - 60, y, landlord_config.get('name', ''))
    
    status = data.get('Status', 'ACTIVE')
    
    c.setFont(FONT_REGULAR, 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(40, 40, f"Receipt Status : {status}")
    if status == 'ARCHIVED':
        archived_date = data.get('Archived_Date', '')
        c.drawString(160, 40, f"Archived : {archived_date}")
        
    gen_date = data.get("Date", "")
    c.drawRightString(width / 2.0 + 30, 40, f"Generated : {gen_date}")
    c.drawRightString(width - 40, 40, f"Receipt No : {data['Bill']}")
    
    c.showPage()
    c.save()
    
    if is_stream:
        output_path.seek(0)
        return output_path
        
    return output_path

