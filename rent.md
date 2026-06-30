```json
// File: RentReceiptGenerator/config.json
{
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
```

```python
// File: RentReceiptGenerator/main.py
import customtkinter as ctk
from ui.dashboard import DashboardFrame
from ui.billing import BillingFrame
from ui.history import HistoryFrame
from ui.settings import SettingsFrame

# Set appearance mode and color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class RentReceiptApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Rent Receipt Generator")
        self.geometry("900x700")
        
        # Configure grid layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Create sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Rent Receipt App", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))
        
        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_billing = ctk.CTkButton(self.sidebar_frame, text="Generate Receipt", command=self.show_billing)
        self.btn_billing.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_history = ctk.CTkButton(self.sidebar_frame, text="History", command=self.show_history)
        self.btn_history.grid(row=3, column=0, padx=20, pady=10)
        
        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings)
        self.btn_settings.grid(row=4, column=0, padx=20, pady=10)
        
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Light", "Dark"],
                                                               command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 20))

        # Main content frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Initialize views
        self.dashboard_view = DashboardFrame(self.main_frame)
        self.billing_view = BillingFrame(self.main_frame, update_callback=self.on_receipt_generated)
        self.history_view = HistoryFrame(self.main_frame)
        self.settings_view = SettingsFrame(self.main_frame)
        
        # Show default view
        self.show_dashboard()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        
    def hide_all_views(self):
        self.dashboard_view.grid_forget()
        self.billing_view.grid_forget()
        self.history_view.grid_forget()
        self.settings_view.grid_forget()

    def show_dashboard(self):
        self.hide_all_views()
        self.dashboard_view.refresh_stats()
        self.dashboard_view.grid(row=0, column=0, sticky="nsew")

    def show_billing(self):
        self.hide_all_views()
        self.billing_view.refresh_config_values()
        self.billing_view.grid(row=0, column=0, sticky="nsew")

    def show_history(self):
        self.hide_all_views()
        self.history_view.load_receipts()
        self.history_view.grid(row=0, column=0, sticky="nsew")

    def show_settings(self):
        self.hide_all_views()
        self.settings_view.load_current_settings()
        self.settings_view.grid(row=0, column=0, sticky="nsew")
        
    def on_receipt_generated(self):
        self.dashboard_view.refresh_stats()
        self.history_view.load_receipts()

if __name__ == "__main__":
    app = RentReceiptApp()
    app.mainloop()
```

```python
// File: RentReceiptGenerator/ui/billing.py
import os
import platform
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from utils.config import load_config
from utils.bill_manager import calculate_bill, generate_receipt

class BillingFrame(ctk.CTkFrame):
    def __init__(self, master, update_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.update_callback = update_callback
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Generate Receipt", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        
        # Input Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # Tenant Name
        ctk.CTkLabel(self.input_frame, text="Tenant Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.tenant_entry = ctk.CTkEntry(self.input_frame)
        self.tenant_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Billing Month
        ctk.CTkLabel(self.input_frame, text="Billing Month:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.month_entry = ctk.CTkEntry(self.input_frame)
        self.month_entry.insert(0, datetime.now().strftime("%B %Y"))
        self.month_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Current Meter Reading
        ctk.CTkLabel(self.input_frame, text="Current Meter Reading:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.reading_entry = ctk.CTkEntry(self.input_frame)
        self.reading_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.reading_entry.bind("<KeyRelease>", self.update_preview)
        
        # Additional Persons
        ctk.CTkLabel(self.input_frame, text="Additional Persons:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.add_persons_entry = ctk.CTkEntry(self.input_frame)
        self.add_persons_entry.insert(0, "0")
        self.add_persons_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        self.add_persons_entry.bind("<KeyRelease>", self.update_preview)
        
        self.calc_btn = ctk.CTkButton(self.input_frame, text="Calculate", command=self.update_preview)
        self.calc_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Preview Frame
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.preview_frame, text="Bill Preview", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.preview_text = ctk.CTkTextbox(self.preview_frame, height=250, state="disabled")
        self.preview_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Generate Button
        self.generate_btn = ctk.CTkButton(self, text="Generate Receipt & Export PDF", command=self.generate, font=ctk.CTkFont(size=14, weight="bold"), height=40)
        self.generate_btn.grid(row=2, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        
        self.refresh_config_values()
        
    def refresh_config_values(self):
        self.config = load_config()
        self.update_preview()
        
    def update_preview(self, event=None):
        try:
            current_reading = float(self.reading_entry.get() or 0)
            add_persons = int(self.add_persons_entry.get() or 0)
            
            calc_data = calculate_bill("", "", current_reading, add_persons)
            
            prev = calc_data['Previous Unit']
            consumed = calc_data['Consumed Units']
            
            preview = f"Rent: ₹{calc_data['Rent']}\n"
            preview += f"Additional Persons ({add_persons}): ₹{calc_data['Additional Charge']}\n"
            preview += f"Water: ₹{calc_data['Water']}\n\n"
            preview += f"Electricity:\n"
            preview += f"  Previous: {prev}\n"
            preview += f"  Current:  {current_reading}\n"
            preview += f"  Consumed: {consumed} units\n"
            preview += f"  Rate:     ₹{calc_data['Rate']}\n"
            preview += f"  Charge:   ₹{calc_data['Electricity']}\n"
            preview += "-"*30 + "\n"
            preview += f"TOTAL: ₹{calc_data['Total']}"
            
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", preview)
            self.preview_text.configure(state="disabled")
            
        except ValueError:
            pass
            
    def generate(self):
        tenant = self.tenant_entry.get().strip()
        month = self.month_entry.get().strip()
        reading_str = self.reading_entry.get().strip()
        add_persons_str = self.add_persons_entry.get().strip()
        
        if not tenant:
            messagebox.showerror("Error", "Tenant name cannot be empty.")
            return
            
        try:
            current_reading = float(reading_str)
            add_persons = int(add_persons_str or 0)
        except ValueError:
            messagebox.showerror("Error", "Invalid number for reading or additional persons.")
            return
            
        config = load_config()
        prev_reading = config.get("previous_meter_reading", 0)
        if current_reading < prev_reading:
            messagebox.showerror("Error", "Current meter reading cannot be lower than the previous reading.")
            return
            
        try:
            pdf_path, _ = generate_receipt(tenant, month, current_reading, add_persons)
            messagebox.showinfo("Success", f"Receipt generated successfully!\nSaved to: {pdf_path}")
            
            # Clear fields
            self.tenant_entry.delete(0, 'end')
            self.reading_entry.delete(0, 'end')
            self.add_persons_entry.delete(0, 'end')
            self.add_persons_entry.insert(0, "0")
            self.refresh_config_values()
            
            # Open PDF
            if platform.system() == 'Darwin':       # macOS
                subprocess.call(('open', pdf_path))
            elif platform.system() == 'Windows':    # Windows
                os.startfile(pdf_path)
            else:                                   # linux variants
                subprocess.call(('xdg-open', pdf_path))
                
            if self.update_callback:
                self.update_callback()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate receipt: {str(e)}")
```

```python
// File: RentReceiptGenerator/ui/dashboard.py
import customtkinter as ctk
from utils.config import load_config
from utils.csv_manager import get_all_receipts

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 20), sticky="w")
        
        # Cards
        self.bill_card = self.create_card("Next Bill No.", "-", 1, 0)
        self.tenant_card = self.create_card("Last Tenant", "-", 1, 1)
        self.meter_card = self.create_card("Last Meter Reading", "-", 1, 2)
        
        self.refresh_stats()
        
    def create_card(self, title, value, row, col):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        title_lbl = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=14))
        title_lbl.pack(pady=(15, 5))
        
        val_lbl = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=24, weight="bold"))
        val_lbl.pack(pady=(5, 15))
        
        return val_lbl
        
    def refresh_stats(self):
        config = load_config()
        receipts = get_all_receipts()
        
        next_bill = config.get("next_bill_number", 1)
        self.bill_card.configure(text=f"#{next_bill}")
        
        self.meter_card.configure(text=str(config.get("previous_meter_reading", 0)))
        
        if receipts:
            last_tenant = receipts[-1].get("Tenant", "-")
            self.tenant_card.configure(text=last_tenant)
        else:
            self.tenant_card.configure(text="-")
```

```python
// File: RentReceiptGenerator/ui/history.py
import os
import platform
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from utils.csv_manager import get_all_receipts
from utils.pdf_generator import generate_pdf
from utils.config import load_config

class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Receipt History", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Search
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search by Tenant Name or Bill No...")
        self.search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.filter_receipts)
        
        self.refresh_btn = ctk.CTkButton(self.search_frame, text="Refresh", command=self.load_receipts)
        self.refresh_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # Scrollable List
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        self.all_receipts = []
        self.load_receipts()
        
    def load_receipts(self):
        self.all_receipts = get_all_receipts()
        self.all_receipts.reverse() # Show newest first
        self.populate_list(self.all_receipts)
        
    def filter_receipts(self, event=None):
        query = self.search_entry.get().lower()
        filtered = [r for r in self.all_receipts if query in r.get("Tenant", "").lower() or query in r.get("Bill No", "").lower()]
        self.populate_list(filtered)
        
    def populate_list(self, receipts):
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        for r in receipts:
            row_frame = ctk.CTkFrame(self.list_frame)
            row_frame.pack(fill="x", padx=5, pady=5)
            
            info = f"Bill #{r.get('Bill No', '')} | {r.get('Date', '')} | {r.get('Tenant', '')} | Total: ₹{r.get('Total', '')}"
            lbl = ctk.CTkLabel(row_frame, text=info, font=ctk.CTkFont(size=14))
            lbl.pack(side="left", padx=10, pady=10)
            
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.pack(side="right", padx=10, pady=10)
            
            view_btn = ctk.CTkButton(btn_frame, text="Open PDF", command=lambda receipt=r: self.open_pdf(receipt))
            view_btn.pack(side="left", padx=5)
            
            re_export_btn = ctk.CTkButton(btn_frame, text="Re-export", command=lambda receipt=r: self.reexport_pdf(receipt))
            re_export_btn.pack(side="left", padx=5)
            
    def open_pdf(self, receipt):
        config = load_config()
        pdf_dir = config.get("pdf_directory", "receipts")
        pdf_path = os.path.join(pdf_dir, receipt.get("PDF", ""))
        
        if os.path.exists(pdf_path):
            if platform.system() == 'Darwin':
                subprocess.call(('open', pdf_path))
            elif platform.system() == 'Windows':
                os.startfile(pdf_path)
            else:
                subprocess.call(('xdg-open', pdf_path))
        else:
            messagebox.showerror("Error", "PDF file not found. Try re-exporting it.")
            
    def reexport_pdf(self, receipt):
        config = load_config()
        pdf_dir = config.get("pdf_directory", "receipts")
        
        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir)
            
        pdf_path = os.path.join(pdf_dir, receipt.get("PDF", f"Receipt_{receipt.get('Bill No')}.pdf"))
        
        try:
            generate_pdf(receipt, config, pdf_path)
            messagebox.showinfo("Success", f"Receipt re-exported to {pdf_path}")
            self.open_pdf(receipt)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to re-export PDF: {e}")
```

```python
// File: RentReceiptGenerator/ui/settings.py
import customtkinter as ctk
from tkinter import messagebox
from utils.config import load_config, save_config

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        
        self.fields = {}
        
        settings_fields = [
            ("Landlord Name", "landlord_name", "string"),
            ("Property Address", "property_address", "string"),
            ("Monthly Rent", "default_rent", "float"),
            ("Additional Person Charge", "additional_person_charge", "float"),
            ("Water Charge", "water_charge", "float"),
            ("Electricity Rate", "electricity_rate", "float"),
            ("Current Meter Reading (Previous for next bill)", "previous_meter_reading", "float"),
            ("Next Bill Number", "next_bill_number", "int"),
            ("PDF Save Folder", "pdf_directory", "string")
        ]
        
        row = 1
        for label_text, key, type_ in settings_fields:
            label = ctk.CTkLabel(self, text=label_text)
            label.grid(row=row, column=0, padx=20, pady=10, sticky="w")
            
            entry = ctk.CTkEntry(self)
            entry.grid(row=row, column=1, padx=20, pady=10, sticky="ew")
            
            self.fields[key] = (entry, type_)
            row += 1
            
        self.save_button = ctk.CTkButton(self, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=row, column=0, columnspan=2, padx=20, pady=20)
        
        self.load_current_settings()
        
    def load_current_settings(self):
        config = load_config()
        for key, (entry, type_) in self.fields.items():
            entry.delete(0, ctk.END)
            val = config.get(key, "")
            entry.insert(0, str(val))
            
    def save_settings(self):
        config = load_config()
        try:
            for key, (entry, type_) in self.fields.items():
                val = entry.get()
                if type_ == "float":
                    config[key] = float(val)
                elif type_ == "int":
                    config[key] = int(val)
                else:
                    config[key] = val
                    
            save_config(config)
            messagebox.showinfo("Success", "Settings saved successfully!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for numeric fields.")
```

```python
// File: RentReceiptGenerator/utils/bill_manager.py
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
```

```python
// File: RentReceiptGenerator/utils/config.py
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
```

```python
// File: RentReceiptGenerator/utils/csv_manager.py
import csv
import os
import shutil

CSV_FILE = "tenant.csv"
BACKUP_FILE = "tenant_backup.csv"

HEADERS = [
    "Bill No", "Date", "Month", "Tenant", "Rent", "Additional Persons", 
    "Additional Charge", "Previous Unit", "Current Unit", "Consumed Units", 
    "Rate", "Electricity", "Water", "Total", "PDF"
]

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

def save_receipt_data(data_dict):
    init_csv()
    
    # Backup before writing
    if os.path.exists(CSV_FILE):
        try:
            shutil.copy2(CSV_FILE, BACKUP_FILE)
        except Exception:
            pass

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writerow(data_dict)

def get_all_receipts():
    init_csv()
    receipts = []
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            receipts.append(row)
    return receipts
```

```python
// File: RentReceiptGenerator/utils/pdf_generator.py
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from num2words import num2words

def generate_pdf(data, config, output_path):
    # data is a dict containing the receipt info
    # config contains landlord name, address, etc.
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2.0, height - 50, "RENT RECEIPT")
    
    # Header Info
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Receipt No : {data['Bill No']}")
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
    curr = config.get('currency', '₹')
    
    c.drawString(50, height - y_offset, "Rent")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Rent']}")
    y_offset += 20
    
    c.drawString(50, height - y_offset, f"Additional Persons ({data['Additional Persons']})")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Additional Charge']}")
    y_offset += 20
    
    c.drawString(50, height - y_offset, "Water")
    c.drawRightString(width - 50, height - y_offset, f"{curr}{data['Water']}")
    y_offset += 30
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - y_offset, "Electricity")
    c.setFont("Helvetica", 12)
    y_offset += 20
    
    c.drawString(50, height - y_offset, f"Previous Reading {data['Previous Unit']}")
    y_offset += 15
    c.drawString(50, height - y_offset, f"Current Reading {data['Current Unit']}")
    y_offset += 15
    c.drawString(50, height - y_offset, f"Units Consumed {data['Consumed Units']}")
    y_offset += 15
    c.drawString(50, height - y_offset, f"Rate {curr}{data['Rate']}")
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
    
    c.showPage()
    c.save()
    return output_path
```

```python
// File: rent-receipt/app.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import os

from utils.config_manager import load_config, save_config
from utils.csv_manager import get_all_receipts, get_receipt
from utils.billing import process_bill, edit_bill_process, BillRequest
from utils.tenant_manager import get_tenants, add_tenant, delete_tenant

app = FastAPI(title="Rent Receipt Generator")

# Create required directories if not exist
os.makedirs("receipts", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = load_config()
    receipts = get_all_receipts()
    tenants = get_tenants()
    last_tenant = "-"
    if receipts:
        last_tenant = receipts[-1].get("Tenant", "-")
    return templates.TemplateResponse(
        request=request, name="index.html", context={
        "next_bill_number": str(config.get("next_bill_number", 1)).zfill(3),
        "last_meter_reading": config.get("previous_meter_reading", 0),
        "last_tenant": last_tenant,
        "total_tenants": len(tenants)
    })

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    config = load_config()
    tenants = get_tenants()
    return templates.TemplateResponse(
        request=request, name="billing.html", context={
        "config": config,
        "tenants": tenants
    })

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts()
    receipts.reverse()
    return templates.TemplateResponse(
        request=request, name="history.html", context={
        "receipts": receipts
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    config = load_config()
    return templates.TemplateResponse(
        request=request, name="settings.html", context={
        "config": config
    })

@app.get("/tenants", response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = get_tenants()
    return templates.TemplateResponse(
        request=request, name="tenants.html", context={
        "tenants": tenants
    })

@app.get("/edit_bill/{bill_no}", response_class=HTMLResponse)
async def edit_bill_page(request: Request, bill_no: str):
    config = load_config()
    tenants = get_tenants()
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    return templates.TemplateResponse(
        request=request, name="edit_bill.html", context={
        "config": config,
        "tenants": tenants,
        "receipt": receipt
    })

# --- REST API ---

@app.get("/api/config")
async def get_config():
    return load_config()

class ConfigUpdate(BaseModel):
    landlord_name: str
    landlord_phone: str
    landlord_email: str
    property_address: str
    default_rent: float
    additional_person_charge: float
    water_charge: float
    electricity_rate: float
    previous_meter_reading: float
    next_bill_number: int

@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    config = load_config()
    config.update(data.dict())
    save_config(config)
    return {"status": "success", "config": config}

@app.get("/api/history")
async def get_history():
    receipts = get_all_receipts()
    receipts.reverse()
    return {"receipts": receipts}

@app.post("/api/bill")
async def create_bill(request: BillRequest):
    config = load_config()
    prev = float(config.get("previous_meter_reading", 0))
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current reading cannot be less than previous reading.")
    
    data_dict = process_bill(request)
    return {"status": "success", "data": data_dict}

@app.post("/api/edit_bill/{bill_no}")
async def edit_bill(bill_no: str, request: BillRequest):
    try:
        data_dict = edit_bill_process(bill_no, request)
        return {"status": "success", "data": data_dict}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class TenantCreate(BaseModel):
    name: str
    phone: str
    email: str

@app.post("/api/tenants")
async def api_add_tenant(data: TenantCreate):
    return add_tenant(data.name, data.phone, data.email)

@app.delete("/api/tenants/{tenant_id}")
async def api_delete_tenant(tenant_id: int):
    return delete_tenant(tenant_id)


@app.get("/api/pdf/{bill_no}")
async def download_pdf(bill_no: str):
    pdf_path = os.path.join("receipts", f"{bill_no}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type='application/pdf', filename=f"Receipt_{bill_no}.pdf")
    else:
        raise HTTPException(status_code=404, detail="PDF not found")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=20081, reload=True)
```

```json
// File: rent-receipt/config.json
{
    "landlord_name": "Vijay Kumar Sharma",
    "property_address": "1 E, Shiv Durga Vihar Lakarpur, Surajkund Faridabad, Faridabad, Haryana - 121009",
    "default_rent": 8000.0,
    "additional_person_charge": 1000.0,
    "water_charge": 500.0,
    "electricity_rate": 15.0,
    "previous_meter_reading": 100.0,
    "next_bill_number": 2
}
```

```json
// File: rent-receipt/config_backup.json
{
    "landlord_name": "Vijay Kumar Sharma",
    "property_address": "1 E, Shiv Durga Vihar Lakarpur, Surajkund Faridabad, Faridabad, Haryana - 121009",
    "default_rent": 8000.0,
    "additional_person_charge": 1000.0,
    "water_charge": 500.0,
    "electricity_rate": 15.0,
    "previous_meter_reading": 0.0,
    "next_bill_number": 1
}
```

```
// File: rent-receipt/install.log
Requirement already satisfied: fastapi in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 1)) (0.136.1)
Requirement already satisfied: uvicorn in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 2)) (0.46.0)
Requirement already satisfied: jinja2 in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 3)) (3.1.6)
Requirement already satisfied: python-multipart in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 4)) (0.0.27)
Requirement already satisfied: reportlab in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 5)) (5.0.0)
Requirement already satisfied: num2words in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 6)) (0.5.14)
Requirement already satisfied: pydantic in /root/venv/lib/python3.13/site-packages (from -r requirements.txt (line 7)) (2.13.4)
Requirement already satisfied: starlette>=0.46.0 in /root/venv/lib/python3.13/site-packages (from fastapi->-r requirements.txt (line 1)) (1.0.0)
Requirement already satisfied: typing-extensions>=4.8.0 in /root/venv/lib/python3.13/site-packages (from fastapi->-r requirements.txt (line 1)) (4.15.0)
Requirement already satisfied: typing-inspection>=0.4.2 in /root/venv/lib/python3.13/site-packages (from fastapi->-r requirements.txt (line 1)) (0.4.2)
Requirement already satisfied: annotated-doc>=0.0.2 in /root/venv/lib/python3.13/site-packages (from fastapi->-r requirements.txt (line 1)) (0.0.4)
Requirement already satisfied: click>=7.0 in /root/venv/lib/python3.13/site-packages (from uvicorn->-r requirements.txt (line 2)) (8.3.3)
Requirement already satisfied: h11>=0.8 in /root/venv/lib/python3.13/site-packages (from uvicorn->-r requirements.txt (line 2)) (0.16.0)
Requirement already satisfied: MarkupSafe>=2.0 in /root/venv/lib/python3.13/site-packages (from jinja2->-r requirements.txt (line 3)) (3.0.3)
Requirement already satisfied: pillow>=9.0.0 in /root/venv/lib/python3.13/site-packages (from reportlab->-r requirements.txt (line 5)) (12.2.0)
Requirement already satisfied: charset-normalizer in /root/venv/lib/python3.13/site-packages (from reportlab->-r requirements.txt (line 5)) (3.4.7)
Requirement already satisfied: docopt>=0.6.2 in /root/venv/lib/python3.13/site-packages (from num2words->-r requirements.txt (line 6)) (0.6.2)
Requirement already satisfied: annotated-types>=0.6.0 in /root/venv/lib/python3.13/site-packages (from pydantic->-r requirements.txt (line 7)) (0.7.0)
Requirement already satisfied: pydantic-core==2.46.4 in /root/venv/lib/python3.13/site-packages (from pydantic->-r requirements.txt (line 7)) (2.46.4)
Requirement already satisfied: anyio<5,>=3.6.2 in /root/venv/lib/python3.13/site-packages (from starlette>=0.46.0->fastapi->-r requirements.txt (line 1)) (4.13.0)
Requirement already satisfied: idna>=2.8 in /root/venv/lib/python3.13/site-packages (from anyio<5,>=3.6.2->starlette>=0.46.0->fastapi->-r requirements.txt (line 1)) (3.13)
```

```text
// File: rent-receipt/requirements.txt
fastapi
uvicorn
jinja2
python-multipart
reportlab
num2words
pydantic
```

```
// File: rent-receipt/server.log
INFO:     Will watch for changes in these directories: ['/root/rent/rent-receipt']
INFO:     Uvicorn running on http://0.0.0.0:20081 (Press CTRL+C to quit)
INFO:     Started reloader process [12220] using StatReload
INFO:     Started server process [12233]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:60320 - "GET / HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/root/venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 415, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 56, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/fastapi/applications.py", line 1159, in __call__
    await super().__call__(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/root/venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/routing.py", line 660, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/routing.py", line 680, in app
    await route.handle(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/routing.py", line 276, in handle
    await self.app(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 134, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 120, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 674, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 328, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/rent/rent-receipt/app.py", line 31, in dashboard
    return templates.TemplateResponse("index.html", {
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
        "request": request,
        ^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        "last_tenant": last_tenant
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
    })
    ^^
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 148, in TemplateResponse
    template = self.get_template(name)
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 115, in get_template
    return self.env.get_template(name)
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 1016, in get_template
    return self._load_template(name, globals)
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 964, in _load_template
    template = self.cache.get(cache_key)
  File "/root/venv/lib/python3.13/site-packages/jinja2/utils.py", line 477, in get
    return self[key]
           ~~~~^^^^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/utils.py", line 515, in __getitem__
    rv = self._mapping[key]
         ~~~~~~~~~~~~~^^^^^
TypeError: unhashable type: 'dict'
WARNING:  StatReload detected changes in 'app.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [12233]
INFO:     Started server process [13128]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:35012 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:35016 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:35016 - "GET /static/css/style.css HTTP/1.1" 200 OK
INFO:     127.0.0.1:35020 - "GET /static/js/main.js HTTP/1.1" 200 OK
INFO:     127.0.0.1:35020 - "GET /favicon.ico HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:56116 - "GET /api/config HTTP/1.1" 200 OK
INFO:     127.0.0.1:33688 - "GET /history HTTP/1.1" 200 OK
INFO:     127.0.0.1:33688 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:33702 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:33702 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:36986 - "POST /api/config HTTP/1.1" 200 OK
INFO:     127.0.0.1:36992 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:36992 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:36998 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
WARNING:  Invalid HTTP request received.
INFO:     127.0.0.1:35156 - "WebSocket /ws" 403
INFO:     connection rejected (403 Forbidden)
INFO:     connection closed
INFO:     127.0.0.1:54606 - "POST /api/bill HTTP/1.1" 200 OK
INFO:     127.0.0.1:54606 - "GET /api/pdf/001 HTTP/1.1" 200 OK
INFO:     127.0.0.1:54606 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:54606 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:54618 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:51496 - "GET /history HTTP/1.1" 200 OK
INFO:     127.0.0.1:51496 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:51512 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:41828 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:41828 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:41844 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:48182 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:48182 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:48186 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:48202 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:48206 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:60674 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:60674 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:60676 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:50702 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:50702 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:50718 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:39582 - "GET / HTTP/1.1" 200 OK
WARNING:  StatReload detected changes in 'utils/config_manager.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [13128]
INFO:     Started server process [23260]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
WARNING:  StatReload detected changes in 'utils/csv_manager.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [23260]
INFO:     Started server process [23275]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
WARNING:  StatReload detected changes in 'utils/billing.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [23275]
INFO:     Started server process [23369]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
WARNING:  StatReload detected changes in 'utils/pdf.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [23369]
INFO:     Started server process [23384]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
WARNING:  StatReload detected changes in 'app.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [23384]
INFO:     Started server process [23481]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:60426 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:60426 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:60434 - "GET /static/js/main.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:60434 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:60436 - "GET /tenants HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/root/venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 415, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 56, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/fastapi/applications.py", line 1159, in __call__
    await super().__call__(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/root/venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/routing.py", line 660, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/routing.py", line 680, in app
    await route.handle(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/routing.py", line 276, in handle
    await self.app(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 134, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 120, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 674, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/fastapi/routing.py", line 328, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/rent/rent-receipt/app.py", line 71, in tenants_page
    return templates.TemplateResponse(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^
        request=request, name="tenants.html", context={
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        "tenants": tenants
        ^^^^^^^^^^^^^^^^^^
    })
    ^^
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 148, in TemplateResponse
    template = self.get_template(name)
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 115, in get_template
    return self.env.get_template(name)
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 1016, in get_template
    return self._load_template(name, globals)
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 975, in _load_template
    template = self.loader.load(self, name, self.make_globals(globals))
  File "/root/venv/lib/python3.13/site-packages/jinja2/loaders.py", line 126, in load
    source, filename, uptodate = self.get_source(environment, name)
                                 ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/loaders.py", line 209, in get_source
    raise TemplateNotFound(
    ...<2 lines>...
    )
jinja2.exceptions.TemplateNotFound: 'tenants.html' not found in search path: 'templates'
INFO:     127.0.0.1:60450 - "GET /tenants HTTP/1.1" 200 OK
INFO:     127.0.0.1:60450 - "GET /tenants HTTP/1.1" 200 OK
INFO:     127.0.0.1:60450 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:60450 - "GET /history HTTP/1.1" 200 OK
INFO:     127.0.0.1:38162 - "GET /history HTTP/1.1" 200 OK
INFO:     127.0.0.1:38162 - "GET /history HTTP/1.1" 200 OK
INFO:     127.0.0.1:34760 - "GET /edit_bill/001 HTTP/1.1" 200 OK
INFO:     127.0.0.1:37966 - "GET /api/config HTTP/1.1" 200 OK
INFO:     127.0.0.1:34930 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:34930 - "GET /history HTTP/1.1" 200 OK
INFO:     127.0.0.1:34930 - "GET /edit_bill/001 HTTP/1.1" 200 OK
INFO:     127.0.0.1:39582 - "GET /billing HTTP/1.1" 200 OK
```

```css
// File: rent-receipt/static/css/style.css
body {
    background-color: #f8f9fa;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", "Liberation Sans", Arial, sans-serif;
}

.card {
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    border: none;
    border-radius: 0.5rem;
}

.navbar {
    box-shadow: 0 2px 4px rgba(0,0,0,.1);
}
```

```javascript
// File: rent-receipt/static/js/main.js
// Main JavaScript file for common utilities
console.log("Rent Receipt Generator Initialized");
```

```html
// File: rent-receipt/templates/base.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Rent Receipt Generator{% endblock %}</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Custom CSS -->
    <link href="/static/css/style.css" rel="stylesheet">
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
    <div class="container">
        <a class="navbar-brand" href="/">Rent Receipt Generator</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item">
                    <a class="nav-link" href="/">Dashboard</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/billing">New Bill</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/history">History</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/tenants">Tenants</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/settings">Settings</a>
                </li>
            </ul>
        </div>
    </div>
</nav>

<div class="container">
    {% block content %}{% endblock %}
</div>

<!-- Bootstrap 5 JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<!-- Custom JS -->
<script src="/static/js/main.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>
```

```html
// File: rent-receipt/templates/billing.html
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">Billing Details</h4>
            </div>
            <div class="card-body">
                <form id="billingForm">
                    <div class="mb-3">
                        <label class="form-label">Tenant Name</label>
                        <select class="form-select" id="tenant" required>
                            <option value="">Select Tenant...</option>
                            {% for t in tenants %}
                            <option value="{{ t.name }}">{{ t.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Billing Month</label>
                        <select class="form-select" id="month" required>
                            <!-- Populated by JS -->
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Additional Persons</label>
                        <input type="number" class="form-control" id="additional_persons" placeholder="If no additional person, leave this field empty" min="0" oninput="calculatePreview()">
                        <div class="form-text">No additional person are there leave this field. Enter numbers only.</div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Current Meter Reading</label>
                        <input type="number" class="form-control" id="current_reading" step="0.1" required oninput="calculatePreview()">
                        <div class="form-text">Enter numbers only.</div>
                    </div>
                    <button type="submit" class="btn btn-success w-100" id="generateBtn">Generate Receipt</button>
                </form>
                <div class="mt-3 text-center d-none" id="downloadSection">
                    <a href="#" class="btn btn-outline-primary" id="downloadBtn" target="_blank">Download PDF</a>
                </div>
                <div class="alert alert-danger mt-3 d-none" id="errorAlert"></div>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card text-bg-light">
            <div class="card-header">
                <h4 class="mb-0">Auto Calculation Preview</h4>
            </div>
            <div class="card-body">
                <table class="table table-borderless">
                    <tbody>
                        <tr>
                            <td>Rent:</td>
                            <td class="text-end">₹<span id="preview_rent">{{ config.default_rent }}</span></td>
                        </tr>
                        <tr>
                            <td>Additional Person Charge:</td>
                            <td class="text-end">₹<span id="preview_add_charge">0.00</span></td>
                        </tr>
                        <tr>
                            <td>Water Charge:</td>
                            <td class="text-end">₹<span id="preview_water">{{ config.water_charge }}</span></td>
                        </tr>
                        <tr>
                            <td colspan="2"><hr></td>
                        </tr>
                        <tr>
                            <td>Previous Reading:</td>
                            <td class="text-end"><span id="preview_prev_reading">{{ config.previous_meter_reading }}</span></td>
                        </tr>
                        <tr>
                            <td>Consumed Units:</td>
                            <td class="text-end"><span id="preview_consumed_units">0.00</span></td>
                        </tr>
                        <tr>
                            <td>Electricity Charge (₹{{ config.electricity_rate }}/unit):</td>
                            <td class="text-end">₹<span id="preview_electricity">0.00</span></td>
                        </tr>
                        <tr>
                            <td colspan="2"><hr></td>
                        </tr>
                        <tr class="fw-bold fs-5">
                            <td>Grand Total:</td>
                            <td class="text-end text-primary">₹<span id="preview_total">{{ config.default_rent + config.water_charge }}</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const rent = {{ config.default_rent }};
    const water = {{ config.water_charge }};
    const prevReading = {{ config.previous_meter_reading }};
    const rate = {{ config.electricity_rate }};
    const addPersonCharge = {{ config.additional_person_charge }};

    document.addEventListener("DOMContentLoaded", function() {
        const monthSelect = document.getElementById("month");
        const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        const d = new Date();
        const currentYear = d.getFullYear();
        const currentMonthIndex = d.getMonth();
        
        // Add options for current year
        months.forEach((m, idx) => {
            let option = document.createElement("option");
            option.value = m + " " + currentYear;
            option.text = m + " " + currentYear;
            if (idx === currentMonthIndex) option.selected = true;
            monthSelect.appendChild(option);
        });
        
        // Optional: next year's first few months
        months.slice(0, 3).forEach((m) => {
            let option = document.createElement("option");
            option.value = m + " " + (currentYear + 1);
            option.text = m + " " + (currentYear + 1);
            monthSelect.appendChild(option);
        });
    });

    function calculatePreview() {
        const currentReadingStr = document.getElementById("current_reading").value;
        const addPersonsStr = document.getElementById("additional_persons").value;
        
        const currentReading = parseFloat(currentReadingStr) || 0;
        const addPersons = parseInt(addPersonsStr) || 0;
        
        let consumed = Math.max(0, currentReading - prevReading);
        let electricity = consumed * rate;
        let addCharge = addPersons * addPersonCharge;
        
        let total = rent + addCharge + water + electricity;
        
        document.getElementById("preview_add_charge").innerText = addCharge.toFixed(2);
        document.getElementById("preview_consumed_units").innerText = consumed.toFixed(2);
        document.getElementById("preview_electricity").innerText = electricity.toFixed(2);
        document.getElementById("preview_total").innerText = total.toFixed(2);
    }

    document.getElementById("billingForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        document.getElementById("errorAlert").classList.add("d-none");
        document.getElementById("downloadSection").classList.add("d-none");
        
        const tenant = document.getElementById("tenant").value;
        const month = document.getElementById("month").value;
        const currentReading = parseFloat(document.getElementById("current_reading").value);
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        
        if (currentReading < prevReading) {
            document.getElementById("errorAlert").innerText = "Current reading cannot be less than previous reading.";
            document.getElementById("errorAlert").classList.remove("d-none");
            return;
        }
        
        const btn = document.getElementById("generateBtn");
        btn.disabled = true;
        btn.innerText = "Generating...";
        
        try {
            const res = await fetch("/api/bill", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tenant: tenant,
                    month: month,
                    current_reading: currentReading,
                    additional_persons: addPersons
                })
            });
            const data = await res.json();
            
            if (res.ok) {
                const billNo = data.data.Bill;
                const pdfLink = `/api/pdf/${billNo}`;
                const downloadBtn = document.getElementById("downloadBtn");
                downloadBtn.href = pdfLink;
                document.getElementById("downloadSection").classList.remove("d-none");
                
                // Clear inputs
                document.getElementById("tenant").value = "";
                document.getElementById("current_reading").value = "";
                document.getElementById("additional_persons").value = "";
                
                // Automatically open PDF
                window.open(pdfLink, "_blank");
                
                // Optional: reload page to fetch new config values (like previous meter reading)
                setTimeout(() => window.location.reload(), 1500);
            } else {
                document.getElementById("errorAlert").innerText = data.detail || "Error generating bill.";
                document.getElementById("errorAlert").classList.remove("d-none");
            }
        } catch(err) {
            document.getElementById("errorAlert").innerText = "Network error occurred.";
            document.getElementById("errorAlert").classList.remove("d-none");
        } finally {
            btn.disabled = false;
            btn.innerText = "Generate Receipt";
        }
    });
</script>
{% endblock %}
```

```html
// File: rent-receipt/templates/edit_bill.html
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header bg-warning text-dark">
                <h4 class="mb-0">Edit Bill #{{ receipt.Bill }}</h4>
            </div>
            <div class="card-body">
                <form id="editForm">
                    <div class="mb-3">
                        <label class="form-label">Tenant Name</label>
                        <select class="form-select" id="tenant" required>
                            <option value="">Select Tenant...</option>
                            {% for t in tenants %}
                            <option value="{{ t.name }}" {% if t.name == receipt.Tenant %}selected{% endif %}>{{ t.name }}</option>
                            {% endfor %}
                            <option value="{{ receipt.Tenant }}" selected>{{ receipt.Tenant }}</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Billing Month</label>
                        <select class="form-select" id="month" required>
                            <option value="{{ receipt.Month }}" selected>{{ receipt.Month }}</option>
                            <!-- other options generated by js -->
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Additional Persons</label>
                        {% set initial_add_persons = (receipt.Additional|float / config.additional_person_charge|float)|int if config.additional_person_charge|float > 0 else 0 %}
                        <input type="number" class="form-control" id="additional_persons" value="{{ initial_add_persons }}" min="0" oninput="calculatePreview()">
                        <div class="form-text">No additional person are there leave this field. Enter numbers only.</div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Current Meter Reading</label>
                        <input type="number" class="form-control" id="current_reading" value="{{ receipt.Current }}" step="0.1" required oninput="calculatePreview()">
                        <div class="form-text">Enter numbers only.</div>
                    </div>
                    <button type="submit" class="btn btn-warning w-100" id="updateBtn">Update Bill</button>
                </form>
                <div class="mt-3 text-center d-none" id="downloadSection">
                    <a href="#" class="btn btn-outline-primary" id="downloadBtn" target="_blank">Download Updated PDF</a>
                </div>
                <div class="alert alert-danger mt-3 d-none" id="errorAlert"></div>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card text-bg-light">
            <div class="card-header">
                <h4 class="mb-0">Auto Calculation Preview</h4>
            </div>
            <div class="card-body">
                <table class="table table-borderless">
                    <tbody>
                        <tr>
                            <td>Rent:</td>
                            <td class="text-end">₹<span id="preview_rent">{{ config.default_rent }}</span></td>
                        </tr>
                        <tr>
                            <td>Additional Person Charge:</td>
                            <td class="text-end">₹<span id="preview_add_charge">0.00</span></td>
                        </tr>
                        <tr>
                            <td>Water Charge:</td>
                            <td class="text-end">₹<span id="preview_water">{{ config.water_charge }}</span></td>
                        </tr>
                        <tr>
                            <td colspan="2"><hr></td>
                        </tr>
                        <tr>
                            <td>Previous Reading:</td>
                            <td class="text-end"><span id="preview_prev_reading">{{ receipt.Previous }}</span></td>
                        </tr>
                        <tr>
                            <td>Consumed Units:</td>
                            <td class="text-end"><span id="preview_consumed_units">0.00</span></td>
                        </tr>
                        <tr>
                            <td>Electricity Charge (₹{{ config.electricity_rate }}/unit):</td>
                            <td class="text-end">₹<span id="preview_electricity">0.00</span></td>
                        </tr>
                        <tr>
                            <td colspan="2"><hr></td>
                        </tr>
                        <tr class="fw-bold fs-5">
                            <td>Grand Total:</td>
                            <td class="text-end text-primary">₹<span id="preview_total">0.00</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const rent = {{ config.default_rent }};
    const water = {{ config.water_charge }};
    const prevReading = {{ receipt.Previous }};
    const rate = {{ config.electricity_rate }};
    const addPersonCharge = {{ config.additional_person_charge }};

    document.addEventListener("DOMContentLoaded", function() {
        const monthSelect = document.getElementById("month");
        const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        const d = new Date();
        const currentYear = d.getFullYear();
        
        months.forEach((m) => {
            let val = m + " " + currentYear;
            // Prevent duplicate option since we already added the selected one from jinja
            if(monthSelect.options[0].value !== val) {
                let option = document.createElement("option");
                option.value = val;
                option.text = val;
                monthSelect.appendChild(option);
            }
        });
        
        calculatePreview();
    });

    function calculatePreview() {
        const currentReadingStr = document.getElementById("current_reading").value;
        const addPersonsStr = document.getElementById("additional_persons").value;
        
        const currentReading = parseFloat(currentReadingStr) || 0;
        const addPersons = parseInt(addPersonsStr) || 0;
        
        let consumed = Math.max(0, currentReading - prevReading);
        let electricity = consumed * rate;
        let addCharge = addPersons * addPersonCharge;
        
        let total = rent + addCharge + water + electricity;
        
        document.getElementById("preview_add_charge").innerText = addCharge.toFixed(2);
        document.getElementById("preview_consumed_units").innerText = consumed.toFixed(2);
        document.getElementById("preview_electricity").innerText = electricity.toFixed(2);
        document.getElementById("preview_total").innerText = total.toFixed(2);
    }

    document.getElementById("editForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        document.getElementById("errorAlert").classList.add("d-none");
        document.getElementById("downloadSection").classList.add("d-none");
        
        const tenant = document.getElementById("tenant").value;
        const month = document.getElementById("month").value;
        const currentReading = parseFloat(document.getElementById("current_reading").value);
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        
        if (currentReading < prevReading) {
            document.getElementById("errorAlert").innerText = "Current reading cannot be less than previous reading.";
            document.getElementById("errorAlert").classList.remove("d-none");
            return;
        }
        
        const btn = document.getElementById("updateBtn");
        btn.disabled = true;
        btn.innerText = "Updating...";
        
        try {
            const res = await fetch("/api/edit_bill/{{ receipt.Bill }}", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tenant: tenant,
                    month: month,
                    current_reading: currentReading,
                    additional_persons: addPersons
                })
            });
            const data = await res.json();
            
            if (res.ok) {
                const pdfLink = `/api/pdf/{{ receipt.Bill }}`;
                const downloadBtn = document.getElementById("downloadBtn");
                downloadBtn.href = pdfLink;
                document.getElementById("downloadSection").classList.remove("d-none");
                
                window.open(pdfLink, "_blank");
            } else {
                document.getElementById("errorAlert").innerText = data.detail || "Error updating bill.";
                document.getElementById("errorAlert").classList.remove("d-none");
            }
        } catch(err) {
            document.getElementById("errorAlert").innerText = "Network error occurred.";
            document.getElementById("errorAlert").classList.remove("d-none");
        } finally {
            btn.disabled = false;
            btn.innerText = "Update Bill";
        }
    });
</script>
{% endblock %}
```

```html
// File: rent-receipt/templates/history.html
{% extends "base.html" %}

{% block content %}
<div class="row mb-3">
    <div class="col-12">
        <h2>Receipt History</h2>
    </div>
</div>

<div class="row mb-3">
    <div class="col-md-6">
        <input type="text" class="form-control" id="searchInput" placeholder="Search by Tenant Name or Month..." onkeyup="filterTable()">
    </div>
</div>

<div class="row">
    <div class="col-12">
        <div class="table-responsive">
            <table class="table table-striped table-hover align-middle" id="historyTable">
                <thead class="table-dark">
                    <tr>
                        <th>Bill #</th>
                        <th>Date</th>
                        <th>Month</th>
                        <th>Tenant</th>
                        <th>Total (₹)</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in receipts %}
                    <tr>
                        <td>{{ r.Bill }}</td>
                        <td>{{ r.Date }}</td>
                        <td>{{ r.Month }}</td>
                        <td class="tenant-col">{{ r.Tenant }}</td>
                        <td>{{ r.Total }}</td>
                        <td>
                            <a href="/edit_bill/{{ r.Bill }}" class="btn btn-sm btn-outline-secondary me-1">Edit</a>
                            <a href="/api/pdf/{{ r.Bill }}" target="_blank" class="btn btn-sm btn-outline-primary">Download PDF</a>
                        </td>
                    </tr>
                    {% endfor %}
                    {% if not receipts %}
                    <tr>
                        <td colspan="6" class="text-center">No receipts generated yet.</td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    function filterTable() {
        const input = document.getElementById("searchInput").value.toLowerCase();
        const table = document.getElementById("historyTable");
        const trs = table.getElementsByTagName("tr");
        
        for (let i = 1; i < trs.length; i++) {
            let row = trs[i];
            // Tenant is col index 3, Month is 2
            let tdTenant = row.getElementsByTagName("td")[3];
            let tdMonth = row.getElementsByTagName("td")[2];
            
            if (tdTenant && tdMonth) {
                let txtTenant = tdTenant.textContent || tdTenant.innerText;
                let txtMonth = tdMonth.textContent || tdMonth.innerText;
                
                if (txtTenant.toLowerCase().indexOf(input) > -1 || txtMonth.toLowerCase().indexOf(input) > -1) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            }
        }
    }
</script>
{% endblock %}
```

```html
// File: rent-receipt/templates/index.html
{% extends "base.html" %}

{% block content %}
<div class="row text-center mb-5">
    <div class="col-12">
        <h2 class="display-5">Dashboard</h2>
        <p class="text-muted">Welcome to the Rent Receipt Generator</p>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-4 mb-3">
        <div class="card text-bg-light h-100 text-center">
            <div class="card-body">
                <h5 class="card-title">Next Bill Number</h5>
                <h2 class="display-4 text-primary">{{ next_bill_number }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card text-bg-light h-100 text-center">
            <div class="card-body">
                <h5 class="card-title">Last Meter Reading</h5>
                <h2 class="display-4 text-primary">{{ last_meter_reading }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card text-bg-light h-100 text-center">
            <div class="card-body">
                <h5 class="card-title">Total Tenants</h5>
                <h2 class="display-4 text-primary">{{ total_tenants }}</h2>
            </div>
        </div>
    </div>
</div>

<div class="row text-center">
    <div class="col-md-4 mb-3">
        <a href="/billing" class="btn btn-primary btn-lg w-100">New Bill</a>
    </div>
    <div class="col-md-4 mb-3">
        <a href="/history" class="btn btn-secondary btn-lg w-100">History</a>
    </div>
    <div class="col-md-4 mb-3">
        <a href="/settings" class="btn btn-outline-secondary btn-lg w-100">Settings</a>
    </div>
</div>
{% endblock %}
```

```html
// File: rent-receipt/templates/settings.html
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-8 mx-auto">
        <div class="card">
            <div class="card-header bg-secondary text-white">
                <h4 class="mb-0">Settings Configuration</h4>
            </div>
            <div class="card-body">
                <form id="settingsForm">
                    <div class="mb-3">
                        <label class="form-label">Landlord Name</label>
                        <input type="text" class="form-control" id="landlord_name" value="{{ config.landlord_name }}">
                    </div>
                    <div class="row mb-3">
                        <div class="col">
                            <label class="form-label">Landlord Phone</label>
                            <input type="text" class="form-control" id="landlord_phone" value="{{ config.landlord_phone }}">
                        </div>
                        <div class="col">
                            <label class="form-label">Landlord Email</label>
                            <input type="email" class="form-control" id="landlord_email" value="{{ config.landlord_email }}">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Property Address</label>
                        <textarea class="form-control" id="property_address" rows="2">{{ config.property_address }}</textarea>
                    </div>
                    <div class="row mb-3">
                        <div class="col">
                            <label class="form-label">Monthly Rent (₹)</label>
                            <input type="number" class="form-control" id="default_rent" value="{{ config.default_rent }}" step="0.01">
                        </div>
                        <div class="col">
                            <label class="form-label">Additional Person Charge (₹)</label>
                            <input type="number" class="form-control" id="additional_person_charge" value="{{ config.additional_person_charge }}" step="0.01">
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col">
                            <label class="form-label">Water Charge (₹)</label>
                            <input type="number" class="form-control" id="water_charge" value="{{ config.water_charge }}" step="0.01">
                        </div>
                        <div class="col">
                            <label class="form-label">Electricity Rate (₹/unit)</label>
                            <input type="number" class="form-control" id="electricity_rate" value="{{ config.electricity_rate }}" step="0.01">
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col">
                            <label class="form-label">Current Meter Reading</label>
                            <input type="number" class="form-control" id="previous_meter_reading" value="{{ config.previous_meter_reading }}" step="0.1">
                        </div>
                        <div class="col">
                            <label class="form-label">Next Bill Number</label>
                            <input type="number" class="form-control" id="next_bill_number" value="{{ config.next_bill_number }}" step="1">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary w-100" id="saveBtn">Save Settings</button>
                </form>
                <div class="alert alert-success mt-3 d-none" id="successAlert">Settings saved successfully!</div>
                <div class="alert alert-danger mt-3 d-none" id="errorAlert"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    document.getElementById("settingsForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        document.getElementById("successAlert").classList.add("d-none");
        document.getElementById("errorAlert").classList.add("d-none");
        
        const data = {
            landlord_name: document.getElementById("landlord_name").value,
            landlord_phone: document.getElementById("landlord_phone").value,
            landlord_email: document.getElementById("landlord_email").value,
            property_address: document.getElementById("property_address").value,
            default_rent: parseFloat(document.getElementById("default_rent").value) || 0,
            additional_person_charge: parseFloat(document.getElementById("additional_person_charge").value) || 0,
            water_charge: parseFloat(document.getElementById("water_charge").value) || 0,
            electricity_rate: parseFloat(document.getElementById("electricity_rate").value) || 0,
            previous_meter_reading: parseFloat(document.getElementById("previous_meter_reading").value) || 0,
            next_bill_number: parseInt(document.getElementById("next_bill_number").value) || 1
        };
        
        const btn = document.getElementById("saveBtn");
        btn.disabled = true;
        btn.innerText = "Saving...";
        
        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            
            if (res.ok) {
                document.getElementById("successAlert").classList.remove("d-none");
            } else {
                document.getElementById("errorAlert").innerText = "Error saving settings.";
                document.getElementById("errorAlert").classList.remove("d-none");
            }
        } catch(err) {
            document.getElementById("errorAlert").innerText = "Network error occurred.";
            document.getElementById("errorAlert").classList.remove("d-none");
        } finally {
            btn.disabled = false;
            btn.innerText = "Save Settings";
        }
    });
</script>
{% endblock %}
```

```html
// File: rent-receipt/templates/tenants.html
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-5 mb-4">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">Add New Tenant</h4>
            </div>
            <div class="card-body">
                <form id="tenantForm">
                    <div class="mb-3">
                        <label class="form-label">Tenant Name</label>
                        <input type="text" class="form-control" id="t_name" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Phone</label>
                        <input type="text" class="form-control" id="t_phone">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control" id="t_email">
                    </div>
                    <button type="submit" class="btn btn-success w-100" id="addBtn">Add Tenant</button>
                </form>
                <div class="alert alert-success mt-3 d-none" id="successAlert">Tenant added successfully!</div>
                <div class="alert alert-danger mt-3 d-none" id="errorAlert"></div>
            </div>
        </div>
    </div>
    
    <div class="col-md-7">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Existing Tenants</h4>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-striped mb-0">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Phone</th>
                                <th>Email</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for t in tenants %}
                            <tr>
                                <td>{{ t.name }}</td>
                                <td>{{ t.phone }}</td>
                                <td>{{ t.email }}</td>
                                <td>
                                    <button class="btn btn-sm btn-danger" onclick="deleteTenant({{ t.id }})">Delete</button>
                                </td>
                            </tr>
                            {% endfor %}
                            {% if not tenants %}
                            <tr><td colspan="4" class="text-center">No tenants found.</td></tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    document.getElementById("tenantForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        const btn = document.getElementById("addBtn");
        btn.disabled = true;
        btn.innerText = "Adding...";
        
        try {
            const res = await fetch("/api/tenants", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: document.getElementById("t_name").value,
                    phone: document.getElementById("t_phone").value,
                    email: document.getElementById("t_email").value
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                window.location.reload();
            } else {
                document.getElementById("errorAlert").innerText = data.message || "Error adding tenant.";
                document.getElementById("errorAlert").classList.remove("d-none");
                btn.disabled = false;
                btn.innerText = "Add Tenant";
            }
        } catch(err) {
            document.getElementById("errorAlert").innerText = "Network error occurred.";
            document.getElementById("errorAlert").classList.remove("d-none");
            btn.disabled = false;
            btn.innerText = "Add Tenant";
        }
    });
    
    async function deleteTenant(id) {
        if (!confirm("Are you sure you want to delete this tenant?")) return;
        try {
            await fetch(`/api/tenants/${id}`, { method: "DELETE" });
            window.location.reload();
        } catch(e) {
            alert("Failed to delete tenant");
        }
    }
</script>
{% endblock %}
```

```
// File: rent-receipt/tenant.csv
Bill,Date,Month,Tenant,Previous,Current,Units,Rent,Additional,Water,Electricity,Total,PDF
001,30-06-2026,June 2026,LT Elevator,0.0,100.0,100.0,8000.0,2000.0,500.0,1500.0,12000.0,001.pdf
```

```
// File: rent-receipt/tenant_backup.csv
Bill,Date,Month,Tenant,Previous,Current,Units,Rent,Additional,Water,Electricity,Total,PDF
```

```python
// File: rent-receipt/utils/billing.py
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
```

```python
// File: rent-receipt/utils/config_manager.py
import json
import os
import shutil

CONFIG_FILE = "config.json"
BACKUP_FILE = "config_backup.json"

DEFAULT_CONFIG = {
    "landlord_name": "",
    "landlord_phone": "",
    "landlord_email": "",
    "property_address": "",
    "default_rent": 8000,
    "additional_person_charge": 1000,
    "water_charge": 500,
    "electricity_rate": 15,
    "previous_meter_reading": 0,
    "next_bill_number": 1
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
    if os.path.exists(CONFIG_FILE):
        try:
            shutil.copy2(CONFIG_FILE, BACKUP_FILE)
        except Exception:
            pass
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")
```

```python
// File: rent-receipt/utils/csv_manager.py
import csv
import os
import shutil

CSV_FILE = "tenant.csv"
BACKUP_FILE = "tenant_backup.csv"

HEADERS = [
    "Bill", "Date", "Month", "Tenant", "Previous", "Current", 
    "Units", "Rent", "Additional", "Water", "Electricity", "Total", "PDF"
]

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

def save_receipt_data(data_dict):
    init_csv()
    
    if os.path.exists(CSV_FILE):
        try:
            shutil.copy2(CSV_FILE, BACKUP_FILE)
        except Exception:
            pass

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writerow(data_dict)

def get_all_receipts():
    init_csv()
    receipts = []
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            receipts.append(row)
    return receipts

def get_receipt(bill_no):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == bill_no:
            return r
    return None

def update_receipt(bill_no, updated_data):
    receipts = get_all_receipts()
    for i, r in enumerate(receipts):
        if r["Bill"] == bill_no:
            receipts[i] = updated_data
            break
            
    if os.path.exists(CSV_FILE):
        try:
            shutil.copy2(CSV_FILE, BACKUP_FILE)
        except Exception:
            pass

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(receipts)
```

```python
// File: rent-receipt/utils/pdf.py
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
```

```python
// File: rent-receipt/utils/tenant_manager.py
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
```
