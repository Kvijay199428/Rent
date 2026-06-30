import json
import os
import shutil

CONFIG_FILE = "config.json"
BACKUP_FILE = "config_backup.json"

DEFAULT_CONFIG = {
    "landlord_name": "",
    "property_address": "",
    "default_rent": 8000,
    "additional_person_charge": 1000,
    "water_charge": 500,
    "electricity_rate": 15,
    "previous_meter_reading": 0,
    "next_bill_number": 1,
    "currency": "₹",
    "pdf_directory": "receipts"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Merge with defaults in case of missing keys
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except json.JSONDecodeError:
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    # Backup existing config before saving
    if os.path.exists(CONFIG_FILE):
        try:
            shutil.copy2(CONFIG_FILE, BACKUP_FILE)
        except Exception as e:
            print(f"Failed to backup config: {e}")
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")
