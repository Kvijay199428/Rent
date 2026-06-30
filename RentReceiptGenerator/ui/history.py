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
