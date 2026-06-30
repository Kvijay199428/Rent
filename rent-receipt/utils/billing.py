import os
from datetime import datetime
from pydantic import BaseModel
from .config_manager import load_config, save_config
from .csv_manager import save_receipt_data, update_receipt, get_receipt
from .pdf import generate_pdf

class BillRequest(BaseModel):
    tenant: str
    month: str
    current_reading: float
    additional_persons: int

def process_bill(request: BillRequest):
    config = load_config()
    
    rent = float(config.get("default_rent", 0))
    water = float(config.get("water_charge", 0))
    prev_reading = float(config.get("previous_meter_reading", 0))
    rate = float(config.get("electricity_rate", 0))
    add_person_charge = float(config.get("additional_person_charge", 0))
    
    consumed_units = max(0.0, request.current_reading - prev_reading)
    electricity_charge = consumed_units * rate
    
    total_additional_charge = request.additional_persons * add_person_charge
    total = rent + total_additional_charge + water + electricity_charge
    
    bill_no = str(config.get("next_bill_number", 1)).zfill(3)
    date_str = datetime.now().strftime("%d-%m-%Y")
    
    pdf_filename = f"{bill_no}.pdf"
    pdf_dir = "receipts"
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    data_dict = {
        "Bill": bill_no,
        "Date": date_str,
        "Month": request.month,
        "Tenant": request.tenant,
        "Previous": prev_reading,
        "Current": request.current_reading,
        "Units": consumed_units,
        "Rent": rent,
        "Additional": total_additional_charge,
        "Water": water,
        "Electricity": electricity_charge,
        "Total": total,
        "PDF": pdf_filename
    }
    
    generate_pdf(data_dict, config, pdf_path)
    save_receipt_data(data_dict)
    
    config["next_bill_number"] = int(bill_no) + 1
    config["previous_meter_reading"] = request.current_reading
    save_config(config)
    
    return data_dict

def edit_bill_process(bill_no: str, request: BillRequest):
    config = load_config()
    existing_receipt = get_receipt(bill_no)
    if not existing_receipt:
        raise ValueError("Receipt not found")
        
    rent = float(config.get("default_rent", 0))
    water = float(config.get("water_charge", 0))
    prev_reading = float(existing_receipt.get("Previous", 0))
    rate = float(config.get("electricity_rate", 0))
    add_person_charge = float(config.get("additional_person_charge", 0))
    
    consumed_units = max(0.0, request.current_reading - prev_reading)
    electricity_charge = consumed_units * rate
    
    total_additional_charge = request.additional_persons * add_person_charge
    total = rent + total_additional_charge + water + electricity_charge
    
    date_str = existing_receipt.get("Date")
    
    pdf_filename = existing_receipt.get("PDF", f"{bill_no}.pdf")
    pdf_dir = "receipts"
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    data_dict = {
        "Bill": bill_no,
        "Date": date_str,
        "Month": request.month,
        "Tenant": request.tenant,
        "Previous": prev_reading,
        "Current": request.current_reading,
        "Units": consumed_units,
        "Rent": rent,
        "Additional": total_additional_charge,
        "Water": water,
        "Electricity": electricity_charge,
        "Total": total,
        "PDF": pdf_filename
    }
    
    generate_pdf(data_dict, config, pdf_path)
    update_receipt(bill_no, data_dict)
    
    # Do not update global next_bill_number or previous_meter_reading for history edits
    # to avoid messing up the sequential billing for the next new bill.
    
    return data_dict

