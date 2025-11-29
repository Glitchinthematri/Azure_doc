import os
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# 1. Load Environment Variables
# This loads AZURE_DI_ENDPOINT and AZURE_DI_KEY from your .env file
load_dotenv() 

# --- Configuration ---
# Variables are loaded from the environment
endpoint = os.environ.get("AZURE_DI_ENDPOINT")
key = os.environ.get("AZURE_DI_KEY")

# IMPORTANT: Use the full, absolute path you found to fix the "file not found" error
# Replace the placeholder path with the one you copied (e.g., r"C:\Users\...\Md Istikhar.pdf")
pdf_file_path = r"Mohd.Aman Ali Hashmi.pdf"
# ---------------------

def extract_pdf_text_with_document_intelligence(file_path, endpoint, key):
    """
    Reads a local PDF file, sends it to Azure Document Intelligence for extraction, 
    and prints the contents.
    """
    # CRITICAL CHECK 1: Credentials
    if not endpoint or not key:
        print("CRITICAL ERROR: Environment variables were NOT loaded. Check your .env file and 'load_dotenv()'.")
        return

    # CRITICAL CHECK 2: File Exists
    if not os.path.exists(file_path):
        print(f"CRITICAL ERROR: The file '{file_path}' was not found at the specified path.")
        return

    print(f"--- 1. Initializing Azure Client for {file_path} ---")
    try:
        # Create the client
        document_intelligence_client = DocumentIntelligenceClient(
            endpoint=endpoint, 
            credential=AzureKeyCredential(key)
        )
        print("--- 1. Azure Client Initialized (Connection Test Passed) ---")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize Azure Client. Check endpoint URL. Error: {e}")
        return

    print(f"--- 2. Reading PDF file: {file_path} ---")
    
    # Read the file bytes in binary mode
    try:
        with open(file_path, "rb") as f:
            pdf_data = f.read()
    except Exception as e:
        print(f"CRITICAL ERROR: Could not read file data. Error: {e}")
        return

    print("--- 3. Calling Document Intelligence Layout Model (Prebuilt) ---")
    
    try:
        # **WORKAROUND FIX:** Using 'body' instead of 'document' to bypass the SDK conflict
        poller = document_intelligence_client.begin_analyze_document(
            model_id="prebuilt-layout", 
            body=pdf_data, 
            content_type="application/pdf"
        )
        
        # Wait for the operation to complete
        result = poller.result()
        
    except Exception as e:
        print(f"--- NETWORK/AUTH ERROR ---")
        print(f"Error during document analysis. Check your API Key and Network connection. Error: {e}")
        return

    print("\n" + "="*50)
    print("4. Extracted Document Content")
    print("="*50)
    
    # The 'content' property holds the full text extracted from the document
    if result.content:
        print(result.content)
    else:
        print("Analysis completed, but no readable text content was extracted.")

# --- Execution ---
if __name__ == "__main__":
    extract_pdf_text_with_document_intelligence(pdf_file_path, endpoint, key)