```json
// File: config.json
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
// File: main.py
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
// File: ui/billing.py
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
// File: ui/dashboard.py
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
// File: ui/history.py
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
// File: ui/settings.py
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
// File: utils/bill_manager.py
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
// File: utils/config.py
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
// File: utils/csv_manager.py
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
// File: utils/pdf_generator.py
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
// File: app.py
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import os

from services.config_service import (
    get_billing_config, save_billing_config,
    get_landlord_config, save_landlord_config,
    get_ui_config, save_ui_config
)
from services.tenant_service import (
    load_tenants, add_tenant, update_tenant, delete_tenant
)
from services.billing_service import (
    get_all_receipts, get_receipt, get_billing_months,
    calculate_charges, create_bill, update_bill, delete_bill,
    get_dashboard_stats
)
from models.tenant import Tenant

app = FastAPI(title="Rent Receipt Web Application")

# Mount Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- UI Theme Context Injection ---
@app.middleware("http")
async def add_theme_to_templates(request: Request, call_next):
    # Store theme in request state so it is accessible in template responses
    ui_conf = get_ui_config()
    request.state.theme = ui_conf.get("theme", "system")
    response = await call_next(request)
    return response

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_dashboard_stats()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={
            "stats": stats,
            "theme": theme
        }
    )

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    billing_conf = get_billing_config()
    tenants = [t for t in load_tenants() if t.status == "Active"]
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="billing.html", context={
            "config": billing_conf,
            "tenants": tenants,
            "theme": theme
        }
    )

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts()
    receipts.reverse()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="history.html", context={
            "receipts": receipts,
            "theme": theme
        }
    )

@app.get("/tenants", response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = load_tenants()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="tenants.html", context={
            "tenants": tenants,
            "theme": theme
        }
    )

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    billing_conf = get_billing_config()
    landlord_conf = get_landlord_config()
    ui_conf = get_ui_config()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="settings.html", context={
            "billing_config": billing_conf,
            "landlord_config": landlord_conf,
            "ui_config": ui_conf,
            "theme": theme
        }
    )

@app.get("/edit_bill/{bill_no}", response_class=HTMLResponse)
async def edit_bill_page(request: Request, bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    billing_conf = get_billing_config()
    tenants = load_tenants()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="edit_bill.html", context={
            "receipt": receipt,
            "config": billing_conf,
            "tenants": tenants,
            "theme": theme
        }
    )

# --- REST API ---

@app.get("/api/config")
async def get_config():
    return {
        "billing": get_billing_config(),
        "landlord": get_landlord_config(),
        "ui": get_ui_config()
    }

class ConfigUpdateModel(BaseModel):
    landlord: dict
    billing: dict

@app.post("/api/config")
async def update_config(data: ConfigUpdateModel):
    save_landlord_config(data.landlord)
    save_billing_config(data.billing)
    return {"status": "success"}

@app.post("/api/ui/theme")
async def update_theme(data: dict):
    theme = data.get("theme", "system")
    ui_conf = get_ui_config()
    ui_conf["theme"] = theme
    save_ui_config(ui_conf)
    return {"status": "success"}

@app.get("/api/billing/months")
async def api_billing_months():
    return get_billing_months()

@app.get("/api/billing/preview")
async def api_billing_preview(current_reading: float, additional_persons: int):
    return calculate_charges(current_reading, additional_persons)

class BillRequest(BaseModel):
    tenant: str
    month: str
    current_reading: float
    additional_persons: int

@app.post("/api/bill")
async def api_create_bill(request: BillRequest):
    billing_conf = get_billing_config()
    prev = float(billing_conf.get("previous_meter_reading", 0.0))
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current meter reading cannot be less than previous reading.")
        
    try:
        data = create_bill(
            request.tenant,
            request.month,
            request.current_reading,
            request.additional_persons
        )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/edit_bill/{bill_no}")
async def api_update_bill(bill_no: str, request: BillRequest):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    prev = float(receipt["Previous"])
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current meter reading cannot be less than previous reading.")
        
    try:
        data = update_bill(
            bill_no,
            request.tenant,
            request.month,
            request.current_reading,
            request.additional_persons
        )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/bill/{bill_no}")
async def api_delete_bill(bill_no: str):
    try:
        delete_bill(bill_no)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/pdf/{bill_no}")
async def download_pdf(bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
        
    try:
        year_str = receipt["Month"].split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_path = os.path.join("receipts", year_str, receipt["PDF"])
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type='application/pdf', filename=f"Receipt_{bill_no}.pdf")
    else:
        # Fallback: Regenerate PDF if missing
        try:
            from services.pdf_service import generate_professional_pdf
            landlord_conf = get_landlord_config()
            generate_professional_pdf(receipt, landlord_conf, pdf_path)
            return FileResponse(pdf_path, media_type='application/pdf', filename=f"Receipt_{bill_no}.pdf")
        except Exception:
            raise HTTPException(status_code=404, detail="PDF file not found and could not be regenerated.")

@app.get("/api/tenants")
async def api_get_tenants():
    return load_tenants()

@app.post("/api/tenants")
async def api_add_tenant(t: Tenant):
    return add_tenant(t)

@app.put("/api/tenants/{tenant_id}")
async def api_update_tenant(tenant_id: int, t: Tenant):
    t.id = tenant_id
    return update_tenant(t)

@app.delete("/api/tenants/{tenant_id}")
async def api_delete_tenant(tenant_id: int):
    delete_tenant(tenant_id)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=20081, reload=True)
```

```
// File: backups/billing.json.bak
{
    "rent": 8000,
    "water": 500,
    "electricity_rate": 15,
    "additional_person_charge": 1000,
    "previous_meter_reading": 597,
    "next_bill_number": 1
}
```

```
// File: backups/landlord.json.bak
{
    "name": "Vijay Kumar Sharma",
    "phone": "9599130381",
    "email": "sharmajiindia2012@gmail.com",
    "address": "House No 1, Street No 1, E Block, Shiv Durga Vihar Lakkarpur, Surajkund Faridabad, Faridabad Haryana - 121009"
}
```

```
// File: backups/receipts.csv.bak
Bill,Date,Month,Tenant,Previous,Current,Units,Rent,Additional,Water,Electricity,Total,PDF,Tenant_Phone,Tenant_Company,Tenant_Address
```

```
// File: backups/tenants.csv.bak
ID,Tenant Name,Company,Phone,Email,Permanent Address,Room Number,Occupation,Notes,Status
```

```json
// File: config/billing.json
{
    "rent": 8000,
    "water": 500,
    "electricity_rate": 15,
    "additional_person_charge": 1000,
    "previous_meter_reading": 709.0,
    "next_bill_number": 2
}
```

```json
// File: config/landlord.json
{
    "name": "Vijay Kumar Sharma",
    "phone": "9599130381",
    "email": "sharmajiindia2012@gmail.com",
    "address": "House No 1, Street No 1, E Block, Shiv Durga Vihar Lakkarpur, Surajkund Faridabad, Faridabad Haryana - 121009"
}
```

```json
// File: config/ui.json
{
    "theme": "system"
}
```

```
// File: database/receipts.csv
Bill,Date,Month,Tenant,Previous,Current,Units,Rent,Additional,Water,Electricity,Total,PDF,Tenant_Phone,Tenant_Company,Tenant_Address,Rate
001,30 June 2026,June 2026,L T Elevator,597.0,709.0,112.0,8000.0,2000.0,500.0,1680.0,12180.0,001.pdf,,,,15.0
```

```
// File: database/tenants.csv
ID,Tenant Name,Company,Phone,Email,Permanent Address,Room Number,Occupation,Notes,Status
1,L T Elevator,,,,,2nd Floor,,,Active
```

```
// File: install.log
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

```python
// File: models/receipt.py
from pydantic import BaseModel
from typing import Optional

class Receipt(BaseModel):
    bill_no: str
    date: str
    month: str
    tenant_name: str
    previous_reading: float
    current_reading: float
    units_consumed: float
    rent: float
    additional_charge: float
    water_charge: float
    electricity_charge: float
    total: float
    pdf_filename: str
```

```python
// File: models/tenant.py
from pydantic import BaseModel, Field
from typing import Optional

class Tenant(BaseModel):
    id: Optional[int] = None
    name: str
    company: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    room_number: Optional[str] = ""
    occupation: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "Active" # Active or Inactive
```

```text
// File: requirements.txt
fastapi
uvicorn
jinja2
python-multipart
reportlab
num2words
pydantic
```

```
// File: server.log
INFO:     Will watch for changes in these directories: ['/root/rent/rent-receipt']
INFO:     Uvicorn running on http://0.0.0.0:20081 (Press CTRL+C to quit)
INFO:     Started reloader process [12443] using StatReload
INFO:     Started server process [12445]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:58044 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:58044 - "GET /static/css/style.css HTTP/1.1" 200 OK
INFO:     127.0.0.1:58044 - "GET /tenants HTTP/1.1" 500 Internal Server Error
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
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 191, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.13/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/rent/rent-receipt/app.py", line 37, in add_theme_to_templates
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
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
  File "/root/rent/rent-receipt/app.py", line 81, in tenants_page
    return templates.TemplateResponse(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^
        request=request, name="tenants.html", context={
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        }
        ^
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 149, in TemplateResponse
    return _TemplateResponse(
        template,
    ...<4 lines>...
        background=background,
    )
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 43, in __init__
    content = template.render(context)
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "templates/tenants.html", line 1, in top-level template code
    {% extends "base.html" %}
  File "templates/base.html", line 75, in top-level template code
    {% block content %}{% endblock %}
    ^^^^^^^^^^^^^
  File "templates/tenants.html", line 121, in block 'content'
    <button class="btn btn-sm btn-outline-primary" onclick="editTenant({{ t | tojson }})"><i class="bi bi-pencil"></i> Edit</button>
    
  File "/root/venv/lib/python3.13/site-packages/jinja2/filters.py", line 1721, in do_tojson
    return htmlsafe_json_dumps(value, dumps=dumps, **kwargs)
  File "/root/venv/lib/python3.13/site-packages/jinja2/utils.py", line 669, in htmlsafe_json_dumps
    dumps(obj, **kwargs)
    ~~~~~^^^^^^^^^^^^^^^
  File "/usr/lib/python3.13/json/__init__.py", line 238, in dumps
    **kw).encode(obj)
          ~~~~~~^^^^^
  File "/usr/lib/python3.13/json/encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/lib/python3.13/json/encoder.py", line 261, in iterencode
    return _iterencode(o, 0)
  File "/usr/lib/python3.13/json/encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
                    f'is not JSON serializable')
TypeError: Object of type Tenant is not JSON serializable
INFO:     127.0.0.1:58054 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:58054 - "GET /tenants HTTP/1.1" 500 Internal Server Error
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
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 191, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.13/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/rent/rent-receipt/app.py", line 37, in add_theme_to_templates
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
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
  File "/root/rent/rent-receipt/app.py", line 81, in tenants_page
    return templates.TemplateResponse(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^
        request=request, name="tenants.html", context={
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        }
        ^
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 149, in TemplateResponse
    return _TemplateResponse(
        template,
    ...<4 lines>...
        background=background,
    )
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 43, in __init__
    content = template.render(context)
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "templates/tenants.html", line 1, in top-level template code
    {% extends "base.html" %}
  File "templates/base.html", line 75, in top-level template code
    {% block content %}{% endblock %}
    ^^^^^^^^^^^^^
  File "templates/tenants.html", line 121, in block 'content'
    <button class="btn btn-sm btn-outline-primary" onclick="editTenant({{ t | tojson }})"><i class="bi bi-pencil"></i> Edit</button>
    
  File "/root/venv/lib/python3.13/site-packages/jinja2/filters.py", line 1721, in do_tojson
    return htmlsafe_json_dumps(value, dumps=dumps, **kwargs)
  File "/root/venv/lib/python3.13/site-packages/jinja2/utils.py", line 669, in htmlsafe_json_dumps
    dumps(obj, **kwargs)
    ~~~~~^^^^^^^^^^^^^^^
  File "/usr/lib/python3.13/json/__init__.py", line 238, in dumps
    **kw).encode(obj)
          ~~~~~~^^^^^
  File "/usr/lib/python3.13/json/encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/lib/python3.13/json/encoder.py", line 261, in iterencode
    return _iterencode(o, 0)
  File "/usr/lib/python3.13/json/encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
                    f'is not JSON serializable')
TypeError: Object of type Tenant is not JSON serializable
INFO:     127.0.0.1:51872 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:51872 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:51876 - "GET /tenants HTTP/1.1" 500 Internal Server Error
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
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 191, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.13/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/rent/rent-receipt/app.py", line 37, in add_theme_to_templates
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
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
  File "/root/rent/rent-receipt/app.py", line 81, in tenants_page
    return templates.TemplateResponse(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^
        request=request, name="tenants.html", context={
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        }
        ^
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 149, in TemplateResponse
    return _TemplateResponse(
        template,
    ...<4 lines>...
        background=background,
    )
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 43, in __init__
    content = template.render(context)
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "templates/tenants.html", line 1, in top-level template code
    {% extends "base.html" %}
  File "templates/base.html", line 75, in top-level template code
    {% block content %}{% endblock %}
    ^^^^^^^^^^^^^
  File "templates/tenants.html", line 121, in block 'content'
    <button class="btn btn-sm btn-outline-primary" onclick="editTenant({{ t | tojson }})"><i class="bi bi-pencil"></i> Edit</button>
    
  File "/root/venv/lib/python3.13/site-packages/jinja2/filters.py", line 1721, in do_tojson
    return htmlsafe_json_dumps(value, dumps=dumps, **kwargs)
  File "/root/venv/lib/python3.13/site-packages/jinja2/utils.py", line 669, in htmlsafe_json_dumps
    dumps(obj, **kwargs)
    ~~~~~^^^^^^^^^^^^^^^
  File "/usr/lib/python3.13/json/__init__.py", line 238, in dumps
    **kw).encode(obj)
          ~~~~~~^^^^^
  File "/usr/lib/python3.13/json/encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/lib/python3.13/json/encoder.py", line 261, in iterencode
    return _iterencode(o, 0)
  File "/usr/lib/python3.13/json/encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
                    f'is not JSON serializable')
TypeError: Object of type Tenant is not JSON serializable
INFO:     127.0.0.1:33392 - "GET /tenants HTTP/1.1" 500 Internal Server Error
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
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 191, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.13/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
    raise exc
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/rent/rent-receipt/app.py", line 37, in add_theme_to_templates
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/root/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
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
  File "/root/rent/rent-receipt/app.py", line 81, in tenants_page
    return templates.TemplateResponse(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^
        request=request, name="tenants.html", context={
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        }
        ^
    )
    ^
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 149, in TemplateResponse
    return _TemplateResponse(
        template,
    ...<4 lines>...
        background=background,
    )
  File "/root/venv/lib/python3.13/site-packages/starlette/templating.py", line 43, in __init__
    content = template.render(context)
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/root/venv/lib/python3.13/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "templates/tenants.html", line 1, in top-level template code
    {% extends "base.html" %}
  File "templates/base.html", line 75, in top-level template code
    {% block content %}{% endblock %}
    ^^^^^^^^^^^^^
  File "templates/tenants.html", line 121, in block 'content'
    <button class="btn btn-sm btn-outline-primary" onclick="editTenant({{ t | tojson }})"><i class="bi bi-pencil"></i> Edit</button>
    
  File "/root/venv/lib/python3.13/site-packages/jinja2/filters.py", line 1721, in do_tojson
    return htmlsafe_json_dumps(value, dumps=dumps, **kwargs)
  File "/root/venv/lib/python3.13/site-packages/jinja2/utils.py", line 669, in htmlsafe_json_dumps
    dumps(obj, **kwargs)
    ~~~~~^^^^^^^^^^^^^^^
  File "/usr/lib/python3.13/json/__init__.py", line 238, in dumps
    **kw).encode(obj)
          ~~~~~~^^^^^
  File "/usr/lib/python3.13/json/encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/lib/python3.13/json/encoder.py", line 261, in iterencode
    return _iterencode(o, 0)
  File "/usr/lib/python3.13/json/encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
                    f'is not JSON serializable')
TypeError: Object of type Tenant is not JSON serializable
INFO:     127.0.0.1:33396 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:33396 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:33396 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:33396 - "GET /api/billing/months HTTP/1.1" 200 OK
Error saving receipts: dict contains fields not in fieldnames: 'Rate'
INFO:     127.0.0.1:45298 - "POST /api/bill HTTP/1.1" 200 OK
INFO:     127.0.0.1:45298 - "GET /api/pdf/001 HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:45298 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:45298 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:45298 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:48354 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:48354 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:48354 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:48354 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:48360 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:48360 - "GET /tenants HTTP/1.1" 200 OK
INFO:     127.0.0.1:48360 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:48360 - "GET /api/billing/months HTTP/1.1" 200 OK
WARNING:  StatReload detected changes in 'services/billing_service.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [12445]
INFO:     Started server process [13372]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:49330 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:49330 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:45184 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:45184 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:45196 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:45196 - "GET /tenants HTTP/1.1" 200 OK
INFO:     127.0.0.1:45196 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:45196 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:45196 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:45196 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:43278 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:43278 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:43278 - "GET /settings HTTP/1.1" 200 OK
INFO:     127.0.0.1:36310 - "POST /api/config HTTP/1.1" 200 OK
INFO:     127.0.0.1:36310 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:36310 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:36310 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:54318 - "POST /api/bill HTTP/1.1" 200 OK
INFO:     127.0.0.1:54318 - "GET /api/pdf/001 HTTP/1.1" 200 OK
INFO:     127.0.0.1:54318 - "GET /billing HTTP/1.1" 200 OK
INFO:     127.0.0.1:54318 - "GET /static/css/style.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:54318 - "GET /api/billing/months HTTP/1.1" 200 OK
INFO:     127.0.0.1:35352 - "GET / HTTP/1.1" 200 OK
```

```python
// File: services/billing_service.py
import csv
import os
import shutil
from datetime import datetime
from services.config_service import get_billing_config, save_billing_config, get_landlord_config
from services.tenant_service import load_tenants
from services.pdf_service import generate_professional_pdf

DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)

RECEIPTS_CSV = os.path.join(DB_DIR, "receipts.csv")
BACKUP_DIR = "backups"

HEADERS = [
    "Bill", "Date", "Month", "Tenant", "Previous", "Current", 
    "Units", "Rent", "Additional", "Water", "Electricity", "Total", "PDF",
    "Tenant_Phone", "Tenant_Company", "Tenant_Address", "Rate"
]

def init_csv():
    if not os.path.exists(RECEIPTS_CSV):
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def get_all_receipts():
    init_csv()
    receipts = []
    try:
        with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                receipts.append(row)
    except Exception as e:
        print(f"Error loading receipts: {e}")
    return receipts

def get_receipt(bill_no):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == bill_no:
            return r
    return None

def save_all_receipts(receipts_list):
    init_csv()
    if os.path.exists(RECEIPTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "receipts.csv.bak")
        try:
            shutil.copy2(RECEIPTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(receipts_list)
    except Exception as e:
        print(f"Error saving receipts: {e}")

def get_billing_months():
    now = datetime.now()
    current_year = now.year
    current_month_idx = now.month  # 1-12
    
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    months_list = []
    for i in range(current_month_idx):
        months_list.append(f"{months_names[i]} {current_year}")
        
    return {
        "currentMonth": f"{months_names[current_month_idx - 1]} {current_year}",
        "months": months_list
    }

def calculate_charges(current_reading, additional_persons, prev_reading=None):
    billing_conf = get_billing_config()
    
    rent = float(billing_conf.get("rent", 8000.0))
    water = float(billing_conf.get("water", 500.0))
    rate = float(billing_conf.get("electricity_rate", 15.0))
    add_person_charge = float(billing_conf.get("additional_person_charge", 1000.0))
    
    if prev_reading is None:
        prev_reading = float(billing_conf.get("previous_meter_reading", 0.0))
        
    units = max(0.0, current_reading - prev_reading)
    electricity = units * rate
    additional = additional_persons * add_person_charge
    total = rent + additional + water + electricity
    
    return {
        "rent": rent,
        "water": water,
        "rate": rate,
        "additional": additional,
        "units": units,
        "electricity": electricity,
        "total": total,
        "previous": prev_reading
    }

def create_bill(tenant_name, month, current_reading, additional_persons):
    billing_conf = get_billing_config()
    landlord_conf = get_landlord_config()
    tenants = load_tenants()
    
    # Find tenant details
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    t_phone = tenant_details.phone if tenant_details else ""
    t_company = tenant_details.company if tenant_details else ""
    t_address = tenant_details.address if tenant_details else ""
    
    charges = calculate_charges(current_reading, additional_persons)
    
    bill_no = str(billing_conf.get("next_bill_number", 1)).zfill(3)
    date_str = datetime.now().strftime("%d %B %Y")
    
    # Group PDF by year
    # Extract year from month ("July 2026" -> "2026")
    try:
        year_str = month.split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_filename = f"{bill_no}.pdf"
    pdf_path = os.path.join("receipts", year_str, pdf_filename)
    
    data_dict = {
        "Bill": bill_no,
        "Date": date_str,
        "Month": month,
        "Tenant": tenant_name,
        "Previous": charges["previous"],
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": t_phone,
        "Tenant_Company": t_company,
        "Tenant_Address": t_address,
        "Rate": charges["rate"]
    }
    
    # Generate PDF
    generate_professional_pdf(data_dict, landlord_conf, pdf_path)
    
    # Save receipt info
    init_csv()
    receipts = get_all_receipts()
    receipts.append(data_dict)
    save_all_receipts(receipts)
    
    # Update configs
    billing_conf["next_bill_number"] = int(bill_no) + 1
    billing_conf["previous_meter_reading"] = current_reading
    save_billing_config(billing_conf)
    
    return data_dict

def update_bill(bill_no, tenant_name, month, current_reading, additional_persons):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    landlord_conf = get_landlord_config()
    tenants = load_tenants()
    
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    t_phone = tenant_details.phone if tenant_details else ""
    t_company = tenant_details.company if tenant_details else ""
    t_address = tenant_details.address if tenant_details else ""
    
    # Recalculate using original previous reading
    prev_reading = float(receipt["Previous"])
    charges = calculate_charges(current_reading, additional_persons, prev_reading=prev_reading)
    
    try:
        year_str = month.split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_filename = receipt.get("PDF", f"{bill_no}.pdf")
    pdf_path = os.path.join("receipts", year_str, pdf_filename)
    
    updated_dict = {
        "Bill": bill_no,
        "Date": receipt["Date"],
        "Month": month,
        "Tenant": tenant_name,
        "Previous": prev_reading,
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": t_phone,
        "Tenant_Company": t_company,
        "Tenant_Address": t_address,
        "Rate": charges["rate"]
    }
    
    # Regenerate PDF
    generate_professional_pdf(updated_dict, landlord_conf, pdf_path)
    
    # Update CSV list
    for idx, item in enumerate(receipts):
        if item["Bill"] == bill_no:
            receipts[idx] = updated_dict
            break
    save_all_receipts(receipts)
    
    return updated_dict

def delete_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    try:
        year_str = receipt["Month"].split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_path = os.path.join("receipts", year_str, receipt["PDF"])
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass
            
    receipts = [r for r in receipts if r["Bill"] != bill_no]
    save_all_receipts(receipts)

def get_dashboard_stats():
    billing_conf = get_billing_config()
    receipts = get_all_receipts()
    tenants = load_tenants()
    
    next_bill = str(billing_conf.get("next_bill_number", 1)).zfill(3)
    months_info = get_billing_months()
    current_month = months_info["currentMonth"]
    prev_reading = billing_conf.get("previous_meter_reading", 0.0)
    
    total_tenants = len([t for t in tenants if t.status == "Active"])
    total_receipts = len(receipts)
    
    # Revenue this month
    revenue_this_month = 0.0
    for r in receipts:
        if r["Month"] == current_month:
            revenue_this_month += float(r.get("Total", 0.0))
            
    # Recent bills (last 5)
    recent_bills = []
    for r in reversed(receipts[-5:]):
        recent_bills.append({
            "bill_no": r["Bill"],
            "tenant_name": r["Tenant"],
            "total": r["Total"],
            "month": r["Month"]
        })
        
    # Stats for Charts
    # Group revenue/electricity by month for the current year
    current_year = datetime.now().strftime("%Y")
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    revenue_chart_data = {m: 0.0 for m in months_names}
    electricity_chart_data = {m: 0.0 for m in months_names}
    
    for r in receipts:
        try:
            r_month, r_year = r["Month"].split()
            if r_year == current_year and r_month in revenue_chart_data:
                revenue_chart_data[r_month] += float(r.get("Total", 0.0))
                electricity_chart_data[r_month] += float(r.get("Units", 0.0))
        except Exception:
            pass
            
    # Convert dict to ordered lists
    chart_months = [m for m in months_names if revenue_chart_data[m] > 0 or electricity_chart_data[m] > 0]
    if not chart_months:
        # Default to showing at least up to current month
        now_month_idx = datetime.now().month
        chart_months = months_names[:now_month_idx]
        
    revenue_list = [revenue_chart_data[m] for m in chart_months]
    electricity_list = [electricity_chart_data[m] for m in chart_months]
    
    return {
        "next_bill": next_bill,
        "current_month": current_month,
        "prev_reading": prev_reading,
        "total_tenants": total_tenants,
        "total_receipts": total_receipts,
        "revenue_this_month": revenue_this_month,
        "recent_bills": recent_bills,
        "chart_labels": chart_months,
        "chart_revenue": revenue_list,
        "chart_electricity": electricity_list
    }
```

```python
// File: services/config_service.py
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
```

```python
// File: services/pdf_service.py
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from num2words import num2words

def generate_professional_pdf(data, landlord_config, output_path):
    # Ensure parent dir exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Border
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2.0, height - 70, "RENT RECEIPT")
    
    # Decorative line
    c.setLineWidth(2)
    c.line(40, height - 85, width - 40, height - 85)
    
    # Receipt Details Top Right / Left
    c.setFont("Helvetica", 11)
    y = height - 120
    c.drawString(50, y, f"Receipt No: {data['Bill']}")
    c.drawRightString(width - 50, y, f"Date: {data['Date']}")
    y -= 20
    c.drawString(50, y, f"Billing Month: {data['Month']}")
    
    c.setLineWidth(1)
    y -= 15
    c.line(40, y, width - 40, y)
    
    # Landlord & Tenant details side-by-side
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "LANDLORD")
    c.drawString(width/2 + 20, y, "TENANT")
    
    c.setFont("Helvetica", 10)
    # Landlord
    y -= 15
    c.drawString(50, y, f"Name: {landlord_config.get('name', '')}")
    # Tenant
    tenant_name = data.get('Tenant', '')
    c.drawString(width/2 + 20, y, f"Name: {tenant_name}")
    
    y -= 15
    c.drawString(50, y, f"Phone: {landlord_config.get('phone', '')}")
    c.drawString(width/2 + 20, y, f"Phone: {data.get('Tenant_Phone', '')}")
    
    y -= 15
    c.drawString(50, y, f"Email: {landlord_config.get('email', '')}")
    # Render address or company for Tenant
    company = data.get('Tenant_Company', '')
    if company:
        c.drawString(width/2 + 20, y, f"Company: {company}")
        y -= 15
        
    c.drawString(50, y, f"Address: {landlord_config.get('address', '')}")
    # Tenant Address
    tenant_addr = data.get('Tenant_Address', '')
    # Wrap address text if long
    c.drawString(width/2 + 20, y, f"Address: {tenant_addr[:40]}")
    if len(tenant_addr) > 40:
        y -= 12
        c.drawString(width/2 + 65, y, tenant_addr[40:80])
        
    y -= 20
    c.line(40, y, width - 40, y)
    
    # Table Description Header
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "DESCRIPTION")
    c.drawRightString(width - 60, y, "AMOUNT (₹)")
    
    y -= 10
    c.line(50, y, width - 50, y)
    
    # Table Content
    items = [
        ("Rent", float(data.get('Rent', 0))),
        ("Additional Person Charges", float(data.get('Additional', 0))),
        ("Water Charges", float(data.get('Water', 0))),
        ("Electricity Charges", float(data.get('Electricity', 0)))
    ]
    
    c.setFont("Helvetica", 11)
    for name, amt in items:
        y -= 20
        c.drawString(60, y, name)
        c.drawRightString(width - 60, y, f"₹{amt:,.2f}")
        
    y -= 15
    c.line(50, y, width - 50, y)
    
    # Total
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "TOTAL")
    c.drawRightString(width - 60, y, f"₹{float(data.get('Total', 0)):,.2f}")
    
    y -= 15
    c.line(40, y, width - 40, y)
    
    # Electricity Details
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Electricity Details")
    
    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(50, y, f"Previous Reading: {data.get('Previous', 0)}")
    c.drawString(width/2, y, f"Current Reading: {data.get('Current', 0)}")
    y -= 15
    c.drawString(50, y, f"Consumed: {data.get('Units', 0)} units")
    rate = data.get('Rate', landlord_config.get('electricity_rate', 15.0))
    c.drawString(width/2, y, f"Rate: ₹{rate}/unit")
    
    y -= 20
    c.line(40, y, width - 40, y)
    
    # Amount in words
    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Amount in Words:")
    c.setFont("Helvetica-Oblique", 11)
    try:
        total_float = float(data['Total'])
        words = num2words(total_float, lang='en_IN').replace(',', '').title()
        c.drawString(160, y, f"Rupees {words} Only")
    except Exception:
        c.drawString(160, y, f"{data['Total']}")
        
    # Signature
    y -= 60
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 60, y, "________________________")
    y -= 15
    c.drawRightString(width - 60, y, "Landlord Signature")
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 60, y, landlord_config.get('name', ''))
    
    c.showPage()
    c.save()
    return output_path
```

```python
// File: services/tenant_service.py
import csv
import os
import shutil
from models.tenant import Tenant

DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)

TENANTS_CSV = os.path.join(DB_DIR, "tenants.csv")
BACKUP_DIR = "backups"

HEADERS = [
    "ID", "Tenant Name", "Company", "Phone", "Email", 
    "Permanent Address", "Room Number", "Occupation", "Notes", "Status"
]

def init_csv():
    if not os.path.exists(TENANTS_CSV):
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def load_tenants():
    init_csv()
    tenants = []
    try:
        with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Map CSV keys to Tenant alias keys
                t = Tenant(
                    id=int(row["ID"]) if row["ID"] else None,
                    name=row["Tenant Name"],
                    company=row["Company"],
                    phone=row["Phone"],
                    email=row["Email"],
                    address=row["Permanent Address"],
                    room_number=row["Room Number"],
                    occupation=row["Occupation"],
                    notes=row["Notes"],
                    status=row["Status"]
                )
                tenants.append(t)
    except Exception as e:
        print(f"Error loading tenants: {e}")
    return tenants

def save_all_tenants(tenants_list):
    init_csv()
    # Backup
    if os.path.exists(TENANTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "tenants.csv.bak")
        try:
            shutil.copy2(TENANTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
            for t in tenants_list:
                row = {
                    "ID": t.id,
                    "Tenant Name": t.name,
                    "Company": t.company,
                    "Phone": t.phone,
                    "Email": t.email,
                    "Permanent Address": t.address,
                    "Room Number": t.room_number,
                    "Occupation": t.occupation,
                    "Notes": t.notes,
                    "Status": t.status
                }
                writer.writerow(row)
    except Exception as e:
        print(f"Error saving tenants: {e}")

def add_tenant(t: Tenant):
    tenants = load_tenants()
    # Find next ID
    next_id = 1
    if tenants:
        next_id = max(x.id for x in tenants if x.id is not None) + 1
    t.id = next_id
    tenants.append(t)
    save_all_tenants(tenants)
    return t

def update_tenant(t: Tenant):
    tenants = load_tenants()
    for idx, item in enumerate(tenants):
        if item.id == t.id:
            tenants[idx] = t
            break
    save_all_tenants(tenants)
    return t

def delete_tenant(tenant_id: int):
    tenants = load_tenants()
    tenants = [t for t in tenants if t.id != tenant_id]
    save_all_tenants(tenants)
```

```css
// File: static/css/style.css
body {
    font-size: .875rem;
}

/* Sidebar layout adjustments */
.sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 100; /* Behind the navbar */
    padding: 20px 0 0; /* Adjusted for no navbar */
    box-shadow: inset -1px 0 0 rgba(0, 0, 0, .1);
    width: 250px;
}

@media (min-width: 768px) {
    main {
        margin-left: 250px !important;
        width: calc(100% - 250px) !important;
    }
}

@media (max-width: 767.98px) {
    .sidebar {
        position: relative;
        padding-top: 20px;
        min-height: auto !important;
        width: 100%;
    }
    main {
        margin-left: 0 !important;
        width: 100% !important;
    }
}

.sidebar .nav-link {
    font-weight: 500;
    color: var(--bs-body-color);
    border-radius: 6px;
    padding: 0.6rem 1rem;
}

.sidebar .nav-link:hover {
    background-color: var(--bs-secondary-bg);
}

.sidebar .nav-link.active {
    color: #fff;
    background-color: var(--bs-primary);
}

/* Typography & Custom card styles */
.fs-7 {
    font-size: 0.75rem;
}
.fs-8 {
    font-size: 0.65rem;
}
.tracking-wider {
    letter-spacing: 0.05em;
}

/* Dark Mode support details */
[data-bs-theme="dark"] .sidebar {
    box-shadow: inset -1px 0 0 rgba(255, 255, 255, .1);
}
```

```javascript
// File: static/js/main.js
// Main JavaScript file for common utilities
console.log("Rent Receipt Generator Initialized");
```

```html
// File: templates/base.html
<!DOCTYPE html>
<html lang="en" data-bs-theme="{% if theme == 'dark' %}dark{% elif theme == 'light' %}light{% else %}auto{% endif %}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Rent Receipt System{% endblock %}</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <!-- Custom CSS -->
    <link href="/static/css/style.css" rel="stylesheet">
    {% block head %}{% endblock %}
</head>
<body>

<div class="container-fluid">
    <div class="row">
        <!-- Sidebar -->
        <nav class="col-md-3 col-lg-2 d-md-block bg-body-tertiary sidebar collapse min-vh-100 border-end">
            <div class="position-sticky pt-3">
                <div class="px-3 mb-4 text-center">
                    <h5 class="fw-bold text-primary"><i class="bi bi-receipt-cutoff me-2"></i>RRG Suite</h5>
                    <hr>
                </div>
                <ul class="nav flex-column gap-2 px-2">
                    <li class="nav-item">
                        <a class="nav-link {% if request.url.path == '/' %}active{% endif %}" href="/">
                            <i class="bi bi-house-door me-2"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.url.path == '/billing' %}active{% endif %}" href="/billing">
                            <i class="bi bi-file-earmark-plus me-2"></i> New Receipt
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.url.path == '/tenants' %}active{% endif %}" href="/tenants">
                            <i class="bi bi-people me-2"></i> Tenants
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.url.path == '/history' %}active{% endif %}" href="/history">
                            <i class="bi bi-journal-text me-2"></i> Receipt History
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.url.path == '/settings' %}active{% endif %}" href="/settings">
                            <i class="bi bi-gear me-2"></i> Settings
                        </a>
                    </li>
                </ul>
                
                <!-- Theme Picker in Sidebar -->
                <div class="position-absolute bottom-0 start-0 w-100 p-3">
                    <hr>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary w-100 dropdown-toggle d-flex align-items-center justify-content-between" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <span>
                                <i class="bi bi-circle-half me-2"></i> Theme
                            </span>
                        </button>
                        <ul class="dropdown-menu w-100">
                            <li><button class="dropdown-item d-flex align-items-center" onclick="setTheme('light')"><i class="bi bi-sun-fill me-2"></i> Light</button></li>
                            <li><button class="dropdown-item d-flex align-items-center" onclick="setTheme('dark')"><i class="bi bi-moon-stars-fill me-2"></i> Dark</button></li>
                            <li><button class="dropdown-item d-flex align-items-center" onclick="setTheme('system')"><i class="bi bi-laptop me-2"></i> System</button></li>
                        </ul>
                    </div>
                </div>
            </div>
        </nav>

        <!-- Main Content -->
        <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4 py-4">
            {% block content %}{% endblock %}
        </main>
    </div>
</div>

<!-- Bootstrap 5 JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<!-- Theme Handler Script -->
<script>
    function applySystemTheme() {
        const theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-bs-theme', theme);
    }

    const currentTheme = "{{ theme }}";
    if (currentTheme === 'system') {
        applySystemTheme();
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applySystemTheme);
    }

    async function setTheme(themeName) {
        try {
            const res = await fetch("/api/ui/theme", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ theme: themeName })
            });
            if (res.ok) {
                window.location.reload();
            }
        } catch (e) {
            console.error("Failed to update theme preference", e);
        }
    }
</script>
{% block scripts %}{% endblock %}
</body>
</html>
```

```html
// File: templates/billing.html
{% extends "base.html" %}

{% block title %}New Receipt | Rent Receipt System{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-7 col-md-9 col-12">
        <div class="card shadow-sm border-0">
            <div class="card-header bg-primary text-white py-3">
                <h4 class="mb-0 fw-bold"><i class="bi bi-file-earmark-plus me-2"></i>New Receipt</h4>
            </div>
            <div class="card-body px-4 py-4">
                <form id="receiptForm">
                    <!-- Tenant Selection -->
                    <div class="mb-4">
                        <label class="form-label fw-semibold">Tenant Name</label>
                        <select class="form-select form-select-lg" id="tenant" required onchange="onTenantChange()">
                            <option value="">Select Tenant...</option>
                            {% for t in tenants %}
                            <option value="{{ t.name }}">{{ t.name }} {% if t.room_number %}(Room {{ t.room_number }}){% endif %}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <!-- Billing Month -->
                    <div class="mb-4">
                        <label class="form-label fw-semibold">Billing Month</label>
                        <select class="form-select form-select-lg" id="month" required>
                            <!-- Dynamically loaded from /api/billing/months -->
                        </select>
                    </div>

                    <hr class="my-4 text-muted">

                    <!-- Meter Readings -->
                    <h5 class="fw-bold mb-3">Electricity Readings</h5>
                    <div class="row g-3">
                        <div class="col-sm-6">
                            <label class="form-label">Current Meter Reading</label>
                            <input type="number" class="form-control form-control-lg" id="current_reading" step="0.1" placeholder="0.0" required oninput="calculateLiveTotal()">
                        </div>
                        <div class="col-sm-6">
                            <label class="form-label">Previous Meter Reading</label>
                            <input type="text" class="form-control form-control-lg bg-body-tertiary" id="prev_reading" value="{{ config.previous_meter_reading }}" readonly>
                        </div>
                    </div>
                    
                    <div class="mt-3">
                        <p class="text-muted mb-0">Consumed Units: <strong id="consumed_units_label" class="text-primary">0.0</strong></p>
                    </div>

                    <hr class="my-4 text-muted">

                    <!-- Fixed Charges info & Additional Persons -->
                    <h5 class="fw-bold mb-3">Other Charges</h5>
                    <div class="row g-3">
                        <div class="col-sm-4">
                            <label class="form-label">Monthly Rent (₹)</label>
                            <input type="text" class="form-control bg-body-tertiary" id="rent_val" value="{{ config.rent }}" readonly>
                        </div>
                        <div class="col-sm-4">
                            <label class="form-label">Water Charges (₹)</label>
                            <input type="text" class="form-control bg-body-tertiary" id="water_val" value="{{ config.water }}" readonly>
                        </div>
                        <div class="col-sm-4">
                            <label class="form-label">Additional Persons</label>
                            <input type="number" class="form-control" id="additional_persons" placeholder="Blank if none" min="0" oninput="calculateLiveTotal()">
                            <div class="form-text fs-8 text-muted">No additional person? Leave empty.</div>
                        </div>
                    </div>

                    <hr class="my-4 text-muted">

                    <!-- Rate Info -->
                    <div class="bg-body-tertiary p-3 rounded-2 mb-4 d-flex justify-content-between align-items-center">
                        <span class="fw-semibold">Electricity Rate:</span>
                        <span class="badge bg-warning text-dark fs-6">₹{{ config.electricity_rate }}/unit</span>
                    </div>

                    <!-- Live Total Details Area -->
                    <div class="border rounded-3 p-4 bg-light-subtle mb-4">
                        <h6 class="text-uppercase fw-bold text-muted mb-3 fs-7 tracking-wider">Live Breakdown</h6>
                        
                        <div class="d-flex justify-content-between mb-2">
                            <span>Rent:</span>
                            <span class="fw-bold">₹<span id="live_rent">0.00</span></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Water:</span>
                            <span class="fw-bold">₹<span id="live_water">0.00</span></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Additional:</span>
                            <span class="fw-bold">₹<span id="live_additional">0.00</span></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Electricity:</span>
                            <span class="fw-bold">₹<span id="live_electricity">0.00</span></span>
                        </div>
                        <hr>
                        <div class="d-flex justify-content-between align-items-center mb-0">
                            <span class="fs-5 fw-bold">TOTAL:</span>
                            <span class="fs-4 fw-bold text-success">₹<span id="live_total">0.00</span></span>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-success btn-lg w-100 py-3" id="submitBtn">
                        <i class="bi bi-file-pdf me-2"></i>Generate Receipt
                    </button>
                </form>
                
                <div class="alert alert-danger mt-4 d-none" id="errorAlert"></div>
                <div class="alert alert-success mt-4 d-none" id="successAlert"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const defaultRent = {{ config.rent }};
    const defaultWater = {{ config.water }};
    const prevMeterVal = {{ config.previous_meter_reading }};
    const electricityRate = {{ config.electricity_rate }};
    const additionalPersonCharge = {{ config.additional_person_charge }};

    document.addEventListener("DOMContentLoaded", function() {
        loadMonths();
        calculateLiveTotal();
    });

    async function loadMonths() {
        try {
            const res = await fetch("/api/billing/months");
            if (res.ok) {
                const data = await res.json();
                const select = document.getElementById("month");
                select.innerHTML = "";
                
                data.months.forEach(m => {
                    let option = document.createElement("option");
                    option.value = m;
                    option.text = m;
                    if (m === data.currentMonth) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error("Failed to load month list", e);
        }
    }

    function onTenantChange() {
        // Can be extended if custom rent/water is linked to specific tenants
    }

    function calculateLiveTotal() {
        const currentVal = parseFloat(document.getElementById("current_reading").value) || 0;
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        
        let consumed = Math.max(0, currentVal - prevMeterVal);
        let electricity = consumed * electricityRate;
        let additional = addPersons * additionalPersonCharge;
        let total = defaultRent + defaultWater + additional + electricity;
        
        // Update Labels
        document.getElementById("consumed_units_label").innerText = consumed.toFixed(1);
        document.getElementById("live_rent").innerText = defaultRent.toFixed(2);
        document.getElementById("live_water").innerText = defaultWater.toFixed(2);
        document.getElementById("live_additional").innerText = additional.toFixed(2);
        document.getElementById("live_electricity").innerText = electricity.toFixed(2);
        document.getElementById("live_total").innerText = total.toFixed(2);
    }

    document.getElementById("receiptForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        
        const tenant = document.getElementById("tenant").value;
        const month = document.getElementById("month").value;
        const currentVal = parseFloat(document.getElementById("current_reading").value);
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        
        const errorAlert = document.getElementById("errorAlert");
        const successAlert = document.getElementById("successAlert");
        
        errorAlert.classList.add("d-none");
        successAlert.classList.add("d-none");
        
        if (currentVal < prevMeterVal) {
            errorAlert.innerText = `Current meter reading (${currentVal}) cannot be less than the previous reading (${prevMeterVal}).`;
            errorAlert.classList.remove("d-none");
            return;
        }
        
        const submitBtn = document.getElementById("submitBtn");
        submitBtn.disabled = true;
        submitBtn.innerText = "Generating Receipt...";
        
        try {
            const res = await fetch("/api/bill", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tenant: tenant,
                    month: month,
                    current_reading: currentVal,
                    additional_persons: addPersons
                })
            });
            const result = await res.json();
            
            if (res.ok) {
                successAlert.innerHTML = `Receipt generated successfully! <a href="/api/pdf/${result.data.Bill}" target="_blank" class="alert-link">Download PDF</a>`;
                successAlert.classList.remove("d-none");
                
                // Reset inputs
                document.getElementById("current_reading").value = "";
                document.getElementById("additional_persons").value = "";
                
                // Automatically open PDF in a new tab
                window.open(`/api/pdf/${result.data.Bill}`, "_blank");
                
                // Auto reload config details in 1.5s
                setTimeout(() => window.location.reload(), 1500);
            } else {
                errorAlert.innerText = result.detail || "Failed to create receipt.";
                errorAlert.classList.remove("d-none");
                submitBtn.disabled = false;
                submitBtn.innerText = "Generate Receipt";
            }
        } catch(err) {
            errorAlert.innerText = "Connection error occurred.";
            errorAlert.classList.remove("d-none");
            submitBtn.disabled = false;
            submitBtn.innerText = "Generate Receipt";
        }
    });
</script>
{% endblock %}
```

```html
// File: templates/dashboard.html
{% extends "base.html" %}

{% block title %}Dashboard | Rent Receipt System{% endblock %}

{% block head %}
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Dashboard</h1>
</div>

<!-- Stats Cards -->
<div class="row row-cols-1 row-cols-md-3 row-cols-xl-6 g-3 mb-4">
    <div class="col">
        <div class="card h-100 border-start border-primary border-4 shadow-sm">
            <div class="card-body py-3">
                <h6 class="card-subtitle mb-1 text-muted text-uppercase fs-7">Next Bill</h6>
                <h3 class="card-title mb-0 fw-bold">{{ stats.next_bill }}</h3>
            </div>
        </div>
    </div>
    <div class="col">
        <div class="card h-100 border-start border-success border-4 shadow-sm">
            <div class="card-body py-3">
                <h6 class="card-subtitle mb-1 text-muted text-uppercase fs-7">Billing Month</h6>
                <h5 class="card-title mb-0 fw-bold" style="white-space: nowrap;">{{ stats.current_month }}</h5>
            </div>
        </div>
    </div>
    <div class="col">
        <div class="card h-100 border-start border-info border-4 shadow-sm">
            <div class="card-body py-3">
                <h6 class="card-subtitle mb-1 text-muted text-uppercase fs-7">Last Reading</h6>
                <h3 class="card-title mb-0 fw-bold">{{ stats.prev_reading }}</h3>
            </div>
        </div>
    </div>
    <div class="col">
        <div class="card h-100 border-start border-warning border-4 shadow-sm">
            <div class="card-body py-3">
                <h6 class="card-subtitle mb-1 text-muted text-uppercase fs-7">Total Tenants</h6>
                <h3 class="card-title mb-0 fw-bold">{{ stats.total_tenants }}</h3>
            </div>
        </div>
    </div>
    <div class="col">
        <div class="card h-100 border-start border-danger border-4 shadow-sm">
            <div class="card-body py-3">
                <h6 class="card-subtitle mb-1 text-muted text-uppercase fs-7">Receipts</h6>
                <h3 class="card-title mb-0 fw-bold">{{ stats.total_receipts }}</h3>
            </div>
        </div>
    </div>
    <div class="col">
        <div class="card h-100 border-start border-dark border-4 shadow-sm">
            <div class="card-body py-3">
                <h6 class="card-subtitle mb-1 text-muted text-uppercase fs-7">This Month Rev</h6>
                <h4 class="card-title mb-0 fw-bold text-success">₹{{ "{:,.2f}".format(stats.revenue_this_month) }}</h4>
            </div>
        </div>
    </div>
</div>

<div class="row g-4 mb-4">
    <!-- Chart: Monthly Revenue -->
    <div class="col-md-6">
        <div class="card shadow-sm h-100">
            <div class="card-header bg-transparent fw-bold"><i class="bi bi-graph-up-arrow me-2 text-success"></i>Monthly Revenue</div>
            <div class="card-body">
                <canvas id="revenueChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Chart: Electricity Consumption -->
    <div class="col-md-6">
        <div class="card shadow-sm h-100">
            <div class="card-header bg-transparent fw-bold"><i class="bi bi-lightning-charge-fill me-2 text-warning"></i>Electricity Consumption</div>
            <div class="card-body">
                <canvas id="electricityChart"></canvas>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <!-- Recent Bills -->
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header bg-transparent fw-bold"><i class="bi bi-list-stars me-2"></i>Recent Bills</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-striped table-hover mb-0 align-middle">
                        <thead>
                            <tr>
                                <th>Bill #</th>
                                <th>Tenant</th>
                                <th>Month</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for b in stats.recent_bills %}
                            <tr>
                                <td>{{ b.bill_no }}</td>
                                <td class="fw-bold">{{ b.tenant_name }}</td>
                                <td>{{ b.month }}</td>
                                <td class="text-success fw-bold">₹{{ b.total }}</td>
                            </tr>
                            {% endfor %}
                            {% if not stats.recent_bills %}
                            <tr>
                                <td colspan="4" class="text-center py-3">No bills generated yet.</td>
                            </tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Quick Actions -->
    <div class="col-md-4">
        <div class="card shadow-sm">
            <div class="card-header bg-transparent fw-bold"><i class="bi bi-lightning me-2 text-danger"></i>Quick Actions</div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="/billing" class="btn btn-outline-primary text-start py-2"><i class="bi bi-plus-circle me-2"></i> New Bill</a>
                    <a href="/tenants" class="btn btn-outline-success text-start py-2"><i class="bi bi-person-plus me-2"></i> Add Tenant</a>
                    <a href="/settings" class="btn btn-outline-secondary text-start py-2"><i class="bi bi-sliders me-2"></i> Settings</a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    // Config Chart.js color based on bootstrap theme
    const themeAttr = document.documentElement.getAttribute('data-bs-theme');
    const isDark = themeAttr === 'dark' || (themeAttr === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    const textColor = isDark ? '#adb5bd' : '#495057';
    const gridColor = isDark ? '#343a40' : '#dee2e6';

    const labels = {{ stats.chart_labels | tojson }};
    const revenueData = {{ stats.chart_revenue | tojson }};
    const electricityData = {{ stats.chart_electricity | tojson }};

    // Revenue Chart
    new Chart(document.getElementById('revenueChart'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue (₹)',
                data: revenueData,
                backgroundColor: 'rgba(25, 135, 84, 0.7)',
                borderColor: 'rgb(25, 135, 84)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                },
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                }
            },
            plugins: {
                legend: { labels: { color: textColor } }
            }
        }
    });

    // Electricity Chart
    new Chart(document.getElementById('electricityChart'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Electricity (Units)',
                data: electricityData,
                backgroundColor: 'rgba(255, 193, 7, 0.2)',
                borderColor: 'rgb(255, 193, 7)',
                borderWidth: 2,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                },
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                }
            },
            plugins: {
                legend: { labels: { color: textColor } }
            }
        }
    });
</script>
{% endblock %}
```

```html
// File: templates/edit_bill.html
{% extends "base.html" %}

{% block title %}Edit Receipt | Rent Receipt System{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-7 col-md-9 col-12">
        <div class="card shadow-sm border-0">
            <div class="card-header bg-warning text-dark py-3">
                <h4 class="mb-0 fw-bold"><i class="bi bi-pencil-square me-2"></i>Edit Receipt #{{ receipt.Bill }}</h4>
            </div>
            <div class="card-body px-4 py-4">
                <form id="receiptForm">
                    <!-- Tenant Selection -->
                    <div class="mb-4">
                        <label class="form-label fw-semibold">Tenant Name</label>
                        <select class="form-select form-select-lg" id="tenant" required>
                            {% for t in tenants %}
                            <option value="{{ t.name }}" {% if t.name == receipt.Tenant %}selected{% endif %}>{{ t.name }}</option>
                            {% endfor %}
                            <!-- In case tenant was deleted/renamed -->
                            {% if receipt.Tenant not in tenants|map(attribute='name') %}
                            <option value="{{ receipt.Tenant }}" selected>{{ receipt.Tenant }}</option>
                            {% endif %}
                        </select>
                    </div>

                    <!-- Billing Month -->
                    <div class="mb-4">
                        <label class="form-label fw-semibold">Billing Month</label>
                        <select class="form-select form-select-lg" id="month" required>
                            <option value="{{ receipt.Month }}" selected>{{ receipt.Month }}</option>
                            <!-- loaded dynamically by JS -->
                        </select>
                    </div>

                    <hr class="my-4 text-muted">

                    <!-- Meter Readings -->
                    <h5 class="fw-bold mb-3">Electricity Readings</h5>
                    <div class="row g-3">
                        <div class="col-sm-6">
                            <label class="form-label">Current Meter Reading</label>
                            <input type="number" class="form-control form-control-lg" id="current_reading" value="{{ receipt.Current }}" step="0.1" required oninput="calculateLiveTotal()">
                        </div>
                        <div class="col-sm-6">
                            <label class="form-label">Previous Meter Reading</label>
                            <input type="text" class="form-control form-control-lg bg-body-tertiary" id="prev_reading" value="{{ receipt.Previous }}" readonly>
                        </div>
                    </div>
                    
                    <div class="mt-3">
                        <p class="text-muted mb-0">Consumed Units: <strong id="consumed_units_label" class="text-primary">0.0</strong></p>
                    </div>

                    <hr class="my-4 text-muted">

                    <!-- Charges info & Additional Persons -->
                    <h5 class="fw-bold mb-3">Other Charges</h5>
                    <div class="row g-3">
                        <div class="col-sm-4">
                            <label class="form-label">Monthly Rent (₹)</label>
                            <input type="text" class="form-control bg-body-tertiary" id="rent_val" value="{{ config.rent }}" readonly>
                        </div>
                        <div class="col-sm-4">
                            <label class="form-label">Water Charges (₹)</label>
                            <input type="text" class="form-control bg-body-tertiary" id="water_val" value="{{ config.water }}" readonly>
                        </div>
                        <div class="col-sm-4">
                            <label class="form-label">Additional Persons</label>
                            {% set add_persons = (receipt.Additional|float / config.additional_person_charge|float)|int if config.additional_person_charge|float > 0 else 0 %}
                            <input type="number" class="form-control" id="additional_persons" value="{{ add_persons }}" min="0" oninput="calculateLiveTotal()">
                            <div class="form-text fs-8 text-muted">No additional person? Leave empty.</div>
                        </div>
                    </div>

                    <hr class="my-4 text-muted">

                    <!-- Rate Info -->
                    <div class="bg-body-tertiary p-3 rounded-2 mb-4 d-flex justify-content-between align-items-center">
                        <span class="fw-semibold">Electricity Rate:</span>
                        <span class="badge bg-warning text-dark fs-6">₹{{ config.electricity_rate }}/unit</span>
                    </div>

                    <!-- Live Total Details Area -->
                    <div class="border rounded-3 p-4 bg-light-subtle mb-4">
                        <h6 class="text-uppercase fw-bold text-muted mb-3 fs-7 tracking-wider">Live Breakdown</h6>
                        
                        <div class="d-flex justify-content-between mb-2">
                            <span>Rent:</span>
                            <span class="fw-bold">₹<span id="live_rent">0.00</span></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Water:</span>
                            <span class="fw-bold">₹<span id="live_water">0.00</span></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Additional:</span>
                            <span class="fw-bold">₹<span id="live_additional">0.00</span></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Electricity:</span>
                            <span class="fw-bold">₹<span id="live_electricity">0.00</span></span>
                        </div>
                        <hr>
                        <div class="d-flex justify-content-between align-items-center mb-0">
                            <span class="fs-5 fw-bold">TOTAL:</span>
                            <span class="fs-4 fw-bold text-success">₹<span id="live_total">0.00</span></span>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-warning btn-lg w-100 py-3" id="submitBtn">
                        <i class="bi bi-save me-2"></i>Update Receipt
                    </button>
                </form>
                
                <div class="alert alert-danger mt-4 d-none" id="errorAlert"></div>
                <div class="alert alert-success mt-4 d-none" id="successAlert"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const defaultRent = {{ config.rent }};
    const defaultWater = {{ config.water }};
    const prevMeterVal = {{ receipt.Previous }};
    const electricityRate = {{ config.electricity_rate }};
    const additionalPersonCharge = {{ config.additional_person_charge }};

    document.addEventListener("DOMContentLoaded", function() {
        loadMonths();
        calculateLiveTotal();
    });

    async function loadMonths() {
        try {
            const res = await fetch("/api/billing/months");
            if (res.ok) {
                const data = await res.json();
                const select = document.getElementById("month");
                
                data.months.forEach(m => {
                    if (m !== "{{ receipt.Month }}") {
                        let option = document.createElement("option");
                        option.value = m;
                        option.text = m;
                        select.appendChild(option);
                    }
                });
            }
        } catch (e) {
            console.error("Failed to load month list", e);
        }
    }

    function calculateLiveTotal() {
        const currentVal = parseFloat(document.getElementById("current_reading").value) || 0;
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        
        let consumed = Math.max(0, currentVal - prevMeterVal);
        let electricity = consumed * electricityRate;
        let additional = addPersons * additionalPersonCharge;
        let total = defaultRent + defaultWater + additional + electricity;
        
        // Update Labels
        document.getElementById("consumed_units_label").innerText = consumed.toFixed(1);
        document.getElementById("live_rent").innerText = defaultRent.toFixed(2);
        document.getElementById("live_water").innerText = defaultWater.toFixed(2);
        document.getElementById("live_additional").innerText = additional.toFixed(2);
        document.getElementById("live_electricity").innerText = electricity.toFixed(2);
        document.getElementById("live_total").innerText = total.toFixed(2);
    }

    document.getElementById("receiptForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        
        const tenant = document.getElementById("tenant").value;
        const month = document.getElementById("month").value;
        const currentVal = parseFloat(document.getElementById("current_reading").value);
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        
        const errorAlert = document.getElementById("errorAlert");
        const successAlert = document.getElementById("successAlert");
        
        errorAlert.classList.add("d-none");
        successAlert.classList.add("d-none");
        
        if (currentVal < prevMeterVal) {
            errorAlert.innerText = `Current meter reading (${currentVal}) cannot be less than the previous reading (${prevMeterVal}).`;
            errorAlert.classList.remove("d-none");
            return;
        }
        
        const submitBtn = document.getElementById("submitBtn");
        submitBtn.disabled = true;
        submitBtn.innerText = "Updating Receipt...";
        
        try {
            const res = await fetch("/api/edit_bill/{{ receipt.Bill }}", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tenant: tenant,
                    month: month,
                    current_reading: currentVal,
                    additional_persons: addPersons
                })
            });
            const result = await res.json();
            
            if (res.ok) {
                successAlert.innerHTML = `Receipt updated successfully! <a href="/api/pdf/{{ receipt.Bill }}" target="_blank" class="alert-link">Download PDF</a>`;
                successAlert.classList.remove("d-none");
                
                window.open(`/api/pdf/{{ receipt.Bill }}`, "_blank");
                
                setTimeout(() => window.location.href = "/history", 1500);
            } else {
                errorAlert.innerText = result.detail || "Failed to update receipt.";
                errorAlert.classList.remove("d-none");
                submitBtn.disabled = false;
                submitBtn.innerText = "Update Receipt";
            }
        } catch(err) {
            errorAlert.innerText = "Connection error occurred.";
            errorAlert.classList.remove("d-none");
            submitBtn.disabled = false;
            submitBtn.innerText = "Update Receipt";
        }
    });
</script>
{% endblock %}
```

```html
// File: templates/history.html
{% extends "base.html" %}

{% block title %}Receipt History | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Receipt History</h1>
</div>

<!-- Filters Panel -->
<div class="card shadow-sm mb-4">
    <div class="card-body">
        <div class="row g-3">
            <div class="col-md-3">
                <label class="form-label fw-semibold">Search Tenant</label>
                <input type="text" class="form-control" id="searchTenant" placeholder="Search by name..." onkeyup="applyFilters()">
            </div>
            <div class="col-md-3">
                <label class="form-label fw-semibold">Month</label>
                <select class="form-select" id="filterMonth" onchange="applyFilters()">
                    <option value="">All Months</option>
                    <!-- Populated dynamically -->
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label fw-semibold">Year</label>
                <select class="form-select" id="filterYear" onchange="applyFilters()">
                    <option value="">All Years</option>
                    <!-- Populated dynamically -->
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label fw-semibold">Tenant Filter</label>
                <select class="form-select" id="filterTenant" onchange="applyFilters()">
                    <option value="">All Tenants</option>
                    <!-- Populated dynamically -->
                </select>
            </div>
        </div>
    </div>
</div>

<!-- Receipts Table -->
<div class="card shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-striped table-hover mb-0 align-middle" id="receiptsTable">
                <thead class="table-dark">
                    <tr>
                        <th>Bill #</th>
                        <th>Date</th>
                        <th>Month</th>
                        <th>Tenant</th>
                        <th>Rent (₹)</th>
                        <th>Electricity (₹)</th>
                        <th>Total (₹)</th>
                        <th class="text-end px-4">Actions</th>
                    </tr>
                </thead>
                <tbody id="receiptsTableBody">
                    {% for r in receipts %}
                    <tr data-tenant="{{ r.Tenant }}" data-month="{{ r.Month }}" data-bill="{{ r.Bill }}">
                        <td>{{ r.Bill }}</td>
                        <td>{{ r.Date }}</td>
                        <td>{{ r.Month }}</td>
                        <td class="fw-bold">{{ r.Tenant }}</td>
                        <td>₹{{ "{:,.2f}".format(r.Rent|float) }}</td>
                        <td>₹{{ "{:,.2f}".format(r.Electricity|float) }}</td>
                        <td class="fw-bold text-success">₹{{ "{:,.2f}".format(r.Total|float) }}</td>
                        <td class="text-end px-4">
                            <div class="btn-group gap-1">
                                <a href="/api/pdf/{{ r.Bill }}" target="_blank" class="btn btn-sm btn-outline-info" title="View PDF"><i class="bi bi-eye"></i> View</a>
                                <a href="/edit_bill/{{ r.Bill }}" class="btn btn-sm btn-outline-warning" title="Edit Bill"><i class="bi bi-pencil"></i> Edit</a>
                                <a href="/api/pdf/{{ r.Bill }}" download class="btn btn-sm btn-outline-primary" title="Download PDF"><i class="bi bi-file-pdf"></i> PDF</a>
                                <button onclick="deleteBill('{{ r.Bill }}')" class="btn btn-sm btn-outline-danger" title="Delete Bill"><i class="bi bi-trash"></i> Delete</button>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                    {% if not receipts %}
                    <tr id="noDataRow">
                        <td colspan="8" class="text-center py-4">No receipts generated yet.</td>
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
    document.addEventListener("DOMContentLoaded", function() {
        populateFilterOptions();
    });

    function populateFilterOptions() {
        const rows = document.querySelectorAll("#receiptsTableBody tr:not(#noDataRow)");
        const months = new Set();
        const years = new Set();
        const tenants = new Set();

        rows.forEach(row => {
            const monthYear = row.getAttribute("data-month");
            const tenant = row.getAttribute("data-tenant");
            
            if (monthYear) {
                const parts = monthYear.split(" ");
                if (parts.length === 2) {
                    months.add(parts[0]);
                    years.add(parts[1]);
                }
            }
            if (tenant) {
                tenants.add(tenant);
            }
        });

        // Populate Month Dropdown
        const monthSelect = document.getElementById("filterMonth");
        months.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.innerText = m;
            monthSelect.appendChild(opt);
        });

        // Populate Year Dropdown
        const yearSelect = document.getElementById("filterYear");
        years.forEach(y => {
            const opt = document.createElement("option");
            opt.value = y;
            opt.innerText = y;
            yearSelect.appendChild(opt);
        });

        // Populate Tenant Dropdown
        const tenantSelect = document.getElementById("filterTenant");
        tenants.forEach(t => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.innerText = t;
            tenantSelect.appendChild(opt);
        });
    }

    function applyFilters() {
        const searchVal = document.getElementById("searchTenant").value.toLowerCase();
        const selectedMonth = document.getElementById("filterMonth").value;
        const selectedYear = document.getElementById("filterYear").value;
        const selectedTenant = document.getElementById("filterTenant").value;

        const rows = document.querySelectorAll("#receiptsTableBody tr:not(#noDataRow)");
        let visibleCount = 0;

        rows.forEach(row => {
            const tenant = row.getAttribute("data-tenant") || "";
            const monthYearStr = row.getAttribute("data-month") || "";
            
            let parts = monthYearStr.split(" ");
            let month = parts[0] || "";
            let year = parts[1] || "";
            
            let matchesSearch = tenant.toLowerCase().includes(searchVal);
            let matchesMonth = !selectedMonth || month === selectedMonth;
            let matchesYear = !selectedYear || year === selectedYear;
            let matchesTenant = !selectedTenant || tenant === selectedTenant;

            if (matchesSearch && matchesMonth && matchesYear && matchesTenant) {
                row.style.display = "";
                visibleCount++;
            } else {
                row.style.display = "none";
            }
        });

        // Show/hide empty state
        const noDataRow = document.getElementById("noDataRow");
        if (noDataRow) {
            if (visibleCount === 0 && rows.length > 0) {
                noDataRow.style.display = "";
            } else {
                noDataRow.style.display = "none";
            }
        }
    }

    async function deleteBill(billNo) {
        if (!confirm(`Are you sure you want to delete Bill #${billNo}? This action is irreversible.`)) {
            return;
        }

        try {
            const res = await fetch(`/api/bill/${billNo}`, {
                method: "DELETE"
            });
            if (res.ok) {
                window.location.reload();
            } else {
                alert("Failed to delete the bill.");
            }
        } catch(e) {
            alert("Network error occurred.");
        }
    }
</script>
{% endblock %}
```

```html
// File: templates/index.html
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
// File: templates/settings.html
{% extends "base.html" %}

{% block title %}Settings | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Settings</h1>
</div>

<div class="row g-4">
    <!-- Landlord Configuration -->
    <div class="col-lg-6">
        <div class="card shadow-sm border-0 h-100">
            <div class="card-header bg-secondary text-white py-3">
                <h5 class="mb-0 fw-bold"><i class="bi bi-person-gear me-2"></i>Landlord Details</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label fw-semibold">Landlord Name</label>
                    <input type="text" class="form-control" id="landlord_name" value="{{ landlord_config.name }}">
                </div>
                <div class="mb-3">
                    <label class="form-label fw-semibold">Phone Number</label>
                    <input type="text" class="form-control" id="landlord_phone" value="{{ landlord_config.phone }}">
                </div>
                <div class="mb-3">
                    <label class="form-label fw-semibold">Email Address</label>
                    <input type="email" class="form-control" id="landlord_email" value="{{ landlord_config.email }}">
                </div>
                <div class="mb-3">
                    <label class="form-label fw-semibold">Address Details</label>
                    <textarea class="form-control" id="landlord_address" rows="3">{{ landlord_config.address }}</textarea>
                </div>
            </div>
        </div>
    </div>

    <!-- Billing Parameters Configuration -->
    <div class="col-lg-6">
        <div class="card shadow-sm border-0 h-100">
            <div class="card-header bg-primary text-white py-3">
                <h5 class="mb-0 fw-bold"><i class="bi bi-wallet2 me-2"></i>Default Rates & billing</h5>
            </div>
            <div class="card-body">
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Monthly Rent (₹)</label>
                        <input type="number" class="form-control" id="default_rent" value="{{ billing_config.rent }}" step="0.01">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Water Charges (₹)</label>
                        <input type="number" class="form-control" id="water_charge" value="{{ billing_config.water }}" step="0.01">
                    </div>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Electricity Rate (₹/unit)</label>
                        <input type="number" class="form-control" id="electricity_rate" value="{{ billing_config.electricity_rate }}" step="0.01">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Additional Person (₹)</label>
                        <input type="number" class="form-control" id="add_person_charge" value="{{ billing_config.additional_person_charge }}" step="0.01">
                    </div>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Current Meter Reading</label>
                        <input type="number" class="form-control" id="prev_reading" value="{{ billing_config.previous_meter_reading }}" step="0.1">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Next Bill Number</label>
                        <input type="number" class="form-control" id="next_bill_no" value="{{ billing_config.next_bill_number }}" step="1">
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-12 text-end">
        <button onclick="saveAllSettings()" class="btn btn-success btn-lg px-5 py-2 shadow-sm" id="saveAllBtn">
            <i class="bi bi-save me-2"></i>Save All Settings
        </button>
        <div class="alert alert-success text-start mt-3 d-none" id="successAlert">Settings saved successfully!</div>
        <div class="alert alert-danger text-start mt-3 d-none" id="errorAlert"></div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    async function saveAllSettings() {
        const btn = document.getElementById("saveAllBtn");
        const successAlert = document.getElementById("successAlert");
        const errorAlert = document.getElementById("errorAlert");
        
        btn.disabled = true;
        successAlert.classList.add("d-none");
        errorAlert.classList.add("d-none");

        const data = {
            landlord: {
                name: document.getElementById("landlord_name").value,
                phone: document.getElementById("landlord_phone").value,
                email: document.getElementById("landlord_email").value,
                address: document.getElementById("landlord_address").value
            },
            billing: {
                rent: parseFloat(document.getElementById("default_rent").value) || 0,
                water: parseFloat(document.getElementById("water_charge").value) || 0,
                electricity_rate: parseFloat(document.getElementById("electricity_rate").value) || 0,
                additional_person_charge: parseFloat(document.getElementById("add_person_charge").value) || 0,
                previous_meter_reading: parseFloat(document.getElementById("prev_reading").value) || 0,
                next_bill_number: parseInt(document.getElementById("next_bill_no").value) || 1
            }
        };

        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                successAlert.classList.remove("d-none");
                setTimeout(() => successAlert.classList.add("d-none"), 3000);
            } else {
                errorAlert.innerText = "Failed to update configuration settings.";
                errorAlert.classList.remove("d-none");
            }
        } catch(e) {
            errorAlert.innerText = "Network error occurred.";
            errorAlert.classList.remove("d-none");
        } finally {
            btn.disabled = false;
        }
    }
</script>
{% endblock %}
```

```html
// File: templates/tenants.html
{% extends "base.html" %}

{% block title %}Tenants Management | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Tenants Management</h1>
</div>

<div class="row">
    <!-- Add/Edit Tenant Card -->
    <div class="col-xl-4 col-lg-5 mb-4">
        <div class="card shadow-sm border-0">
            <div class="card-header bg-primary text-white py-3">
                <h5 class="mb-0 fw-bold" id="formTitle"><i class="bi bi-person-plus me-2"></i>Add Tenant</h5>
            </div>
            <div class="card-body">
                <form id="tenantForm">
                    <input type="hidden" id="tenant_id">
                    
                    <div class="mb-3">
                        <label class="form-label">Tenant Name *</label>
                        <input type="text" class="form-control" id="name" required>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Company Name</label>
                        <input type="text" class="form-control" id="company">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Phone Number</label>
                        <input type="text" class="form-control" id="phone">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control" id="email">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Permanent Address</label>
                        <textarea class="form-control" id="address" rows="2"></textarea>
                    </div>

                    <div class="row g-2 mb-3">
                        <div class="col-sm-6">
                            <label class="form-label">Room/Unit Number</label>
                            <input type="text" class="form-control" id="room_number">
                        </div>
                        <div class="col-sm-6">
                            <label class="form-label">Occupation</label>
                            <input type="text" class="form-control" id="occupation">
                        </div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Status</label>
                        <select class="form-select" id="status">
                            <option value="Active">Active</option>
                            <option value="Inactive">Inactive</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Notes</label>
                        <textarea class="form-control" id="notes" rows="2"></textarea>
                    </div>

                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-success w-100" id="saveBtn">Save Tenant</button>
                        <button type="button" class="btn btn-outline-secondary d-none" id="cancelBtn" onclick="resetForm()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Tenants List -->
    <div class="col-xl-8 col-lg-7">
        <div class="card shadow-sm border-0">
            <div class="card-header bg-transparent py-3">
                <h5 class="mb-0 fw-bold"><i class="bi bi-people-fill me-2"></i>Tenants Directory</h5>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-striped table-hover mb-0 align-middle">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Room</th>
                                <th>Phone</th>
                                <th>Status</th>
                                <th class="text-end px-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for t in tenants %}
                            <tr>
                                <td>
                                    <div class="fw-bold">{{ t.name }}</div>
                                    {% if t.company %}<small class="text-muted">{{ t.company }}</small>{% endif %}
                                </td>
                                <td>
                                    {% if t.room_number %}
                                    <span class="badge bg-secondary">Room {{ t.room_number }}</span>
                                    {% else %}
                                    -
                                    {% endif %}
                                </td>
                                <td>{{ t.phone or '-' }}</td>
                                <td>
                                    {% if t.status == 'Active' %}
                                    <span class="badge bg-success">Active</span>
                                    {% else %}
                                    <span class="badge bg-danger">Inactive</span>
                                    {% endif %}
                                </td>
                                <td class="text-end px-4">
                                    <div class="btn-group gap-1">
                                        <button class="btn btn-sm btn-outline-primary" onclick='editTenant({{ t.dict() | tojson }})'><i class="bi bi-pencil"></i> Edit</button>
                                        <button class="btn btn-sm btn-outline-danger" onclick="deleteTenant({{ t.id }})"><i class="bi bi-trash"></i> Delete</button>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                            {% if not tenants %}
                            <tr>
                                <td colspan="5" class="text-center py-4">No tenants registered yet.</td>
                            </tr>
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
        
        const id = document.getElementById("tenant_id").value;
        const tenantData = {
            name: document.getElementById("name").value,
            company: document.getElementById("company").value,
            phone: document.getElementById("phone").value,
            email: document.getElementById("email").value,
            address: document.getElementById("address").value,
            room_number: document.getElementById("room_number").value,
            occupation: document.getElementById("occupation").value,
            status: document.getElementById("status").value,
            notes: document.getElementById("notes").value
        };
        
        const isEdit = !!id;
        const url = isEdit ? `/api/tenants/${id}` : "/api/tenants";
        const method = isEdit ? "PUT" : "POST";
        
        const saveBtn = document.getElementById("saveBtn");
        saveBtn.disabled = true;
        
        try {
            const res = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(tenantData)
            });
            if (res.ok) {
                window.location.reload();
            } else {
                alert("Failed to save tenant.");
                saveBtn.disabled = false;
            }
        } catch (e) {
            alert("Network error occurred.");
            saveBtn.disabled = false;
        }
    });

    function editTenant(tenant) {
        document.getElementById("tenant_id").value = tenant.id;
        document.getElementById("name").value = tenant.name || '';
        document.getElementById("company").value = tenant.company || '';
        document.getElementById("phone").value = tenant.phone || '';
        document.getElementById("email").value = tenant.email || '';
        document.getElementById("address").value = tenant.address || '';
        document.getElementById("room_number").value = tenant.room_number || '';
        document.getElementById("occupation").value = tenant.occupation || '';
        document.getElementById("status").value = tenant.status || 'Active';
        document.getElementById("notes").value = tenant.notes || '';
        
        document.getElementById("formTitle").innerHTML = `<i class="bi bi-pencil-square me-2"></i>Edit Tenant`;
        document.getElementById("cancelBtn").classList.remove("d-none");
    }

    function resetForm() {
        document.getElementById("tenant_id").value = '';
        document.getElementById("tenantForm").reset();
        document.getElementById("formTitle").innerHTML = `<i class="bi bi-person-plus me-2"></i>Add Tenant`;
        document.getElementById("cancelBtn").classList.add("d-none");
    }

    async function deleteTenant(id) {
        if (!confirm("Are you sure you want to delete this tenant? All history will remain intact, but they won't appear in active bill lists.")) {
            return;
        }
        
        try {
            const res = await fetch(`/api/tenants/${id}`, { method: "DELETE" });
            if (res.ok) {
                window.location.reload();
            } else {
                alert("Failed to delete tenant.");
            }
        } catch(e) {
            alert("Network error occurred.");
        }
    }
</script>
{% endblock %}
```
