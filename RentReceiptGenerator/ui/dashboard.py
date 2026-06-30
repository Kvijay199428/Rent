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
