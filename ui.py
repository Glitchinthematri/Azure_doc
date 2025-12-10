import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog
import os
import shutil
# import csv # No longer needed, as we read JSON directly
import json  # NEW: Needed for reading the structured output
from pathlib import Path
from PIL import Image  # Requires pip install pillow if not present, but usually standard
import time # Needed for checking file modification time

# --- Configuration ---
IMG_FOLDER = "img"
OUTPUT_FOLDER = "agent_outputs"
# CSV_FILE is removed, as we now monitor the whole folder for JSON files.
LOG_FILE = os.path.join(OUTPUT_FOLDER, "processing_log.txt")

ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class InvoiceDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Finance AI Agent - Dashboard")
        self.geometry("1100x700")

        # Layout Configuration (Grid)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- NEW: State Tracking for Refresh ---
        self.last_log_size = 0
        self.last_json_count = 0  # We track file count instead of mod time
        
        # --- 1. Sidebar (Navigation) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🧾 Finance Agent", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)

        self.btn_data = ctk.CTkButton(self.sidebar_frame, text="Live Data", command=self.show_data)
        self.btn_data.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_logs = ctk.CTkButton(self.sidebar_frame, text="System Logs", command=self.show_logs)
        self.btn_logs.grid(row=3, column=0, padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: ● Active", text_color="#00FF00", font=("Arial", 12))
        self.status_label.grid(row=5, column=0, padx=20, pady=20)

        # --- 2. Main Frames (Pages) ---
        
        # A. Dashboard Frame (Upload & Stats)
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.dashboard_frame.grid_columnconfigure(0, weight=1)
        
        # Upload Section
        self.upload_card = ctk.CTkFrame(self.dashboard_frame, corner_radius=15)
        self.upload_card.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.lbl_upload = ctk.CTkLabel(self.upload_card, text="Process New Invoice", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_upload.pack(pady=(20, 10))
        
        self.btn_upload = ctk.CTkButton(self.upload_card, text="📂 Upload File", height=50, width=200, 
                                      font=ctk.CTkFont(size=16), fg_color="#2CC985", hover_color="#229A65",
                                      command=self.upload_file)
        self.btn_upload.pack(pady=20)
        
        self.lbl_hint = ctk.CTkLabel(self.upload_card, text="Supports .jpg (Auto-processed via Watchdog)", text_color="gray")
        self.lbl_hint.pack(pady=(0, 20))

        # Stats Section
        self.stats_frame = ctk.CTkFrame(self.dashboard_frame, corner_radius=15)
        self.stats_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.lbl_stats_title = ctk.CTkLabel(self.stats_frame, text="Session Statistics", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_stats_title.pack(pady=10)
        self.lbl_total_processed = ctk.CTkLabel(self.stats_frame, text="Invoices Processed: 0", font=("Arial", 24))
        self.lbl_total_processed.pack(pady=20)

        # B. Data Frame (Live Table)
        self.data_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_table()

        # C. Log Frame (Console Output)
        self.log_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.log_box = ctk.CTkTextbox(self.log_frame, width=800, height=600, font=("Consolas", 12))
        self.log_box.pack(padx=20, pady=20, fill="both", expand=True)

        # Start on Dashboard
        self.show_dashboard()
        
        # Start Auto-Refresh Loop
        self.after(1000, self.refresh_data)

    # --- Setup Methods ---
    def setup_table(self):
        # We use a standard Tkinter Treeview because it handles tables better, but we style it
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#2a2d2e", 
                        foreground="white", 
                        rowheight=25, 
                        fieldbackground="#343638", 
                        bordercolor="#343638", 
                        borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#3484F0')])

        columns = ("file", "total_pre_tax", "total_post_tax", "check_passed")
        self.tree = ttk.Treeview(self.data_frame, columns=columns, show="headings", height=20)
        
        self.tree.heading("file", text="File Name")
        self.tree.heading("total_pre_tax", text="Before Tax")
        self.tree.heading("total_post_tax", text="After Tax")
        self.tree.heading("check_passed", text="Math Check")
        
        self.tree.column("file", width=200)
        self.tree.column("total_pre_tax", width=100)
        self.tree.column("total_post_tax", width=100)
        self.tree.column("check_passed", width=100)
        
        self.tree.pack(padx=20, pady=20, fill="both", expand=True)

    # --- Navigation Methods ---
    def show_dashboard(self):
        self.hide_all_frames()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")

    def show_data(self):
        self.hide_all_frames()
        self.data_frame.grid(row=0, column=1, sticky="nsew")
        self.load_json_data() # <-- RENAMED: Load data from JSON files

    def show_logs(self):
        self.hide_all_frames()
        self.log_frame.grid(row=0, column=1, sticky="nsew")

    def hide_all_frames(self):
        self.dashboard_frame.grid_forget()
        self.data_frame.grid_forget()
        self.log_frame.grid_forget()

    # --- Action Methods ---
    def upload_file(self):
        file_path = filedialog.askopenfilename(title="Select Invoice", filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if file_path:
            try:
                file_name = Path(file_path).name
                destination = Path(IMG_FOLDER) / file_name
                shutil.copy(file_path, destination)
                self.log_box.insert("end", f"🚀 Uploaded: {file_name}\n")
                # Switch to logs to show activity
                self.show_logs() 
            except Exception as e:
                self.log_box.insert("end", f"❌ Error: {e}\n")

    # --- NEW METHOD: Loads data from all JSON files ---
    def load_json_data(self):
        # Clears table
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Find all JSON files in the output folder
        try:
            json_files = list(Path(OUTPUT_FOLDER).glob("*.json"))
        except FileNotFoundError:
            # This happens if agent_outputs folder doesn't exist yet
            json_files = [] 
        
        count = 0
        
        for json_file_path in json_files:
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if isinstance(data, dict):
                        count += 1
                        # Insert row into table using data read from JSON
                        self.tree.insert("", "end", values=(
                            data.get('file_name', json_file_path.name),
                            data.get('total_amount_before_tax', 'N/A'),
                            data.get('total_amount_after_tax', 'N/A'),
                            data.get('internal_check_passed', 'FAIL')
                        ))
                    
            except json.JSONDecodeError:
                # Log the error but continue processing other files
                print(f"Error: Skipped invalid JSON file: {json_file_path.name}")
            except Exception as e:
                print(f"Error reading file {json_file_path.name}: {e}")

        self.lbl_total_processed.configure(text=f"Invoices Processed: {count}")


    # --- Auto-Refresh Loop ---
    def refresh_data(self):
        # 1. Update Logs (Refined for robustness)
        if os.path.exists(LOG_FILE):
            try:
                current_size = os.stat(LOG_FILE).st_size
                if current_size > self.last_log_size:
                    # CRITICAL FIX: Ensure file is read with UTF-8 encoding
                    with open(LOG_FILE, 'r', encoding='utf-8') as f:
                        f.seek(self.last_log_size)
                        new_text = f.read()
                        self.log_box.insert("end", new_text)
                        self.log_box.see("end")
                    self.last_log_size = current_size
            except Exception as e:
                # Fail silently in the loop if the log file is being written to
                pass 

        # 2. Update JSON Data (Check file count)
        try:
            current_json_files = list(Path(OUTPUT_FOLDER).glob("*.json"))
            current_json_count = len(current_json_files)
            
            # Reload data if a new JSON file has appeared
            if current_json_count > self.last_json_count:
                self.load_json_data()
                self.last_json_count = current_json_count
        except Exception:
            # Ignore errors if the output folder path is temporarily unavailable
            pass


        self.after(2000, self.refresh_data) # Check again in 2 seconds

if __name__ == "__main__":
    # Ensure folders exist
    os.makedirs(IMG_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    app = InvoiceDashboard()
    app.mainloop()