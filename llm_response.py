from google import genai
from google.genai import errors
from google.genai.types import GenerateContentConfig
import os
from dotenv import load_dotenv

# Load environment variables from the .env file in the current directory
load_dotenv()

# The genai.Client() will automatically look for the key in the 
# GEMINI_API_KEY environment variable set by load_dotenv()
try:
    client = genai.Client()
    print("✅ Gemini API Client initialized successfully.")
except Exception as e:
    print("FATAL ERROR: Could not initialize Gemini Client.")
    print("Ensure GEMINI_API_KEY is correctly set in your .env file.")
    print(f"Underlying Error: {e}")
    client = None

# --- Configuration for JSON Output ---
# This remains critical to prevent JSONDecodeErrors in agent.py
JSON_CONFIG = GenerateContentConfig(
    response_mime_type="application/json"
)

# ----------------------------------------------------------------
# Removed the @retry decorator
# ----------------------------------------------------------------
def get_response(prompt: str):
    """
    Generates content from the Gemini model, enforcing JSON output.
    """
    if client is None:
        # If client setup failed due to missing key, return a safe error response
        return '{"error": "API Client Not Initialized due to missing API Key"}' 

    # The actual API call logic
    # NOTE: The genai client still has some built-in retries for transient errors,
    # so your code is not totally unprotected.
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=JSON_CONFIG
        )
        return response.text
    except errors.APIError as api_e:
        # Catch specific API errors (like 429, 400, 500) and log them
        print(f"🚨 API Error occurred during generate_content: {api_e}")
        # Return a structured error to be caught by the calling agent
        return f'{{"error": "API_CALL_FAILED", "message": "{str(api_e)}"}}'
    except Exception as e:
        # Catch any other unexpected errors
        print(f"🚨 An unexpected error occurred: {e}")
        return f'{{"error": "UNEXPECTED_ERROR", "message": "{str(e)}"}}'