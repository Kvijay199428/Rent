import json
import os
import shutil

CONFIG_DIR = "config"
BACKUP_DIR = "backups"

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

BILLING_FILE = os.path.join(CONFIG_DIR, "billing.json")
LANDLORD_FILE = os.path.join(CONFIG_DIR, "landlord.json")
UI_FILE = os.path.join(CONFIG_DIR, "ui.json")

def load_json(filepath, defaults):
    if not os.path.exists(filepath):
        save_json(filepath, defaults)
        return defaults
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure all keys in defaults exist in the loaded data
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return defaults.copy()

def save_json(filepath, data):
    # Create backup
    if os.path.exists(filepath):
        filename = os.path.basename(filepath)
        backup_path = os.path.join(BACKUP_DIR, f"{filename}.bak")
        try:
            shutil.copy2(filepath, backup_path)
        except Exception:
            pass
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

def get_billing_config():
    defaults = {
        "rent": 8000.0,
        "water": 500.0,
        "electricity_rate": 15.0,
        "additional_person_charge": 1000.0,
        "previous_meter_reading": 0.0,
        "next_bill_number": 1
    }
    return load_json(BILLING_FILE, defaults)

def save_billing_config(data):
    save_json(BILLING_FILE, data)

def get_landlord_config():
    defaults = {
        "name": "",
        "phone": "",
        "email": "",
        "address": ""
    }
    return load_json(LANDLORD_FILE, defaults)

def save_landlord_config(data):
    save_json(LANDLORD_FILE, data)

def get_ui_config():
    defaults = {
        "theme": "system"
    }
    return load_json(UI_FILE, defaults)

def save_ui_config(data):
    save_json(UI_FILE, data)
