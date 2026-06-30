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
