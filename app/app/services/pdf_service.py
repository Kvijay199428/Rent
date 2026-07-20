import io
import os
import sys
from datetime import datetime
from xml.sax.saxutils import escape

from num2words import num2words
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

try:
    from app.core.paths import UPLOADS_DIR
except Exception:
    try:
        from app.core.paths import UPLOADSDIR as UPLOADS_DIR
    except Exception:
        UPLOADS_DIR = ""

try:
    from app.core.config_service import config
except Exception:
    try:
        from app.core.config_service import config
    except Exception:
        config = None

try:
    from app.services.tenant_service import get_tenant as _get_tenant
except Exception:
    try:
        from app.services.tenant_service import get_tenant as _get_tenant
    except Exception:
        _get_tenant = None


font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".fonts")

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

try:
    pdfmetrics.registerFont(TTFont("NotoSans", os.path.join(font_dir, "NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold", os.path.join(font_dir, "NotoSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSans-Italic", os.path.join(font_dir, "NotoSans-Italic.ttf")))
    FONT_REGULAR = "NotoSans"
    FONT_BOLD = "NotoSans-Bold"
    FONT_ITALIC = "NotoSans-Italic"
except Exception as e:
    print(
        f"WARNING: Missing custom fonts in {font_dir}. Falling back to Helvetica. Error: {e}",
        file=sys.stderr,
    )

CURRENCY_SYMBOL = "₹" if FONT_REGULAR.startswith("NotoSans") else "Rs."


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


def _currency(value):
    return f"{CURRENCY_SYMBOL}{_safe_float(value):,.2f}"


def _clean_text(value):
    if value is None:
        return ""
    return escape(str(value)).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _p(text, style):
    return Paragraph(_clean_text(text), style)


def _config_get(section, key=None, default=None):
    if config is None:
        return default

    attempts = []
    if key is None:
        attempts.append((section,))
    else:
        attempts.append((section, key))
        attempts.append((f"{section}.{key}",))

    for args in attempts:
        try:
            return config.get(*args, default=default)
        except TypeError:
            try:
                return config.get(*args)
            except Exception:
                pass
        except Exception:
            pass

    return default


def _mask_account_number(account_number, mask=True):
    account_number = str(account_number or "").strip()
    if not account_number:
        return ""
    if not mask:
        return account_number
    if len(account_number) <= 4:
        return "X" * len(account_number)
    return "X" * (len(account_number) - 4) + account_number[-4:]


def _build_key_value_table(rows, total_width, label_width, label_style, value_style, top_padding=0):
    colon_width = 10
    value_width = max(total_width - label_width - colon_width, 40)

    data = []
    for label, value in rows:
        data.append(
            [
                _p(label, label_style),
                _p(":", label_style),
                _p(value, value_style),
            ]
        )

    table = Table(data, colWidths=[label_width, colon_width, value_width])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), top_padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _build_info_card(title, rows, width, title_style, label_style, value_style):
    inner_width = width - 20
    kv_table = _build_key_value_table(
        rows=rows,
        total_width=inner_width,
        label_width=58,
        label_style=label_style,
        value_style=value_style,
        top_padding=1,
    )

    card = Table(
        [
            [_p(title, title_style)],
            [kv_table],
        ],
        colWidths=[width],
    )
    card.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 10),
                ("BOTTOMPADDING", (0, 0), (0, 0), 6),
                ("TOPPADDING", (0, 1), (0, 1), 0),
                ("BOTTOMPADDING", (0, 1), (0, 1), 10),
            ]
        )
    )
    return card


def generate_professional_pdf(data, landlord_config, output_path=None):
    tenant_id = data.get("TenantId") or data.get("tenantId")
    current_tenant = _get_tenant(tenant_id) if tenant_id and _get_tenant else None

    if current_tenant:
        data["Tenant_Phone"] = getattr(current_tenant, "phone", "") or data.get("Tenant_Phone", "")
        data["Tenant_Company"] = getattr(current_tenant, "company", "") or data.get("Tenant_Company", "")
        data["Tenant_Address"] = getattr(current_tenant, "address", "") or data.get("Tenant_Address", "")

    is_stream = False
    if output_path is None:
        output_path = io.BytesIO()
        is_stream = True
    else:
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    tenant_name = data.get("Tenant", "Unknown")
    bill_no = data.get("Bill", "000")
    date_str = data.get("Date") or ""
    try:
        date_obj = datetime.strptime(str(date_str), "%d %B %Y")
        formatted_date = date_obj.strftime("%Y%m%d")
    except Exception:
        formatted_date = str(date_str).replace(" ", "")

    safe_tenant_name = str(tenant_name).replace(" ", "_")
    pdf_title = f"{safe_tenant_name}_{formatted_date}_{bill_no}"
    c.setTitle(pdf_title)

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle(
        "PdfNormal",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=10,
        leading=13,
        textColor=colors.black,
        spaceAfter=0,
    )
    style_label = ParagraphStyle(
        "PdfLabel",
        parent=style_normal,
        fontName=FONT_BOLD,
    )
    style_heading = ParagraphStyle(
        "PdfHeading",
        parent=style_normal,
        fontName=FONT_BOLD,
        fontSize=12,
        leading=14,
        spaceAfter=0,
    )
    style_subtle = ParagraphStyle(
        "PdfSubtle",
        parent=style_normal,
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#666666"),
    )
    style_amount_words = ParagraphStyle(
        "PdfAmountWords",
        parent=style_normal,
        fontName=FONT_ITALIC,
        fontSize=11,
        leading=14,
    )

    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)

    c.setFont(FONT_BOLD, 24)
    c.drawCentredString(width / 2.0, height - 70, "RENT RECEIPT")

    c.setLineWidth(2)
    c.line(40, height - 85, width - 40, height - 85)

    c.setFont(FONT_REGULAR, 11)
    y = height - 105
    c.drawString(50, y, f"Receipt No: {data.get('Bill', '')}")
    c.drawCentredString(width / 2.0, y, f"Billing Month : {data.get('Month', '')}")
    c.drawRightString(width - 50, y, f"Date: {data.get('Date', '')}")

    y -= 25
    c.setLineWidth(1)
    c.line(40, y, width - 40, y)

    landlord_rows = [
        ("Name", landlord_config.get("name", "")),
        ("Phone", landlord_config.get("phone", "")),
        ("Email", landlord_config.get("email", "")),
        ("Address", landlord_config.get("address", "")),
    ]

    tenant_rows = [
        ("Name", data.get("Tenant", "")),
        ("Phone", data.get("Tenant_Phone", "")),
    ]
    company = data.get("Tenant_Company", "")
    if company:
        tenant_rows.append(("Company", company))
    tenant_rows.append(("Address", data.get("Tenant_Address", "")))

    card_width = (width - 100 - 20) / 2.0

    landlord_card = _build_info_card(
        title="LANDLORD",
        rows=landlord_rows,
        width=card_width,
        title_style=style_heading,
        label_style=style_label,
        value_style=style_normal,
    )
    tenant_card = _build_info_card(
        title="TENANT",
        rows=tenant_rows,
        width=card_width,
        title_style=style_heading,
        label_style=style_label,
        value_style=style_normal,
    )

    party_table = Table(
        [[landlord_card, "", tenant_card]],
        colWidths=[card_width, 20, card_width],
    )
    party_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (0, 0), 1, colors.black),
                ("BOX", (2, 0), (2, 0), 1, colors.black),
            ]
        )
    )

    tw, th = party_table.wrapOn(c, width, height)
    y -= 15
    y -= th
    party_table.drawOn(c, 50, y)

    y -= 25
    c.line(40, y, width - 40, y)

    y -= 25
    c.setFont(FONT_BOLD, 12)
    c.drawString(60, y, "DESCRIPTION")
    c.drawRightString(width - 60, y, "AMOUNT")

    y -= 10
    c.line(50, y, width - 50, y)

    items = []

    rent = _safe_float(data.get("Rent"))
    if rent:
        items.append(("Rent", "", rent))

    add_charge = _safe_float(data.get("Additional"))
    add_count = _safe_int(data.get("Additional_Persons"))
    add_rate = _safe_float(data.get("additionalPersonRate"))
    if add_charge:
        subtitle = f"{add_count} Persons x {_currency(add_rate)}" if add_count or add_rate else ""
        items.append(("Additional Person Charges", subtitle, add_charge))

    water = _safe_float(data.get("Water"))
    if water:
        items.append(("Water Charges", "", water))

    tank_water = _safe_float(data.get("tankWater"))
    if tank_water:
        items.append(("Tank Water Charges", "", tank_water))

    maintenance = _safe_float(data.get("MaintenanceCharge"))
    if maintenance > 0:
        items.append(("Maintenance Charges", data.get("MaintenanceDesc", ""), maintenance))

    electricity = _safe_float(data.get("Electricity"))
    units = _safe_float(data.get("Units"))
    rate = _safe_float(data.get("Rate"))
    prev = data.get("Previous", "")
    curr = data.get("Current", "")
    if electricity or units or rate:
        if prev == "" and curr == "":
            subtitle = f"{units:g} Units x {_currency(rate)}"
        else:
            subtitle = f"{prev} - {curr} = {units:g} Units x {_currency(rate)}"
        items.append(("Electricity Charges", subtitle, electricity))

    for title, subtitle, amt in items:
        y -= 20
        c.setFont(FONT_REGULAR, 11)
        c.drawString(60, y, title)
        c.drawRightString(width - 60, y, f"{amt:,.2f}")

        if subtitle:
            y -= 14
            subtitle_p = _p(subtitle, style_subtle)
            pw, ph = subtitle_p.wrapOn(c, width - 140, 40)
            subtitle_p.drawOn(c, 60, y - (ph - 10))
            y -= max(ph - 10, 0)

    y -= 15
    c.line(50, y, width - 50, y)

    curr_total = _safe_float(data.get("Total"))
    prev_arr = _safe_float(data.get("previousArrears"))
    grand_total = curr_total + prev_arr
    amt_recv = _safe_float(data.get("amountReceived"), grand_total)
    balance = grand_total - amt_recv

    y -= 20
    c.setFont(FONT_REGULAR, 11)
    c.drawString(60, y, "CURRENT MONTH TOTAL")
    c.drawRightString(width - 60, y, f"{curr_total:,.2f}")

    if prev_arr != 0:
        y -= 15
        c.setFont(FONT_REGULAR, 11)
        c.drawString(60, y, "PREVIOUS ARREARS" if prev_arr > 0 else "PREVIOUS ADVANCE")
        c.drawRightString(width - 60, y, f"{abs(prev_arr):,.2f}")

    y -= 15
    c.line(40, y, width - 40, y)

    y -= 20
    c.setFont(FONT_BOLD, 12)
    c.drawString(60, y, "GRAND TOTAL")
    c.drawRightString(width - 60, y, f"{grand_total:,.2f}")

    if balance < 0:
        y -= 15
        c.setFont(FONT_BOLD, 11)
        c.drawString(60, y, "ADVANCE AMOUNT")
        c.drawRightString(width - 60, y, f"{abs(balance):,.2f}")

    y -= 15
    c.line(40, y, width - 40, y)

    y -= 25
    c.setFont(FONT_BOLD, 11)
    c.drawString(50, y, "Amount in Words:")
    try:
        words = num2words(grand_total, lang="en_IN").replace(",", "").title()
        amount_p = Paragraph(f"Rupees {escape(words)} Only", style_amount_words)
        pw, ph = amount_p.wrapOn(c, width - 200, height)
        amount_p.drawOn(c, 160, y - (ph - 11))
        y -= max(ph - 11, 0)
    except Exception:
        c.setFont(FONT_ITALIC, 11)
        c.drawString(160, y, f"{grand_total:,.2f}")

    bank_acc_no = str(landlord_config.get("bank_account_number") or "").strip()
    show_bank_details = bool(_config_get("receipt", "toggles.show_bank_details", True))

    if bank_acc_no and show_bank_details:
        y -= 25

        masked_no = _mask_account_number(
            bank_acc_no,
            mask=bool(landlord_config.get("mask_bank_account", True)),
        )

        branch = str(landlord_config.get("bank_branch") or "").strip()
        ifsc = str(landlord_config.get("bank_ifsc") or "").strip()
        branch_ifsc = " - ".join([part for part in [branch, ifsc] if part])

        payment_rows = [
            ("Account Holder", landlord_config.get("bank_account_name", "") or landlord_config.get("name", "")),
            ("Account Number", masked_no),
            ("Bank Name", landlord_config.get("bank_name", "")),
            ("Branch & IFSC", branch_ifsc),
        ]

        payment_table = _build_key_value_table(
            rows=payment_rows,
            total_width=300,
            label_width=92,
            label_style=style_label,
            value_style=style_normal,
            top_padding=0,
        )

        ptw, pth = payment_table.wrapOn(c, 300, 100)
        box_width = 320
        box_height = max(90, pth + 30)
        box_y = y - box_height

        c.setLineWidth(1)
        c.rect(50, box_y, box_width, box_height)
        c.setFont(FONT_BOLD, 10)
        c.drawString(60, box_y + box_height - 15, "PAYMENT DETAILS")
        c.line(50, box_y + box_height - 20, 50 + box_width, box_y + box_height - 20)

        payment_table.drawOn(c, 60, box_y + 8)
        y = box_y

    y -= 50
    if y < 90:
        y = 90

    sig_filename = landlord_config.get("signature_image", "")
    show_signature = bool(_config_get("receipt", "toggles.show_signature", True))

    if sig_filename and show_signature:
        sig_img_path = os.path.join(UPLOADS_DIR, sig_filename)

        if os.path.exists(sig_img_path):
            try:
                from PIL import Image
                from reportlab.lib.utils import ImageReader

                pil_img = Image.open(sig_img_path).convert("RGBA")
                background = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
                alpha_composite = Image.alpha_composite(background, pil_img)
                final_img = alpha_composite.convert("RGB")

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

                c.drawImage(
                    img,
                    width - 60 - new_w,
                    y,
                    width=new_w,
                    height=new_h,
                    preserveAspectRatio=True,
                )
                y -= 15
            except Exception as e:
                print(f"Error drawing signature image: {e}", file=sys.stderr)
                c.setFont(FONT_REGULAR, 11)
                c.drawRightString(width - 60, y, "________________________")
                y -= 15
        else:
            print(f"Warning: Signature image not found at {sig_img_path}", file=sys.stderr)
            c.setFont(FONT_REGULAR, 11)
            c.drawRightString(width - 60, y, "________________________")
            y -= 15
    else:
        c.setFont(FONT_REGULAR, 11)
        c.drawRightString(width - 60, y, "________________________")
        y -= 15

    c.setFont(FONT_REGULAR, 11)
    sig_text = landlord_config.get("signature_text", "")
    c.drawRightString(width - 60, y, sig_text or "Authorized Signature")

    y -= 15
    c.setFont(FONT_BOLD, 11)
    c.drawRightString(width - 60, y, landlord_config.get("name", ""))

    status = data.get("Status", "ACTIVE")

    c.setFont(FONT_REGULAR, 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(40, 40, f"Receipt Status : {status}")
    if status == "ARCHIVED":
        archived_date = data.get("Archived_Date", "")
        c.drawString(160, 40, f"Archived : {archived_date}")

    gen_date = data.get("Date", "")
    c.drawRightString(width / 2.0 + 30, 40, f"Generated : {gen_date}")
    c.drawRightString(width - 40, 40, f"Receipt No : {data.get('Bill', '')}")

    c.showPage()
    c.save()

    if is_stream:
        output_path.seek(0)
        return output_path

    return output_path


generateprofessionalpdf = generate_professional_pdf
