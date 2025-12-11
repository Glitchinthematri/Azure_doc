from llm_response import get_response
# Assuming azure_di is a local file with the get_layout_as_markdown function
from azure_di import get_layout_as_markdown
import os
from pathlib import Path
import random
import json
import csv
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

# --- Configuration ---
LOG_FILE_PATH = Path("agent_outputs") / "processing_log.txt"
# Ensure the output folder is created right away
os.makedirs(Path("agent_outputs"), exist_ok=True)


# --- FileLogger Class (Fixed for UTF-8 Encoding) ---
class FileLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        # FIX 1: Open the log file with UTF-8 encoding to prevent UnicodeEncodeError
        self.log = open(filename, 'a', encoding='utf-8') 

    def write(self, message):
        self.terminal.write(message)
        # FIX 2: Correctly write to the opened log file and flush immediately
        self.log.write(message) 
        self.log.flush() 

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Overwrite the system standard output for all print statements
sys.stdout = FileLogger(LOG_FILE_PATH)
# --- END of Log Redirection Code ---
    
    csv_path = os.path.join(output_folder, csv_filename)
    
    fieldnames = [
        'file_name', 
        'total_amount_before_tax', 
        'total_amount_after_tax',
        'calculated_items_sum',
        'internal_check_passed'
    ]

    csv_row = {
        'file_name': data_dict.get('file_name', 'N/A'),
        'total_amount_before_tax': data_dict.get('total_amount_before_tax', 'N/A'),
        'total_amount_after_tax': data_dict.get('total_amount_after_tax', 'N/A'),
        'calculated_items_sum': data_dict.get('calculated_items_sum', 0.0),
        'internal_check_passed': data_dict.get('internal_check_passed', False)
    }

    try:
        file_exists = os.path.exists(csv_path)
        
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()
            
            writer.writerow(csv_row)
            
        print(f"✅ Data successfully appended to {csv_filename}")

    except Exception as e:
        print(f"❌ ERROR writing CSV data: {e}")


# ==============================================================================
# 2. MAIN AGENT FUNCTION
# (No changes here, remains the same)
# ==============================================================================

def agent(file_path):
    
    # --------------------------------------------------------------------------
    # --- IMPORTANT: We check for a valid file path before proceeding! ---
    # The watchdog observer can sometimes pick up temporary files.
    # --------------------------------------------------------------------------
    if not Path(file_path).is_file() or Path(file_path).name.startswith('~'):
        return # Exit the function if it's not a real file
        
    print("="*60)
    print(f"🚀 Starting agent for file: {Path(file_path).name}")
    
<<<<<<< HEAD
=======
    # 1. Get OCR Data
>>>>>>> task2
    ocr_output = get_layout_as_markdown(file_path)

    # 2. Define the strict JSON prompt
    prompt = f"""
# Role: 
    you are an assistant working in the finance department
# Context:
    you are given the ocr response from a receipt: {ocr_output}
# Task:
your job is to identify all the items mentioned in the receipt and their amounts and the total amount

# Output format:
**STRICTLY** output only a single, valid JSON object. Do not include any text, notes, or markdown formatting (like ```json) outside of the JSON object itself.
The JSON object must have the following fields: 
total_amount_before_tax (float), 
total_amount_after_tax (float), 
items (list of dicts).
items must be a list of dicts with fields: item_name (string), item_amount (float).
"""

    # 3. Get LLM Response
    response = get_response(prompt)

    # --- Initialization ---
    validated_data = None 
    
    # --- JSON Validation, CALCULATION, and Cleaning ---
    try:
        # Tries to load the response as a JSON dictionary
        data_dict = json.loads(response)
        
        # Check for errors returned by llm_response.py
        if data_dict.get('error'):
            raise Exception(f"LLM API Error: {data_dict['error']}")
        
        # Add internal fields
        data_dict['file_name'] = Path(file_path).name 
        
        # Sum up item amounts and compare to total_amount_before_tax
        calculated_sum = 0.0
        target_before_tax = float(data_dict.get('total_amount_before_tax', 0.0))
        
        for item in data_dict.get('items', []):
            try:
                calculated_sum += float(item.get('item_amount', 0.0))
            except ValueError:
                print(f"⚠️ Non-numeric amount found for item: {item.get('item_name')}. Skipping sum check.")
        
        # Set internal check status
        check_passed = (round(calculated_sum, 2) == round(target_before_tax, 2))
        data_dict['internal_check_passed'] = check_passed
        data_dict['calculated_items_sum'] = round(calculated_sum, 2)
        
        print(f"💰 Internal Check: Sum ({round(calculated_sum, 2)}) == Target ({round(target_before_tax, 2)})? -> {check_passed}")

        validated_data = data_dict
        print("✅ Response validated, checked, and cleaned.")
        
    except json.JSONDecodeError as e:
        print(f"❌ WARNING: Failed to decode response as JSON. Error: {e}")
        validated_data = {
            'file_name': Path(file_path).name,
            'total_amount_before_tax': 'JSON_FAIL',
            'total_amount_after_tax': 'JSON_FAIL',
            'internal_check_passed': False,
            'raw_response': response.strip()
        }
    except Exception as e:
         print(f"❌ WARNING: An error occurred during processing: {e}")
         validated_data = {
            'file_name': Path(file_path).name,
            'total_amount_before_tax': 'PROCESS_FAIL',
            'total_amount_after_tax': 'PROCESS_FAIL',
            'internal_check_passed': False,
            'error_details': str(e)
        }


    # --- File Saving Logic (.JSON) ---
    output_folder = "agent_outputs"
    file_name_only = Path(file_path).stem 
    json_save_path = os.path.join(output_folder, f"{file_name_only}.json")

    if validated_data:
        try:
            # Save the structured data as a .JSON file (which the UI now reads)
            with open(json_save_path, "w", encoding="utf-8") as json_file:
                json.dump(validated_data, json_file, indent=4) 
            print(f"✅ Successfully saved structured JSON data to: {json_save_path}")
        except Exception as e:
            print(f"❌ Error saving JSON file {json_save_path}: {e}")
            
    

# ==============================================================================
# 3. MAIN EXECUTION BLOCK (Watchdog Monitoring)
# ==============================================================================

# 1. Define the handler class that watches for new files
class NewFileHandler(FileSystemEventHandler):
    
    # We use on_modified for reliable file drop detection
    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.jpg'):
            # Pause to ensure the file is completely written before reading
            time.sleep(0.5) 
            agent(event.src_path)

if __name__ == "__main__":
    
    image_directory = "img" 
    os.makedirs(image_directory, exist_ok=True)
    
    print(f"⭐ Starting real-time file monitor on folder: {image_directory}...")
    print("⭐ Press Ctrl+C to stop monitoring.")

    # Set up the watchdog observer
    path = image_directory
    event_handler = NewFileHandler()
    observer = Observer()
    
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nMonitor stopped by user.")
        
    observer.join()