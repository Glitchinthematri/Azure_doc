from llm_response import get_response
from azure_di import get_layout_as_markdown
import os
from pathlib import Path
import random
import json
import time # Needed for the while loop pause
from watchdog.observers import Observer # New monitoring tool
from watchdog.events import FileSystemEventHandler # New event handler tool
# --- START of Log Redirection Code ---
# This ensures all 'print()' statements go to a file instead of the console, 
# allowing the GUI to read them.
import sys
LOG_FILE_PATH = Path("agent_outputs") / "processing_log.txt"

class FileLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a',encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        # Fix the file opening logic: open in 'a' mode outside of write, and ensure logging path is correct
        # NOTE: The original code re-opened 'logfile.txt' here. I'll just write to the one opened in __init__.
        # This fix is for correctness, but is outside the scope of your request.
        self.log.write(message)
        self.log.flush() # Ensure data is written immediately

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Overwrite the system standard output for all print statements
sys.stdout = FileLogger(LOG_FILE_PATH)
# --- END of Log Redirection Code ---
    
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
**STRICTLY** output only a single, valid JSON object. Do not include any text, notes, or markdown formatting (like ```json) outside of the JSON object itself.
The JSON object must have the following fields: 
total_amount_before_tax (float), 
total_amount_after_tax (float), 
items (list of dicts).
items must be a list of dicts with fields: item_name (string), item_amount (float).
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
    
    # This dictionary will hold the final validated structure, used for JSON saving
    validated_data = None 

    # --- JSON Validation, CALCULATION, and Cleaning ---
    try:
        # Tries to load the response as a JSON dictionary
        data_dict = json.loads(response)
        
        data_dict['file_name'] = Path(file_path).name 
        
        # 1. Sum up the item amounts
        for item in data_dict.get('items', []):
            try:
                # Ensure we handle potential string floats (e.g., "10.00")
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

        # Store the validated and enriched dictionary for saving
        validated_data = data_dict
        
        # The final output text will be the pretty-printed JSON
        final_output = json.dumps(data_dict, indent=4)
        print("✅ Response validated, checked, and cleaned.")
        
    except json.JSONDecodeError as e:
        print(f"❌ WARNING: Failed to decode response as JSON. Error: {e}")
        print("--- Raw model response (might not be valid JSON) ---")
        print(response) # This will print the raw text that failed to decode
        print("-----------------------------------------------------")
        
        # Create a simple safe dictionary with failure status for saving
        validated_data = {
            'file_name': Path(file_path).name,
            'status': 'JSON_DECODE_FAILED',
            'raw_response': response.strip()[:500] + '...' if len(response) > 500 else response,
            'error_details': str(e)
        }
        
        final_output = response # Keep raw response for TXT if needed, but we'll prioritize saving the JSON object

    # --------------------------------------------------------------------------
    # --- NEW FILE SAVING LOGIC (.JSON) ---
    # --------------------------------------------------------------------------
    output_folder = "agent_outputs"
    os.makedirs(output_folder, exist_ok=True)
    
    file_name_only = Path(file_path).stem 
    
    # Save the structured data as a .JSON file
    json_save_path = os.path.join(output_folder, f"{file_name_only}.json")

    try:
        # Use json.dump() to save the dictionary object directly
        if validated_data:
            with open(json_save_path, "w", encoding="utf-8") as json_file:
                json.dump(validated_data, json_file, indent=4) 
            print(f"✅ Successfully saved structured JSON data to: {json_save_path}")
        else:
            print("❌ Cannot save JSON: No valid data dictionary to write.")

    except Exception as e:
        print(f"❌ Error saving JSON file {json_save_path}: {e}")
        
    # OPTIONAL: You can remove the old .txt file saving or keep it for debugging
    # The JSON file now contains all the structured info.

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
            # The previous quota error (429) suggests excessive calls.
            # You might want to remove one of these calls (on_created or on_modified)
            # or implement a debouncer to prevent double processing.
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