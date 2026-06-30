import os
from datetime import datetime
from .config import load_config, save_config
from .csv_manager import save_receipt_data
from .pdf_generator import generate_pdf

def calculate_bill(tenant_name, billing_month, current_reading, additional_persons_count):
    config = load_config()
    
    # Values from config
    rent = float(config.get("default_rent", 0))
    water = float(config.get("water_charge", 0))
    prev_reading = float(config.get("previous_meter_reading", 0))
    rate = float(config.get("electricity_rate", 0))
    add_person_charge = float(config.get("additional_person_charge", 0))
    
    # Calculations
    consumed_units = max(0.0, current_reading - prev_reading)
    electricity_charge = consumed_units * rate
    
    total_additional_charge = additional_persons_count * add_person_charge
    
    total = rent + total_additional_charge + water + electricity_charge
    
    return {
        "Rent": rent,
        "Additional Persons": additional_persons_count,
        "Additional Charge": total_additional_charge,
        "Water": water,
        "Previous Unit": prev_reading,
        "Current Unit": current_reading,
        "Consumed Units": consumed_units,
        "Rate": rate,
        "Electricity": electricity_charge,
        "Total": total
    }

def generate_receipt(tenant_name, billing_month, current_reading, additional_persons_count, date_str=None):
    config = load_config()
    
    if date_str is None:
        date_str = datetime.now().strftime("%d-%m-%Y")
        
    bill_no = str(config.get("next_bill_number", 1)).zfill(3)
    
    calc_data = calculate_bill(tenant_name, billing_month, current_reading, additional_persons_count)
    
    pdf_filename = f"Receipt_{bill_no}.pdf"
    pdf_dir = config.get("pdf_directory", "receipts")
    
    # Ensure PDF directory exists
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    data_dict = {
        "Bill No": bill_no,
        "Date": date_str,
        "Month": billing_month,
        "Tenant": tenant_name,
        "Rent": calc_data["Rent"],
        "Additional Persons": calc_data["Additional Persons"],
        "Additional Charge": calc_data["Additional Charge"],
        "Previous Unit": calc_data["Previous Unit"],
        "Current Unit": calc_data["Current Unit"],
        "Consumed Units": calc_data["Consumed Units"],
        "Rate": calc_data["Rate"],
        "Electricity": calc_data["Electricity"],
        "Water": calc_data["Water"],
        "Total": calc_data["Total"],
        "PDF": pdf_filename
    }
    
    # Generate PDF
    generate_pdf(data_dict, config, pdf_path)
    
    # Save to CSV
    save_receipt_data(data_dict)
    
    # Update config
    config["next_bill_number"] = int(bill_no) + 1
    config["previous_meter_reading"] = calc_data["Current Unit"]
    save_config(config)
    
    return pdf_path, data_dict
