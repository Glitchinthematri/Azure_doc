from llm_response import get_response
from azure_di import get_layout_as_markdown
import os
from pathlib import Path
import random
import json
import csv

# ==============================================================================
# 1. HELPER FUNCTION: CSV EXPORT
# ==============================================================================

def save_to_csv(data_dict, output_folder="agent_outputs", csv_filename="master_invoice_data.csv"):
    """Flattens the data dictionary and appends it to a master CSV file."""
    
    csv_path = os.path.join(output_folder, csv_filename)
    
    # Define the columns (headers) for the CSV file
    fieldnames = [
        'file_name', 
        'total_amount_before_tax', 
        'total_amount_after_tax',
        'calculated_items_sum',
        'internal_check_passed'
    ]

    # Flatten the data_dict into a single row
    csv_row = {
        'file_name': data_dict.get('file_name', 'N/A'),
        'total_amount_before_tax': data_dict.get('total_amount_before_tax', 'N/A'),
        'total_amount_after_tax': data_dict.get('total_amount_after_tax', 'N/A'),
        'calculated_items_sum': data_dict.get('calculated_items_sum', 0.0),
        'internal_check_passed': data_dict.get('internal_check_passed', False)
    }

    # Write to the CSV file
    try:
        file_exists = os.path.exists(csv_path)
        
        # Open the file in 'a' (append) mode
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write headers only if the file is new
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(csv_row)
            
        print(f"✅ Data successfully appended to {csv_filename}")

    except Exception as e:
        print(f"❌ ERROR writing CSV data: {e}")


# ==============================================================================
# 2. MAIN AGENT FUNCTION
# ==============================================================================

def agent(file_path):
    
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
    print("="*40)
    print(prompt)
    print("="*40)

    # Note: get_response is called outside the large try/except block to ensure 'response' is defined.
    response = get_response(prompt)
    print("Agent Response (Raw):", response)

    # --- Initialization before TRY/EXCEPT (PREVENTS UnboundLocalError) ---
    final_output = response 
    data_dict = {} 
    check_passed = False 
    calculated_sum = 0.0
    target_before_tax = 0.0

    # --- JSON Validation, CALCULATION, and Cleaning ---
    try:
        data_dict = json.loads(response)
        
        # Add the filename to the dictionary for easy tracking
        data_dict['file_name'] = Path(file_path).name 
        
        # 1. Sum up the item amounts from the list
        for item in data_dict.get('items', []):
            try:
                # Convert the amount string to a number (float)
                amount = float(item.get('item_amount', 0.0))
                calculated_sum += amount
            except ValueError:
                print(f"⚠️ Non-numeric amount found for item: {item.get('item_name')}. Skipping from sum check.")
        
        # 2. Get the target amount from the LLM response
        try:
            # This updates the initialized variable target_before_tax
            target_before_tax = float(data_dict.get('total_amount_before_tax', 0.0))
        except ValueError:
            print("❌ total_amount_before_tax is missing or not a valid number.")
            
        # 3. Compare the calculated sum and the target value (using rounding)
        check_passed = (round(calculated_sum, 2) == round(target_before_tax, 2))
        
        # 4. Store the check result and calculated sum in the final dictionary
        data_dict['internal_check_passed'] = check_passed
        data_dict['calculated_items_sum'] = round(calculated_sum, 2)
        
        print(f"💰 Internal Check: Items sum ({round(calculated_sum, 2)}) == Before Tax ({round(target_before_tax, 2)})? -> {check_passed}")

        # 5. Re-dump the validated data and update final_output
        final_output = json.dumps(data_dict, indent=4)
        print("✅ Response validated, checked, and cleaned.")
        
        # 6. EXPORT VALIDATED DATA TO CSV (Runs only on success)
        save_to_csv(data_dict) 
        
    except json.JSONDecodeError as e:
        # If JSON decoding fails, this block creates the error row for the CSV
        print(f"❌ WARNING: Failed to decode response as JSON. Error: {e}")
        
        # Create a simple data_dict with file_name and failure status for logging
        safe_data_dict = {
            'file_name': Path(file_path).name,
            'total_amount_before_tax': 'JSON_FAIL',
            'total_amount_after_tax': 'JSON_FAIL',
            'calculated_items_sum': 0.0,
            'internal_check_passed': False
        }
        
        # Write the failure row to the CSV
        save_to_csv(safe_data_dict) 
        
        # final_output remains the raw response text for the .txt file
        final_output = response


    # --- File Saving Logic (.TXT file for reference) ---
    
    output_folder = "agent_outputs"
    os.makedirs(output_folder, exist_ok=True)
    
    file_name_only = Path(file_path).stem 
    save_path = os.path.join(output_folder, f"{file_name_only}.txt")

    try:
        with open(save_path, "w", encoding="utf-8") as text_file:
            # Writes the clean JSON (if successful) or the raw, messy response (if JSON failed)
            text_file.write(final_output) 
        print(f"✅ Successfully saved final output to: {save_path}")
    except Exception as e:
        print(f"❌ Error saving file {save_path}: {e}")


# ==============================================================================
# 3. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == "__main__":
    image_directory = "img" 
    
    jpg_files = list(Path(image_directory).glob("*.jpg"))

    if jpg_files:
        file_path = random.choice(jpg_files)
        print(f"Calling agent for file_path: {file_path}")
        agent(file_path)
    else:
        print(f"⚠️ No .jpg files found in the '{image_directory}' directory.")