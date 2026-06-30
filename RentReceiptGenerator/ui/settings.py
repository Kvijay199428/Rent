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
