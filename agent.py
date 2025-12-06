from llm_response import get_response
from azure_di import get_layout_as_markdown
import os
from pathlib import Path
import random
import json
import csv
import time # Needed for the while loop pause
from watchdog.observers import Observer # New monitoring tool
from watchdog.events import FileSystemEventHandler # New event handler tool


# ==============================================================================
# 1. HELPER FUNCTION: CSV EXPORT
# (No changes here, remains the same)
# ==============================================================================

def save_to_csv(data_dict, output_folder="agent_outputs", csv_filename="master_invoice_data.csv"):
    """Flattens the data dictionary and appends it to a master CSV file."""
    
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
    
    ocr_output = get_layout_as_markdown(file_path)

    prompt = f"""
# Role: 
    you are an assistant working in the finance department
# Context:
    you are given the ocr response from a receipt: {ocr_output}
# Task:
your job is to identify all the items mentioned in the receipt and their amounts and the total amount

# Output format:
your output should be a json dict with fields: total_amount_before_tax, total_amount_after_tax, items
items will be a list of dicts with fields: item_name, item_amount
MAKE SURE YOUR IS A VALID DICTIONARY
"""
    # print("="*40); print(prompt); print("="*40) # Commented out for cleaner output

    response = get_response(prompt)
    # print("Agent Response (Raw):", response) # Commented out for cleaner output

    # --- Initialization before TRY/EXCEPT ---
    final_output = response 
    data_dict = {} 
    check_passed = False 
    calculated_sum = 0.0
    target_before_tax = 0.0

    # --- JSON Validation, CALCULATION, and Cleaning ---
    try:
        data_dict = json.loads(response)
        
        data_dict['file_name'] = Path(file_path).name 
        
        # 1. Sum up the item amounts
        for item in data_dict.get('items', []):
            try:
                amount = float(item.get('item_amount', 0.0))
                calculated_sum += amount
            except ValueError:
                print(f"⚠️ Non-numeric amount found for item: {item.get('item_name')}. Skipping from sum check.")
        
        # 2. Get the target amount
        try:
            target_before_tax = float(data_dict.get('total_amount_before_tax', 0.0))
        except ValueError:
            target_before_tax = 0.0
            print("❌ total_amount_before_tax is missing or not a valid number.")
            
        # 3. Compare and set status
        check_passed = (round(calculated_sum, 2) == round(target_before_tax, 2))
        data_dict['internal_check_passed'] = check_passed
        data_dict['calculated_items_sum'] = round(calculated_sum, 2)
        
        print(f"💰 Internal Check: Items sum ({round(calculated_sum, 2)}) == Before Tax ({round(target_before_tax, 2)})? -> {check_passed}")

        final_output = json.dumps(data_dict, indent=4)
        print("✅ Response validated, checked, and cleaned.")
        
        # 6. EXPORT VALIDATED DATA TO CSV (Success)
        save_to_csv(data_dict) 
        
    except json.JSONDecodeError as e:
        print(f"❌ WARNING: Failed to decode response as JSON. Error: {e}")
        
        # Create a simple data_dict with failure status for logging
        safe_data_dict = {
            'file_name': Path(file_path).name,
            'total_amount_before_tax': 'JSON_FAIL',
            'total_amount_after_tax': 'JSON_FAIL',
            'calculated_items_sum': 0.0,
            'internal_check_passed': False
        }
        save_to_csv(safe_data_dict) 
        final_output = response


    # --- File Saving Logic (.TXT file for reference) ---
    output_folder = "agent_outputs"
    os.makedirs(output_folder, exist_ok=True)
    
    file_name_only = Path(file_path).stem 
    save_path = os.path.join(output_folder, f"{file_name_only}.txt")

    try:
        with open(save_path, "w", encoding="utf-8") as text_file:
            text_file.write(final_output) 
        print(f"✅ Successfully saved final output to: {save_path}")
    except Exception as e:
        print(f"❌ Error saving file {save_path}: {e}")
        
    # --- FINAL STEP: DELETE THE ORIGINAL FILE ---
    # Necessary to stop the observer from triggering on file deletion, and to clean the folder
    try:
        os.remove(file_path)
        print(f"🗑️ Cleaned up original file: {Path(file_path).name}")
    except Exception as e:
        print(f"❌ Error deleting file {file_path.name}: {e}")
    print("="*60)


# ==============================================================================
# 3. MAIN EXECUTION BLOCK (Updated for Watchdog Monitoring)
# ==============================================================================

# 1. Define the handler class that watches for new files
class NewFileHandler(FileSystemEventHandler):
    
    # This function is called every time a new file is created
    def on_created(self, event):
        # We only care about files (not folders) ending with .jpg
        if not event.is_directory and event.src_path.lower().endswith('.jpg'):
            # The .5 second pause is important to ensure the file is completely written 
            # by the user before the script tries to read it.
            time.sleep(0.5) 
            agent(event.src_path)
            
    # This function is called every time a file is modified (e.g., when it is dropped in)
    def on_modified(self, event):
        # We use on_modified for reliable file drop detection as well
        if not event.is_directory and event.src_path.lower().endswith('.jpg'):
            time.sleep(0.5)
            agent(event.src_path)

if __name__ == "__main__":
    
    # Ensure the img folder exists before starting monitoring
    image_directory = "img" 
    os.makedirs(image_directory, exist_ok=True)
    
    print(f"⭐ Starting real-time file monitor on folder: {image_directory}...")
    print("⭐ Press Ctrl+C to stop monitoring.")

    # Set up the watchdog observer
    path = image_directory
    event_handler = NewFileHandler()
    observer = Observer()
    
    # Tell the observer to watch the target folder and use our custom handler
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    
    # Keep the main program running in the background
    try:
        while True:
            time.sleep(1) # Pauses the loop for 1 second to save CPU resources
    except KeyboardInterrupt:
        observer.stop()
        print("\nMonitor stopped by user.")
        
    observer.join()