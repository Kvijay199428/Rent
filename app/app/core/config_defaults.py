DEFAULT_CONFIGS = {
    "billing": {
        "rent": 8000.0,
        "water": 500.0,
        "electricityRate": 15.0,
        "additionalPersonCharge": 1000.0,
        "previousMeter_reading": 0.0,
        "next_bill_number": 1
    },
    "landlord": {
        "name": "",
        "phone": "",
        "email": "",
        "address": "",
        "pan": "",
        "bank_account_name": "",
        "bank_account_number": "",
        "bank_name": "",
        "bank_branch": "",
        "bank_ifsc": "",
        "mask_bank_account": True,
        "signature_text": "Authorized Signature",
        "signature_image": ""
    },
    "whatsapp": {
        "single_template": {
            "label": "Single Receipt Message Template",
            "readonly_by_default": True,
            "allowed_variables": [
                "{tenantName}",
                "{month}",
                "{billNo}",
                "{total}",
                "{currency}",
                "{link}",
                "{tenantPin}"
            ],
            "default_message": "Hello {tenantName},\n\nYour rent receipt for {month} has been generated.\n\n*Bill No:* {billNo}\n*Total Amount:* {currency}{total}\n\nYou can view and download your receipt securely here: {link}\n*Tenant Portal PIN:* {tenantPin}\n\nThank you!",
            "message": "Hello {tenantName},\n\nYour rent receipt for {month} has been generated.\n\n*Bill No:* {billNo}\n*Total Amount:* {currency}{total}\n\nYou can view and download your receipt securely here: {link}\n*Tenant Portal PIN:* {tenantPin}\n\nThank you!"
        },
        "country_code": "91"
    },
    "ui": {
        "theme": "system",
        "menu": [
            {"name": "Dashboard", "icon": "bi-speedometer2", "type": "internal",
            "route": "home_page"},
            {"name": "Billing", "icon": "bi-receipt", "type": "internal",
            "route": "billing_page"},
            {"name": "History", "icon": "bi-clock-history", "type": "internal",
            "route": "history_page"},
            {"name": "Tenants", "icon": "bi-people", "type": "internal",
            "route": "tenants_page"},
            {"name": "Archive", "icon": "bi-archive", "type": "internal",
            "route": "archive_page"},
            {"name": "Backups", "icon": "bi-database", "type": "internal",
            "route": "backups_page"},
            {"name": "Settings", "icon": "bi-gear", "type": "internal",
            "route": "settings_page"}
        ]
    },
    "schema": {
        "tenant_schema": 2,
        "receipt_schema": 1
    },
    "backup": {
        "enabled": True,
        "frequency": "daily",
        "max_daily": 30,
        "max_weekly": 12,
        "location": "backups",
        "compress": True,
        "verify": True,
        "encrypt": False,
        "create_restore_points": {
            "tenant_update": True,
            "receipt_edit": True,
            "receipt_archive": True,
            "settings_save": True,
            "schema_migration": True
        },
        "tenantRecoveryRetention": {
            "value": 30,
            "unit": "days"
        }
    },
    "system": {
        "security": {
            "tenantPinlength": 4,
            "adminTotpRequired": True,
        },
        "server": {
            "host": "0.0.0.0",
            "port": 20081,
            "debug": True
        },
        "app": {
            "title": "Rent Receipt Web Application",
            "short_name": "RRG Suite",
            "currency_symbol": "₹",
            "locale": "en-IN"
        },
        "limits": {
            "max_upload_size_mb": 2,
            "public_history_months": 12
        },
        "whatsapp": {
            "country_code": "91"
        },
        "features": {
            "whatsapp_sync": True
        }
    },
    "TENANTPROFILE": {},
    "rentReceipt": {},
    "payment": {},
    "dashboard": {},
    "archive": {},
    "pdf": {},
    "features": {},
    "theme": {},
    "validation": {}
}

