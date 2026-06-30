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
