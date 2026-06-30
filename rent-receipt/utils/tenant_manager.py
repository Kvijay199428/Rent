import json
import os

TENANTS_FILE = "tenants.json"

def get_tenants():
    if not os.path.exists(TENANTS_FILE):
        return []
    try:
        with open(TENANTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def add_tenant(name, phone="", email=""):
    tenants = get_tenants()
    # Check if exists
    for t in tenants:
        if t["name"].lower() == name.lower():
            return {"status": "error", "message": "Tenant already exists"}
    
    new_tenant = {"id": len(tenants) + 1, "name": name, "phone": phone, "email": email}
    tenants.append(new_tenant)
    
    with open(TENANTS_FILE, "w", encoding="utf-8") as f:
        json.dump(tenants, f, indent=4)
        
    return {"status": "success", "tenant": new_tenant}

def delete_tenant(tenant_id):
    tenants = get_tenants()
    tenants = [t for t in tenants if t["id"] != tenant_id]
    with open(TENANTS_FILE, "w", encoding="utf-8") as f:
        json.dump(tenants, f, indent=4)
    return {"status": "success"}
