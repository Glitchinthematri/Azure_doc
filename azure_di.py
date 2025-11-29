import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1️⃣ Get Azure Document Intelligence credentials from .env



def get_layout_as_markdown(document_path: str) -> str:
    """
    Analyzes a document (PDF or image) using the 'prebuilt-layout' model
    and returns the full content as a single Markdown string.
    """
    endpoint = os.getenv("AZURE_DI_ENDPOINT")
    key = os.getenv("AZURE_DI_KEY")

    # 2️⃣ Validate environment variables
    if not endpoint or not key:
        raise ValueError(
            "❌ Missing Azure credentials. "
            "Please set AZURE_ENDPOINT and AZURE_KEY in your .env file"
        )

    # 3️⃣ Initialize Azure Document Intelligence client
    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
    if not os.path.exists(document_path):
        raise FileNotFoundError(f"❌ File not found: {document_path}")

    print(f"Analyzing document: {document_path}...")

    with open(document_path, "rb") as f:
        # 4️⃣ Use 'prebuilt-layout' and request 'markdown' output
        poller = client.begin_analyze_document(
            "prebuilt-layout",            # <-- Change 1: Use layout model
            body=f,
            output_content_format="markdown"  # <-- Change 2: Request markdown
        )
        result = poller.result()

    # 5️⃣ The result.content will be a single string containing the Markdown
    if result.content:
        return result.content
    else:
        return "No content extracted."


# --- UPDATED EXECUTION BLOCK ---
if __name__ == "__main__":
    
    # Path to your image (JPG works perfectly fine)
    doc_path = r"C:\Users\91956\OneDrive\Documents\Azure doc\img\X00016469619.jpg"
    
    try:
        markdown_output = get_layout_as_markdown(doc_path)
        print("\n----- 🦾 Extracted Markdown -----")
        print(markdown_output)

        # Optional: Save the markdown to a file to view it
        output_md_file = os.path.splitext(doc_path)[0] + ".md"
        with open(output_md_file, "w", encoding="utf-8") as f:
            f.write(markdown_output)
        print(f"\n✅ Markdown content also saved to: {output_md_file}")

    except Exception as e:
        print(f"❌ Error: {e}")